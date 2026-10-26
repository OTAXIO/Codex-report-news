"""Exercise preparation and archived lookup with code nested inside the repo."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from project_paths import release_root,workspace_root
from release_manager import prepare
from episode_paths import episode_directory
from uploader_plan import plan
import upload_bridge


class ProjectLayoutChecks(unittest.TestCase):
    def test_nested_checkout_uses_external_release_for_prepare_plan_and_archive(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            work=Path(folder);root=work/'Codex-report-news/News_Video'
            source=root/'episodes/fixture';source.mkdir(parents=True)
            def write(path,value):path.write_text(json.dumps(value),encoding='utf-8')
            write(root/'config.json',dict(workspace_directory='../..',release=dict(directory='../../release')))
            ep=dict(id='fixture',edition_date='2026-10-27',edition_slot='morning',scenes=[dict(id='intro')])
            for name,value in [('episode.json',ep),('publication.json',dict(title='Migration fixture',tags=['AI'])),
                               ('check.json',dict(ok=True)),('timings.json',dict(duration=3)),
                               ('progress-validation.json',[dict(item='intro')])]:write(source/name,value)
            for name in ['sample.mp4','cover-4x3.png','cover-16x9.png','script.txt']:(source/name).write_bytes(b'offline fixture')
            result=prepare('fixture',root=root);directory=Path(result['directory'])
            self.assertEqual(directory,work/'release/2026_10_27_morning')
            self.assertEqual(workspace_root(root),work)
            self.assertFalse((work/'Codex-report-news/release').exists())
            self.assertFalse(plan(directory,root)['submitted'])
            write(source/'release.json',dict(relative_directory=result['relative_directory'],published=True))
            self.assertEqual(episode_directory(root,'fixture'),directory)
            with self.assertRaises(ValueError):plan(root.parent/'release/invalid',root)

    def test_moved_upload_bridge_keeps_private_home_outside_repository(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            work=Path(folder);root=work/'Codex-report-news/News_Video';root.mkdir(parents=True)
            (root/'config.json').write_text(json.dumps(dict(workspace_directory='../..',
                publisher=dict(private_home='../../.codex-upload-private'),release=dict(directory='../../release'))),encoding='utf-8')
            cli,home=upload_bridge.paths(root)
            self.assertEqual(home,work/'.codex-upload-private')
            self.assertEqual(cli,root/'skills/codex-upload/scripts/codex_upload.py')
            self.assertEqual(release_root(root),work/'release')
            with patch.object(upload_bridge,'call') as call:
                result=upload_bridge.pending(root)
                self.assertEqual(result,[]);call.assert_not_called()

if __name__=='__main__':unittest.main()
