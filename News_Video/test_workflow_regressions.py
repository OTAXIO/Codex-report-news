"""Small isolated regressions for the daily workflow boundaries."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hourly_monitor
import important_events
import news_video
import build_film
import release_manager
import render_sample
import production_flow
import upload_bridge


class WorkflowRegressions(unittest.TestCase):
    def test_stage_router_holds_prepared_release_until_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);root=work/'News_Video';source=root/'episodes'/'edition';source.mkdir(parents=True)
            release=work/'release'/'edition';release.mkdir(parents=True)
            upload_bridge.save(source/'episode.json',{'id':'edition','edition_slot':'night'})
            upload_bridge.save(source/'release-target.json',{'directory':str(release)})
            upload_bridge.save(release/'release.json',{'state':'ready_for_upload'})
            self.assertEqual(production_flow.status('edition',root)['stage'],'resume_export')
            (release/'used-news-record.json').write_text('{}')
            upload_bridge.save(release/'release.json',{'state':'ready_for_upload','upload_policy':'automatic'})
            self.assertEqual(production_flow.status('edition',root)['stage'],'recover_upload')
            upload_bridge.save(release/'release.json',{'state':'published','published':True})
            self.assertEqual(production_flow.status('edition',root)['stage'],'complete')

    def test_visual_fingerprint_tracks_story_and_picture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);episode=root/'episodes'/'edition';episode.mkdir(parents=True)
            image=root/'picture.png';image.write_bytes(b'first')
            (episode/'episode.json').write_text(json.dumps({'scenes':[{'image':'picture.png'}]}))
            (episode/'timings.json').write_text('{"duration":31}')
            with patch.object(build_film,'ROOT',root):
                first=build_film.input_fingerprint('edition',{'backend':'hyperframes'})
                image.write_bytes(b'second')
                second=build_film.input_fingerprint('edition',{'backend':'hyperframes'})
                (episode/'episode.json').write_text(json.dumps({'scenes':[{'image':'picture.png','title':'new'}]}))
                third=build_film.input_fingerprint('edition',{'backend':'hyperframes'})
            self.assertEqual(len({first,second,third}),3)

    def test_prerelease_feed_item_does_not_lead_stable_news(self):
        base={'kind':'ai','published':'2026-10-28T00:00:00+00:00','priority_tier':1,'preferred_vendor_order':0,'source_priority':1}
        stable=dict(base,url='https://example.com/official/model-release')
        alpha=dict(base,url='https://github.com/openai/codex/releases/tag/rust-v0.166.0-alpha.5')
        self.assertLess(news_video.candidate_order(stable),news_video.candidate_order(alpha))

    def test_recap_stays_before_games(self):
        event={'event_key':'new', 'original_event_key':'old', 'episode_id':'temporary-x',
               'url':'https://example.com/x', 'scene':{'id':'x','item_id':'x',
               'title':'发布模型','short_title':'模型','source_url':'https://example.com/x',
               'narration':'OpenAI 发布模型。','section':'临时新闻'}}
        episode={'edition_slot':'night','scenes':[
            {'id':'ordinary','section':'AI 动态'}, {'id':'game','section':'游戏资讯','game':'arknights'}]}
        with patch.object(important_events,'recap_candidates',return_value=[event]), \
             patch.object(important_events,'recap_allowed_for_event',return_value=True):
            important_events.prepare_main_recaps(episode)
        self.assertEqual([s['id'] for s in episode['scenes']],['ordinary','recap-temporary-x','game'])

    def test_failed_release_quality_does_not_write_used_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'episodes'/'edition';source.mkdir(parents=True)
            (source/'episode.json').write_text(json.dumps({'id':'edition'}))
            with patch.object(render_sample,'ROOT',root), \
                 patch('production_policy.validate_video'), \
                 patch.object(release_manager,'prepare',side_effect=ValueError('quality failed')), \
                 patch('used_news.record_export') as ledger:
                with self.assertRaisesRegex(ValueError,'quality failed'):
                    render_sample.complete_export('edition',allow_upload=False)
                ledger.assert_not_called()

    def test_upload_manifest_failure_follows_used_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'episodes'/'edition';source.mkdir(parents=True)
            (source/'episode.json').write_text(json.dumps({'id':'edition'}))
            calls=[]
            def record(*_):calls.append('ledger')
            def attach(*_):calls.append('attach')
            def upload(*_):calls.append('upload');raise ValueError('uploader unavailable')
            with patch.object(render_sample,'ROOT',root), \
                 patch('production_policy.validate_video'), \
                 patch.object(release_manager,'prepare',return_value={'directory':str(root/'release')}) as prepared, \
                 patch('used_news.record_export',side_effect=record), \
                 patch.object(release_manager,'attach_used_record',side_effect=attach), \
                 patch.object(upload_bridge,'prepare',side_effect=upload):
                with self.assertRaisesRegex(ValueError,'uploader unavailable'):
                    render_sample.complete_export('edition',allow_upload=False)
            self.assertEqual(calls,['ledger','attach','upload'])
            self.assertFalse(prepared.call_args.kwargs['create_upload_manifest'])

    def test_release_record_attachment_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'episode';source.mkdir();release=root/'release';release.mkdir()
            (source/'used-news-record.json').write_text('{"episode_id":"edition"}')
            (release/'release.json').write_text('{"state":"ready_for_upload","archive_files":[]}')
            first=release_manager.attach_used_record(release,source)
            second=release_manager.attach_used_record(release,source)
            self.assertEqual(first['archive_files'],second['archive_files'])
            self.assertEqual(len(second['archive_files']),1)

    def test_bad_release_does_not_block_other_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);release=root/'release';release.mkdir()
            upload_bridge.save(root/'config.json',{'release':{'directory':'release'}})
            bad=release/'bad';bad.mkdir();(bad/'release.json').write_text('{bad json')
            good=release/'good';good.mkdir()
            upload_bridge.save(good/'release.json',{'state':'unknown','published':False})
            with patch.object(upload_bridge,'recover',return_value={'ok':True}) as recover:
                rows=upload_bridge.pending(root)
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]['result']['error']['code'],'RELEASE_RECOVERY_ERROR')
            recover.assert_called_once_with(good,root)

    def test_one_recovery_exception_does_not_hide_next_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);upload_bridge.save(root/'config.json',{'release':{'directory':'release'}})
            for name in ('a','b'):
                folder=root/'release'/name;folder.mkdir(parents=True)
                upload_bridge.save(folder/'release.json',{'state':'unknown','published':False})
            def recover(directory,_):
                if directory.name=='a':raise RuntimeError('isolated failure')
                return {'ok':True}
            with patch.object(upload_bridge,'recover',side_effect=recover):
                rows=upload_bridge.pending(root)
            self.assertEqual([x['result'].get('ok') for x in rows],[False,True])

    def test_compact_hourly_reports_stop_without_sources(self):
        report={'leaders':{'stopped':True,'reason':'NEED_LOGIN',
                           'requires_user_resolution':True,'sources':[]},
                'resets':{'pending':['alert-id'],'new_alerts':[]}}
        compact=hourly_monitor.compact_report(report)
        self.assertEqual(compact['reason'],'NEED_LOGIN')
        self.assertFalse(compact['source_ok'])
        self.assertTrue(compact['requires_user_resolution'])
        self.assertEqual(compact['pending'],['alert-id'])
        self.assertTrue(compact['error_fingerprint'])

    def test_hourly_stop_notifies_once_until_signal_changes(self):
        report={'finished':'2026-10-28T00:00:00+00:00',
                'leaders':{'stopped':True,'reason':'NEED_LOGIN','sources':[]},
                'resets':{'pending':[],'new_alerts':[]}}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=hourly_monitor.compact_with_change(report,root)
            second=hourly_monitor.compact_with_change(report,root)
            report['resets']['pending']=['new-reset']
            third=hourly_monitor.compact_with_change(report,root)
        self.assertTrue(first['notification_worthy'])
        self.assertFalse(second['notification_worthy'])
        self.assertTrue(third['notification_worthy'])

    def test_hourly_busy_does_not_notify_without_pending(self):
        report={'finished':'2026-10-28T00:00:00+00:00',
                'leaders':{'stopped':True,'reason':'BUSY','sources':[]},
                'resets':{'pending':[],'new_alerts':[]}}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(hourly_monitor.compact_with_change(report,Path(tmp))['notification_worthy'])


if __name__=='__main__':unittest.main()
