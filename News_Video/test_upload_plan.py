import json,tempfile,unittest
from pathlib import Path
from uploader_plan import plan

class UploadPlanChecks(unittest.TestCase):
    def test_only_release_and_never_repeat_published(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder)/'News_Video';root.mkdir();release=root.parent/'release'/'2026_10_26_night';release.mkdir(parents=True)
            receipt={'published':False,'video_filename':'2026_10_26_night_晚间新闻.mp4'}
            (release/'release.json').write_text(json.dumps(receipt),encoding='utf-8')
            (release/'publication.json').write_text(json.dumps({'title':'真实新闻','tags':['AI','OpenAI'],'description':'来源'}),encoding='utf-8')
            for name in [receipt['video_filename'],'cover-4x3.png','cover-16x9.png']:(release/name).write_bytes(b'fixture')
            from release_manager import digest
            receipt['archive_files']=[dict(file=receipt['video_filename'],sha256=digest(release/receipt['video_filename']))]
            (release/'release.json').write_text(json.dumps(receipt),encoding='utf-8')
            result=plan(release,root);self.assertFalse(result['submitted']);self.assertTrue((release/'upload.web-skill.json').is_file())
            meta=json.loads((release/'upload.web-skill.json').read_text(encoding='utf-8'));self.assertTrue(meta['video'].startswith(str(root.parent/'release')));self.assertNotIn('subtitles',meta)
            receipt['published']=True;(release/'release.json').write_text(json.dumps(receipt),encoding='utf-8')
            with self.assertRaises(ValueError):plan(release,root)
            with self.assertRaises(ValueError):plan(root,root)

if __name__=='__main__':unittest.main()
