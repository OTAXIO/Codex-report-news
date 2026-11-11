"""Shared read-only X connection through Agent Reach: cold-start allowance, bounded retries,
per-account isolation, a catch-up pass and a health log. No X API keys, no login, no backend switch.

Why (2026-11-11): every 06:00 run from 11-06 to 11-11 hit a cold reader browser; the first account
timed out after 55 s and the old loop stopped *all* accounts and rumor searches for 5 minutes, so the
AI morning edition went out without X and without its rumor column. Now:

- the first request of a run gets `warmup_timeout_seconds` (cold browser start), later ones `timeout_seconds`;
- TIMEOUT / BUSY / an unreadable reply is retried once after a short pause, then that account is skipped
  and the run continues; only `max_consecutive_failures` transient failures in a row mean X is unreachable;
- accounts that failed transiently get one more try at the end of the run, when the browser is warm;
- hard platform signals (NEED_LOGIN, PLATFORM_BLOCKED, RATE_LIMITED, NEED_SETUP, local permission)
  still stop at once and are never retried or routed around, as before.

    python -B x_reach.py probe          # one live read: is X reachable now, and how fast
    python -B x_reach.py doctor         # per-account success over recent runs
"""
from __future__ import annotations
import argparse,datetime as dt,json,os,re,shutil,subprocess,time
from pathlib import Path

HARD={'NEED_SETUP','NEED_LOGIN','RATE_LIMITED','PLATFORM_BLOCKED','LOCAL_PERMISSION_DENIED'}
TRANSIENT={'TIMEOUT','UPSTREAM_BROKEN','BUSY'}
DEFAULTS=dict(timeout_seconds=60,warmup_timeout_seconds=150,retries=1,retry_backoff_seconds=15,
              max_consecutive_failures=3,transient_cooldown_seconds=120,catch_up_pass=True,max_pause_seconds=180)

def policy(cfg):
    return {**DEFAULTS,**{k:v for k,v in (cfg.get('x_collection') or {}).items() if k in DEFAULTS}}

def pause_of(result):
    """Seconds the reader asked us to wait (its breaker pauses a backend after UPSTREAM_BROKEN, e.g. 75 s)."""
    error=result.get('error') or {}
    waits=[error.get('retry_after_seconds')]+[a.get('retry_after_seconds') for a in (result.get('meta') or {}).get('attempts') or [] if isinstance(a,dict)]
    waits=[int(w) for w in waits if isinstance(w,(int,float)) and w>0]
    return max(waits) if waits else 0

def code_of(result):
    return None if result.get('ok') else (result.get('error') or {}).get('code','UPSTREAM_BROKEN')

def local_failure(process):
    # Classify locally; never persist raw stderr or session data.
    diagnostic=(process.stderr or '')+'\n'+(process.stdout or '')
    if re.search(r'PermissionError|\[Errno 13\]|Access is denied|EACCES',diagnostic,re.I):
        return dict(ok=False,error=dict(code='LOCAL_PERMISSION_DENIED',stage='local_runtime',
            message='Local runtime permission denied before a usable platform response.',
            hint='Run the same approved collector with access to the existing runtime and browser locks; do not change account or backend.'))
    return dict(ok=False,error=dict(code='UPSTREAM_BROKEN',stage='cli_response',
        message='Reader returned no valid structured response; inspect local runtime diagnostics.'))

def call(executable,args,timeout,run=None,hidden=None,quiet=None):
    """One Agent Reach invocation -> its JSON envelope, or a classified local failure."""
    if not executable:return dict(ok=False,error=dict(code='NEED_SETUP'))
    from quiet_background import hidden_kwargs,quiet_reach
    run=run or subprocess.run;hidden=hidden or hidden_kwargs;quiet=quiet or quiet_reach
    env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    try:
        with quiet():
            process=run([executable,*args,'--timeout',str(timeout)],capture_output=True,text=True,encoding='utf-8',
                        errors='replace',timeout=timeout+15,env=env,**hidden())
        try:result=json.loads((process.stdout or '').lstrip('﻿'))
        except (json.JSONDecodeError,ValueError):return local_failure(process)
        if not isinstance(result,dict) or not isinstance(result.get('ok'),bool):return local_failure(process)
        error=result.get('error') or {}
        if not result['ok'] and re.search(r'Could not resolve @',str(error.get('message',''))):
            # A renamed or missing account is that account's problem, not an X outage.
            result['error']=dict(error,code='NOT_FOUND',stage='account_not_found')
        return result
    except subprocess.TimeoutExpired:return dict(ok=False,error=dict(code='TIMEOUT',stage='process_timeout'))
    except PermissionError:return dict(ok=False,error=dict(code='LOCAL_PERMISSION_DENIED',stage='process_start'))
    except OSError:return dict(ok=False,error=dict(code='NEED_SETUP'))

def executable(cfg):
    return shutil.which((cfg.get('x_collection') or {}).get('executable','agent-reach'))

class Link:
    """Retry and failure accounting for one collection run; `attempt(timeout)` does the actual read."""
    def __init__(self,settings,sleep=time.sleep,clock=time.monotonic):
        self.p=settings;self.sleep=sleep;self.clock=clock;self.warm=False;self.consecutive=0;self.hard=None

    @property
    def unreachable(self):return self.consecutive>=self.p['max_consecutive_failures']

    def fetch(self,attempt):
        """Returns the last result with `_attempts` and `_seconds`; transient failures are retried once."""
        started=self.clock();result={}
        for index in range(self.p['retries']+1):
            if index:
                # Respect the reader's own pause (bounded), otherwise a short backoff; BUSY waits a little longer.
                wait=pause_of(result)
                self.sleep(min(wait+5,self.p['max_pause_seconds']) if wait else self.p['retry_backoff_seconds']*(2 if code_of(result)=='BUSY' else 1))
            result=dict(attempt(self.p['timeout_seconds'] if self.warm else self.p['warmup_timeout_seconds']))
            code=code_of(result)
            if code is None:self.warm=True;break
            if code in HARD or code=='NOT_FOUND':break
        code=code_of(result)
        if code is None or code=='NOT_FOUND':self.consecutive=0
        elif code in HARD:self.hard=code
        else:self.consecutive+=1
        result['_attempts']=index+1;result['_seconds']=round(self.clock()-started,1)
        return result

    def cooldown(self,result,now):
        """Hard signals keep the platform's retry_after (>=300 s); an unreachable reader gets a short pause."""
        if code_of(result) in HARD:
            try:delay=int((result.get('error') or {}).get('retry_after_seconds') or 300)
            except (TypeError,ValueError):delay=300
            return (now+dt.timedelta(seconds=max(delay,300))).isoformat()
        return (now+dt.timedelta(seconds=self.p['transient_cooldown_seconds'])).isoformat()

def stale_lock(lock,max_age_minutes=30):
    """A lock left by a killed run must not block every later run (seen as BUSY on 2026-11-09)."""
    try:age=time.time()-lock.stat().st_mtime
    except FileNotFoundError:return False
    try:pid=int(lock.read_text(encoding='utf-8').strip() or 0)
    except (OSError,ValueError):pid=0
    alive=False
    if pid:
        if os.name=='nt':
            out=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/NH'],capture_output=True,text=True,errors='replace').stdout
            alive=str(pid) in out
        else:
            try:os.kill(pid,0);alive=True
            except OSError:alive=False
    return not alive or age>max_age_minutes*60

def log_health(root,kind,report):
    """One line per run; only codes, counts and timings (no post bodies, no session data)."""
    rows=[dict(source_id=s.get('source_id'),handle=s.get('handle'),query=bool(s.get('query')),ok=s.get('ok'),
               code=s.get('error_code'),attempts=s.get('attempts'),seconds=s.get('seconds'),accepted=s.get('accepted'),caught_up=s.get('caught_up'))
          for s in report.get('sources',[])]
    line=dict(kind=kind,started=report.get('started'),finished=report.get('finished'),stopped=report.get('stopped'),
              reason=report.get('reason'),sources=rows)
    path=Path(root)/'data/x-health.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(line,ensure_ascii=False)+'\n')

def doctor(root,days=3):
    path=Path(root)/'data/x-health.jsonl'
    if not path.is_file():return dict(runs=0,note='no runs logged yet')
    cutoff=(dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=days)).isoformat()
    runs=[json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]
    runs=[r for r in runs if (r.get('started') or '')>=cutoff]
    accounts={}
    for run in runs:
        final={}
        for s in run['sources']:   # a caught-up account counts once, by its last read in the run
            if not s.get('query'):final[s.get('handle') or s.get('source_id')]=s
        for s in final.values():
            a=accounts.setdefault(s.get('handle') or s.get('source_id'),dict(ok=0,failed=0,last_ok=None,codes={}))
            if s.get('ok'):a['ok']+=1;a['last_ok']=max(a['last_ok'] or '',run.get('finished') or run.get('started') or '')
            else:a['failed']+=1;a['codes'][s.get('code')]=a['codes'].get(s.get('code'),0)+1
    stops={}
    for run in runs:
        if run.get('stopped'):stops[run.get('reason')]=stops.get(run.get('reason'),0)+1
    weak=sorted((h for h,a in accounts.items() if a['failed']>a['ok']),key=str)
    return dict(runs=len(runs),days=days,stopped_runs=stops,weak_accounts=weak,accounts=accounts)

def probe(root,cfg,handle='OpenAI'):
    p=policy(cfg);started=time.monotonic()
    result=call(executable(cfg),['twitter','tweets',handle,'--limit','1'],p['warmup_timeout_seconds'])
    return dict(ok=result.get('ok'),code=code_of(result),seconds=round(time.monotonic()-started,1),
                latest=(result.get('items') or [{}])[0].get('published_at'),hint=(result.get('error') or {}).get('hint'))

if __name__=='__main__':
    import news_video as n
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action',choices=['probe','doctor']);parser.add_argument('--handle',default='OpenAI');parser.add_argument('--days',type=int,default=3)
    args=parser.parse_args()
    out=probe(n.ROOT,n.config(),args.handle) if args.action=='probe' else doctor(n.ROOT,args.days)
    print(json.dumps(out,ensure_ascii=False,indent=2))
