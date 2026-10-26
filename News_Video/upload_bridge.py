"""News release -> codex-upload manifest -> automatic submit -> verified cleanup."""
from __future__ import annotations
import argparse,datetime as dt,json,os,subprocess,sys
from pathlib import Path
from project_paths import release_root

ROOT=Path(__file__).resolve().parent

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def settings(root=ROOT):
    cfg=Path(root)/'config.json'
    return load(cfg).get('publisher',{}) if cfg.exists() else {}
def paths(root=ROOT):
    cfg=settings(root);root=Path(root).resolve()
    return (root/cfg.get('skill_cli','skills/codex-upload/scripts/codex_upload.py')).resolve(),(root/cfg.get('private_home','../.codex-upload-private')).resolve()
def call(args,root=ROOT):
    cli,home=paths(root)
    if not cli.is_file():raise ValueError('codex-upload CLI is missing: '+str(cli))
    env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    p=subprocess.run([sys.executable,'-B',str(cli),'--home',str(home),*map(str,args)],capture_output=True,text=True,encoding='utf-8',env=env)
    try:result=json.loads(p.stdout)
    except ValueError:raise ValueError('codex-upload returned no structured result; inspect local diagnostics')
    return result
def prepare(directory,root=ROOT):
    if not settings(root).get('enabled'):return None
    result=call(['from-release',str(Path(directory).resolve())],root)
    if not result.get('ok'):raise ValueError('Upload contract invalid: '+result.get('error',{}).get('code','UNKNOWN'))
    return result
def publish_ready(directory,root=ROOT):
    root=Path(root).resolve();directory=Path(directory).resolve()
    if not directory.is_relative_to(release_root(root)):raise ValueError('Use release only')
    cfg=settings(root);receipt=load(directory/'release.json')
    if receipt.get('published') or receipt.get('state') in {'submitted','reviewing','published'}:return dict(ok=True,skipped='already_submitted_or_published')
    if receipt.get('state') in {'unknown','uploading','submitting'}:return dict(ok=False,error=dict(code='RECONCILE_REQUIRED'))
    pub=load(directory/'publication.json')
    if not cfg.get('enabled') or not cfg.get('auto_submit') or pub.get('auto_publish') is False:return dict(ok=True,skipped='automatic_upload_disabled_for_this_release')
    if not (directory/'upload.codex.json').exists():prepare(directory,root)
    result=call(['publish',str(directory/'upload.codex.json'),'--execute','--unattended'],root)
    save(directory/'upload-attempt.json',result)
    if result.get('ok') and result.get('state') in {'submitted','reviewing','published'}:
        receipt.update(state=result['state'],submitted=True,published=False,platform=result['receipt'],upload_backend='codex-upload')
    elif result.get('state')=='unknown':receipt.update(state='unknown',upload_backend='codex-upload')
    else:receipt.update(state='upload_failed',upload_error=result.get('error',result.get('result',{}).get('error',{})))
    save(directory/'release.json',receipt)
    return result
def verify_release(directory,root=ROOT,cleanup=True):
    root=Path(root).resolve();directory=Path(directory).resolve()
    if not directory.is_relative_to(release_root(root)):raise ValueError('Use release only')
    receipt=load(directory/'release.json')
    if receipt.get('published'):return dict(ok=True,skipped='already_published')
    if receipt.get('state')=='unknown':
        attempt=load(directory/'upload-attempt.json')
        if not attempt.get('key'):return dict(ok=False,error=dict(code='RECONCILE_KEY_MISSING'))
        reconciled=call(['reconcile',attempt['key']],root)
        if reconciled.get('state') not in {'submitted','published'}:return reconciled
        receipt.update(state=reconciled['state'],platform=reconciled['receipt']);save(directory/'release.json',receipt)
    platform=receipt.get('platform',{});target=platform.get('bvid') or platform.get('aid')
    if not target:return dict(ok=False,error=dict(code='PLATFORM_RECEIPT_MISSING'))
    result=call(['verify',str(target)],root)
    if not result.get('ok') or result.get('state')!='published':return result
    episode=load(directory/'episode.json')
    if result['receipt'].get('title')!=load(directory/'publication.json')['title']:return dict(ok=False,error=dict(code='PLATFORM_TITLE_MISMATCH'))
    proof=dict(**result,verified_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat())
    save(directory/'publication-verified.json',proof)
    source=root/'episodes'/episode['id']
    if cleanup and root==ROOT and (source/'episode.json').exists():
        from finalize_release import finalize
        return finalize(episode['id'],receipt.get('edition_slot') or episode['edition_slot'],published=True,publication_evidence=proof)
    receipt.update(state='published',published=True,submitted=True,platform=result['receipt'],publication_evidence='Verified authenticated account and public video view')
    save(directory/'release.json',receipt);return result
def pending(root=ROOT):
    root=Path(root).resolve();out=[]
    for path in release_root(root).rglob('release.json'):
        receipt=load(path)
        if not receipt.get('published') and receipt.get('state') in {'submitted','reviewing','unknown'}:
            out.append(dict(directory=str(path.parent),result=verify_release(path.parent,root)))
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    for name in ['prepare','publish','verify']:
        a=sub.add_parser(name);a.add_argument('directory')
    sub.add_parser('pending');a=p.parse_args()
    result=prepare(a.directory) if a.command=='prepare' else publish_ready(a.directory) if a.command=='publish' else verify_release(a.directory) if a.command=='verify' else pending()
    print(json.dumps(result,ensure_ascii=False,indent=2))
