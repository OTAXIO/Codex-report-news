"""Single-audience series: one AI video each morning, one per game each evening."""
import unittest
import edition_series as es
import production_policy as p
from layout_policy import prepare_overview
from publication_policy import title_for
from release_manager import naming
from test_story_order import ai,game


def endfield(identity='ef',**kw):
    scene=game(identity,**kw);scene['game']='endfield';return scene


def series_episode(series,scenes,**kw):
    slot=es.SERIES[series]['slot']
    return dict(id=es.episode_id('2026-11-07',series),edition_date='2026-11-07',edition_slot=slot,edition_series=series,
                production_policy_version=4,scenes=scenes,hook='明日方舟公布了新版本更新内容。',**kw)


class EditionSeriesChecks(unittest.TestCase):
    def test_ids_and_release_names_separate_the_three_videos(self):
        self.assertEqual(es.episode_id('2026-11-07','ai'),'daily-20261107-morning')
        self.assertEqual(es.episode_id('2026-11-07','arknights'),'daily-20261107-night-arknights')
        self.assertEqual(naming('2026-11-07','morning',series='ai'),('2026_11_07_morning','2026_11_07_morning_AI早报.mp4'))
        self.assertEqual(naming('2026-11-07','night',series='endfield'),('2026_11_07_night_endfield','2026_11_07_night_endfield_终末地情报.mp4'))
        self.assertEqual(naming('2026-11-07','night')[1],'2026_11_07_night_晚间新闻.mp4')  # legacy unchanged
        with self.assertRaises(ValueError):naming('2026-11-07','morning',series='arknights')

    def test_game_video_has_one_module_no_announcement_and_series_title(self):
        ep=series_episode('arknights',[game('a'),game('b')])
        p.apply_story_order(ep);prepare_overview(ep,True);p.validate_content(ep)
        body=ep['scenes'][1:]
        self.assertEqual(ep['story_order']['default_order'],['games'])
        self.assertFalse(any(s['narration'].startswith(('先来看','接下来是')) for s in body))
        self.assertEqual(ep['scenes'][0]['narration'],'明日方舟公布了新版本更新内容。')
        title=title_for(ep,dict(title_groups=[dict(kind='games',event_ids=['a'])]))
        self.assertEqual(title,'a｜明日方舟情报 11.7')

    def test_stories_outside_the_series_are_rejected(self):
        ep=series_episode('endfield',[endfield(),game('ak')])
        p.apply_story_order(ep);prepare_overview(ep,True)
        with self.assertRaisesRegex(ValueError,'SERIES_SCENE_MISMATCH'):p.validate_content(ep)
        ep=series_episode('ai',[ai(),endfield()])
        with self.assertRaisesRegex(ValueError,'SERIES_SCENE_MISMATCH'):es.validate(ep)
        ep=series_episode('ai',[ai()]);ep['id']='daily-20261107-night'
        with self.assertRaisesRegex(ValueError,'SERIES_ID_MISMATCH'):es.validate(ep)

    def test_hook_is_required_for_series_videos(self):
        ep=series_episode('ai',[ai()]);ep.pop('hook')
        p.apply_story_order(ep)
        with self.assertRaisesRegex(ValueError,'HOOK_REQUIRED'):prepare_overview(ep,True)

    def test_candidate_filter_and_fixed_tags(self):
        rows=[dict(kind='ai'),dict(kind='games',game='arknights'),dict(kind='games',game='endfield')]
        self.assertEqual([r.get('game') for r in rows if es.accepts_candidate('endfield',r)],['endfield'])
        self.assertEqual(len([r for r in rows if es.accepts_candidate('ai',r)]),1)
        self.assertEqual(len([r for r in rows if es.accepts_candidate(None,r)]),3)
        self.assertEqual(p.tags(['终末地','新干员'],dict(edition_series='endfield'))[:3],['明日方舟终末地','终末地','新干员'])
        self.assertEqual(p.tags(['OpenAI'],dict(edition_series='ai')),['AI','OpenAI'])
        self.assertEqual(p.tags(['OpenAI'])[:2],['明日方舟','终末地'])  # legacy/temporary unchanged
        self.assertEqual(len(p.tags([str(i) for i in range(20)],dict(edition_series='endfield'))),9)


if __name__=='__main__':unittest.main()
