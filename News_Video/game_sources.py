"""Read-only official game announcements; no fabricated RSS or publishing."""
import datetime as dt,gzip,hashlib,html,json,re
from pathlib import Path
from urllib.parse import urljoin,urlparse

def decode(body,encoding='utf-8'):
    return (gzip.decompress(body) if body[:2]==b'\x1f\x8b' else body).decode(encoding,errors='replace')

def objects(page):
    # Next.js server data is JSON, not executable JavaScript. Never eval it.
    decoder=json.JSONDecoder();texts=[page]
    for raw in re.findall(r'self\.__next_f\.push\((\[.*?\])\)</script>',page):
        try:
            value=json.loads(raw)
            if len(value)>1 and isinstance(value[1],str):texts.append(value[1])
        except ValueError:continue
    def walk(v):
        if isinstance(v,dict):
            yield v
            for x in v.values():yield from walk(x)
        elif isinstance(v,list):
            for x in v:yield from walk(x)
    for text in texts:
        for m in re.finditer(r'\{',text):
            try:v,_=decoder.raw_decode(text[m.start():])
            except ValueError:continue
            yield from walk(v)

def topic(title):
    return 'update' if re.search(r'更新|维护|修复|update|maintenance|patch',title,re.I) else 'event' if re.search(r'活动|庆典|寻访|联动|直播|event|celebration|headhunt|livestream',title,re.I) else 'other'

def parse(page,source):
    from news_video import text,parse_date
    seen=set();out=[]
    for row in objects(page):
        key=row.get('cid',row.get('id'));title=row.get('title');stamp=row.get('displayTime',row.get('publishTime'))
        if not key or not title or stamp is None or str(key) in seen:continue
        seen.add(str(key))
        published=dt.datetime.fromtimestamp(stamp/1000 if stamp>100000000000 else stamp,dt.timezone.utc).isoformat() if isinstance(stamp,(int,float)) else parse_date(stamp)
        url=source['article_base'].rstrip('/')+'/'+str(key)
        images=[urljoin(url,str(row[k])) for k in ['cover','image','thumb','thumbnail'] if isinstance(row.get(k),str) and row[k]]
        images+=re.findall(r'<img[^>]+src=[\"\x27]([^\"\x27]+)',str(row.get('content','')),re.I)
        out.append(dict(title=text(title),url=url,published=published,raw_published=stamp,source_timezone='UTC' if isinstance(stamp,(int,float)) else source.get('timezone'),summary=text(row.get('brief') or row.get('content') or row.get('description') or title),images=images,game=source['game'],game_region=source['game_region'],game_topic=topic(title),source_type='official_game_page',body_complete=bool(row.get('content'))))
    if not out:raise ValueError('Official game page returned no dated announcements; inspect source drift, do not invent news')
    return out

def archive(root,item_id,item,source):
    folder=Path(root)/'data/game-items';folder.mkdir(parents=True,exist_ok=True)
    value=dict(game=source.get('game'),game_region=source.get('game_region'),game_topic=topic(item['title']),activity_start=None,activity_end=None)
    value.update(item);value['source_id']=source['id']
    (folder/(item_id+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def article(root,item_id,data,page):
    """Download related official images on article inspection, not hourly."""
    from news_video import fetch
    matches=[v for v in objects(page) if v.get('title')==data['title'] and any(v.get(k) for k in ['content','body'])]
    bodies=[str(v.get('content') or v.get('body')) for v in matches]
    images=list(dict.fromkeys(data.get('images',[])+[html.unescape(urljoin(data['url'],u)) for u in re.findall(r'<img[^>]+src=[\"\x27]([^\"\x27]+)',page+'\n'+'\n'.join(bodies),re.I)]))
    local=[];folder=Path(root)/'assets/game-news';folder.mkdir(parents=True,exist_ok=True)
    for url in images[:4]:
        host=urlparse(url).hostname or ''
        if urlparse(url).scheme!='https' or not any(host==h or host.endswith('.'+h) for h in ['hypergryph.com','hycdn.cn','hg-cdn.com','gryphline.com','yo-star.com','yostar.com']):continue
        try:
            b,final,_=fetch(url)
            from PIL import Image
            import io
            image=Image.open(io.BytesIO(b));image.verify()
            name=hashlib.sha256(url.encode()).hexdigest()[:20]+'.png';dest=folder/name
            Image.open(io.BytesIO(b)).convert('RGB').save(dest)
            local.append(dict(file=dest.relative_to(root).as_posix(),source_url=url,final_url=final,article_url=data['url']))
        except Exception as e:local.append(dict(source_url=url,error=type(e).__name__))
    data.update(official_body=bodies or data.get('official_body') or ([data.get('summary','')] if data.get('body_complete') else []),related_images=local)
    return data

def coverage(rows):
    targets={'arknights_cn':1,'arknights_global':1,'endfield_update':1,'endfield_event':1};buckets={k:[] for k in targets};seen=set()
    for row in sorted(rows,key=lambda x:({'update':0,'event':1}.get(x.get('game_topic'),2),0 if x.get('source_type')!='official_x' else 1)):
        key=row.get('event_key') or row.get('url')
        if key in seen or row.get('kind')!='games':continue
        seen.add(key)
        slot='arknights_'+('cn' if row.get('game_region')=='cn' else 'global') if row.get('game')=='arknights' else 'endfield_'+row.get('game_topic','other')
        if slot in buckets:buckets[slot].append(row['id'])
    return dict(targets=targets,candidate_ids=buckets,advisory_only=True,maximum_items=None,enforce_minimum=False,
                selection_policy='Review all independent fresh events, not one per bucket; prefer updates then meaningful activities. No filler.',
                counts={k:len(v) for k,v in buckets.items()},shortfall={k:max(0,1-len(v)) for k,v in buckets.items()})
