"""Check/deploy the validated uploader; defaults to read-only drift detection."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,shutil
from pathlib import Path
from project_paths import workspace_root
from upload_bridge import implementation_fingerprint
ROOT=Path(__file__).resolve().parent


def sync(apply=False,installed=False,root=ROOT):
    root=Path(root).resolve();work=workspace_root(root)
    source=work/'codex-upload-video/codex-upload'
    targets=[root/'skills/codex-upload']
    if installed:targets.append(Path.home()/'.codex/skills/codex-upload')
    # Only public skill assets and code. Never copy runtime/account/browser state.
    files=[p.relative_to(source) for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.mjs','.md','.json','.yaml','.txt'}]
    changed=[];stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    for index,target in enumerate(targets):
        for rel in files:
            src=source/rel;dst=target/rel
            if dst.exists() and src.read_bytes()==dst.read_bytes():continue
            changed.append(dict(target=str(target),file=rel.as_posix()))
            if apply:
                if dst.exists():
                    backup=root/'.cache/upload-skill-backups'/stamp/str(index)/rel
                    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,backup)
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    fingerprint=implementation_fingerprint(source)
    cfg=json.loads((root/'config.json').read_text(encoding='utf-8'))
    pinned=cfg.get('publisher',{}).get('implementation_sha256')
    if apply:
        for target in targets:
            if implementation_fingerprint(target)!=fingerprint:raise ValueError('Uploader deployment hash mismatch')
        cfg['publisher']['implementation_sha256']=fingerprint
        (root/'config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return dict(ok=(apply or not changed) and (apply or pinned==fingerprint),applied=apply,changed=changed,implementation_sha256=fingerprint,pin_matches=apply or pinned==fingerprint)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--installed',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    r=sync(a.apply,a.installed);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['ok'] else 2)
