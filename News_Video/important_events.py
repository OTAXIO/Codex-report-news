"""Published temporary events remain eligible for clearly labelled main-edition recaps."""
import datetime as dt,re
from pathlib import Path
import news_video as n
from project_paths import release_root
from layout_policy import is_overview

MAIN_SLOTS={'morning','noon','night'}

def daily_main_history(root,day):
    """Successful main exports record each event, even before approval.

    Temporary bulletins do not consume it. Use release receipts as well as the
    ledger so an older partial log cannot re-enable recaps in later editions.
    """
    from used_news import recent_records
    root=Path(root);found=[]
    when=dt.datetime.combine(dt.date.fromisoformat(day),dt.time(23,59),tzinfo=dt.timezone(dt.timedelta(hours=8)))
    for record in recent_records(root,days=1,now=when):
        identity=record.get('episode_id','')
        slot=record.get('edition_slot')
        if not slot:
            match=re.search(r'(morning|noon|night|evening)(?:-v\d+)?$',identity)
            slot=match.group(1) if match else None
            if slot=='evening':slot='night'
        date=record.get('edition_date')
        if not date:
            match=re.search(r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})',identity)
            date='-'.join(match.groups()) if match else None
        if slot in MAIN_SLOTS and date==day and (record.get('video_sha256') or record.get('event') in {'edition_exported','revision_exported'}):
            found.append(dict(edition_slot=slot,edition_key=record.get('edition_key'),episode_id=identity,exported_at=record.get('generated_at'),news=record.get('news') or []))
    for path in release_root(root).glob('*/release.json'):
        receipt=n.load(path)
        if receipt.get('edition_slot') not in MAIN_SLOTS or receipt.get('edition_date')!=day:continue
        if not (path.parent/receipt.get('video_filename','sample.mp4')).is_file():continue
        episode_path=path.parent/'episode.json'
        scenes=n.load(episode_path).get('scenes',[]) if episode_path.exists() else []
        found.append(dict(edition_slot=receipt['edition_slot'],edition_key=receipt.get('edition_key'),episode_id=receipt.get('episode_id'),exported_at=receipt.get('prepared_at'),news=scenes))
    return found

def event_keys(item):
    from used_news import canonical_url
    result=set()
    for value in [item.get('event_key'),item.get('original_event_key')]:
        if value:result.add('event:'+value)
    if item.get('item_id'):result.add('id:'+item['item_id'])
    value=item.get('source_url') or item.get('url')
    if value:result.add('url:'+canonical_url(value))
    return result

def recap_allowed_for_event(event,ep,root=None):
    if ep.get('edition_slot') not in MAIN_SLOTS:return False
    day=ep.get('edition_date') or dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
    identity=event_keys(event)|event_keys(event['scene'])
    history=[r for r in daily_main_history(root or n.ROOT,day) if any(identity&event_keys(item) for item in r['news'])]
    if not history:return True
    def order(row):
        value=row.get('exported_at')
        if value:
            try:return dt.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
            except (ValueError,TypeError):pass
        hour={'morning':6,'noon':12,'night':18}[row['edition_slot']]
        return dt.datetime.fromisoformat(day+f'T{hour:02}:00:00+08:00').timestamp()
    # The first main edition for THIS EVENT may recap it; other new events in
    # later main editions remain eligible. Same-slot revisions stay idempotent.
    return min(history,key=order)['edition_slot']==ep['edition_slot']

def entries(root=None):
    root=Path(root or n.ROOT);found=[]
    for p in release_root(root).glob('*/release.json'):
        receipt=n.load(p);directory=p.parent
        if not receipt.get('published') or receipt.get('edition_slot')!='temporary' or not (directory/'publication-verified.json').is_file():continue
        proof=n.load(directory/'publication-verified.json')
        if proof.get('state')!='published' or not proof.get('receipt',{}).get('bvid'):continue
        ep=n.load(directory/'episode.json');scenes=[s for s in ep['scenes'] if not is_overview(s)]
        if not scenes:continue
        first=scenes[0];kind='reset' if ep.get('alert_id') else 'model_release' if ep.get('temporary_kind')=='official_model_release' else None
        model=re.search(r'GPT[- ]?\d+(?:\.\d+)*(?: (?:Terra|Astra|Sol))?',ep.get('title',''),re.I)
        # Compatibility for the verified user-commissioned Terra launch, without editing its release.
        if kind is None and first.get('source_type')=='official_x' and model and re.search(r'发布|release|introduc',ep.get('title',''),re.I):kind='model_release'
        if kind is None:continue
        event=ep.get('event_key') or first.get('event_key')
        if kind=='model_release' and model:event=first.get('company',first['publisher']).casefold()+':model-release:'+model.group().casefold().replace(' ','')
        found.append(dict(event_key=event,original_event_key=ep.get('event_key') or first.get('event_key'),kind=kind,episode_id=ep['id'],url=proof['receipt']['url'],published=first['published'],title=ep['title'],scene=first))
    return found

def recap_candidates(root=None,now=None):
    now=now or dt.datetime.now(n.UTC);result=[]
    for event in entries(root):
        stamp=dt.datetime.fromisoformat(event['published'])
        if dt.timedelta(0)<=now-stamp<=dt.timedelta(hours=24):result.append(event)
    return result

def prepare_main_recaps(ep,root=None):
    if ep.get('edition_slot') not in MAIN_SLOTS:return
    events=recap_candidates(root)
    blocked=[e for e in events if not recap_allowed_for_event(e,ep,root)]
    ep['recap_policy']=dict(frequency='once_per_event_per_beijing_date',skipped_event_keys=[e['event_key'] for e in blocked])
    ep['scenes']=[s for s in ep['scenes'] if not (s.get('editorial_role')=='recap' and any(event_keys(s)&(event_keys(e)|event_keys(e['scene'])) for e in blocked))]
    existing=set().union(*(event_keys(s) for s in ep['scenes']))
    for event in events:
        if event in blocked:continue
        identity=event_keys(event)|event_keys(event['scene'])
        if identity&existing:continue
        scene=dict(event['scene']);scene.update(id='recap-'+event['episode_id'],section='AI 动态',title='重点回顾｜'+scene['title'],short_title='回顾 '+scene.get('short_title',scene['title']),editorial_role='recap',recap_of=event['url'],event_key=event['event_key'])
        scene['narration']='回顾此前的重要动态。据当时的原始消息，'+scene['narration']
        scene['selection_reason']='Important verified temporary event also included in scheduled main edition as a recap'
        index=next((i for i,s in enumerate(ep['scenes']) if s.get('section','').startswith(('国内','国际'))),len(ep['scenes']))
        ep['scenes'].insert(index,scene)
        existing.update(identity)

def validate_recap(scene,ep,root=None):
    if ep.get('edition_slot') not in {'morning','noon','night'}:raise ValueError('Recaps are for scheduled main editions only')
    event=next((e for e in recap_candidates(root) if e['event_key']==scene.get('event_key') and e['url']==scene.get('recap_of')),None)
    if not event or event['scene']['item_id']!=scene.get('item_id'):raise ValueError('Recap requires a verified published temporary event within 24 hours')
    if not recap_allowed_for_event(event,ep,root):raise ValueError('This event has already appeared in another main video on this Beijing date')
    if '回顾' not in scene.get('narration','') or scene.get('published')!=event['published']:raise ValueError('Recap must keep attribution, original time and recap wording')
