import json,tempfile,unittest
from pathlib import Path
from release_manager import naming,prepare,digest

class ReleaseWorkflowChecks(unittest.TestCase):
    def test_named_video_in_release_before_publication_and_repeat_safe(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder)/'News_Video';source=root/'episodes'/'edition';source.mkdir(parents=True)
            ep={'id':'edition','edition_date':'2026-10-26','edition_slot':'night','scenes':[{'id':'intro'}]}
            for name,value in [('episode.json',ep),('publication.json',{'title':'真实新闻标题','tags':['AI','OpenAI']}),('check.json',{'ok':True}),('timings.json',{'duration':3}),('progress-validation.json',[{'item':'intro'}])]:
                (source/name).write_text(json.dumps(value),encoding='utf-8')
            for name in ['sample.mp4','cover-4x3.png','cover-16x9.png','script.txt']:(source/name).write_bytes(b'local fixture')
            r=prepare('edition',root=root)
            self.assertFalse(r['published']);self.assertEqual(r['state'],'ready_for_upload')
            self.assertEqual(r['video_filename'],'2026_10_26_night_晚间新闻.mp4')
            self.assertEqual(digest(Path(r['directory'])/r['video_filename']),digest(source/'sample.mp4'))
            self.assertEqual(prepare('edition',root=root)['video_filename'],r['video_filename'])
            path=Path(r['directory'])/'release.json';r['published']=True;path.write_text(json.dumps(r),encoding='utf-8')
            with self.assertRaises(ValueError):prepare('edition',root=root)
    def test_names_and_slot_validation(self):
        self.assertEqual(naming('2026-10-26','morning')[0],'2026_10_26_morning')
        self.assertEqual(naming('2026-10-26','noon')[1],'2026_10_26_noon_午间新闻.mp4')
        with self.assertRaises(ValueError):naming('2026-10-26','../unsafe')

    def test_two_temporary_releases_do_not_use_a_main_slot(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder)/'News_Video'
            targets=[]
            for index in [1,2]:
                identity=f'{index:020x}';eid=f'reset-fixture-{index}';source=root/'episodes'/eid;source.mkdir(parents=True)
                ep=dict(id=eid,edition_date='2026-10-26',edition_slot='temporary',edition_type='temporary',edition_timestamp='2026-10-26T22:00:00+08:00',alert_id=identity,counts_toward_daily_main_limit=False,scenes=[dict(id='reset')])
                for name,value in [('episode.json',ep),('publication.json',dict(title='tibo 重置消息',tags=['AI'])),('check.json',dict(ok=True)),('timings.json',dict(duration=3)),('progress-validation.json',[dict(item='reset')])]:
                    (source/name).write_text(json.dumps(value),encoding='utf-8')
                for name in ['sample.mp4','cover-4x3.png','cover-16x9.png','script.txt']:(source/name).write_bytes(b'offline fixture')
                result=prepare(eid,root=root);targets.append(result['directory'])
                self.assertFalse(result['counts_toward_daily_main_limit']);self.assertTrue(result['video_filename'].endswith('_临时新闻.mp4'))
                self.assertEqual(result['edition_slot'],'temporary')
            self.assertNotEqual(targets[0],targets[1]);self.assertFalse((root.parent/'release/2026_10_26_night').exists())

if __name__=='__main__':unittest.main()
