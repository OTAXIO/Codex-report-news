"""Render an episode-specific factual cover from cover.json and verified assets."""
import argparse,json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageChops
from layout_policy import cover_footer

ROOT=Path(__file__).parent
BLUE='#01A1FE';BLACK='#101218'
LABELS={'morning':'早间新闻','noon':'午间新闻','night':'晚间新闻','temporary':'临时新闻','preview':'新闻样片'}

def slot_label(ep):
    from edition_series import label
    return label(ep,LABELS[ep['edition_slot']])

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
    label=slot_label(ep);date=ep['edition_date'][5:].replace('-','.')
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

SLANT=math.tan(math.radians(12))  # same lean as the video's skewX(-12deg)
# 2026-11-12 user minimums: line 1 never below the "更新第二阶段" sample (138px), line 3 never
# below the "两千八百亿" sample (166px). The picture shrinks (to ART_MIN) before text does.
TOP_MIN,HI_MIN,MAIN_MIN,ART_MIN=138,166,52,360

def tag(text,f,fg,bg,shadow=None,offset=0,padx=0,pady=0,outline=None):
    """Upright text (2026-11-12: no slanted lettering); only a background plate keeps the
    parallelogram lean. bg None draws bare text, outline gives it a hard ink shadow."""
    box=ImageDraw.Draw(Image.new('L',(1,1))).textbbox((0,0),text,font=f)
    w,h=box[2]-box[0]+2*padx,box[3]-box[1]+2*pady
    lean=math.ceil(SLANT*h) if bg else 0
    layer=Image.new('RGBA',(w+lean+offset,h+offset),(0,0,0,0));d=ImageDraw.Draw(layer)
    if bg:
        plate=lambda dx,dy:[(lean+dx,dy),(w+lean-1+dx,dy),(w-1+dx,h-1+dy),(dx,h-1+dy)]
        if shadow:d.polygon(plate(offset,offset),fill=shadow)
        d.polygon(plate(0,0),fill=bg)
    x,y=padx+lean//2-box[0],pady-box[1]
    if outline:d.text((x+offset,y+offset),text,font=f,fill=outline)
    d.text((x,y),text,font=f,fill=fg)
    return layer

def fitted_tag(text,initial,width,minimum=None,**style):
    minimum=minimum or max(18,initial//2)
    for size in range(initial,minimum-1,-4):
        layer=tag(text,font(size),**style)
        if layer.width<=width:return layer
    raise ValueError(f'Cover text "{text}" does not fit at {minimum}px; shorten it in cover.json')

def art_panel(brief,max_w,max_h,border=10):
    """News pictures fill a frame of their own aspect (clamped to 3:4..2:1, centre-cropped beyond);
    logos keep a white square so their artwork has a clean background."""
    from PIL import ImageOps
    path=(ROOT/brief['image']).resolve()
    if '/logos/' in path.as_posix():
        side=min(max_w,max_h)-40;art=cover_art(brief,side-120)
        inner=Image.new('RGBA',(side,side),'white');inner.paste(art,((side-art.width)//2,(side-art.height)//2),art)
    else:
        art=cover_art(brief,4096).convert('RGB')
        ratio=min(max(art.width/art.height,0.75),2.0)
        w=min(max_w-2*border,round((max_h-2*border)*ratio));h=round(w/ratio)
        inner=ImageOps.fit(art,(w,h),Image.Resampling.LANCZOS).convert('RGBA')
    framed=Image.new('RGBA',(inner.width+2*border+6+22,inner.height+2*border+6+22),(0,0,0,0));fd=ImageDraw.Draw(framed)
    W,H=inner.width+2*border+6,inner.height+2*border+6
    fd.rectangle((22,22,W+21,H+21),fill=BLACK);fd.rectangle((0,0,W-1,H-1),fill=BLACK)
    fd.rectangle((3,3,W-4,H-4),fill='white');framed.paste(inner,(3+border,3+border),inner)
    return framed.rotate(3,resample=Image.Resampling.BICUBIC,expand=True)

def persona_canvas(ep,brief,height):
    """Video-matching P3 blue/white cover; 4:3 is laid out natively, not letterboxed."""
    # 2026-11-12 layout (user-approved samples): white band lower, picture top-right beside
    # lines 1-2, line 3 full width under it; sizes medium / small / large; date bottom-right.
    W,H=1920,height;tall=H>1080
    image=Image.new('RGB',(W,H),BLUE);d=ImageDraw.Draw(image)
    run=math.tan(math.radians(25))*H
    for x in range(-int(run),W+60,44):d.polygon([(x+run,0),(x+run+3,0),(x+3,H),(x,H)],fill=LINE)
    edge=lambda x,base:base-80*x/W  # bottom band rises toward the right, like the video header edge
    band=H-(160 if tall else 130)
    d.polygon([(0,edge(0,band)-30),(W,edge(W,band)-30),(W,edge(W,band)-20),(0,edge(0,band)-20)],fill=NAVY)
    d.polygon([(0,edge(0,band)-12),(W,edge(W,band)-12),(W,edge(W,band)),(0,edge(0,band))],fill=BLACK)
    d.polygon([(0,edge(0,band)),(W,edge(W,band)),(W,H),(0,H)],fill='white')
    slot=tag(slot_label(ep),font(54),BLUE,'white',shadow=BLACK,offset=8,padx=26,pady=10)
    top_y=110 if tall else 70
    image.paste(slot,(104,top_y),slot)
    hi=None
    if brief.get('highlight'):
        hi=fitted_tag(brief['highlight'],300 if tall else 230,W-220,HI_MIN,fg=BLUE,bg='white',shadow=BLACK,offset=16,padx=34,pady=14)
        hi_y=int(edge(100+hi.width,band))-60-hi.height
    else:hi_y=int(edge(0,band))-40
    zone_bottom=hi_y-(60 if tall else 36)
    top_style=dict(fg='white',bg=None,outline=BLACK,offset=9)
    main_style=dict(fg='white',bg=BLACK,shadow='white',offset=10,padx=26,pady=14)
    # The picture gives up width when line 1/2 need it at their minimum size; 80 covers the
    # frame border, shadow and tilt. A frame takes the picture's own shape (2026-11-09).
    need=max(tag(brief['headline_top'],font(TOP_MIN),**top_style).width if brief.get('headline_top') else 0,
             tag(brief['headline_main'],font(MAIN_MIN),**main_style).width)
    right=W-70;art_w=max(ART_MIN,min(760,right-104-40-need-80))
    framed=art_panel(brief,art_w,zone_bottom-top_y-20)
    ax=right-framed.width;ay=top_y+(zone_bottom-top_y-framed.height)//2
    image.paste(framed,(ax,ay),framed)
    if brief.get('image_label'):
        label=tag(brief['image_label'],font(40),'white',BLACK,shadow=BLUE,offset=6,padx=22,pady=8)
        image.paste(label,(ax+framed.width-label.width-30,ay+framed.height-40),label)
    col=ax-104-40;rows=[]
    if brief.get('headline_top'):rows.append((fitted_tag(brief['headline_top'],190 if tall else 170,col,TOP_MIN,**top_style),104))
    rows.append((fitted_tag(brief['headline_main'],88 if tall else 76,col,MAIN_MIN,**main_style),96))
    gap=40 if tall else 26;start=top_y+slot.height+(60 if tall else 30)
    y=start+max(0,(zone_bottom-start-sum(r.height for r,_ in rows)-gap*(len(rows)-1))//2)
    for layer,x in rows:image.paste(layer,(x,y),layer);y+=layer.height+gap
    if hi:image.paste(hi,(100,hi_y),hi)
    # The edition date appears exactly once, bottom-right on the white band.
    date=ep['edition_date'][5:].replace('-','.')
    df=display(140 if tall else 120);db=d.textbbox((0,0),date,font=df)
    d.text((W-110-db[2],H-db[3]-(34 if tall else 26)),date,font=df,fill=BLACK)
    footer=cover_footer(brief)
    if footer!=slot_label(ep):
        ff=fitted(d,footer,44,760,False);fb=d.textbbox((0,0),footer,font=ff)
        d.text((110,H-fb[3]-(50 if tall else 40)),footer,font=ff,fill=BLACK)
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
