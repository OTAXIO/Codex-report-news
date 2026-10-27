import datetime as dt,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import news_video as n
from leader_editorial import apply_leader_identity_and_speech,prepare_main_leaders
class LeaderEditorialChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        p=patch.object(n,'ROOT',self.root);p.start();self.addCleanup(p.stop)
        self.source=dict(id='x-leader-sama',handle='sama',name='Sam Altman',vendor='OpenAI',type='leader_x',enabled=True,identity_checked=True,identity_label='OpenAI CEO',identity_evidence='https://openai.com/our-structure/')
        n.dump(self.root/'leader_sources.json',dict(accounts=[self.source]))
    def scene(self):return dict(id='sam',item_id='sam-post',source_type='leader_x',author_handle='sama',publisher='Sam Altman',published='2026-10-27T05:48:31+00:00',section='AI 动态',narration='Sam Altman 表示，团队正在改进产品。',claim_type='opinion')
    def test_checked_identity_on_screen_subject_and_original_minute_in_speech(self):
        ep=dict(scenes=[self.scene()]);apply_leader_identity_and_speech(ep,self.root);s=ep['scenes'][0]
        self.assertEqual(s['speaker_identity'],'OpenAI CEO');self.assertIn('Sam Altman 于北京时间10月27日13点48分',s['narration'])
        self.assertNotIn('CEO',s['narration']);self.assertIn('发帖表示，团队正在改进产品。',s['narration'])
        old=s['narration'];apply_leader_identity_and_speech(ep,self.root);self.assertEqual(s['narration'],old)
    def test_missing_exact_time_never_invents_clock(self):
        s=self.scene();s.update(published='2026-10-27',published_precision='date');ep=dict(scenes=[s]);apply_leader_identity_and_speech(ep,self.root)
        self.assertNotIn('点',s['narration']);self.assertEqual(s['speaker_identity'],'OpenAI CEO')
    def test_archived_original_time_overrides_editor_or_collection_time(self):
        s=self.scene();s['published']='2026-10-27T06:00:00+00:00'
        n.dump(self.root/'data/leader-posts/sam-post.json',dict(handle='sama',published='2026-10-27T05:48:31+00:00',fetched_at='2026-10-27T06:00:00+00:00'))
        apply_leader_identity_and_speech(dict(scenes=[s]),self.root)
        self.assertIn('13点48分',s['narration']);self.assertNotIn('14点0分',s['narration'])
    def test_actual_import_attribution_order_and_audit(self):
        now=dt.datetime.now(dt.timezone.utc);stamp=now.isoformat();s=self.scene()
        s.update(published=stamp,title='Sam 的产品观点',source_url='https://x.com/sama/status/123',evidence='test original',selection_reason='fresh normal opinion',attribution_checked=True)
        n.dump(self.root/'data/leader-posts/sam-post.json',dict(handle='sama',author='Sam Altman',published=stamp,source_type='leader_x',requires_context=False))
        db=n.database();db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',('sam-post',self.source['id'],'Sam Altman','ai','Post',s['source_url'],stamp,'statement',stamp,stamp,'hash'));db.commit();db.close()
        n.dump(self.root/'config.json',dict(editorial=dict(include_important_recaps=False),presentation=dict(prefer_overview=False),publication_preset={}))
        n.dump(self.root/'input.json',dict(id='leader-import',producer='Codex current conversation',edition_slot='noon',scenes=[s,dict(id='company',section='AI 动态',narration='公司发布产品。')]))
        n.import_editorial(self.root/'input.json')
        saved=n.load(self.root/'episodes/leader-import/episode.json')
        self.assertEqual([x['id'] for x in saved['scenes']],['company','sam'])
        self.assertIn('Sam Altman 于北京时间',saved['scenes'][1]['narration'])
        self.assertEqual(saved['scenes'][1]['speaker_identity'],'OpenAI CEO')
        self.assertEqual(n.load(self.root/'episodes/leader-import/leader-audit.json')['reviewed_posts'][0]['decision'],'include')
    def test_fresh_other_leader_post_is_considered_and_placed_after_companies(self):
        now=dt.datetime(2026,10,27,6,tzinfo=dt.timezone.utc);s=self.scene()
        db=n.database();db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',('sam-post',self.source['id'],'Sam Altman','ai','post','https://x.com/sama/status/123',s['published'],'A normal statement',s['published'],s['published'],'hash'));db.commit();db.close()
        ep=dict(id='main',edition_slot='noon',scenes=[s,dict(id='company',section='AI 动态'),dict(id='social',section='国内新闻')])
        audit=prepare_main_leaders(ep,self.root,now);self.assertEqual([s['id'] for s in ep['scenes']],['company','sam','social']);self.assertEqual(audit['reviewed_posts'][0]['decision'],'include')
        ep=dict(id='other',edition_slot='night',scenes=[dict(id='company',section='AI 动态')])
        with self.assertRaisesRegex(ValueError,'Review fresh leader post'):prepare_main_leaders(ep,self.root,now)
        ep['leader_consideration']={'sam-post':dict(decision='skip',reason='Unrelated sensitive subject; select other news')};prepare_main_leaders(ep,self.root,now)
