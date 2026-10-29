import copy,json,tempfile,unittest
from pathlib import Path
from PIL import Image
import scene_media as m

class PageImageChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.save('config.json',dict(presentation=dict(require_image_every_page=True)))
        assets=[]
        for key in ['openai','arknights','endfield']:
            path=self.root/'assets/logos'/(key+'.png');path.parent.mkdir(parents=True,exist_ok=True);Image.new('RGB',(64,64),'blue').save(path)
            assets.append(dict(id=key,path=path.relative_to(self.root).as_posix(),sha256=m.digest(path),source='https://official.example/'+key))
        self.save('assets/logos/sources.json',dict(assets=assets))
    def save(self,path,value):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value),encoding='utf-8')
    def test_news_picture_precedes_identity_and_each_page_is_audited(self):
        pic=self.root/'assets/news.png';Image.new('RGB',(128,64),'white').save(pic)
        ep=dict(scenes=[dict(id='overview',scene_type='overview'),dict(id='a',game='arknights',image='assets/news.png',image_source_url='https://official.example/poster'),dict(id='b',company='OpenAI')])
        audit=m.prepare(ep,self.root);self.assertEqual(len(audit['pages']),3)
        self.assertEqual(ep['scenes'][0]['resolved_media']['subject'],'arknights')
        self.assertEqual(ep['scenes'][1]['resolved_media']['kind'],'news_image')
        self.assertEqual(ep['scenes'][2]['resolved_media']['subject'],'openai')
        self.assertTrue(m.validate(ep,self.root)['ok'])
    def test_missing_or_corrupt_news_picture_uses_related_game_icon(self):
        for value in ['assets/missing.png','assets/broken.png']:
            (self.root/'assets/broken.png').write_text('not a PNG')
            ep=dict(scenes=[dict(id='news',game='endfield',image=value)])
            m.prepare(ep,self.root);self.assertEqual(ep['scenes'][0]['resolved_media']['subject'],'endfield')
    def test_no_unrelated_company_fallback_or_generic_placeholder(self):
        ep=dict(scenes=[dict(id='new',company='Unknown Company',title='Comparison with OpenAI')])
        with self.assertRaisesRegex(ValueError,'no verified related'):m.prepare(ep,self.root)
    def test_identity_cannot_escape_assets_or_silently_change(self):
        ep=dict(scenes=[dict(id='a',company='OpenAI')]);m.prepare(ep,self.root)
        Image.new('RGB',(64,64),'red').save(self.root/'assets/logos/openai.png')
        with self.assertRaisesRegex(ValueError,'asset changed'):m.validate(ep,self.root)
        with self.assertRaisesRegex(ValueError,'assets/'):m.image_info(self.root,'../other.png')
    def test_every_reset_page_gets_company_identity_without_truncation(self):
        ep=dict(scenes=[dict(id='p'+str(i),source_type='leader_x',author_handle='thsottiaux',original_text_page='full text '+str(i)) for i in range(3)])
        before=[s['original_text_page'] for s in ep['scenes']];m.prepare(ep,self.root)
        self.assertEqual([s['original_text_page'] for s in ep['scenes']],before)
        self.assertTrue(all(s['resolved_media']['subject']=='openai' for s in ep['scenes']))
    def test_broken_or_unattributed_explicit_logo_is_not_accepted(self):
        Image.new('RGB',(32,32)).save(self.root/'assets/unknown.png')
        ep=dict(scenes=[dict(id='a',company='Unknown',logo='assets/unknown.png')])
        with self.assertRaises(ValueError):m.prepare(ep,self.root)
    def test_page_removing_media_is_rejected_but_frozen_old_episode_is_untouched(self):
        ep=dict(scenes=[dict(id='a',company='OpenAI')]);m.prepare(ep,self.root);ep['scenes'][0].pop('resolved_media')
        with self.assertRaises(ValueError):m.validate(ep,self.root)
        self.assertIsNone(m.validate(dict(scenes=[dict(id='old')]),self.root))
    def test_copying_other_game_identity_to_page_is_rejected(self):
        ep=dict(scenes=[dict(id='ark',game='arknights'),dict(id='end',game='endfield')]);m.prepare(ep,self.root)
        ep['scenes'][0]['resolved_media']=ep['scenes'][1]['resolved_media']
        with self.assertRaisesRegex(ValueError,'subject'):m.validate(ep,self.root)
    def test_tall_news_poster_uses_portrait_layout_but_square_icon_does_not(self):
        Image.new('RGB',(100,210),'white').save(self.root/'assets/poster.png')
        ep=dict(scenes=[dict(id='poster',game='arknights',image='assets/poster.png',image_source_url='https://official.example/poster'),dict(id='icon',game='endfield')])
        m.prepare(ep,self.root)
        self.assertEqual([s['resolved_media']['layout'] for s in ep['scenes']],['portrait','landscape'])

if __name__=='__main__':unittest.main()
