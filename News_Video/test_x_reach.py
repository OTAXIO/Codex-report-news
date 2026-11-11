"""2026-11-11: one slow X account must not cost the whole run (the 06:00 cold-browser timeouts)."""
import datetime as dt,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext
import news_video as n
import leader_sources as x
import x_reach

HERE=Path(__file__).resolve().parent

def tweet(handle,now):
    return dict(text='A meaningful product update from '+handle+' today.',url=f'https://x.com/{handle}/status/{abs(hash(handle))%10**12}',published_at=now.isoformat())

class Scripted:
    """Runner that answers per handle from a script of results; records the timeout of every call."""
    def __init__(self,now,script=None):self.now=now;self.script=script or {};self.calls=[]
    def __call__(self,executable,source,limit,timeout):
        self.calls.append((source['handle'],timeout))
        queue=self.script.get(source['handle'])
        code=queue.pop(0) if queue else None
        if code:return dict(ok=False,error=dict(code=code))
        return dict(ok=True,items=[tweet(source['handle'],self.now)])

class LeaderRobustness(unittest.TestCase):
    def setUp(self):
        quiet=patch.object(x,'quiet_reach',side_effect=lambda:nullcontext());quiet.start();self.addCleanup(quiet.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for name in ['config.json','sources.json','leader_sources.json']:shutil.copy2(HERE/name,self.root/name)
        for p in [patch.object(n,'ROOT',self.root),patch.object(x.shutil,'which',return_value='reader')]:p.start();self.addCleanup(p.stop)
        self.now=dt.datetime.now(n.UTC);self.handles=[s['handle'] for s in x.registry() if s.get('enabled') and s.get('identity_checked') and s.get('group','ai')=='ai']

    def collect(self,runner,**kw):return x.collect(runner=runner,sleep=lambda s:None,scope='ai',**kw)

    def test_cold_first_call_gets_the_warmup_allowance(self):
        runner=Scripted(self.now);self.collect(runner)
        p=x_reach.policy(n.config())
        self.assertEqual(runner.calls[0][1],p['warmup_timeout_seconds'])
        self.assertTrue(all(t==p['timeout_seconds'] for _,t in runner.calls[1:]))

    def test_one_timeout_skips_one_account_and_is_caught_up(self):
        first=self.handles[0]
        runner=Scripted(self.now,{first:['TIMEOUT','TIMEOUT']})   # fails twice (with its retry), works at the end
        report=self.collect(runner)
        self.assertFalse(report['stopped']);self.assertEqual(report['pending_handles'],[])
        self.assertEqual(report['read_ok'],len(self.handles))
        caught=[s for s in report['sources'] if s.get('caught_up')]
        self.assertEqual([s['handle'] for s in caught],[first]);self.assertTrue(caught[0]['ok'])
        self.assertEqual(runner.calls[-1][0],first)
        health=[json.loads(l) for l in (self.root/'data/x-health.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(health[-1]['kind'],'leaders')

    def test_reader_down_stops_after_consecutive_failures_with_short_cooldown(self):
        runner=Scripted(self.now,{h:['TIMEOUT']*4 for h in self.handles})
        report=self.collect(runner)
        self.assertEqual(report['reason'],'X_UNREACHABLE')
        limit=x_reach.policy(n.config())['max_consecutive_failures']
        self.assertEqual(len({h for h,_ in runner.calls}),limit)
        self.assertEqual(set(report['pending_handles']),set(self.handles))
        wait=dt.datetime.fromisoformat(report['retry_after_utc'])-dt.datetime.fromisoformat(report['started'])
        self.assertLess(wait.total_seconds(),300)

    def test_retry_failed_reads_only_the_pending_accounts(self):
        runner=Scripted(self.now,{h:['TIMEOUT']*4 for h in self.handles})
        self.collect(runner)
        state=json.loads((self.root/'data/leader-collection-state.json').read_text(encoding='utf-8'))
        state['retry_after_utc']=None;(self.root/'data/leader-collection-state.json').write_text(json.dumps(state),encoding='utf-8')
        again=Scripted(self.now);report=self.collect(again,retry_failed=True)
        self.assertEqual({h for h,_ in again.calls},set(state['pending_handles']))
        self.assertFalse(report['stopped'])

    def test_hard_signal_is_never_retried(self):
        runner=Scripted(self.now,{self.handles[0]:['PLATFORM_BLOCKED']})
        report=self.collect(runner)
        self.assertEqual(report['reason'],'PLATFORM_BLOCKED');self.assertEqual(len(runner.calls),1)

    def test_stale_lock_from_a_killed_run_is_cleared(self):
        lock=self.root/'data/leader-collection.lock';lock.parent.mkdir(parents=True,exist_ok=True)
        lock.write_text('999999',encoding='utf-8')   # no such process
        report=self.collect(Scripted(self.now));self.assertFalse(report['stopped'])
        lock.write_text(str(os.getpid()),encoding='utf-8')   # a live run keeps its lock
        self.assertEqual(self.collect(Scripted(self.now))['reason'],'BUSY');lock.unlink()

    def test_doctor_names_weak_accounts(self):
        self.collect(Scripted(self.now,{self.handles[1]:['TIMEOUT']*4}))   # read, retry, catch-up, retry: all fail
        report=x_reach.doctor(self.root)
        self.assertEqual(report['runs'],1);self.assertEqual(report['weak_accounts'],[self.handles[1]])

class CallTests(unittest.TestCase):
    def test_missing_account_is_not_an_outage(self):
        import subprocess
        envelope=dict(ok=False,error=dict(code='UPSTREAM_BROKEN',message='Could not resolve @renamed'))
        done=subprocess.CompletedProcess([],1,json.dumps(envelope),'')
        result=x_reach.call('reader',['twitter','tweets','renamed'],60,run=lambda *a,**k:done,hidden=lambda:{},quiet=nullcontext)
        self.assertEqual(result['error']['code'],'NOT_FOUND')

class PauseTests(unittest.TestCase):
    def test_retry_waits_for_the_readers_own_pause(self):
        waits=[];answers=[dict(ok=False,error=dict(code='UPSTREAM_BROKEN'),meta=dict(attempts=[dict(retry_after_seconds=75)])),dict(ok=True,items=[])]
        link=x_reach.Link(x_reach.policy({}),sleep=waits.append)
        self.assertTrue(link.fetch(lambda t:answers.pop(0))['ok'])
        self.assertEqual(waits,[80])
        long=x_reach.Link(x_reach.policy({}),sleep=waits.append)
        long.fetch(lambda t:dict(ok=False,error=dict(code='TIMEOUT',retry_after_seconds=3600)))
        self.assertEqual(waits[-1],x_reach.policy({})['max_pause_seconds'])

if __name__=='__main__':unittest.main()
