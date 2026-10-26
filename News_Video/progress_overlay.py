"""Editable chapter overview and deterministic whole-video progress."""
import html,json,math
def group(scene):
    section=scene['section']
    if scene['id']=='intro':return '开场'
    if section.startswith('AI'):return 'AI 动态'
    if section.startswith('国内'):return '国内新闻'
    if section.startswith('国际'):return '国际新闻'
    return section

def build_progress(episode,offsets,duration,blue):
    footer_tag=html.escape(episode.get('footer_tag','AI 生成 · 本地样片'))
    chapters=[];headlines=[]
    for scene,timing in zip(episode['scenes'],offsets):
        label=group(scene)
        chapters.append(dict(id=scene['id'],label=scene.get('short_title',scene['title']),start=timing['start'],end=timing['end'],kind='intro' if scene['id']=='intro' else 'news'))
        text=label+' · '+scene['title']
        headlines.append(f'<div id="overview-{scene["id"]}" class="headline clip" data-start="{timing["start"]:.6f}" data-duration="{timing["end"]-timing["start"]:.6f}" data-track-index="4">{html.escape(text)}</div>')
    labels=[];markers=[]
    for i,c in enumerate(chapters):
        x=192+1536*c['start']/duration;w=1536*(c['end']-c['start'])/duration
        label=html.escape(c['label'])
        labels.append(f'<span class="chapter" data-layout-allow-occlusion="true" style="left:{x:.4f}px;width:{w:.4f}px">{label}</span>')
        labels.append(f'<div id="active-{c["id"]}" class="chapter current clip" data-start="{c["start"]:.6f}" data-duration="{c["end"]-c["start"]:.6f}" data-track-index="5" style="left:{x:.4f}px;width:{w:.4f}px"><span>{label}</span></div>')
        if i:markers.append(f'<i class="marker" style="left:{x:.4f}px"></i>')
    modules=[];module_html=[]
    social=next((i for i,s in enumerate(episode['scenes']) if s['section'].startswith(('国内','国际'))),None)
    ranges=([('ai','AI 动态',0,offsets[social]['start'])] if social not in (None,0) else [])
    if social is None:ranges=[('ai','AI 动态',0,duration)]
    elif social is not None:ranges.append(('news','国内外重点新闻',offsets[social]['start'],duration))
    if episode.get('edition_slot')=='temporary':ranges=[('temporary','临时新闻',0,duration)]
    for mid,label,start,end in ranges:
        x=192+1536*start/duration;w=1536*(end-start)/duration
        modules.append(dict(id=mid,label=label,start=start,end=end))
        module_html.append(f'<div class="module" data-layout-allow-occlusion="true" style="left:{x:.4f}px;width:{w:.4f}px">{label}</div>')
        module_html.append(f'<div id="module-active-{mid}" class="module module-active clip" data-start="{start:.6f}" data-duration="{end-start:.6f}" data-track-index="6" style="left:{x:.4f}px;width:{w:.4f}px">{label}</div>')
    end_seconds=round(duration);total=f'{end_seconds//60:02}:{end_seconds%60:02}'
    markup=f'''<template><style>
@font-face{{font-family:NewsSans;src:url('assets/fonts/msyh.ttc');font-weight:400}}
@font-face{{font-family:NewsSans;src:url('assets/fonts/msyhbd.ttc');font-weight:700}}
#root{{position:absolute;inset:0;pointer-events:none;font-family:NewsSans;color:#101218}}
.footer{{position:absolute;left:192px;top:930px;width:1536px;height:126px;background:#FFFFFF;border-top:1px solid #E4E7EB}}
.module{{position:absolute;top:938px;height:32px;box-sizing:border-box;font-size:26px;line-height:29px;font-weight:700;text-align:center;color:#757A82;background:#FFFFFF;border-bottom:4px solid #E4E7EB}}
.module-active{{color:#101218;border-bottom-color:var(--blue,{blue})}}
.headline{{position:absolute;left:192px;top:977px;width:940px;height:34px;font-size:24px;line-height:32px;font-weight:700}}
.tag{{position:absolute;left:1170px;top:980px;font-size:19px;line-height:28px}}
.clock{{position:absolute;right:192px;top:977px;font-size:24px;line-height:32px;font-variant-numeric:tabular-nums;text-align:right}}
.chapter{{position:absolute;top:1013px;height:28px;font-size:18px;line-height:26px;text-align:center;white-space:nowrap}}
.current{{background:#FFFFFF;font-weight:700}}.current span{{display:inline-block;background:var(--blue,{blue});padding:0}}
.track,.fill{{position:absolute;left:192px;top:1045px;width:1536px;height:8px}}
.track{{background:#E4E7EB}}.fill{{background:var(--blue,{blue});transform-origin:left center}}
.marker{{position:absolute;top:1042px;width:2px;height:14px;background:#101218}}
</style><div id="root" data-composition-id="progress" data-width="1920" data-height="1080">
<div id="progress-frame" class="clip" data-start="0" data-duration="{duration:.6f}" data-layout-allow-overlap="true"><div class="footer"></div>{''.join(module_html)}<div class="tag">{footer_tag}</div><div id="progress-clock" class="clock">00:00 / {total}</div>{''.join(labels)}<div class="track"></div><div id="progress-fill" class="fill"></div>{''.join(markers)}</div>{''.join(headlines)}
</div><script>
const time={{value:0}};const clock=document.getElementById('progress-clock');
function formatTime(t){{const s=Math.floor(Math.max(0,t));return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}}
const tl=gsap.timeline({{paused:true}});
tl.fromTo('#progress-fill',{{scaleX:0}},{{scaleX:1,duration:{duration:.9f},ease:'none'}},0);
tl.to(time,{{value:{duration:.9f},duration:{duration:.9f},ease:'none',onUpdate:()=>{{clock.textContent=formatTime(time.value)+' / {total}';}}}},0);
window.__timelines['progress']=tl;
</script></template>'''
    spec=dict(duration=duration,chapters=chapters,modules=modules,module_highlight_y=968,bar=dict(x=192,y=1045,width=1536,height=8),blue=blue,clock_step_seconds=1)
    return markup,spec
