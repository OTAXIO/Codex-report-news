import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import publication_policy as p
import production_policy


class PublicationChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.ep=dict(id='daily-test',edition_slot='night',edition_date='2026-10-30',lead_event_id='g',scenes=[
            dict(id='g',event_key='g',game='arknights',title='明日方舟塔露拉展示',narration='明日方舟展示新增干员塔露拉。',facts=[]),
            dict(id='a',event_key='a',title='OpenAI公布API额度',narration='OpenAI公布API额度。',facts=[])])
        self.pub=dict(lead_event_id='g',title_groups=[dict(kind='games',event_ids=['g']),dict(kind='ai',event_ids=['a'])])
        self.pub['title']=self.ep['title']=p.title_for(self.ep,self.pub)
        self.cover=dict(lead_event_id='g',headline_top='明日方舟',headline_main='塔露拉',highlight='展示')
        for name in ['cover-16x9.png','cover-4x3.png','cover-bilibili.jpg']:(self.root/name).write_bytes(b'reviewed-pixels')
        self.save();p.seal(self.root)

    def save(self):
        for name,value in [('episode.json',self.ep),('publication.json',self.pub),('cover.json',self.cover)]:
            (self.root/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')

    def test_grouped_final_title_and_valid_seal(self):
        self.assertEqual(self.pub['title'],'游戏：明日方舟塔露拉展示｜AI：OpenAI公布API额度｜10月30日晚报')
        p.validate(self.root)

    def test_removed_story_cannot_remain_in_title_even_after_reordering(self):
        self.ep['scenes'].pop();self.save()
        with self.assertRaisesRegex(ValueError,'TITLE_EVENT_REMOVED'):p.validate(self.root)

    def test_free_text_stale_title_rejected(self):
        self.pub['title']='塔露拉｜终末地寻访与API额度';self.save()
        with self.assertRaisesRegex(ValueError,'TITLE_CONTENT_MISMATCH'):p.validate(self.root)

    def test_mixed_category_group_rejected(self):
        self.pub['title_groups']=[dict(kind='games',event_ids=['g','a'])];self.save()
        with self.assertRaisesRegex(ValueError,'TITLE_CATEGORY_MIXED'):p.validate(self.root)

    def test_unrelated_cover_claim_rejected(self):
        self.cover['highlight']='终末地寻访';self.save()
        with self.assertRaisesRegex(ValueError,'COVER_CLAIM_NOT_IN_LEAD'):p.validate(self.root)

    def test_content_edit_and_cover_pixels_invalidate_review(self):
        self.ep['scenes'][0]['narration']+='修改后的内容。';self.save()
        with self.assertRaisesRegex(ValueError,'PUBLICATION_REVIEW_STALE'):p.validate(self.root)
        p.seal(self.root);(self.root/'cover-4x3.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'PUBLICATION_REVIEW_STALE'):p.validate(self.root)

    def test_upload_stops_before_uploader_call(self):
        import upload_bridge
        self.ep['scenes'].pop();self.save()
        with patch.object(upload_bridge,'settings',return_value={'enabled':True}),patch.object(upload_bridge,'call') as call:
            with self.assertRaisesRegex(ValueError,'TITLE_EVENT_REMOVED'):upload_bridge.prepare(self.root)
            call.assert_not_called()

    def test_published_episode_cannot_be_resealed(self):
        (self.root/'release.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'released'):p.seal(self.root)


if __name__=='__main__':unittest.main()
