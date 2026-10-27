import datetime as dt,unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import important_events as i
class MainRecapChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'config.json').write_text(json.dumps(dict(workspace_directory='.')))
        p=patch.object(i.n,'ROOT',self.root);p.start();self.addCleanup(p.stop)
        self.day=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
    def exported(self,slot='morning',news=None):
        folder=self.root/'logs/news-used';folder.mkdir(parents=True,exist_ok=True)
        with (folder/(self.day+'.jsonl')).open('a') as f:f.write(json.dumps(dict(event='edition_exported',edition_date=self.day,edition_slot=slot,episode_id='daily-'+self.day+'-'+slot,news=news or []))+'\n')
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
    def test_same_event_regular_story_is_not_duplicated_as_recap(self):
        ep=dict(edition_slot='noon',scenes=[dict(id='new-report',item_id='collected',event_key='different-normalized-key')])
        with patch.object(i,'entries',return_value=[self.event()]):i.prepare_main_recaps(ep,self.root)
        self.assertEqual(len(ep['scenes']),1)
    def test_morning_event_does_not_repeat_in_noon_or_night(self):
        self.exported(news=[dict(event_key='old-event',item_id='collected')])
        with patch.object(i,'entries',return_value=[self.event()]):
            for slot in ['noon','night']:
                ep=dict(edition_date=self.day,edition_slot=slot,scenes=[dict(id='stale-recap',editorial_role='recap',item_id='collected',event_key='event'),dict(id='new-story')])
                i.prepare_main_recaps(ep,self.root)
                self.assertEqual([s['id'] for s in ep['scenes']],['new-story'])
                self.assertEqual(ep['recap_policy']['skipped_event_keys'],['event'])
                event=self.event();scene=dict(event['scene'],event_key='event',recap_of=event['url'])
                with self.assertRaisesRegex(ValueError,'already appeared'):i.validate_recap(scene,ep,self.root)
    def test_morning_temporary_can_recap_at_noon_but_not_again_at_night(self):
        self.exported('morning')  # An unrelated morning edition is not a global ban.
        self.exported('temporary',[dict(event_key='event',item_id='collected')])
        ep=dict(edition_date=self.day,edition_slot='noon',scenes=[])
        with patch.object(i,'entries',return_value=[self.event()]):
            i.prepare_main_recaps(ep,self.root);self.assertEqual(len(ep['scenes']),1)
        self.exported('noon',[dict(event_key='event',item_id='collected')])
        self.assertTrue(i.recap_allowed_for_event(self.event(),ep,self.root))
        self.assertFalse(i.recap_allowed_for_event(self.event(),dict(edition_date=self.day,edition_slot='night'),self.root))
        self.exported('night')
        self.assertTrue(i.recap_allowed_for_event(self.event(),ep,self.root))
        tomorrow=(dt.date.fromisoformat(self.day)+dt.timedelta(days=1)).isoformat()
        self.assertTrue(i.recap_allowed_for_event(self.event(),dict(edition_date=tomorrow,edition_slot='morning'),self.root))
    def test_afternoon_new_event_is_eligible_for_night_while_noon_event_is_not(self):
        self.exported('noon',[dict(event_key='event',item_id='collected')])
        a=self.event();b=self.event();b.update(event_key='new-afternoon',original_event_key='new-original',episode_id='afternoon')
        b['scene']=dict(b['scene'],item_id='afternoon-item')
        ep=dict(edition_date=self.day,edition_slot='night',scenes=[])
        with patch.object(i,'entries',return_value=[a,b]):i.prepare_main_recaps(ep,self.root)
        self.assertEqual([s['item_id'] for s in ep['scenes']],['afternoon-item'])
    def test_release_receipt_blocks_repeat_when_ledger_is_missing(self):
        folder=self.root/'release'/(self.day+'_morning');folder.mkdir(parents=True)
        (folder/'video.mp4').write_bytes(b'export fixture')
        (folder/'release.json').write_text(json.dumps(dict(edition_date=self.day,edition_slot='morning',video_filename='video.mp4')))
        (folder/'episode.json').write_text(json.dumps(dict(scenes=[dict(item_id='collected')])) )
        self.assertFalse(i.recap_allowed_for_event(self.event(),dict(edition_date=self.day,edition_slot='noon'),self.root))
