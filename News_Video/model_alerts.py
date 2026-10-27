"""Official new-model leads: deterministic discovery, semantic review, then draft."""
import argparse,datetime as dt,hashlib,json,re
from contextlib import contextmanager
import news_video as n

def folder():
    p=n.ROOT/'data/model-alerts';p.mkdir(parents=True,exist_ok=True);return p

@contextmanager
def locked():
    p=folder()/'write.lock'
    with p.open('x',encoding='utf-8') as f:f.write('model-alert-state')
    try:yield folder()
    finally:p.unlink(missing_ok=True)

def pending():
    return [n.load(p) for p in (folder()/'queue').glob('*.json') if n.load(p)['status']=='needs_review']

def scan(now=None):
    now=now or dt.datetime.now(n.UTC)
    if not n.config().get('model_alerts',{}).get('enabled',True):return dict(disabled=True,new_alerts=[])
    from leader_sources import registry
    allowed={a['handle'].lower() for a in registry() if a.get('enabled') and a.get('identity_checked') and a.get('type')=='official_x' and a.get('model_release_alerts',True)}
    posts=[n.load(p) for p in (n.ROOT/'data/leader-posts').glob('*.json')]
    posts=[p for p in posts if p.get('source_type')=='official_x' and p.get('handle','').lower() in allowed]
    with locked() as base:
        path=base/'state.json';state=n.load(path) if path.exists() else None
        hashes={p['id']:hashlib.sha256(p['summary'].encode()).hexdigest() for p in posts}
        if state is None:
            n.dump(path,dict(seen=hashes,initialized=now.isoformat()));return dict(initialized=True,new_alerts=[])
        new=[]
        for post in posts:
            if post['id'] in state['seen']:continue
            body=post['summary'];fresh=dt.timedelta(0)<=now-dt.datetime.fromisoformat(post['published'])<=dt.timedelta(hours=n.config().get('model_alerts',{}).get('max_age_hours',6))
            release=re.search(r'introducing|new model|(?:releas|launch)(?:e|ed|ing)?|available now|发布|推出|上线',body,re.I)
            model=re.search(r'GPT[- ]?\d|Claude|DeepSeek|Qwen|GLM[- ]?\d|MiniMax|Gemini|Gemma|Veo|Lyria|Kimi|Hunyuan|混元|Hy[- ]?\d|new model|新模型',body,re.I)
            if fresh and release and model:
                alert=dict(id=post['id'],kind='model_release',status='needs_review',item_id=post['id'],source=post,discovered_at=now.isoformat(),counts_toward_daily_main_limit=False)
                n.dump(base/'queue'/(post['id']+'.json'),alert);new.append(post['id'])
        state['seen'].update(hashes);state['updated_at']=now.isoformat();n.dump(path,state)
        return dict(initialized=False,new_alerts=new,pending=len(pending()),model_calls=0)

def dismiss(key,reason):
    if not reason.strip():raise ValueError('A dismissal reason is required')
    with locked() as base:
        p=base/'queue'/(key+'.json');a=n.load(p)
        if a['status']!='needs_review':raise ValueError('Lead is not awaiting review')
        a.update(status='dismissed',reason=reason);n.dump(p,a);return a

def draft(key,review_path,now=None):
    now=(now or dt.datetime.now(n.UTC)).astimezone(n.CN);review=n.load(review_path)
    if not n.config().get('model_alerts',{}).get('publication_authorized_by_user'):raise ValueError('No standing authorization for model-release publication')
    with locked() as base:
        p=base/'queue'/(key+'.json');alert=n.load(p);post=alert['source']
        if alert['status'] in {'drafted','ready_for_upload','published'}:return alert
        if alert['status']!='needs_review':raise ValueError('Model lead already handled')
        if review.get('release_status') not in {'released','rolling_out','available'}:raise ValueError('A not-yet-released preview cannot trigger a model-release bulletin')
        if review.get('is_new_model_release') is not True or review.get('context_verified') is not True:raise ValueError('Verify an actual new model release and original context')
        if now-dt.datetime.fromisoformat(post['published']).astimezone(n.CN)>dt.timedelta(hours=n.config().get('model_alerts',{}).get('max_age_hours',6)):raise ValueError('Expired model announcement')
        for field in ['model_name','title','narration','summary','quote']:
            if not isinstance(review.get(field),str) or not review[field].strip():raise ValueError('Missing review field: '+field)
        if review['quote'] not in post['summary'] or len(review['quote'])>200:raise ValueError('Quote must be an exact short excerpt')
        if review['model_name'].casefold().replace(' ','') not in post['summary'].casefold().replace(' ',''):raise ValueError('Model name is not in the original announcement')
        if post.get('requires_context') and not review.get('context_evidence'):raise ValueError('Read the referenced original context')
        if post['author'].casefold() not in review['narration'].casefold():raise ValueError('Narration must attribute the official author')
        event=post['company'].casefold()+':model-release:'+review['model_name'].casefold().replace(' ','')
        for q in (base/'queue').glob('*.json'):
            other=n.load(q)
            if other['id']!=key and other.get('event_key')==event and other['status']!='dismissed':raise ValueError('This model event is already queued or produced')
        from important_events import entries
        if any(x['event_key']==event for x in entries()):raise ValueError('This model event was already published')
        token=hashlib.sha256(event.encode()).hexdigest()[:20];eid='model-'+now.strftime('%Y%m%d-%H%M%S')+'-'+token
        scene=dict(id='model-release',section='临时新闻',title=review['title'],short_title=review['model_name'],facts=review.get('facts') or [dict(title=review['model_name'],detail=review['summary'])],narration=review['narration'],item_id=post['id'],source_url=post['url'],publisher=post['author'],published=post['published'],source_type='official_x',author_handle=post['handle'],claim_type='announcement',attribution_checked=True,context_evidence=review.get('context_evidence'),event_key=event,company=post['company'],evidence=review['quote'],selection_reason='Verified new-model announcement; user authorized hourly temporary publication')
        logo={'OpenAI':'openai.png','Anthropic':'anthropic.png','Qwen':'qwen.png'}.get(post['company'])
        if logo and (n.ROOT/'assets/logos'/logo).is_file():scene['logo']='assets/logos/'+logo
        ep=dict(id=eid,producer='Codex current conversation',edition_date=now.date().isoformat(),edition_timestamp=now.isoformat(),edition_slot='temporary',edition_type='temporary',temporary_kind='official_model_release',temporary_event_id=token,model_alert_id=key,event_key=event,publication_authorized_by_user=True,authorization_evidence='User standing rule: hourly official X new model release -> temporary video and automatic publish',counts_toward_daily_main_limit=False,title=review['title'],footer_tag='临时新闻',scenes=[scene])
        editorial=base/'drafts'/(eid+'.json');n.dump(editorial,ep);n.import_editorial(editorial)
        directory=n.ROOT/'episodes'/eid;pub=dict(n.config()['publication_preset'],title=review['title'],description=review['summary']+'\n原帖：'+post['url']+'\nAI辅助文稿、配音和画面；原创整理。',tags=review.get('tags',['AI',post['company'],'大模型','科技资讯']),auto_publish=True);n.dump(directory/'publication.json',pub);(directory/'description.txt').write_text(pub['description'],encoding='utf-8')
        if scene.get('logo'):n.dump(directory/'cover.json',dict(headline_top=post['company']+' 新模型',headline_main=review['model_name'],highlight='正式发布',image=scene['logo'],image_label=post['company'],footnote='模型发布速报'))
        alert.update(status='drafted',episode_id=eid,event_key=event,review=review);n.dump(p,alert);return alert

def mark_release(key,directory):
    with locked() as base:
        p=base/'queue'/(key+'.json');a=n.load(p);receipt=n.load(__import__('pathlib').Path(directory)/'release.json')
        if receipt.get('episode_id')!=a.get('episode_id'):raise ValueError('Model alert/release mismatch')
        a.update(status='ready_for_upload',release_directory=str(directory));n.dump(p,a)

def mark_published(key,directory):
    with locked() as base:
        p=base/'queue'/(key+'.json');a=n.load(p);directory=__import__('pathlib').Path(directory);proof=n.load(directory/'publication-verified.json');receipt=n.load(directory/'release.json')
        if proof.get('state')!='published' or not receipt.get('published') or receipt.get('episode_id')!=a.get('episode_id'):raise ValueError('Public publication evidence required')
        a.update(status='published',platform=proof['receipt']);n.dump(p,a)

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('scan');s.add_parser('pending');a=s.add_parser('dismiss');a.add_argument('id');a.add_argument('reason');a=s.add_parser('draft');a.add_argument('id');a.add_argument('review');a=p.parse_args()
    result=scan() if a.cmd=='scan' else pending() if a.cmd=='pending' else dismiss(a.id,a.reason) if a.cmd=='dismiss' else draft(a.id,a.review)
    print(json.dumps(result,ensure_ascii=False,indent=2))
