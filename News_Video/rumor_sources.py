"""Unofficial AI rumors (new models first): read-only collection, import gate, ledger.

User decision 2026-11-09: the AI edition opens with rumors, then media reports,
then official news. A rumor scene is never presented as fact. Collection uses
Agent Reach read-only; it never logs in, rotates accounts or retries a block.

    python -B rumor_sources.py collect          # watch accounts + model searches
    python -B rumor_sources.py ledger           # open rumors for follow-up
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path
import news_video as n
from content_rules import check_rumor_narration,check_public_words,screen

STOP_CODES={'NEED_SETUP','NEED_LOGIN','UPSTREAM_BROKEN','TIMEOUT','RATE_LIMITED','PLATFORM_BLOCKED','BUSY','LOCAL_PERMISSION_DENIED'}
EVIDENCE_TYPES={'tierA_source','two_independent','artifact'}
CREDIBILITY={'较可信','待观察','存疑'}
OFFICIAL_STATUS={'未回应','已否认','已部分确认'}
SEARCH_ID='rumor-x-search'

def registry(root=None):
    return n.load(Path(root or n.ROOT)/'rumor_sources.json')

def accounts(root=None):
    return [a for a in registry(root)['watch_accounts'] if a.get('enabled') and a.get('identity_checked')]

def tier_of(handle,root=None):
    found=next((a for a in registry(root)['watch_accounts'] if a['handle'].lower()==str(handle or '').lower()),None)
    return found['tier'] if found else 'C'

def queries(root=None,offset=0):
    reg=registry(root);signals=reg['search']['signals']
    out=[]
    for family in reg['model_watchlist']:
        terms=' OR '.join(f'"{t}"' if ' ' in t else t for t in family['terms'])
        out.append(dict(family=family['family'],vendor=family['vendor'],query=f'({terms}) ({" OR ".join(signals)})'))
    limit=reg['search']['max_queries_per_run']
    # Rotate so every family is searched within a few runs without a long burst.
    start=offset%len(out) if out else 0
    return (out[start:]+out[:start])[:limit]

def run_reach(args,timeout=60):
    executable=shutil.which(n.config().get('x_collection',{}).get('executable','agent-reach'))
    if not executable:return dict(ok=False,error=dict(code='NEED_SETUP'))
    env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
    from quiet_background import hidden_kwargs,quiet_reach
    try:
        with quiet_reach():
            process=subprocess.run([executable,*args,'--timeout',str(timeout)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout+20,env=env,**hidden_kwargs())
        result=json.loads(process.stdout.lstrip('﻿'))
        return result if isinstance(result,dict) and isinstance(result.get('ok'),bool) else dict(ok=False,error=dict(code='UPSTREAM_BROKEN'))
    except subprocess.TimeoutExpired:return dict(ok=False,error=dict(code='TIMEOUT'))
    except (json.JSONDecodeError,ValueError):return dict(ok=False,error=dict(code='UPSTREAM_BROKEN'))
    except OSError:return dict(ok=False,error=dict(code='NEED_SETUP'))

def normalize(item,now,hours=48,root=None,source_id=SEARCH_ID,query=None):
    """A dated, authored post with a body; search URLs (x.com/i/status) get the author's path."""
    raw=item.get('raw') or {}
    author=(item.get('author') or raw.get('author') or '').lstrip('@')
    status=re.search(r'/status/(\d+)',item.get('url') or '')
    if not author or not status:raise ValueError('Missing author or status id')
    url=n.normalized_url(f'https://x.com/{author}/status/{status.group(1)}',allow_x=True)
    body=n.text(item.get('text') or raw.get('text') or '')
    if len(body)<8:raise ValueError('Missing or insufficient post body')
    published=n.parse_date(item.get('published_at') or raw.get('created_at'))
    if not published:raise ValueError('Missing original publication time')
    stamp=dt.datetime.fromisoformat(published)
    if not now-dt.timedelta(hours=hours)<=stamp<=now+dt.timedelta(minutes=15):raise ValueError('Outside fresh-news window')
    quote=raw.get('quoted_tweet') or {}
    quoted=dict(author=quote.get('author',''),text=n.text(quote.get('text',''))) if quote.get('text') else None
    key=hashlib.sha256(url.encode()).hexdigest()[:20]
    likes=raw.get('likes');views=raw.get('views')
    return dict(id=key,source_id=source_id,source_type='rumor_x',kind='ai',url=url,author=author,handle=author,tier=tier_of(author,root),
                published=published,raw_published=item.get('published_at') or raw.get('created_at'),time_basis='original_publication',
                title=body[:180],original_text=item.get('text') or raw.get('text') or '',summary=body+('\n[引用 @'+quoted['author']+'] '+quoted['text'] if quoted else ''),
                quoted=quoted,likes=likes if isinstance(likes,int) else None,views=views if isinstance(views,int) else None,
                has_media=bool(raw.get('has_media')),query=query,fetched_at=now.isoformat())

def store(db,post,root=None):
    root=Path(root or n.ROOT)
    from freshness import time_evidence
    n.dump(root/'data/rumors'/(post['id']+'.json'),post)
    n.dump(root/'data/time-evidence'/(post['id']+'.json'),time_evidence(post))
    existed=db.execute('SELECT id FROM items WHERE id=?',(post['id'],)).fetchone()
    now=post['fetched_at']
    db.execute('''INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
        last_seen=excluded.last_seen,title=excluded.title,summary=excluded.summary,content_hash=excluded.content_hash''',
        (post['id'],post['source_id'],'@'+post['handle'],'ai',post['title'],post['url'],post['published'],post['summary'],now,now,hashlib.sha256(post['summary'].encode()).hexdigest()))
    db.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?)',(post['id'],post['source_id'],now))
    return not existed

def collect(hours=48,runner=run_reach,sleep=time.sleep,root=None):
    """Watch accounts, then rotating model-family searches; stop a channel on the first block."""
    root=Path(root or n.ROOT);reg=registry(root);now=dt.datetime.now(n.UTC)
    state_path=root/'data/rumor-collection-state.json'
    state=n.load(state_path) if state_path.is_file() else {}
    report=dict(kind='rumors',started=now.isoformat(),model_calls=0,sources=[],accepted=0,new_items=0,stopped=False)
    if state.get('retry_after_utc') and dt.datetime.fromisoformat(state['retry_after_utc'])>now:
        report.update(stopped=True,reason='COOLDOWN',retry_after_utc=state['retry_after_utc']);return report
    if state.get('reason') in {'NEED_LOGIN','PLATFORM_BLOCKED'}:
        report.update(stopped=True,reason=state['reason'],requires_user_resolution=True);return report
    spacing=reg['search'].get('spacing_seconds',10);floor=reg['search'].get('min_engagement',{}).get('likes',0)
    jobs=[(a['id'],['twitter','tweets',a['handle'],'--limit',str(a.get('limit',8))],None,a['handle']) for a in accounts(root)]
    jobs+=[(SEARCH_ID,['twitter','search',q['query'],'--limit',str(reg['search']['limit_per_query'])],q['query'],None) for q in queries(root,state.get('query_offset',0))]
    db=n.database()
    try:
        for index,(source_id,args,query,handle) in enumerate(jobs):
            if index:sleep(spacing)
            result=runner(args)
            status=dict(source_id=source_id,query=query,handle=handle,ok=result['ok'],accepted=0,rejected=0)
            if not result['ok']:
                code=result.get('error',{}).get('code','UPSTREAM_BROKEN');status['error_code']=code;report['sources'].append(status)
                if code=='NOT_FOUND':continue
                delay=result.get('error',{}).get('retry_after_seconds',300)
                report.update(stopped=True,reason=code,retry_after_utc=(now+dt.timedelta(seconds=max(int(delay or 300),300))).isoformat());break
            for item in result.get('items',[]):
                try:post=normalize(item,now,hours,root,source_id,query)
                except (ValueError,TypeError,AttributeError):status['rejected']+=1;continue
                if handle and post['handle'].lower()!=handle.lower():status['rejected']+=1;continue
                # Searches surface noise: keep engaged posts or posts by tracked accounts.
                if query and post['tier']=='C' and (post['likes'] or 0)<floor:status['rejected']+=1;continue
                if screen(post['summary'],root,allow=('flamewar','spoiler')):status['rejected']+=1;continue
                report['new_items']+=int(store(db,post,root));status['accepted']+=1;report['accepted']+=1
            report['sources'].append(status)
        db.commit()
    finally:db.close()
    report['finished']=dt.datetime.now(n.UTC).isoformat()
    n.dump(state_path,dict(report,query_offset=state.get('query_offset',0)+reg['search']['max_queries_per_run']))
    return report

# --- Import gate --------------------------------------------------------------
def evidence_record(item_id,root=None):
    """Archived rumor post (X) or a collected rumor-feed item (Reddit)."""
    root=Path(root or n.ROOT);path=root/'data/rumors'/(str(item_id)+'.json')
    if path.is_file():return n.load(path)
    db=n.database()
    try:row=db.execute('SELECT * FROM items WHERE id=?',(item_id,)).fetchone()
    finally:db.close()
    if not row:raise ValueError('RUMOR_SOURCE_NOT_COLLECTED: '+str(item_id))
    row=dict(row);catalog={s['id']:s for s in n.load(root/'sources.json')}
    source=catalog.get(row['source_id'],{})
    if not source.get('rumor'):raise ValueError('RUMOR_SOURCE_NOT_RUMOR_FEED: '+str(item_id))
    return dict(id=row['id'],source_id=row['source_id'],source_type='rumor_'+source.get('rumor_platform','feed'),url=row['url'],
                author=source.get('name'),handle=source.get('name'),tier=source.get('tier','C'),summary=row['summary'] or row['title'],title=row['title'])

def is_rumor_item(row,catalog):
    return str(row.get('source_id','')).startswith('rumor-x-') or bool(catalog.get(row.get('source_id'),{}).get('rumor'))

def validate_scene(scene,root=None):
    """Rumor scene contract: concrete claim, collected sources, evidence rule, honest narration."""
    root=Path(root or n.ROOT)
    if scene.get('scene_type')!='rumor':raise ValueError('RUMOR_SCENE_TYPE: a rumor source must be presented as scene_type=rumor')
    claim=str(scene.get('claim','')).strip()
    if len(claim)<6:raise ValueError('RUMOR_CLAIM_REQUIRED: name the model/feature/time being claimed')
    ids=list(dict.fromkeys([scene['item_id']]+list(scene.get('rumor_sources') or [])))
    records=[evidence_record(i,root) for i in ids]
    evidence_type=scene.get('evidence_type')
    if evidence_type not in EVIDENCE_TYPES:raise ValueError('RUMOR_EVIDENCE_TYPE: use tierA_source, two_independent or artifact')
    authors={str(r.get('handle') or r.get('author') or r['url']).lower() for r in records}
    if evidence_type=='tierA_source' and not any(r.get('tier')=='A' for r in records):raise ValueError('RUMOR_EVIDENCE: no tier-A source among the cited posts')
    if evidence_type=='two_independent' and len(authors)<2:raise ValueError('RUMOR_EVIDENCE: two independent authors are required')
    if evidence_type=='artifact':
        artifact=scene.get('artifact') or {}
        quote=str(artifact.get('quote','')).strip()
        if not artifact.get('kind') or len(quote)<3 or not any(quote in (r.get('summary','')+'\n'+r.get('original_text','')) for r in records):
            raise ValueError('RUMOR_EVIDENCE: artifact needs kind and a quote found in a cited post')
    if scene.get('credibility') not in CREDIBILITY:raise ValueError('RUMOR_CREDIBILITY: 较可信/待观察/存疑')
    if scene.get('credibility')=='较可信' and evidence_type=='two_independent' and not any(r.get('tier') in {'A','B'} for r in records):
        raise ValueError('RUMOR_CREDIBILITY: two C-tier posts cannot be 较可信')
    unknowns=scene.get('unknowns')
    if not isinstance(unknowns,list) or not [u for u in unknowns if str(u).strip()]:raise ValueError('RUMOR_UNKNOWNS_REQUIRED')
    status=scene.get('official_status')
    if status not in OFFICIAL_STATUS:raise ValueError('RUMOR_OFFICIAL_STATUS: 未回应/已否认/已部分确认')
    if scene.get('rumor_safety_checked') is not True:
        raise ValueError('RUMOR_SAFETY_REVIEW: confirm no private life, minors or personal attacks (rumor_safety_checked=true)')
    names=[r.get('handle') for r in records]+[r.get('author') for r in records]+list(scene.get('source_spoken_names') or [])
    if any(r['source_type']=='rumor_reddit' for r in records):names.append('Reddit')
    check_rumor_narration(scene.get('narration',''),[x for x in names if x],status)
    check_public_words(scene.get('title',''),root,rumor=True)
    card=scene.get('quote_card')
    if card:
        # The original post as an on-screen text card: account, Beijing time, excerpt, Chinese translation below.
        excerpt=str(card.get('excerpt','')).strip()
        if not excerpt or len(excerpt)>90 or not any(excerpt in (r.get('original_text','')+'\n'+r.get('summary','')) for r in records):
            raise ValueError('RUMOR_QUOTE_CARD: excerpt (<=90 chars) must be copied from a cited post')
        label=str(card.get('account') or records[0].get('handle'))+' · '+str(card.get('time_label',''))
        detail=excerpt+(('　译：'+str(card['translation']).strip()) if card.get('translation') else '')
        facts=scene.setdefault('facts',[])
        if not facts or not isinstance(facts[0],dict) or facts[0].get('quote_card')!=True:
            facts.insert(0,dict(title='原帖 '+label.strip(' ·'),detail=detail,quote_card=True))
    scene['rumor_audit']=dict(sources=[dict(item_id=r['id'],url=r['url'],handle=r.get('handle'),tier=r.get('tier')) for r in records],
                             evidence_type=evidence_type,independent_authors=len(authors))
    scene.setdefault('badge','传闻·未经官方证实')
    return scene['rumor_audit']

# --- Ledger -----------------------------------------------------------------
def ledger_path(root=None):return Path(root or n.ROOT)/'data/rumor-ledger.jsonl'

def ledger(root=None):
    path=ledger_path(root)
    if not path.is_file():return {}
    out={}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row=json.loads(line);out[row['key']]=row
    return out

def rumor_key(scene):
    return scene.get('rumor_key') or 'rumor:'+hashlib.sha256(re.sub(r'\s+','',scene['claim']).casefold().encode()).hexdigest()[:16]

def check_ledger(episode,root=None,now=None):
    """Same rumor within 7 days needs new evidence; follow-ups must say the earlier rumor's outcome."""
    entries=ledger(root);now=now or dt.datetime.now(n.UTC);changes=[]
    for scene in episode['scenes']:
        if scene.get('scene_type')=='rumor':
            key=rumor_key(scene);scene['rumor_key']=key;previous=entries.get(key)
            sources=set([scene['item_id']]+list(scene.get('rumor_sources') or []))
            if previous and previous['last_episode']!=episode['id'] and dt.datetime.fromisoformat(previous['last_reported_at'])>now-dt.timedelta(days=7):
                if not sources-set(previous.get('sources',[])):raise ValueError('RUMOR_REPEATED: '+key+' was reported within 7 days; add new evidence or skip')
            changes.append(dict(key=key,claim=scene['claim'],status=scene['official_status'],sources=sorted(sources),episode=episode['id']))
        resolve=scene.get('resolves_rumor')
        if resolve:
            if resolve.get('key') not in entries:raise ValueError('RUMOR_FOLLOWUP_UNKNOWN: '+str(resolve.get('key')))
            if resolve.get('status') not in {'confirmed','denied'}:raise ValueError('RUMOR_FOLLOWUP_STATUS: confirmed or denied')
            if scene.get('scene_type')=='rumor':raise ValueError('RUMOR_FOLLOWUP_SOURCE: resolve a rumor with an official or media scene')
            if not re.search(r'此前.{0,12}传闻|传闻.{0,12}(?:官宣|落地|成真|被否认|辟谣)',scene.get('narration','')):
                raise ValueError('RUMOR_FOLLOWUP_NARRATION: say that the earlier rumor was confirmed/denied')
            changes.append(dict(key=resolve['key'],claim=entries[resolve['key']]['claim'],status=resolve['status'],sources=entries[resolve['key']].get('sources',[]),episode=episode['id'],resolved_by=scene.get('item_id')))
    return changes

def record_ledger(changes,root=None,now=None):
    if not changes:return
    entries=ledger(root);now=(now or dt.datetime.now(n.UTC)).isoformat()
    for change in changes:
        row=entries.get(change['key'],dict(key=change['key'],first_episode=change['episode'],first_reported_at=now))
        row.update(claim=change['claim'],status=change['status'],last_episode=change['episode'],last_reported_at=now,
                   sources=sorted(set(row.get('sources',[]))|set(change.get('sources',[]))))
        if change.get('resolved_by'):row['resolved_by']=change['resolved_by']
        entries[change['key']]=row
    path=ledger_path(root);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in entries.values()),encoding='utf-8')

def open_rumors(root=None,days=30):
    cutoff=dt.datetime.now(n.UTC)-dt.timedelta(days=days)
    return [r for r in ledger(root).values() if r['status'] not in {'confirmed','denied'} and dt.datetime.fromisoformat(r['last_reported_at'])>cutoff]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['collect','ledger']);parser.add_argument('--hours',type=int,default=48)
    args=parser.parse_args()
    if args.action=='collect':print(json.dumps(collect(args.hours),ensure_ascii=False,indent=2))
    else:print(json.dumps(open_rumors(),ensure_ascii=False,indent=2))
