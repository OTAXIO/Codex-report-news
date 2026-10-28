import datetime as dt,json,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext
import news_video as n
import leader_sources as x

class LeaderChecks(unittest.TestCase):
    def test_hourly_compact_cannot_hide_stop_errors_or_reset_work(self):
        import hourly_monitor as monitor
        report=dict(leaders=dict(sources=[dict(handle='thsottiaux',ok=False,error_code='NEED_LOGIN',error_stage='reading')]),
                    resets=dict(new_alerts=['new-reset'],pending=['new-reset','existing-draft']))
        result=monitor.compact_report(report)
        self.assertFalse(result['source_ok']);self.assertEqual(result['source_errors'][0]['error_code'],'NEED_LOGIN')
        self.assertEqual(result['pending'],['new-reset','existing-draft']);self.assertEqual(result['new_alerts'],['new-reset'])
        self.assertFalse(monitor.compact_report(dict(leaders=dict(sources=[])))['source_ok'])

    def test_hidden_process_flags_are_forwarded_without_changing_result(self):
        envelope=dict(ok=True,items=[])
        process=subprocess.CompletedProcess([],0,json.dumps(envelope),'')
        with patch.object(x.subprocess,'run',return_value=process) as run,patch.object(x,'hidden_kwargs',return_value=dict(creationflags=123)):
            self.assertEqual(x.run_reach('reader',dict(handle='thsottiaux'),10,40),envelope)
        self.assertEqual(run.call_args.kwargs['creationflags'],123)
        self.assertTrue(run.call_args.kwargs['capture_output'])

    def test_local_browser_lock_denial_is_not_an_x_failure(self):
        process=subprocess.CompletedProcess([],1,stdout='',stderr='PermissionError: [Errno 13] browser-locks/lock; cookie=PRIVATE_SECRET')
        with patch.object(x.subprocess,'run',return_value=process):
            result=x.run_reach('reader',dict(handle='thsottiaux'),10,40)
        self.assertEqual(result['error']['code'],'LOCAL_PERMISSION_DENIED')
        self.assertNotIn('PRIVATE_SECRET',json.dumps(result))

    def test_platform_stop_survives_wrapper_unchanged(self):
        envelope=dict(ok=False,error=dict(code='PLATFORM_BLOCKED',message='Verification required'))
        with patch.object(x.subprocess,'run',return_value=subprocess.CompletedProcess([],1,json.dumps(envelope),'')):
            self.assertEqual(x.run_reach('reader',dict(handle='thsottiaux'),10,40),envelope)

    def test_permission_denied_at_process_start(self):
        with patch.object(x.subprocess,'run',side_effect=PermissionError('Denied')):
            self.assertEqual(x.run_reach('reader',dict(handle='thsottiaux'),10,40)['error']['code'],'LOCAL_PERMISSION_DENIED')

    def setUp(self):
        quiet=patch.object(x,'quiet_reach',side_effect=lambda:nullcontext());quiet.start();self.addCleanup(quiet.stop)
        self.now=dt.datetime.now(n.UTC)
        self.source=x.registry()[0]
        self.post=dict(text='Codex has a new documented feature. Here is how the preview works.',
            url='https://twitter.com/thsottiaux/status/1234567890?s=20',published_at=self.now.isoformat())

    def test_status_identity_and_freshness(self):
        post=x.normalize_post(self.post,self.source,self.now)
        self.assertEqual(post['url'],'https://x.com/thsottiaux/status/1234567890')
        self.assertEqual(post['publisher'],'tibo');self.assertEqual(post['company'],'OpenAI')
        for update in [dict(url='https://x.com/fan/status/123'),dict(published_at=None),
                       dict(published_at=(self.now-dt.timedelta(days=5)).isoformat()),dict(snippet_only=True)]:
            with self.assertRaises(ValueError):x.normalize_post(dict(self.post,**update),self.source,self.now)

    def test_public_claim_requires_attribution(self):
        evidence=x.normalize_post(self.post,self.source,self.now)
        scene=dict(source_type='leader_x',author_handle='thsottiaux',claim_type='preview',
                   attribution_checked=True,narration='tibo 预告了一项 Codex 新功能。')
        x.validate_scene(scene,evidence)
        with self.assertRaises(ValueError):x.validate_scene(dict(scene,narration='OpenAI 正式发布了新功能。'),evidence)
        with self.assertRaises(ValueError):x.validate_scene(scene,dict(evidence,requires_context=True))
        x.validate_scene(dict(scene,context_evidence='Verified original thread and quoted post'),dict(evidence,requires_context=True))

    def test_official_source_type_is_preserved_and_validated(self):
        source=dict(self.source,type='official_x',handle='OpenAI',name='OpenAI')
        post=dict(self.post,url='https://x.com/OpenAI/status/1234567890')
        evidence=x.normalize_post(post,source,self.now)
        self.assertEqual(evidence['source_type'],'official_x')
        scene=dict(source_type='official_x',author_handle='OpenAI',claim_type='announcement',attribution_checked=True,narration='OpenAI 发布新模型。')
        x.validate_scene(scene,evidence)
        with self.assertRaises(ValueError):x.validate_scene(dict(scene,source_type='leader_x'),evidence)
        self.assertTrue(x.normalize_post(dict(post,raw=dict(is_retweet=True)),source,self.now)['requires_context'])

    def test_ai_refreshes_x_social_does_not(self):
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.workspace(root);n.dump(root/'sources.json',[])
            with patch.object(n,'ROOT',root),patch.object(x,'collect',return_value=dict(accepted_items=0)) as reader,redirect_stdout(io.StringIO()):
                self.assertIn('x',n.collect('ai'));reader.assert_called_once()
                reader.reset_mock();self.assertNotIn('x',n.collect('social'));reader.assert_not_called()

    def test_company_priority(self):
        def row(name,vendor,order):return dict(title=name,kind='ai',priority_tier=1,preferred_vendor_order=vendor,source_priority=order,published=self.now.isoformat())
        rows=[row('OpenAI official',0,100),row('Claude official',1,100),row('Boris',1,10),row('Sam',0,10),row('tibo',0,0)]
        self.assertEqual([r['title'] for r in sorted(rows,key=n.candidate_order)],['tibo','Sam','OpenAI official','Boris','Claude official'])

    def workspace(self,path):
        n.dump(path/'config.json',dict(x_enabled=True,x_collection=dict(mode='agent_reach_read_only'),upload_enabled=False))
        n.dump(path/'leader_sources.json',dict(accounts=[self.source,dict(self.source,id='second',handle='sama',name='Sam Altman')]))

    def test_standalone_tweet_and_idempotent_ingestion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.workspace(root)
            with patch.object(n,'ROOT',root),patch.object(x.shutil,'which',return_value='fake-read-only-cli'):
                runner=lambda *args:dict(ok=True,items=[self.post])
                a=x.collect(only='thsottiaux',runner=runner);b=x.collect(only='thsottiaux',runner=runner)
                self.assertEqual(a['new_items'],1);self.assertEqual(b['new_items'],0)
                db=n.database();self.assertEqual(db.execute('select count(*) from items').fetchone()[0],1);db.close()
                # No official item is required for an eligible leader candidate.
                self.assertEqual(len(list((root/'data/leader-posts').glob('*.json'))),1)

    def test_stop_and_cooldown_without_backend_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.workspace(root);calls=[]
            def runner(*args):calls.append(args);return dict(ok=False,error=dict(code='RATE_LIMITED',retry_after_seconds=900))
            with patch.object(n,'ROOT',root),patch.object(x.shutil,'which',return_value='fake-read-only-cli'):
                report=x.collect(runner=runner);self.assertEqual(report['reason'],'RATE_LIMITED')
                self.assertEqual(len(calls),1)
                report=x.collect(runner=runner);self.assertEqual(report['reason'],'COOLDOWN');self.assertEqual(len(calls),1)

    def test_login_must_be_resolved_before_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.workspace(root);calls=[]
            def runner(*args):calls.append(args);return dict(ok=False,error=dict(code='NEED_LOGIN'))
            with patch.object(n,'ROOT',root),patch.object(x.shutil,'which',return_value='fake-read-only-cli'):
                x.collect(runner=runner)
                report=x.collect(runner=runner);self.assertTrue(report['requires_user_resolution']);self.assertEqual(len(calls),1)
                x.collect(runner=runner,resume_after_fix=True);self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
