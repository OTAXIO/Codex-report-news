import unittest
from progress_overlay import navigation_layout,build_progress

class BottomProgressChecks(unittest.TestCase):
    def test_both_engines_end_exactly_at_bottom_edge(self):
        for engine in ['multiplane','hyperframes']:
            spec=navigation_layout(engine);bar=spec['bar']
            self.assertEqual(bar['y']+bar['height'],1080)
            self.assertLess(spec['module_highlight_y'],spec['chapter_highlight_y'])
            self.assertLess(spec['chapter_highlight_y'],bar['y'])
    def test_legacy_markup_and_sampling_coordinates_move_together(self):
        ep=dict(scenes=[dict(id='a',section='AI 动态',title='OpenAI发布公告')])
        markup,spec=build_progress(ep,[dict(start=0,end=35)],35,'#01A1FE')
        self.assertIn('top:1072px',markup)
        self.assertIn('top:1040px',markup)
        self.assertEqual(spec['chapter_highlight_y'],1041)
        self.assertEqual(spec['chapters'][0]['id'],'a')
    def test_captions_follow_navigation_and_content_stays_above_them(self):
        for engine,old_y in [('multiplane',836),('hyperframes',844)]:
            spec=navigation_layout(engine);caption=spec['caption']
            self.assertEqual(caption['y']-old_y,spec['nav_offset_y'])
            self.assertEqual(spec['content_extra_y'],spec['nav_offset_y'])
            self.assertGreater(caption['y']-spec['reading_area_bottom'],10)
            self.assertLess(caption['y']+caption['height'],spec['module_highlight_y']-25)

if __name__=='__main__':unittest.main()
