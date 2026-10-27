import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('news_upload_cli',ROOT/'skills/codex-upload/scripts/codex_upload.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class UploadRecoveryChecks(unittest.TestCase):
    def test_only_returned_field_failure_before_submit_is_retryable(self):
        for started,field_error,expected in [(False,'SELECTOR_MISSING','failed'),(True,'SELECTOR_MISSING','unknown'),(False,'TIMEOUT','unknown'),(None,'SELECTOR_MISSING','unknown')]:
            with self.subTest(started=started,field_error=field_error),tempfile.TemporaryDirectory() as tmp:
                home=Path(tmp);key='a'*64;meta=home/'manifest.json';u.write(meta,dict(title='one story'))
                u.write(home/'state'/(key+'.json'),dict(key=key,operation='upload',state='unknown',manifest=str(meta),started_at='2026-10-27T02:00:00+08:00',result=dict(ok=False,error=dict(code=field_error))))
                if started is not None:u.write(home/'state'/(key+'.progress.json'),dict(video_selected=True,submit_started=started))
                with patch.object(u,'backend',return_value=dict(ok=True,state='unknown')):result=u.reconcile(key,home)
                self.assertEqual(result['state'],expected)

    def test_cover_dialog_failure_can_recover_but_unknown_dialog_cannot(self):
        for text,expected in [('封面制作\n智能','failed'),('请支付费用','unknown')]:
            with self.subTest(text=text),tempfile.TemporaryDirectory() as tmp:
                home=Path(tmp);key='b'*64;meta=home/'manifest.json';u.write(meta,dict(title='story'))
                u.write(home/'state'/(key+'.json'),dict(key=key,operation='upload',state='unknown',manifest=str(meta),started_at='2026-10-27T02:00:00+08:00',result=dict(ok=False,error=dict(code='UNKNOWN_DIALOG',details=dict(dialog_text=text)))))
                u.write(home/'state'/(key+'.progress.json'),dict(video_selected=True,submit_started=False))
                with patch.object(u,'backend',return_value=dict(ok=True,state='unknown')):result=u.reconcile(key,home)
                self.assertEqual(result['state'],expected)

    def test_failed_creator_recheck_cannot_enable_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);key='c'*64;meta=home/'manifest.json';u.write(meta,dict(title='story'))
            u.write(home/'state'/(key+'.json'),dict(operation='upload',state='unknown',manifest=str(meta),started_at='2026-10-27T02:00:00+08:00',result=dict(error=dict(code='SELECTOR_MISSING'))))
            u.write(home/'state'/(key+'.progress.json'),dict(submit_started=False))
            with patch.object(u,'backend',return_value=dict(ok=False,error=dict(code='AUTH_REQUIRED'))):result=u.reconcile(key,home)
            self.assertFalse(result['ok']);self.assertEqual(u.read(home/'state'/(key+'.json'))['state'],'unknown')

class BridgeRecoveryChecks(unittest.TestCase):
    def setup_release(self,root,state='unknown'):
        import upload_bridge as b
        b.save(root/'config.json',{'release':{'directory':'release'},'publisher':{'enabled':True,'auto_submit':True}})
        directory=root/'release'/'edition';directory.mkdir(parents=True)
        b.save(directory/'release.json',{'state':state,'upload_policy':'automatic','published':False})
        b.save(directory/'upload-attempt.json',{'key':'a'*64})
        b.save(directory/'publication.json',{'auto_publish':True})
        return directory

    def test_each_presubmit_recovery_rechecks_without_an_attempt_cap(self):
        import upload_bridge as b
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=self.setup_release(root)
            evidence={'submit_started':False,'returned_field_error':'UNKNOWN_DIALOG'}
            with patch.object(b,'call',return_value={'ok':True,'state':'failed','safe_retry_evidence':evidence}),patch.object(b,'publish_ready',return_value={'ok':False,'state':'unknown'}) as publish:
                b.recover(directory,root)
                self.assertEqual(publish.call_count,1)
                self.assertEqual(b.load(directory/'release.json')['automatic_recovery_attempts'],1)
                # No subjective speech_review confirmation field was needed.
                b.recover(directory,root)
                self.assertEqual(publish.call_count,2)
                self.assertEqual(b.load(directory/'release.json')['automatic_recovery_attempts'],2)

    def test_uncertain_submit_never_reuploads(self):
        import upload_bridge as b
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=self.setup_release(root)
            with patch.object(b,'call',return_value={'ok':True,'state':'unknown'}),patch.object(b,'publish_ready') as publish:
                b.recover(directory,root);publish.assert_not_called()

    def test_same_cover_failure_requires_changed_code_or_inputs_without_a_count_cap(self):
        import upload_bridge as b
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=self.setup_release(root,'upload_failed')
            attempt=b.load(directory/'upload-attempt.json');attempt['repair_signature']=b.repair_signature(directory,root);b.save(directory/'upload-attempt.json',attempt)
            checked={'ok':True,'state':'failed','safe_retry_evidence':{'submit_started':False,'returned_field_error':'COVER_NOT_LOADED'}}
            with patch.object(b,'call',return_value=checked) as recheck,patch.object(b,'publish_ready',return_value={'ok':False}) as publish:
                self.assertEqual(b.recover(directory,root)['error']['code'],'REPAIR_REQUIRED');publish.assert_not_called();recheck.assert_called_once()
                b.save(directory/'publication.json',{'auto_publish':True,'repair':'updated verified cover'})
                b.recover(directory,root);publish.assert_called_once();self.assertEqual(b.load(directory/'release.json')['automatic_recovery_attempts'],1)

    def test_diagnostic_hold_is_not_picked_up_by_pending(self):
        import upload_bridge as b
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=self.setup_release(root,'ready_for_upload')
            b.save(directory/'release.json',{'state':'ready_for_upload','upload_policy':'diagnostic_hold'})
            with patch.object(b,'recover') as recover:
                self.assertEqual(b.pending(root),[]);recover.assert_not_called()

    def test_stale_uploader_is_blocked_before_browser_or_network(self):
        import upload_bridge as b
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);skill=root/'skills/codex-upload'
            for name in ['codex_upload.py','forms.mjs','browser.mjs']:
                p=skill/'scripts'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('validated')
            fingerprint=b.implementation_fingerprint(skill)
            b.save(root/'config.json',{'publisher':{'implementation_sha256':fingerprint}})
            (skill/'scripts/forms.mjs').write_text('old implementation')
            with patch.object(b.subprocess,'run') as run:
                self.assertEqual(b.call(['doctor'],root)['error']['code'],'SKILL_VERSION_MISMATCH');run.assert_not_called()

    def test_ready_release_refreshes_cached_manifest_before_publish(self):
        import upload_bridge as b
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=self.setup_release(root,'ready_for_upload')
            b.save(directory/'upload.codex.json',{'activity':{'strategy':'relevant_popular_free'}})
            with patch.object(b,'prepare') as prepare,patch.object(b,'call',return_value={'ok':True,'state':'submitted','receipt':{'aid':123}}):
                b.publish_ready(directory,root);prepare.assert_called_once_with(directory,root)
            with patch.object(b,'prepare') as prepare:
                b.publish_ready(directory,root);prepare.assert_not_called()
