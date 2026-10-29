"""Current news delivery rules, shared by export and upload boundaries."""
import json,math,subprocess
from pathlib import Path

FIXED_TAGS=['明日方舟','终末地']

ORDER_VERSION=3
MAJOR_CATEGORIES={'model_release','product_launch','quota_reset','game_update'}

def event_id(scene):
    return scene.get('event_key') or scene.get('item_id') or scene['id']

def is_game(scene):
    return bool(scene.get('game') or scene.get('section','').startswith('游戏'))

def is_major(scene,root=None):
    """Editorial semantic review is explicit; keywords never grant priority."""
    review=scene.get('importance_review') or {}
    if not review:return False
    if not (review.get('verified') is True and review.get('category') in MAJOR_CATEGORIES
            and review.get('reason') and review.get('quote') and review.get('source_url')==scene.get('source_url')):
        raise ValueError('Major news needs a semantic importance_review, source URL, exact quote and reason')
    if root is not None:
        # Bind review to existing local source evidence, not the editor's claim.
        texts=[]
        for folder in ['articles','leader-posts','game-items']:
            path=Path(root)/'data'/folder/(scene.get('item_id','')+'.json')
            if path.is_file():
                record=json.loads(path.read_text(encoding='utf-8'))
                for key in ['text','original_text','summary','official_body']:
                    value=record.get(key)
                    if value:texts.append('\n'.join(value) if isinstance(value,list) else str(value))
        if review['quote'] not in '\n'.join(texts):
            raise ValueError('Major news quote is absent from archived source evidence')
    return True

def apply_story_order(episode,root=None):
    """One order, after recaps/leaders merge and before overview/voice/timings."""
    if episode.get('edition_slot') not in {'morning','night'}:return
    from layout_policy import is_overview
    guides=[s for s in episode['scenes'] if is_overview(s)]
    groups={}
    for scene in episode['scenes']:
        if not is_overview(scene):groups.setdefault(event_id(scene),[]).append(scene)
    if not groups:raise ValueError('No body news to order')
    major=[key for key,pages in groups.items() if any(is_major(s,root) for s in pages)]
    games=[key for key,pages in groups.items() if is_game(pages[0])]
    # Editor ranks equally eligible stories by input order. A plain AI cover
    # cannot displace available games; choose the lead before making artwork.
    requested=episode.get('lead_event_id')
    company_keys=[k for k,v in groups.items() if v[0].get('source_type')!='leader_x']
    eligible=major or games or company_keys or list(groups)
    if requested and requested not in eligible:raise ValueError('lead_event_id must name a verified major event, or a game when available')
    lead=requested or eligible[0]
    remaining=[key for key in groups if key not in major and key not in games and key!=lead]
    leaders=[key for key in remaining if groups[key][0].get('source_type')=='leader_x']
    companies=[key for key in remaining if key not in leaders]
    ai=[]
    for key in companies:
        ai.append(key);company=str(groups[key][0].get('company','')).casefold()
        related=[k for k in leaders if company and str(groups[k][0].get('company','')).casefold()==company]
        ai.extend(related);leaders=[k for k in leaders if k not in related]
    ai+=leaders
    order=list(dict.fromkeys([lead]+major+games+ai))
    body=[s for key in order for s in groups[key]]
    for scene in body:
        scene['navigation_group']='headline' if event_id(scene) in major else 'games' if is_game(scene) else 'ai'
        old=scene.pop('module_intro_text',None)
        if old and scene.get('narration','').startswith(old):scene['narration']=scene['narration'][len(old):]
    previous=None
    for scene in body:
        group=scene['navigation_group']
        if group!=previous:
            intro=''
            # Do not duplicate an authored or old generated module preamble.
            if group=='games':intro=('先来看游戏资讯。' if previous is None else '接下来是游戏资讯。')
            elif group=='ai' and previous is not None:intro='接下来是AI动态。'
            if intro and not scene.get('narration','').startswith(('接下来是游戏资讯','先来看游戏资讯','接下来是AI动态')):
                scene['module_intro_text']=intro;scene['narration']=intro+scene.get('narration','')
        previous=group
    episode['scenes']=guides+body
    episode['lead_event_id']=lead
    episode['story_order']=dict(version=ORDER_VERSION,event_ids=order,major_event_ids=major,
                               default_order=['games','ai'],lead_event_id=lead)

def validate_lead_contract(episode,publication=None,cover=None):
    from layout_policy import validate_overview
    validate_overview(episode)
    if not episode.get('story_order'):return  # Frozen historical episodes.
    from layout_policy import is_overview
    body=[s for s in episode['scenes'] if not is_overview(s)]
    lead=episode['lead_event_id']
    if not body or event_id(body[0])!=lead:raise ValueError('First body story differs from lead_event_id')
    actual=[]
    for scene in body:
        key=event_id(scene)
        if not actual or actual[-1]!=key:actual.append(key)
    if actual!=episode['story_order']['event_ids']:
        raise ValueError('Body story order changed after the canonical editorial plan')
    for name,value in [('publication',publication),('cover',cover)]:
        if value is not None and value.get('lead_event_id')!=lead:raise ValueError(name+' lead_event_id differs from the first story')
    guide=next((s for s in episode['scenes'] if is_overview(s)),None)
    if guide and (not guide.get('facts') or guide['facts'][0].get('scene_id')!=body[0]['id']):
        raise ValueError('First overview highlight must match the lead story')

def config(root):
    path=Path(root)/'config.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}

def tags(values):
    # Reserve two mandatory tags and one platform activity slot.
    return FIXED_TAGS+list(dict.fromkeys(t for t in values if t not in FIXED_TAGS))[:7]

def validate_video(root,video):
    cfg=config(root)
    if not cfg.get('production',{}).get('minimum_duration_exclusive_seconds'):return None
    ff=cfg.get('voice',{}).get('qwen3',{}).get('ffmpeg_executable','ffmpeg')
    probe=Path(ff).with_name('ffprobe.exe' if str(ff).endswith('.exe') else 'ffprobe')
    p=subprocess.run([str(probe),'-v','error','-show_entries','format=duration:stream=codec_type,duration','-of','json',str(video)],capture_output=True,text=True,check=True)
    data=json.loads(p.stdout);duration=float(data['format']['duration'])
    video_stream=next((s for s in data.get('streams',[]) if s.get('codec_type')=='video'),None)
    if video_stream is None:raise ValueError('Formal news needs an actual video stream')
    actual=min(duration,float(video_stream.get('duration',duration)))
    minimum=cfg['production']['minimum_duration_exclusive_seconds']
    if not math.isfinite(actual) or actual<=minimum:raise ValueError('Formal news MP4 must exceed 30.0 seconds; enrich the sourced content and regenerate, never pad or edit metadata')
    return dict(duration=actual,minimum_exclusive=minimum,ok=True)

def validate_content(episode):
    if episode.get('edition_slot') not in {'morning','night'}:return
    body=[s for s in episode['scenes'] if s.get('scene_type')!='overview']
    if any(s.get('section','').startswith(('国内','国际')) for s in body):raise ValueError('New main editions contain AI and game news only; social news removed')
    seen={}
    for s in body:
        event=s.get('event_key') or s.get('item_id') or s.get('id')
        if event in seen:
            previous=seen[event]
            if not (s.get('game') and s.get('item_id') and s.get('item_id')==previous.get('item_id') and isinstance(s.get('page_number'),int) and isinstance(previous.get('page_number'),int) and s['page_number']>previous['page_number']):raise ValueError('Duplicate event across sources/languages; same-story pages need explicit page numbers')
        seen[event]=s
        if s.get('game') or s.get('section','').startswith('游戏'):
            if not s.get('event_key'):raise ValueError('Game news needs a reviewed cross-source event key; translated announcements are one event')
            if s.get('game') not in {'arknights','endfield'}:raise ValueError('Unsupported game')
            if not s.get('game_region') or s.get('game_topic') not in {'update','event','other'}:raise ValueError('Game news needs verified region and topic')
        # Module ranges follow actual scene order, including a headline group.
    first=next((s for s in body if s.get('game')),None)
    if first and episode.get('production_policy_version',0)<3 and not first['narration'].startswith('接下来是游戏资讯'):
        first['narration']='接下来是游戏资讯，先来看'+('明日方舟。' if first['game']=='arknights' else '明日方舟：终末地。')+first['narration']
    validate_lead_contract(episode)

def modules(episode,offsets,duration):
    if episode.get('edition_slot')=='temporary':return [('temporary','临时新闻',0,duration)]
    if any(is_game(s) for s in episode['scenes']):
        from layout_policy import is_overview
        labels={'headline':'头条','games':'游戏资讯','ai':'AI 动态'};runs=[]
        for i,s in enumerate(episode['scenes']):
            if is_overview(s):continue
            key=s.get('navigation_group') or ('games' if is_game(s) else 'ai')
            start=offsets[i]['start'] if runs else 0
            if runs and runs[-1][0]==key:continue
            if runs:runs[-1][3]=start
            runs.append([key,labels[key],start,duration])
        # IDs must stay unique even for historical discontiguous modules.
        counts={};out=[]
        for key,label,start,end in runs:
            counts[key]=counts.get(key,0)+1
            out.append((key if counts[key]==1 else key+'-'+str(counts[key]),label,start,end))
        return out
    # Historical layouts stay readable; new imports reject social stories.
    social=next((i for i,s in enumerate(episode['scenes']) if s.get('section','').startswith(('国内','国际'))),None)
    if social is None:return [('ai','AI 动态',0,duration)]
    return ([('ai','AI 动态',0,offsets[social]['start'])] if social else [])+[('news','国内外重点新闻',offsets[social]['start'],duration)]
