"""快讯 pages (2026-11-11): one page carries 2-3 short, verified items.

Why: a competitor fits 18 stories into 8.5 minutes; we fit 7 into 4, because every story took a full
page. Secondary stories now share a 快讯 page: each line is a collected, fresh, unused candidate with
its own source; the on-screen lines are built here from the entries, never typed as free facts.

Scene contract (AI edition; after official news, before GitHub; never the lead):
    {"scene_type":"briefs","item_id":<first entry's item_id>,"source_url":<its url>,
     "brief_items":[{"item_id","source_url","title"(<=22字),"detail"(<=40字),"spoken_key"}...2-3],
     "narration": one or two sentences per entry, in order, each naming its spoken_key}
Rumors and posts that need reply/quote context keep their own full page.
"""
from __future__ import annotations
import re

MIN_ITEMS,MAX_ITEMS,TITLE_MAX,DETAIL_MAX=2,3,22,40

def _catalog(root,catalog):
    from leader_sources import registry
    merged=dict(catalog)
    try:merged.update({s['id']:s for s in registry()})
    except (OSError,KeyError,ValueError):pass
    return merged

def validate(scene,db,catalog,root,reference=None):
    """Checks every entry and fills scene facts; returns [(item_id,row)] for selection and used-news."""
    from freshness import evidence_for,check
    import datetime as dt
    entries=scene.get('brief_items') or []
    if not MIN_ITEMS<=len(entries)<=MAX_ITEMS:raise ValueError(f'BRIEFS_ITEMS: a 快讯 page carries {MIN_ITEMS}-{MAX_ITEMS} entries')
    ids=[e.get('item_id') for e in entries]
    if len(set(ids))!=len(ids):raise ValueError('BRIEFS_DUPLICATE: the same story twice on one 快讯 page')
    if scene.get('item_id')!=ids[0] or scene.get('source_url')!=entries[0].get('source_url'):
        raise ValueError('BRIEFS_LEAD_ENTRY: item_id/source_url of the page must be its first entry')
    catalog=_catalog(root,catalog);reference=reference or dt.datetime.now(dt.timezone.utc)
    narration=scene.get('narration','');spoken=narration.casefold();facts=[];out=[];last=-1
    for e in entries:
        row=db.execute('SELECT * FROM items WHERE id=?',(e.get('item_id'),)).fetchone()
        if not row:raise ValueError('BRIEFS_UNKNOWN: '+str(e.get('item_id'))+' was not collected')
        row=dict(row);source=catalog.get(row['source_id'],{})
        if str(row['source_id']).startswith('rumor-x-') or source.get('rumor'):raise ValueError('BRIEFS_SOURCE: a rumor needs its own rumor page')
        if source.get('lead_only'):raise ValueError('BRIEFS_SOURCE: '+row['source_id']+' is a discovery lead; cite the official original')
        if row['source_id']=='github-trending' or str(row['source_id']).startswith('community-'):raise ValueError('BRIEFS_SOURCE: GitHub and community items keep their own pages')
        if e.get('source_url')!=row['url']:raise ValueError('BRIEFS_URL: '+e['item_id']+' source_url differs from the collected candidate')
        title=str(e.get('title','')).strip();detail=str(e.get('detail','')).strip();key=str(e.get('spoken_key','')).strip()
        if not title or len(title)>TITLE_MAX or not detail or len(detail)>DETAIL_MAX:
            raise ValueError(f'BRIEFS_TEXT: {e["item_id"]} title 1-{TITLE_MAX} chars, detail 1-{DETAIL_MAX} chars')
        if len(key)<2 or key.casefold() not in title.casefold():raise ValueError('BRIEFS_KEY: spoken_key must be a name shown in the entry title')
        at=spoken.find(key.casefold(),last+1)
        if at<0:raise ValueError('BRIEFS_NARRATION: say "'+key+'" in the narration, entries in screen order')
        last=at
        result=check(evidence_for(root,dict(item_id=row['id'])),reference,48)
        if not result['ok']:raise ValueError('BRIEFS_FRESHNESS: '+row['id']+': '+result['reason'])
        publisher=source.get('publisher') or row.get('publisher') or ''
        if source.get('tier')=='media' and not re.search('据\\s*'+re.escape(publisher),narration,re.I):
            raise ValueError('BRIEFS_MEDIA: say 据'+publisher+'报道 for the media entry')
        if source.get('type') in {'leader_x','official_x'}:
            from news_video import ROOT,load
            post=load(ROOT/'data/leader-posts'/(row['id']+'.json'))
            if post.get('requires_context'):raise ValueError('BRIEFS_CONTEXT: a reply/quote/repost needs its own page with context evidence')
            names=[source.get('name',''),source.get('handle','')]
            if source.get('type')=='leader_x' and not any(n and n.casefold() in spoken for n in names):
                raise ValueError('BRIEFS_ATTRIBUTION: name '+source.get('name','the author')+' in the narration')
            publisher=source.get('name',publisher)
        facts.append(dict(title=title,detail=detail+'（'+publisher+'）'))
        out.append((row['id'],row))
    scene['facts']=facts;scene['badge']='快讯';scene['segment']='briefs'
    # The page cites several sources; the source strip lists them all instead of the first entry's URL.
    scene['brief_publishers']=list(dict.fromkeys(f['detail'].rsplit('（',1)[1].rstrip('）') for f in facts))
    scene['briefs_audit']=[dict(item_id=i,source_id=r['source_id'],url=r['url']) for i,r in out]
    return out
