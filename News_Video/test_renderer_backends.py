import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import renderer_backends as r

class RenderSelectionChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.episode=self.root/'episodes/test';self.episode.mkdir(parents=True)
        (self.episode/'narration.wav').write_bytes(b'fixture')
        (self.root/'renderers').mkdir();(self.root/'renderers/audit-shot.mjs').write_text('// fixture')
        r.save(self.root/'config.json',dict(rendering=dict(default_backend='multiplane',node_executable='node',multiplane=dict(workers=2))))
        for name,version in [('multiplane','0.3.13'),('hyperframes','0.8.196')]:r.save(self.root/'node_modules'/name/'package.json',dict(version=version))
    def test_new_default_and_style_are_pinned_despite_later_config_changes(self):
        first=r.select_plan(self.root,self.episode)
        self.assertEqual((first['backend'],first['template']),('multiplane','editorial'))
        cfg=r.load(self.root/'config.json');cfg['rendering']['default_backend']='hyperframes';r.save(self.root/'config.json',cfg)
        self.assertEqual(r.select_plan(self.root,self.episode),first)
        with self.assertRaisesRegex(ValueError,'pinned'):r.select_plan(self.root,self.episode,template='graphic')
    def test_old_in_progress_episode_stays_hyperframes(self):
        r.save(self.episode/'scene-timings.json',[])
        self.assertEqual(r.select_plan(self.root,self.episode)['backend'],'hyperframes')
    def test_legacy_cover_does_not_change_multiplane_video_plan(self):
        import cover_generator as cover
        plan=r.select_plan(self.root,self.episode,'multiplane','graphic')
        cfg=r.load(self.root/'config.json');cfg['cover_generation']={'backend':'hyperframes'};r.save(self.root/'config.json',cfg)
        with patch.object(cover,'ROOT',self.root),patch.object(cover,'make_hyperframes') as legacy,patch.object(r,'select_plan',side_effect=AssertionError('Cover must not select video renderer')):
            cover.make('test');legacy.assert_called_once_with('test')
        self.assertEqual(r.load(self.episode/'render-plan.json'),plan)
    def test_temporary_reset_and_model_editions_use_graphic_default(self):
        cfg=r.load(self.root/'config.json');cfg['rendering']['default_template']='graphic';r.save(self.root/'config.json',cfg)
        for alert_type in ['reset','model']:
            episode=self.root/'episodes'/alert_type;episode.mkdir()
            r.save(episode/'episode.json',dict(edition_slot='temporary',alert_type=alert_type))
            plan=r.select_plan(self.root,episode)
            self.assertEqual((plan['backend'],plan['template']),('multiplane','graphic'))
            self.assertEqual(r.load(episode/'render-plan.json'),plan)
    def test_explicit_old_engine_and_graphic_option(self):
        self.assertEqual(r.select_plan(self.root,self.episode,'hyperframes')['template'],'legacy')
        other=self.root/'episodes/graphic';other.mkdir()
        self.assertEqual(r.select_plan(self.root,other,'multiplane','graphic')['template'],'graphic')
    def test_archived_media_and_version_drift_are_not_rebuilt(self):
        r.select_plan(self.root,self.episode)
        r.save(self.root/'node_modules/multiplane/package.json',dict(version='99'))
        with self.assertRaisesRegex(ValueError,'version changed'):r.select_plan(self.root,self.episode)
        r.save(self.episode/'release.json',dict(published=True))
        with self.assertRaisesRegex(ValueError,'Archived'):r.select_plan(self.root,self.episode)
    def test_json_protocol_uses_final_result_not_progress_messages(self):
        p=SimpleNamespace(returncode=0,stdout='{"type":"progress","ok":false}\n{"type":"result","ok":true,"data":{}}\n',stderr='')
        with patch.object(r.subprocess,'run',return_value=p):self.assertTrue(r.run_multiplane(self.root,'doctor')['ok'])
        p.stdout='{"type":"progress","ok":true}\n'
        with patch.object(r.subprocess,'run',return_value=p),self.assertRaisesRegex(RuntimeError,'missing_result'):r.run_multiplane(self.root,'doctor')
    def test_interrupted_job_is_not_silently_restarted(self):
        plan=r.select_plan(self.root,self.episode)
        r.save(self.episode/'timings.json',dict(duration=2));r.save(self.episode/'render-job.json',dict(ok=False,job_id='interrupted'))
        with self.assertRaisesRegex(ValueError,'resume-render'):r.render_multiplane(self.root,self.episode,plan)
    def test_preview_cannot_enter_export_even_via_resume(self):
        import render_sample as render
        r.save(self.episode/'episode.json',dict(usage_tracking=False,review_status='local_sample_renderer'))
        with patch.object(render,'ROOT',self.root),self.assertRaisesRegex(ValueError,'never enter'):render.complete_export('test')

if __name__=='__main__':unittest.main()
