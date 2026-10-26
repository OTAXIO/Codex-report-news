import datetime as dt,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import news_video as n
import leader_sources as x

class LeaderChecks(unittest.TestCase):
    def setUp(self):
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
