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
        ep=dict(edition_slot='night',scenes=scenes);prepare_overview(ep);guides=[s for s in ep['scenes'] if s.get('scene_type')=='overview']
        facts=[f for g in guides for f in g['facts']]
        # 2026-11-28: seven stories no longer get cut to four; they continue on a second overview page (4+3).
        self.assertEqual([len(g['facts']) for g in guides],[4,3]);self.assertEqual(guides[0]['total_stories'],7)
        self.assertEqual([f['scene_id'] for f in facts],['a0','a1','a2','a3','a4','domestic','world'])
        self.assertTrue(all(f['detail'] for f in facts))
        self.assertNotIn('接下来',facts[5]['detail']);self.assertIn('研究人员',facts[5]['detail'])
        self.assertEqual(folio_numbers(ep['scenes'])[:3],[0,0,1])
    def test_legacy_label_only_guide_is_upgraded_before_voice(self):
        ep=dict(scenes=[dict(id='guide',scene_type='overview',facts=[dict(title='新版本',detail='')],narration='这是本视频的导览。'),dict(id='story',title='WorkBuddy 新增办公功能',narration='WorkBuddy 新增了办公功能。')])
        prepare_overview(ep);self.assertEqual(ep['scenes'][0]['id'],'guide');self.assertEqual(len(ep['scenes']),2)
        self.assertIn('WorkBuddy',ep['scenes'][0]['facts'][0]['title']);self.assertEqual(ep['scenes'][0]['overview_schema_version'],3)
    def test_social_only_does_not_invent_ai_section(self):
        ep=dict(scenes=[dict(id='domestic',section='国内新闻',title='研究人员发现化石',narration='研究人员发现了化石。')]);prepare_overview(ep)
        self.assertNotIn('AI',ep['scenes'][0]['lead']);self.assertEqual(len(ep['scenes'][0]['facts']),1)
    def test_series_overview_allows_rich_hook_and_diverse_segment_cards(self):
        scenes=[
            dict(id='lead',game='arknights',game_region='cn',section='游戏资讯',segment='official',title='雪山复刻开启',narration='雪山复刻今日开启，白拿六星溯光星源。'),
            dict(id='act1',game='arknights',game_region='cn',section='游戏资讯',segment='activities',scene_type='activity',title='网页领奖还剩两天',narration='冻土与火种网页活动还剩两天。'),
            dict(id='cal1',game='arknights',game_region='cn',section='游戏资讯',segment='activities',scene_type='activity_calendar',title='活动日历（一）',narration='近期活动截止时间如下。'),
            dict(id='cal2',game='arknights',game_region='cn',section='游戏资讯',segment='activities',scene_type='activity_calendar',title='活动日历（二）',narration='其余版本活动如下。'),
            dict(id='talk',game='arknights',game_region='cn',section='游戏资讯',segment='community',scene_type='community_pulse',title='玩家怎么看凯尔希',narration='玩家认为M3新形象很像凯尔希。'),
        ]
        hook='雪山复刻今日开启，完成任务白拿六星溯光星源！冻土与火种网页领奖还剩最后两天，文末还有双页全活动DDL日历与玩家热议。'
        ep=dict(edition_slot='night',edition_series='arknights',hook=hook,scenes=scenes)
        prepare_overview(ep,True);guide=ep['scenes'][0]
        self.assertEqual(guide['title'],'明日方舟｜今日情报与活动DDL')
        self.assertEqual(guide['narration'],hook)
        self.assertEqual([f['scene_id'] for f in guide['facts']],['lead','act1','cal1','talk'])
        self.assertEqual([f['category'] for f in guide['facts']],['重磅头条','重点活动','全活动DDL','玩家热议'])
    def test_overview_prioritizes_cn_cards_and_labels_global(self):
        cn=[
            dict(id='c1',game='arknights',game_region='cn',section='游戏资讯',segment='official',title='国服新版本',narration='国服新版本上线。'),
            dict(id='c2',game='arknights',game_region='cn',section='游戏资讯',segment='official',title='国服新干员',narration='国服公开新干员。'),
            dict(id='c3',game='arknights',game_region='cn',section='游戏资讯',segment='activities',scene_type='activity',title='国服活动',narration='国服活动进行中。'),
            dict(id='c4',game='arknights',game_region='cn',section='游戏资讯',segment='activities',scene_type='activity_calendar',title='活动日历',narration='活动日历汇总。'),
        ]
        en=dict(id='g1',game='arknights',game_region='global',section='游戏资讯',segment='official',title='国际服活动',narration='国际服推出活动。')
        ep=dict(edition_slot='night',edition_series='arknights',hook='国服新版本与新干员今天上线！',scenes=cn+[en])
        prepare_overview(ep,True)
        pages=[s for s in ep['scenes'] if s.get('scene_type')=='overview']
        self.assertEqual([[f['scene_id'] for f in g['facts']] for g in pages],[['c1','c2','c3'],['c4','g1']])
        self.assertEqual(pages[1]['facts'][1]['category'],'国际服动态')
        ep2=dict(edition_slot='night',edition_series='arknights',hook='国服新版本今天上线！',scenes=cn[:2]+[en])
        prepare_overview(ep2,True)
        self.assertEqual([f['scene_id'] for f in ep2['scenes'][0]['facts']],['c1','c2','g1'])
        self.assertEqual(ep2['scenes'][0]['facts'][2]['category'],'国际服动态')
    def test_overview_continues_on_more_pages_and_is_idempotent(self):
        scenes=[dict(id=f's{i}',section='AI 动态',title=f'OpenAI 更新产品{i}',short_title=f'OpenAI 产品{i}',narration='OpenAI 宣布了一项产品更新。') for i in range(9)]
        ep=dict(edition_slot='morning',scenes=scenes);prepare_overview(ep);prepare_overview(ep)
        pages=[s for s in ep['scenes'] if s.get('scene_type')=='overview']
        self.assertEqual([len(p['facts']) for p in pages],[3,3,3]);self.assertEqual(len(ep['scenes']),12)
        self.assertEqual([p['id'] for p in pages],['overview','overview-2','overview-3'])
        self.assertEqual([p['overview_offset'] for p in pages],[0,3,6])
        self.assertEqual(pages[1]['short_title'],'导览（续）');self.assertTrue(pages[1]['title'].endswith('（续）'))
        self.assertEqual(pages[1]['narration'],'本期还有：OpenAI 产品3、OpenAI 产品4、OpenAI 产品5。')
        self.assertEqual(folio_numbers(ep['scenes']),[0,0,0]+list(range(1,10)))
    def test_paginate_balances_pages(self):
        from layout_policy import paginate
        self.assertEqual([len(p) for p in paginate(list(range(5)))],[3,2])
        self.assertEqual([len(p) for p in paginate(list(range(4)))],[4])
        self.assertEqual([len(p) for p in paginate(list(range(10)))],[4,3,3])
        self.assertEqual(paginate([]),[])
    def test_multi_page_calendar_is_one_overview_entry(self):
        cal=lambda i:dict(id=f'cal{i}',game='endfield',game_region='cn',section='游戏资讯',segment='activities',scene_type='activity_calendar',title=f'活动日历{i}',narration='活动如下。')
        ep=dict(edition_slot='night',scenes=[dict(id='lead',game='endfield',game_region='cn',section='游戏资讯',title='终末地新活动',narration='终末地新活动开启。'),cal(1),cal(2),cal(3)])
        prepare_overview(ep)
        self.assertEqual([f['scene_id'] for f in ep['scenes'][0]['facts']],['lead','cal1'])

if __name__=='__main__':unittest.main()
