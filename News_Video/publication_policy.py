"""Bind public promises to final stories and reviewed cover pixels."""
import argparse, hashlib, json, re
from pathlib import Path
from production_policy import event_id, is_game, validate_lead_contract
from layout_policy import is_overview


def normalize(value):
    return re.sub(r'[\W_]+','',str(value),flags=re.UNICODE).casefold()


def describe(episode, publication, timings=None):
    """Description for upload: chapter list, sources, rumor disclaimer (2026-11-09).
    A producer-written description wins; the result is never empty."""
    written=str(publication.get('description') or '').strip()
    if written:
        text=written
    else:
        lines=[]
        starts={}
        for row in (timings or {}).get('sentences',[]):starts.setdefault(row['scene_id'],row['start'])
        for scene in episode['scenes']:
            if is_overview(scene):continue
            stamp=starts.get(scene['id'])
            # A 快讯 page lists its entries, so every story the video covers is findable in the chapters.
            title='快讯：'+' / '.join(e['title'] for e in scene['brief_items']) if scene.get('brief_items') else scene['title']
            label=(f'{int(stamp)//60:02}:{int(stamp)%60:02} ' if stamp is not None else '')+title
            if lines and lines[-1].endswith(title):continue
            lines.append(label)
        sources=list(dict.fromkeys(url for s in episode['scenes'] if not is_overview(s)
                                   for url in ([e.get('source_url') for e in s['brief_items']] if s.get('brief_items') else [s.get('source_url')]) if url))
        text='\n'.join(lines)
        if sources:
            # Story order; stop short of the 2000-character upload limit so the disclaimers below still fit.
            text+='\n\n来源：'
            for url in sources:
                if len(text)+len(url)+1>1880:break
                text+='\n'+url
        if any(s.get('scene_type')=='rumor' for s in episode['scenes']):text+='\n\n传闻内容未经官方证实，请以官方公告为准。'
        if any(s.get('scene_type')=='community_pulse' for s in episode['scenes']):text+='\n玩家热议为B站公开评论的归纳，代表玩家个人看法。'
    if not text.strip() or len(text)>2000:raise ValueError('DESCRIPTION_REQUIRED: description must be 1-2000 characters')
    return text


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def title_for(episode, publication):
    stories={}
    for scene in episode['scenes']:
        if not is_overview(scene):stories.setdefault(event_id(scene), scene)
    groups=publication.get('title_groups')
    if not isinstance(groups,list) or not groups:raise ValueError('TITLE_CONTENT_REQUIRED: select final events in title_groups')
    from edition_series import spec
    series=spec(episode)
    parts=[];seen=set();kinds=set()
    for group in groups:
        kind=group.get('kind');ids=group.get('event_ids')
        if kind not in {'games','ai'} or kind in kinds or not isinstance(ids,list) or not ids:
            raise ValueError('TITLE_GROUP_INVALID: one nonempty group per category')
        titles=[];kinds.add(kind)
        for key in ids:
            if key not in stories:raise ValueError('TITLE_EVENT_REMOVED: '+str(key))
            scene=stories[key]
            if ('games' if is_game(scene) else 'ai')!=kind:raise ValueError('TITLE_CATEGORY_MIXED: '+key)
            if key in seen:raise ValueError('TITLE_EVENT_DUPLICATED: '+key)
            if scene.get('brief_items'):raise ValueError('TITLE_BRIEFS_PAGE: a 快讯 page is not a title story; name a full story')
            seen.add(key);title=scene['title'].strip()
            if not title or re.search(r'[|｜\n\r]',title):raise ValueError('TITLE_STORY_SEPARATOR_INVALID')
            titles.append(title)
        # A single-audience series needs no category prefix; its name ends the title.
        parts.append('、'.join(titles) if series else ('游戏：' if kind=='games' else 'AI：')+'、'.join(titles))
    if episode['lead_event_id'] not in seen:raise ValueError('TITLE_LEAD_MISSING')
    if series:
        if kinds-set(series['kinds']):raise ValueError('TITLE_CATEGORY_OUTSIDE_SERIES')
        date=episode['edition_date']
        hook=str(publication.get('title_hook') or '').strip()
        if hook:
            # 2026-11-09: a short hook may open the title; it must restate facts of the chosen stories.
            if len(hook)>16 or re.search(r'[|｜\n\r]',hook):raise ValueError('TITLE_HOOK_INVALID: at most 16 characters, no separators')
            body=normalize(' '.join(stories[k].get('title','')+' '+stories[k].get('narration','')+' '+json.dumps(stories[k].get('facts',[]),ensure_ascii=False) for k in seen))
            anchors=publication.get('title_hook_evidence') or []
            if not anchors or any(not normalize(a) or normalize(a) not in body or normalize(a) not in normalize(hook) for a in anchors):
                raise ValueError('TITLE_HOOK_UNSUPPORTED: list title_hook_evidence phrases that appear in both the hook and the chosen stories')
            parts=[hook+' '+parts[0]]+parts[1:]
        rumor=any(stories[k].get('scene_type')=='rumor' for k in seen)
        from content_rules import check_public_words,RUMOR_MARKERS
        for k in seen:
            if stories[k].get('scene_type')=='rumor' and not any(m in stories[k]['title'] for m in RUMOR_MARKERS):
                raise ValueError('TITLE_RUMOR_MARKER: a rumor in the title must say 曝/传/疑似 in its story title: '+k)
        title='｜'.join(parts+[f"{series['label']} {int(date[5:7])}.{int(date[8:10])}"])
        check_public_words(title,rumor=rumor)
        if len(title)>60:raise ValueError('TITLE_TOO_LONG: pick one or two events in title_groups (series titles stay within 60 characters)')
        return title
    date=episode['edition_date'];slot={'morning':'早报','night':'晚报'}[episode['edition_slot']]
    return '｜'.join(parts+[f'{int(date[5:7])}月{int(date[8:10])}日{slot}'])


def snapshot(episode, publication, cover, directory):
    validate_lead_contract(episode,publication,cover)
    title=title_for(episode,publication)
    if publication.get('title')!=title or episode.get('title')!=title:
        raise ValueError('TITLE_CONTENT_MISMATCH: regenerate title from final title_groups')
    lead=next(s for s in episode['scenes'] if not is_overview(s))
    # Cover claims must quote the actual lead's public text, never another story.
    normalize=lambda s:re.sub(r'[\W_]+','',s,flags=re.UNICODE).casefold()
    source=normalize(lead.get('title','')+' '+lead.get('narration','')+' '+json.dumps(lead.get('facts',[]),ensure_ascii=False))
    for key in ['headline_top','headline_main','highlight']:
        text=normalize(cover.get(key,''))
        if text and text not in source:raise ValueError('COVER_CLAIM_NOT_IN_LEAD: '+key)
    if not normalize(cover.get('headline_main','')):raise ValueError('COVER_HEADLINE_REQUIRED')
    images={}
    for name in ['cover-16x9.png','cover-4x3.png','cover-bilibili.jpg']:
        path=Path(directory)/name
        if not path.is_file():raise ValueError('COVER_PIXELS_REQUIRED: '+name)
        images[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    if lead.get('scene_type')=='rumor':
        from content_rules import RUMOR_MARKERS
        if not any(m in cover.get('headline_main','')+cover.get('headline_top','') for m in RUMOR_MARKERS):
            raise ValueError('COVER_RUMOR_MARKER: a rumor cover headline says 曝/传/疑似')
    promises={key:publication.get(key) for key in ['title','title_groups','lead_event_id']}
    if publication.get('title_hook'):promises['title_hook']=publication['title_hook']
    return dict(version=1,content=digest(episode),publication=digest(promises),cover=digest(cover),images=images)


def validate(directory):
    directory=Path(directory)
    load=lambda name:json.loads((directory/name).read_text(encoding='utf-8-sig'))
    episode=load('episode.json')
    if episode.get('edition_slot') not in {'morning','night'}:return
    publication=load('publication.json');cover=load('cover.json')
    actual=snapshot(episode,publication,cover,directory)
    record=directory/'publication-content-review.json'
    if not record.is_file() or load(record.name)!=actual:
        raise ValueError('PUBLICATION_REVIEW_STALE: final content, title or cover changed; review and seal again')


def seal(directory):
    directory=Path(directory)
    if (directory/'release.json').exists():raise ValueError('Seal only an unexported episode; never rewrite a released edition')
    load=lambda name:json.loads((directory/name).read_text(encoding='utf-8-sig'))
    episode=load('episode.json');publication=load('publication.json');cover=load('cover.json')
    record=snapshot(episode,publication,cover,directory)
    (directory/'publication-content-review.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['title','seal','check']);parser.add_argument('directory');parser.add_argument('--write',action='store_true');args=parser.parse_args()
    directory=Path(args.directory)
    if args.action=='title':
        episode=json.loads((directory/'episode.json').read_text(encoding='utf-8-sig'))
        publication=json.loads((directory/'publication.json').read_text(encoding='utf-8-sig'))
        title=title_for(episode,publication)
        if args.write:
            if (directory/'release.json').exists():raise ValueError('Do not rewrite released metadata')
            episode['title']=publication['title']=title
            for name,value in [('episode.json',episode),('publication.json',publication)]:
                (directory/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        print(title)
    elif args.action=='seal':seal(directory)
    else:validate(directory)
