import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import upload_bridge as b

class UploadBridgeChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.work=Path(self.tmp.name);self.root=self.work/'News_Video';self.root.mkdir()
        b.save(self.root/'config.json',dict(publisher=dict(enabled=True,auto_submit=True)))
        self.release=self.work/'release/edition';self.release.mkdir(parents=True)
        b.save(self.release/'release.json',dict(state='ready_for_upload',published=False,episode_id='edition'))
        b.save(self.release/'publication.json',dict(title='Verified title',auto_publish=True))
        b.save(self.release/'episode.json',dict(id='edition',edition_slot='night'))
        b.save(self.release/'upload.codex.json',dict(schema_version=1))
    def tearDown(self):self.tmp.cleanup()
    def test_submitted_is_not_published_and_does_not_submit_twice(self):
        with patch.object(b,'call',return_value=dict(ok=True,state='submitted',key='a'*64,receipt=dict(aid=123,bvid='BV1aaaaaaaaa'))) as call:
            result=b.publish_ready(self.release,self.root);self.assertEqual(result['state'],'submitted')
            receipt=b.load(self.release/'release.json');self.assertTrue(receipt['submitted']);self.assertFalse(receipt['published'])
            again=b.publish_ready(self.release,self.root);self.assertIn('skipped',again);self.assertEqual(call.call_count,1)
    def test_per_release_manual_opt_out_and_unknown_do_not_upload(self):
        with patch.object(b,'call') as call:
            b.save(self.release/'publication.json',dict(title='Verified title',auto_publish=False))
            self.assertIn('skipped',b.publish_ready(self.release,self.root));call.assert_not_called()
            b.save(self.release/'release.json',dict(state='unknown',published=False))
            self.assertEqual(b.publish_ready(self.release,self.root)['error']['code'],'RECONCILE_REQUIRED');call.assert_not_called()
    def test_wrong_platform_title_cannot_trigger_cleanup_or_publication(self):
        b.save(self.release/'release.json',dict(state='submitted',published=False,platform=dict(bvid='BV1aaaaaaaaa')))
        with patch.object(b,'call',return_value=dict(ok=True,state='published',receipt=dict(title='Wrong title',aid=123))):
            self.assertEqual(b.verify_release(self.release,self.root)['error']['code'],'PLATFORM_TITLE_MISMATCH')
            self.assertFalse(b.load(self.release/'release.json')['published'])

if __name__=='__main__':unittest.main()
