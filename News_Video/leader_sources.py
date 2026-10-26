"""Bounded, read-only Agent Reach ingestion; no X API keys or browser access."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
import news_video as n

STOP_CODES={'NEED_SETUP','NEED_LOGIN','UPSTREAM_BROKEN','TIMEOUT','RATE_LIMITED','PLATFORM_BLOCKED','BUSY','LOCAL_PERMISSION_DENIED'}

def registry():
    return n.load(n.ROOT/'leader_sources.json')['accounts']

def normalize_post(item, source, now, hours=48):
    """Only a dated, authored status with actual body becomes a candidate."""
    url=n.normalized_url(item.get('url',''),allow_x=True)
    if url.split('/')[3].lower()!=source['handle'].lower():raise ValueError('Wrong author')
    body=n.text(item.get('text',''))
    if len(body)<2:raise ValueError('Missing or insufficient post body')
    if item.get('snippet_only') or item.get('truncated') or item.get('is_truncated'):
        raise ValueError('Incomplete post; fetch the full original before use')
    published=n.parse_date(item.get('published_at'))
    if not published:raise ValueError('Missing original publication time')
    stamp=dt.datetime.fromisoformat(published)
    if not now-dt.timedelta(hours=hours)<=stamp<=now+dt.timedelta(minutes=15):
        raise ValueError('Outside fresh-news window')
    key=hashlib.sha256(url.encode()).hexdigest()[:20]
    return dict(id=key,source_id=source['id'],publisher=source['name'],kind='ai',
                title=body[:180],url=url,published=published,summary=body[:20000],
                company=source['vendor'],handle=source['handle'],author=source['name'],
                attribution=source['name']+' (@'+source['handle']+')',
                source_type='leader_x',requires_context=bool(item.get('is_reply') or item.get('is_repost') or item.get('is_quote')),
                context_policy='Check reply/quote/thread context before editorial use; individual statement is not an official release.',
                fetched_at=now.isoformat())

def validate_scene(scene, evidence):
    if scene.get('source_type')!='leader_x':raise ValueError('Leader source_type missing')
    if scene.get('author_handle','').lower()!=evidence['handle'].lower():raise ValueError('Leader author attribution missing')
    if scene.get('claim_type') not in {'announcement','preview','opinion','experience','reshare'}:
        raise ValueError('Classify leader statement before use')
    if not scene.get('attribution_checked'):raise ValueError('Review public attribution and claim status')
    if evidence['requires_context'] and not scene.get('context_evidence'):
        raise ValueError('Reply/repost requires original context evidence')
    # The producer must actually attribute the tweet in public narration.
    public=scene.get('narration','').casefold()
    aliases=[evidence['author'],evidence['handle']]+scene.get('author_spoken_aliases',[])
    if not any(a and a.casefold() in public for a in aliases):raise ValueError('Attribute the speaker in narration')

def local_failure(process):
    # Classify locally; never persist raw stderr or session data.
    diagnostic=(process.stderr or '')+'\n'+(process.stdout or '')
    if re.search(r'PermissionError|\[Errno 13\]|Access is denied|EACCES',diagnostic,re.I):
        return dict(ok=False,error=dict(code='LOCAL_PERMISSION_DENIED',stage='local_runtime',
            message='Local runtime permission denied before a usable platform response.',
            hint='Run the same approved collector with access to the existing runtime and browser locks; do not change account or backend.'))
    return dict(ok=False,error=dict(code='UPSTREAM_BROKEN',stage='cli_response',
        message='Reader returned no valid structured response; inspect local runtime diagnostics.'))


def run_reach(executable, source, limit, timeout):
    env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    try:
        process=subprocess.run([executable,'twitter','tweets',source['handle'],'--limit',str(limit),'--timeout',str(timeout)],
                               capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout+15,env=env)
        try:result=json.loads(process.stdout.lstrip('\ufeff'))
        except (json.JSONDecodeError,ValueError):return local_failure(process)
        if not isinstance(result,dict) or not isinstance(result.get('ok'),bool):return local_failure(process)
        return result
    except subprocess.TimeoutExpired:return dict(ok=False,error=dict(code='TIMEOUT'))
    except PermissionError:return dict(ok=False,error=dict(code='LOCAL_PERMISSION_DENIED',stage='process_start'))
    except OSError:return dict(ok=False,error=dict(code='NEED_SETUP'))

def collect(hours=48, only=None, runner=run_reach, resume_after_fix=False):
    cfg=n.config();policy=cfg.get('x_collection',{})
    if not cfg.get('x_enabled'):raise ValueError('X sources disabled')
    if not 1<=hours<=72:raise ValueError('Freshness window must be 1-72 hours')
    accounts=[s for s in registry() if s.get('enabled') and s.get('identity_checked')]
    if only:
        accounts=[s for s in accounts if s['handle'].lower()==only.lower().lstrip('@')]
        if not accounts:raise ValueError('Handle is not in the verified allowlist')
    executable=shutil.which(policy.get('executable','agent-reach'))
    now=dt.datetime.now(n.UTC);run_id=now.strftime('%Y%m%dT%H%M%S%f')+'_leaders'
    report=dict(id=run_id,kind='leaders',started=now.isoformat(),model_calls=0,paid_api_calls=0,
                sources=[],new_items=0,accepted_items=0,rejected_items=0,stopped=False)
    directory=n.ROOT/'data/collections'/run_id;directory.mkdir(parents=True,exist_ok=True)
    state_path=n.ROOT/'data/leader-collection-state.json'
    previous=n.load(state_path) if state_path.exists() else {}
    auth_pending=previous.get('reason') in {'NEED_LOGIN','PLATFORM_BLOCKED'}
    if auth_pending and not resume_after_fix:
        report.update(stopped=True,reason=previous['reason'],requires_user_resolution=True)
        n.dump(directory/'report.json',report);return report
    if previous.get('retry_after_utc') and dt.datetime.fromisoformat(previous['retry_after_utc'])>now and not (auth_pending and resume_after_fix):
        report.update(stopped=True,reason='COOLDOWN',retry_after_utc=previous['retry_after_utc'])
        n.dump(directory/'report.json',report);return report
    lock=n.ROOT/'data/leader-collection.lock'
    try:handle=lock.open('x',encoding='utf-8')
    except FileExistsError:
        report.update(stopped=True,reason='BUSY');n.dump(directory/'report.json',report);return report
    with handle:handle.write(str(os.getpid()))
    db=n.database()
    try:
        for source in accounts:
            result=runner(executable,source,min(10,max(1,policy.get('limit_per_account',5))),policy.get('timeout_seconds',40)) if executable else dict(ok=False,error=dict(code='NEED_SETUP'))
            status=dict(source_id=source['id'],handle=source['handle'],ok=result['ok'],accepted=0,rejected=0)
            # Only content fields are retained. Never persist raw backend/session dumps.
            if result.get('meta',{}).get('update'):report['update_available']=result['meta']['update'].get('latest')
            if not result['ok']:
                code=result.get('error',{}).get('code','UPSTREAM_BROKEN');status['error_code']=code
                if result.get('error',{}).get('stage') in {'local_runtime','process_start','cli_response'}:
                    status['error_stage']=result['error']['stage']
                report['sources'].append(status)
                if code!='NOT_FOUND':
                    report.update(stopped=True,reason=code)
                    try:delay=int(result.get('error',{}).get('retry_after_seconds',300))
                    except (TypeError,ValueError):delay=300
                    report['retry_after_utc']=(now+dt.timedelta(seconds=max(delay,300))).isoformat()
                    break
                continue
            for item in result.get('items',[]):
                try:post=normalize_post(item,source,now,hours)
                except (ValueError,TypeError,AttributeError):
                    status['rejected']+=1;report['rejected_items']+=1;continue
                existed=db.execute('SELECT id FROM items WHERE id=?',(post['id'],)).fetchone()
                report['new_items']+=int(not existed);report['accepted_items']+=1;status['accepted']+=1
                db.execute('''INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                    last_seen=excluded.last_seen,title=excluded.title,summary=excluded.summary,content_hash=excluded.content_hash''',
                    (post['id'],source['id'],post['publisher'],'ai',post['title'],post['url'],post['published'],post['summary'],now.isoformat(),now.isoformat(),hashlib.sha256(post['summary'].encode()).hexdigest()))
                db.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?)',(post['id'],source['id'],now.isoformat()))
                n.dump(n.ROOT/'data/leader-posts'/(post['id']+'.json'),post)
            report['sources'].append(status)
        report['finished']=dt.datetime.now(n.UTC).isoformat()
        db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(run_id,'leaders',report['started'],report['finished'],json.dumps(report,ensure_ascii=False)))
        db.commit();n.dump(directory/'report.json',report);n.dump(state_path,report)
    finally:db.close();lock.unlink(missing_ok=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hours',type=int,default=48);p.add_argument('--handle')
    p.add_argument('--resume-after-fix',action='store_true',help='Only after the user resolved login/verification; never bypasses rate-limit cooldown')
    a=p.parse_args();print(json.dumps(collect(a.hours,a.handle,resume_after_fix=a.resume_after_fix),ensure_ascii=False,indent=2))
