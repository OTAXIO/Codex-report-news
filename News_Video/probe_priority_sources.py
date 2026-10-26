"""Read public official sources only; no paid API or model calls."""
import concurrent.futures,json
from pathlib import Path
import news_video as n
ROOT=Path(__file__).parent
URLS={'qwen-research':'https://qwen.ai/research','glm-release-notes':'https://docs.z.ai/release-notes/new','qwen-code-releases':'https://github.com/QwenLM/qwen-code/releases.atom','glm-blog':'https://z.ai/blog'}
def probe(pair):
    key,url=pair;out=ROOT/'data/source-probes';out.mkdir(exist_ok=True)
    try:
        body,final,enc=n.fetch(url);(out/(key+'.source')).write_bytes(body)
        if key.endswith('releases'):count=len(n.parse_feed(body,{}));summary=f'{count} Atom entries'
        else:
            page=n.PageText();page.feed(body.decode(enc,errors='replace'));n.dump(out/(key+'.parsed.json'),dict(text=' '.join(page.parts),links=page.links));summary=f'{len(page.links)} links'
        return dict(id=key,url=url,ok=True,bytes=len(body),summary=summary)
    except Exception as e:return dict(id=key,url=url,ok=False,error=str(e))
if __name__=='__main__':
    results=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(probe,URLS.items()));n.dump(ROOT/'data/source-probes/report.json',results);print(json.dumps(results,ensure_ascii=False,indent=2))
