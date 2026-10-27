"""Leader selection audit, verified identities, attributed speech and Tibo placement."""
import datetime as dt,json,re,sqlite3
from pathlib import Path
from contextlib import closing

HANDLE='thsottiaux'

def is_tibo(scene):
    return str(scene.get('author_handle',scene.get('handle','')) or '').lower()==HANDLE

def reset_reviewed(item,root):
    p=Path(root)/'data/reset-alerts/queue'/(item['id']+'.json')
    if not p.exists():return False
    r=json.loads(p.read_text(encoding='utf-8')).get('review',{})
    return r.get('is_reset_announcement') is True and r.get('context_verified') is True

def review_candidates(items,root):
    result=[]
    for item in items:
        if item.get('source_id')!='x-leader-thsottiaux' and not is_tibo(item):continue
        verified=reset_reviewed(item,root)
        item['tibo_message_type']='reset' if verified else 'needs_semantic_review'
        item['source_priority']=-10 if verified else 150
        result.append(dict(item_id=item['id'],url=item['url'],published=item['published'],text=item.get('summary',''),
                           requires_context=item.get('requires_context',False),reset_keyword_hint=bool(re.search(r'\breset\b|重置',item.get('summary',''),re.I)),
                           verified_reset=verified,required_action='Include on one Tibo page or record a factual skip/defer reason; keyword alone does not prove reset'))
    return result

def prepare_main_tibo(ep,root,now=None):
    if ep.get('edition_slot') not in {'morning','noon','night'}:return None
    from used_news import recent_records,exclude_used
    from layout_policy import is_overview
    root=Path(root);now=now or dt.datetime.now(dt.timezone.utc)
    dbpath=root/'data/news.sqlite3';items=[]
    if dbpath.exists():
        with closing(sqlite3.connect(dbpath)) as db:
            db.row_factory=sqlite3.Row
            cutoff=(now-dt.timedelta(hours=24)).isoformat()
            items=[dict(r) for r in db.execute("SELECT * FROM items WHERE source_id=? AND published>=? AND published<=?",('x-leader-thsottiaux',cutoff,now.isoformat()))]
    key=ep.get('edition_key',re.sub(r'-v\d+$','',ep['id']))
    items,_,_=exclude_used(items,[r for r in recent_records(root) if r['edition_key']!=key])
    selected=[s for s in ep['scenes'] if is_tibo(s)]
    if len(selected)>1:raise ValueError('Main edition permits one Tibo page; select the most important message and do not split into multiple scenes')
    included={s.get('item_id') for s in selected};decisions=ep.get('tibo_consideration',{})
    audit=[]
    for item in items:
        if item['id'] in included:decision=dict(decision='include',reason='Included on the single Tibo page')
        else:
            decision=decisions.get(item['id'],{})
            if decision.get('decision') not in {'skip','defer'} or not isinstance(decision.get('reason'),str) or not decision['reason'].strip():
                raise ValueError('Review fresh Tibo post '+item['id']+': include it or supply tibo_consideration[id] with skip/defer and actual reason')
        audit.append(dict(item_id=item['id'],url=item['url'],published=item['published'],**decision))
    placement='not_included'
    if selected:
        scene=selected[0];kind=scene.get('tibo_message_type');verified_recap=False
        if scene.get('editorial_role')=='recap':
            from important_events import recap_candidates,validate_recap
            events=recap_candidates(root)
            if any(e['kind']=='reset' and e['event_key']==scene.get('event_key') and e['url']==scene.get('recap_of') for e in events):
                validate_recap(scene,ep,root);kind='reset';verified_recap=True
        if kind not in {'reset','commentary'}:raise ValueError('Classify Tibo page as reset or commentary after reading its context')
        if kind=='commentary':
            source=root/'data/leader-posts'/(scene.get('item_id','')+'.json')
            post=json.loads(source.read_text(encoding='utf-8')) if source.exists() else {}
            if re.search(r'\breset\b|重置',post.get('summary',''),re.I):
                review=scene.get('reset_review',{})
                if review.get('is_reset_announcement') is not False or review.get('context_verified') is not True or not review.get('reason'):
                    raise ValueError('A reset keyword needs semantic review even when classified as commentary')
        if kind=='reset' and not verified_recap:
            review=scene.get('reset_review',{})
            source=root/'data/leader-posts'/(scene.get('item_id','')+'.json')
            post=json.loads(source.read_text(encoding='utf-8')) if source.exists() else {}
            if review.get('is_reset_announcement') is not True or review.get('context_verified') is not True or review.get('announcement_status') not in {'planned','ongoing','completed'} or not review.get('quote') or review['quote'] not in post.get('summary',''):
                raise ValueError('Tibo reset placement requires verified affirmative reset semantics, exact quote and accurate status')
        rest=[s for s in ep['scenes'] if not is_tibo(s)]
        if kind=='reset':index=next((i for i,s in enumerate(rest) if not is_overview(s)),len(rest));placement='before_company_news'
        else:index=next((i for i,s in enumerate(rest) if s.get('section','').startswith(('国内','国际'))),len(rest));placement='after_company_news'
        scene['section']='AI 动态';scene['tibo_message_type']=kind
        rest.insert(index,scene);ep['scenes']=rest
    return dict(max_pages=1,placement=placement,reviewed_posts=audit,no_fresh_unused_posts=not items)


def leader_registry(root):
    path=Path(root)/'leader_sources.json'
    if not path.exists():return {}
    return {s['handle'].lower():s for s in json.loads(path.read_text(encoding='utf-8'))['accounts'] if s.get('enabled') and s.get('identity_checked') and s.get('type')=='leader_x'}


def review_leader_candidates(items,root):
    registry=leader_registry(root);out=[]
    for item in items:
        source=next((s for s in registry.values() if s['id']==item.get('source_id')),None)
        if not source:continue
        out.append(dict(item_id=item['id'],handle=source['handle'],name=source['name'],identity_label=source.get('identity_label',source['vendor']),
                        published=item['published'],url=item['url'],text=item.get('summary',''),requires_context=item.get('requires_context',False),
                        selection_policy='Prefer a fresh, normal and interesting statement, including personal insight; otherwise explicitly skip/defer with the real reason.'))
    return out


def apply_leader_identity_and_speech(ep,root):
    registry=leader_registry(root)
    for scene in ep['scenes']:
        if scene.get('source_type')!='leader_x':continue
        archive=Path(root)/'data/leader-posts'/(scene.get('item_id','')+'.json')
        if archive.is_file():
            evidence=json.loads(archive.read_text(encoding='utf-8'))
            if evidence.get('handle','').lower()!=scene.get('author_handle','').lower():
                raise ValueError('Speaker does not match the archived original author')
            # Bind the introduction and source label to the original, never to
            # an editor-supplied timestamp or the collection clock.
            scene['published']=evidence.get('published','')
            if evidence.get('published_precision'):scene['published_precision']=evidence['published_precision']
        handle=scene.get('author_handle','').lower();source=registry.get(handle,{})
        name=source.get('name') or scene.get('publisher') or handle
        scene['speaker_name']=name
        scene['speaker_identity']=source.get('identity_label') or ('X 账号 @'+handle)
        # No invented job title: only the checked registry label reaches pixels.
        scene['speaker_identity_evidence']=source.get('identity_evidence','')
        published=scene.get('published','')
        try:stamp=dt.datetime.fromisoformat(published.replace('Z','+00:00'))
        except (ValueError,TypeError):continue
        if stamp.tzinfo is None or scene.get('published_precision')=='date':continue
        stamp=stamp.astimezone(dt.timezone(dt.timedelta(hours=8)))
        clock=f'北京时间{stamp.month}月{stamp.day}日{stamp.hour}点{stamp.minute}分'
        body=scene.get('narration','').strip()
        compact=re.sub(r'\s+','',body)
        if clock in compact and re.sub(r'\s+','',name).casefold() in compact.casefold():continue
        old_intro=scene.get('speaker_intro_text','')
        if old_intro and body.startswith(old_intro):body=body[len(old_intro):].lstrip()
        content=body
        # Keep the recap qualifier, then anchor the statement to original time.
        recap=''
        preamble='回顾此前的重要动态。据当时的原始消息，'
        if content.startswith(preamble):recap=preamble;content=content[len(preamble):]
        match=re.match(re.escape(name)+r'\s*(表示|提到|透露|认为|宣布|预告|提醒)[，,:：\s]*',content,re.I)
        if match:
            intro=recap+name+' 于'+clock+'发帖'+match.group(1)+'，'
            rest=content[match.end():]
        else:intro=recap+name+' 于'+clock+'发表推文。';rest=content
        scene['leader_content_narration']=body
        scene['speaker_intro_text']=intro;scene['narration']=intro+rest


def prepare_main_leaders(ep,root,now=None):
    if ep.get('edition_slot') not in {'morning','noon','night'}:return None
    from used_news import recent_records,exclude_used
    root=Path(root);now=now or dt.datetime.now(dt.timezone.utc);registry=leader_registry(root)
    dbpath=root/'data/news.sqlite3';rows=[]
    if dbpath.exists():
        with closing(sqlite3.connect(dbpath)) as db:
            db.row_factory=sqlite3.Row
            rows=[dict(r) for r in db.execute("SELECT * FROM items WHERE published>=? AND published<=?",((now-dt.timedelta(hours=24)).isoformat(),now.isoformat()))]
    key=ep.get('edition_key',re.sub(r'-v\d+$','',ep['id']))
    rows,_,_=exclude_used(rows,[r for r in recent_records(root) if r['edition_key']!=key])
    candidates=review_leader_candidates(rows,root);selected={s.get('item_id') for s in ep['scenes'] if s.get('source_type')=='leader_x'}
    decisions=ep.get('leader_consideration',{});audit=[]
    for item in candidates:
        if item['handle'].lower()==HANDLE:continue  # special Tibo policy below
        decision=dict(decision='include',reason='Presented with checked on-screen identity') if item['item_id'] in selected else decisions.get(item['item_id'],{})
        if decision.get('decision') not in {'include','skip','defer'} or not decision.get('reason'):
            raise ValueError('Review fresh leader post '+item['item_id']+': include or record leader_consideration[id] skip/defer and reason')
        if decision['decision']=='include' and item['item_id'] not in selected:raise ValueError('Included leader post is missing its video scene')
        audit.append(dict(item_id=item['item_id'],handle=item['handle'],**decision))
    tibo=prepare_main_tibo(ep,root,now)
    # Ordinary leader pages follow company AI news; the verified reset page
    # stays at the front. Never turn an unreviewed keyword into that exception.
    regular=[s for s in ep['scenes'] if s.get('source_type')=='leader_x' and not (is_tibo(s) and s.get('tibo_message_type')=='reset')]
    counts={}
    for s in regular:
        handle=s.get('author_handle','').lower();counts[handle]=counts.get(handle,0)+1
        if counts[handle]>2:raise ValueError('A leader may occupy at most two news pages; summarize rather than add pages')
    rest=[s for s in ep['scenes'] if s not in regular]
    index=next((i for i,s in enumerate(rest) if s.get('section','').startswith(('国内','国际'))),len(rest))
    ep['scenes']=rest[:index]+regular+rest[index:]
    ep['tibo_audit']=tibo
    return dict(policy='Prefer normal interesting leader statements; separate personal views from company announcements',reviewed_posts=audit,tibo=tibo)
