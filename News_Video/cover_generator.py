"""Render an episode-specific factual cover from cover.json and verified assets."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
from layout_policy import cover_footer

ROOT=Path(__file__).parent
BLUE='#01A1FE';BLACK='#101218'
LABELS={'morning':'早间新闻','noon':'午间新闻','night':'晚间新闻','temporary':'临时新闻','preview':'新闻样片'}

def font(size,bold=True):return ImageFont.truetype('C:/Windows/Fonts/'+('msyhbd.ttc' if bold else 'msyh.ttc'),size)

def fitted(draw,text,initial,width,bold=True):
    minimum=min(56,max(18,initial//2))
    for size in range(initial,minimum-1,-2):
        f=font(size,bold);box=draw.textbbox((0,0),text,font=f)
        if box[2]-box[0]<=width:return f
    raise ValueError('Cover text is too long; shorten the factual headline')

def make_hyperframes(episode_id):
    out=ROOT/'episodes'/episode_id
    if (out/'release.json').exists():raise ValueError('Published edition: create a new revision')
    ep=json.loads((out/'episode.json').read_text(encoding='utf-8'))
    brief=json.loads((out/'cover.json').read_text(encoding='utf-8'))
    image_path=(ROOT/brief['image']).resolve()
    if not image_path.is_relative_to((ROOT/'assets').resolve()):raise ValueError('Cover image must be a verified asset under assets/')
    logo=Image.open(image_path).convert('RGBA')
    if '/logos/' in image_path.as_posix():
        # Official logo downloads may contain a large white/transparent canvas.
        box=logo.getchannel('A').getbbox() if logo.getchannel('A').getextrema()[0]<255 else ImageChops.difference(logo.convert('RGB'),Image.new('RGB',logo.size,'white')).convert('L').point(lambda x:255 if x>12 else 0).getbbox()
        if box:logo=logo.crop(box)
        scale=min(480/logo.width,480/logo.height)
        logo=logo.resize((round(logo.width*scale),round(logo.height*scale)),Image.Resampling.LANCZOS)
    else:logo.thumbnail((480,480),Image.Resampling.LANCZOS)
    label=LABELS[ep['edition_slot']];date=ep['edition_date'][5:].replace('-','.')
    image=Image.new('RGB',(1920,1080),'white');d=ImageDraw.Draw(image)
    d.polygon([(1840,0),(1920,0),(1920,1080),(1770,1080)],fill=BLUE)
    d.polygon([(1880,0),(1920,0),(1920,180),(1860,120)],fill=BLACK)
    d.rectangle((112,100,124,162),fill=BLUE);d.text((156,90),label,font=font(64),fill=BLACK)
    for key,y,size,color in [('headline_top',250,120,BLACK),('headline_main',420,116,BLACK),('highlight',560,230,BLUE)]:
        text=brief.get(key,'')
        if text:d.text((116,y),text,font=fitted(d,text,size,1060),fill=color)
    d.text((124,895),date,font=font(89),fill=BLACK)
    footer=cover_footer(brief);d.text((434,929),footer,font=fitted(d,footer,38,750,False),fill=BLACK)
    d.line((124,1015,1670,1015),fill=BLUE,width=12)
    image.paste(logo,(1240+(480-logo.width)//2,340+(480-logo.height)//2),logo)
    name=brief.get('image_label','');box=d.textbbox((0,0),name,font=font(36));d.text((1480-(box[2]-box[0])/2,835),name,font=font(36),fill=BLACK)
    image.save(out/'cover-16x9.png')
    cover43=Image.new('RGB',(1920,1440),'white');cover43.paste(image,(0,180));cover43.save(out/'cover-4x3.png')
    cover43.resize((1200,900),Image.Resampling.LANCZOS).save(out/'cover-bilibili.jpg',quality=96,subsampling=0)
    print(out/'cover-16x9.png')

def make(episode_id,renderer=None,template=None):
    from renderer_backends import select_plan
    out=ROOT/'episodes'/episode_id;plan=select_plan(ROOT,out,renderer,template)
    if plan['backend']=='multiplane':
        from renderers.multiplane_cover import make as make_multiplane_cover
        make_multiplane_cover(ROOT,out,plan)
    else:make_hyperframes(episode_id)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');p.add_argument('--renderer',choices=['hyperframes','multiplane']);p.add_argument('--template',choices=['editorial','graphic']);a=p.parse_args();make(a.episode,a.renderer,a.template)
