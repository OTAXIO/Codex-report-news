import copy,datetime as dt,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import freshness as f
import news_video as n
import upload_bridge as u
from layout_policy import prepare_overview,validate_overview

class FreshnessChecks(unittest.TestCase):
    def setUp(self):self.now=dt.datetime(2026,10,29,10,tzinfo=f.UTC)
    def evidence(self,age=0,**extra):return dict(f.time_evidence(dict(published=(self.now-dt.timedelta(hours=age)).isoformat(),url='https://official.example/news')),**extra)
    def test_inclusive_boundary_future_and_bad_time(self):
        for age in [47+59/60,48]:self.assertTrue(f.check(self.evidence(age),self.now)['ok'])
        for age in [48.001,-.001]:self.assertFalse(f.check(self.evidence(age),self.now)['ok'])
        for value in [None,'2026-10-29T10:00:00','bad']:
            self.assertFalse(f.check(dict(self.evidence(),original_published_at=value),self.now)['ok'])
    def test_timezones_and_stricter_alert_window(self):
        e=dict(self.evidence(),original_published_at='2026-10-29T18:00:00+08:00')
        self.assertTrue(f.check(e,self.now)['ok']);self.assertFalse(f.check(self.evidence(7),self.now,6)['ok'])
        day=dict(self.evidence(),original_published_at='2026-10-28',precision='date',source_timezone='America/Los_Angeles')
        self.assertTrue(f.check(day,self.now)['ok'])
    def test_date_precision_conservative_and_updated_not_original(self):
        e=dict(self.evidence(),original_published_at='2026-10-28',precision='date',source_timezone='Asia/Shanghai')
        self.assertTrue(f.check(e,self.now)['ok'])
        for day in ['2026-10-27','2026-10-29']:self.assertFalse(f.check(dict(e,original_published_at=day),self.now)['ok'])
        self.assertFalse(f.check(dict(e,source_timezone=None),self.now)['ok'])
        self.assertFalse(f.check(dict(self.evidence(),time_basis='rss_updated'),self.now)['ok'])
    def test_atom_updated_does_not_resurrect_old_news(self):
        atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Test</title><link href="https://example.org/a"/><updated>2026-10-29T00:00:00Z</updated></entry></feed>'
        self.assertIsNone(n.parse_feed(atom,{})[0]['published'])
    def root(self,path):
        root=Path(path);n.dump(root/'config.json',dict(freshness=dict(enabled=True),publisher=dict(enabled=True,auto_submit=True)))
        return root
    def episode(self):return dict(id='new',edition_slot='night',scenes=[dict(id='news',item_id='post',published=self.now.isoformat())])
    def test_manual_timestamp_cannot_override_archive_and_bind_keeps_precision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.root(tmp);ep=self.episode();n.dump(root/'data/time-evidence/post.json',self.evidence(49))
            with self.assertRaisesRegex(ValueError,'FRESHNESS'):f.audit_episode(ep,root,self.now,True)
            n.dump(root/'data/time-evidence/post.json',self.evidence(1));f.audit_episode(ep,root,self.now,True)
            self.assertEqual(ep['scenes'][0]['published'],self.evidence(1)['original_published_at'])
    def test_recap_and_temporary_keep_shorter_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.root(tmp);ep=self.episode();n.dump(root/'data/time-evidence/post.json',self.evidence(25))
            ep['scenes'][0]['editorial_role']='recap'
            with self.assertRaises(ValueError):f.audit_episode(ep,root,self.now)
            ep=self.episode();ep.update(edition_slot='temporary',alert_id='reset')
            n.dump(root/'data/time-evidence/post.json',self.evidence(7))
            with self.assertRaises(ValueError):f.audit_episode(ep,root,self.now)
    def test_first_submit_blocked_but_unknown_and_submitted_never_reupload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.root(Path(tmp)/'News_Video');directory=Path(tmp)/'release/test';ep=self.episode()
            n.dump(root/'data/time-evidence/post.json',self.evidence(49));n.dump(directory/'episode.json',ep)
            n.dump(directory/'publication.json',dict(auto_publish=True));n.dump(directory/'release.json',dict(state='ready_for_upload'))
            with patch.object(u,'call') as browser:
                self.assertEqual(u.publish_ready(directory,root)['error']['code'],'FRESHNESS_BLOCKED');browser.assert_not_called()
                for state in ['unknown','submitted','published']:
                    n.dump(directory/'release.json',dict(state=state));u.publish_ready(directory,root)
                browser.assert_not_called()
    def test_pagination_uses_saved_reference_and_rejects_widening(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(n,'ROOT',Path(tmp)),patch('builtins.print') as output:
            n.dump(Path(tmp)/'data/candidates.json',dict(hours=48,generated_at=self.now.isoformat(),items=[dict(id='a'),dict(id='b')],game_coverage={}))
            n.candidates(48,True,1,1);self.assertEqual(json.loads(output.call_args.args[0])['reference_time'],self.now.isoformat())
            with self.assertRaises(ValueError):n.candidates(72)
    def test_overview_subject_and_action_gate(self):
        scene=dict(id='api',company='OpenAI',title='API额度上调',narration='OpenAI宣布提高API使用限额。')
        ep=dict(overview_subject_policy=1,scenes=[scene]);prepare_overview(ep)
        self.assertEqual(ep['scenes'][0]['facts'][0]['title'],'OpenAI｜API额度上调')
        self.assertIn('OpenAI',ep['scenes'][1]['short_title'])
        ep['scenes'][0]['facts'][0]['title']='API额度'
        with self.assertRaises(ValueError):validate_overview(ep)
        for bad in [dict(id='a',title='新增内容',narration='今日发布。'),dict(id='b',company='OpenAI',title='API额度')]:
            with self.assertRaises(ValueError):prepare_overview(dict(overview_subject_policy=1,scenes=[bad]))
    def test_game_region_and_product_not_company_invented(self):
        ep=dict(overview_subject_policy=1,scenes=[dict(id='a',game='arknights',game_region='global',title='新增干员展示',narration='明日方舟发布干员展示。'),dict(id='b',title='额度重置公告',product='Codex',company='OpenAI',narration='Codex额度将重置。')]);prepare_overview(ep)
        facts=ep['scenes'][0]['facts'];self.assertIn('明日方舟英文国际服',facts[0]['title']);self.assertIn('Codex',facts[1]['title'])
    def test_import_old_game_cannot_bypass_candidates(self):
        from test_story_order import game,episode
        with tempfile.TemporaryDirectory() as tmp:
            root=self.root(tmp);cfg=n.load(root/'config.json');cfg.update(editorial=dict(include_important_recaps=False),publication_preset={});n.dump(root/'config.json',cfg)
            old=(dt.datetime.now(f.UTC)-dt.timedelta(hours=49)).isoformat()
            s=game(published=old,source_url='https://example.org/game',evidence=['Original'],selection_reason='test')
            n.dump(root/'data/game-items/game.json',dict(s,url=s['source_url']))
            n.dump(root/'input.json',episode([s],id='old-import',producer='Codex current conversation'))
            with patch.object(n,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'FRESHNESS'):n.import_editorial(root/'input.json')
            self.assertFalse((root/'episodes/old-import').exists())
    def test_skland_article_never_implicitly_opens_browser(self):
        import skland_sources
        with tempfile.TemporaryDirectory() as tmp,patch.object(n,'ROOT',Path(tmp)),patch.object(skland_sources,'BrowserReader') as browser:
            root=Path(tmp);n.dump(root/'config.json',dict(game_news=dict(skland_mode='non_browser_only')))
            db=n.database();db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',('cached','skland-arknights','Official','games','title','https://www.skland.com/article?id=1',self.now.isoformat(),'','','',''));db.commit();db.close()
            n.dump(root/'data/game-items/cached.json',dict(source_type='skland_browser'))
            with self.assertRaisesRegex(ValueError,'SOURCE_GAP'):n.article('cached')
            n.dump(root/'data/articles/cached.json',dict(body_complete=True,title='title',published=self.now.isoformat(),text='Official original'))
            with patch('builtins.print'):n.article('cached',True)
            browser.assert_not_called()

if __name__=='__main__':unittest.main()
