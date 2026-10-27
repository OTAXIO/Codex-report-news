"""Dual-ratio covers through Multiplane, preserving the cover.json contract."""
import shutil
from pathlib import Path
from PIL import Image
from renderer_backends import load,run_multiplane
from layout_policy import cover_footer
from renderers.multiplane import text

def make(root,episode,plan):
    root=Path(root);episode=Path(episode);ep=load(episode/'episode.json');brief=load(episode/'cover.json')
    source=(root/brief['image']).resolve()
    if not source.is_relative_to((root/'assets').resolve()) or not source.is_file():raise ValueError('Cover image must be a verified local asset')
    for ratio,width in [('16x9',1920),('4x3',1440)]:
        folder=root/plan['artifact_directory']/'covers'/ratio;folder.mkdir(parents=True,exist_ok=True)
        for font in ['msyh.ttc','msyhbd.ttc']:shutil.copy2(Path('C:/Windows/Fonts')/font,folder/font)
        shutil.copy2(source,folder/source.name)
        content_width=width*.61;logo_width=width*.27
        heading=text(brief.get('headline_top',''));headline=text(brief.get('headline_main',''));highlight=text(brief.get('highlight',''))
        page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><link rel="stylesheet" href="/multiplane/runtime/shot.css"><style>
@font-face{{font-family:News;src:url('msyhbd.ttc');font-weight:700}}*{{box-sizing:border-box}}#stage{{position:relative;width:{width}px;height:1080px;background:#fff;color:#101218;font-family:News;font-weight:700;overflow:hidden}}
.edge{{position:absolute;left:0;top:0;width:42px;height:1080px;background:#101218;transform:skew(-3deg)}}.blue{{position:absolute;right:-60px;top:0;width:100px;height:1080px;background:#01A1FE;transform:skew(-8deg)}}.copy{{position:absolute;left:90px;top:215px;width:{content_width}px}}h1{{font-size:{98 if width<1500 else 120}px;line-height:1.2;margin:0 0 30px}}h2{{font-size:{85 if width<1500 else 110}px;line-height:1.25;margin:0}}p{{font-size:32px;border-top:5px solid #01A1FE;padding-top:25px;margin-top:45px}}.image{{position:absolute;right:95px;top:320px;width:{logo_width}px;height:380px;object-fit:contain}}.date{{position:absolute;left:90px;top:855px;font-size:100px;letter-spacing:-4px}}.type{{position:absolute;left:370px;top:920px;font-size:34px}}.rule{{position:absolute;left:90px;bottom:70px;width:{width-190}px;height:9px;background:#01A1FE}}
.edge{{width:16px;transform:none}}.blue{{right:0;width:64px;transform:none}}
</style><div id="stage"><div class="edge"></div><div class="blue"></div><div class="copy"><h1>{heading}</h1><h2>{headline}</h2><p>{highlight}</p></div><img class="image" src="{text(source.name)}"><div class="date">{text(ep['edition_date'][5:].replace('-','.'))}</div><div class="type">{text(cover_footer(brief))}</div><div class="rule"></div></div><script src="/multiplane/runtime/shot.js"></script><script>Shot.define({{duration:1,fonts:[['700 120px News','新闻模型']],setup:()=>Promise.all(Array.from(document.images,i=>i.decode())),render(t){{}},post:{{motionBlur:1,grain:0}}}})</script></html>'''
        shot=folder/'index.html';shot.write_text(page,encoding='utf-8')
        result=run_multiplane(root,'stills',shot,['--at','0','--out',str(folder/'stills'),'--overwrite'],episode/('cover-'+ratio+'-render.json'),plan)
        output=Path(result['data']['stills'][0]['path']);shutil.copy2(output,episode/('cover-'+ratio+'.png'))
    with Image.open(episode/'cover-4x3.png') as image:image.convert('RGB').resize((1200,900),Image.Resampling.LANCZOS).save(episode/'cover-bilibili.jpg',quality=96)
