import datetime as dt,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import news_video as n
from leader_editorial import prepare_main_tibo,review_candidates

class TiboMainChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        p=patch.object(n,'ROOT',self.root);p.start();self.addCleanup(p.stop)
        self.now=dt.datetime(2026,10,27,1,tzinfo=dt.timezone.utc);self.time=(self.now-dt.timedelta(hours=1)).isoformat()
        self.post=dict(id='post1',source_id='x-leader-thsottiaux',url='https://x.com/thsottiaux/status/123',published=self.time,summary='Codex has a new workflow.',title='reset',kind='ai')
        db=n.database();db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',('post1','x-leader-thsottiaux','tibo','ai','reset',self.post['url'],self.time,self.post['summary'],self.time,self.time,'hash'));db.commit();db.close()
        n.dump(self.root/'data/leader-posts/post1.json',self.post)
    def scene(self,kind='commentary'):
        return dict(id='tibo',item_id='post1',author_handle='thsottiaux',section='AI 动态',tibo_message_type=kind)
    def ep(self,scenes):return dict(id='main-test',edition_slot='noon',scenes=scenes)
    def test_commentary_one_page_after_companies_before_social(self):
        ep=self.ep([self.scene(),dict(id='openai',section='AI 动态'),dict(id='claude',section='AI 动态'),dict(id='domestic',section='国内新闻')])
        audit=prepare_main_tibo(ep,self.root,self.now)
        self.assertEqual([s['id'] for s in ep['scenes']],['openai','claude','tibo','domestic']);self.assertEqual(audit['placement'],'after_company_news')
    def test_verified_reset_precedes_companies_but_not_overview(self):
        n.dump(self.root/'data/leader-posts/post1.json',dict(self.post,summary='We will reset Codex limits.'))
        scene=self.scene('reset');scene['reset_review']=dict(is_reset_announcement=True,context_verified=True,announcement_status='planned',quote='will reset Codex limits')
        ep=self.ep([dict(id='overview'),dict(id='openai',section='AI 动态'),scene,dict(id='domestic',section='国内新闻')])
        audit=prepare_main_tibo(ep,self.root,self.now)
        self.assertEqual([s['id'] for s in ep['scenes']],['overview','tibo','openai','domestic']);self.assertEqual(audit['placement'],'before_company_news')
    def test_keyword_alone_cannot_be_approved_reset(self):
        with self.assertRaisesRegex(ValueError,'verified affirmative reset'):prepare_main_tibo(self.ep([self.scene('reset')]),self.root,self.now)
        rows=review_candidates([dict(self.post,summary='We will reset Codex limits.')],self.root);self.assertTrue(rows[0]['reset_keyword_hint']);self.assertFalse(rows[0]['verified_reset'])
    def test_omission_requires_actual_skip_or_source_gap_reason(self):
        ep=self.ep([dict(id='openai',section='AI 动态')])
        with self.assertRaisesRegex(ValueError,'Review fresh Tibo post'):prepare_main_tibo(ep,self.root,self.now)
        ep['tibo_consideration']={'post1':dict(decision='defer',reason='Original reply context unavailable; do not guess')}
        audit=prepare_main_tibo(ep,self.root,self.now);self.assertEqual(audit['reviewed_posts'][0]['decision'],'defer')
    def test_more_than_one_tibo_page_rejected(self):
        with self.assertRaisesRegex(ValueError,'one Tibo page'):prepare_main_tibo(self.ep([self.scene(),dict(self.scene(),id='second')]),self.root,self.now)
    def test_temporary_trigger_path_unchanged(self):
        self.assertIsNone(prepare_main_tibo(dict(edition_slot='temporary',scenes=[self.scene()]),self.root,self.now))
