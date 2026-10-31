"""Render an episode-specific factual cover from cover.json and verified assets."""
import argparse,json,math
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

def load_brief(episode_id):
    out=ROOT/'episodes'/episode_id
    if (out/'release.json').exists():raise ValueError('Published edition: create a new revision')
    ep=json.loads((out/'episode.json').read_text(encoding='utf-8'))
    brief=json.loads((out/'cover.json').read_text(encoding='utf-8'))
    from production_policy import validate_lead_contract
    publication=json.loads((out/'publication.json').read_text(encoding='utf-8')) if (out/'publication.json').exists() else None
    validate_lead_contract(ep,publication,brief)
    return out,ep,brief
def cover_art(brief,size):
    image_path=(ROOT/brief['image']).resolve()
    if not image_path.is_relative_to((ROOT/'assets').resolve()):raise ValueError('Cover image must be a verified asset under assets/')
    logo=Image.open(image_path).convert('RGBA')
    if '/logos/' in image_path.as_posix():
        # Official logo downloads may contain a large white/transparent canvas.
        box=logo.getchannel('A').getbbox() if logo.getchannel('A').getextrema()[0]<255 else ImageChops.difference(logo.convert('RGB'),Image.new('RGB',logo.size,'white')).convert('L').point(lambda x:255 if x>12 else 0).getbbox()
        if box:logo=logo.crop(box)
        scale=min(size/logo.width,size/logo.height)
        logo=logo.resize((round(logo.width*scale),round(logo.height*scale)),Image.Resampling.LANCZOS)
    else:logo.thumbnail((size,size),Image.Resampling.LANCZOS)
    return logo

def make_hyperframes(episode_id):
    out,ep,brief=load_brief(episode_id)
    logo=cover_art(brief,480)
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

NAVY='#023077';LINE=(1,147,238)  # LINE = 12% navy speed line over the blue field
def display(size):return ImageFont.truetype('C:/Windows/Fonts/impact.ttf',size)

def sheared(layer,angle=12):
    # Same lean as the video's skewX(-12deg): the top shifts right, the baseline stays put.
    k=math.tan(math.radians(angle));pad=math.ceil(k*layer.height)
    return layer.transform((layer.width+pad,layer.height),Image.Transform.AFFINE,(1,k,-pad,0,1,0),Image.Resampling.BICUBIC)

def tag(text,f,fg,bg,shadow=None,offset=0,padx=0,pady=0,outline=None):
    """A slanted label; bg None draws bare text, outline gives it a hard ink shadow."""
    box=ImageDraw.Draw(Image.new('L',(1,1))).textbbox((0,0),text,font=f)
    w,h=box[2]-box[0]+2*padx,box[3]-box[1]+2*pady
    layer=Image.new('RGBA',(w+offset,h+offset),(0,0,0,0));d=ImageDraw.Draw(layer)
    if bg:
        if shadow:d.rectangle((offset,offset,w+offset-1,h+offset-1),fill=shadow)
        d.rectangle((0,0,w-1,h-1),fill=bg)
    elif outline:d.text((padx-box[0]+offset,pady-box[1]+offset),text,font=f,fill=outline)
    d.text((padx-box[0],pady-box[1]),text,font=f,fill=fg)
    return sheared(layer)

def fitted_tag(text,initial,width,**style):
    for size in range(initial,max(18,initial//2)-1,-4):
        layer=tag(text,font(size),**style)
        if layer.width<=width:return layer
    raise ValueError('Cover text is too long; shorten the factual headline')

def persona_canvas(ep,brief,height):
    """Video-matching P3 blue/white cover; 4:3 is laid out natively, not letterboxed."""
    W,H=1920,height;dy=(H-1080)//2
    image=Image.new('RGB',(W,H),BLUE);d=ImageDraw.Draw(image)
    run=math.tan(math.radians(25))*H
    for x in range(-int(run),W+60,44):d.polygon([(x+run,0),(x+run+3,0),(x+3,H),(x,H)],fill=LINE)
    edge=lambda x,base:base-80*x/W  # bottom band rises toward the right, like the video header edge
    band=H-215
    d.polygon([(0,edge(0,band)-30),(W,edge(W,band)-30),(W,edge(W,band)-20),(0,edge(0,band)-20)],fill=NAVY)
    d.polygon([(0,edge(0,band)-12),(W,edge(W,band)-12),(W,edge(W,band)),(0,edge(0,band))],fill=BLACK)
    d.polygon([(0,edge(0,band)),(W,edge(W,band)),(W,H),(0,H)],fill='white')
    # Verified art in a tilted white frame with an ink outline and hard shadow.
    art=cover_art(brief,520);frame=Image.new('RGBA',(600,600),'white');frame.paste(art,((600-art.width)//2,(600-art.height)//2),art)
    framed=Image.new('RGBA',(640,640),(0,0,0,0));fd=ImageDraw.Draw(framed)
    fd.rectangle((28,28,639,639),fill=BLACK);fd.rectangle((0,0,611,611),fill=BLACK);framed.paste(frame,(6,6))
    framed=framed.rotate(4,resample=Image.Resampling.BICUBIC,expand=True)
    cx,cy=1450,440+dy;image.paste(framed,(cx-framed.width//2,cy-framed.height//2),framed)
    if brief.get('image_label'):
        label=tag(brief['image_label'],font(38),'white',BLACK,shadow=BLUE,offset=6,padx=22,pady=8)
        image.paste(label,(cx-label.width//2,cy+framed.height//2-34),label)
    # Headline stack: slot tag, subject, black title bar, oversized highlight.
    slot=tag(LABELS[ep['edition_slot']],font(54),BLUE,'white',shadow=BLACK,offset=8,padx=26,pady=10)
    image.paste(slot,(104,70+dy//2),slot)
    y=200+dy
    if brief.get('headline_top'):
        top=fitted_tag(brief['headline_top'],150,1060,fg='white',bg=None,outline=BLACK,offset=10)
        image.paste(top,(104,y),top);y+=top.height+24
    main=fitted_tag(brief['headline_main'],110,1080,fg='white',bg=BLACK,shadow='white',offset=12,padx=28,pady=14)
    image.paste(main,(96,y),main);y+=main.height+34
    if brief.get('highlight'):
        hi=fitted_tag(brief['highlight'],170,1040,fg=BLUE,bg='white',shadow=BLACK,offset=14,padx=30,pady=6)
        image.paste(hi,(110,min(y,band-hi.height-70)),hi)
    # The edition date appears exactly once, on the white band.
    date=ep['edition_date'][5:].replace('-','.')
    stamp=tag(date,display(140),BLACK,None);image.paste(stamp,(110,H-188),stamp)
    footer=cover_footer(brief)
    if footer!=LABELS[ep['edition_slot']]:
        note=tag(footer,fitted(d,footer,44,760,False),BLACK,None);image.paste(note,(110+stamp.width+40,H-112),note)
    return image

def make_persona(episode_id):
    out,ep,brief=load_brief(episode_id)
    persona_canvas(ep,brief,1080).save(out/'cover-16x9.png')
    cover43=persona_canvas(ep,brief,1440);cover43.save(out/'cover-4x3.png')
    cover43.resize((1200,900),Image.Resampling.LANCZOS).save(out/'cover-bilibili.jpg',quality=96,subsampling=0)
    print(out/'cover-16x9.png')

def make(episode_id,renderer=None,template=None,style=None):
    # Cover art has its own user preference; selecting it must not change the
    # video's pinned Multiplane/B render plan.
    cfg=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    backend=renderer or cfg.get('cover_generation',{}).get('backend','hyperframes')
    if backend=='hyperframes':
        style=style or cfg.get('cover_generation',{}).get('style','legacy')
        if style not in {'legacy','persona'}:raise ValueError('Unknown cover style')
        return make_persona(episode_id) if style=='persona' else make_hyperframes(episode_id)
    if backend!='multiplane':raise ValueError('Unknown cover renderer')
    from renderer_backends import select_plan
    out=ROOT/'episodes'/episode_id;plan=select_plan(ROOT,out,backend,template)
    if plan['backend']=='multiplane':
        from renderers.multiplane_cover import make as make_multiplane_cover
        make_multiplane_cover(ROOT,out,plan)
    else:make_hyperframes(episode_id)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');p.add_argument('--renderer',choices=['hyperframes','multiplane']);p.add_argument('--template',choices=['editorial','graphic']);p.add_argument('--style',choices=['legacy','persona']);a=p.parse_args();make(a.episode,a.renderer,a.template,a.style)
