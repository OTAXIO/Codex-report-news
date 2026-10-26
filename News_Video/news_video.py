"""RSS + read-only Agent Reach -> editorial -> local voice -> captioned video.

No model APIs, direct X scraping, uploads, credential discovery or task writes.
"""
from __future__ import annotations
import argparse, concurrent.futures, datetime as dt, email.utils, hashlib
import html, json, os, re, sqlite3, subprocess, sys, time
import urllib.parse, urllib.request, xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UTC = dt.timezone.utc
CN = dt.timezone(dt.timedelta(hours=8))

def dump(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def config():
    cfg = load(ROOT / "config.json")
    if cfg.get("upload_enabled") or cfg.get("auto_publish"):
        raise ValueError("Automatic upload/publish is not configured.")
    if cfg.get("x_enabled") and cfg.get('x_collection',{}).get('mode')!='agent_reach_read_only':
        raise ValueError("X requires the read-only Agent Reach adapter.")
    if cfg.get("social_collection_allow_model_calls"):
        raise ValueError("Hourly social collection must have zero model calls.")
    return cfg

def database():
    path = ROOT / "data/news.sqlite3"; path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY, source_id TEXT, publisher TEXT, kind TEXT,
        title TEXT, url TEXT, published TEXT, summary TEXT,
        first_seen TEXT, last_seen TEXT, content_hash TEXT);
      CREATE TABLE IF NOT EXISTS observations (
        item_id TEXT, source_id TEXT, seen TEXT,
        PRIMARY KEY(item_id, source_id));
      CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY, kind TEXT, started TEXT, finished TEXT, report TEXT);
    ''')
    return db

def text(value):
    value = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", value or "", flags=re.S|re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()

def normalized_url(url, *, allow_x=False):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in {"https", "http"}: raise ValueError("Non-web URL")
    host=(parts.hostname or '').lower()
    if host in {'x.com','twitter.com','www.x.com','www.twitter.com','t.co'}:
        match=re.fullmatch(r'/([A-Za-z0-9_]{1,15})/status/(\d+)/?',parts.path)
        if not allow_x or not match or host=='t.co':
            raise ValueError("X links require the Agent Reach status adapter")
        return 'https://x.com/'+match[1].lower()+'/status/'+match[2]
    query = [(k,v) for k,v in urllib.parse.parse_qsl(parts.query) if not k.startswith("utm_") and k not in {"spm", "ref"}]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, urllib.parse.urlencode(query), ""))

def parse_date(value):
    if not value: return None
    try: result = email.utils.parsedate_to_datetime(value)
    except (ValueError, TypeError):
        try: result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError: return None
    if result.tzinfo is None: result = result.replace(tzinfo=UTC)
    return result.astimezone(UTC).isoformat()

def fetch(url, timeout=22):
    normalized_url(url)
    proxy = system_proxy()
    local_first = "chinanews.com" in url or "people.com.cn" in url
    modes = [False, True] if local_first else [True, False]
    last = None
    for attempt, use_proxy in enumerate(modes):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"NewsVideoLocal/0.1 (+RSS reader)", "Accept-Encoding":"identity"})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http":proxy,"https":proxy})) if use_proxy and proxy else urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=timeout) as response:
                final = normalized_url(response.url)
                body = response.read(4_000_000)
                encoding = response.headers.get_content_charset() or "utf-8"
                return body, final, encoding
        except Exception as error:
            last = error
            if attempt == 0: time.sleep(.5)
    raise RuntimeError(str(last))

def system_proxy():
    """Reuse the configured loopback Windows proxy; never modify global settings."""
    if os.name != "nt": return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            enabled=winreg.QueryValueEx(key,"ProxyEnable")[0]
            address=winreg.QueryValueEx(key,"ProxyServer")[0]
        match=re.search(r"(?:127\.0\.0\.1|localhost):(\d+)",address)
        # Explicit process-local use is also valid when the system proxy toggle
        # is off (for example a TUN setup); do not change that global toggle.
        return "http://127.0.0.1:"+match.group(1) if match else None
    except OSError:return None

def parse_feed(body, source):
    root = ET.fromstring(body)
    ns = "{http://www.w3.org/2005/Atom}"
    rss = root.tag == "rss"
    if not rss and root.tag != ns+"feed": raise ValueError("Not RSS or Atom")
    entries = root.findall("./channel/item") if rss else root.findall(ns+"entry")
    output = []
    for entry in entries:
        if rss:
            title = entry.findtext("title", "")
            link = entry.findtext("link", "")
            date = entry.findtext("pubDate", "")
            summary = entry.findtext("description", "") or entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
        else:
            title = entry.findtext(ns+"title", "")
            links = entry.findall(ns+"link")
            link = next((x.attrib.get("href", "") for x in links if x.attrib.get("rel", "alternate")=="alternate"), "")
            date = entry.findtext(ns+"published", "") or entry.findtext(ns+"updated", "")
            summary = entry.findtext(ns+"summary", "") or entry.findtext(ns+"content", "")
        if not title or not link: continue
        try: link = normalized_url(link)
        except ValueError: continue
        output.append(dict(title=text(title), url=link, published=parse_date(date), summary=text(summary)[:10000]))
    return output

class PageText(HTMLParser):
    def __init__(self): super().__init__(); self.skip=0; self.parts=[]; self.metadata={}; self.links=[]; self.anchor=None
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in {"script", "style", "nav", "footer", "header"}: self.skip+=1
        if tag=="meta": self.metadata[attrs.get("property") or attrs.get("name", "")]=attrs.get("content", "")
        if tag=="a": self.anchor=[attrs.get("href", ""), []]
        if tag in {"p", "h1", "h2", "h3", "li", "article", "time"}: self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "header"}: self.skip=max(0,self.skip-1)
        if tag=="a" and self.anchor:
            self.links.append((self.anchor[0], " ".join(self.anchor[1]).strip())); self.anchor=None
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.anchor: self.anchor[1].append(data)

def official_bridge(body, source, encoding):
    """Explicit local conversion of official page indexes; never called native RSS."""
    page = PageText(); page.feed(body.decode(encoding, errors="replace"))
    entries=[]
    if source['id']=='glm-zcode':
        content=re.sub(r'\s+',' ',' '.join(page.parts))
        matches=list(re.finditer(r'(\d+\.\d+\.\d+) Released ([A-Z][a-z]{2} \d{1,2}, 20\d{2})',content))
        for i,match in enumerate(matches):
            version,date=match.groups();published=dt.datetime.strptime(date,'%b %d, %Y').replace(tzinfo=UTC).isoformat()
            end=matches[i+1].start() if i+1<len(matches) else len(content)
            entries.append(dict(title='ZCode '+version+' 更新',url=source['url'],entry_key=source['id']+':'+version,published=published,summary=content[match.end():end].strip()[:10000]))
        if not entries:raise ValueError('GLM/ZCode page has no dated release entries; preserve coverage gap')
        return entries
    for href, title in page.links:
        url=urllib.parse.urljoin(source["url"], href)
        if source["id"]=="anthropic": eligible="anthropic.com/news/" in url and len(title)>15
        elif source["id"]=="minimax": eligible="minimax.io/news/" in url and len(title)>10
        else: eligible=False
        if eligible:
            date_match = re.search(r"(20\d{2})[-/](\d{2})[-/](\d{2})", title + " " + url)
            published=parse_date("-".join(date_match.groups())) if date_match else None
            entries.append(dict(title=text(title), url=normalized_url(url), published=published, summary=""))
    if source["id"]=="deepseek":
        # Docusaurus anchors are a changelog, not separate fabricated news URLs.
        page_text=" ".join(page.parts)
        chunks=re.split(r"Date:\s*(20\d{2}-\d{2}-\d{2})", page_text)
        for i in range(1,len(chunks)-1,2):
            date, content=chunks[i], re.sub(r"\s+", " ", chunks[i+1]).strip()
            if content:
                entries.append(dict(title="DeepSeek 更新 "+date, url=source["url"]+"?edition="+date, published=parse_date(date),summary=content[:8000]))
    if not entries: raise ValueError("Official page has no extractable dated news entries; source gap preserved")
    return entries

def collect(kind):
    config(); now=dt.datetime.now(UTC); run_id=now.strftime("%Y%m%dT%H%M%S")+"_"+kind
    sources=[s for s in load(ROOT/"sources.json") if kind=="all" or s["group"]==kind]
    directory=ROOT/"data/collections"/run_id; directory.mkdir(parents=True,exist_ok=True)
    def one(source):
        result=dict(source_id=source["id"],source_type=source["type"],model_calls=0)
        try:
            body,final,encoding=fetch(source["url"])
            (directory/(source["id"]+".source")).write_bytes(body)
            entries=parse_feed(body,source) if source["type"]=="rss" else official_bridge(body,source,encoding)
            result.update(ok=True, final_url=final, items=entries, count=len(entries))
            if source["type"]=="official_page":
                rss=ET.Element("rss",version="2.0"); channel=ET.SubElement(rss,"channel")
                ET.SubElement(channel,"title").text=source["name"]+" — local converted feed"
                for item in entries:
                    node=ET.SubElement(channel,"item")
                    for key,tag in [("title","title"),("url","link"),("summary","description")]: ET.SubElement(node,tag).text=item[key]
                    if item.get('entry_key'):ET.SubElement(node,'guid',isPermaLink='false').text=item['entry_key']
                    if item["published"]: ET.SubElement(node,"pubDate").text=email.utils.format_datetime(dt.datetime.fromisoformat(item["published"]))
                ET.ElementTree(rss).write(directory/(source["id"]+".converted.xml"),encoding="utf-8",xml_declaration=True)
        except Exception as error: result.update(ok=False,error=str(error),items=[])
        return source,result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(one,sources))
    db=database(); reports=[]; new=0
    for source,result in results:
        for item in result.pop("items"):
            key=hashlib.sha256(item.get('entry_key',item["url"]).encode()).hexdigest()[:20]
            existed=db.execute("SELECT id FROM items WHERE id=?",(key,)).fetchone()
            new+=int(not existed)
            db.execute('''INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,
              title=excluded.title,summary=excluded.summary,content_hash=excluded.content_hash,
              published=COALESCE(excluded.published,items.published)''',
              (key,source["id"],source["publisher"],source["group"],item["title"],item["url"],item["published"],item["summary"],now.isoformat(),now.isoformat(),hashlib.sha256((item["title"]+item["summary"]).encode()).hexdigest()))
            db.execute("INSERT OR REPLACE INTO observations VALUES(?,?,?)",(key,source["id"],now.isoformat()))
        reports.append(result)
    report=dict(id=run_id,started=now.isoformat(),finished=dt.datetime.now(UTC).isoformat(),kind=kind,model_calls=0,new_items=new,sources=reports)
    db.execute("INSERT INTO runs VALUES(?,?,?,?,?)",(run_id,kind,report["started"],report["finished"],json.dumps(report,ensure_ascii=False))); db.commit();db.close()
    dump(directory/"report.json",report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def candidates(hours=48):
    cutoff=(dt.datetime.now(UTC)-dt.timedelta(hours=hours)).isoformat()
    db=database()
    rows=[dict(row) for row in db.execute("SELECT * FROM items WHERE published>=? ORDER BY kind,published DESC",(cutoff,))]
    sources={s['id']:s for s in load(ROOT/'sources.json')}
    if config().get('x_enabled'):
        from leader_sources import registry
        sources.update({s['id']:s for s in registry() if s.get('enabled')})
    preferred=config().get('editorial',{}).get('preferred_vendors',[])
    for item in rows:
        item["observed_sources"]=[r[0] for r in db.execute("SELECT source_id FROM observations WHERE item_id=?",(item["id"],))]
        source=sources.get(item['source_id'],{})
        if source.get('type')=='official_page' and item['url']==source.get('url'):
            item['event_key']=item['source_id']+':'+item['title']
        item['priority_tier']=source.get('priority_tier',2)
        item['selection_policy']=source.get('selection_policy','standard')
        vendor=source.get('vendor',item['publisher'])
        item['preferred_vendor_order']=preferred.index(vendor) if vendor in preferred else len(preferred)
        item['source_priority']=source.get('source_priority',100)
        if source.get('type')=='leader_x':
            evidence=load(ROOT/'data/leader-posts'/(item['id']+'.json'))
            item.update(source_type='leader_x',company=vendor,author=source['name'],handle=source['handle'],
                        attribution=evidence['attribution'],requires_context=evidence['requires_context'],
                        evidence_path='data/leader-posts/'+item['id']+'.json')
    rows.sort(key=candidate_order)
    db.close()
    from used_news import recent_records,exclude_used
    rows,excluded,used_context=exclude_used(rows,recent_records(ROOT,days=max(2,(hours+23)//24+1)))
    payload=dict(producer="RSS + Agent Reach collector; no model calls",cutoff_utc=cutoff,generated_at=dt.datetime.now(UTC).isoformat(),items=rows,
        excluded_used_news=excluded,previously_used_news=used_context,
        dedup_policy='Exclude completed exports by item ID, canonical URL, event key or normalized source title; compare previously_used_news before selecting rewritten reports of the same event.')
    dump(ROOT/"data/candidates.json",payload)
    for item in rows: print(json.dumps({k:item[k] for k in ["id","kind","publisher","published","title","url","summary"]},ensure_ascii=False))

def candidate_order(item):
    # Within a company, executives precede official feeds; Tibo is first at OpenAI.
    ai=item['kind']=='ai'
    return (0 if ai else 1,item.get('priority_tier',2) if ai else 0,
            item.get('preferred_vendor_order',99) if ai else 0,
            item.get('source_priority',100) if ai else 0,
            -dt.datetime.fromisoformat(item['published']).timestamp())

def article(item_id):
    db=database(); row=db.execute("SELECT * FROM items WHERE id=?",(item_id,)).fetchone();db.close()
    if not row: raise ValueError("Unknown candidate")
    row=dict(row)
    if row['source_id'].startswith('x-leader-'):
        evidence=load(ROOT/'data/leader-posts'/(item_id+'.json'))
        print(json.dumps(evidence,ensure_ascii=False,indent=2));return
    body,final,encoding=fetch(row["url"])
    page=PageText(); page.feed(body.decode(encoding,errors="replace"))
    content=re.sub(r"[ \t]+"," "," ".join(page.parts))
    data=dict(item_id=item_id,title=row["title"],url=final,metadata=page.metadata,text=content[:60000],fetched_at=dt.datetime.now(UTC).isoformat())
    dump(ROOT/"data/articles"/(item_id+".json"),data)
    print(json.dumps(data,ensure_ascii=False,indent=2))

def import_editorial(path):
    cfg=config(); episode=load(path)
    if episode.get('edition_slot')=='temporary':
        from reset_alerts import validate_temporary
        validate_temporary(episode)
    if episode.get('producer') not in cfg.get('editorial',{}).get('allowed_producers',['Codex current conversation','DeepSeek Harness','manual editor']):raise ValueError('Producer must be disclosed using an allowed producer name')
    db=database(); selected=[];selected_rows=[]
    for scene in episode["scenes"]:
        if scene.get("item_id"):
            row=db.execute("SELECT * FROM items WHERE id=?",(scene["item_id"],)).fetchone()
            if not row: raise ValueError("Editorial refers to unknown collected candidate")
            row=dict(row)
            if scene.get("source_url") != row["url"]: raise ValueError("Source URL does not match collected candidate")
            if not scene.get("evidence") or not scene.get("selection_reason"): raise ValueError("Missing evidence/ranking reason")
            if row['source_id'].startswith('x-leader-'):
                from leader_sources import validate_scene
                validate_scene(scene,load(ROOT/'data/leader-posts'/(scene['item_id']+'.json')))
            selected.append(scene["item_id"])
            selected_rows.append(dict(row,**({'event_key':scene['event_key']} if scene.get('event_key') else {})))
    if len(set(selected))!=len(selected): raise ValueError("Duplicate event selection")
    db.close()
    from used_news import recent_records,exclude_used
    edition_key=episode.get('edition_key',re.sub(r'-v\d+$','',episode['id']))
    _,already_used,_=exclude_used(selected_rows,[r for r in recent_records(ROOT) if r['edition_key']!=edition_key])
    if already_used:raise ValueError('News already used in another completed edition: '+', '.join(x['id'] for x in already_used))
    episode["publication_preset"]=cfg["publication_preset"]
    episode["upload_enabled"]=False; episode["auto_publish"]=False
    directory=ROOT/"episodes"/episode["id"]; directory.mkdir(parents=True,exist_ok=True)
    if (directory/'release.json').exists():raise ValueError('Published edition is archived; create a new revision ID')
    dump(directory/"episode.json",episode)
    (directory/"script.txt").write_text("\n".join(s["narration"] for s in episode["scenes"]),encoding="utf-8")
    print(directory)

def voice(episode_id):
    cfg=config(); directory=ROOT/"episodes"/episode_id
    if (directory/'release.json').exists():raise ValueError('Published edition is archived; create a new revision ID')
    episode=load(directory/'episode.json')
    v=cfg["voice"]; profile=load(v["profile"])
    from pronunciation import spoken_text
    display_script=(directory/'script.txt').read_text(encoding='utf-8')
    spoken_path=directory/'spoken_script.txt'
    spoken_path.write_text(spoken_text(display_script,v.get('pronunciations',{})),encoding='utf-8')
    job=dict(project=v["engine"],gpt=profile["model"]["t2s_weights_path"],sovits=profile["model"]["vits_weights_path"],reference=v.get("reference_audio",profile["request"]["ref_audio_path"]),reference_text=v.get("reference_text",profile["request"]["prompt_text"]),reference_language="all_zh",text_file=str(directory/"script.txt"),output_file=str(directory/"narration.wav"),language=v["language"],speed=v["speed"],pause=v["pause"],cleanup=v["cleanup"],seed=42,temperature=.75)
    dump(directory/"voice_job.json",job)
    job['text_file']=str(spoken_path)
    dump(directory/'voice_job.json',job)
    executable=Path(v["engine"])/"runtime/python.exe"
    worker=Path(v["repository"])/"tools/generate_job.py"
    env=os.environ.copy();env.update(PYTHONIOENCODING="utf-8",PYTHONUTF8="1",PYTHONDONTWRITEBYTECODE="1")
    # Workspace-owned lock; never terminate another voice/desktop process.
    lock=ROOT/"data/voice.lock"
    with lock.open("x",encoding="utf-8") as handle: handle.write(str(os.getpid()))
    try:
        with (directory/"voice.log").open("w",encoding="utf-8") as log:
            result=subprocess.run([str(executable),"-u","-B",str(worker),"--job",str(directory/"voice_job.json")],cwd=v["engine"],env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode: raise RuntimeError("Voice failed; inspect "+str(directory/"voice.log"))
    finally: lock.unlink(missing_ok=True)
    if v.get("tail_style")=="crisp":
        with (directory/"crisp.log").open("w",encoding="utf-8") as log:
            processed=subprocess.run([str(executable),str(ROOT/"crisp_tails.py"),episode_id,episode_id],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if processed.returncode:raise RuntimeError("Crisp release processing failed; inspect "+str(directory/"crisp.log"))
    elif v.get("soft_release"):
        from voice_tuning import soften_file
        soften_file(directory/"narration.wav",directory/"narration.json")
    from scene_pauses import apply_scene_holds
    meta=load(directory/'narration.json')
    display_sentences=[part.strip() for part in re.split(r'(?<=[。！？!?])\s*|(?<=\.)\s+|\n+',display_script) if part.strip()]
    if len(display_sentences)!=len(meta['sentences']):raise ValueError('Pronunciation rules changed sentence boundaries')
    for entry,display in zip(meta['sentences'],display_sentences):
        entry['spoken_sentence']=entry['sentence'];entry['sentence']=display
    meta=apply_scene_holds(directory/'narration.wav',meta,episode,v['pause'])
    dump(directory/'narration.json',meta)
    rate=meta["sample_rate"]; current=0; sentences=[]
    for index,entry in enumerate(meta["sentences"]):
        duration=entry["processed_samples"]/rate
        sentences.append(dict(text=entry["sentence"],start=current,end=current+duration,cleanup=entry["mode"]))
        current+=duration+(entry.get('pause_after_samples',round(v['pause']*rate))/rate if index+1<len(meta["sentences"]) else 0)
    expected=[]
    for scene in episode["scenes"]:
        expected.extend([scene["id"]]*len([p for p in re.split(r"(?<=[。！？!?])\s*|(?<=\.)\s+|\n+",scene["narration"]) if p.strip()]))
    if len(expected)!=len(sentences): raise RuntimeError("Voice sentence/scene mapping mismatch")
    for sentence,scene_id in zip(sentences,expected): sentence["scene_id"]=scene_id
    dump(directory/"timings.json",dict(sample_rate=rate,duration=meta["seconds"],sentences=sentences))
    print(json.dumps(dict(duration=meta["seconds"],sentences=len(sentences),cleanup=job["cleanup"]),ensure_ascii=False))

def doctor():
    cfg=config();v=cfg["voice"]
    checks={"voice_worker":(Path(v["repository"])/"tools/generate_job.py").is_file(),"voice_python":(Path(v["engine"])/"runtime/python.exe").is_file(),"voice_profile":Path(v["profile"]).is_file(),"upload_disabled":not cfg["upload_enabled"],"hourly_model_calls_disabled":not cfg["social_collection_allow_model_calls"]}
    print(json.dumps(checks,ensure_ascii=False,indent=2)); return all(checks.values())

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="cmd",required=True)
    sub.add_parser("doctor")
    p=sub.add_parser("collect");p.add_argument("--kind",choices=["social","ai","all"],required=True)
    p=sub.add_parser("candidates");p.add_argument("--hours",type=int,default=48)
    p=sub.add_parser("article");p.add_argument("id")
    p=sub.add_parser("import-editorial");p.add_argument("path")
    p=sub.add_parser("voice");p.add_argument("episode")
    args=parser.parse_args()
    if args.cmd=="doctor": return 0 if doctor() else 1
    if args.cmd=="collect":collect(args.kind)
    elif args.cmd=="candidates":candidates(args.hours)
    elif args.cmd=="article":article(args.id)
    elif args.cmd=="import-editorial":import_editorial(args.path)
    elif args.cmd=="voice":voice(args.episode)
    return 0

if __name__=="__main__":raise SystemExit(main())
