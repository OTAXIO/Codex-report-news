"""Build local, deterministic news shots with the existing episode data."""
import datetime as dt,html,json,re,shutil
from pathlib import Path
from caption_layout import sentence_captions
from layout_policy import is_overview,folio_numbers
from progress_overlay import group,navigation_layout
from audio_mix import ensure_soundtrack
from renderer_backends import save,load

EXTRA_FONTS={'persona':['impact.ttf'],'cornerstone':['impact.ttf','NotoSerifSC-VF.ttf','bahnschrift.ttf']}
# The progress/chapter highlight colour; verify_progress_video derives its pixel mask from it.
TEMPLATE_BLUE={'cornerstone':'#2335E8'}
SERIES_NAMES={'arknights':'明日方舟','endfield':'明日方舟：终末地'}
SIDE_CODES={'ai':'AI DAILY','endfield':'ENDFIELD INTEL','arknights':'ARKNIGHTS INTEL'}
OFFICIAL_SOURCES={'skland_capture','official_game_page','official_rss','official_site','official_x'}
# 2026-11-09 segment badges: rumors are visibly unconfirmed, player views visibly opinions.
BADGE_COLORS={'rumor':'#F06A00','community':'#12925A','media':'#5B6470','github':'#24292F','activities':'#0A6FB5','global_games':'#5B6470'}
ACTIVITY_COLORS={'online':'#0A6FB5','offline':'#0A8F6A','collab':'#B8327C'}
FIT_MODES={'game','product','social','brief'}

def photo_frame(media,mode,extra):
    """The frame takes the picture's own shape inside the page's picture box, so no
    letterbox bars or cropped posters; the text column gets whatever width is left."""
    w,h=media['width'],media['height'];pad=20
    if media.get('layout')=='portrait':
        if h>w*2.2:return ' crop-media',''   # very long poster: keep the existing top crop
        bw,bh,edge,gap=560,700+extra,1640,84
    else:bw,bh,edge,gap=(880 if mode=='game' else 740),460+extra,(1756 if mode=='brief' else 1820),54   # a brief may open the film: its 64px entry slide must stay inside the reading area
    scale=min((bw-pad)/w,(bh-pad)/h,1.6)
    fw,fh=round(w*scale)+pad,round(h*scale)+pad
    return ' hug-media',f'--media-w:{fw}px;--media-h:{fh}px;--text-w:{edge-fw-96-gap}px'

def countdown(activity):
    c=activity['countdown'];upcoming=activity['phase']=='upcoming'
    place=' · '.join(x for x in [activity.get('location') and '地点 '+activity['location'],activity.get('partner') and '联动 '+activity['partner']] if x)
    return (f'<div class="countdown{" urgent" if activity["urgent"] else ""}{" upcoming" if upcoming else ""}"><div class="count"><small>{text(c["lead"])}</small><strong>{text(c["big"])}</strong><b>{text(c["tail"])}</b></div>'
            f'<div class="when"><h3>{text(activity["start_label"] if upcoming else activity["end_label"])}</h3><p>{text(activity["window_label"])}</p>'+(f'<p class="place">{text(place)}</p>' if place else '')+'</div></div>')

def text(value):return html.escape(str(value),quote=True)

def beijing(iso):
    t=dt.datetime.fromisoformat(iso.replace('Z','+00:00')).astimezone(dt.timezone(dt.timedelta(hours=8)));return t.strftime('%m.%d %H:%M')

def brand_label(s):
    """Return (is_series_art, caption) for a logo window. Series art is captioned by the series'
    proper name only, never with an "icon" suffix or a lowercase company slug."""
    media=s.get('resolved_media',{});subject=media.get('subject','')
    if media.get('kind')=='game_identity':
        return True,SERIES_NAMES.get(s.get('game')) or SERIES_NAMES.get(subject) or s.get('company') or subject
    return False,s.get('company') or SERIES_NAMES.get(s.get('game'),subject)

def cornerstone_extras(s):
    """Cornerstone reading-column extras: fact chips (region, source kind, publish time) and a short
    excerpt of the original text. Only facts already on the scene are shown; nothing is inferred."""
    if s.get('scene_type') in ('overview','activity_calendar','briefs'):return ''
    chips=[]
    if s.get('game_region'):chips.append(('国服' if s['game_region']=='cn' else '国际服',False))
    if s.get('activity'):chips.append((s['activity'].get('kind_label','活动'),False))
    elif s.get('source_type') in OFFICIAL_SOURCES:chips.append(('官方公告',False))
    elif s.get('scene_type')=='community_pulse':chips.append(('B站玩家评论',False))
    if not s.get('game_region') and s.get('publisher'):chips.append((s['publisher'],False))
    if s.get('published'):chips.append((beijing(s['published'])+' 发布',False))
    if s.get('activity',{}).get('end_at'):chips.append(('截止 '+beijing(s['activity']['end_at']),True))
    leader=s.get('speaker_identity') or s.get('source_type')=='leader_x'
    meta='' if s.get('activity') or leader or not chips else '<div class="meta">'+''.join(f'<span class="{"hot" if hot else ""}">{text(c)}</span>' for c,hot in chips)+'</div>'
    ev=s.get('evidence') or ''
    if not ev or s.get('scene_type')=='community_pulse' or leader:return meta
    out=''
    for x in [x.strip(' ·') for x in re.split(r'…|\.\.\.',ev) if x.strip()]:
        if len(out)>=70:break
        out+=('……' if out else '')+x
    label='官方原文' if s.get('source_type') in OFFICIAL_SOURCES else '原文摘录'
    return meta+f'<blockquote class="evidence"><b>{label}</b><p>{text(out)}</p></blockquote>'
def phrase(value):
    # Keep English/model tokens intact; Chinese still wraps naturally.
    return ''.join('<span class="keep">'+text(p)+'</span>' if re.match(r'[A-Za-z0-9]',p) else text(p)
                   for p in re.split(r'([A-Za-z][A-Za-z0-9.+_-]*(?: [A-Za-z0-9][A-Za-z0-9.+_-]*)*)',str(value)) if p)

def secondary_photo(root,scene,primary_media):
    """Find one additional verified official picture of the same orientation for mid-scene switching."""
    if not primary_media or primary_media.get('field')!='image' or not scene.get('item_id'):return None
    if scene.get('segment')=='community' or scene.get('scene_type') in {'overview','activity_calendar'}:return None
    from scene_media import article_images,image_info,quality
    cfg=load(root/'config.json') if (root/'config.json').is_file() else {}
    gate=cfg.get('presentation',{}).get('image_quality') or {}
    want_portrait=primary_media.get('layout')=='portrait'
    primary_rel=Path(primary_media['path']).as_posix()
    best=None
    for item in article_images(root,scene.get('item_id')):
        rel=Path(item['file']).as_posix()
        if rel==primary_rel:continue
        try:
            path,_=image_info(root,rel)
            q=quality(path,gate)
        except (ValueError,OSError):continue
        if q.get('reject') or q.get('long_poster'):continue
        is_portrait=q['height']>q['width']*1.35
        if is_portrait!=want_portrait:continue
        if best is None or q['score']>best[0]:best=(q['score'],path)
    return best[1] if best else None

def build(root,episode,plan):
    from build_film import source_publication_label
    root=Path(root);episode=Path(episode);ep=load(episode/'episode.json');timing=load(episode/'timings.json')
    from scene_media import validate
    media_audit=validate(ep,root)
    if media_audit:save(episode/'scene-media.json',media_audit)
    out=root/plan['artifact_directory'];out.mkdir(parents=True,exist_ok=True)
    assets=out/'assets';assets.mkdir(exist_ok=True)
    fonts=assets/'fonts';fonts.mkdir(exist_ok=True)
    for name in ['msyh.ttc','msyhbd.ttc']+EXTRA_FONTS.get(plan['template'],[]):
        shutil.copy2(Path('C:/Windows/Fonts')/name,fonts/name)
    for name in ['news-shot.css','news-shot.js']:
        shutil.copy2(Path(__file__).parent/name,out/name)
    cornerstone=plan['template']=='cornerstone'
    if cornerstone:
        from renderers.cornerstone_art import write_assets
        shutil.copy2(Path(__file__).parent/'cornerstone.css',out/'cornerstone.css');write_assets(assets)
    soundtrack=ensure_soundtrack(root,episode,timing['duration'])
    # Audio is attached by the renderer CLI, never advanced by browser playback.
    offsets=[];scenes=[];cards=[];chapters=[];folios=folio_numbers(ep['scenes'])
    extra=navigation_layout('multiplane')['content_extra_y']
    for index,s in enumerate(ep['scenes']):
        parts=[p for p in timing['sentences'] if p['scene_id']==s['id']]
        if not parts:raise ValueError('No timing for scene '+s['id'])
        start=parts[0]['start'];last=parts[-1]['end']
        end=next((p['start'] for p in timing['sentences'] if p['start']>=last and p['scene_id']!=s['id']),timing['duration'])
        offsets.append(dict(id=s['id'],start=start,end=end))
        mode='overview' if is_overview(s) else 'game' if s.get('game') else 'leader' if s.get('source_type')=='leader_x' or s.get('speaker_identity') else 'brief' if s.get('scene_type')=='temporary_news' or ep.get('edition_slot')=='temporary' else 'product' if s.get('logo') else 'social'
        scene=dict(id=s['id'],start=start,end=end,mode=mode,section=group(s),title=s['title'],
                   sentences=[dict(start=p['start'],end=p['end'],text=p.get('text','')) for p in parts])
        scenes.append(scene)
        logo='';picture='';diagram=''
        selected=[(s['resolved_media']['field'],s['resolved_media']['path'])] if s.get('resolved_media') else [(field,s.get(field)) for field in ['logo','image']]
        for field,value in selected:
            if not value or not isinstance(value,str):continue
            source=(root/value).resolve()
            if not source.is_file():raise ValueError('Missing local verified '+field+': '+value)
            name=f'{index}-'+source.name;shutil.copy2(source,assets/name)
            # 2026-11-26 (user): series art carries the series' proper name, never a "· 游戏图标" caption
            # or a lowercase company slug.
            series,label=brand_label(s)
            if field=='logo':logo=f'<aside class="brand{" series-mark" if series else ""}"><div class="brand-window"><img src="assets/{text(name)}" alt="{text(label)}"></div><b>{text(label)}</b></aside>'
            else:
                alt_path=secondary_photo(root,s,s.get('resolved_media'))
                if alt_path:
                    alt_name=f'{index}-alt-'+alt_path.name;shutil.copy2(alt_path,assets/alt_name)
                    picture=(f'<aside class="photo" data-multi="2">'
                             f'<img class="photo-img" data-idx="0" src="assets/{text(name)}" alt="{text(s.get("image_alt",s["title"]))}">'
                             f'<img class="photo-img" data-idx="1" src="assets/{text(alt_name)}" alt="{text(s.get("image_alt",s["title"]))}" style="display:none"></aside>')
                else:
                    picture=f'<aside class="photo"><img src="assets/{text(name)}" alt="{text(s.get("image_alt",s["title"]))}"></aside>'
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
        if s.get('scene_type')=='activity_calendar':mode='calendar';scene['mode']=mode
        if mode=='calendar':
            # 2026-11-22 活动日历 (1-3 pages, 8 rows/page, with DDL remaining progress bars & urgency tiers).
            rows=s.get('calendar_rows') or []
            if not rows:raise ValueError('ACTIVITY_CALENDAR: bind the calendar rows before rendering')
            grid_rows=max(3,(len(rows)+1)//2)
            def cal_card(r):
                tier=r.get('urgency_tier') or ('critical' if r.get('urgent') else 'normal')
                ulabel=r.get('urgency_label') or ''
                pct=int(r.get('progress_pct',55 if tier=='version' else 60))
                pill=f'<em class="cal-tier tier-{text(tier)}">{text(ulabel)}</em>' if ulabel else ''
                return (f'<article class="cal-row tier-{text(tier)}{" urgent" if r.get("urgent") else ""}" data-title="{text(r["title"])}" data-key="{text(r.get("key",""))}">'
                        f'<div class="cal-days{" word" if r["big"] in ("今天","明天") else ""}"><span class="cal-days-val"><strong>{text(r["big"])}</strong><b>{text(r["unit"])}</b></span></div>'
                        f'<div class="cal-text"><h2>{phrase(r["title"])}<i>{text(r["region"])}</i>{pill}</h2><p>{phrase(r["detail"])}</p>'
                        f'<div class="cal-progress"><span style="width:{pct}%"></span></div></div></article>')
            body=f'<div class="cal-grid" style="--cal-rows:{grid_rows}">'+''.join(cal_card(r) for r in rows)+'</div>'+logo
        elif mode=='overview':
            if len(facts)>4:raise ValueError('Upgrade the overview to at most four complete highlights before rendering')
            body='<p class="lead">'+text(s.get('lead','本期我们一起了解这些重点动态。'))+'</p><div class="overview-grid">'+''.join(
                f'<article data-idx="{i}"><div class="overview-head"><span class="overview-idx">{i+1:02}</span><div class="category">{text(f.get("category","重点新闻"))}</div></div><h2>{phrase(f["title"])}</h2><p>{phrase(f.get("detail",""))}</p></article>' for i,f in enumerate(facts))+'</div>'+logo+picture
        else:
            identity=(f'<div class="identity"><b>{text(s.get("speaker_name",s.get("publisher","")))}</b><span>{text(s.get("speaker_identity",""))}</span><i>{text({"opinion":"个人观点","preview":"预告 / 计划","experience":"使用体会","reshare":"转发信息"}.get(s.get("claim_type"),"推文动态"))}</i></div>' if mode in {'leader','original'} else '')
            body=identity+(countdown(s['activity']) if s.get('activity') else '')+'<div class="facts">'+''.join(f'<article data-idx="{i}"><span class="point-number">{i+1:02}</span><div><h2>{phrase(f["title"])}</h2><p>{phrase(f.get("detail",""))}</p></div></article>' for i,f in enumerate(facts))+'</div>'+logo+picture+diagram
        source=(f'<div class="source"><b>{text(s.get("publisher",""))}</b>　{source_publication_label(s)}<span>{text(re.sub(r"^https?://","",s.get("source_url","")))}</span></div>' if s.get('show_source',True) and mode!='overview' else '')
        if mode=='calendar':
            pg_tag=f'（第 {int(s["calendar_page"])}/{int(s["calendar_total_pages"])} 页）' if int(s.get('calendar_total_pages') or 1)>1 else ''
            source=f'<div class="source"><b>活动日历{pg_tag}</b>　时间均取自官方活动公告（{len(s.get("calendar_sources") or [1])} 份），服务器时间以公告为准'+(f'；另有 {int(s["calendar_more"])} 项进行中未列出' if s.get('calendar_more') else '')+'<span>原文链接见简介</span></div>'
        if s.get('brief_publishers'):source=f'<div class="source"><b>快讯来源</b>　{text(" · ".join(s["brief_publishers"]))}<span>每条出处见括号，原文链接见简介</span></div>'
        extras=cornerstone_extras(s) if cornerstone else ''
        classes=('has-meta ' if '<div class="meta">' in extras else '')+f'scene {mode}'+(' has-media' if logo or picture or diagram else '')+(' has-diagram' if diagram else '')+(' portrait-media' if s.get('resolved_media',{}).get('layout')=='portrait' else '')
        frame=''
        if picture and not diagram and mode in FIT_MODES and s.get('resolved_media'):
            hug,frame=photo_frame(s['resolved_media'],mode,extra);classes+=hug
        if mode in FIT_MODES:classes+=' fit'
        if s.get('activity'):classes+=' activity'
        badge=s.get('badge')
        badge_html=(f'<b class="segment-badge" style="display:inline-block;margin-left:22px;padding:4px 16px;font-size:24px;letter-spacing:1px;color:#fff;transform:skewX(-14deg);background:{ACTIVITY_COLORS[s["activity"]["kind"]] if s.get("activity") else (BADGE_COLORS.get(s.get("navigation_group")) or BADGE_COLORS.get(s.get("segment"),"#101218"))}">{text(badge)}</b>' if badge else '')
        cards.append(f'<section class="{classes}" id="scene-{text(s["id"])}"'+(f' style="{frame}"' if frame else '')+f'><div class="scene-folio">{folios[index]:02}</div><div class="kicker"><span>{text(scene["section"])}</span>{badge_html}<i></i></div><h1><span class="title-ink">{phrase(s["title"])}</span></h1>{body}{extras}{source}</section>')
        chapters.append(dict(id=s['id'],label=s.get('short_title',s['title']),start=start,end=end))
    captions=load(episode/'captions.json') if (episode/'captions.json').exists() else [dict(id=f'caption-{i}-{j}',**cue) for i,p in enumerate(timing['sentences']) for j,cue in enumerate(sentence_captions(p))]
    for c in captions:
        if '\n' in c['text']:raise ValueError('Only single-line captions are supported')
    from production_policy import modules as module_ranges
    modules=[dict(id=key,label=label,start=start,end=end) for key,label,start,end in module_ranges(ep,offsets,timing['duration'])]
    spec=dict(duration=timing['duration'],chapters=chapters,modules=modules,blue=TEMPLATE_BLUE.get(plan['template'],'#01A1FE'),full_bleed_edges=True,right_block_width=64,
              **navigation_layout('multiplane'),
              chapter_bounds=[dict(x=96+1728*c['start']/timing['duration'],width=1728*(c['end']-c['start'])/timing['duration']) for c in chapters])
    model=dict(duration=timing['duration'],scenes=scenes,captions=captions,progress=spec,template=plan['template'],require_page_image=bool(ep.get('page_image_policy_version')))
    data=json.dumps(model,ensure_ascii=False).replace('</','<\\/')
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>新闻视频</title><link rel="stylesheet" href="/multiplane/runtime/shot.css"><link rel="stylesheet" href="news-shot.css">{'<link rel="stylesheet" href="cornerstone.css">' if cornerstone else ''}</head><body><div id="stage" class="{plan['template']}" style="--caption-y:{spec['caption']['y']}px;--content-extra-y:{spec['content_extra_y']}px"><div class="edge-band"></div><div class="edge-ticks"></div>{f'<div class="cs-side">{text(SIDE_CODES.get(ep.get("edition_series"),"NEWS"))} — {text(ep.get("edition_date","").replace("-","."))}</div>' if cornerstone else ''}<div class="publication-label">{text(ep.get('edition_date','').replace('-','.'))}　{text(ep.get('footer_tag','新闻速报'))}</div>{''.join(cards)}<div id="wipe" class="wipe"></div><div id="caption" class="caption"></div><div class="navigation" style="--navigation-offset:{spec['nav_offset_y']}px"><div id="modules"></div><div class="now-label" id="now-label"></div><div id="clock"></div><div id="chapters"></div><div id="track"></div><div id="fill"></div><div id="markers"></div></div></div><script id="story-data" type="application/json">{data}</script><script src="/multiplane/runtime/shot.js"></script><script src="news-shot.js"></script></body></html>'''
    (out/'index.html').write_text(page,encoding='utf-8')
    save(episode/'scene-timings.json',offsets);save(episode/'captions.json',captions);save(episode/'progress.json',spec)
    save(out/'storyboard.json',model)
    save(episode/'render-assets.json',dict(shot=str(out/'index.html'),soundtrack=str(soundtrack),backend=plan['backend'],template=plan['template']))
    print(out);return out
