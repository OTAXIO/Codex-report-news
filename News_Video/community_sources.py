"""玩家热议: what B站 players discuss about one game (2026-11-09 user decision).

Per game: the most-played videos of the last 48h and the newest videos above a
small engagement floor; for each, the rendered comment section sorted by 最热
and by 最新, plus public danmaku. Only text, like counts and video facts are
kept: no usernames, avatars or UIDs. Reading needs a dedicated local Chrome
profile that the user logged into once (a secondary account); the program never
logs in, exports cookies, signs or replays requests, and stops on any
verification page.

    python -B community_sources.py login                     # opens a window; the user logs in
    python -B community_sources.py login-check
    python -B community_sources.py collect --series endfield
    python -B community_sources.py topics <item_id>          # glossary mentions per video
    python -B community_sources.py glossary-candidates       # new official terms to review
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,re,subprocess,tempfile,urllib.parse,zlib
from pathlib import Path
import news_video as n
from content_rules import screen,check_public_words

SERIES={'arknights','endfield'}
CN=dt.timezone(dt.timedelta(hours=8))

def policy(root=None):
    return n.load(Path(root or n.ROOT)/'config.json').get('community',{})

def glossary(root=None):
    return n.load(Path(root or n.ROOT)/'game_glossary.json')['games']

def runtime(root=None):
    """Browser/puppeteer paths are shared with the uploader runtime; the profile is the reader's own."""
    root=Path(root or n.ROOT);cfg=n.load(root/'config.json');pol=cfg.get('community',{})
    home=(root/cfg.get('publisher',{}).get('private_home','../../.codex-upload-private')).resolve()
    shared=n.load(home/'runtime.local.json') if (home/'runtime.local.json').is_file() else {}
    profile=(root/pol.get('profile_directory','../../.community-reader-private/chrome-profile')).resolve()
    upload_profile=(home/'profile').resolve()
    if profile==upload_profile or upload_profile in profile.parents:raise ValueError('COMMUNITY_PROFILE: never reuse the upload profile')
    return dict(node=pol.get('node_executable') or shared.get('node_executable') or 'node',
                browser_executable=pol.get('browser_executable') or shared.get('browser_executable'),
                puppeteer_module=pol.get('puppeteer_module') or shared.get('puppeteer_module'),profile_dir=str(profile))

def run_reader(job,root=None,timeout=900):
    root=Path(root or n.ROOT);rt=runtime(root)
    Path(rt['profile_dir']).mkdir(parents=True,exist_ok=True)
    job=dict(job,profile_dir=rt['profile_dir'],browser_executable=rt['browser_executable'],puppeteer_module=rt['puppeteer_module'],
             interval_ms=[int(x*1000) for x in policy(root).get('page_interval_seconds',[3,5])])
    with tempfile.NamedTemporaryFile('w',suffix='.json',delete=False,encoding='utf-8') as handle:
        json.dump(job,handle,ensure_ascii=False);path=handle.name
    try:
        process=subprocess.run([rt['node'],str(root/'community_reader.mjs'),path],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        try:return json.loads(process.stdout.strip().splitlines()[-1])
        except (ValueError,IndexError):return dict(ok=False,error=dict(code='UPSTREAM_BROKEN',message=(process.stderr or '')[-300:]))
    except subprocess.TimeoutExpired:return dict(ok=False,error=dict(code='TIMEOUT'))
    finally:os.unlink(path)

# --- Card parsing -----------------------------------------------------------
def count(value):
    value=str(value or '').strip()
    match=re.fullmatch(r'([\d.]+)\s*(万|亿)?',value)
    if not match:return None
    return int(float(match.group(1))*{'万':10_000,'亿':100_000_000}.get(match.group(2),1))

def card_time(text,now):
    """B站 card dates: 刚刚 / N分钟前 / N小时前 / 昨天 / MM-DD / YYYY-MM-DD / YYYY年M月D日 / M月D日."""
    text=str(text or '').strip();local=now.astimezone(CN)
    if text=='刚刚':return now
    m=re.fullmatch(r'(\d+)\s*分钟前',text)
    if m:return now-dt.timedelta(minutes=int(m.group(1)))
    m=re.fullmatch(r'(\d+)\s*小时前',text)
    if m:return now-dt.timedelta(hours=int(m.group(1)))
    m=re.fullmatch(r'(\d+)\s*天前',text)
    if m:return now-dt.timedelta(days=int(m.group(1)))
    if text.startswith('昨天'):return (local-dt.timedelta(days=1)).replace(hour=12,minute=0,second=0,microsecond=0)
    m=re.fullmatch(r'(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?',text) or re.fullmatch(r'(\d{1,2})[-月](\d{1,2})日?',text)
    if m:
        parts=[int(x) for x in m.groups()];year,month,day=parts if len(parts)==3 else [local.year]+parts
        return dt.datetime(year,month,day,12,tzinfo=CN)
    return None

def title_matches(series,title,root=None):
    games=glossary(root);spec=games[series]
    return any(name in title for name in spec['names']) and not any(x in title for x in spec.get('exclude_title_terms',[]))

def choose_videos(series,searches,now,root=None):
    """Most-played in the window + newest above the floor; topic, safety and window checked."""
    pol=policy(root);rows={};report=[]
    for search in searches:
        hot=search['label']=='hot'
        for rank,card in enumerate(search['cards']):
            published=card_time(card.get('date'),now);plays=count((card.get('stats') or [None])[0]);danmaku=count((card.get('stats') or [None,None])[1])
            reason=None
            if not title_matches(series,card['title'],root):reason='other_topic'
            elif screen(card['title'],root,allow=('spoiler',)):reason='content_filter'
            elif published is None or published<now-dt.timedelta(hours=48):reason='outside_48h'
            elif not hot and (plays or 0)<pol.get('min_plays_newest',200) and (danmaku or 0)<pol.get('min_comments_newest',10):reason='below_engagement_floor'
            report.append(dict(bvid=card['bvid'],label=search['label'],rank=rank,reason=reason or 'selected_candidate'))
            if reason or card['bvid'] in rows:continue
            rows[card['bvid']]=dict(bvid=card['bvid'],title=card['title'],plays=plays,danmaku_count=danmaku,published=published.isoformat(),picked_by=search['label'],search_rank=rank)
    hot=sorted([r for r in rows.values() if r['picked_by']=='hot'],key=lambda r:-(r['plays'] or 0))[:5]
    newest=[r for r in rows.values() if r['picked_by']=='newest' and r not in hot][:3]
    return (hot+newest)[:pol.get('max_videos_per_game',8)],report

def search_jobs(series,now,root=None):
    """B站 ignores pubtime_* when order=click (verified 2026-11-09: all-time PVs come back),
    so 'hot' reads the default order inside the 48h window over a few pages and
    choose_videos ranks by plays itself. One page of the newest videos follows."""
    keyword=glossary(root)[series]['names'][0]
    q=urllib.parse.quote(keyword);end=int(now.timestamp());begin=end-48*3600
    base=f'https://search.bilibili.com/video?keyword={q}'
    pages=max(1,policy(root).get('max_searches_per_game',4)-1)
    hot=[dict(label='hot',url=f'{base}&pubtime_begin_s={begin}&pubtime_end_s={end}'+(f'&page={p}' if p>1 else '')) for p in range(1,pages+1)]
    return hot+[dict(label='newest',url=f'{base}&order=pubdate')]

def danmaku(bvid,limit=200):
    """Public danmaku; anonymous and read-only."""
    head={'User-Agent':'Mozilla/5.0','Referer':'https://www.bilibili.com'}
    import urllib.request
    view=json.loads(urllib.request.urlopen(urllib.request.Request('https://api.bilibili.com/x/web-interface/view?bvid='+bvid,headers=head),timeout=20).read())
    raw=urllib.request.urlopen(urllib.request.Request(f"https://comment.bilibili.com/{view['data']['cid']}.xml",headers=head),timeout=20).read()
    try:raw=zlib.decompress(raw,-zlib.MAX_WBITS)
    except zlib.error:pass
    import html
    return [html.unescape(t).strip() for t in re.findall(r'<d [^>]*>([^<]*)</d>',raw.decode('utf-8','replace'))][:limit]

def clean(items,root=None):
    kept=[];dropped=0;seen=set()
    for item in items:
        text=re.sub(r'\s+',' ',str(item.get('text',''))).strip()[:200]
        if not text or text in seen:continue
        seen.add(text)
        if screen(text,root):dropped+=1;continue
        kept.append(dict(item,text=text))
    return kept,dropped

def collect(series,root=None,reader=run_reader,read_danmaku=danmaku,now=None):
    if series not in SERIES:raise ValueError('Use --series arknights or endfield')
    root=Path(root or n.ROOT);now=now or dt.datetime.now(n.UTC)
    report=dict(kind='community',series=series,started=now.isoformat(),ok=False)
    result=reader(dict(mode='search',searches=search_jobs(series,now,root)),root)
    if not result.get('ok'):report.update(error=result.get('error'));return report
    videos,choices=choose_videos(series,result['searches'],now,root)
    report['selection']=choices
    if not videos:report.update(error=dict(code='NO_QUALIFIED_VIDEOS'));return report
    result=reader(dict(mode='comments',videos=[v['bvid'] for v in videos],scrolls=5),root)
    if not result.get('ok'):report.update(error=result.get('error'));return report
    read={v['bvid']:v for v in result['videos']};dropped=0
    for video in videos:
        page=read.get(video['bvid'],{})
        for sort in ('hot','newest'):
            raw=[dict(text=c['text'],likes=count(c.get('likes')) or 0,sort=sort) for c in page.get('sorts',{}).get(sort,{}).get('comments',[])]
            video['comments_'+sort],d=clean(raw,root);dropped+=d
        video['comment_header']=page.get('header')
        try:video['danmaku'],d=clean([dict(text=t) for t in read_danmaku(video['bvid'])],root);dropped+=d
        except Exception as error:video['danmaku']=[];video['danmaku_error']=type(error).__name__
    key=hashlib.sha256(f'community-{series}:{now.isoformat()}'.encode()).hexdigest()[:20]
    title={'arknights':'明日方舟','endfield':'明日方舟：终末地'}[series]+' B站玩家热议素材'
    snapshot=dict(id=key,source_id='community-'+series,game=series,game_region='cn',game_topic='other',source_type='community',
                  url=search_jobs(series,now,root)[0]['url'],published=now.isoformat(),raw_published=now.isoformat(),time_basis='original_publication',
                  title=title,videos=videos,dropped_by_filter=dropped,collected_at=now.isoformat(),
                  privacy='No usernames, avatars or UIDs are read or stored.')
    snapshot['summary']=f"{len(videos)} 个视频；"+'；'.join(v['title'][:30] for v in videos)
    from freshness import time_evidence
    n.dump(root/'data/community'/(key+'.json'),snapshot)
    n.dump(root/'data/time-evidence'/(key+'.json'),time_evidence(snapshot))
    n.dump(root/'data/game-items'/(key+'.json'),{k:snapshot[k] for k in ('game','game_region','game_topic','source_type','title','url','published','summary')}|dict(source_id=snapshot['source_id']))
    db=n.database()
    try:
        db.execute('''INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,summary=excluded.summary''',
                   (key,snapshot['source_id'],'B站玩家','games',title,snapshot['url'],snapshot['published'],snapshot['summary'],now.isoformat(),now.isoformat(),hashlib.sha256(snapshot['summary'].encode()).hexdigest()))
        db.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?)',(key,snapshot['source_id'],now.isoformat()));db.commit()
    finally:db.close()
    report.update(ok=True,item_id=key,videos=len(videos),samples=sum(len(v['comments_hot'])+len(v['comments_newest'])+len(v['danmaku']) for v in videos),dropped_by_filter=dropped)
    return report

# --- Topics & import gate ---------------------------------------------------------
def snapshot(item_id,root=None):
    path=Path(root or n.ROOT)/'data/community'/(str(item_id)+'.json')
    if not path.is_file():raise ValueError('COMMUNITY_NOT_COLLECTED: '+str(item_id))
    return n.load(path)

def samples(snap,bvids):
    texts=[];seen=set()
    for video in snap['videos']:
        if video['bvid'] not in bvids:continue
        for item in video.get('comments_hot',[])+video.get('comments_newest',[])+video.get('danmaku',[]):
            if item['text'] not in seen:seen.add(item['text']);texts.append(item)
    return texts

def term(series,name,root=None):
    return next((t for t in glossary(root)[series]['terms'] if t['name']==name),None)

def topics(item_id,root=None):
    """Reviewed glossary terms ranked by how many samples mention them, per video."""
    snap=snapshot(item_id,root);series=snap['game'];out=[]
    for t in glossary(root)[series]['terms']:
        rows=[]
        for video in snap['videos']:
            hits=[s for s in samples(snap,{video['bvid']}) if t['name'] in s['text']]
            if hits:rows.append(dict(bvid=video['bvid'],title=video['title'],mentions=len(hits)))
        if rows:out.append(dict(entity_name=t['name'],entity_type=t['type'],reviewed=t['reviewed'],mentions=sum(r['mentions'] for r in rows),videos=rows))
    out.sort(key=lambda x:-x['mentions'])
    return dict(item_id=item_id,series=series,total_samples=len(samples(snap,{v['bvid'] for v in snap['videos']})),topics=out)

OPINION=re.compile(r'认为|觉得|吐槽|期待|担心|称赞|质疑|争议|讨论|调侃|好评|不满')

def validate_scene(scene,episode,root=None):
    """A topic must belong to this game: reviewed term, matching videos, enough direct mentions."""
    root=Path(root or n.ROOT);snap=snapshot(scene['item_id'],root);series=episode.get('edition_series') or snap['game']
    if scene.get('scene_type')!='community_pulse':raise ValueError('COMMUNITY_SCENE_TYPE: use scene_type=community_pulse')
    if sum(1 for s in episode['scenes'] if s.get('scene_type')=='community_pulse')>3:raise ValueError('COMMUNITY_TOPICS: at most three topics per edition')
    subject=scene.get('subject') or {}
    if not (subject.get('game')==scene.get('game')==snap['game']==series):raise ValueError('COMMUNITY_SUBJECT_MISMATCH: topic game differs from this edition')
    entry=term(series,subject.get('entity_name'),root)
    if not entry or not entry['reviewed'] or entry['type']!=subject.get('entity_type'):
        raise ValueError('COMMUNITY_SUBJECT_MISMATCH: '+str(subject.get('entity_name'))+' is not a reviewed '+str(subject.get('entity_type'))+' of '+series)
    other='endfield' if series=='arknights' else 'arknights'
    shared=term(other,subject['entity_name'],root) is not None
    bvids=set(scene.get('videos') or [])
    known={v['bvid']:v for v in snap['videos']}
    if not bvids or not bvids<=set(known):raise ValueError('COMMUNITY_VIDEOS: cite collected videos of this snapshot')
    for bvid in bvids:
        if not title_matches(series,known[bvid]['title'],root):raise ValueError('COMMUNITY_SUBJECT_MISMATCH: video '+bvid+' is not about '+series)
        if shared and not any(name in known[bvid]['title'] for name in glossary(root)[series]['names']):
            raise ValueError('COMMUNITY_SUBJECT_MISMATCH: shared term needs the game name in every video title')
    texts=samples(snap,bvids);minimum=policy(root).get('minimum_samples',30)
    mentions=[s for s in texts if subject['entity_name'] in s['text']]
    if len(texts)<minimum:raise ValueError(f'COMMUNITY_SAMPLES: {len(texts)} screened samples, need {minimum}')
    if len(mentions)<5:raise ValueError('COMMUNITY_SUBJECT_MISMATCH: fewer than 5 samples mention '+subject['entity_name'])
    if scene.get('sample_count')!=len(texts):raise ValueError(f'COMMUNITY_SAMPLE_COUNT: use {len(texts)} (from topics) and say it in narration')
    narration=scene.get('narration','')
    if str(len(texts)) not in narration:raise ValueError('COMMUNITY_SAMPLE_COUNT: say the sample count in narration')
    if '玩家' not in narration or not OPINION.search(narration):raise ValueError('COMMUNITY_OPINION_LABEL: say these are players\' views (玩家…认为/觉得)')
    if '@' in narration or screen(narration,root,allow=('flamewar',)):raise ValueError('COMMUNITY_NARRATION_FILTER')
    quotes=scene.get('quotes') or []
    if len(quotes)>3:raise ValueError('COMMUNITY_QUOTES: at most three quotes per topic')
    pool='\n'.join(s['text'] for s in texts)
    for quote in quotes:
        quote=str(quote)
        if len(quote)>20 or quote not in pool or screen(quote,root):raise ValueError('COMMUNITY_QUOTE_INVALID: '+quote)
    check_public_words(scene.get('title',''),root)
    scene['community_audit']=dict(entity=subject,samples=len(texts),mentions=len(mentions),videos=sorted(bvids),shared_term=shared,collected_at=snap['collected_at'])
    return scene['community_audit']

def glossary_candidates(root=None,days=60):
    """Bracketed names in recent official posts that the glossary does not have yet."""
    root=Path(root or n.ROOT);cut=(dt.datetime.now(n.UTC)-dt.timedelta(days=days)).isoformat();out={g:{} for g in SERIES}
    known={g:{t['name'] for t in spec['terms']}|set(spec['names']) for g,spec in glossary(root).items()}
    for path in (root/'data/game-items').glob('*.json'):
        item=n.load(path)
        if item.get('game') not in SERIES or (item.get('published') or '')<cut or item.get('source_type')=='community':continue
        text=' '.join([item.get('title','')]+[str(x) for x in item.get('official_body') or []]+[item.get('summary','')])
        article=root/'data/articles'/path.name
        if article.is_file():text+=' '+n.load(article).get('text','')
        for name in re.findall(r'[「【《]([^」】》\n]{2,12})[」】》]',text):
            if name not in known[item['game']]:out[item['game']][name]=out[item['game']].get(name,0)+1
    return {g:sorted(v.items(),key=lambda kv:-kv[1])[:60] for g,v in out.items()}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['login','login-check','collect','topics','glossary-candidates'])
    parser.add_argument('target',nargs='?');parser.add_argument('--series',choices=sorted(SERIES))
    args=parser.parse_args()
    if args.action=='login':print(json.dumps(run_reader(dict(mode='login'),timeout=700),ensure_ascii=False))
    elif args.action=='login-check':print(json.dumps(run_reader(dict(mode='login-check'),timeout=120),ensure_ascii=False))
    elif args.action=='collect':print(json.dumps(collect(args.series),ensure_ascii=False,indent=2))
    elif args.action=='topics':print(json.dumps(topics(args.target),ensure_ascii=False,indent=2))
    else:print(json.dumps(glossary_candidates(),ensure_ascii=False,indent=2))
