"""Successful exports -> Beijing-date JSONL ledger -> next-edition exclusions."""
import datetime as dt
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

CN=dt.timezone(dt.timedelta(hours=8))
ROOT=Path(__file__).resolve().parent
PROBE=Path('D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/ffprobe.exe')

def canonical_url(url):
    parts=urlsplit(url)
    query=[(k,v) for k,v in parse_qsl(parts.query) if not k.startswith('utm_') and k not in {'spm','from','source'}]
    return urlunsplit((parts.scheme.lower(),parts.netloc.lower(),parts.path.rstrip('/'),urlencode(query),''))

def keys(item):
    result=set()
    if item.get('item_id',item.get('id')):result.add('id:'+item.get('item_id',item.get('id')))
    url=item.get('url',item.get('source_url'))
    if url and (not item.get('event_key') or item['event_key']==canonical_url(url)):result.add('url:'+canonical_url(url))
    if item.get('event_key'):result.add('event:'+item['event_key'])
    title=item.get('source_title',item.get('title',''))
    title=re.sub(r'[^\w\u4e00-\u9fff]','',title.lower())
    if title:result.add('title:'+title)
    return result

def normalize_record(record):
    """Read legacy export/association rows without rewriting audit history."""
    record=dict(record)
    episode_id=record.get('episode_id')
    if not record.get('edition_key'):
        record['edition_key']=re.sub(r'-v\d+$','',episode_id) if episode_id else 'legacy:'+hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    record.setdefault('news',[])
    return record


def recent_records(root=ROOT,days=7,now=None):
    now=now or dt.datetime.now(CN);today=now.astimezone(CN).date();records=[]
    for i in range(days):
        path=Path(root)/'logs/news-used'/f'{today-dt.timedelta(days=i)}.jsonl'
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.strip():records.append(normalize_record(json.loads(line)))
    return records

def exclude_used(items,records):
    seen=set();context={}
    for record in records:
        for item in record.get('news',[]):
            seen.update(keys(item));context.setdefault(item.get('event_key') or item.get('item_id') or item.get('url') or item.get('title'),item)
    fresh=[];excluded=[]
    for item in items:
        matched=keys(item)&seen
        if matched:excluded.append(dict(id=item['id'],title=item['title'],reason='already_in_successful_export',matched_keys=sorted(matched)))
        else:fresh.append(item)
    return fresh,excluded,list(context.values())

def record_export(directory,root=ROOT,now=None):
    directory=Path(directory);root=Path(root)
    episode=json.loads((directory/'episode.json').read_text(encoding='utf-8'))
    if episode.get('review_status','').startswith('local_sample') or episode.get('usage_tracking') is False:return None
    movie=directory/'sample.mp4'
    probe=subprocess.run([str(PROBE),'-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(movie)],capture_output=True,text=True,check=True)
    media=json.loads(probe.stdout)
    if {s['codec_type'] for s in media['streams']}!={'video','audio'}:raise ValueError('Incomplete export: audio/video required')
    timing=json.loads((directory/'timings.json').read_text(encoding='utf-8'))
    if abs(float(media['format']['duration'])-timing['duration'])>.15:raise ValueError('Incomplete export: duration mismatch')
    now=now or dt.datetime.now(CN);now=now.astimezone(CN)
    folder=root/'logs/news-used';folder.mkdir(parents=True,exist_ok=True)
    log=folder/f'{now.date()}.jsonl';lock=folder/'write.lock'
    sha=hashlib.sha256(movie.read_bytes()).hexdigest()
    edition_key=episode.get('edition_key',re.sub(r'-v\d+$','',episode['id']))
    db=sqlite3.connect(root/'data/news.sqlite3');db.row_factory=sqlite3.Row
    news=[]
    try:
        for scene in episode['scenes']:
            if not scene.get('item_id'):continue
            source=db.execute('SELECT title,kind FROM items WHERE id=?',(scene['item_id'],)).fetchone()
            if source is None:raise ValueError('Export refers to unknown collected news')
            news.append(dict(item_id=scene['item_id'],title=scene['title'],source_title=source['title'],
                url=canonical_url(scene['source_url']),event_key=scene.get('event_key',canonical_url(scene['source_url'])),
                kind=source['kind'],publisher=scene['publisher'],published=scene['published']))
    finally:db.close()
    with lock.open('x',encoding='utf-8') as lock_handle:
        lock_handle.close()
        try:
            records=recent_records(root,days=7,now=now)
            record=next((r for r in records if r.get('episode_id')==episode['id'] and r.get('video_sha256')==sha),None)
            if record is None:
                same=any(r['edition_key']==edition_key for r in records)
                record=dict(event='revision_exported' if same else 'edition_exported',edition_key=edition_key,
                    episode_id=episode['id'],edition_date=episode.get('edition_date'),
                    generated_at=now.isoformat(),timezone='Asia/Shanghai',video=str(movie.resolve()),
                    video_sha256=sha,title=episode['title'],news=news,submitted=False)
                record.update(edition_slot=episode.get('edition_slot'),edition_type=episode.get('edition_type','main'),
                    counts_toward_daily_main_limit=episode.get('counts_toward_daily_main_limit',episode.get('edition_slot')!='temporary'),alert_id=episode.get('alert_id'))
                with log.open('a',encoding='utf-8') as output:output.write(json.dumps(record,ensure_ascii=False)+'\n');output.flush()
            day=[normalize_record(json.loads(line)) for line in log.read_text(encoding='utf-8').splitlines() if line.strip()]
            unique={}
            for r in day:
                for item in r['news']:
                    key=item.get('event_key') or canonical_url(item.get('url','')) or item['item_id']
                    unique.setdefault(key,(item,r['edition_key']))
            lines=[f'# {now.date()} 已生成视频使用的新闻','',f'成功导出记录：{len(day)}；唯一新闻：{len(unique)}。修订不计为新一期。','', '| 新闻 | 来源 | 所属期次 |','|---|---|---|']
            for item,edition in unique.values():lines.append(f"| [{item['title']}]({item['url']}) | {item['publisher']} | {edition} |")
            (folder/f'{now.date()}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
            (directory/'used-news-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            return log
        finally:lock.unlink(missing_ok=True)
