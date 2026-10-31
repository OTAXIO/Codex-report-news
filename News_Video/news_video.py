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
    if cfg.get('upload_enabled') or cfg.get('auto_publish'):
        publisher=cfg.get('publisher',{})
        if not publisher.get('enabled') or publisher.get('backend')!='codex-upload' or not publisher.get('user_authorized'):
            raise ValueError('Automatic upload requires the configured, user-authorized codex-upload backend')
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
            date = entry.findtext(ns+"published", "")
            summary = entry.findtext(ns+"summary", "") or entry.findtext(ns+"content", "")
        if not title or not link: continue
        try: link = normalized_url(link)
        except ValueError: continue
        images=[urllib.parse.urljoin(link,u) for u in re.findall(r'<img[^>]+src=[\"\x27]([^\"\x27]+)',summary,re.I)]
        images += [node.attrib.get('url') for node in entry.iter() if node.tag.split('}')[-1] in {'content','thumbnail','enclosure'} and node.attrib.get('url') and ('image' in node.attrib.get('type','image'))]
        output.append(dict(title=text(title), url=link, published=parse_date(date), raw_published=date,
                           time_basis='original_publication',summary=text(summary)[:10000],images=list(dict.fromkeys(images))))
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
    if source['id']=='workbuddy-changelog':
        markup=body.decode(encoding,errors='replace')
        headings=list(re.finditer(r'<h2\b[^>]*>(.*?)</h2>',markup,re.S))
        for i,heading in enumerate(headings):
            title=text(heading.group(1)).replace('\u200b','').strip()
            date=re.search(r'(20\d{2}-\d{2}-\d{2})',title)
            version=re.search(r'\b(\d+\.\d+\.\d+)\b',title)
            if not date or not version:continue
            end=headings[i+1].start() if i+1<len(headings) else len(markup)
            entries.append(dict(title='WorkBuddy '+title,url=source['url'],entry_key='workbuddy:'+version.group(1)+':'+date.group(1),published=parse_date(date.group(1)),raw_published=date.group(1),published_precision='date',summary=text(markup[heading.end():end])[:10000]))
        if not entries:raise ValueError('WorkBuddy changelog has no dated version headings; preserve source gap')
        return list({item['entry_key']:item for item in entries}.values())
    if source['id']=='kimi-blog':
        markup=body.decode(encoding,errors='replace')
        for card in re.findall(r'<div\b[^>]*class="[^"]*card-body[^"]*"[^>]*>(.*?)</div>',markup,re.S):
            title=re.search(r'<h[1-6]\b[^>]*>(.*?)</h[1-6]>',card,re.S)
            date=re.search(r'>(20\d{2}-\d{2}-\d{2})<',card)
            if not title or not date:continue
            # Card link precedes its body; bind using the source HTML position.
            before=markup[:markup.find(card)]
            links=re.findall(r'href="([^"]*/blog/[^"]+)"',before)
            if not links:continue
            url=normalized_url(urllib.parse.urljoin(source['url'],links[-1]))
            if urllib.parse.urlsplit(url).hostname!='www.kimi.com':continue
            entries.append(dict(title=text(title.group(1)),url=url,published=parse_date(date.group(1)),raw_published=date.group(1),summary='',published_precision='date'))
        if not entries:raise ValueError('Kimi blog has no dated article cards; preserve source gap')
        return list({item['url']:item for item in entries}.values())
    if source['id']=='glm-zcode':
        content=re.sub(r'\s+',' ',' '.join(page.parts))
        matches=list(re.finditer(r'(\d+\.\d+\.\d+) Released ([A-Z][a-z]{2} \d{1,2}, 20\d{2})',content))
        for i,match in enumerate(matches):
            version,date=match.groups();published=dt.datetime.strptime(date,'%b %d, %Y').replace(tzinfo=UTC).isoformat()
            end=matches[i+1].start() if i+1<len(matches) else len(content)
            entries.append(dict(title='ZCode '+version+' 更新',url=source['url'],entry_key=source['id']+':'+version,published=published,raw_published=date,published_precision='date',summary=content[match.end():end].strip()[:10000]))
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
            entries.append(dict(title=text(title), url=normalized_url(url), published=published, raw_published="-".join(date_match.groups()) if date_match else None,published_precision="date", summary=""))
    if source["id"]=="deepseek":
        # Docusaurus anchors are a changelog, not separate fabricated news URLs.
        page_text=" ".join(page.parts)
        chunks=re.split(r"Date:\s*(20\d{2}-\d{2}-\d{2})", page_text)
        for i in range(1,len(chunks)-1,2):
            date, content=chunks[i], re.sub(r"\s+", " ", chunks[i+1]).strip()
            if content:
                entries.append(dict(title="DeepSeek 更新 "+date, url=source["url"]+"?edition="+date, published=parse_date(date),raw_published=date,published_precision="date",summary=content[:8000]))
    if not entries: raise ValueError("Official page has no extractable dated news entries; source gap preserved")
    return entries

def collect(kind):
    config(); now=dt.datetime.now(UTC); run_id=now.strftime("%Y%m%dT%H%M%S")+"_"+kind
    sources=[s for s in load(ROOT/"sources.json") if s.get("enabled",True) and (kind!="all" or s["group"] in config().get("main_content_groups",["ai","social"])) and (kind=="all" or s["group"]==kind)]
    directory=ROOT/"data/collections"/run_id; directory.mkdir(parents=True,exist_ok=True)
    def one(source):
        result=dict(source_id=source["id"],source_type=source["type"],model_calls=0)
        try:
            if source['type']=='skland_browser':
                from skland_sources import BrowserReader
                with BrowserReader(ROOT) as browser:entries,details=browser.collect(source)
                final=source['url'];result['browser']=details
            else:
                body,final,encoding=fetch(source["url"])
                (directory/(source["id"]+".source")).write_bytes(body)
            if source['type']=='skland_browser':pass
            elif source["type"]=="official_game_page":
                from game_sources import parse,decode
                entries=parse(decode(body,encoding),source)
            else:entries=parse_feed(body,source) if source["type"]=="rss" else official_bridge(body,source,encoding)
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(one,[s for s in sources if s['type']!='skland_browser']))
    # One browser task at a time; stop failures per source, never rotate identity.
    browser_error=None
    for source in sources:
        if source['type']=='skland_browser':
            if browser_error:results.append((source,dict(source_id=source['id'],source_type=source['type'],model_calls=0,ok=False,error=browser_error,items=[],stopped=True)))
            else:
                pair=one(source);results.append(pair)
                if not pair[1].get('ok'):browser_error=pair[1]['error']
    db=database(); reports=[]; new=0
    for source,result in results:
        for item in result.pop("items"):
            key=hashlib.sha256(item.get('entry_key',item["url"]).encode()).hexdigest()[:20]
            from freshness import time_evidence
            evidence_path=ROOT/'data/time-evidence'/(key+'.json')
            evidence=time_evidence(item,source)
            # A refreshed feed must not make an existing URL younger.
            if evidence_path.is_file():
                previous=load(evidence_path)
                from freshness import stamp
                try:
                    old_stamp=stamp(previous['original_published_at'])
                    if not evidence.get('original_published_at') or old_stamp<=stamp(evidence['original_published_at']):evidence=previous
                except (ValueError,TypeError,KeyError):pass
            dump(evidence_path,evidence)
            if source["group"]=="games":
                from game_sources import archive
                archive(ROOT,key,item,source)
            existed=db.execute("SELECT id FROM items WHERE id=?",(key,)).fetchone()
            new+=int(not existed)
            db.execute('''INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,
              title=excluded.title,summary=excluded.summary,content_hash=excluded.content_hash,
              published=COALESCE(excluded.published,items.published)''',
              (key,source["id"],source["publisher"],source["group"],item["title"],item["url"],item["published"],item["summary"],now.isoformat(),now.isoformat(),hashlib.sha256((item["title"]+item["summary"]).encode()).hexdigest()))
            db.execute("INSERT OR REPLACE INTO observations VALUES(?,?,?)",(key,source["id"],now.isoformat()))
        reports.append(result)
    gaps=[dict(source_id=s['id'],status='disabled_source_gap',reason=s['disabled_reason']) for s in load(ROOT/'sources.json')
          if not s.get('enabled',True) and s.get('disabled_reason') and (kind=='all' or s['group']==kind)]
    report=dict(id=run_id,started=now.isoformat(),finished=dt.datetime.now(UTC).isoformat(),kind=kind,model_calls=0,new_items=new,sources=reports,source_gaps=gaps)
    db.execute("INSERT INTO runs VALUES(?,?,?,?,?)",(run_id,kind,report["started"],report["finished"],json.dumps(report,ensure_ascii=False))); db.commit();db.close()
    if kind in {'ai','games','all'} and config().get('x_enabled'):
        from leader_sources import collect as collect_x
        report['x']=collect_x(scope='games' if kind=='games' else 'ai' if kind=='ai' else None)
    dump(directory/"report.json",report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report

def candidates(hours=48,compact=False,limit=12,cursor=0):
    if limit<1 or limit>50 or cursor<0:raise ValueError('Use limit 1-50 and a nonnegative cursor')
    if not 0<hours<=48:raise ValueError('Formal candidates require a window of 1-48 hours')
    snapshot=ROOT/'data/candidates.json'
    if cursor:
        if not snapshot.is_file():raise ValueError('Start candidate pagination with cursor 0')
        payload=load(snapshot)
        if payload.get('hours')!=hours:raise ValueError('Candidate window changed; restart cursor 0')
        rows=payload['items'];selected=rows[cursor:cursor+limit]
        if compact:
            print(json.dumps(dict(total=len(rows),cursor=cursor,next_cursor=cursor+len(selected) if cursor+len(selected)<len(rows) else None,
                                  items=[{k:v for k,v in item.items() if k not in {'summary','content_hash'}} for item in selected],
                                  reference_time=payload['generated_at'],game_coverage=payload['game_coverage'],full_file='data/candidates.json'),ensure_ascii=False));return
        for item in selected:print(json.dumps(item,ensure_ascii=False))
        return
    reference=dt.datetime.now(UTC)
    cutoff=(reference-dt.timedelta(hours=hours)).isoformat()
    db=database()
    rows=[dict(row) for row in db.execute("SELECT * FROM items WHERE published IS NOT NULL ORDER BY kind,published DESC")]
    from freshness import check,evidence_for,time_evidence
    rejected=[];fresh=[]
    for row in rows:
        try:evidence=evidence_for(ROOT,dict(item_id=row['id']))
        except ValueError:
            # Existing records retain their collected timestamp; date precision
            # is refined below from the source registry before acceptance.
            source=next((s for s in load(ROOT/'sources.json') if s['id']==row['source_id']),{})
            evidence=time_evidence(row,source)
        result=check(evidence,reference,hours)
        if result['ok']:fresh.append(row)
        else:rejected.append(dict(item_id=row['id'],reason=result['reason']))
    rows=fresh
    sources={s['id']:s for s in load(ROOT/'sources.json')}
    if config().get('x_enabled'):
        from leader_sources import registry
        sources.update({s['id']:s for s in registry() if s.get('enabled')})
    preferred=config().get('editorial',{}).get('preferred_vendors',[])
    rows=[row for row in rows if row["kind"] in config().get("main_content_groups",["ai","social"])]
    for item in rows:
        game_path=ROOT/"data/game-items"/(item["id"]+".json")
        if game_path.exists():
            game=load(game_path);item.update({k:game[k] for k in ["game","game_region","game_topic","images","source_type"] if k in game})
        item["observed_sources"]=[r[0] for r in db.execute("SELECT source_id FROM observations WHERE item_id=?",(item["id"],))]
        source=sources.get(item['source_id'],{})
        if source.get('type')=='official_page' and item['url']==source.get('url'):
            item['event_key']=item['source_id']+':'+item['title']
        item['priority_tier']=source.get('priority_tier',2)
        item['selection_policy']=source.get('selection_policy','standard')
        from editorial_policy import region_of
        item['region']=region_of(item,sources,config().get('editorial',{}))
        if source.get('published_precision')=='date' or source.get('id')=='kimi-blog':item['published_precision']='date'
        if source.get('product'):item['product']=source['product']
        if source.get('product_scope'):item['source_products']=source['product_scope']
        vendor=source.get('vendor',item['publisher'])
        item['preferred_vendor_order']=preferred.index(vendor) if vendor in preferred else len(preferred)
        item['source_priority']=source.get('source_priority',100)
        if source.get('type') in {'leader_x','official_x'}:
            evidence=load(ROOT/'data/leader-posts'/(item['id']+'.json'))
            item.update(source_type=source['type'],company=vendor,author=source['name'],handle=source['handle'],
                        attribution=evidence['attribution'],requires_context=evidence['requires_context'],
                        evidence_path='data/leader-posts/'+item['id']+'.json')
    from leader_editorial import review_candidates
    review_candidates(rows,ROOT)
    rows.sort(key=candidate_order)
    db.close()
    from used_news import recent_records,exclude_used
    rows,excluded,used_context=exclude_used(rows,recent_records(ROOT,days=max(2,(hours+23)//24+1)))
    payload=dict(producer="RSS + Agent Reach collector; no model calls",cutoff_utc=cutoff,generated_at=reference.isoformat(),hours=hours,excluded_stale=rejected,items=rows,
        excluded_used_news=excluded,previously_used_news=used_context,
        dedup_policy='Exclude completed exports by item ID, canonical URL, event key or normalized source title; compare previously_used_news before selecting rewritten reports of the same event.')
    from important_events import recap_candidates
    payload['important_recaps']=recap_candidates(ROOT)
    from editorial_policy import coverage
    payload['ai_coverage']=coverage(rows,sources,config().get('editorial',{}))
    from game_sources import coverage as game_coverage
    payload['game_coverage']=game_coverage(rows)
    payload['tibo_review_candidates']=review_candidates(rows,ROOT)
    from leader_editorial import review_leader_candidates
    payload['leader_review_candidates']=review_leader_candidates(rows,ROOT)
    dump(ROOT/"data/candidates.json",payload)
    if compact:
        selected=rows[cursor:cursor+limit]
        brief=[{k:item.get(k) for k in ('id','kind','publisher','published','title','url','source_type','priority_tier','game','game_region','game_topic','evidence_path') if item.get(k) is not None} for item in selected]
        print(json.dumps(dict(total=len(rows),cursor=cursor,next_cursor=cursor+len(selected) if cursor+len(selected)<len(rows) else None,
                              items=brief,excluded_used_count=len(excluded),full_file='data/candidates.json',
                              game_coverage=payload['game_coverage'],
                              note='Open full local evidence before final factual claims; compact list omits summaries.'),ensure_ascii=False))
    else:
        for item in rows: print(json.dumps({k:item[k] for k in ["id","kind","publisher","published","title","url","summary"]},ensure_ascii=False))

def candidate_order(item):
    # Discovery order only; leader_editorial applies verified reset exceptions
    # and the final company-before-ordinary-leaders scene order at import.
    ai=item['kind']=='ai'
    if item['kind']=='games':return (-1,{'update':0,'event':1}.get(item.get('game_topic'),2),item.get('source_priority',100),0,-dt.datetime.fromisoformat(item['published']).timestamp())
    prerelease=bool(re.search(r'/(?:releases/tag)/[^/]*(?:alpha|beta|nightly|preview)',item.get('url',''),re.I))
    repost=bool(re.match(r'^(?:RT\s+@|转发)',item.get('title',''),re.I))
    link_only=bool(re.fullmatch(r'https?://\S+',item.get('title','').strip(),re.I))
    return (0 if ai else 1,int(prerelease or repost or link_only) if ai else 0,item.get('priority_tier',2) if ai else 0,
            item.get('preferred_vendor_order',99) if ai else 0,
            item.get('source_priority',100) if ai else 0,
            -dt.datetime.fromisoformat(item['published']).timestamp())

def article(item_id,compact=False,max_chars=8000):
    if max_chars<500 or max_chars>60000:raise ValueError('Use max_chars 500-60000')
    db=database(); row=db.execute("SELECT * FROM items WHERE id=?",(item_id,)).fetchone();db.close()
    if not row: raise ValueError("Unknown candidate")
    row=dict(row)
    if row['source_id'].startswith(('x-leader-','x-official-')):
        evidence=load(ROOT/'data/leader-posts'/(item_id+'.json'))
        if compact:
            print(json.dumps(dict(item_id=item_id,source_type=evidence.get('source_type'),published=evidence.get('published'),
                                  original_text=evidence.get('original_text'),evidence_path='data/leader-posts/'+item_id+'.json'),ensure_ascii=False))
        else:print(json.dumps(evidence,ensure_ascii=False,indent=2))
        return
    game_path=ROOT/'data/game-items'/(item_id+'.json')
    game_data=load(game_path) if game_path.exists() else {}
    if game_data.get('source_type')=='skland_browser':
        if config().get('game_news',{}).get('skland_mode')=='non_browser_only':
            cached=ROOT/'data/articles'/(item_id+'.json')
            if not cached.is_file() or not load(cached).get('body_complete'):
                raise ValueError('SOURCE_GAP: no inspected cached Skland original; browser fallback is disabled')
            data=load(cached)
            if compact:
                print(json.dumps(dict(item_id=item_id,title=data['title'],published=data['published'],
                    text=data.get('text','')[:max_chars],truncated=len(data.get('text',''))>max_chars,
                    full_file='data/articles/'+item_id+'.json',source_status='cached_original_only'),ensure_ascii=False))
            else:print(json.dumps(data,ensure_ascii=False,indent=2))
            return
        from skland_sources import BrowserReader
        from game_sources import article as game_article
        with BrowserReader(ROOT) as browser:data=browser.article(game_data)
        data.update(item_id=item_id,fetched_at=dt.datetime.now(UTC).isoformat())
        data=game_article(ROOT,item_id,data,'')
        dump(ROOT/'data/articles'/(item_id+'.json'),data)
        if compact:
            print(json.dumps(dict(item_id=item_id,title=data['title'],published=data['published'],published_precision=data['published_precision'],
                 text=data['text'][:max_chars],truncated=len(data['text'])>max_chars,body_complete=True,
                 related_images=data['related_images'],full_file='data/articles/'+item_id+'.json'),ensure_ascii=False))
        else:print(json.dumps(data,ensure_ascii=False,indent=2))
        return
    body,final,encoding=fetch(row["url"])
    page=PageText(); page.feed(body.decode(encoding,errors="replace"))
    content=re.sub(r"[ \t]+"," "," ".join(page.parts))
    data=dict(item_id=item_id,title=row["title"],url=final,metadata=page.metadata,text=content[:60000],fetched_at=dt.datetime.now(UTC).isoformat())
    game_path=ROOT/"data/game-items"/(item_id+".json")
    if game_path.exists():
        from game_sources import article as game_article
        data=game_article(ROOT,item_id,dict(load(game_path),**data),body.decode(encoding,errors="replace"))
    dump(ROOT/"data/articles"/(item_id+".json"),data)
    if compact:
        brief={k:data.get(k) for k in ('item_id','title','url','metadata','fetched_at','images') if k in data}
        brief.update(text=data['text'][:max_chars],text_chars=len(data['text']),truncated=len(data['text'])>max_chars,
                     full_file='data/articles/'+item_id+'.json')
        print(json.dumps(brief,ensure_ascii=False))
    else:print(json.dumps(data,ensure_ascii=False,indent=2))

def import_editorial(path):
    cfg=config(); episode=load(path)
    if cfg.get('freshness',{}).get('enabled'):episode['overview_subject_policy']=1
    episode['audio_content_review_required']=True
    from production_policy import ORDER_VERSION,validate_content
    episode['production_policy_version']=ORDER_VERSION
    validate_content(episode)
    if cfg.get('background_music',{}).get('enabled'):
        bgm=cfg['background_music']
        episode['background_music_requirement']={k:bgm[k] for k in ['sha256','repeat_from_seconds','reference_voice_gap_db','voice_gap_measure','music_peak_dbfs']}
    source_catalog={s['id']:s for s in load(ROOT/'sources.json')} if (ROOT/'sources.json').exists() else {}
    from important_events import prepare_main_recaps
    if cfg.get('editorial',{}).get('include_important_recaps',True):prepare_main_recaps(episode,ROOT)
    from leader_editorial import apply_leader_identity_and_speech,prepare_main_leaders
    apply_leader_identity_and_speech(episode,ROOT)
    leader_audit=prepare_main_leaders(episode,ROOT)
    # Leader attribution prepends an introduction sentence, so a grouping plan
    # computed before this step would no longer cover every spoken sentence.
    if episode.get('voice_context_group_sentence_counts'):
        from reset_layout import context_groups
        episode['voice_context_group_sentence_counts']=context_groups(episode['scenes'])
    tibo_audit=episode.get('tibo_audit')
    if leader_audit:episode['leader_audit']=leader_audit
    from freshness import audit_episode
    audit_episode(episode,ROOT,bind=True)
    from production_policy import apply_story_order
    apply_story_order(episode,ROOT)
    from layout_policy import prepare_overview
    prepare_overview(episode,cfg.get('presentation',{}).get('prefer_overview',True))
    from scene_media import prepare as prepare_scene_media
    media_audit=prepare_scene_media(episode,ROOT)
    if episode.get('edition_slot')=='temporary':
        from temporary_editions import validate_temporary
        validate_temporary(episode)
    if episode.get('producer') not in cfg.get('editorial',{}).get('allowed_producers',['Codex current conversation','DeepSeek Harness','manual editor']):raise ValueError('Producer must be disclosed using an allowed producer name')
    db=database(); selected=[];selected_rows=[]
    for scene in episode["scenes"]:
        if scene.get("item_id"):
            row=db.execute("SELECT * FROM items WHERE id=?",(scene["item_id"],)).fetchone()
            if not row: raise ValueError("Editorial refers to unknown collected candidate")
            row=dict(row)
            if row["kind"]=="social":raise ValueError("Social stories removed from new editions")
            if row["kind"]=="games":
                record=load(ROOT/"data/game-items"/(row["id"]+".json"))
                if scene.get("game")!=record.get("game") or scene.get("game_region")!=record.get("game_region"):raise ValueError("Game identity/region differs from official source")
                if record.get('source_type')=='skland_browser':
                    inspected=ROOT/'data/articles'/(row['id']+'.json')
                    if not inspected.exists() or not load(inspected).get('body_complete'):
                        raise ValueError('Read full Skland official article before selecting it')
                    scene['published']=load(inspected)['published'];scene['published_precision']=load(inspected)['published_precision']
            if scene.get("image") and row["kind"]=="games":
                article_path=ROOT/"data/articles"/(row["id"]+".json")
                if not article_path.exists() or not any(x.get("file")==scene["image"] and x.get("source_url")==scene.get("image_source_url") for x in load(article_path).get("related_images",[])):raise ValueError("Game picture must match the inspected official article and recorded source URL")
            if scene.get("source_url") != row["url"]: raise ValueError("Source URL does not match collected candidate")
            if not scene.get("evidence") or not scene.get("selection_reason"): raise ValueError("Missing evidence/ranking reason")
            if row['source_id'].startswith(('x-leader-','x-official-')):
                from leader_sources import validate_scene
                validate_scene(scene,load(ROOT/'data/leader-posts'/(scene['item_id']+'.json')))
            if source_catalog.get(row['source_id'],{}).get('published_precision')=='date' or row['source_id']=='kimi-blog':scene['published_precision']='date'
            selected.append(scene["item_id"])
            if scene.get('editorial_role')=='recap':
                from important_events import validate_recap
                validate_recap(scene,episode,ROOT)
            else:selected_rows.append(dict(row,**({'event_key':scene['event_key']} if scene.get('event_key') else {})))
    if len(set(selected))!=len(selected) and not episode.get("alert_id"):
        for repeated in {item for item in selected if selected.count(item)>1}:
            pages=[sc for sc in episode["scenes"] if sc.get("item_id")==repeated]
            if any(not sc.get("game") or not isinstance(sc.get("page_number"),int) for sc in pages) or len({sc.get("event_key") for sc in pages})!=1 or len({sc["page_number"] for sc in pages})!=len(pages):raise ValueError("Duplicate event selection")
    db.close()
    from used_news import recent_records,exclude_used
    edition_key=episode.get('edition_key',re.sub(r'-v\d+$','',episode['id']))
    _,already_used,_=exclude_used(selected_rows,[r for r in recent_records(ROOT) if r['edition_key']!=edition_key])
    if already_used:raise ValueError('News already used in another completed edition: '+', '.join(x['id'] for x in already_used))
    selection_audit=None
    if episode.get('edition_slot') in {'morning','noon','night'} and cfg.get('editorial',{}).get('ai_coverage'):
        from editorial_policy import audit_selection
        sources={s['id']:s for s in load(ROOT/'sources.json')} if (ROOT/'sources.json').exists() else {}
        if cfg.get('x_enabled'):
            from leader_sources import registry
            sources.update({s['id']:s for s in registry() if s.get('enabled')})
        pool_db=database()
        try:pool=[dict(r) for r in pool_db.execute("SELECT * FROM items WHERE kind='ai'")]
        finally:pool_db.close()
        pool,_,_=exclude_used(pool,[r for r in recent_records(ROOT) if r['edition_key']!=edition_key])
        selection_audit=audit_selection(episode,selected_rows,pool,sources,cfg.get('editorial',{}))
        if selection_audit:episode['ai_coverage_audit']=selection_audit
    validate_content(episode)
    episode["publication_preset"]=cfg["publication_preset"]
    episode['upload_enabled']=bool(cfg.get('upload_enabled'));episode['auto_publish']=bool(cfg.get('auto_publish'))
    directory=ROOT/"episodes"/episode["id"]; directory.mkdir(parents=True,exist_ok=True)
    if (directory/'release.json').exists():raise ValueError('Published edition is archived; create a new revision ID')
    if selection_audit:dump(directory/'ai-coverage-audit.json',selection_audit)
    from game_sources import coverage as game_coverage
    game_rows=[]
    for sc in episode['scenes']:
        if sc.get('game'):game_rows.append(dict(sc,kind='games',url=sc['source_url']))
    dump(directory/'game-coverage-audit.json',game_coverage(game_rows))
    if episode.get('original_post_text'):dump(directory/'original-post.json',dict(text=episode['original_post_text'],source_url=episode['scenes'][0]['source_url'],published=episode['scenes'][0]['published']))
    if tibo_audit:dump(directory/'tibo-audit.json',tibo_audit)
    if leader_audit:dump(directory/'leader-audit.json',leader_audit)
    dump(directory/"episode.json",episode)
    if media_audit:dump(directory/'scene-media.json',media_audit)
    (directory/"script.txt").write_text("\n".join(s["narration"] for s in episode["scenes"]),encoding="utf-8")
    print(directory)

def voice(episode_id):
    cfg=config(); directory=ROOT/"episodes"/episode_id
    if (directory/'release.json').exists():raise ValueError('Published edition is archived; create a new revision ID')
    episode=load(directory/'episode.json')
    v=cfg["voice"]
    from pronunciation import spoken_text
    display_script=(directory/'script.txt').read_text(encoding='utf-8')
    spoken_path=directory/'spoken_script.txt'
    spoken_path.write_text(spoken_text(display_script,v.get('pronunciations',{})),encoding='utf-8')
    backend=v.get('backend','gpt-sovits')
    job=dict(text_file=str(spoken_path),output_file=str(directory/'narration.wav'),pause=v['pause'],seed=42)
    if backend=='qwen3':
        qwen=v['qwen3'];executable=Path(qwen['python']);context=qwen.get('contextual_generation',False)
        worker=Path(v['repository'])/'tools'/('qwen_generate_context.py' if context else 'qwen_generate_job.py')
        job.update(model_path=qwen['model_path'],reference=v['reference_audio'],reference_text=v['reference_text'],qwen_language='Chinese',synthesis_unit='sentence',max_new_tokens=1024,cleanup='off')
        job.update(qwen.get('sampling',{}));job['consistent_unit_seed']=qwen.get('consistent_unit_seed',False)
        job['speech_rate']=qwen.get('speech_rate',1);job['ffmpeg_executable']=qwen.get('ffmpeg_executable')
        job['compound_pause_max_seconds']=qwen.get('compound_pause_max_seconds',.12)
        job['context_max_new_tokens']=int(episode.get('voice_context_max_new_tokens',1024))
        if context:
            from scene_pauses import sentence_scene_ids
            ids=sentence_scene_ids(episode)
            job.update(context_group_sentence_counts=episode.get('voice_context_group_sentence_counts') or [ids.count(scene['id']) for scene in episode['scenes']],alignment_python=qwen['alignment_python'],alignment_model=qwen['alignment_model'],paragraph_pause=qwen.get('paragraph_pause',.6))
        worker_cwd=v['repository']
    elif backend=='gpt-sovits':
        profile=load(v['profile']);executable=Path(v['engine'])/'runtime/python.exe';worker=Path(v['repository'])/'tools/generate_job.py';worker_cwd=v['engine']
        job.update(project=v['engine'],gpt=profile['model']['t2s_weights_path'],sovits=profile['model']['vits_weights_path'],reference=v.get('reference_audio',profile['request']['ref_audio_path']),reference_text=v.get('reference_text',profile['request']['prompt_text']),reference_language='all_zh',language=v['language'],speed=v['speed'],cleanup=v['cleanup'],temperature=.75)
    else:raise ValueError('Unknown local voice backend')
    dump(directory/'voice_job.json',job)
    env=os.environ.copy();env.update(PYTHONIOENCODING="utf-8",PYTHONUTF8="1",PYTHONDONTWRITEBYTECODE="1")
    # Workspace-owned lock; never terminate another voice/desktop process.
    lock=ROOT/"data/voice.lock"
    with lock.open("x",encoding="utf-8") as handle: handle.write(str(os.getpid()))
    try:
        with (directory/"voice.log").open("w",encoding="utf-8") as log:
            result=subprocess.run([str(executable),"-u","-B",str(worker),"--job",str(directory/"voice_job.json")],cwd=worker_cwd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if result.returncode: raise RuntimeError("Voice failed; inspect "+str(directory/"voice.log"))
    finally: lock.unlink(missing_ok=True)
    if backend=='gpt-sovits' and v.get("tail_style")=="crisp":
        with (directory/"crisp.log").open("w",encoding="utf-8") as log:
            processed=subprocess.run([str(executable),str(ROOT/"crisp_tails.py"),episode_id,episode_id],env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if processed.returncode:raise RuntimeError("Crisp release processing failed; inspect "+str(directory/"crisp.log"))
    elif backend=='gpt-sovits' and v.get("soft_release"):
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
    if backend=='qwen3':
        episode['audio_content_review_required']=True
        dump(directory/'episode.json',episode)
        local_python=v['qwen3']['alignment_python']
        quality_env=env.copy();quality_env['NUMBA_CACHE_DIR']=str(ROOT/'.cache/numba-asr')
        for check_worker in ['verify_speech_content.py','align_captions.py']:
            subprocess.run([local_python,'-u','-B',str(ROOT/check_worker),episode_id],env=quality_env,cwd=ROOT,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    print(json.dumps(dict(duration=meta["seconds"],sentences=len(sentences),cleanup=job["cleanup"]),ensure_ascii=False))

def doctor():
    cfg=config();v=cfg["voice"]
    qwen=v.get('backend')=='qwen3';context=qwen and v['qwen3'].get('contextual_generation',False)
    worker='qwen_generate_context.py' if context else 'qwen_generate_job.py' if qwen else 'generate_job.py'
    python=Path(v['qwen3']['python']) if qwen else Path(v['engine'])/'runtime/python.exe'
    checks={"voice_worker":(Path(v['repository'])/'tools'/worker).is_file(),"voice_python":python.is_file(),"upload_policy_valid":not cfg.get('upload_enabled') or cfg.get('publisher',{}).get('user_authorized',False),"hourly_model_calls_disabled":not cfg['social_collection_allow_model_calls']}
    if not qwen:checks['voice_profile']=Path(v['profile']).is_file()
    if context:checks.update(alignment_python=Path(v['qwen3']['alignment_python']).is_file(),alignment_weights=(Path(v['qwen3']['alignment_model'])/'model.pt').is_file())
    if cfg.get('background_music',{}).get('enabled'):
        from audio_mix import digest
        bgm=cfg['background_music'];path=(ROOT/bgm['file']).resolve()
        checks['background_music_file']=path.is_file()
        checks['background_music_hash']=path.is_file() and (not bgm.get('sha256') or digest(path)==bgm['sha256'])
    if cfg.get('publisher',{}).get('enabled'):
        from upload_bridge import paths
        cli,home=paths(ROOT);checks.update(upload_skill_cli=cli.is_file(),upload_runtime=(home/'runtime.local.json').is_file(),upload_account_bound=(home/'account.json').is_file())
    if v.get('backend')=='qwen3':
        q=v['qwen3'];checks.update(qwen_python=Path(q['python']).is_file(),qwen_worker=(Path(v['repository'])/'tools/qwen_generate_job.py').is_file(),qwen_weights=(Path(q['model_path'])/'model.safetensors').is_file(),qwen_tokenizer=(Path(q['model_path'])/'speech_tokenizer/model.safetensors').is_file())
        reference=Path(v.get('reference_audio',''))
        checks.update(qwen_reference_audio=reference.is_file(),qwen_reference_text=bool(v.get('reference_text','').strip()))
        if v.get('reference_sha256'):checks['qwen_reference_hash']=reference.is_file() and hashlib.sha256(reference.read_bytes()).hexdigest()==v['reference_sha256']
    print(json.dumps(checks,ensure_ascii=False,indent=2)); return all(checks.values())

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="cmd",required=True)
    sub.add_parser("doctor")
    p=sub.add_parser("collect");p.add_argument("--kind",choices=["social","games","ai","all"],required=True)
    p=sub.add_parser("candidates");p.add_argument("--hours",type=int,default=48);p.add_argument("--compact",action="store_true");p.add_argument("--limit",type=int,default=12);p.add_argument("--cursor",type=int,default=0)
    p=sub.add_parser("article");p.add_argument("id");p.add_argument("--compact",action="store_true");p.add_argument("--max-chars",type=int,default=8000)
    p=sub.add_parser("import-editorial");p.add_argument("path")
    p=sub.add_parser("voice");p.add_argument("episode")
    args=parser.parse_args()
    if args.cmd=="doctor": return 0 if doctor() else 1
    if args.cmd=="collect":collect(args.kind)
    elif args.cmd=="candidates":candidates(args.hours,args.compact,args.limit,args.cursor)
    elif args.cmd=="article":article(args.id,args.compact,args.max_chars)
    elif args.cmd=="import-editorial":import_editorial(args.path)
    elif args.cmd=="voice":voice(args.episode)
    return 0

if __name__=="__main__":raise SystemExit(main())
