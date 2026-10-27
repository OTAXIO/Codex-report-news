"""Build editable, offline HyperFrames scenes with burned-in captions."""
import argparse, html, json, re, shutil, datetime
from pathlib import Path
from progress_overlay import build_progress
from layout_policy import folio_numbers,is_overview
from caption_layout import sentence_captions,tokens,width
ROOT=Path(__file__).parent
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def esc(value): return html.escape(str(value),quote=True)
def overview_markup(value):
    parts=re.split(r'(?<=[，。；！？])',str(value))
    units=[]
    for part in parts:
        if not part:continue
        units.extend([part] if width(part)<=22 else tokens(part))
    return ''.join('<span class="overview-phrase">'+esc(unit)+'</span>' for unit in units)


def source_publication_label(scene):
    published=scene.get('published','')
    if not published:return '发布时间未提供'
    if 'T' not in published or scene.get('published_precision')=='date':
        return published[:10].replace('-','.')
    try:stamp=datetime.datetime.fromisoformat(published.replace('Z','+00:00'))
    except ValueError:return '发布时间待核实'
    if stamp.tzinfo is None:
        return stamp.strftime('%Y.%m.%d %H:%M')+'（来源时区未提供）'
    return stamp.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y.%m.%d %H:%M 北京时间')

def build_hyperframes(episode_id,film_directory=None):
    from episode_paths import episode_directory
    cfg=read(ROOT/'config.json'); epdir=episode_directory(ROOT,episode_id)
    episode=read(epdir/'episode.json'); timing=read(epdir/'timings.json')
    film=Path(film_directory) if film_directory else ROOT/'film'; assets=film/'assets'; comps=film/'compositions'
    assets.mkdir(parents=True,exist_ok=True); comps.mkdir(exist_ok=True)
    (assets/'fonts').mkdir(exist_ok=True)
    for filename in ('msyh.ttc','msyhbd.ttc'):
        target=assets/'fonts'/filename
        if not target.exists():shutil.copyfile(Path('C:/Windows/Fonts')/filename,target)
    shutil.copyfile(ROOT/'node_modules/hyperframes/dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js',assets/'gsap.min.js')
    from audio_mix import ensure_soundtrack
    soundtrack=ensure_soundtrack(ROOT,epdir,timing['duration'])
    shutil.copyfile(soundtrack,assets/'narration.wav')
    duration=timing['duration']; hosts=[]; offsets=[]; captions=[]
    folios=folio_numbers(episode['scenes'])
    for index,scene in enumerate(episode['scenes']):
        parts=[x for x in timing['sentences'] if x['scene_id']==scene['id']]
        start=parts[0]['start']; end=(next((x['start'] for x in timing['sentences'] if x['start']>parts[-1]['end']),duration))
        length=end-start; sid=scene['id']; offsets.append(dict(id=sid,start=start,end=end))
        facts=''.join(f'<li><div class="point">{esc(f["title"])}</div><div class="detail">{esc(f["detail"])}</div></li>' if isinstance(f,dict) else f'<li><div class="point">{esc(f)}</div></li>' for f in scene['facts'])
        overview=is_overview(scene)
        lead_html=''
        overview_css=''
        if overview:
            facts=''.join(f'<li><div class="overview-category">{esc(f.get("category","重点新闻"))}</div><div class="point">{overview_markup(f["title"])}</div><div class="detail">{overview_markup(f["detail"])}</div></li>' for f in scene['facts'])
            lead_html=f'<div class="overview-lead">{esc(scene.get("lead","本期我们将一起了解这些重点新闻。"))}</div><div class="overview-note">{esc(scene.get("footer_note","本期重点将按正文顺序展开。"))}</div>'
            overview_css='''
.title{font-size:62px;width:1460px}
.overview-lead{position:absolute;left:192px;top:284px;width:1460px;font-size:28px;line-height:1.45;color:#414955}
.facts{top:354px;width:1460px}
.facts ul{display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:216px;column-gap:42px;row-gap:18px}
.facts li{margin:0;padding:0 0 0 20px;border-left:4px solid var(--blue);overflow:visible}
.facts li:before{content:none}
.overview-phrase{white-space:nowrap}
.overview-category{font-size:28px;line-height:1.3;color:#006AAA;margin-bottom:9px;font-weight:700}
.point{font-size:30px;line-height:1.32}
.detail{font-size:28px;line-height:1.42;margin-top:10px;color:#414955}
.overview-note{position:absolute;left:192px;top:822px;width:1460px;font-size:22px;line-height:1.3;color:#414955}
'''
        logo=''
        if scene.get('logo'):
            source_logo=ROOT/scene['logo']
            if not source_logo.is_file():raise ValueError('Missing verified company logo: '+str(source_logo))
            (assets/'logos').mkdir(exist_ok=True);shutil.copyfile(source_logo,assets/'logos'/source_logo.name)
            logo=f'<div class="brand"><img src="{esc(scene["logo"])}" alt="{esc(scene["company"])} organization logo"><div>{esc(scene["company"])}</div></div>'
        identity_html='';identity_css=''
        if scene.get('speaker_identity') and not overview:
            label={'opinion':'个人观点','preview':'预告 / 计划','experience':'使用体会','reshare':'转发信息'}.get(scene.get('claim_type'),'推文动态')
            identity_html=f'<div class="speaker-line"><strong>{esc(scene.get("speaker_name",scene.get("publisher","")))}</strong><span>　｜　{esc(scene["speaker_identity"])}　·　{esc(label)}</span></div>'
            identity_css='.title{top:178px;font-size:56px;line-height:1.25;width:'+('1000px' if logo else '1460px')+'}.speaker-line{position:absolute;left:192px;top:350px;width:1050px;padding-left:18px;border-left:4px solid var(--blue);font-size:28px;line-height:1.4}.speaker-line strong{color:#006AAA}.speaker-line span{font-weight:400}.facts,.facts.has-brand{top:418px}'
        date=source_publication_label(scene)
        source=scene.get('publisher','本地制作流程说明')
        url=scene.get('source_url','')
        shorturl=re.sub(r'^https?://','',url).split('?')[0]
        if len(shorturl)>96:shorturl=shorturl[:93]+'…'
        source_html=(f'<div class="source" style="{"width:1050px" if logo else ""}">来源：{esc(source)}　{esc(date)}<br>{esc(shorturl)}</div>' if scene.get('show_source',True) else '')
        data=f'''<template>
<style>
@font-face{{font-family:NewsSans;src:url('assets/fonts/msyh.ttc');font-weight:400}}
@font-face{{font-family:NewsSans;src:url('assets/fonts/msyhbd.ttc');font-weight:700}}
#root{{position:absolute;inset:0;background:#FFFFFF;color:#101218;font-family:NewsSans;overflow:hidden}}
.edge{{position:absolute;right:-35px;top:0;width:105px;height:1080px;background:var(--blue,{cfg['theme']['blue']});transform:skew(-4deg)}}
.edge:before{{content:'';position:absolute;right:30px;top:0;width:20px;height:160px;background:#101218}}
.edge:after{{content:'';position:absolute;right:55px;bottom:75px;width:60px;height:150px;background:#101218;clip-path:polygon(70% 0,100% 0,30% 100%,0 100%)}}
.folio{{position:absolute;right:100px;top:119px;color:#101218;font-size:48px;font-weight:700}}
.kicker{{position:absolute;left:192px;top:115px;font-size:32px;font-weight:700;letter-spacing:4px}}
.kicker:before{{content:'';position:absolute;left:-30px;top:4px;width:8px;height:34px;background:var(--blue,{cfg['theme']['blue']})}}
.title{{position:absolute;left:192px;top:190px;width:1190px;font-size:70px;font-weight:700;line-height:1.28}}
.brand{{position:absolute;left:1260px;top:300px;width:460px;text-align:center;font-size:30px;line-height:1.4;z-index:2}}
.brand img{{display:block;width:440px;height:440px;object-fit:contain;margin:0 auto 10px}}
.facts{{position:absolute;left:192px;top:338px;width:1480px;background:transparent;color:#101218}}
.facts.has-brand{{top:318px;width:1000px}}
.facts.has-brand li{{margin-bottom:14px}}
.facts.has-brand .point{{font-size:34px}}
.facts.has-brand .detail{{font-size:28px;line-height:1.35;margin-top:6px}}
ul{{margin:0;padding:0;list-style:none}}li{{position:relative;margin:0 0 18px;padding-left:28px}}li:before{{content:'·';position:absolute;left:0;top:0;font-size:36px;font-weight:700}}
.point{{font-size:36px;line-height:1.3;font-weight:700}}.detail{{font-size:29px;line-height:1.4;margin-top:8px}}
.source{{position:absolute;left:192px;top:740px;width:1450px;font-size:23px;line-height:1.35;overflow-wrap:anywhere}}
.stamp{{position:absolute;left:192px;top:1005px;color:#101218;font-size:22px;letter-spacing:2px}}
{overview_css}
{identity_css}
</style>
<div id="root" data-composition-id="{sid}" data-width="1920" data-height="1080">
<div id="{sid}-body" class="clip" data-start="0" data-duration="{length:.6f}" data-layout-allow-overlap="true" data-layout-allow-overflow="true">
<div class="edge"></div><div class="folio">{folios[index]:02d}</div>
<div class="kicker">{esc(scene['section'])}</div><div class="title">{esc(scene['title'])}</div>
{logo}
{lead_html}
{identity_html}
<div class="facts{' has-brand' if logo else ''}"><ul>{facts}</ul></div>
{source_html}
</div></div>
<script>const tl=gsap.timeline({{paused:true}});tl.fromTo('#{sid}-body',{{x:44,opacity:0}},{{x:0,opacity:1,duration:.20,ease:'power3.out'}},0);window.__timelines['{sid}']=tl;</script>
</template>'''
        (comps/(sid+'.html')).write_text(data,encoding='utf-8')
        hosts.append(f'<div id="{sid}" class="clip" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{start:.6f}" data-duration="{length:.6f}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>')
    for i,s in enumerate(timing['sentences']):
        for j,cue in enumerate(sentence_captions(s)):
            captions.append(dict(id=f'caption-{i}-{j}',**cue))
    caphtml=''.join(f'<div id="{x["id"]}" class="caption clip" data-start="{x["start"]:.6f}" data-duration="{x["end"]-x["start"]:.6f}" data-track-index="3">{esc(x["text"]).replace(chr(10),"<br>")}</div>' for x in captions)
    captionfile=f'''<template><style>@font-face{{font-family:NewsSans;src:url('assets/fonts/msyhbd.ttc');font-weight:700}}#root{{position:absolute;inset:0;pointer-events:none}}.caption{{position:absolute;left:192px;bottom:140px;width:1536px;min-height:88px;padding:12px 30px;background:#FFFFFF;color:#101218;font:700 40px/1.3 NewsSans;text-align:center;box-sizing:border-box}}</style><div id="root" data-composition-id="captions" data-width="1920" data-height="1080">{caphtml}</div><script>window.__timelines['captions']=gsap.timeline({{paused:true}});</script></template>'''
    captionfile=captionfile.replace('bottom:140px','bottom:160px').replace('min-height:88px','min-height:64px').replace('text-align:center;box-sizing:border-box','text-align:center;white-space:nowrap;box-sizing:border-box')
    (comps/'captions.html').write_text(captionfile,encoding='utf-8')
    variables=esc(json.dumps([dict(id='blue',type='color',label='主蓝色',default=cfg['theme']['blue'])],ensure_ascii=False))
    root=f'''<!doctype html><html lang="zh-CN" data-composition-variables='{variables}'><head><meta charset="utf-8"><script src="assets/gsap.min.js"></script><style>*{{box-sizing:border-box}}html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:#FFFFFF}}:root{{--blue:{cfg['theme']['blue']}}}#root{{position:relative;width:1920px;height:1080px}}#root>.clip{{position:absolute;inset:0}}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{duration:.6f}" data-width="1920" data-height="1080" data-fps="30">{''.join(hosts)}<div id="captions" class="clip" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{duration:.6f}" data-track-index="3" data-track-kind="captions" data-width="1920" data-height="1080" style="z-index:10"></div><audio id="narration" class="clip" src="assets/narration.wav" data-start="0" data-duration="{duration:.6f}" data-track-index="2"></audio></div><script>window.__timelines=window.__timelines||{{}};window.__timelines.main=gsap.timeline({{paused:true}});</script></body></html>'''
    progress,spec=build_progress(episode,offsets,duration,cfg['theme']['blue'])
    (comps/'progress.html').write_text(progress,encoding='utf-8')
    host=f'<div id="progress" class="clip" data-composition-id="progress" data-composition-src="compositions/progress.html" data-start="0" data-duration="{duration:.6f}" data-track-index="4" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index:20"></div>'
    root=root.replace('<audio id="narration"',host+'<audio id="narration"')
    (film/'index.html').write_text(root,encoding='utf-8')
    (epdir/'progress.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    (film/'hyperframes.json').write_text(json.dumps({'name':'news-video','version':'1.0.0'},indent=2),encoding='utf-8')
    (epdir/'scene-timings.json').write_text(json.dumps(offsets,ensure_ascii=False,indent=2),encoding='utf-8')
    (epdir/'captions.json').write_text(json.dumps(captions,ensure_ascii=False,indent=2),encoding='utf-8')
    print(film)
def build(episode_id,renderer=None,template=None):
    from episode_paths import episode_directory
    from renderer_backends import select_plan
    epdir=episode_directory(ROOT,episode_id)
    plan=select_plan(ROOT,epdir,renderer,template)
    if plan['backend']=='hyperframes':
        build_hyperframes(episode_id,ROOT/plan['artifact_directory'])
    else:
        from renderers.multiplane import build as build_multiplane
        build_multiplane(ROOT,epdir,plan)
    return ROOT/plan['artifact_directory']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');p.add_argument('--renderer',choices=['hyperframes','multiplane']);p.add_argument('--template',choices=['editorial','graphic']);a=p.parse_args();build(a.episode,a.renderer,a.template)
