import tempfile,unittest
from pathlib import Path
import renderer_backends as r
from renderers import multiplane as m
from renderers.cornerstone_art import write_assets

class CornerstoneTemplate(unittest.TestCase):
    def test_template_is_selectable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'episodes/e').mkdir(parents=True);(root/'renderers').mkdir()
            r.save(root/'config.json',dict(rendering=dict(default_backend='multiplane',node_executable='node')))
            r.save(root/'node_modules/multiplane/package.json',dict(version='0.3.13'))
            plan=r.select_plan(root,root/'episodes/e','multiplane','cornerstone')
            self.assertEqual(plan['artifact_directory'],'episodes/e/visuals/multiplane-cornerstone')
    def test_ornament_assets_are_deterministic(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            names=write_assets(Path(a));self.assertEqual(names,write_assets(Path(b)))
            self.assertEqual(len(names),15)
            for n in names:self.assertEqual((Path(a)/n).read_bytes(),(Path(b)/n).read_bytes())
    def test_series_art_caption_is_the_series_name(self):
        art=dict(kind='game_identity',subject='endfield')
        self.assertEqual(m.brand_label(dict(game='endfield',company='endfield',resolved_media=art)),(True,'明日方舟：终末地'))
        self.assertEqual(m.brand_label(dict(game='arknights',resolved_media=dict(kind='game_identity')))[1],'明日方舟')
        series,label=m.brand_label(dict(company='OpenAI',resolved_media=dict(kind='company_logo')))
        self.assertEqual((series,label),(False,'OpenAI'));self.assertNotIn('图标',label)
    def test_reading_column_extras_only_show_scene_facts(self):
        s=dict(scene_type='news',game_region='cn',source_type='official_site',published='2026-11-26T02:00:00Z',evidence='第一句……第二句')
        out=m.cornerstone_extras(s)
        for part in ['国服','官方公告','11.26 10:00 发布','官方原文','第一句……第二句']:self.assertIn(part,out)
        self.assertEqual(m.cornerstone_extras(dict(scene_type='overview',evidence='x')),'')
        self.assertNotIn('evidence',m.cornerstone_extras(dict(source_type='leader_x',evidence='quote',published='2026-11-26T02:00:00Z')))
    def test_progress_mask_follows_template_blue(self):
        import verify_progress_video as v,inspect
        self.assertIn("spec.get('blue'",inspect.getsource(v.verify))
        self.assertEqual(m.TEMPLATE_BLUE['cornerstone'],'#2335E8')

if __name__=='__main__':unittest.main()
