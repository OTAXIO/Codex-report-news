"""Prepare named deliverables in release before any upload; never publish here."""
import argparse,datetime as dt,hashlib,json,shutil,subprocess,re
from pathlib import Path
from project_paths import release_root

ROOT=Path(__file__).resolve().parent
SLOTS={'morning':'早间新闻','noon':'午间新闻','night':'晚间新闻','temporary':'临时新闻'}
FINAL_NAMES={
 'soundtrack.wav','audio-mix.json',
 'leader-audit.json','tibo-audit.json','ai-coverage-audit.json','sample.mp4','cover-bilibili.jpg','cover-16x10.png','cover-16x9.png','cover-4x3.png',
 'description.txt','script.txt','spoken_script.txt','publication.json','episode.json',
 'narration.wav','narration_原始.wav','narration.json','timings.json','captions.json',
 'scene-timings.json','progress.json','used-news-record.json','SPEECH_REVIEW.md',
 'check.json','ffprobe.json','progress-validation.json','verification-result.json',
 'transition-preview.png','delivery-manifest.json','voice_job.json','inference.yaml','cover.json','reset-alert.json'}

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def naming(date,slot,edition_timestamp=None,alert_id=None):
    date=dt.date.fromisoformat(date)
    if slot not in SLOTS:raise ValueError('Unknown edition slot')
    folder=f'{date:%Y_%m_%d}_{slot}'
    if slot=='temporary':
        if not edition_timestamp or not re.fullmatch(r'[a-f0-9]{12,64}',alert_id or ''):
            raise ValueError('Temporary news requires timestamp and stable alert ID')
        when=dt.datetime.fromisoformat(edition_timestamp)
        if when.tzinfo is None:raise ValueError('Temporary timestamp requires timezone')
        when=when.astimezone(dt.timezone(dt.timedelta(hours=8)))
        if when.date()!=date:raise ValueError('Temporary edition date mismatch')
        folder+='_'+when.strftime('%H%M%S')+'_'+alert_id
    return folder,f'{folder}_{SLOTS[slot]}.mp4'

def infer_slot(ep):
    if ep.get('edition_slot') in SLOTS:return ep['edition_slot']
    value=ep.get('edition_label',ep.get('footer_tag','')+' '+ep.get('title',''))
    for slot,label in SLOTS.items():
        if label in value:return slot
    raise ValueError('Set edition_slot to morning, noon, night or temporary')

def release_target(root,ep,slot):
    folder,name=naming(ep['edition_date'],slot,ep.get('edition_timestamp'),ep.get('temporary_event_id') or ep.get('alert_id'));target=release_root(root)/folder
    if (target/'release.json').exists():
        previous=json.loads((target/'release.json').read_text(encoding='utf-8'))
        if previous.get('episode_id')!=ep['id']:
            target=target/'revisions'/ep['id']
            revision=re.search(r'-v(\d+)$',ep['id'])
            suffix='v'+revision.group(1) if revision else ep['id']
            name=Path(name).stem+'_'+suffix+'.mp4'
    return target,name

def prepare(episode_id,slot=None,root=ROOT):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,95}',episode_id):raise ValueError('Use a safe lowercase episode ID')
    root=Path(root).resolve();source=(root/'episodes'/episode_id).resolve()
    if not source.is_relative_to(root/'episodes'):raise ValueError('Invalid episode path')
    if (source/'release.json').exists():raise ValueError('Edition already archived; use a new revision ID')
    ep=json.loads((source/'episode.json').read_text(encoding='utf-8'));slot=slot or infer_slot(ep)
    if ep['id']!=episode_id:raise ValueError('Episode ID does not match its directory')
    target,video_name=release_target(root,ep,slot)
    for required in ['sample.mp4','cover-4x3.png','cover-16x9.png','script.txt','publication.json','check.json','progress-validation.json']:
        if not (source/required).is_file():raise ValueError('Release is incomplete: '+required)
    check=json.loads((source/'check.json').read_text(encoding='utf-8-sig'))
    if not check.get('ok'):raise ValueError('Video check has not passed')
    timing=json.loads((source/'timings.json').read_text(encoding='utf-8'))
    from audio_mix import validate_release_mix
    validate_release_mix(source,ep.get('background_music_requirement'),timing['duration'])
    tested=json.loads((source/'progress-validation.json').read_text(encoding='utf-8'))
    if len(tested)!=len(ep['scenes']):raise ValueError('Not all news navigation segments were verified')
    old=json.loads((target/'release.json').read_text(encoding='utf-8')) if (target/'release.json').exists() else None
    if old and old.get('published'):raise ValueError('Published release is immutable; prepare a new revision directory explicitly')
    if old and ((target/'upload-attempt.json').exists() or old.get('state') in {'unknown','uploading','submitting','submitted','reviewing'}):
        raise ValueError('Existing upload attempt must be recovered/verified; do not reset release via prepare')
    if target.exists() and any(target.iterdir()) and (not old or old.get('episode_id')!=episode_id):
        raise ValueError('Release folder belongs to another edition/revision')
    target.mkdir(parents=True,exist_ok=True);files=[]
    for name in sorted(FINAL_NAMES):
        path=source/name
        if not path.is_file():continue
        out_name=video_name if name=='sample.mp4' else name
        destination=target/out_name;tmp=destination.with_name(destination.name+'.preparing')
        shutil.copy2(path,tmp)
        if digest(tmp)!=digest(path):raise ValueError('Copy hash mismatch: '+name)
        tmp.replace(destination)
        files.append(dict(file=out_name,bytes=destination.stat().st_size,sha256=digest(destination)))
    publication=json.loads((source/'publication.json').read_text(encoding='utf-8'))
    (target/'title.txt').write_text(publication['title']+'\n',encoding='utf-8')
    (target/'tags.txt').write_text('\n'.join(publication.get('tags',[]))+'\n',encoding='utf-8')
    receipt=dict(state='ready_for_upload',published=False,episode_id=episode_id,edition_slot=slot,
        edition_date=ep['edition_date'],directory=str(target),relative_directory=target.relative_to(release_root(root)).as_posix(),video_filename=video_name,
        prepared_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),archive_files=files,
        duration=timing['duration'],upload_source='release only',
        counts_toward_daily_main_limit=ep.get('counts_toward_daily_main_limit',slot!='temporary'))
    (target/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    (source/'release-target.json').write_text(json.dumps(dict(directory=str(target),video_filename=video_name),ensure_ascii=False,indent=2),encoding='utf-8')
    from upload_bridge import prepare as prepare_upload
    prepare_upload(target,root)
    return receipt

def migrate_video_name(directory):
    directory=Path(directory).resolve();receipt=json.loads((directory/'release.json').read_text(encoding='utf-8'))
    ep=json.loads((directory/'episode.json').read_text(encoding='utf-8'))
    slot=infer_slot(ep);_,name=naming(ep['edition_date'],slot,ep.get('edition_timestamp'),ep.get('temporary_event_id') or ep.get('alert_id'))
    old_name=receipt.get('video_filename','sample.mp4');source=directory/old_name;target=directory/name
    if source!=target and source.exists():
        before=digest(source)
        if target.exists():raise ValueError('Named video already exists; refusing overwrite')
        source.rename(target)
        if digest(target)!=before:raise ValueError('Renamed video hash mismatch')
    if not target.is_file():raise ValueError('Release video is missing')
    receipt['video_filename']=name;receipt['state']='published' if receipt.get('published') else 'ready_for_upload'
    receipt['relative_directory']=directory.relative_to(release_root(ROOT)).as_posix()
    for item in receipt.get('archive_files',[]):
        if item['file']==old_name:item['file']=name
    (directory/'release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    pointer=ROOT/'episodes'/receipt['episode_id']/'release.json'
    if pointer.exists():
        p=json.loads(pointer.read_text(encoding='utf-8'));p['video_filename']=name;p['relative_directory']=receipt['relative_directory']
        pointer.write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('episode');a.add_argument('--slot',choices=SLOTS)
    a=sub.add_parser('rename-existing');a.add_argument('directory')
    args=p.parse_args();result=prepare(args.episode,args.slot) if args.command=='prepare' else migrate_video_name(args.directory)
    print(json.dumps({k:v for k,v in result.items() if k!='archive_files'},ensure_ascii=False,indent=2))
