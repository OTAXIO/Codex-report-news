"""Published temporary events remain eligible for clearly labelled main-edition recaps."""
import datetime as dt,re
from pathlib import Path
import news_video as n
from project_paths import release_root
from layout_policy import is_overview

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
    if ep.get('edition_slot') not in {'morning','noon','night'}:return
    existing={s.get('event_key') for s in ep['scenes']}
    for event in recap_candidates(root):
        if event['event_key'] in existing or event.get('original_event_key') in existing:continue
        scene=dict(event['scene']);scene.update(id='recap-'+event['episode_id'],section='AI 动态',title='重点回顾｜'+scene['title'],short_title='回顾 '+scene.get('short_title',scene['title']),editorial_role='recap',recap_of=event['url'],event_key=event['event_key'])
        scene['narration']='回顾此前的重要动态。据当时的原始消息，'+scene['narration']
        scene['selection_reason']='Important verified temporary event also included in scheduled main edition as a recap'
        index=next((i for i,s in enumerate(ep['scenes']) if s.get('section','').startswith(('国内','国际'))),len(ep['scenes']))
        ep['scenes'].insert(index,scene)

def validate_recap(scene,ep,root=None):
    if ep.get('edition_slot') not in {'morning','noon','night'}:raise ValueError('Recaps are for scheduled main editions only')
    event=next((e for e in recap_candidates(root) if e['event_key']==scene.get('event_key') and e['url']==scene.get('recap_of')),None)
    if not event or event['scene']['item_id']!=scene.get('item_id'):raise ValueError('Recap requires a verified published temporary event within 24 hours')
    if '回顾' not in scene.get('narration','') or scene.get('published')!=event['published']:raise ValueError('Recap must keep attribution, original time and recap wording')
