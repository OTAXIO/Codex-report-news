"""Game activity calendar: every running activity, its deadline and its phases (2026-11-15).

Why: game editions missed in-game milestones — Endfield's 「丹青渡」 version had a dozen
activities running and several 第二阶段/内容更新 dates, Arknights opened the third stage of
「时间啊，向前！」 — because the collector keeps only a 100-character summary of each official
notice and the old ledger only remembered activities that already had a page.

Now `sync` reads the full text of every official notice of the last `max_source_age_days`,
extracts each activity window (start - end, or "版本更新维护前" resolved through the version)
and every phase node (第N段 / Part.N / Phase N / 活动内容更新时间 / 开放后续…) with the official
sentence it came from, and keeps them in data/activity-calendar.json until they end.

Every game edition then carries one 活动日历 page (`scene_type:"activity_calendar"`): the rows and
their countdowns come from the calendar, never from the writer; the narration must name every
activity that ends within 3 days and every phase that opens today or tomorrow, with its day.
A single activity may still get its own page (`scene_type:"activity"`, one per page, countdown).
When an edition has fewer than `min_body_pages` (5) message pages — 导览, 活动日历 and 玩家热议 not
counted — the most pressing calendar rows with a known deadline get their own page
(`scene_type:"activity"` + `calendar_key`, filled from the calendar) right before the 活动日历 page.

The production agent maintains the file every edition: `sync` rebuilds it from the notices and
deletes what has ended (a version-bound activity ends when the next version's maintenance starts);
`add` enters an activity the parser missed, `fix`/`hide` correct one.

CLI:
  python -B activities.py sync --series endfield     read official notices, update the calendar, delete ended rows
  python -B activities.py list --series endfield     running activities with days left and phases
  python -B activities.py fill --series endfield --pages 3   which rows need their own page with 3 message pages
  python -B activities.py add  --series endfield --name 「X」 --start-at <ISO> (--end-at <ISO>|--version 丹青渡|--open) --quote "<official sentence>" --item <item_id>
  python -B activities.py prune --series endfield    delete ended rows without a sync
  python -B activities.py fix  --series endfield --key <key> --json '{"end_at":"..."}'  correct an entry
  python -B activities.py hide --series endfield --key <key> --reason "..."  drop a false positive
  python -B activities.py version --series endfield --name 丹青渡 --end-at <ISO> --quote "<official sentence>" --item <item_id>
"""
from __future__ import annotations
import datetime as dt,json,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
UTC=dt.timezone.utc
BEIJING=dt.timezone(dt.timedelta(hours=8))
KINDS={'online':'线上活动','offline':'线下活动','collab':'联动活动'}
SCALES={'main':0,'minor':1}
STATE_ORDER={'ending':0,'ongoing':1,'upcoming':2}
CN_DIGITS='零一二三四五六七八九'
REGION_LABEL={'cn':'国服','global':'国际服'}
# Server time written as "服务器时间"/"server time" when a notice gives no offset.
SERVER_OFFSET={('arknights','cn'):8,('arknights','global'):-7,('endfield','cn'):8,('endfield','global'):8}
CALENDAR_SOURCES={'official_game_page','skland_capture','skland_browser','official_x'}

def chinese_number(n):
    """0-99 as spoken Chinese, for matching narration written for TTS."""
    if n<10:return CN_DIGITS[n]
    tens,ones=divmod(n,10)
    return ('' if tens==1 else CN_DIGITS[tens])+'十'+(CN_DIGITS[ones] if ones else '')

def spoken_dates(moment):
    m,d=moment.month,moment.day
    return {f'{m}月{d}日',f'{m}月{d}号',f'{chinese_number(m)}月{chinese_number(d)}日',f'{chinese_number(m)}月{chinese_number(d)}号'}

def status(start,end,reference):
    """Countdown for the screen, in Beijing calendar days."""
    now=reference.astimezone(BEIJING);s=start.astimezone(BEIJING);e=end.astimezone(BEIJING)
    upcoming=s>now;target=s if upcoming else e
    days=(target.date()-now.date()).days;verb='开启' if upcoming else '截止'
    if days<=1:lead,big,tail=('今天' if days<=0 else '明天'),target.strftime('%H:%M'),verb
    else:lead,big,tail='距'+verb+'还有',str(days),'天'
    same_year=s.year==e.year
    fmt=(lambda t:f'{t.month}月{t.day}日 {t:%H:%M}') if same_year else (lambda t:f'{t.year}年{t.month}月{t.day}日 {t:%H:%M}')
    return dict(phase='upcoming' if upcoming else 'running',days=max(days,0),urgent=not upcoming and days<=1,
                countdown=dict(lead=lead,big=big,tail=tail),label=lead+verb if days<=1 else f'{days}天后开启' if upcoming else f'还剩{days}天',
                window_label=fmt(s)+' – '+fmt(e),end_label=fmt(e)+' 截止',start_label=fmt(s)+' 开启')

# ---- single activity pages (2026-11-10) ----
def describe(scene,entry,check,reference,official_text):
    """Validate one activity page and return the block bound to the scene."""
    kind=entry.get('kind','online');scale=entry.get('scale','main')
    if kind not in KINDS:raise ValueError('ACTIVITY_KIND: kind is online, offline or collab')
    if scale not in SCALES:raise ValueError('ACTIVITY_SCALE: scale is main or minor (web/community mini activity)')
    if not str(entry.get('name','')).strip():raise ValueError('ACTIVITY_NAME: every activity page names its activity')
    facts=scene.get('facts',[])
    # The countdown band takes the top of the text column, so the page carries two points (how to join / what you get).
    if not 1<=len(facts)<=2 or any(len(str(f.get('detail','') if isinstance(f,dict) else '').strip())>54 for f in facts):
        raise ValueError('ACTIVITY_FACTS: an activity page has 1-2 facts, each detail at most 54 characters; dates go in activity_items, not in facts')
    for field,required in [('location',kind=='offline'),('partner',kind=='collab')]:
        value=str(entry.get(field,'')).strip()
        if required and not value:raise ValueError(f'ACTIVITY_{field.upper()}: a {kind} activity states its {field} as written by the official post')
        if value and value not in official_text:raise ValueError(f'ACTIVITY_{field.upper()}: "{value}" is not in the official text')
    start=dt.datetime.fromisoformat(check['start_at']);end=dt.datetime.fromisoformat(check['end_at'])
    info=status(start,end,reference)
    moment=start if info['phase']=='upcoming' else end
    if not any(token in scene.get('narration','') for token in spoken_dates(moment.astimezone(BEIJING))|spoken_dates(moment.astimezone(dt.datetime.fromisoformat(str(entry['end_at'])).tzinfo))):
        raise ValueError('ACTIVITY_DEADLINE_NOT_SPOKEN: say when "'+entry['name']+'" '+('starts' if info['phase']=='upcoming' else 'ends')+' ('+(info['start_label'] if info['phase']=='upcoming' else info['end_label'])+') in the narration')
    return dict(name=entry['name'].strip(),region=scene.get('game_region') or 'cn',kind=kind,kind_label=KINDS[kind],scale=scale,state=check['state'],
                location=str(entry.get('location','')).strip(),partner=str(entry.get('partner','')).strip(),
                start_at=check['start_at'],end_at=check['end_at'],item_id=entry.get('item_id'),**info)

def _region_rank(region):return 0 if str(region or 'cn').strip().casefold()=='cn' else 1

def sort_key(activity):return (_region_rank(activity.get('region','cn')),SCALES[activity['scale']],STATE_ORDER[activity['state']],activity['end_at'])

def arrange(episode):
    """Inside the slots they occupy: single activity pages in reporting order (CN first), then the calendar fill
    pages (CN first, most pressing first), then the 活动日历 page(s) in page order."""
    def key(s):
        if s.get('scene_type')=='activity_calendar':return (2,int(s.get('calendar_page') or s.get('page_number') or 1),0,0,'')
        if s.get('calendar_key'):return (1,_region_rank(s.get('game_region','cn')),s.get('calendar_rank',0),0,'')
        return (0,)+sort_key(s['activity'])
    slots=[i for i,s in enumerate(episode['scenes']) if s.get('activity') or s.get('scene_type')=='activity_calendar']
    ordered=sorted((episode['scenes'][i] for i in slots),key=key)
    for i,scene in zip(slots,ordered):episode['scenes'][i]=scene

def validate_pages(episode,max_pages,max_calendar_pages=3):
    """Episode-level rules for single-activity and 活动日历 pages; scenes already carry `activity`."""
    cal_count=sum(s.get('scene_type')=='activity_calendar' for s in episode['scenes'])
    if cal_count>max_calendar_pages:raise ValueError(f'ACTIVITY_CALENDAR: at most {max_calendar_pages} 活动日历 pages per edition')
    pages=[s for s in episode['scenes'] if s.get('activity')]
    if not pages:return
    if len(pages)>max_pages:raise ValueError(f'ACTIVITY_PAGES: at most {max_pages} activity pages; drop minor ones first')
    seen=set()
    for s in pages:
        key=(s['activity']['item_id'],s['activity']['name'])
        if key in seen:raise ValueError('ACTIVITY_DUPLICATE: '+s['activity']['name']+' has two pages')
        seen.add(key)
    news={s.get('item_id') for s in episode['scenes'] if s.get('item_id') and not s.get('activity') and s.get('scene_type')!='activity_calendar'}
    for s in pages:
        # A fill page shows one activity of a notice (often the version note) that may also be a news page.
        if s.get('item_id') in news and not s.get('calendar_key'):raise ValueError('ACTIVITY_DUPLICATE: '+s['activity']['name']+' is already a news page in this edition; keep one')
    body=[s for s in pages if (not episode.get('lead_event_id') or s.get('event_key')!=episode['lead_event_id']) and not s.get('calendar_key')]
    wanted=sorted(body,key=lambda s:sort_key(s['activity']))
    if [s['id'] for s in body]!=[s['id'] for s in wanted]:
        raise ValueError('ACTIVITY_ORDER: CN activities before global; within each, main activities first, mini web/community activities last, ending soon -> ongoing -> upcoming. Expected order: '+' / '.join(s['activity']['name'] for s in wanted))

# ---- reading official wording ----
MONTHS={m:i+1 for i,m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])}
CLOCK=r'(?:\s*(?:at\s*)?(\d{1,2})[:：](\d{2})(?:[:：](\d{2}))?)?'
NUMERIC=r'(?:(\d{4})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})\s*日?|(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]?|(\d{1,2})/(\d{1,2})(?=\s+\d{1,2}[:：]))'+CLOCK
ENGLISH=r'(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?)'+r',?'+CLOCK
VERSION_START=r'「([^」]{1,12})」\s*版本(?:更新)?(?:后|开启后|上线后)'
VERSION_END=r'(?:下次)?版本更新维护前|「[^」]{1,12}」\s*版本结束|before the next version update(?: and maintenance)?|until the next version update'
POINT=f'(?:{NUMERIC}|{ENGLISH}|{VERSION_START}|(?P<vend>{VERSION_END}))'
ZONE=r'(?:\s*[（(]\s*(?:服务器时间|server time|UTC\s*([+\-]\s*\d{1,2})|UTC)\s*[)）])?'
SEP=r'\s*(?:-|–|—|~|～|至|到|to)\s*'
RANGE=re.compile('(?P<a>'+POINT.replace('?P<vend>','')+')'+ZONE+SEP+'(?P<b>'+POINT.replace('?P<vend>','')+')'+ZONE,re.I)
SINGLE_POINT=re.compile('(?P<a>'+NUMERIC+'|'+ENGLISH+')'+ZONE,re.I)
POINT_RE=re.compile(POINT,re.I)
# Lines that introduce a later stage of an activity already being described.
PHASE_LABEL=re.compile(r'(<\s*第[一二三四五六七八九十\d]+段\s*>|第[一二三四五六七八九十\d]+(?:段|阶段|期)|Part\.?\s*\d+|Phase\s*\d+|预选期|招募期|后半|下半)',re.I)
PHASE_TIME=re.compile(r'(活动内容更新时间|内容更新时间|更新时间|开放后续|追加|开放第二|新增关卡开放)',re.I)
HEADING=re.compile(r'^\s*(?:[一二三四五六七八九十]+、|\d{1,2}\s*[\.、．]\s*|[○■◆●]\s*)?(.*?(?:「[^」]+」|【[^】]+】|\[[^\]]+\]).*)$')
SECTION=re.compile(r'^\s*(?:[一二三四五六七八九十]+、|\d{1,2}\s*[\.、．]\s*\S|○\s*「)')
BARE=re.compile(r'^\s*(?:◆\s*)?(【[^】]+】|「[^」]+」)\s*$')

GENERIC_HEADING={'活动时间','活动说明','活动规则','开放时间','活动奖励','参与方式','活动内容','奖励说明','注意事项','活动地址','活动介绍','更新时间','更新说明'}
NOTE_START=('·','※','注意','◆注意','暂','本次','该','将','均','如','若','以上','上述','期间','活动期间','博士','各位')

def is_heading(line):
    s=line.strip()
    core=re.findall(r'「([^」]+)」|【([^】]+)】',s)
    if core and all(_norm(a or b) in {_norm(g) for g in GENERIC_HEADING} for a,b in core):return False
    english=bool(re.match(r'^(?:\d{1,2}\s+)?\[[^\]]+\][^一-鿿]*$',s))   # 01 [ARKNIGHTS X MONSTER HUNTER] SIDESTORY: …
    return bool(HEADING.match(s)) and len(s)<=(110 if english else 60) and not s.startswith(NOTE_START) and '：' not in s and (english or not re.search(r':\s',s)) and not NOT_ACTIVITY.search(s) and not SINGLE_POINT.search(s)
NOT_ACTIVITY=re.compile(r'维护|补偿|兑奖|发放时间|过期|停机|预下载|Maintenance|Compensation|expire',re.I)

def _offset(game,region,zone):
    if zone:return int(zone.replace(' ',''))
    return SERVER_OFFSET.get((game,region),8)

def _point(groups,published,tz,default_end):
    """One date/time match -> aware datetime; a missing time is 00:00 (start) or 23:59:59 (end)."""
    y,mo,d,mo2,d2,mo3,d3,h,mi,s,em,ed,ey,eh,emi,es=groups[:16]
    if em:year,month,day,h,mi,s=ey,MONTHS[em[:3].lower()],ed,eh,emi,es
    else:year,month,day=(y,mo,d) if y else (None,mo2,d2) if mo2 else (None,mo3,d3)
    month,day=int(month),int(day)
    if year:year=int(year)
    else:year=published.year+(1 if month<published.month-6 else -1 if month>published.month+6 else 0)
    if h:return dt.datetime(year,month,day,int(h),int(mi),int(s or 0),tzinfo=tz)
    return dt.datetime(year,month,day,23,59,59,tzinfo=tz) if default_end else dt.datetime(year,month,day,tzinfo=tz)

def _resolve(text_point,published,tz,default_end,versions,game,region):
    """A start/end written as a date, as '「X」版本更新后' or as '版本更新维护前'."""
    m=POINT_RE.fullmatch(text_point.strip())
    if not m:raise ValueError('unreadable time: '+text_point)
    g=m.groups()
    if m.group('vend'):
        return None,'version_end'
    if g[16]:   # 「X」版本更新后
        v=versions.get(f'{game}|{region}|{g[16]}')
        return (dt.datetime.fromisoformat(v['start_at']) if v and v.get('start_at') else None),'version_start:'+g[16]
    return _point(g,published,tz,default_end),'fixed'

def clean_name(heading):
    """Activity name from a notice heading: drop numbering, the series prefix and 'opens' verbs."""
    text=re.sub(r'^\s*(?:[一二三四五六七八九十]+、|\d{1,2}\s*[\.、．]\s*|[○■◆●·]\s*)','',heading).strip()
    text=re.sub(r'^Dear Doctors?,?\s*|^\d{1,2}\s+(?=\[)','',text,flags=re.I)
    text=re.sub(r'\s+(?:IS NOW OPEN|NOW OPEN|OPENS?)$','',text,flags=re.I)
    parts=re.split(r'，(?![^「【\[]*[」】\]])',text);text=parts[-1] if len(parts)>1 and re.search(r'「|【|\[|活动|寻访|签到',parts[-1]) else text
    text=re.sub(r'(?:限时)?(?:活动)?(?:即将)?(?:开启|开放|上架)(?:公告|说明)?$|(?:说明|公告)$','',text).strip(' ：:')
    return text[:40] if re.search(r'[一-鿿]',text) else text[:90]

def _norm(name):return re.sub(r'[\s「」【】\[\]《》<>·•：:，,。.!！？?\-—_#]','',str(name)).casefold()

def key_name(name):
    """Calendar identity: the bracketed names (「归野」, 【将雪投火】, 「危机合约…」·机密圣所), so a Skland repost
    titled 「归野」明河叙事活动 and the version note's 「归野」叙事活动 are one activity.
    English titles share a series tag ([ARKNIGHTS X MONSTER HUNTER] …), so there the whole title is the identity."""
    if not re.search(r'[一-鿿]',str(name)):return _norm(name)
    head,_,tail=re.sub(r'(「[^」]*」|【[^】]*】)',lambda m:m.group(0).replace('·','\x00'),str(name)).partition('·')
    cores=[_norm(x.replace('\x00','·')) for group in re.findall(r'「([^」]+)」|【([^】]+)】|\[([^\]]+)\]',head) for x in group if x]
    if not cores:return _norm(name)
    return cores[0]+('·'+_norm(tail.replace('\x00','·')) if tail else '')

def _category(name):
    if re.search(r'礼包|组合包|作战包|资金箱|数据包|数据套组|零钱包|手提箱|新增家具|月卡|Bundles?\b|Packs?\b|Monthly Card',name,re.I):return 'pack'
    if re.search(r'寻访|申领|Headhunt|Banner|卡池|Arsenal|Issue',name,re.I):return 'headhunt'
    if re.search(r'签到|登录|Check-?in|Login',name,re.I):return 'signin'
    if re.search(r'商店|兑换|上架|特卖|时装|Store|Shop|Outfit|圣所',name,re.I):return 'shop'
    if re.search(r'网页|H5|官服更新活动|征集|投稿|社区|Web event|Creation|Voting',name,re.I):return 'web'
    return 'event'

def _add_phase(entry,phase):
    if any(p['label']==phase['label'] and p['start_at']==phase['start_at'] for p in entry['phases']):return
    if phase['label']=='内容更新' and phase['start_at']==entry.get('start_at'):return
    entry['phases'].append(phase)

def calendar_key(game,region,name):
    # A web/H5 event shares its name with the in-game event it promotes; keep them apart.
    return f'{game}|{region}|{key_name(name)}'+('·web' if _category(name)=='web' else '')

SOURCE_RANK={'official_game_page':0,'official_x':1,'skland_capture':2,'skland_browser':2}

def extract(text,game,region,published,item_id,versions=None,title=''):
    """Activity windows and phase nodes in one official text, each with the sentence it came from.

    Returns (activities, version_starts). A window line belongs to the nearest heading above it
    (「X」/【X】/[X] with optional 一、/1./○ numbering); a stage label (第二段/Part.2/Phase 2/预选期)
    on or just above the line makes it a phase of that heading instead of a new activity."""
    versions=dict(versions or {});tz=dt.timezone(dt.timedelta(hours=_offset(game,region,None)))
    if re.search(r'DURATION\s*:',text,re.I):
        # English notices arrive as one paragraph: break before their labels and numbered headings.
        text=re.sub(r'(?<!Phase)\s+(?=\d{1,2}\s+\[)|\s+(?=DURATION\s*:|DETAILS\s*:|REWARDS\s*:|NOTE\s*:|UNLOCK REQUIREMENT\s*:|Phase\s*\d+\s*\[)|(?<!Phase \d)\s+(?=\[\s*[A-Z])','\n',text)
    lines=[l.strip() for l in re.split(r'\n|(?<=[。；])\s+',text) if l.strip()]
    found={};order=[];version_starts={}
    title_version=re.search(r'「([^」]{1,12})」\s*版本更新(?:说明|公告)',text)
    heading=None;section=None;stage=None;used=set()
    def phase_label(line):
        m=PHASE_TIME.search(line)
        return '后续开放' if m and m.group(1) in {'开放后续','追加','新增关卡开放','开放第二'} else '内容更新'
    for i,line in enumerate(lines):
        if i in used:continue
        if title_version and re.search(r'更新维护时间',line) and i+1<len(lines):
            m=RANGE.search(line) or RANGE.search(lines[i+1])
            if m and not RANGE.search(line):used.add(i+1)   # the maintenance window is not an activity
            if m:
                zone=m.groups()[-1];tzv=dt.timezone(dt.timedelta(hours=_offset(game,region,zone)))
                end,_=_resolve(m.group('b'),published,tzv,False,versions,game,region)
                if end:
                    version_starts[title_version.group(1)]=dict(start_at=end.isoformat(),quote=m.group(0).strip(),item_id=item_id)
                    versions[f'{game}|{region}|{title_version.group(1)}']={**versions.get(f'{game}|{region}|{title_version.group(1)}',{}),'start_at':end.isoformat()}
                continue
        label=PHASE_LABEL.search(line)
        ranges=list(RANGE.finditer(line))
        if not ranges:
            if label and len(line)<=40:stage=label.group(1);continue
            if BARE.match(line) and not is_heading(line):stage=None;continue   # 【活动时间】 etc. closes a stage block
            if is_heading(line):
                bare=BARE.match(line)
                if SECTION.match(line) or not section:section=line
                bare_text=bare.group(1).strip('「」【】') if bare else ''
                if bare and section and section!=line and not re.fullmatch(r'(?:挑战|活动|奖励|任务|兑换)?(?:开放|领取|持续|参与|活动)?时间',bare_text):
                    heading=clean_name(section)+'·'+bare_text
                else:heading=section if bare and section and section!=line else line
                stage=None
            single=SINGLE_POINT.search(line)
            if single and heading and PHASE_TIME.search(line) and not NOT_ACTIVITY.search(line):
                zone=single.groups()[-1]
                when=_point(single.groups()[1:],published,dt.timezone(dt.timedelta(hours=_offset(game,region,zone))),False)
                key=key_name(clean_name(heading))
                if key in found:_add_phase(found[key],dict(label=phase_label(line),start_at=when.isoformat(),quote=line[:160],item_id=item_id))
                elif re.match(r'^[·\s]*(?:更新|开放)时间',line) and any(PHASE_TIME.search(l) and SINGLE_POINT.search(l) for l in lines[i+1:i+4]):
                    # A content drop with no end date whose later part opens on a stated day
                    # (「密境行者」画外遗光: 3 spaces now, 3 more on 11/19): the later opening is the node to remind.
                    name=clean_name(heading)
                    found[key]=dict(name=name,game=game,region=region,category=_category(name),kind='online',scale='main',start_at=when.isoformat(),start_rule='fixed',
                                    end_at=None,end_rule='open',version=title_version.group(1) if title_version else None,quote=line[:200],item_id=item_id,phases=[])
                    order.append(key)
            continue
        for m in ranges:
            before=line[:m.start()].strip()
            prev=lines[i-1] if i else ''
            if NOT_ACTIVITY.search(before) or (not before and len(prev)<=24 and NOT_ACTIVITY.search(prev)):continue
            zone=m.groups()[-1]
            tzv=dt.timezone(dt.timedelta(hours=_offset(game,region,zone)))
            try:
                start,start_rule=_resolve(m.group('a'),published,tzv,False,versions,game,region)
                end,end_rule=_resolve(m.group('b'),published,tzv,True,versions,game,region)
            except (ValueError,KeyError):continue
            quote=(before+' '+m.group(0)).strip()[:200]
            own=re.search(r'(「[^」]+」|【[^】]+】|\[[^\]]+\])[^：:]{0,12}$',re.sub(r'[:：]\s*$','',before))
            phase=(label.group(1) if label else None) or stage
            if heading is None and own is None:heading=title or lines[0]
            parent=clean_name(heading) if heading else clean_name(own.group(1))
            if own and _norm(own.group(1)) not in _norm(parent) and not phase:
                sub_label=own.group(1).strip('「」【】[]')
                if re.fullmatch(r'(?:挑战|活动|奖励|任务|兑换)?(?:开放|领取|持续|参与|活动)?时间',sub_label):name=parent
                else:name=parent+'·'+sub_label if heading else clean_name(own.group(1))
            else:name=parent
            key=key_name(name)
            if phase and key in found:
                entry=found[key]
                _add_phase(entry,dict(label=re.sub(r'[<>\s]','',phase),start_at=start.isoformat() if start else None,quote=quote,item_id=item_id))
                if end and entry['end_rule']=='fixed' and entry['end_at'] and end>dt.datetime.fromisoformat(entry['end_at']):entry['end_at']=end.isoformat()
                continue
            if key in found and not phase:continue
            entry=dict(name=name,game=game,region=region,category=_category(name),kind='collab' if re.search(r'联动|联名|×|collab',name,re.I) else 'offline' if re.search(r'线下|展会|快闪|主题店|Round1',name,re.I) else 'online',
                       scale='minor' if _category(name)=='web' else 'main',start_at=start.isoformat() if start else None,start_rule=start_rule,
                       end_at=end.isoformat() if end else None,end_rule='fixed' if end_rule=='fixed' else 'version_end',
                       version=title_version.group(1) if title_version else (start_rule.split(':',1)[1] if start_rule.startswith('version_start:') else None),
                       quote=quote,item_id=item_id,phases=[])
            if phase:entry['phases'].append(dict(label=re.sub(r'[<>\s]','',phase),start_at=entry['start_at'],quote=quote,item_id=item_id))
            found[key]=entry;order.append(key)
    # 2026-11-22: merge sub-items of the same notice (e.g. 「雪山降临1101」·变革之路 / 观测站后勤处,
    # or a companion event exchange shop starting at the same time as the main event) into the parent
    # activity so one event never spawns 3-5 redundant calendar rows.
    dropped=set()
    for key in list(order):
        if key in dropped:continue
        entry=found[key]
        if '·' in key:
            base,sub=key.split('·',1)
            if base in found and base not in dropped:
                parent_entry=found[base]
                if entry.get('start_at') and entry.get('start_at')!=parent_entry.get('start_at'):
                    _add_phase(parent_entry,dict(label=sub,start_at=entry['start_at'],quote=entry.get('quote',''),item_id=item_id))
                for p in entry.get('phases',[]):_add_phase(parent_entry,p)
                dropped.add(key);continue
        # Companion shop/exchange in the same notice (not standalone outfit/skin sales).
        is_companion_shop=(entry.get('category')=='shop' or bool(re.search(r'奖杯兑换|活动商店|后勤处|兑换商店|Trophies|Workshop',entry['name'],re.I))) and not re.search(r'时装|服饰|Outfit|Fashion|风尚',entry['name'],re.I)
        if is_companion_shop and entry.get('start_at'):
            host=next((found[k] for k in order if k!=key and k not in dropped and found[k].get('category')=='event' and found[k].get('start_at')==entry['start_at']),None)
            if host is not None:
                for p in entry.get('phases',[]):_add_phase(host,p)
                dropped.add(key);continue
    order=[k for k in order if k not in dropped]
    for k in dropped:found.pop(k,None)
    for entry in found.values():
        phases=[p for p in entry['phases'] if p['start_at']]
        if phases and (not entry['start_at'] or min(p['start_at'] for p in phases)<entry['start_at']):entry['start_at']=min(p['start_at'] for p in phases)
    return [found[k] for k in order],version_starts

# ---- the calendar file ----
def calendar_path(root):return Path(root)/'data/activity-calendar.json'

def load_calendar(root):
    path=calendar_path(root)
    if path.is_file():return json.loads(path.read_text(encoding='utf-8'))
    calendar=dict(schema=2,synced_at={},versions={},activities={})
    # The 2026-11-10 ledger only knew activities that had their own page; carry them over.
    old=Path(root)/'data/activity-ledger.json'
    if old.is_file():
        for value in json.loads(old.read_text(encoding='utf-8')).values():
            key=f"{value.get('game')}|{value.get('game_region') or 'cn'}|{key_name(value['name'])}"
            calendar['activities'][key]=dict(name=value['name'],game=value.get('game'),region=value.get('game_region') or 'cn',category=_category(value['name']),
                kind=value.get('kind','online'),scale=value.get('scale','main'),start_at=value['start_at'],start_rule='fixed',end_at=value['end_at'],end_rule='fixed',
                quote=value.get('window_quote'),item_id=value.get('item_id'),source_url=value.get('source_url'),phases=[],origin='reported_page',
                reported=[value['last_edition']] if value.get('last_edition') else [])
    return calendar

def save_calendar(root,calendar):
    path=calendar_path(root);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.json.writing');tmp.write_text(json.dumps(calendar,ensure_ascii=False,indent=1),encoding='utf-8',newline='\n');tmp.replace(path)

def policy(root):
    cfg=json.loads((Path(root)/'config.json').read_text(encoding='utf-8')) if (Path(root)/'config.json').is_file() else {}
    return cfg.get('activity_calendar',{})

def _source_text(root,item_id,item,fetch):
    """Full official wording: inspected article, else fetch the official page once; the collected text if fuller."""
    body=item.get('official_body') or []
    stored='\n'.join([item.get('title',''),item.get('summary','')]+(body if isinstance(body,list) else [str(body)]))
    stored_how='summary' if item.get('source_type')!='official_x' else 'post'
    path=Path(root)/'data/articles'/(item_id+'.json');page,how='',None
    if path.is_file():
        data=json.loads(path.read_text(encoding='utf-8'));page=data.get('text') or '\n'.join(data.get('official_body') or []);how='article'
    elif fetch and item.get('source_type')=='official_game_page':
        from news_video import read_web_article
        page=read_web_article(item_id,dict(url=item['url'],title=item['title'])).get('text','');how='fetched'
    # A script-rendered page (arknights.global) archives as an empty shell; the collected text is then the full copy.
    return (page,how) if len(page)>=len(stored) else (stored,stored_how)

def sync(root,game,reference=None,fetch=True):
    """Read the official notices of one game and merge every activity into the calendar."""
    root=Path(root);reference=reference or dt.datetime.now(UTC);rule=policy(root)
    regions=rule.get('regions',{}).get(game,['cn','global']);max_age=rule.get('max_source_age_days',60)
    calendar=load_calendar(root);report=dict(game=game,scanned=0,added=[],updated=[],fetched=0,unreadable=[],summary_only=[])
    items=[]
    for path in (root/'data/game-items').glob('*.json'):
        item=json.loads(path.read_text(encoding='utf-8'))
        if item.get('game')!=game or item.get('game_region','cn') not in regions or item.get('source_type') not in CALENDAR_SOURCES or not item.get('published'):continue
        published=dt.datetime.fromisoformat(item['published'])
        if published.tzinfo is None:published=published.replace(tzinfo=UTC)
        if not reference-dt.timedelta(days=max_age)<=published<=reference:continue
        items.append((published,path.stem,item))
    items.sort(key=lambda x:x[0])   # later notices (time adjustments) win
    # Rebuilt from the official text on every sync, so a parser fix also repairs older rows.
    # Kept: editor corrections/hides and activities that entered through a reported page.
    before={k:json.loads(json.dumps(v)) for k,v in calendar['activities'].items() if v.get('game')==game}
    calendar['activities']={k:v for k,v in calendar['activities'].items()
                            if v.get('game')!=game or v.get('origin')!='official_text' or v.get('hidden') or v.get('fixed_by_editor')}
    for published,item_id,item in items:
        try:text,how=_source_text(root,item_id,item,fetch)
        except Exception as error:report['unreadable'].append(dict(item_id=item_id,title=item.get('title'),error=type(error).__name__));continue
        report['scanned']+=1;report['fetched']+=how=='fetched'
        if how=='summary' and item.get('source_type')=='official_game_page':report['summary_only'].append(item_id)
        region=item.get('game_region','cn')
        try:found,starts=extract(text,game,region,published.astimezone(BEIJING),item_id,calendar['versions'],item.get('title',''))
        except Exception as error:report['unreadable'].append(dict(item_id=item_id,title=item.get('title'),error=str(error)[:120]));continue
        for name,v in starts.items():
            key=f'{game}|{region}|{name}';old=calendar['versions'].get(key,{})
            calendar['versions'][key]={**old,**v,'name':name,'game':game,'region':region}
        for entry in found:
            key=calendar_key(game,region,entry['name']);old=calendar['activities'].get(key)
            entry.update(source_url=item.get('url'),source_published=item['published'],source_type=item.get('source_type'),origin='official_text')
            # An X post's first sentence is no activity name; only bracketed names count there.
            if item.get('source_type')=='official_x' and not re.search(r'「|【|\[',entry['name']):continue
            if old and old.get('hidden'):continue
            if old and old.get('fixed_by_editor'):
                old.setdefault('phases',[])
                for p in entry['phases']:_add_phase(old,p)
                continue
            if old and SOURCE_RANK.get(old.get('source_type'),3)<SOURCE_RANK.get(entry['source_type'],3):
                # The official site already gave this activity; a Skland repost only adds stage dates.
                for p in entry['phases']:_add_phase(old,p)
                continue
            if old:
                merged={**old,**{k:v for k,v in entry.items() if v not in (None,[],'')}}
                merged['phases']=old.get('phases',[])+[p for p in entry['phases'] if all(p['label']!=q['label'] or p['start_at']!=q['start_at'] for q in old.get('phases',[]))]
                merged['reported']=old.get('reported',[])
                calendar['activities'][key]=merged
            else:calendar['activities'][key]=dict(entry,reported=[])
    report['expired']=_prune(calendar,game,reference)
    # Reported against the file as it was before this sync (rows are rebuilt, so compare contents).
    now={k:v for k,v in calendar['activities'].items() if v.get('game')==game}
    report['added']=[k for k in now if k not in before]
    report['updated']=[k for k in now if k in before and before[k]!=now[k]]
    calendar['synced_at'][game]=reference.isoformat()
    save_calendar(root,calendar)
    return report

def _expired(entry,calendar,reference):
    """Over for good: its end has passed, or (no end date) its last part opened over a day ago."""
    end,basis=_resolved_end(entry,calendar)
    if end is not None:return end<=reference
    if basis!='open':return False   # ends with a version whose end is not known yet
    marks=[p['start_at'] for p in entry.get('phases',[]) if p.get('start_at')]+([entry['start_at']] if entry.get('start_at') else [])
    return bool(marks) and dt.datetime.fromisoformat(max(marks))<reference-dt.timedelta(days=1)

def _prune(calendar,game,reference):
    """Delete the game's finished activities (editor rows and hidden rows included) from the file."""
    gone=[dict(key=k,name=v['name'],end_at=_resolved_end(v,calendar)[0].isoformat() if _resolved_end(v,calendar)[0] else None)
          for k,v in calendar['activities'].items() if v.get('game')==game and _expired(v,calendar,reference)]
    for g in gone:del calendar['activities'][g['key']]
    return gone

def prune(root,game,reference=None):
    calendar=load_calendar(root);gone=_prune(calendar,game,reference or dt.datetime.now(UTC))
    if gone:save_calendar(root,calendar)
    return dict(game=game,expired=gone)

def _resolved_end(entry,calendar):
    if entry.get('end_at'):return dt.datetime.fromisoformat(entry['end_at']),'fixed'
    if entry.get('end_rule')=='open':return None,'open'
    same=[x for x in calendar['versions'].values() if x['game']==entry['game'] and x['region']==entry['region'] and x.get('start_at')]
    version=entry.get('version')
    v=calendar['versions'].get(f"{entry['game']}|{entry['region']}|{version}") if version else None
    if not v and entry.get('start_at'):
        # The version the activity started in: the latest one that had begun by then.
        began=[x for x in same if x['start_at']<=entry['start_at']]
        v=max(began,key=lambda x:x['start_at']) if began else None
    if v and v.get('end_at'):return dt.datetime.fromisoformat(v['end_at']),'version_end'
    if v and v.get('start_at'):
        # A version ends when the next one starts (its 更新维护时间 is read from the next version note).
        later=[x['start_at'] for x in same if x['start_at']>v['start_at']]
        if later:return dt.datetime.fromisoformat(min(later)),'next_version_start'
    return None,'version_end_unknown'

def reminders(root,game,reference=None,calendar=None):
    """Running activities of a game, soonest deadline first, with days left and phases due today/tomorrow."""
    reference=reference or dt.datetime.now(UTC);calendar=calendar or load_calendar(root);rule=policy(root)
    regions=rule.get('regions',{}).get(game,['cn','global']);ahead=dt.timedelta(days=rule.get('upcoming_days',3))
    now=reference.astimezone(BEIJING);rows=[]
    for key,entry in calendar['activities'].items():
        if entry.get('game')!=game or entry.get('hidden') or entry.get('category')=='pack' or entry.get('region','cn') not in regions or not entry.get('start_at'):continue
        start=dt.datetime.fromisoformat(entry['start_at']);end,basis=_resolved_end(entry,calendar)
        if end is not None and end<=reference:continue
        if start>reference+ahead:continue
        if end is None and basis=='open':
            # No end date: listed while a later part is still to open, then dropped a day after the last one.
            later=[dt.datetime.fromisoformat(p['start_at']) for p in entry.get('phases',[]) if p.get('start_at')]
            if not later or max(later)<reference-dt.timedelta(days=1):continue
            info=dict(phase='running' if start<=reference else 'upcoming',days=None,urgent=False,label='长期开放',
                      end_label='无结束时间',start_label=status(start,start+dt.timedelta(days=1),reference)['start_label'])
        elif end is None:
            # Ends with the version; without an announced maintenance time only the rule is shown.
            info=dict(phase='running' if start<=reference else 'upcoming',days=None,urgent=False,label='版本更新前结束',
                      end_label='版本更新维护前截止',start_label=status(start,start+dt.timedelta(days=1),reference)['start_label'])
        else:info=status(start,end,reference)
        due=[]
        for p in entry.get('phases',[]):
            if not p.get('start_at'):continue
            at=dt.datetime.fromisoformat(p['start_at']).astimezone(BEIJING)
            delta=(at.date()-now.date()).days
            if -1<=delta<=ahead.days and at>start.astimezone(BEIJING):
                day_word={-1:'昨天',0:'今天',1:'明天'}.get(delta,f'{at.month}月{at.day}日')
                due.append(dict(p,when=day_word+at.strftime('%H:%M'),day=delta))
        state='upcoming' if start>reference else 'ending' if end is not None and end<=reference+dt.timedelta(days=3) else 'ongoing'
        rows.append(dict(key=key,name=entry['name'],region=entry.get('region','cn'),category=entry.get('category','event'),kind=entry.get('kind','online'),
                         scale=entry.get('scale','main'),state=state,start_at=entry['start_at'],end_at=end.isoformat() if end else None,end_basis=basis,
                         phases_due=due,item_id=entry.get('item_id'),source_url=entry.get('source_url'),**info))
    # 2026-11-23: CN activities always precede global activities; within each region, what must be said aloud leads, then soonest deadline.
    rows.sort(key=lambda r:(_region_rank(r.get('region','cn')),not must_mention(r),r['end_at'] or '9999',STATE_ORDER[r['state']],SCALES[r['scale']]))
    return rows

def running(root,game,reference=None,ahead_days=7):
    """Back-compatible listing (name/label/window) of the calendar's running activities."""
    return [dict(r,window_label=r.get('window_label','')) for r in reminders(root,game,reference)]

# ---- the 活动日历 page ----
def must_mention(row):
    """Ending within 3 days, opening within 3 days, or a phase today/tomorrow: say it aloud."""
    return row['state'] in {'ending','upcoming'} or any(0<=p['day']<=1 for p in row['phases_due'])

def _day_tokens(row):
    tokens={'今天','明天','后天','今晚','明晚','今日','明日','本周','下周','周末','最后一天','最后两天','最后三天'}
    if row.get('days') is not None:
        tokens|={f"{row['days']}天",chinese_number(row['days'])+'天',f"还剩{row['days']}天",f"仅剩{row['days']}天"}
        if row['days']==2:tokens|={'两天','还剩两天','仅剩两天'}   # spoken Chinese says 两天, not 二天
    for value in [row.get('end_at'),row.get('start_at')]+[p['start_at'] for p in row['phases_due']]:
        if value:tokens|=spoken_dates(dt.datetime.fromisoformat(value).astimezone(BEIJING))
    return tokens

def calendar_rows(rows,limit,reference=None):
    reference=reference or dt.datetime.now(UTC)
    out=[]
    for r in rows[:limit]:
        soon=any(0<=p['day']<=1 for p in r['phases_due'])
        if r['phases_due']:
            p=r['phases_due'][0];detail=f"{p['when']} {p['label']}开启"+(f" · {r['label']}" if r['label'] else '')
        elif r['state']=='upcoming':detail=r['start_label']
        else:detail=r['label']+(' · '+r['end_label'] if r.get('end_at') else '')
        days=r.get('days');opening=r['state']=='upcoming'
        if soon:big,unit='!',''
        elif days is None:big,unit='—',''
        elif days<=1:big,unit=('今天' if days==0 else '明天'),('开' if opening else '止')   # never "0天"
        else:big,unit=str(days),('天后开' if opening else '天')
        if soon:
            urgency_tier='critical';urgency_label='今日阶段' if r['phases_due'][0]['day']==0 else '明日阶段'
        elif r['state']=='ending':
            urgency_tier='critical';urgency_label='紧急截止'
        elif opening:
            urgency_tier='upcoming';urgency_label='即将开启'
        elif r.get('end_at') is None:
            urgency_tier='version';urgency_label='跟版本'
        else:
            urgency_tier='normal';urgency_label='进行中'
        if opening:progress_pct=100
        elif r.get('start_at') and r.get('end_at'):
            s_dt=dt.datetime.fromisoformat(r['start_at']);e_dt=dt.datetime.fromisoformat(r['end_at'])
            total=max(1.0,(e_dt-s_dt).total_seconds());rem=max(0.0,(e_dt-reference).total_seconds())
            progress_pct=max(6,min(100,round(100*rem/total)))
        else:progress_pct=55
        out.append(dict(key=r['key'],title=r['name'],detail=detail,region=REGION_LABEL[r['region']],category=r['category'],
                        big=big,unit=unit,urgent=r['state']=='ending' or soon or (opening and days is not None and days<=1),
                        progress_pct=progress_pct,urgency_tier=urgency_tier,urgency_label=urgency_label))
    return out

def calendar_pages(rows,rows_per_page=8,max_pages=3,reference=None):
    """Split running activities into 1..max_pages clean calendar pages (default 8 rows/page)."""
    if not rows:return []
    limit=max(1,int(rows_per_page));cap=max(1,int(max_pages))
    sliced=[rows[i*limit:(i+1)*limit] for i in range(cap) if rows[i*limit:(i+1)*limit]]
    total=len(sliced);cn_page=('一','二','三','四','五')
    pages=[]
    for idx,chunk in enumerate(sliced):
        urgent=sum(1 for r in chunk if must_mention(r))
        all_global=all(_region_rank(r.get('region','cn'))==1 for r in chunk)
        suffix='国际服活动汇总' if all_global else (f'{urgent}项近期变动' if urgent else '进行中与版本活动')
        hint=(f'活动日历（{cn_page[idx]}）：' if total>1 else '活动日历：')+suffix
        pages.append(dict(page=idx+1,total_pages=total,title_hint=hint,keys=[r['key'] for r in chunk],
                          rows=calendar_rows(chunk,len(chunk),reference)))
    return pages

def _covered_keys(episode,rows):
    """Activities already featured on a dedicated activity or news page in this episode."""
    covered=set()
    narrated_items={}
    for s in episode.get('scenes',[]):
        if s.get('scene_type')=='activity_calendar':continue
        if s.get('calendar_key'):covered.add(s['calendar_key'])
        for entry in s.get('activity_items') or []:
            if entry.get('calendar_key'):covered.add(entry['calendar_key'])
            if entry.get('name'):covered.add(calendar_key(s.get('game'),s.get('game_region') or 'cn',entry['name']))
        if s.get('item_id') and s.get('narration'):
            narrated_items[s['item_id']]=narrated_items.get(s['item_id'],'')+' '+s['narration']
    for r in rows:
        text=narrated_items.get(r.get('item_id'),'')
        if text and any(_norm(r['name'])[i:i+4] in _norm(text) for i in range(max(1,len(_norm(r['name']))-3))):
            covered.add(r['key'])
    return covered

def bind_calendar(scene,episode,root,reference,bind=True):
    """Fill one (of 1-3) 活动日历 pages from the calendar and verify due items are named."""
    game=scene.get('game')
    if game not in {'arknights','endfield'}:raise ValueError('ACTIVITY_CALENDAR: the 活动日历 page names its game (arknights/endfield)')
    calendar=load_calendar(root);rule=policy(root)
    synced=calendar['synced_at'].get(game)
    if not synced or reference-dt.datetime.fromisoformat(synced)>dt.timedelta(hours=rule.get('max_sync_age_hours',12)):
        raise ValueError(f'ACTIVITY_CALENDAR_STALE: run python -B activities.py sync --series {game} before writing this edition')
    rows=reminders(root,game,reference,calendar)
    if not rows:raise ValueError('ACTIVITY_CALENDAR_EMPTY: no running activity in the calendar; drop the 活动日历 page')
    limit=rule.get('rows_per_page',8);max_pages=rule.get('max_pages',3)
    cal_scenes=[s for s in episode.get('scenes',[]) if s.get('scene_type')=='activity_calendar']
    if scene not in cal_scenes:cal_scenes=[scene]
    page_count=len(cal_scenes)
    if page_count>max_pages:raise ValueError(f'ACTIVITY_CALENDAR: at most {max_pages} 活动日历 pages per edition')
    page_index=cal_scenes.index(scene);page_num=page_index+1
    by_key={r['key']:r for r in rows}
    if scene.get('calendar_keys'):
        page_rows=[by_key[k] for k in scene['calendar_keys'] if k in by_key][:limit]
        if not page_rows:raise ValueError('ACTIVITY_CALENDAR_EMPTY: calendar_keys matched no running activities')
    else:
        page_rows=rows[page_index*limit:(page_index+1)*limit]
        if not page_rows:raise ValueError(f'ACTIVITY_CALENDAR_EMPTY: calendar page {page_num} has no remaining rows (only {len(rows)} running activities)')
    # Combine narration and spoken maps across all 活动日历 pages so multi-page calendars validate smoothly,
    # and skip repeating deadlines for activities already featured on their own dedicated page this episode.
    all_narration='\n'.join(str(s.get('narration','')) for s in cal_scenes)
    all_spoken={}
    for s in cal_scenes:all_spoken.update(s.get('spoken') or {})
    sentences=[s for s in re.split(r'(?<=[。！？!?；\n])',all_narration) if s.strip()]
    covered=_covered_keys(episode,rows)
    missing=[]
    for r in page_rows:
        if not must_mention(r) or r['key'] in covered:continue
        phrase=str(all_spoken.get(r['key'],'')).strip()
        if not phrase or phrase not in all_narration:
            missing.append(f"{r['key']} ({r['name']}: {r['phases_due'][0]['when']+' '+r['phases_due'][0]['label'] if r['phases_due'] else r['label']})");continue
        if re.search(r'[一-鿿]',r['name']) and not any(_norm(phrase)[i:i+2] in _norm(r['name']) for i in range(max(1,len(_norm(phrase))-1))):
            raise ValueError(f'ACTIVITY_CALENDAR_SPOKEN: "{phrase}" does not name {r["name"]}')
        matching=[s for s in sentences if phrase in s]
        if not any(any(t in sent for t in _day_tokens(r)) for sent in matching):
            raise ValueError(f'ACTIVITY_CALENDAR_DAY: the sentence naming {r["name"]} must say when (今天/明天/N天/日期): {matching[0].strip()}')
    if missing:
        raise ValueError('ACTIVITY_CALENDAR_SPOKEN: name these in the narration and map them in "spoken" {key: phrase as spoken}: '+'; '.join(missing))
    if bind:
        shown=calendar_rows(page_rows,limit,reference)
        scene['calendar_rows']=shown
        scene['calendar_page']=page_num;scene['calendar_total_pages']=page_count
        shown_total=min(len(rows),page_count*limit)
        scene['calendar_more']=max(0,len(rows)-shown_total) if page_index==page_count-1 else 0
        # Attach the full description list only on the first calendar page to avoid duplicating it in description.txt.
        if page_index==0:
            scene['calendar_all']=[dict(title=r['title'],region=r['region'],detail=r['detail']) for r in calendar_rows(rows,len(rows),reference)]
        else:
            scene.pop('calendar_all',None)
        scene['facts']=[dict(title=r['title'],detail=r['detail']) for r in shown]
        scene['badge']=f'活动日历 {page_num}/{page_count}' if page_count>1 else '活动日历'
        scene['segment']='activities'
        cn_page=('一','二','三')
        if page_count>1:
            scene['page_number']=page_num
            titles=[str(s.get('title','')) for s in cal_scenes]
            if titles.count(scene.get('title',''))>1:
                scene['title']=str(scene.get('title','活动日历'))+f'（{cn_page[page_index]}）'
            shorts=[str(s.get('short_title','')) for s in cal_scenes]
            if not scene.get('short_title') or shorts.count(scene.get('short_title',''))>1:
                scene['short_title']=f'活动日历{page_num}/{page_count}'
        urls=[r['source_url'] for r in page_rows if r.get('source_url')] or [r['source_url'] for r in rows if r.get('source_url')]
        scene['calendar_sources']=list(dict.fromkeys(urls))
        if urls:scene['source_url']=max(scene['calendar_sources'],key=urls.count)
        scene.setdefault('game_region','cn');scene['game_topic']='event'
        scene.setdefault('section','游戏资讯');scene.setdefault('company','明日方舟' if game=='arknights' else '明日方舟：终末地')
        scene['event_key']=f'{game}-activity-calendar' if page_count==1 else f'{game}-activity-calendar-{page_num}'
        scene['calendar_audit']=dict(synced_at=synced,page=page_num,total_pages=page_count,
                                     rows=[dict(key=r['key'],end_at=r['end_at'],end_basis=r['end_basis'],phases_due=[p['label'] for p in r['phases_due']],item_id=r['item_id']) for r in page_rows])
    return dict(reason='activity_calendar_bound',basis='activity_calendar',rows=len(page_rows),total_rows=len(rows),page=page_num,total_pages=page_count,synced_at=synced)

def require_calendar(episode,root,reference=None):
    """A game edition must carry 1..max_pages 活动日历 pages whenever its game has running activities,
    plus at least `min_featured_activities` (1) recent activity page."""
    from edition_series import series_of
    series=series_of(episode)
    if series not in {'arknights','endfield'} or episode.get('edition_slot') not in {'morning','night'}:return None
    reference=reference or dt.datetime.now(UTC);rule=policy(root)
    calendar=load_calendar(root);synced=calendar['synced_at'].get(series)
    if not synced or reference-dt.datetime.fromisoformat(synced)>dt.timedelta(hours=rule.get('max_sync_age_hours',12)):
        raise ValueError(f'ACTIVITY_CALENDAR_STALE: run python -B activities.py sync --series {series} before writing this edition')
    rows=reminders(root,series,reference,calendar)
    cal_scenes=[s for s in episode['scenes'] if s.get('scene_type')=='activity_calendar']
    if rows and not cal_scenes:
        raise ValueError('ACTIVITY_CALENDAR_REQUIRED: add 1-3 scene_type="activity_calendar" page(s); running: '+' / '.join(r['name']+'（'+r['label']+'）' for r in rows[:12]))
    if len(cal_scenes)>rule.get('max_pages',3):
        raise ValueError(f'ACTIVITY_CALENDAR: at most {rule.get("max_pages",3)} 活动日历 pages per edition')
    require_fill(episode,root,reference,series,calendar)

# ---- featured recent activities from the calendar (2026-11-22: >=1 recent activity, no 5-page spam) ----
def is_fill(scene):return bool(scene.get('calendar_key'))

def news_pages(episode):
    """Body pages that carry a message: not the 导览, the 活动日历, 玩家热议 or a calendar fill page."""
    from layout_policy import is_overview
    return [s for s in episode['scenes'] if not is_overview(s) and s.get('scene_type')!='activity_calendar'
            and s.get('segment')!='community' and not str(s.get('item_id','')).startswith('community-') and not is_fill(s)]

def fill_plan(episode,root,reference,series=None,calendar=None):
    """Recommended recent activity page(s) from the calendar: urgent/main activities first,
    deprioritizing non-urgent minor web events that were already reported."""
    from edition_series import series_of
    series=series or series_of(episode);calendar=calendar or load_calendar(root);rule=policy(root)
    legacy_target=rule.get('min_body_pages',0)
    min_featured=rule.get('min_featured_activities',1)
    max_fill=rule.get('max_fill_pages',2)
    news=news_pages(episode)
    explicit_activities=[s for s in news if s.get('scene_type')=='activity' or s.get('activity')]
    featured={calendar_key(s.get('game'),s.get('game_region') or 'cn',s['activity_items'][0]['name']) for s in news if s.get('activity_items')}
    narrated={s.get('item_id'):s.get('narration','') for s in news if s.get('item_id')}
    rows=[]
    for r in reminders(root,series,reference,calendar):
        if not r['end_at'] or r['key'] in featured:continue
        if r['item_id'] in narrated and any(_norm(r['name'])[i:i+4] in _norm(narrated[r['item_id']]) for i in range(max(1,len(_norm(r['name']))-3))):continue
        rows.append(r)
    if legacy_target>0:
        need=max(0,legacy_target-len(news))
        return dict(mode='legacy_min_body',news_pages=len(news),target=legacy_target,need=need,keys=[r['key'] for r in rows[:need]],rows=rows[:need])
    # 2026-11-22 mode: prioritize urgent/main activities, deprioritize repeatedly-reported non-urgent minor web events.
    cal_entries=calendar.get('activities',{})
    def rank_featured(r):
        entry=cal_entries.get(r['key'],{})
        repeated_minor=int(r['scale']=='minor' and not must_mention(r) and bool(entry.get('reported')))
        return (_region_rank(r.get('region','cn')),repeated_minor,not must_mention(r),SCALES[r['scale']],STATE_ORDER[r['state']],r['end_at'] or '9999')
    rows.sort(key=rank_featured)
    need=max(0,min_featured-len(explicit_activities))
    recommended_count=max(need,min(max_fill,len(rows))) if len(news)==0 else max(need,min(1,len(rows)))
    return dict(mode='featured_recent',news_pages=len(news),explicit_activities=len(explicit_activities),
                min_featured=min_featured,max_fill=max_fill,need=min(need,len(rows)),
                recommended_count=min(recommended_count,len(rows)),
                keys=[r['key'] for r in rows[:recommended_count]],rows=rows[:max(recommended_count,3)])

def require_fill(episode,root,reference,series=None,calendar=None):
    rule=policy(root);plan=fill_plan(episode,root,reference,series,calendar)
    have=[s['calendar_key'] for s in episode['scenes'] if is_fill(s)]
    if plan.get('mode')=='legacy_min_body':
        if have!=plan['keys']:
            want=' / '.join(f"{r['key']}（{r['name']}，{r['label']}）" for r in plan['rows']) or '无'
            raise ValueError(f"ACTIVITY_FILL: {plan['news_pages']} message pages (target {plan['target']}); the calendar fill pages must be, in this order: {want}. "
                             'Write each as scene_type="activity" with "calendar_key", 1-2 facts and the deadline date in the narration, placed right before the 活动日历 page.')
        episode['calendar_fill']=dict(news_pages=plan['news_pages'],target=plan['target'],keys=plan['keys'])
        return
    cap=max(int(rule.get('max_fill_pages',2)),3)
    if len(have)>cap:
        raise ValueError(f'ACTIVITY_FILL: at most {cap} calendar fill pages; keep the episode concise instead of padding')
    total_featured=plan['explicit_activities']+len(have)
    # Every game edition must include at least min_featured_activities (1) concrete recent activity page
    # when the calendar has running activities with a known deadline.
    if total_featured<plan['min_featured'] and plan['rows']:
        want=' / '.join(f"{r['key']}（{r['name']}，{r['label']}）" for r in plan['rows'][:3])
        raise ValueError(f"ACTIVITY_FILL: every game edition needs at least {plan['min_featured']} recent activity page (scene_type=\"activity\" with calendar_key or activity_items). Recommended: {want}")
    episode['calendar_fill']=dict(mode='featured_recent',news_pages=plan['news_pages'],min_featured=plan['min_featured'],keys=have)

def fill_from_calendar(episode,root,reference=None):
    """Complete each calendar fill page from the calendar entry: window, official sentence, source."""
    reference=reference or dt.datetime.now(UTC);calendar=None
    for scene in episode['scenes']:
        if not is_fill(scene):continue
        calendar=calendar or load_calendar(root);key=scene['calendar_key'];entry=calendar['activities'].get(key)
        if not entry or entry.get('hidden'):raise ValueError('ACTIVITY_FILL_KEY: '+key+' is not in the activity calendar; see activities.py list')
        listed=reminders(root,entry['game'],reference,calendar)
        row=next((r for r in listed if r['key']==key),None)
        if not row or not row['end_at']:raise ValueError('ACTIVITY_FILL_KEY: '+key+' is not running with a known deadline')
        scene['calendar_rank']=listed.index(row)
        if scene.get('scene_type','activity')!='activity' or scene.get('item_id') not in (None,entry.get('item_id')):
            raise ValueError('ACTIVITY_FILL: a calendar fill page is scene_type="activity" and takes its item from the calendar')
        item=dict(name=entry['name'],kind=scene.get('kind',entry.get('kind','online')),scale=entry.get('scale','main'),start_at=entry['start_at'],end_at=row['end_at'],
                  window_quote=entry.get('quote'),item_id=entry.get('item_id'),source_type=entry.get('source_type'),calendar_key=key,end_basis=row['end_basis'])
        for field in ['location','partner']:
            if scene.get(field):item[field]=scene[field]
        scene.update(scene_type='activity',item_id=entry.get('item_id'),source_url=entry.get('source_url'),source_type=entry.get('source_type'),game=entry['game'],
                     game_region=entry.get('region','cn'),freshness_basis='active_window',activity_items=[item])
        scene.setdefault('event_key',key);scene.setdefault('game_topic','event')
        scene.setdefault('section','游戏资讯');scene.setdefault('company','明日方舟' if entry['game']=='arknights' else '明日方舟：终末地')
        scene.setdefault('evidence',entry.get('quote'));scene.setdefault('selection_reason','近期重点活动提醒：从活动日历精选展示')

def calendar_check(root,entry,reference):
    """Freshness of a calendar fill page: the activity is still running/opening and its sentence is official."""
    from freshness import official_text
    calendar=load_calendar(root);key=entry['calendar_key'];stored=calendar['activities'].get(key)
    if not stored:return dict(ok=False,reason='calendar_entry_missing')
    row=next((r for r in reminders(root,stored['game'],reference,calendar) if r['key']==key),None)
    if not row or not row['end_at']:return dict(ok=False,reason='calendar_entry_not_running')
    squash=lambda s:re.sub(r'\s+','',str(s or ''))   # the calendar joins a label and its window with a space
    if not stored.get('quote') or squash(stored['quote']) not in squash(official_text(root,stored.get('item_id'))):return dict(ok=False,reason='calendar_quote_not_in_official_text')
    return dict(ok=True,reason='calendar_entry_running',state=row['state'],
                start_at=dt.datetime.fromisoformat(row['start_at']).astimezone(UTC).isoformat(),end_at=dt.datetime.fromisoformat(row['end_at']).astimezone(UTC).isoformat())

def record(episode,root):
    """Remember which edition reported what; a single activity page also enters the calendar."""
    touched=False;calendar=load_calendar(root)
    for s in episode['scenes']:
        if s.get('scene_type')=='activity_calendar':
            for r in s.get('calendar_audit',{}).get('rows',[]):
                entry=calendar['activities'].get(r['key'])
                if entry is not None and episode['id'] not in entry.setdefault('reported',[]):entry['reported'].append(episode['id']);touched=True
        if not s.get('activity'):continue
        if s.get('calendar_key'):
            # A fill page came from the calendar entry; only note that it was reported.
            entry=calendar['activities'].get(s['calendar_key'])
            if entry is not None and episode['id'] not in entry.setdefault('reported',[]):entry['reported'].append(episode['id']);touched=True
            continue
        a=s['activity'];entry=s['activity_items'][0];region=s.get('game_region') or 'cn'
        key=calendar_key(s.get('game'),region,a['name'])
        value=calendar['activities'].get(key) or dict(name=a['name'],game=s.get('game'),region=region,category=_category(a['name']),phases=[],origin='reported_page',reported=[])
        value.update(kind=a['kind'],scale=a['scale'],location=a['location'],partner=a['partner'],item_id=a['item_id'],start_at=entry['start_at'],start_rule='fixed',
                     end_at=entry['end_at'],end_rule='fixed',quote=entry['window_quote'],source_url=s.get('source_url'),image=s.get('image'),image_source_url=s.get('image_source_url'))
        if episode['id'] not in value['reported']:value['reported'].append(episode['id'])
        calendar['activities'][key]=value;touched=True
    if touched:save_calendar(root,calendar)

# ---- editor corrections (kept across syncs) ----
def fix(root,key,changes):
    calendar=load_calendar(root)
    if key not in calendar['activities']:raise ValueError('ACTIVITY_KEY: unknown '+key)
    for field in ['start_at','end_at']:
        if changes.get(field):
            if dt.datetime.fromisoformat(changes[field]).tzinfo is None:raise ValueError(field+' needs a timezone')
    if not changes.get('quote'):raise ValueError('ACTIVITY_FIX_QUOTE: give the official sentence that supports the correction')
    calendar['activities'][key].update(changes,fixed_by_editor=True);save_calendar(root,calendar)

def hide(root,key,reason):
    calendar=load_calendar(root)
    if key not in calendar['activities']:raise ValueError('ACTIVITY_KEY: unknown '+key)
    calendar['activities'][key].update(hidden=True,hidden_reason=reason);save_calendar(root,calendar)

def set_version(root,game,region,name,end_at,quote,item_id):
    """The maintenance time that ends a version, from the official sentence that states it."""
    from freshness import official_text
    if dt.datetime.fromisoformat(end_at).tzinfo is None:raise ValueError('end_at needs a timezone')
    if not quote or quote not in official_text(root,item_id):raise ValueError('VERSION_QUOTE: the quote must appear in the official text of '+item_id)
    calendar=load_calendar(root);key=f'{game}|{region}|{name}'
    calendar['versions'][key]={**calendar['versions'].get(key,{}),'name':name,'game':game,'region':region,'end_at':end_at,'end_quote':quote,'end_item_id':item_id}
    save_calendar(root,calendar)

def add(root,game,region,name,start_at,quote,item_id,end_at=None,version=None,open_end=False,kind='online',scale='main',reference=None):
    """An activity the parser missed, entered from an official notice; kept across syncs until it ends."""
    from freshness import official_text
    reference=reference or dt.datetime.now(UTC)
    if sum(map(bool,[end_at,version,open_end]))!=1:raise ValueError('ACTIVITY_END: give exactly one of --end-at, --version, --open')
    for field,value in [('start_at',start_at),('end_at',end_at)]:
        if value and dt.datetime.fromisoformat(value).tzinfo is None:raise ValueError(field+' needs a timezone, e.g. 2026-11-20T04:00:00+08:00')
    item=Path(root)/'data/game-items'/(str(item_id)+'.json')
    if not item.is_file() or json.loads(item.read_text(encoding='utf-8')).get('game')!=game:
        raise ValueError(f'ACTIVITY_SOURCE: {item_id} is not a collected {game} official item')
    if not quote or quote not in official_text(root,item_id):raise ValueError('ACTIVITY_QUOTE: the quote must appear verbatim in the official text of '+str(item_id))
    calendar=load_calendar(root);key=calendar_key(game,region,name)
    old=calendar['activities'].get(key)
    if old and not old.get('hidden'):raise ValueError(f'ACTIVITY_EXISTS: {key} is already listed; correct it with fix')
    source=json.loads(item.read_text(encoding='utf-8'))
    entry=dict(name=name,game=game,region=region,category=_category(name),kind=kind,scale=scale,start_at=start_at,start_rule='fixed',
               end_at=end_at,end_rule='fixed' if end_at else 'open' if open_end else 'version_end',version=version,quote=quote,item_id=item_id,
               phases=[],source_url=source.get('url'),source_published=source.get('published'),source_type=source.get('source_type'),
               origin='editor_added',fixed_by_editor=True,reported=(old or {}).get('reported',[]))
    if _expired(entry,calendar,reference):raise ValueError('ACTIVITY_ENDED: this activity is already over; nothing to add')
    calendar['activities'][key]=entry;save_calendar(root,calendar)
    return dict(key=key,**entry)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['sync','list','add','fix','hide','prune','fill','version'])
    parser.add_argument('--pages',type=int,default=0,help='fill: message pages planned for this edition (not counting 导览/活动日历/玩家热议)')
    parser.add_argument('--series',required=True,choices=['arknights','endfield']);parser.add_argument('--at',help='ISO time to evaluate at (default now)')
    parser.add_argument('--no-fetch',action='store_true');parser.add_argument('--key');parser.add_argument('--json');parser.add_argument('--reason')
    parser.add_argument('--region',default='cn');parser.add_argument('--name');parser.add_argument('--end-at');parser.add_argument('--quote');parser.add_argument('--item')
    parser.add_argument('--start-at');parser.add_argument('--version',help='add: ends with this version (name as in versions)');parser.add_argument('--open',action='store_true',help='add: no end date')
    parser.add_argument('--kind',default='online',choices=['online','offline','collab']);parser.add_argument('--scale',default='main',choices=['main','minor'])
    args=parser.parse_args();at=dt.datetime.fromisoformat(args.at) if args.at else None
    rule=policy(ROOT);rpp=rule.get('rows_per_page',8);mp=rule.get('max_pages',3)
    if args.command=='sync':
        out=sync(ROOT,args.series,at,not args.no_fetch)
        running_rows=reminders(ROOT,args.series,at)
        out['running']=[(r['key'],r['label'],[p['when']+' '+p['label'] for p in r['phases_due']]) for r in running_rows]
        out['calendar_pages']=len(calendar_pages(running_rows,rpp,mp,at))
    elif args.command=='list':
        running_rows=reminders(ROOT,args.series,at)
        out=dict(series=args.series,total=len(running_rows),rows_per_page=rpp,max_pages=mp,
                 pages=calendar_pages(running_rows,rpp,mp,at),rows=running_rows)
    elif args.command=='prune':out=prune(ROOT,args.series,at)
    elif args.command=='fill':
        # Preview before writing: top 1-3 recommended recent activities to feature on their own page(s).
        planned=dict(edition_series=args.series,scenes=[dict(id=f'n{i}',item_id=f'planned-{i}') for i in range(args.pages)])
        plan=fill_plan(planned,ROOT,at or dt.datetime.now(UTC),args.series)
        out={k:v for k,v in plan.items() if k!='rows'}
        out['rows']=[dict(key=r['key'],name=r['name'],label=r['label'],scale=r['scale'],end_at=r['end_at']) for r in plan['rows']]
    elif args.command=='add':out=add(ROOT,args.series,args.region,args.name,args.start_at,args.quote,args.item,args.end_at,args.version,args.open,args.kind,args.scale,at)
    elif args.command=='fix':fix(ROOT,args.key,json.loads(args.json));out=dict(ok=True)
    elif args.command=='hide':hide(ROOT,args.key,args.reason or '');out=dict(ok=True)
    else:set_version(ROOT,args.series,args.region,args.name,args.end_at,args.quote,args.item);out=dict(ok=True)
    sys.stdout.buffer.write((json.dumps(out,ensure_ascii=False,indent=1)+'\n').encode('utf-8'))
