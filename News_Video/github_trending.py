"""GitHub daily trending: the closing page of the AI edition (2026-11-09).

Picks the AI / LLM / agent / developer-tool repository with the most stars
today, skipping tools that track people, attack systems, defeat payment or
copyright, or are adult/scam content. The README is archived so the
introduction quotes what the project says about itself.

    python -B github_trending.py collect
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,html,json,re
from pathlib import Path
import news_video as n

SOURCE_ID='github-trending'
URL='https://github.com/trending?since=daily'
RELEVANT=re.compile(r'\b(?:ai|llms?|agents?|agentic|gpt|claude|gemini|qwen|deepseek|llama|mistral|models?|rag|mcp|diffusion|transformers?|inference|prompts?|copilot|embeddings?|vector|machine[- ]learning|deep[- ]learning|neural|chatbots?|openai|anthropic|ollama|langchain|coding|developers?|devtools?|cli|sdk|framework|ide|compiler|terminal|database|api)\b|人工智能|大模型|智能体',re.I)
AI=re.compile(r'\b(?:ai|llms?|agents?|agentic|gpt|claude|gemini|qwen|deepseek|llama|mistral|models?|rag|mcp|diffusion|transformers?|inference|prompts?|copilot|embeddings?|machine[- ]learning|deep[- ]learning|neural|chatbots?|openai|anthropic|ollama|langchain)\b|人工智能|大模型|智能体',re.I)
UNSAFE=re.compile(r'\b(?:osint|sherlock|doxx?(?:ing)?|stalk\w*|people[- ]search|username(?:s)? (?:search|lookup|across)|social (?:media|network)s? (?:accounts?|profiles?) (?:by|search)|phone[- ]number (?:lookup|track)|geolocat\w* (?:people|person)|spyware|stalkerware|keylogger|remote access trojan|\brat\b|malware|ransomware|exploits?|ddos|botnet|phishing|credential (?:stuffing|harvest)|password crack\w*|crack(?:ed|ing)?|keygen|paywall bypass|bypass (?:paywall|drm|license)|drm removal|pirac\w*|torrent|warez|nsfw|porn\w*|hentai|nudify|undress|deepfake|face ?swap|scam|cheats?|aimbot|wallhack)\b|人肉|开盒|社工库|盗号|破解版|去水印',re.I)

def parse(page):
    rows=[]
    for block in re.findall(r'<article class="Box-row">(.*?)</article>',page,re.S):
        name=re.search(r'<h2[^>]*>\s*<a[^>]*href="/([^"/]+/[^"/]+)"',block,re.S)
        if not name:continue
        desc=re.search(r'<p class="[^"]*col-9[^"]*">(.*?)</p>',block,re.S)
        language=re.search(r'itemprop="programmingLanguage">([^<]+)<',block)
        today=re.search(r'([\d,]+) stars? today',block)
        total=re.search(r'href="/[^"]+/stargazers"[^>]*>(.*?)</a>',block,re.S)
        number=lambda m:int(re.sub(r'\D','',html.unescape(re.sub(r'<[^>]+>','',m.group(1)))) or 0) if m else None
        rows.append(dict(repo=name.group(1),description=html.unescape(re.sub(r'<[^>]+>','',desc.group(1))).strip() if desc else '',
                         language=language.group(1).strip() if language else None,stars_today=number(today),stars_total=number(total)))
    if not rows:raise ValueError('GitHub trending returned no repositories; source drift, keep the gap')
    return rows

def judge(row,topics=()):
    """(eligible, reason): unsafe tools are skipped before relevance is considered."""
    text=' '.join([row['repo'].replace('/',' ').replace('-',' ').replace('_',' '),row.get('description',''),' '.join(topics)])
    if UNSAFE.search(text):return False,'unsafe_or_harmful_purpose'
    if not RELEVANT.search(text):return False,'not_ai_or_developer_tool'
    return True,'ai' if AI.search(text) else 'developer_tool'

def repository(repo,fetch=None):
    """Public metadata and README; unauthenticated, read-only."""
    fetch=fetch or n.fetch
    body,_,encoding=fetch('https://api.github.com/repos/'+repo)
    meta=json.loads(body.decode(encoding,errors='replace'))
    readme=''
    for name in ['README.md','readme.md','README.rst','README']:
        try:
            body,_,encoding=fetch(f'https://raw.githubusercontent.com/{repo}/HEAD/{name}')
            readme=body.decode(encoding,errors='replace');break
        except Exception:continue
    return dict(license=(meta.get('license') or {}).get('spdx_id'),topics=meta.get('topics') or [],stars_total=meta.get('stargazers_count'),
                homepage=meta.get('homepage'),archived=bool(meta.get('archived')),description=meta.get('description') or '',
                readme=readme[:30000],readme_complete=len(readme)<=30000)

def card(root,repo,fetch=None):
    """GitHub's own social preview card for the repository page."""
    fetch=fetch or n.fetch
    url='https://opengraph.githubassets.com/1/'+repo
    body,final,_=fetch(url)
    from PIL import Image
    import io
    image=Image.open(io.BytesIO(body));image.verify()
    folder=Path(root)/'assets/github';folder.mkdir(parents=True,exist_ok=True)
    dest=folder/(hashlib.sha256(url.encode()).hexdigest()[:20]+'.png')
    Image.open(io.BytesIO(body)).convert('RGB').save(dest)
    return dict(file=dest.relative_to(root).as_posix(),source_url=url)

def collect(root=None,fetch=None,now=None,keep=3):
    root=Path(root or n.ROOT);fetch=fetch or n.fetch;now=now or dt.datetime.now(n.UTC)
    body,final,encoding=fetch(URL)
    rows=parse(body.decode(encoding,errors='replace'))
    ranked=[];skipped=[]
    for row in rows:
        ok,reason=judge(row)
        (ranked if ok else skipped).append(dict(row,reason=reason))
    ranked.sort(key=lambda r:-(r['stars_today'] or 0))
    chosen=[]
    for row in ranked:
        if len(chosen)>=keep:break
        try:meta=repository(row['repo'],fetch)
        except Exception as error:skipped.append(dict(row,reason='metadata_unavailable: '+type(error).__name__));continue
        ok,reason=judge(row,meta['topics'])
        if not ok or meta['archived'] or not meta['readme']:skipped.append(dict(row,reason=reason if not ok else 'archived_or_no_readme'));continue
        row=dict(row,**{k:v for k,v in meta.items() if k!='description'},repo_description=meta['description'],relevance=reason)
        try:row['image']=card(root,row['repo'],fetch)
        except Exception as error:row['image_error']=type(error).__name__
        chosen.append(row)
    db=n.database();items=[]
    try:
        from freshness import time_evidence
        for rank,row in enumerate(chosen,1):
            key=hashlib.sha256(f"{SOURCE_ID}:{now.date().isoformat()}:{row['repo']}".encode()).hexdigest()[:20]
            url='https://github.com/'+row['repo']
            # The trending ranking is a snapshot published when it is read.
            item=dict(id=key,source_id=SOURCE_ID,url=url,published=now.isoformat(),raw_published=now.isoformat(),time_basis='original_publication',
                      title=f"GitHub 今日热门 #{rank}: {row['repo']}",summary=(row['repo_description'] or row['description'])+'\n\n'+row['readme'][:4000],
                      rank=rank,snapshot_url=URL,fetched_at=now.isoformat(),**{k:v for k,v in row.items() if k not in {'readme'}})
            n.dump(root/'data/github-trending/items'/(key+'.json'),dict(item,readme=row['readme']))
            n.dump(root/'data/time-evidence'/(key+'.json'),time_evidence(item))
            db.execute('''INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                last_seen=excluded.last_seen,title=excluded.title,summary=excluded.summary,content_hash=excluded.content_hash''',
                (key,SOURCE_ID,'GitHub','ai',item['title'],url,item['published'],item['summary'],now.isoformat(),now.isoformat(),hashlib.sha256(item['summary'].encode()).hexdigest()))
            db.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?)',(key,SOURCE_ID,now.isoformat()))
            items.append(dict(id=key,repo=row['repo'],stars_today=row['stars_today'],relevance=row['relevance']))
        db.commit()
    finally:db.close()
    report=dict(ok=True,fetched_at=now.isoformat(),candidates=len(rows),chosen=items,skipped=[dict(repo=s['repo'],reason=s['reason']) for s in skipped])
    n.dump(root/'data/github-trending'/(now.date().isoformat()+'.json'),dict(report,rows=rows))
    return report

def record(item_id,root=None):
    path=Path(root or n.ROOT)/'data/github-trending/items'/(str(item_id)+'.json')
    if not path.is_file():raise ValueError('GITHUB_TRENDING_NOT_COLLECTED: '+str(item_id))
    return n.load(path)

def featured(root=None):
    path=Path(root or n.ROOT)/'data/github-trending/featured.jsonl'
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()] if path.is_file() else []

def validate_scene(scene,root=None,now=None,episode_id=None):
    """Closing GitHub page: collected snapshot, safe repo, facts bound to the record, 7-day no-repeat."""
    root=Path(root or n.ROOT);row=record(scene['item_id'],root);now=now or dt.datetime.now(n.UTC)
    if scene.get('scene_type')!='github_trending':raise ValueError('GITHUB_SCENE_TYPE: use scene_type=github_trending')
    ok,reason=judge(row,row.get('topics',[]))
    if not ok:raise ValueError('GITHUB_REPO_INELIGIBLE: '+reason)
    if scene.get('repo')!=row['repo']:raise ValueError('GITHUB_REPO_MISMATCH')
    if scene.get('stars_today')!=row['stars_today']:raise ValueError('GITHUB_STARS_MISMATCH: use the collected stars_today')
    short=row['repo'].split('/')[1]
    narration=scene.get('narration','')
    if short.casefold() not in narration.casefold() or 'GitHub' not in narration:raise ValueError('GITHUB_NARRATION: name the repository and GitHub')
    if not 90<=len(narration)<=280:raise ValueError('GITHUB_NARRATION_LENGTH: about 30-45 seconds (90-280 characters)')
    for item in featured(root):
        if item['repo']==row['repo'] and item['episode']!=episode_id and dt.datetime.fromisoformat(item['at'])>now-dt.timedelta(days=7):
            raise ValueError('GITHUB_REPEATED: '+row['repo']+' was featured within 7 days; use the next candidate')
    from content_rules import check_public_words
    check_public_words(scene.get('title',''),root)
    scene['github_audit']=dict(repo=row['repo'],rank=row['rank'],stars_today=row['stars_today'],license=row.get('license'),snapshot=row['fetched_at'])
    return scene['github_audit']

def bind_media(scene,root=None):
    """Use the repository's GitHub card as the page image (before page-image checks run)."""
    row=record(scene['item_id'],root)
    if not scene.get('image') and row.get('image'):
        scene['image']=row['image']['file'];scene['image_source_url']=row['image']['source_url']
    scene['company']='GitHub';scene.setdefault('logo','assets/logos/github.png')

def record_featured(episode,root=None,now=None):
    rows=[dict(repo=s['github_audit']['repo'],episode=episode['id'],at=(now or dt.datetime.now(n.UTC)).isoformat()) for s in episode['scenes'] if s.get('github_audit')]
    if not rows:return
    path=Path(root or n.ROOT)/'data/github-trending/featured.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as handle:
        for row in rows:handle.write(json.dumps(row,ensure_ascii=False)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['collect'])
    parser.parse_args();print(json.dumps(collect(),ensure_ascii=False,indent=2))
