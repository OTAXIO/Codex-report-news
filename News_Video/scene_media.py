"""Resolve one related, local image for every page; no network during rendering."""
import hashlib,json,re
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

def catalog(root):
    path=Path(root)/'assets/logos/sources.json'
    if not path.exists():return {}
    return {r['id']:r for r in json.loads(path.read_text(encoding='utf-8'))['assets']}

def identity_key(scene):
    if scene.get('game') in {'arknights','endfield'}:return scene['game']
    aliases=[('openai',r'Open\s*AI|ChatGPT|Codex|thsottiaux|\btibo\b'),('anthropic',r'Anthropic|Claude'),('deepseek',r'DeepSeek'),
             ('qwen',r'Qwen|千问|通义'),('google',r'Google|Gemini|DeepMind'),('minimax',r'MiniMax'),
             ('kimi',r'Kimi|Moonshot|月之暗面'),('glm',r'GLM|智谱|ZCode|Z\.ai'),('tencent',r'Tencent|腾讯|WorkBuddy|混元|Hunyuan'),('ai2',r'\bai2\b|AllenAI')]
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
    records=catalog(root);rows=[]
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
        else:media=choose(scene,root,records)
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
