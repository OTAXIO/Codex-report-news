import unittest
from layout_policy import prepare_overview,folio_numbers,cover_footer
class LayoutChecks(unittest.TestCase):
    def test_no_overview_starts_at_one(self):
        self.assertEqual(folio_numbers([dict(id='a'),dict(id='b')]),[1,2])
    def test_overview_zero_and_idempotent_insertion(self):
        ep=dict(edition_slot='night',scenes=[dict(id='a',title='OpenAI 发布新模型',short_title='模型',section='AI 动态',narration='OpenAI 发布了一款新模型。')]);prepare_overview(ep);prepare_overview(ep)
        self.assertEqual(folio_numbers(ep['scenes']),[0,1]);self.assertEqual(ep['scenes'][0]['narration'],'这是本视频的导览。');self.assertEqual(ep['scenes'][0]['hold_after_seconds'],2)
        self.assertEqual(ep['scenes'][0]['facts'][0]['title'],'OpenAI 发布新模型');self.assertIn('OpenAI',ep['scenes'][0]['facts'][0]['detail'])
        self.assertIn('本期我们',ep['scenes'][0]['lead'])
    def test_reset_skips_overview(self):
        ep=dict(alert_id='abc',scenes=[dict(id='reset',title='重置')]);prepare_overview(ep);self.assertEqual(folio_numbers(ep['scenes']),[1])
    def test_overview_not_allowed_in_middle(self):
        with self.assertRaises(ValueError):folio_numbers([dict(id='a'),dict(id='overview')])
    def test_clean_cover_footer_without_redundant_date(self):
        self.assertEqual(cover_footer(dict(footnote='10.27 模型发布速报')),'模型发布速报')
        self.assertEqual(cover_footer(dict(footnote='2026-10-27 模型发布速报')),'模型发布速报')

    def test_highlights_use_full_subject_and_actual_section_variety(self):
        scenes=[dict(id='a'+str(i),section='AI 动态',title='OpenAI 更新产品'+str(i),short_title='更新',narration='OpenAI 宣布了一项产品更新。') for i in range(5)]
        scenes.extend([dict(id='domestic',section='国内新闻',title='研究人员在贵州发现化石',narration='接下来是国内外重点新闻，先来看化石。研究人员在贵州发现了化石。'),dict(id='world',section='国际新闻',title='联合国发布气候报告',narration='联合国发布了一份气候报告。')])
        ep=dict(edition_slot='night',scenes=scenes);prepare_overview(ep);guide=ep['scenes'][0]
        self.assertEqual(len(guide['facts']),4);self.assertEqual(guide['total_stories'],7)
        self.assertEqual([f['scene_id'] for f in guide['facts']],['a0','a1','domestic','world'])
        self.assertTrue(all(f['detail'] for f in guide['facts']))
        self.assertNotIn('接下来',guide['facts'][2]['detail']);self.assertIn('研究人员',guide['facts'][2]['detail'])
    def test_legacy_label_only_guide_is_upgraded_before_voice(self):
        ep=dict(scenes=[dict(id='guide',scene_type='overview',facts=[dict(title='新版本',detail='')],narration='这是本视频的导览。'),dict(id='story',title='WorkBuddy 新增办公功能',narration='WorkBuddy 新增了办公功能。')])
        prepare_overview(ep);self.assertEqual(ep['scenes'][0]['id'],'guide');self.assertEqual(len(ep['scenes']),2)
        self.assertIn('WorkBuddy',ep['scenes'][0]['facts'][0]['title']);self.assertEqual(ep['scenes'][0]['overview_schema_version'],2)
    def test_social_only_does_not_invent_ai_section(self):
        ep=dict(scenes=[dict(id='domestic',section='国内新闻',title='研究人员发现化石',narration='研究人员发现了化石。')]);prepare_overview(ep)
        self.assertNotIn('AI',ep['scenes'][0]['lead']);self.assertEqual(len(ep['scenes'][0]['facts']),1)
