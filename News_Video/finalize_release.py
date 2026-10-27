"""Archive a user-confirmed published edition, verify, then clean generated work."""
import argparse,datetime as dt,hashlib,json,os,subprocess,zipfile
from pathlib import Path
from project_paths import release_root

ROOT=Path(__file__).resolve().parent
FINAL_NAMES={
 'leader-audit.json','tibo-audit.json','ai-coverage-audit.json','sample.mp4','cover-bilibili.jpg','cover-16x10.png','cover-16x9.png','cover-4x3.png',
 'description.txt','script.txt','spoken_script.txt','publication.json','episode.json',
 'narration.wav','narration_原始.wav','narration.json','timings.json','captions.json',
 'scene-timings.json','progress.json','used-news-record.json','SPEECH_REVIEW.md',
 'check.json','ffprobe.json','progress-validation.json','verification-result.json',
 'transition-preview.png','delivery-manifest.json','voice_job.json','inference.yaml','cover.json','reset-alert.json'}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def safe(path,base):
    path=Path(path).resolve();base=Path(base).resolve()
    if not path.is_relative_to(base) or path==base:raise ValueError('Path outside intended directory: '+str(path))
    return path

def finalize(episode_id,slot,published=False,dry_run=False,publication_evidence=None):
    if not published:raise ValueError('Publication must first be confirmed by the user')
    source=safe(ROOT/'episodes'/episode_id,ROOT/'episodes')
    if (source/'release.json').exists():return json.loads((source/'release.json').read_text(encoding='utf-8'))
    ep=json.loads((source/'episode.json').read_text(encoding='utf-8'))
    date=dt.date.fromisoformat(ep['edition_date'])
    from release_manager import prepare,release_target
    target=safe(release_target(ROOT,ep,slot)[0],release_root(ROOT))
    if target.exists() and any(target.iterdir()):
        ready=json.loads((target/'release.json').read_text(encoding='utf-8'))
        if ready.get('episode_id')!=episode_id:raise ValueError('Release folder belongs to another edition')
        if ready.get('published') and not publication_evidence:raise ValueError('Published release is immutable; verify before cleanup')
    else:ready=None
    final=[p for p in source.iterdir() if p.is_file() and p.name in FINAL_NAMES]
    for required in ['sample.mp4','episode.json','publication.json','script.txt','cover-16x9.png','cover-4x3.png']:
        if not (source/required).is_file():raise ValueError('Missing final artifact: '+required)
    cleanup=set()
    for folder in (ROOT/'episodes').iterdir():
        if not folder.is_dir():continue
        if folder!=source:continue
        for p in folder.rglob('*'):
            if not p.is_file() or p in final:continue
            relative=p.relative_to(folder)
            if folder==source or any(part in {'render-frames','verification-frames','temp','__pycache__'} for part in relative.parts) or p.suffix.lower() in {'.mp4','.wav','.png','.jpg','.log','.ffconcat','.pyc'}:
                cleanup.add(p)
    for p in ROOT.glob('data-'+episode_id+'*'):
        if p.is_file() and p.suffix in {'.json','.jsonl','.log'}:cleanup.add(p)
    for p in cleanup:safe(p,ROOT)
    retained=[p for p in ROOT.glob('*.py')]+[ROOT/x for x in ['config.json','sources.json','package.json','data/news.sqlite3']]
    for folder in [ROOT/'assets',ROOT/'logs',ROOT/'data/articles',ROOT/'data/collections',ROOT/'data/source-probes']:
        if folder.exists():retained.extend(p for p in folder.rglob('*') if p.is_file())
    protected={str(p.relative_to(ROOT)):sha(p) for p in retained if p.is_file()}
    summary=dict(episode_id=episode_id,directory=str(target),final_files=len(final),cleanup_files=len(cleanup),cleanup_bytes=sum(p.stat().st_size for p in cleanup),protected_files=len(protected))
    if dry_run:return summary
    if ready:
        for item in final:
            destination=target/(ready['video_filename'] if item.name=='sample.mp4' else item.name)
            if not destination.is_file() or sha(destination)!=sha(item):raise ValueError('Prepared release differs from working source; create a revision')
    else:ready=prepare(episode_id,slot)
    video_name=ready['video_filename']
    target.mkdir(parents=True,exist_ok=True);audit=target/'audit';audit.mkdir(exist_ok=True)
    manifest=[]
    for p in final:
        destination=target/(video_name if p.name=='sample.mp4' else p.name)
        import shutil
        shutil.copy2(p,destination)
        digest=sha(p)
        if sha(destination)!=digest:raise ValueError('Archive copy hash mismatch')
        manifest.append(dict(file=destination.name,bytes=p.stat().st_size,sha256=digest))
    publication=json.loads((target/'publication.json').read_text(encoding='utf-8'))
    (target/'title.txt').write_text(publication['title']+'\n',encoding='utf-8')
    (target/'tags.txt').write_text('\n'.join(publication.get('tags',[]))+'\n',encoding='utf-8')
    (audit/'protected-files.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf-8')
    backup=audit/'work-history.zip';clean_manifest=[]
    with zipfile.ZipFile(backup,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for p in sorted(cleanup):
            digest=sha(p);arc=p.relative_to(ROOT).as_posix();z.write(p,arc)
            clean_manifest.append(dict(file=arc,bytes=p.stat().st_size,sha256=digest))
    with zipfile.ZipFile(backup) as z:
        bad=z.testzip()
        if bad:raise ValueError('Recovery ZIP CRC failed: '+bad)
        for item in clean_manifest:
            if hashlib.sha256(z.read(item['file'])).hexdigest()!=item['sha256']:raise ValueError('Recovery ZIP hash mismatch')
    (audit/'cleanup-manifest.json').write_text(json.dumps(clean_manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    # Verify retained sources before deleting only individually enumerated work files.
    for name,digest in protected.items():
        if sha(ROOT/name)!=digest:raise ValueError('Protected file changed: '+name)
    skipped=[];deleted_bytes=0;deleted_files=0
    for p in sorted(cleanup):
        size=p.stat().st_size
        try:safe(p,ROOT).unlink();deleted_files+=1;deleted_bytes+=size
        except PermissionError:skipped.append(str(p))
    for p in final:
        if sha(target/(video_name if p.name=='sample.mp4' else p.name))!=sha(p):raise ValueError('Final artifact changed before move')
        try:safe(p,source).unlink()
        except PermissionError:skipped.append(str(p))
    for folder in sorted([p for p in source.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True):
        safe(folder,ROOT/'episodes')
        if not any(folder.iterdir()):folder.rmdir()
    for name,digest in protected.items():
        if sha(ROOT/name)!=digest:raise ValueError('Protected file changed after cleanup: '+name)
    source.mkdir(parents=True,exist_ok=True)
    receipt=dict(**summary,state='published',relative_directory=target.relative_to(release_root(ROOT)).as_posix(),video_filename=video_name,published=True,edition_slot=slot,counts_toward_daily_main_limit=ep.get('counts_toward_daily_main_limit',slot!='temporary'),publication_evidence=publication_evidence or 'User confirmed publication in current Codex conversation; no platform URL supplied',
        completed_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),recovery_zip=str(backup),archive_files=manifest,
        deleted_work_files=deleted_files,deleted_work_bytes=deleted_bytes,skipped_locked_files=skipped,recovery_zip_bytes=backup.stat().st_size)
    if publication_evidence:receipt.update(platform=publication_evidence['receipt'],submitted=True,upload_backend='codex-upload')
    elif ready.get('platform'):receipt.update(platform=ready['platform'],submitted=True)
    (target/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    (source/'release.json').write_text(json.dumps(dict(episode_id=episode_id,directory=str(target),relative_directory=receipt['relative_directory'],published=True,video_filename=video_name),ensure_ascii=False,indent=2),encoding='utf-8')
    if ep.get('model_alert_id') and (target/'publication-verified.json').exists():
        from model_alerts import mark_published
        mark_published(ep['model_alert_id'],target)
    release_logs=ROOT/'logs/releases';release_logs.mkdir(exist_ok=True)
    with (release_logs/f'{date}.jsonl').open('a',encoding='utf-8') as output:
        output.write(json.dumps(dict(episode_id=episode_id,directory=str(target),published=True,confirmation_source='public_platform_verification' if publication_evidence else 'user',completed_at=receipt['completed_at']),ensure_ascii=False)+'\n')
    status_text='平台公开核验已发布。' if publication_evidence else '用户确认已发布。'
    platform_text=('平台地址：'+publication_evidence['receipt'].get('url','')+'；账号与标题已公开核验。') if publication_evidence else '平台地址未提供，未虚构 BV 号；标签为本对话建议，未声称已核验用户实际投稿设置。'
    (target/'README.md').write_text('# '+publication['title']+'\n\n发布状态：'+status_text+'\n\n- '+video_name+'：最终视频\n- cover-4x3.png / cover-16x9.png：封面\n- title.txt / description.txt / tags.txt：发布文案及建议标签\n- script.txt / spoken_script.txt：显示稿与配音稿\n- episode.json / captions.json / timings.json：来源及字幕时间资料\n- audit/work-history.zip：已清理工作残留的恢复包，含旧样片和渲染记录；无需上传平台。\n\n'+platform_text+'\n',encoding='utf-8')
    if ep.get('alert_id'):
        from reset_alerts import mark_release
        mark_release(ep['alert_id'],target,published=True)
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');p.add_argument('--slot',choices=['morning','noon','night','temporary'],required=True);p.add_argument('--published',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    print(json.dumps(finalize(a.episode,a.slot,a.published,a.dry_run),ensure_ascii=False,indent=2))
