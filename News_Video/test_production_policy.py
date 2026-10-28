import json,tempfile,unittest,subprocess,shutil
from pathlib import Path
from unittest.mock import patch
import production_policy as p
import game_sources as g
from reset_layout import original_pages,detailed_pages,context_groups

class NewProductionChecks(unittest.TestCase):
    def test_game_targets_advisory_with_more_than_four_stories(self):
        rows=[dict(id=str(i),kind='games',game='arknights',game_region='cn',game_topic='update',url='https://example.com/'+str(i)) for i in range(7)]
        result=g.coverage(rows)
        self.assertEqual(len(result['candidate_ids']['arknights_cn']),7)
        self.assertIsNone(result['maximum_items']);self.assertFalse(result['enforce_minimum'])
        self.assertTrue(g.coverage([])['advisory_only'])

    def test_rsc_and_yostar_millisecond_dates_and_images(self):
        row=dict(cid='42',title='版本更新',displayTime=1792846800,cover='https://web.hycdn.cn/test.png')
        page='<script>self.__next_f.push('+json.dumps([1,'abc:'+json.dumps({'list':[row]},ensure_ascii=False)])+')</script>'
        source=dict(article_base='https://ak.hypergryph.com/news',game='arknights',game_region='cn')
        parsed=g.parse(page,source);self.assertEqual(len(parsed),1);self.assertEqual(parsed[0]['game_topic'],'update');self.assertTrue(parsed[0]['images'])
        row['displayTime']*=1000
        self.assertEqual(g.parse(json.dumps(row),source)[0]['published'],parsed[0]['published'])

    def test_social_rejected_and_game_module_order_and_transition(self):
        ep=dict(edition_slot='night',scenes=[dict(id='ai',section='AI 动态',narration='消息。'),dict(id='g',event_key='arknights:event:test',section='游戏资讯',game='arknights',game_region='cn',game_topic='event',narration='活动内容。')])
        p.validate_content(ep);self.assertIn('接下来是游戏资讯',ep['scenes'][1]['narration'])
        self.assertEqual([m[1] for m in p.modules(ep,[{'start':0},{'start':20}],45)],['AI 动态','游戏资讯'])
        ep['scenes'][1]['section']='国内新闻'
        with self.assertRaises(ValueError):p.validate_content(ep)

    def test_required_tags_reserve_activity_slot(self):
        tags=p.tags(['AI','明日方舟','终末地']+[str(i) for i in range(12)])
        self.assertEqual(tags[:2],['明日方舟','终末地']);self.assertEqual(len(set(tags)),len(tags));self.assertLessEqual(len(tags),9)

    def test_lossless_full_original_and_short_reset_rejected(self):
        original=('This is a reset announcement.\nMore context and conditions apply. '*12).rstrip()
        self.assertEqual(''.join(original_pages(original)),original)
        with self.assertRaises(ValueError):detailed_pages(original,dict(narration='tibo说重置。'))
        self.assertEqual(context_groups([dict(narration='消息。'*30),dict(narration='下一页。')]),[26,4,1])

    def test_actual_mp4_duration_gate_not_metadata(self):
        ff=Path('D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/ffmpeg.exe')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config.json').write_text(json.dumps(dict(production=dict(minimum_duration_exclusive_seconds=30),voice=dict(qwen3=dict(ffmpeg_executable=str(ff))))))
            for duration,allowed in [(30,False),(31,True)]:
                video=root/(str(duration)+'.mp4')
                subprocess.run([str(ff),'-y','-loglevel','error','-f','lavfi','-i','color=s=64x36:r=1','-t',str(duration),'-c:v','mpeg4',str(video)],check=True,capture_output=True)
                if allowed:self.assertTrue(p.validate_video(root,video)['ok'])
                else:
                    with self.assertRaisesRegex(ValueError,'exceed 30'):p.validate_video(root,video)
                    import upload_bridge
                    config=p.config(root);config['publisher']=dict(enabled=True,auto_submit=True);config['release']=dict(directory='release')
                    (root/'config.json').write_text(json.dumps(config))
                    release=root/'release/short';release.mkdir(parents=True)
                    shutil.copy2(video,release/'short.mp4')
                    (release/'release.json').write_text(json.dumps(dict(state='ready_for_upload',video_filename='short.mp4')))
                    (release/'publication.json').write_text(json.dumps(dict(auto_publish=True,tags=[])))
                    with patch.object(upload_bridge,'call') as browser,patch.object(upload_bridge,'prepare') as contract:
                        with self.assertRaisesRegex(ValueError,'exceed 30'):upload_bridge.publish_ready(release,root)
                        browser.assert_not_called();contract.assert_not_called()

if __name__=='__main__':unittest.main()
