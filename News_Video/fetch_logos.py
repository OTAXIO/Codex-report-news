import concurrent.futures,datetime,hashlib,io,json
from pathlib import Path
from PIL import Image
import news_video as n
ROOT=Path(__file__).parent
specs=[('openai','openai',14957082),('anthropic','anthropics',76263028),('ai2','allenai',5667695)]
def one(spec):
    name,org,ident=spec;url=f'https://avatars.githubusercontent.com/u/{ident}?s=512&v=4'
    body,final,_=n.fetch(url);im=Image.open(io.BytesIO(body));im.verify();im=Image.open(io.BytesIO(body))
    target=ROOT/'assets/logos'/(name+'.png');target.parent.mkdir(parents=True,exist_ok=True)
    im.save(target)
    return dict(id=name,path=target.as_posix(),source=url,organization='https://github.com/'+org,width=im.width,height=im.height,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),usage='Organization identity in a locally reviewed news sample; no implied endorsement')
if __name__=='__main__':
    rows=list(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(one,specs))
    n.dump(ROOT/'assets/logos/sources.json',dict(retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),assets=rows))
    print(json.dumps(rows,ensure_ascii=False,indent=2))
