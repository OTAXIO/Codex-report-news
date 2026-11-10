"""Running activities: one page per activity, each with its deadline (2026-11-10).

A page is `scene_type:"activity"` + `freshness_basis:"active_window"` with exactly one
entry in `activity_items`. The countdown shown on screen is computed here from the
verified window, never typed by the writer. Main activities come first; low-interest
web/community mini activities (`scale:"minor"`) go last.

CLI:
  python -B activities.py list --series endfield     activities already verified and still running
  python -B activities.py scan --series endfield     date windows found in collected official posts
"""
import datetime as dt,json,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
UTC=dt.timezone.utc
BEIJING=dt.timezone(dt.timedelta(hours=8))
KINDS={'online':'线上活动','offline':'线下活动','collab':'联动活动'}
SCALES={'main':0,'minor':1}
STATE_ORDER={'ending':0,'ongoing':1,'upcoming':2}
CN_DIGITS='零一二三四五六七八九'

def chinese_number(n):
    """1-31 as spoken Chinese, for matching narration written for TTS."""
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
    return dict(name=entry['name'].strip(),kind=kind,kind_label=KINDS[kind],scale=scale,state=check['state'],
                location=str(entry.get('location','')).strip(),partner=str(entry.get('partner','')).strip(),
                start_at=check['start_at'],end_at=check['end_at'],item_id=entry.get('item_id'),**info)

def sort_key(activity):return (SCALES[activity['scale']],STATE_ORDER[activity['state']],activity['end_at'])

def arrange(episode):
    """Put activity pages in the reporting order, inside the slots they already occupy."""
    slots=[i for i,s in enumerate(episode['scenes']) if s.get('activity')]
    for i,scene in zip(slots,sorted((episode['scenes'][i] for i in slots),key=lambda s:sort_key(s['activity']))):episode['scenes'][i]=scene

def validate_pages(episode,max_pages):
    """Episode-level rules for single-activity pages; scenes already carry `activity`."""
    pages=[s for s in episode['scenes'] if s.get('activity')]
    if not pages:return
    if len(pages)>max_pages:raise ValueError(f'ACTIVITY_PAGES: at most {max_pages} activity pages; drop minor ones first')
    seen=set()
    for s in pages:
        key=(s['activity']['item_id'],s['activity']['name'])
        if key in seen:raise ValueError('ACTIVITY_DUPLICATE: '+s['activity']['name']+' has two pages')
        seen.add(key)
    news={s.get('item_id') for s in episode['scenes'] if s.get('item_id') and not s.get('activity')}
    for s in pages:
        if s.get('item_id') in news:raise ValueError('ACTIVITY_DUPLICATE: '+s['activity']['name']+' is already a news page in this edition; keep one')
    body=[s for s in pages if not episode.get('lead_event_id') or s.get('event_key')!=episode['lead_event_id']]
    wanted=sorted(body,key=lambda s:sort_key(s['activity']))
    if [s['id'] for s in body]!=[s['id'] for s in wanted]:
        raise ValueError('ACTIVITY_ORDER: main activities first, mini web/community activities last; within each, ending soon -> ongoing -> upcoming. Expected order: '+' / '.join(s['activity']['name'] for s in wanted))

# ---- ledger: what has been verified and is still running ----
def ledger_path(root):return Path(root)/'data/activity-ledger.json'
def load_ledger(root):
    path=ledger_path(root)
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}

def record(episode,root):
    """Remember verified activities so later editions keep reporting them until they end."""
    pages=[s for s in episode['scenes'] if s.get('activity')]
    if not pages:return
    ledger=load_ledger(root)
    for s in pages:
        a=s['activity'];entry=s['activity_items'][0]
        ledger[a['item_id']+'|'+a['name']]=dict(game=s.get('game'),game_region=s.get('game_region'),name=a['name'],kind=a['kind'],scale=a['scale'],
            location=a['location'],partner=a['partner'],item_id=a['item_id'],start_at=entry['start_at'],end_at=entry['end_at'],
            window_quote=entry['window_quote'],source_type=entry['source_type'],source_url=s.get('source_url'),
            image=s.get('image'),image_source_url=s.get('image_source_url'),last_edition=episode['id'])
    path=ledger_path(root);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(ledger,ensure_ascii=False,indent=1),encoding='utf-8',newline='\n')

def running(root,game,reference=None,ahead_days=7):
    reference=reference or dt.datetime.now(UTC);rows=[]
    for value in load_ledger(root).values():
        if value.get('game')!=game:continue
        start=dt.datetime.fromisoformat(value['start_at']);end=dt.datetime.fromisoformat(value['end_at'])
        if end<=reference or start>reference+dt.timedelta(days=ahead_days):continue
        state='ending' if end<=reference+dt.timedelta(days=3) else 'ongoing' if start<=reference else 'upcoming'
        rows.append(dict(value,state=state,**{k:v for k,v in status(start,end,reference).items() if k in {'label','window_label'}}))
    return sorted(rows,key=lambda r:(SCALES[r['scale']],STATE_ORDER[r['state']],dt.datetime.fromisoformat(r['end_at'])))

# ---- scan: find activity windows in collected official posts ----
DATE=r'(?:(\d{4})\s*[年/.-]\s*)?(\d{1,2})\s*[月/.-]\s*(\d{1,2})\s*日?'
CLOCK=r'(?:\s*(\d{1,2})[:：](\d{2})(?:[:：](\d{2}))?)?'
WINDOW=re.compile(DATE+CLOCK+r'\s*(?:[-–—~～至到]|\s-\s)+\s*'+DATE+CLOCK)
OFFLINE=re.compile(r'线下|展会|漫展|主题店|主题餐厅|快闪|门店|音乐会|嘉年华|现场|展位|展台|Gamescom|Comic|offline|booth',re.I)
COLLAB=re.compile(r'联动|联名|合作|collab|×',re.I)
MINOR=re.compile(r'征集|投稿|社区|网页活动|H5|分享|头像挂件|梗图|问答|抽奖|转发|voting|share',re.I)

def windows(text,published):
    """Start/end windows written in a post; a missing year comes from the post date."""
    found=[]
    for m in WINDOW.finditer(text):
        y1,mo1,d1,h1,mi1,s1,y2,mo2,d2,h2,mi2,s2=m.groups()
        try:
            year=int(y1 or published.year)
            start=dt.datetime(year,int(mo1),int(d1),int(h1 or 0),int(mi1 or 0),int(s1 or 0),tzinfo=BEIJING)
            end_year=int(y2 or (year+1 if int(mo2)<int(mo1) else year))
            end=dt.datetime(end_year,int(mo2),int(d2),int(h2) if h2 else 23,int(mi2) if h2 else 59,int(s2 or (0 if h2 else 59)),tzinfo=BEIJING)
        except ValueError:continue
        if end>start:found.append(dict(start_at=start.isoformat(),end_at=end.isoformat(),window_quote=m.group(0).strip()))
    return found

def scan(root,game,reference=None,ahead_days=7,max_age_days=30):
    """Suggestions only: the writer still reads the post and confirms the timezone and the activity name."""
    reference=reference or dt.datetime.now(UTC);root=Path(root);rows=[];known={v['item_id'] for v in load_ledger(root).values()}
    for path in sorted((root/'data/game-items').glob('*.json')):
        item=json.loads(path.read_text(encoding='utf-8'))
        if item.get('game')!=game or not item.get('published'):continue
        published=dt.datetime.fromisoformat(item['published'])
        if published.tzinfo is None:published=published.replace(tzinfo=UTC)
        if not reference-dt.timedelta(days=max_age_days)<=published<=reference:continue
        body=item.get('official_body') or []
        text='\n'.join([item.get('title',''),item.get('summary','')]+(body if isinstance(body,list) else [str(body)]))
        for w in windows(text,published.astimezone(BEIJING)):
            start=dt.datetime.fromisoformat(w['start_at']);end=dt.datetime.fromisoformat(w['end_at'])
            if end<=reference or start>reference+dt.timedelta(days=ahead_days):continue
            head=item.get('title','')+text[:400]
            rows.append(dict(item_id=path.stem,title=item.get('title'),url=item.get('url'),source_type=item.get('source_type'),game_region=item.get('game_region'),
                             published=item['published'],already_in_ledger=path.stem in known,
                             kind_guess='offline' if OFFLINE.search(head) else 'collab' if COLLAB.search(head) else 'online',
                             scale_guess='minor' if MINOR.search(item.get('title','')) else 'main',**w,label=status(start,end,reference)['label']))
    return sorted(rows,key=lambda r:(SCALES[r['scale_guess']],r['end_at']))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['list','scan']);parser.add_argument('--series',required=True,choices=['arknights','endfield'])
    parser.add_argument('--at',help='ISO time to evaluate at (default now)')
    args=parser.parse_args();at=dt.datetime.fromisoformat(args.at) if args.at else None
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8')).get('freshness',{}).get('effective_window',{}).get('active_window',{})
    rows=running(ROOT,args.series,at,cfg.get('ahead_days',7)) if args.command=='list' else scan(ROOT,args.series,at,cfg.get('ahead_days',7),cfg.get('max_announcement_age_days',30))
    sys.stdout.buffer.write((json.dumps(rows,ensure_ascii=False,indent=1)+'\n').encode('utf-8'))
