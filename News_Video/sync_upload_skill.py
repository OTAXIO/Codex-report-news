"""Check/deploy the uploader only after the exact source tree passes validation."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,importlib.util,json,shutil
from pathlib import Path
from project_paths import workspace_root
from upload_bridge import implementation_fingerprint
ROOT=Path(__file__).resolve().parent

def validation_module(repo):
    file=Path(repo)/'validate.py'
    if not file.is_file():raise ValueError('UPLOAD_VALIDATION_REQUIRED: uploader validate.py is missing')
    spec=importlib.util.spec_from_file_location('uploader_validation',file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def atomic_copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True);temporary=dst.with_name(dst.name+'.deploying');shutil.copy2(src,temporary);temporary.replace(dst)

def sync(apply=False,installed=False,root=ROOT):
    root=Path(root).resolve();work=workspace_root(root);repo=work/'codex-upload-video';source=repo/'codex-upload';validator=validation_module(repo)
    targets=[root/'skills/codex-upload']
    if installed:targets.append(Path.home()/'.codex/skills/codex-upload')
    files=validator.public_skill_files(source);fingerprint=implementation_fingerprint(source)
    cfg=json.loads((root/'config.json').read_text(encoding='utf-8'));pinned=cfg.get('publisher',{}).get('implementation_sha256')
    try:receipt=validator.require_receipt(repo);validation_error=None
    except ValueError as error:receipt=None;validation_error=str(error)
    # Enforce before copying even one file or changing the configured pin.
    if apply and not receipt:raise ValueError(validation_error)
    changed=[]
    for target in targets:
        for rel in files:
            src=source/rel;dst=target/rel
            if not dst.resolve().is_relative_to(target.resolve()):raise ValueError('Deployment target escapes its skill directory')
            if not dst.exists() or src.read_bytes()!=dst.read_bytes():changed.append(dict(target=str(target),file=rel.as_posix()))
    if apply:
        lock=root/'.cache/upload-skill-deploy.lock';lock.parent.mkdir(parents=True,exist_ok=True)
        stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f');restores=[];config_before=(root/'config.json').read_bytes()
        evidence=root/'.cache/upload-validation.json';evidence_before=evidence.read_bytes() if evidence.exists() else None
        # Bridge refuses browser work while copies/pin are being switched.
        with lock.open('x',encoding='utf-8') as guard:guard.write(stamp)
        try:
            for index,target in enumerate(targets):
                for rel in files:
                    src=source/rel;dst=target/rel
                    if dst.exists() and src.read_bytes()==dst.read_bytes():continue
                    backup=None
                    if dst.exists():
                        backup=root/'.cache/upload-skill-backups'/stamp/str(index)/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,backup)
                    restores.append((dst,backup));atomic_copy(src,dst)
            validator.require_receipt(repo)
            if implementation_fingerprint(source)!=fingerprint:raise ValueError('Uploader source changed during deployment')
            for target in targets:
                if implementation_fingerprint(target)!=fingerprint:raise ValueError('Uploader deployment hash mismatch')
                if any((target/rel).read_bytes()!=(source/rel).read_bytes() for rel in files):raise ValueError('Uploader public asset readback mismatch')
            deployment={**receipt,'implementation_sha256':fingerprint};evidence.write_text(json.dumps(deployment,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            cfg['publisher'].update(implementation_sha256=fingerprint,validation_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())
            config_temp=(root/'config.json').with_suffix('.json.deploying');config_temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');config_temp.replace(root/'config.json')
        except Exception:
            for dst,backup in reversed(restores):
                if backup:atomic_copy(backup,dst)
                elif dst.exists():dst.unlink()
            (root/'config.json').write_bytes(config_before)
            if evidence_before is not None:evidence.write_bytes(evidence_before)
            elif evidence.exists():evidence.unlink()
            raise
        finally:lock.unlink()
    evidence=root/'.cache/upload-validation.json';deployment_ok=evidence.is_file() and hashlib.sha256(evidence.read_bytes()).hexdigest()==cfg.get('publisher',{}).get('validation_sha256')
    return dict(ok=(apply or not changed) and (apply or pinned==fingerprint) and receipt is not None and deployment_ok,applied=apply,changed=changed,implementation_sha256=fingerprint,pin_matches=apply or pinned==fingerprint,validated=receipt is not None,validation_error=validation_error,validation_checks=receipt.get('checks') if receipt else None)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--installed',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    try:r=sync(a.apply,a.installed);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 2)
    except ValueError as error:print(json.dumps(dict(ok=False,error=str(error)),ensure_ascii=False));raise SystemExit(2)
