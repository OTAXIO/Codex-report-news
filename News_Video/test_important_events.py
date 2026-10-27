import datetime as dt,unittest
from unittest.mock import patch
import important_events as i
class MainRecapChecks(unittest.TestCase):
    def event(self,age=1):
        published=(dt.datetime.now(i.n.UTC)-dt.timedelta(hours=age)).isoformat()
        scene=dict(id='release',item_id='collected',published=published,section='临时新闻',title='模型发布',short_title='模型',narration='OpenAI 发布模型。')
        return dict(event_key='event',original_event_key='old-event',kind='model_release',url='https://www.bilibili.com/video/BVfixture',published=published,episode_id='temporary-fixture',scene=scene)
    def test_recap_preserves_time_and_precedes_social(self):
        ep=dict(edition_slot='noon',scenes=[dict(id='soc',section='国内新闻',title='社会')])
        with patch.object(i,'entries',return_value=[self.event()]):
            i.prepare_main_recaps(ep);self.assertEqual(ep['scenes'][0]['section'],'AI 动态');i.validate_recap(ep['scenes'][0],ep);i.prepare_main_recaps(ep);self.assertEqual(len(ep['scenes']),2)
    def test_stale_or_unpublished_recaps_not_accepted(self):
        with patch.object(i,'entries',return_value=[self.event(25)]):self.assertEqual(i.recap_candidates(),[])
        with patch.object(i,'entries',return_value=[]),self.assertRaises(ValueError):i.validate_recap(dict(event_key='fake',recap_of='fake'),dict(edition_slot='night'))
