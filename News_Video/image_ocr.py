"""Read text out of official image-only posts (e.g. Skland infographics) with local Windows OCR.

Some official Skland announcements are long images with no text body, so a
capture cannot mark them complete and the news was being dropped. This tool
downloads nothing new: it slices the official images already saved by the
capture import, OCRs them locally, and stores the text as the article body
with text_source=image_ocr. OCR can misread digits and names, so the producer
must check every fact used against the image itself before writing it.
"""
import argparse,datetime as dt,hashlib,json,re,subprocess,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SLICE=1600  # WinRT OCR rejects very tall images; slice long infographics.


def clean(line):
    # WinRT inserts spaces between CJK characters; keep spaces only between Latin words.
    line=re.sub(r'(?<=[　-鿿＀-￯])\s+(?=[　-鿿＀-￯0-9])','',line)
    line=re.sub(r'(?<=[0-9])\s+(?=[　-鿿＀-￯])','',line)
    return line.strip()


def is_prose(line):
    """Explanatory sentences survive; UI fragments inside screenshots do not."""
    cjk=len(re.findall(r'[一-鿿]',line))
    return cjk>=8 and cjk/len(line.replace(' ',''))>=0.6


def ocr_files(paths):
    process=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'image_ocr.ps1'),*map(str,paths)],
                           capture_output=True,text=True,encoding='utf-8',timeout=600)
    if process.returncode:raise RuntimeError('Windows OCR failed: '+process.stderr.strip()[-400:])
    files=json.loads(process.stdout)['files']
    files=files if isinstance(files,list) else [files]
    return [[clean(x) for x in (f.get('lines') or []) if clean(x)] for f in files]


def image_text(path):
    from PIL import Image
    image=Image.open(path).convert('RGB')
    with tempfile.TemporaryDirectory() as tmp:
        parts=[]
        for index,top in enumerate(range(0,image.height,SLICE)):
            piece=image.crop((0,top,image.width,min(image.height,top+SLICE)))
            if piece.width>2400:piece=piece.resize((2400,round(piece.height*2400/piece.width)))
            target=Path(tmp)/f'{index}.png';piece.save(target);parts.append(target)
        return [line for lines in ocr_files(parts) for line in lines]


def ocr_article(item_id,root=ROOT):
    """Fill an image-only official article body from its saved official images."""
    import news_video as n
    from game_sources import article as game_article
    root=Path(root);cached=root/'data/articles'/(item_id+'.json')
    game_path=root/'data/game-items'/(item_id+'.json')
    if not game_path.is_file():raise ValueError('Unknown game item; import the Skland capture first')
    record=n.load(cached) if cached.is_file() else dict(n.load(game_path),item_id=item_id)
    if record.get('body_complete') and record.get('text_source')!='image_ocr':
        return dict(item_id=item_id,skipped='text body already complete')
    if not record.get('related_images'):record=game_article(root,item_id,record,'')
    images=[root/x['file'] for x in record.get('related_images',[]) if x.get('file')]
    if not images:raise ValueError('No saved official image to read for '+item_id)
    raw=[];prose=[]
    for path in images:
        lines=image_text(path)
        if lines:raw.append('\n'.join(lines))
        prose+=[x for x in lines if is_prose(x)]
    text='\n'.join(prose).strip()
    if len(text)<40:raise ValueError('OCR found too little readable text; treat as a source gap')
    record.update(text=record.get('title','')+'\n'+text,official_body=raw,body_complete=True,text_source='image_ocr',
                  ocr=dict(engine='Windows.Media.Ocr zh-Hans-CN',images=[str(p.relative_to(root).as_posix()) for p in images],
                           text_sha256=hashlib.sha256(text.encode()).hexdigest(),at=dt.datetime.now(dt.timezone.utc).isoformat(),
                           warning='OCR text: verify every number, date and name against the image before use'))
    n.dump(cached,record)
    return dict(item_id=item_id,images=len(images),chars=len(text),file='data/articles/'+item_id+'.json')


def item_key(value):
    """Accept the candidate item_id or the numeric Skland article id."""
    value=str(value).strip()
    if value.isdigit():return hashlib.sha256(('https://www.skland.com/article?id='+value).encode()).hexdigest()[:20]
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('item_ids',nargs='+')
    for item in p.parse_args().item_ids:print(json.dumps(ocr_article(item_key(item)),ensure_ascii=False))
