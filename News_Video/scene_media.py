"""Resolve one related, local image for every page; no network during rendering.

2026-11-10 picture choice: with `presentation.image_quality` configured, a picture that is
too small or nearly blank is not shown, and a game page may take a better picture from the
same official article. `python -B scene_media.py rank <item_id>` lists an article's pictures
best first so the writer can pick.
"""
import hashlib,json,math,re,sys
from pathlib import Path

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def image_info(root,value):
    from PIL import Image
    path=(Path(root)/value).resolve()
    if not path.is_relative_to((Path(root)/'assets').resolve()):raise ValueError('PAGE_IMAGE: image must be under assets/')
    if not path.is_file():raise ValueError('PAGE_IMAGE: missing '+str(value))
    with Image.open(path) as im:
        im.verify();size=im.size
    if min(size)<16:raise ValueError('PAGE_IMAGE: image too small')
    return path,size

def quality(path,gate=None):
    """Size and information content of a picture, measured on a 96x96 grey thumbnail."""
    from PIL import Image
    gate=gate or {}
    with Image.open(path) as im:
        w,h=im.size;rgba=im.convert('RGBA')
        flatbed=Image.new('RGBA',rgba.size,'white');flatbed.alpha_composite(rgba)   # transparent logos sit on the white page
        hist=flatbed.convert('L').resize((96,96)).histogram()
    n=96*96
    entropy=-sum(c/n*math.log2(c/n) for c in hist if c)
    flat=max(sum(hist[i:i+8]) for i in range(0,256,8))/n   # share of the page in one tone
    long_poster=h>w*2.2
    reject=None
    if min(w,h)<gate.get('min_short_side',0) or max(w,h)<gate.get('min_long_side',0):reject='too_small'
    elif flat>=gate.get('max_flat',2) or entropy<gate.get('min_entropy',0):reject='low_information'
    score=entropy*10+min(w,h,1080)/1080*20-30*max(0,flat-.5)-(30 if long_poster else 0)
    return dict(width=w,height=h,entropy=round(entropy,2),flat=round(flat,3),long_poster=long_poster,score=round(score,1),reject=reject)

def article_images(root,item_id):
    path=Path(root)/'data/articles'/(str(item_id)+'.json')
    if not item_id or not path.is_file():return []
    return [x for x in json.loads(path.read_text(encoding='utf-8')).get('related_images',[]) if x.get('file') and x.get('source_url')]

def rank(root,images,gate):
    rows=[]
    for x in images:
        try:path,_=image_info(root,x['file']);rows.append(dict(file=x['file'],source_url=x.get('source_url'),**quality(path,gate)))
        except (ValueError,OSError) as error:rows.append(dict(file=x['file'],source_url=x.get('source_url'),score=-1,reject='unreadable: '+str(error)))
    return rows

def select(scene,root,gate):
    """Keep the writer's picture unless it fails the gate or is a very long poster that would be
    cropped; then, or when the page has none, take the best picture of the same official article.
    Alternatives come only from the page's own article (or `image_candidates`), so relevance holds."""
    own=[dict(file=scene['image'],source_url=scene.get('image_source_url'))] if scene.get('image') else []
    others=list(scene.get('image_candidates',[]))
    if scene.get('game') and scene.get('segment')!='community':others+=article_images(root,scene.get('item_id'))
    others=[x for i,x in enumerate(others) if x['file']!=scene.get('image') and x['file'] not in [y['file'] for y in others[:i]]]
    rows=rank(root,own+others,gate)
    chosen=rows[0] if own and not rows[0]['reject'] else None
    pool=sorted((r for r in rows[len(own):] if not r['reject'] and r.get('source_url')),key=lambda r:-r['score'])
    if pool and (chosen is None or chosen['long_poster'] and not pool[0]['long_poster']):chosen=pool[0]
    report=dict(requested=scene.get('image'),chosen=chosen and chosen['file'],candidates=rows)
    if chosen and chosen['file']!=scene.get('image'):scene['image'],scene['image_source_url']=chosen['file'],chosen['source_url']
    elif not chosen and own:
        report['rejected']=rows[0]['reject'];scene.pop('image');scene.pop('image_source_url',None)   # falls back to the subject's identity
    return report

def catalog(root):
    path=Path(root)/'assets/logos/sources.json'
    if not path.exists():return {}
    return {r['id']:r for r in json.loads(path.read_text(encoding='utf-8'))['assets']}

def identity_key(scene):
    if scene.get('game') in {'arknights','endfield'}:return scene['game']
    aliases=[('openai',r'Open\s*AI|ChatGPT|Codex|thsottiaux|\btibo\b'),('anthropic',r'Anthropic|Claude'),('deepseek',r'DeepSeek'),
             ('qwen',r'Qwen|千问|通义'),('google',r'Google|Gemini|DeepMind'),('minimax',r'MiniMax'),
             ('kimi',r'Kimi|Moonshot|月之暗面'),('glm',r'GLM|智谱|ZCode|Z\.ai'),('tencent',r'Tencent|腾讯|WorkBuddy|混元|Hunyuan'),('ai2',r'\bai2\b|AllenAI'),('github',r'^GitHub$')]
    if scene.get('company'):
        return next((key for key,pattern in aliases if re.search(pattern,str(scene['company']),re.I)),None)
    for field in ['publisher','product','speaker_name','author_handle','title']:
        found=next((key for key,pattern in aliases if re.search(pattern,str(scene.get(field,'')),re.I)),None)
        if found:return found
    return None

def choose(scene,root,records):
    errors=[]
    for field in ['image','logo']:
        value=scene.get(field)
        if not value:continue
        try:
            path,size=image_info(root,value)
            registered=next((r for r in records.values() if (Path(root)/r['path']).resolve()==path),None)
            source=scene.get('image_source_url') if field=='image' else None
            source=source or (registered or {}).get('source')
            if not source:raise ValueError('Image provenance is missing')
            if registered and registered.get('sha256')!=digest(path):raise ValueError('Registered identity image hash changed')
            if field=='logo' and registered and identity_key(scene) and registered['id']!=identity_key(scene):raise ValueError('Identity belongs to another subject')
            return dict(field=field,path=path.relative_to(Path(root).resolve()).as_posix(),sha256=digest(path),width=size[0],height=size[1],
                        kind='news_image' if field=='image' else 'identity',source_url=source,subject=scene.get('company') or scene.get('game') or scene.get('publisher'),identity_id=(registered or {}).get('id'))
        except (ValueError,OSError) as error:errors.append(str(error))
    key=identity_key(scene);record=records.get(key)
    if not record:raise ValueError('PAGE_IMAGE: no verified related image/identity for '+scene['id']+'; '+str(errors))
    path,size=image_info(root,record['path'])
    if not record.get('source') or record.get('sha256')!=digest(path):raise ValueError('PAGE_IMAGE: invalid identity provenance/hash for '+str(key))
    return dict(field='logo',path=path.relative_to(Path(root).resolve()).as_posix(),sha256=digest(path),width=size[0],height=size[1],
                kind='game_identity' if key in {'arknights','endfield'} else 'company_identity',source_url=record['source'],subject=key,identity_id=key,fallback_reason=errors or ['No news image'])

def prepare(episode,root):
    root=Path(root);cfg=json.loads((root/'config.json').read_text(encoding='utf-8'))
    if not cfg.get('presentation',{}).get('require_image_every_page'):return None
    from layout_policy import is_overview
    records=catalog(root);rows=[];gate=cfg['presentation'].get('image_quality')
    body=[s for s in episode['scenes'] if not is_overview(s)]
    if not episode['scenes']:return dict(ok=True,policy_version=1,pages=[])
    if not body:raise ValueError('PAGE_IMAGE: no news for overview attribution')
    for scene in episode['scenes']:
        if is_overview(scene):
            # The lead's brand identifies the overview without implying that a
            # photograph depicts all stories. Prefer identity, then lead image.
            lead=body[0]
            try:media=choose({k:v for k,v in lead.items() if k not in {'image','image_source_url'}},root,records)
            except ValueError:media=choose(lead,root,records)
            media=dict(media,overview_of=lead['id'])
        else:
            picked=select(scene,root,gate) if gate else None
            media=choose(scene,root,records)
            if picked and (picked['candidates'] or picked['requested']):media['selection']=picked
        media['layout']='portrait' if media['field']=='image' and media['height']>media['width']*1.35 else 'landscape'
        scene['resolved_media']=media;rows.append(dict(scene_id=scene['id'],**media))
    episode['page_image_policy_version']=1
    return dict(ok=True,policy_version=1,pages=rows)

def validate(episode,root):
    if not episode.get('page_image_policy_version'):return None
    rows=[]
    for scene in episode['scenes']:
        media=scene.get('resolved_media')
        if not media or not media.get('source_url'):raise ValueError('PAGE_IMAGE: missing image/provenance for '+scene['id'])
        path,size=image_info(root,media['path'])
        if digest(path)!=media.get('sha256'):raise ValueError('PAGE_IMAGE: asset changed for '+scene['id'])
        from layout_policy import is_overview
        context=next((s for s in episode['scenes'] if not is_overview(s)),scene) if is_overview(scene) else scene
        if media.get('identity_id') and identity_key(context) and media['identity_id']!=identity_key(context):
            raise ValueError('PAGE_IMAGE: identity does not match this page subject')
        rows.append(dict(scene_id=scene['id'],**media))
    return dict(ok=True,policy_version=1,pages=rows)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['rank']);parser.add_argument('item_id')
    args=parser.parse_args();root=Path(__file__).resolve().parent
    gate=json.loads((root/'config.json').read_text(encoding='utf-8'))['presentation'].get('image_quality')
    rows=sorted(rank(root,article_images(root,args.item_id),gate),key=lambda r:(bool(r['reject']),-r['score']))
    sys.stdout.buffer.write((json.dumps(rows,ensure_ascii=False,indent=1)+'\n').encode('utf-8'))
