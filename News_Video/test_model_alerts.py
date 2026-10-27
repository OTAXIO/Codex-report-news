import datetime as dt,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import news_video as n,leader_sources as x,model_alerts as m
class ModelAlertChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);p=patch.object(n,'ROOT',self.root);p.start();self.addCleanup(p.stop);self.now=dt.datetime.now(n.UTC)
        n.dump(self.root/'config.json',dict(x_enabled=True,x_collection=dict(mode='agent_reach_read_only'),publication_preset={},editorial={},model_alerts=dict(max_age_hours=6,publication_authorized_by_user=True)))
        self.source=dict(id='x-official-openai',handle='OpenAI',name='OpenAI',vendor='OpenAI',type='official_x',enabled=True,identity_checked=True)
        n.dump(self.root/'leader_sources.json',dict(accounts=[self.source]))
    def post(self,key):
        item=dict(url='https://x.com/OpenAI/status/'+str(key),text='Introducing GPT-9 Terra, our new model. Available now.',published_at=self.now.isoformat())
        with patch.object(x.shutil,'which',return_value='fake'):x.collect(runner=lambda *args:dict(ok=True,items=[item]))
        return x.normalize_post(item,self.source,self.now)['id']
    def review(self):
        return dict(is_new_model_release=True,release_status='released',context_verified=True,model_name='GPT-9 Terra',title='OpenAI 发布 GPT-9 Terra',summary='测试用虚构事件，绝不上传。',quote='Introducing GPT-9 Terra',narration='OpenAI 发布 GPT-9 Terra。')
    def test_baseline_fresh_review_and_duplicate_event(self):
        self.assertTrue(m.scan(self.now)['initialized']);key=self.post(123);self.assertEqual(m.scan(self.now)['new_alerts'],[key]);self.assertFalse(m.scan(self.now)['new_alerts'])
        n.dump(self.root/'review.json',dict(self.review(),is_new_model_release=False))
        with self.assertRaises(ValueError):m.draft(key,self.root/'review.json',self.now)
        n.dump(self.root/'review.json',self.review())
        with patch('important_events.entries',return_value=[]):alert=m.draft(key,self.root/'review.json',self.now)
        ep=n.load(self.root/'episodes'/alert['episode_id']/'episode.json');self.assertEqual(ep['scenes'][0]['id'],'overview');self.assertEqual(ep['scenes'][1]['source_type'],'official_x');self.assertFalse(ep['counts_toward_daily_main_limit'])
        second=self.post(124);m.scan(self.now)
        with patch('important_events.entries',return_value=[]),self.assertRaises(ValueError):m.draft(second,self.root/'review.json',self.now)
    def test_hourly_scope_only_tibo_and_production_still_reads_all(self):
        n.dump(self.root/'leader_sources.json',dict(accounts=[dict(self.source,id='tibo',handle='thsottiaux',type='leader_x'),self.source,dict(self.source,id='sam',handle='sama',type='leader_x')]))
        called=[]
        def runner(executable,source,*args):called.append(source['handle']);return dict(ok=True,items=[])
        with patch.object(x.shutil,'which',return_value='fake'):x.collect(scope='hourly',runner=runner)
        self.assertEqual(called,['thsottiaux'])
        called.clear()
        with patch.object(x.shutil,'which',return_value='fake'):x.collect(runner=runner)
        self.assertEqual(called,['thsottiaux','OpenAI','sama'])
    def test_hourly_monitor_does_not_fetch_social_rss(self):
        import hourly_monitor as monitor
        with patch.object(n,'collect') as rss,patch.object(x,'collect',return_value={'sources':[]}) as tweets,patch.object(monitor.reset_alerts,'scan',return_value={'pending':[]}):
            report=monitor.run()
        rss.assert_not_called()
        tweets.assert_called_once_with(only=None,scope='hourly')
        self.assertNotIn('social',report)
    def test_old_existing_post_does_not_urgent_republish(self):
        self.post(123);self.assertTrue(m.scan(self.now)['initialized']);self.assertEqual(m.pending(),[])

    def test_google_and_kimi_new_models_enter_semantic_review_queue(self):
        self.assertTrue(m.scan(self.now)['initialized'])
        for index,(company,model,handle) in enumerate([('Google','Gemini 99','GoogleAI'),('Kimi','Kimi 99','Kimi_Moonshot')]):
            source=dict(self.source,id='x-official-'+handle.lower(),handle=handle,name=company,vendor=company)
            accounts=n.load(self.root/'leader_sources.json')['accounts'];accounts.append(source);n.dump(self.root/'leader_sources.json',dict(accounts=accounts))
            post=x.normalize_post(dict(url='https://x.com/'+handle+'/status/'+str(900+index),text='Introducing '+model+'. Available now.',published_at=self.now.isoformat()),source,self.now)
            n.dump(self.root/'data/leader-posts'/(post['id']+'.json'),post)
            self.assertIn(post['id'],m.scan(self.now)['new_alerts'])

    def test_product_support_for_other_models_is_not_model_release_alert(self):
        source=dict(self.source,id='x-official-workbuddy_ai',handle='WorkBuddy_AI',name='WorkBuddy',vendor='Tencent',model_release_alerts=False)
        n.dump(self.root/'leader_sources.json',dict(accounts=[source]));m.scan(self.now)
        post=x.normalize_post(dict(url='https://x.com/WorkBuddy_AI/status/999',text='GPT-99 Terra is now available in WorkBuddy.',published_at=self.now.isoformat()),source,self.now)
        n.dump(self.root/'data/leader-posts'/(post['id']+'.json'),post)
        self.assertEqual(m.scan(self.now)['new_alerts'],[])
