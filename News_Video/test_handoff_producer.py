import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import news_video as n

class HandoffProducerChecks(unittest.TestCase):
    def test_dsh_producer_is_disclosed_without_impersonating_codex(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder);cfg=n.config()
            # This identity-only fixture has no news/assets. Image requirements
            # are exercised by actual reset imports and test_scene_media.
            cfg.setdefault('presentation',{})['require_image_every_page']=False
            (root/'config.json').write_text(json.dumps(cfg),encoding='utf-8')
            ep={'id':'dsh-fixture','producer':'DeepSeek Harness','scenes':[{'id':'intro','narration':'这是本视频的导览。'}]}
            incoming=root/'incoming.json';incoming.write_text(json.dumps(ep),encoding='utf-8')
            with patch.object(n,'ROOT',root):n.import_editorial(incoming)
            saved=json.loads((root/'episodes/dsh-fixture/episode.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['producer'],'DeepSeek Harness')

if __name__=='__main__':unittest.main()
