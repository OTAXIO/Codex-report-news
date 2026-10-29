"""Build local, deterministic news shots with the existing episode data."""
import html,json,re,shutil
from pathlib import Path
from caption_layout import sentence_captions
from layout_policy import is_overview,folio_numbers
from progress_overlay import group,navigation_layout
from audio_mix import ensure_soundtrack
from renderer_backends import save,load

def text(value):return html.escape(str(value),quote=True)
def phrase(value):
    # Keep English/model tokens intact; Chinese still wraps naturally.
    return ''.join('<span class="keep">'+text(p)+'</span>' if re.match(r'[A-Za-z0-9]',p) else text(p)
                   for p in re.split(r'([A-Za-z][A-Za-z0-9.+_-]*(?: [A-Za-z0-9][A-Za-z0-9.+_-]*)*)',str(value)) if p)

def build(root,episode,plan):
    from build_film import source_publication_label
    root=Path(root);episode=Path(episode);ep=load(episode/'episode.json');timing=load(episode/'timings.json')
    from scene_media import validate
    media_audit=validate(ep,root)
    if media_audit:save(episode/'scene-media.json',media_audit)
    out=root/plan['artifact_directory'];out.mkdir(parents=True,exist_ok=True)
    assets=out/'assets';assets.mkdir(exist_ok=True)
    fonts=assets/'fonts';fonts.mkdir(exist_ok=True)
    for name in ['msyh.ttc','msyhbd.ttc']:
        shutil.copy2(Path('C:/Windows/Fonts')/name,fonts/name)
    for name in ['news-shot.css','news-shot.js']:
        shutil.copy2(Path(__file__).parent/name,out/name)
    soundtrack=ensure_soundtrack(root,episode,timing['duration'])
    # Audio is attached by the renderer CLI, never advanced by browser playback.
    offsets=[];scenes=[];cards=[];chapters=[];folios=folio_numbers(ep['scenes'])
    for index,s in enumerate(ep['scenes']):
        parts=[p for p in timing['sentences'] if p['scene_id']==s['id']]
        if not parts:raise ValueError('No timing for scene '+s['id'])
        start=parts[0]['start'];last=parts[-1]['end']
        end=next((p['start'] for p in timing['sentences'] if p['start']>=last and p['scene_id']!=s['id']),timing['duration'])
        offsets.append(dict(id=s['id'],start=start,end=end))
        mode='overview' if is_overview(s) else 'game' if s.get('game') else 'leader' if s.get('source_type')=='leader_x' or s.get('speaker_identity') else 'brief' if s.get('scene_type')=='temporary_news' or ep.get('edition_slot')=='temporary' else 'product' if s.get('logo') else 'social'
        scene=dict(id=s['id'],start=start,end=end,mode=mode,section=group(s),title=s['title'])
        scenes.append(scene)
        logo='';picture='';diagram=''
        selected=[(s['resolved_media']['field'],s['resolved_media']['path'])] if s.get('resolved_media') else [(field,s.get(field)) for field in ['logo','image']]
        for field,value in selected:
            if not value or not isinstance(value,str):continue
            source=(root/value).resolve()
            if not source.is_file():raise ValueError('Missing local verified '+field+': '+value)
            name=f'{index}-'+source.name;shutil.copy2(source,assets/name)
            label=s.get('company') or {'arknights':'明日方舟','endfield':'明日方舟：终末地'}.get(s.get('game'),s.get('resolved_media',{}).get('subject',''))
            if s.get('resolved_media',{}).get('kind')=='game_identity':label+=' · 游戏图标'
            if field=='logo':logo=f'<aside class="brand"><div class="brand-window"><img src="assets/{text(name)}" alt="{text(label)}"></div><b>{text(label)}</b></aside>'
            else:picture=f'<aside class="photo"><img src="assets/{text(name)}" alt="{text(s.get("image_alt",s["title"]))}"></aside>'
        graphic=s.get('diagram',{})
        if graphic:
            if not graphic.get('source_url'):raise ValueError('A factual diagram requires its source URL')
            if graphic.get('type')=='route':
                diagram='<aside class="route"><small>航线示意</small>'+''.join('<div class="route-stop"><i></i><b>'+text(stop)+'</b></div>' for stop in graphic['stops'])+'</aside>'
            elif graphic.get('type')=='metrics':
                diagram='<aside class="metrics">'+''.join(f'<div><strong>{text(m["value"])}</strong><b>{text(m["unit"])}</b><p>{text(m["label"])}</p></div>' for m in graphic['items'])+'</aside>'
        facts=[]
        for f in s.get('facts',[]):
            f=f if isinstance(f,dict) else dict(title=f,detail='')
            facts.append(f)
        if s.get('original_text_page'):mode='original';scene['mode']=mode
        if mode=='overview':
            if len(facts)>4:raise ValueError('Upgrade the overview to at most four complete highlights before rendering')
            body='<p class="lead">'+text(s.get('lead','本期我们一起了解这些重点动态。'))+'</p><div class="overview-grid">'+''.join(
                f'<article><div class="category">{text(f.get("category","重点新闻"))}</div><h2>{phrase(f["title"])}</h2><p>{phrase(f.get("detail",""))}</p></article>' for f in facts)+'</div>'+logo+picture
        else:
            identity=(f'<div class="identity"><b>{text(s.get("speaker_name",s.get("publisher","")))}</b><span>{text(s.get("speaker_identity",""))}</span><i>{text({"opinion":"个人观点","preview":"预告 / 计划","experience":"使用体会","reshare":"转发信息"}.get(s.get("claim_type"),"推文动态"))}</i></div>' if mode in {'leader','original'} else '')
            body=identity+'<div class="facts">'+''.join(f'<article><span class="point-number">{i+1:02}</span><div><h2>{phrase(f["title"])}</h2><p>{phrase(f.get("detail",""))}</p></div></article>' for i,f in enumerate(facts))+'</div>'+logo+picture+diagram
        source=(f'<div class="source"><b>{text(s.get("publisher",""))}</b>　{source_publication_label(s)}<span>{text(re.sub(r"^https?://","",s.get("source_url","")))}</span></div>' if s.get('show_source',True) and mode!='overview' else '')
        classes=f'scene {mode}'+(' has-media' if logo or picture or diagram else '')+(' has-diagram' if diagram else '')+(' portrait-media' if s.get('resolved_media',{}).get('layout')=='portrait' else '')
        cards.append(f'<section class="{classes}" id="scene-{text(s["id"])}"><div class="scene-folio">{folios[index]:02}</div><div class="kicker"><span>{text(scene["section"])}</span><i></i></div><h1>{phrase(s["title"])}</h1>{body}{source}</section>')
        chapters.append(dict(id=s['id'],label=s.get('short_title',s['title']),start=start,end=end))
    captions=load(episode/'captions.json') if (episode/'captions.json').exists() else [dict(id=f'caption-{i}-{j}',**cue) for i,p in enumerate(timing['sentences']) for j,cue in enumerate(sentence_captions(p))]
    for c in captions:
        if '\n' in c['text']:raise ValueError('Only single-line captions are supported')
    from production_policy import modules as module_ranges
    modules=[dict(id=key,label=label,start=start,end=end) for key,label,start,end in module_ranges(ep,offsets,timing['duration'])]
    spec=dict(duration=timing['duration'],chapters=chapters,modules=modules,blue='#01A1FE',full_bleed_edges=True,right_block_width=64,
              **navigation_layout('multiplane'),
              chapter_bounds=[dict(x=96+1728*c['start']/timing['duration'],width=1728*(c['end']-c['start'])/timing['duration']) for c in chapters])
    model=dict(duration=timing['duration'],scenes=scenes,captions=captions,progress=spec,template=plan['template'],require_page_image=bool(ep.get('page_image_policy_version')))
    data=json.dumps(model,ensure_ascii=False).replace('</','<\\/')
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>新闻视频</title><link rel="stylesheet" href="/multiplane/runtime/shot.css"><link rel="stylesheet" href="news-shot.css"></head><body><div id="stage" class="{plan['template']}"><div class="edge-band"></div><div class="edge-ticks"></div><div class="publication-label">{text(ep.get('edition_date','').replace('-','.'))}　{text(ep.get('footer_tag','新闻速报'))}</div>{''.join(cards)}<div id="caption" class="caption"></div><div class="navigation" style="--navigation-offset:{spec['nav_offset_y']}px"><div id="modules"></div><div class="now-label" id="now-label"></div><div id="clock"></div><div id="chapters"></div><div id="track"></div><div id="fill"></div><div id="markers"></div></div></div><script id="story-data" type="application/json">{data}</script><script src="/multiplane/runtime/shot.js"></script><script src="news-shot.js"></script></body></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')
    save(episode/'scene-timings.json',offsets);save(episode/'captions.json',captions);save(episode/'progress.json',spec)
    save(out/'storyboard.json',model)
    save(episode/'render-assets.json',dict(shot=str(out/'index.html'),soundtrack=str(soundtrack),backend=plan['backend'],template=plan['template']))
    print(out);return out
