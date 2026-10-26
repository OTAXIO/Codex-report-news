"""Tibo reset watch: deterministic detection, reviewed single-tweet emergency draft."""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,re
from contextlib import contextmanager
from pathlib import Path
import news_video as n

RESET=re.compile(r'\breset(?:s|ting)?\b|重置|刷新额度',re.I)
NON_ANNOUNCEMENT=re.compile(r'\b(?:wish|hope|hopefully|please|joke|joking)\b|\bno\s+(?:more\s+)?reset|not\s+enough\s+resets|希望|求重置|玩笑|不会重置',re.I)

def folder():return n.ROOT/'data/reset-alerts'

@contextmanager
def locked():
    base=folder();base.mkdir(parents=True,exist_ok=True);lock=base/'write.lock'
    with lock.open('x',encoding='utf-8'):pass
    try:yield base
    finally:lock.unlink(missing_ok=True)

def posts():
    return [n.load(p) for p in (n.ROOT/'data/leader-posts').glob('*.json')]

def fingerprint(post):return hashlib.sha256(post['summary'].encode()).hexdigest()

def scan(now=None):
    now=now or dt.datetime.now(n.UTC);policy=n.config().get('reset_alerts',{})
    if not policy.get('enabled'):raise ValueError('Reset watch disabled')
    with locked() as base:
        state_path=base/'state.json';items=posts()
        if not state_path.exists():
            state=dict(enabled_since=now.isoformat(),start_cutoff=(now-dt.timedelta(minutes=60)).isoformat(),seen={p['id']:fingerprint(p) for p in items})
            n.dump(state_path,state)
            return dict(initialized=True,baseline_posts=len(items),new_alerts=[],model_calls=0)
        state=n.load(state_path);new=[]
        for post in items:
            key=post['id'];sha=fingerprint(post)
            if state['seen'].get(key)==sha:continue
            state['seen'][key]=sha
            if post.get('handle','').lower()!='thsottiaux' or post.get('source_type')!='leader_x':continue
            stamp=dt.datetime.fromisoformat(post['published'])
            # Never turn historical/backfilled resets into new urgent notices.
            if not max(dt.datetime.fromisoformat(state.get('start_cutoff',state['enabled_since'])),now-dt.timedelta(hours=policy.get('max_age_hours',6)))<=stamp<=now:continue
            if not RESET.search(post['summary']):continue
            queue=base/'queue'/(key+'.json')
            if queue.exists():continue
            reason='possible_reset_statement'
            if NON_ANNOUNCEMENT.search(post['summary']):reason='ambiguous_or_non_announcement'
            alert=dict(id=key,item_id=key,status='needs_review',reason=reason,created_at=now.isoformat(),
                source_url=post['url'],published=post['published'],author=post['author'],text=post['summary'],
                edition_type='temporary',counts_toward_daily_main_limit=False,
                review_requirements=['Verify original context and affirmative reset announcement','No inferred account entitlement, scope or effective time'])
            n.dump(queue,alert);new.append(key)
        for path in (base/'queue').glob('*.json'):
            alert=n.load(path)
            if alert['status']=='needs_review' and dt.datetime.fromisoformat(alert['published'])<now-dt.timedelta(hours=policy.get('max_age_hours',6)):
                alert.update(status='expired',expiry_reason='No longer timely for emergency publication');n.dump(path,alert)
        state['last_scan']=now.isoformat();n.dump(state_path,state)
        return dict(initialized=False,new_alerts=new,pending=[a['id'] for a in pending()],model_calls=0)

def pending():
    return [n.load(p) for p in sorted((folder()/'queue').glob('*.json'))
            if n.load(p).get('status') in {'needs_review','drafted','ready_for_upload'}]

def get_alert(alert_id):
    if not re.fullmatch('[a-f0-9]{20}',alert_id):raise ValueError('Invalid alert ID')
    path=folder()/'queue'/(alert_id+'.json');return path,n.load(path)

def dismiss(alert_id,reason):
    if not reason.strip():raise ValueError('Record why this is not an actionable reset')
    with locked():
        path,alert=get_alert(alert_id)
        if alert['status']!='needs_review':raise ValueError('Cannot dismiss an already produced alert')
        alert.update(status='dismissed',dismissal_reason=reason);n.dump(path,alert)
    return alert

def validate_temporary(ep):
    scenes=ep.get('scenes',[])
    if ep.get('edition_type')!='temporary' or ep.get('counts_toward_daily_main_limit') is not False:
        raise ValueError('Temporary news must be separate from the three daily main editions')
    if len(scenes)!=1 or scenes[0].get('author_handle')!='thsottiaux' or scenes[0].get('source_type')!='leader_x':
        raise ValueError('Reset temporary news shows one Tibo post only; no intro or other news')
    if scenes[0].get('section')!='临时新闻' or ep.get('footer_tag')!='临时新闻':raise ValueError('Use the 临时新闻 label')

def draft(alert_id,review_path,now=None):
    """A model/editor checks facts; a keyword match alone never publishes."""
    now=(now or dt.datetime.now(n.UTC)).astimezone(n.CN);review=n.load(review_path)
    with locked() as base:
        path,alert=get_alert(alert_id)
        if alert['status'] in {'drafted','ready_for_upload','published'}:return alert
        if alert['status']!='needs_review':raise ValueError('Alert is not awaiting review')
        if review.get('is_reset_announcement') is not True or review.get('context_verified') is not True:
            raise ValueError('Verify an affirmative reset announcement and its context first')
        if review.get('announcement_status') not in {'planned','ongoing','completed'}:raise ValueError('Missing accurate reset status')
        for field in ['summary','narration','title','reset_event_key']:
            if not isinstance(review.get(field),str) or not review[field].strip():raise ValueError('Missing review field: '+field)
        if now-dt.datetime.fromisoformat(alert['published']).astimezone(n.CN)>dt.timedelta(hours=n.config()['reset_alerts'].get('max_age_hours',6)):
            raise ValueError('Reset alert has expired; do not publish old emergency notices')
        if len(review['summary'])>90 or len(review['title'])>24:raise ValueError('Keep temporary news concise')
        quote=review.get('quote','')
        if not quote or quote not in alert['text'] or len(quote)>160:raise ValueError('Use an exact, short excerpt from the post')
        for other_path in (base/'queue').glob('*.json'):
            other=n.load(other_path)
            if other['id']!=alert_id and other.get('reset_event_key')==review['reset_event_key'] and other.get('status') not in {'dismissed'}:
                raise ValueError('This reset event already has a temporary edition')
        ep_id='reset-'+now.strftime('%Y%m%d-%H%M%S')+'-'+alert_id
        scene=dict(id='reset-message',section='临时新闻',title=review['title'],short_title='reset 消息',
            facts=[dict(title='tibo 推文原文',detail=quote),dict(title='消息概括',detail=review['summary'])],
            narration=review['narration'],item_id=alert['item_id'],source_url=alert['source_url'],publisher='tibo',
            published=alert['published'],source_type='leader_x',author_handle='thsottiaux',
            claim_type='preview' if review['announcement_status']=='planned' else 'announcement',attribution_checked=True,
            context_evidence=review.get('context_evidence',''),selection_reason='User-authorized Tibo reset temporary news',
            evidence=quote,event_key=review['reset_event_key'],show_source=True)
        ep=dict(id=ep_id,producer=review.get('producer','Codex current conversation'),edition_date=now.date().isoformat(),
            edition_slot='temporary',edition_type='temporary',edition_timestamp=now.isoformat(),alert_id=alert_id,
            counts_toward_daily_main_limit=False,title=review['title']+'｜'+now.strftime('%m.%d')+' 临时新闻',
            footer_tag='临时新闻',scenes=[scene])
        validate_temporary(ep)
        incoming=n.ROOT/'data'/f'{ep_id}-editorial.json';n.dump(incoming,ep);n.import_editorial(incoming)
        out=n.ROOT/'episodes'/ep_id
        n.dump(out/'cover.json',dict(headline_top='tibo 发文',headline_main='重置消息',highlight='reset',
            subtitle=review.get('cover_subtitle','原始推文信息'),image='assets/logos/openai.png',image_label='tibo 推文',footnote='原文及中文概括'))
        description=review['summary']+'\n\n原始推文：\n'+alert['source_url']+'\n发布时间：'+alert['published']+'\n\n内容由 AI 辅助整理和配音，字幕已内嵌。'
        pub=dict(title=ep['title'],description=description,tags=['AI','OpenAI','临时新闻'],original=True,ai_generated=True,
            category_requested='News',zone_requested='科技数码',auto_publish=bool(n.config().get('auto_publish')))
        n.dump(out/'publication.json',pub);(out/'description.txt').write_text(description,encoding='utf-8')
        alert.update(status='drafted',episode_id=ep_id,reset_event_key=review['reset_event_key'],review=review)
        n.dump(path,alert);n.dump(out/'reset-alert.json',alert)
    return alert

def mark_release(alert_id,directory,published=False):
    directory=Path(directory).resolve()
    from project_paths import release_root
    if not directory.is_relative_to(release_root(n.ROOT)):raise ValueError('Use release only')
    receipt=n.load(directory/'release.json');ep=n.load(directory/'episode.json')
    if ep.get('alert_id')!=alert_id or (published and not receipt.get('published')):raise ValueError('Release/alert state mismatch')
    with locked():
        path,alert=get_alert(alert_id)
        if alert.get('episode_id')!=ep['id']:raise ValueError('Alert episode mismatch')
        alert.update(status='published' if published else 'ready_for_upload',release_directory=str(directory))
        n.dump(path,alert)

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('scan');sub.add_parser('pending')
    a=sub.add_parser('draft');a.add_argument('id');a.add_argument('--review',required=True)
    a=sub.add_parser('dismiss');a.add_argument('id');a.add_argument('--reason',required=True)
    a=p.parse_args()
    result=scan() if a.cmd=='scan' else pending() if a.cmd=='pending' else draft(a.id,a.review) if a.cmd=='draft' else dismiss(a.id,a.reason)
    print(json.dumps(result,ensure_ascii=False,indent=2))
