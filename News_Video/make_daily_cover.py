"""Original typographic cover using verified, unchanged organization logos."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent
OUT=ROOT/'episodes/daily-20261026-evening'
BLUE='#01A1FE'; BLACK='#101218'

def font(size,bold=True):
    return ImageFont.truetype('C:/Windows/Fonts/'+('msyhbd.ttc' if bold else 'msyh.ttc'),size)

def make(height,name):
    image=Image.new('RGB',(1920,height),'white');d=ImageDraw.Draw(image)
    d.polygon([(1840,0),(1920,0),(1920,height),(1770,height)],fill=BLUE)
    d.polygon([(1880,0),(1920,0),(1920,180),(1860,120)],fill=BLACK)
    d.rectangle((112,100,124,162),fill=BLUE)
    d.text((156,90),'晚间新闻',font=font(64),fill=BLACK)
    d.text((116,250),'OpenAI 官方报告',font=font(120),fill=BLACK)
    d.text((116,420),'存储读取提升',font=font(116),fill=BLACK)
    d.text((110,560),'12 倍',font=font(230),fill=BLUE)
    d.text((124,843),'存储系统指标 · 非模型回答速度',font=font(39,False),fill=BLACK)
    d.text((124,height-185),'10.26',font=font(89),fill=BLACK)
    d.text((434,height-151),'本期焦点 · 近期工程进展',font=font(38,False),fill=BLACK)
    d.line((124,height-65,1670,height-65),fill=BLUE,width=12)
    for key,y,label in [('openai',340,'OpenAI')]:
        im=Image.open(ROOT/f'assets/logos/{key}.png').convert('RGBA')
        im=im.resize((480,480),Image.Resampling.LANCZOS)
        x=1240
        image.paste(im,(x,y),im)
        box=d.textbbox((0,0),label,font=font(36));w=box[2]-box[0]
        d.text((1480-w/2,y+495),label,font=font(36),fill=BLACK)
    image.save(OUT/(name+'.png'))
    return image

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    cover=make(1200,'cover-16x10')
    cover.resize((1146,717),Image.Resampling.LANCZOS).save(OUT/'cover-bilibili.jpg',quality=96,subsampling=0)
    make(1080,'cover-16x9')
    print(OUT/'cover-bilibili.jpg')
