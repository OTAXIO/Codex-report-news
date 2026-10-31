"""Bind public promises to final stories and reviewed cover pixels."""
import argparse, hashlib, json, re
from pathlib import Path
from production_policy import event_id, is_game, validate_lead_contract
from layout_policy import is_overview


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def title_for(episode, publication):
    stories={}
    for scene in episode['scenes']:
        if not is_overview(scene):stories.setdefault(event_id(scene), scene)
    groups=publication.get('title_groups')
    if not isinstance(groups,list) or not groups:raise ValueError('TITLE_CONTENT_REQUIRED: select final events in title_groups')
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
            seen.add(key);title=scene['title'].strip()
            if not title or re.search(r'[|｜\n\r]',title):raise ValueError('TITLE_STORY_SEPARATOR_INVALID')
            titles.append(title)
        parts.append(('游戏：' if kind=='games' else 'AI：')+'、'.join(titles))
    if episode['lead_event_id'] not in seen:raise ValueError('TITLE_LEAD_MISSING')
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
    promises={key:publication.get(key) for key in ['title','title_groups','lead_event_id']}
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
