"""Edition overview, sequential folios and clean cover metadata."""
import math,re

# 2026-11-28 (user): when the stories do not fit on one overview page, continue on more
# overview pages instead of dropping them. Each page holds at most this many cards.
OVERVIEW_PER_PAGE=4

def is_overview(scene):
    return scene.get('scene_type')=='overview' or scene.get('id') in {'guide','overview'} or scene.get('section') in {'导览','概览'} or (scene.get('id')=='intro' and ('导览' in scene.get('title','') or '概览' in scene.get('title','') or scene.get('narration')=='这是本视频的导览。'))

def folio_numbers(scenes):
    """Overview pages form one leading block numbered 00; body pages count from 01."""
    positions=[i for i,s in enumerate(scenes) if is_overview(s)]
    if positions!=list(range(len(positions))):raise ValueError('Overview pages must form one block at the start')
    return [0]*len(positions)+list(range(1,len(scenes)-len(positions)+1))

def overview_group(scene):
    section=scene.get('section','')
    if scene.get('game') or section.startswith('游戏'):return '游戏资讯'
    if section.startswith('国内'):return '国内新闻'
    if section.startswith('国际'):return '国际新闻'
    if section.startswith('AI') or scene.get('source_type') in {'leader_x','official_x'}:return 'AI 动态'
    return section or '重点新闻'


def overview_bucket(scene):
    st=scene.get('scene_type');seg=scene.get('segment')
    if st=='activity_calendar':return 'activity_calendar'
    if st=='community_pulse' or seg=='community':return 'community'
    if st=='activity' or seg=='activities':return 'activities'
    if st=='briefs' or seg=='briefs':return 'briefs'
    if st=='github_trending' or seg=='github':return 'github'
    if st=='rumor' or seg=='rumor':return 'rumor'
    return overview_group(scene)


def _is_global_game(scene):
    return bool(scene.get('game') and str(scene.get('game_region') or 'cn').strip().casefold()=='global')


def overview_category(scene,index,series=None):
    if not series:return overview_group(scene)
    if index==0:return '重磅头条'
    if _is_global_game(scene):return '国际服动态'
    st=scene.get('scene_type');seg=scene.get('segment')
    if st=='activity_calendar':return '全活动DDL'
    if st=='activity' or seg=='activities':return '重点活动'
    if st=='community_pulse' or seg=='community':return '玩家热议'
    if st=='rumor' or seg=='rumor':return '传闻动态'
    if st=='briefs' or seg=='briefs':return '今日快讯'
    if st=='github_trending' or seg=='github':return 'GitHub热门'
    if seg=='media':return '媒体速递'
    return '今日情报' if series in {'arknights','endfield'} else '官方动态'


def overview_highlights(scenes,limit=None):
    """Keep story order while representing actual sections/segments, prioritizing CN game content over global."""
    unique=[];seen=set()
    for scene in scenes:
        # Multi-page activity calendars are one overview entry.
        key='activity_calendar' if scene.get('scene_type')=='activity_calendar' else scene.get('event_key') or scene.get('item_id') or scene.get('id')
        if key in seen:continue
        seen.add(key);unique.append(scene)
    if limit is None:limit=len(unique)
    chosen=[];groups=set()
    for i,scene in enumerate(unique):
        if _is_global_game(scene):continue
        bucket=overview_bucket(scene)
        if bucket not in groups and len(chosen)<limit:chosen.append(i);groups.add(bucket)
    for i,scene in enumerate(unique):
        if len(chosen)>=limit:break
        if i not in chosen and not _is_global_game(scene):chosen.append(i)
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
    useful=[s for s in sentences if not s.startswith(('接下来是','先来看','先看','来看','最后来看','最后看','接下来看','回顾此前的重要动态','这是本视频的导览'))]
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
    guides=[s for s in ep['scenes'] if is_overview(s)]
    if not guides:return
    guide=guides[0]
    for fact in [f for g in guides for f in g.get('facts',[])]:
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


def paginate(items,per_page=OVERVIEW_PER_PAGE):
    """Split into the fewest pages of at most per_page items, as evenly as possible (5 -> 3+2)."""
    if not items:return []
    pages=math.ceil(len(items)/per_page);size,extra=divmod(len(items),pages);out=[];i=0
    for n in range(pages):
        step=size+(n<extra);out.append(items[i:i+step]);i+=step
    return out


def spoken_item(fact,scene):
    """Short spoken label for a continuation page, taken from the story's own navigation title."""
    label=(scene.get('short_title') or fact['title']).strip()
    subject=fact.get('subject')
    if subject and label.casefold().startswith(subject.casefold()) and len(label)>len(subject)+1:label=label[len(subject):]
    return re.sub(r'^[\s｜|:：]+','',label).replace('｜',' ')


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
    from edition_series import series_of
    series=series_of(ep)
    highlights,count=overview_highlights(body)
    facts=[]
    for idx,s in enumerate(highlights):
        value=overview_title(s,bool(ep.get('overview_subject_policy')))
        title,subject=value if isinstance(value,tuple) else (value,None)
        facts.append(dict(title=title,subject=subject,detail=overview_detail(s),category=overview_category(s,idx,series),scene_id=s['id']))
    series_titles={'ai':'AI早报｜今日核心看点','arknights':'明日方舟｜今日情报与活动DDL','endfield':'终末地｜今日情报与活动DDL'}
    guide=dict(id=existing['id'] if existing else 'overview',scene_type='overview',section='概览',
               title=series_titles.get(series,'本期新闻导览'),short_title='导览',
               lead=overview_lead(body,ep.get('edition_slot')=='temporary'),facts=facts,narration='这是本视频的导览。',
               hold_after_seconds=2.0,show_source=False,overview_generated=True,overview_schema_version=3,
               total_stories=count,footer_note='本期重点将按正文顺序展开。')
    if series:
        # Series videos open with an engaging 1-3 sentence hook summarizing the lead news and key highlights.
        hook=re.sub(r'\s+','',str(ep.get('hook') or ''))
        if not 8<=len(hook)<=110 or re.search(r'(?:本视频|本期|新闻)的?导览',hook) or not hook.endswith(('。','！','？')):
            raise ValueError('HOOK_REQUIRED: editorial needs "hook", 1-3 punchy sentences (8-110 chars) summarizing the lead news and key highlights, ending in punctuation')
        guide.update(narration=hook,lead=hook,hold_after_seconds=0.6)
    pages=paginate(facts)
    by_id={s['id']:s for s in body}
    out=[];offset=0
    for n,page in enumerate(pages):
        if n==0:item=dict(guide,facts=page)
        else:
            spoken='、'.join(spoken_item(f,by_id[f['scene_id']]) for f in page)
            item=dict(guide,id=f"{guide['id']}-{n+1}",title=guide['title']+'（续）',short_title='导览（续）',facts=page,
                      lead='本期还有这些内容。',narration='本期还有：'+spoken+'。',hold_after_seconds=0.8)
        item.update(overview_page=n+1,overview_pages=len(pages),overview_offset=offset);offset+=len(page)
        out.append(item)
    if existing:existing.clear();existing.update(out[0]);out[0]=existing
    first=next((i for i,s in enumerate(scenes) if is_overview(s)),0)
    scenes[:]=[s for s in scenes if not is_overview(s)]
    scenes[first:first]=out
    validate_overview(ep)


def cover_footer(brief):
    text=brief.get('footnote','模型发布速报')
    text=re.sub(r'(?<![0-9])(?:20[0-9]{2}[-./])?[0-9]{1,2}[-./月][0-9]{1,2}日?(?![0-9])','',text).strip(' ·｜|-')
    return text or '模型发布速报'
