"""Deployment gate regression tests. All fixtures stay in temporary workspace."""
import hashlib,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sync_upload_skill as sync
import upload_bridge as bridge

ROOT=Path(__file__).resolve().parent
VALIDATOR=ROOT.parents[1]/'codex-upload-video/validate.py'

class DeploymentChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.addCleanup(self.tmp.cleanup);self.work=Path(self.tmp.name);self.root=self.work/'News_Video';self.root.mkdir()
        self.repo=self.work/'codex-upload-video';self.source=self.repo/'codex-upload';self.target=self.root/'skills/codex-upload'
        self.repo.mkdir();shutil.copy2(VALIDATOR,self.repo/'validate.py');self.validator=sync.validation_module(self.repo)
        for name in ['codex_upload.py','browser.mjs','forms.mjs','cover_editor.mjs','browser_ui.mjs']:
            p=self.source/'scripts'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('validated '+name)
        (self.repo/'tests').mkdir();(self.repo/'tests/fixture.js').write_text('native DOM contract')
        self.config=self.root/'config.json';self.config.write_text(json.dumps({'publisher':{'implementation_sha256':'previous'}}))
        self.patch=patch.object(sync,'workspace_root',return_value=self.work);self.patch.start();self.addCleanup(self.patch.stop)
    def green(self):
        directory=self.repo/'.validation';directory.mkdir(exist_ok=True);checks={}
        for name,n in [('python',15),('chrome',24)]:
            log=directory/(name+'.log');log.write_text('offline regression evidence')
            checks[name]={'returncode':0,'tests':n,'skipped':0,'log':log.name,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
        receipt={'schema':1,'ok':True,'source_tree_sha256':self.validator.tree_fingerprint(self.repo),'checks':checks}
        (directory/'latest.json').write_text(json.dumps(receipt));return receipt
    def test_missing_receipt_rejects_before_copy_or_pin_change(self):
        before=self.config.read_bytes()
        with self.assertRaisesRegex(ValueError,'UPLOAD_VALIDATION_REQUIRED'):sync.sync(True,root=self.root)
        self.assertFalse(self.target.exists());self.assertEqual(self.config.read_bytes(),before)
    def test_runtime_and_fixture_changes_invalidate_green_receipt(self):
        for file in [self.source/'scripts/cover_editor.mjs',self.source/'scripts/browser_ui.mjs',self.repo/'tests/fixture.js']:
            with self.subTest(file=file):
                self.green();file.write_text(file.read_text()+' drift')
                with self.assertRaisesRegex(ValueError,'UPLOAD_VALIDATION_STALE'):sync.sync(True,root=self.root)
                self.assertFalse(self.target.exists())
    def test_skipped_browser_or_changed_log_cannot_deploy(self):
        receipt=self.green();receipt['checks']['chrome']['skipped']=1;(self.repo/'.validation/latest.json').write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError,'UPLOAD_VALIDATION_FAILED'):sync.sync(True,root=self.root)
        self.green();(self.repo/'.validation/chrome.log').write_text('changed')
        with self.assertRaisesRegex(ValueError,'EVIDENCE_MISSING'):sync.sync(True,root=self.root)
    def test_validated_deployment_readback_and_rollback_on_copy_failure(self):
        self.green();first=sync.sync(True,root=self.root);self.assertTrue(first['ok']);self.assertTrue(sync.sync(root=self.root)['ok'])
        with patch.object(bridge.subprocess,'run',return_value=type('Result',(),{'stdout':'{"ok": true}'})()) as run:
            self.assertTrue(bridge.call(['doctor'],self.root)['ok']);run.assert_called_once()
        before=self.config.read_bytes();evidence=(self.root/'.cache/upload-validation.json').read_bytes()
        code=self.source/'scripts/cover_editor.mjs';old=(self.target/'scripts/cover_editor.mjs').read_bytes();code.write_text('new validated implementation');self.green()
        copy=sync.atomic_copy
        def fail_source(src,dst):
            if Path(src)==code:raise OSError('simulated copy failure')
            return copy(src,dst)
        with patch.object(sync,'atomic_copy',side_effect=fail_source):
            with self.assertRaises(OSError):sync.sync(True,root=self.root)
        self.assertEqual((self.target/'scripts/cover_editor.mjs').read_bytes(),old);self.assertEqual(self.config.read_bytes(),before)
        self.assertEqual((self.root/'.cache/upload-validation.json').read_bytes(),evidence);self.assertFalse((self.root/'.cache/upload-skill-deploy.lock').exists())
    def test_bridge_blocks_unvalidated_deployment_and_concurrent_deploy(self):
        self.green();sync.sync(True,root=self.root)
        (self.root/'.cache/upload-validation.json').unlink()
        with patch.object(bridge.subprocess,'run') as run:
            self.assertEqual(bridge.call(['doctor'],self.root)['error']['code'],'SKILL_VALIDATION_REQUIRED');run.assert_not_called()
            (self.root/'.cache/upload-skill-deploy.lock').write_text('deploying')
            self.assertEqual(bridge.call(['doctor'],self.root)['error']['code'],'SKILL_DEPLOYING');run.assert_not_called()
    def test_fingerprint_includes_new_runtime_modules(self):
        previous=bridge.implementation_fingerprint(self.source)
        (self.source/'scripts/cover_editor.mjs').write_text('changed')
        self.assertNotEqual(previous,bridge.implementation_fingerprint(self.source))

if __name__=='__main__':unittest.main()
