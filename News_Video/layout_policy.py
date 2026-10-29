"""Edition overview, sequential folios and clean cover metadata."""
import re

def is_overview(scene):
    return scene.get('scene_type')=='overview' or scene.get('id') in {'guide','overview'} or scene.get('section') in {'导览','概览'} or (scene.get('id')=='intro' and ('导览' in scene.get('title','') or '概览' in scene.get('title','') or scene.get('narration')=='这是本视频的导览。'))

def folio_numbers(scenes):
    positions=[i for i,s in enumerate(scenes) if is_overview(s)]
    if positions and positions!=[0]:raise ValueError('One overview is allowed and it must be first')
    return list(range(0 if positions else 1,len(scenes)+(0 if positions else 1)))

def overview_group(scene):
    section=scene.get('section','')
    if scene.get('game') or section.startswith('游戏'):return '游戏资讯'
    if section.startswith('国内'):return '国内新闻'
    if section.startswith('国际'):return '国际新闻'
    if section.startswith('AI') or scene.get('source_type') in {'leader_x','official_x'}:return 'AI 动态'
    return section or '重点新闻'


def overview_highlights(scenes,limit=4):
    """Keep story order while representing actual sections, never fill gaps."""
    unique=[];seen=set()
    for scene in scenes:
        key=scene.get('event_key') or scene.get('item_id') or scene.get('id')
        if key in seen:continue
        seen.add(key);unique.append(scene)
    chosen=[];groups=set()
    for i,scene in enumerate(unique):
        group=overview_group(scene)
        if group not in groups and len(chosen)<limit:chosen.append(i);groups.add(group)
    for i in range(len(unique)):
        if len(chosen)>=limit:break
        if i not in chosen:chosen.append(i)
    return [unique[i] for i in sorted(chosen)],len(unique)


def overview_detail(scene):
    if scene.get('overview_detail'):return scene['overview_detail'].strip()
    narration=scene.get('leader_content_narration') or scene.get('narration','')
    # Skip navigation/recap preambles, but retain the actual attributed claim,
    # qualifications and original sentence. Do not slice words or invent facts.
    sentences=[s.strip() for s in re.split(r'(?<=[。！？!?])\s*',narration) if s.strip()]
    useful=[s for s in sentences if not s.startswith(('接下来是','先来看','回顾此前的重要动态','这是本视频的导览'))]
    if useful:return useful[0]
    for fact in scene.get('facts',[]):
        if isinstance(fact,dict) and fact.get('detail'):return fact['detail'].strip()
    title=scene.get('title','').strip()
    return title.rstrip('。')+'。' if title else '正文将介绍这则消息的具体内容。'

def overview_subject(scene):
    if scene.get('game')=='arknights':return '明日方舟国服' if scene.get('game_region')=='cn' else '明日方舟英文国际服'
    if scene.get('game')=='endfield':return '终末地'
    context=' '.join(str(scene.get(k,'')) for k in ['title','narration','company','publisher','speaker_name','product'])
    # Product names take precedence: API, ChatGPT and Codex are not equivalent.
    names=['Codex','ChatGPT','GPT','OpenAI','Claude Code','Claude','Anthropic','DeepSeek','千问','Qwen','GLM','智谱','Kimi','MiniMax','Google','Gemini','WorkBuddy','腾讯','tibo']
    proposed=scene.get('overview_subject') or scene.get('product') or scene.get('speaker_name') or scene.get('company')
    if proposed and str(proposed).casefold() in context.casefold():return str(proposed)
    return next((name for name in names if re.search(re.escape(name),context,re.I)),None)

def overview_title(scene,strict=False):
    title=(scene.get('overview_title') or scene.get('title') or '').strip()
    if not strict:return title or '本期重点'
    subject=overview_subject(scene)
    if not subject:raise ValueError('OVERVIEW_SUBJECT_REQUIRED: '+scene['id'])
    # Only add a verified subject, never invent an action such as an increase.
    if subject.casefold() not in title.casefold():title=subject+'｜'+title
    event=title.replace(subject,'').strip(' ｜:：')
    if not event or re.sub(r'\s+','',event) in {'动态','消息','更新','API额度','模型更新','负责人发言','活动上线'}:
        raise ValueError('OVERVIEW_EVENT_REQUIRED: provide a concrete sourced action for '+scene['id'])
    return title,subject

def validate_overview(ep):
    if not ep.get('overview_subject_policy'):return
    body={s['id']:s for s in ep['scenes'] if not is_overview(s)}
    guide=next((s for s in ep['scenes'] if is_overview(s)),None)
    if not guide:return
    for fact in guide.get('facts',[]):
        scene=body.get(fact.get('scene_id'))
        if not scene:raise ValueError('OVERVIEW: invalid story reference')
        expected,subject=overview_title(scene,True)
        if fact.get('title')!=expected or fact.get('subject')!=subject or not fact.get('detail'):
            raise ValueError('OVERVIEW: subject/title/detail differs from the canonical story')
    first=next(iter(body),None)
    if not guide.get('facts') or guide['facts'][0].get('scene_id')!=first:raise ValueError('OVERVIEW: first item must match body 01')


def overview_lead(scenes,temporary=False):
    if temporary:return '本期速报聚焦这一事件，下方导览列出了正文将介绍的重点。'
    groups=list(dict.fromkeys(overview_group(s) for s in scenes))
    names=[{'AI 动态':'AI 领域的重点动态','国内新闻':'国内要闻','国际新闻':'国际要闻'}.get(g,g) for g in groups]
    if len(names)>1:return '本期我们先关注'+names[0]+'，随后梳理'+'与'.join(names[1:])+'。'
    return '本期我们将聚焦'+names[0]+'，带你了解相关消息的主要内容。'


def prepare_overview(ep,preferred=True):
    scenes=ep['scenes'];folio_numbers(scenes)
    if ep.get('alert_id') or not preferred or ep.get('include_overview') is False:return
    existing=next((s for s in scenes if is_overview(s)),None)
    body=[s for s in scenes if not is_overview(s)]
    if ep.get('overview_subject_policy'):
        for scene in body:
            _,subject=overview_title(scene,True)
            short=scene.get('short_title') or scene['title']
            if subject.casefold() not in short.casefold():scene['short_title']=subject+' '+short
    if not body:
        if existing:return
        raise ValueError('No news to overview')
    # Preserve a genuinely authored rich guide. Legacy auto-guides used empty
    # details and short navigation labels, so refresh those before voicing.
    if existing and not ep.get('story_order') and not existing.get('overview_generated') and sum(bool(isinstance(f,dict) and f.get('detail')) for f in existing.get('facts',[]))>1:
        existing.setdefault('lead',overview_lead(body,ep.get('edition_slot')=='temporary'));return
    highlights,count=overview_highlights(body)
    facts=[]
    for s in highlights:
        value=overview_title(s,bool(ep.get('overview_subject_policy')))
        title,subject=value if isinstance(value,tuple) else (value,None)
        facts.append(dict(title=title,subject=subject,detail=overview_detail(s),category=overview_group(s),scene_id=s['id']))
    guide=dict(id=existing['id'] if existing else 'overview',scene_type='overview',section='概览',title='本期新闻导览',short_title='导览',
               lead=overview_lead(body,ep.get('edition_slot')=='temporary'),facts=facts,narration='这是本视频的导览。',
               hold_after_seconds=2.0,show_source=False,overview_generated=True,overview_schema_version=2,
               total_stories=count,footer_note='本页展示本期重点，其余内容可通过底部导航查看。' if count>len(facts) else '本期重点将按正文顺序展开。')
    if existing:existing.update(guide)
    else:scenes.insert(0,guide)
    validate_overview(ep)


def cover_footer(brief):
    text=brief.get('footnote','模型发布速报')
    text=re.sub(r'(?<![0-9])(?:20[0-9]{2}[-./])?[0-9]{1,2}[-./月][0-9]{1,2}日?(?![0-9])','',text).strip(' ·｜|-')
    return text or '模型发布速报'
