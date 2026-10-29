"""Read official announcement responses in the user's BrowserSkill session.

The website performs its own authenticated requests. Never read cookies, sign
requests, export profiles, replay API calls or bypass the site's login flow.
"""
import datetime as dt,json,os,shutil,subprocess,time
from pathlib import Path
from urllib.parse import urlparse,parse_qs

class SourceStopped(RuntimeError):pass

def parse_rows(rows,source):
    from game_sources import topic
    out=[]
    for row in rows:
        item=row.get('item',{});user=row.get('user',{})
        if user.get('identity')!=2 or user.get('nickname') not in source['official_authors']:continue
        if item.get('gameId')!=source['skland_game_id'] or item.get('cateId')!=source['skland_cate_id']:continue
        stamp=item.get('publishedAtTs')
        if not stamp or not item.get('id') or not item.get('title'):continue
        published=dt.datetime.fromtimestamp(int(stamp),dt.timezone.utc).isoformat()
        images=[x['url'] for x in item.get('imageList',[]) if x.get('url')]
        if item.get('cover',{}).get('url'):images=list(dict.fromkeys(images+[item['cover']['url']]))
        out.append(dict(title=item['title'],url='https://www.skland.com/article?id='+str(item['id']),
                        published=published,published_precision='second',summary=item.get('brief') or item['title'],
                        body_complete=False,images=images,game=source['game'],game_region=source['game_region'],
                        game_topic=topic(item['title']),source_type='skland_browser',
                        original_author=user['nickname'],author_profile='https://www.skland.com/profile?id='+str(user['id']),
                        official_identity=2,identity_evidence=source['url'],skland_item_id=str(item['id'])))
    return out

class BrowserReader:
    def __init__(self,root):
        self.root=Path(root);self.session=None
        path=self.root/'.cache/skland-browser.json'
        if not path.is_file():raise SourceStopped('NEED_SETUP: configure .cache/skland-browser.json with the verified browser instance_id')
        self.local=json.loads(path.read_text(encoding='utf-8'))
        self.cli=shutil.which('bsk')
        if not self.cli:raise SourceStopped('NEED_SETUP: BrowserSkill CLI missing')

    def call(self,*args):
        env=os.environ.copy();env.update(BSK_AUTO_START='0',PYTHONIOENCODING='utf-8')
        result=subprocess.run([self.cli,*map(str,args),'--json'],capture_output=True,text=True,encoding='utf-8',env=env,
                              timeout=60,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:data=json.loads(result.stdout)
        except ValueError:raise SourceStopped('BROWSER_UNAVAILABLE: BrowserSkill did not return structured JSON')
        if result.returncode or data.get('ok') is False or data.get('error'):
            # No raw browser response or headers in routine logs.
            raise SourceStopped('BROWSER_STOPPED: '+str(data.get('message') or data.get('error') or 'check BrowserSkill session'))
        return data

    def __enter__(self):
        self.session=self.call('session','start','--browser',self.local['instance_id'],'--no-focus')['session_id']
        try:self.call('debug','start','--session',self.session,'--name','official-game-announcements')
        except Exception:
            self.call('session','stop',self.session);raise
        return self

    def __exit__(self,*_):
        if self.session:
            try:self.call('debug','stop','--session',self.session)
            finally:self.call('session','stop',self.session)

    def body(self,request,pointer):
        text='';offset=0
        while True:
            result=self.call('debug','request',request,'--session',self.session,'--part','response',
                             '--pointer',pointer,'--offset',offset,'--max-chars',16384)
            body=result['request']['response_body']
            if body.get('state')!='available' or result.get('output',{}).get('truncated'):
                raise SourceStopped('SOURCE_GAP: incomplete announcement response')
            text+=body.get('text','');next_offset=body.get('next_offset')
            if next_offset is None:break
            if next_offset<=offset or next_offset>65536:raise SourceStopped('SOURCE_GAP: announcement exceeds response slice limit')
            offset=next_offset
        return json.loads(text)

    def responses(self,path):
        rows=self.call('debug','requests','--session',self.session,'--url',path,'--method','GET','--limit',100)['requests']
        if any(r.get('status') in {401,403,429} for r in rows):raise SourceStopped('NEED_USER: login, verification or rate limit; stop channel')
        return [r for r in rows if r.get('state')=='complete' and r.get('status')==200 and r.get('response_body',{}).get('state')=='available']

    def navigate(self,url,path):
        self.call('navigate',url,'--session',self.session)
        for _ in range(12):
            rows=self.responses(path)
            if rows:return rows
            time.sleep(.5)
        raise SourceStopped('SOURCE_GAP: no complete announcement response; verify login and page')

    def collect(self,source):
        rows=self.navigate(source['url'],'/web/v2/home/index');seen=set();entries={};complete=False;reason='page_budget_reached; inspect remaining UI'
        cutoff=dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=48)
        for page in range(self.local.get('max_pages',20)):
            new=[r for r in rows if r['id'] not in seen and parse_qs(urlparse(r['url']).query).get('gameId')==[str(source['skland_game_id'])]]
            all_dates=[];at_end=False
            for response in new:
                seen.add(response['id'])
                payload=self.body(response['id'],'/data');items=payload['list']
                at_end=at_end or payload.get('hasMore') is False
                for row in items:
                    stamp=row.get('item',{}).get('publishedAtTs')
                    if stamp:all_dates.append(dt.datetime.fromtimestamp(int(stamp),dt.timezone.utc))
                for item in parse_rows(items,source):entries[item['url']]=item
            if at_end:complete=True;reason='official_hasMore_false';break
            if new and all_dates and max(all_dates)<cutoff:complete=True;reason='48h_boundary';break
            self.call('wheel','--delta-y',2200,'--session',self.session)
            for _ in range(6):
                time.sleep(.5);rows=self.responses('/web/v2/home/index')
                if any(r['id'] not in seen for r in rows):break
            else:reason='no_next_response; pagination_not_proven_complete';break
        return list(entries.values()),dict(pages=len(seen),pagination_complete=complete,
                stop_reason=reason,model_calls=0)

    def article(self,data):
        rows=self.navigate(data['url'],'/web/v2/item')
        response=next((r for r in reversed(rows) if parse_qs(urlparse(r['url']).query).get('id')==[data['skland_item_id']]),None)
        if not response:raise SourceStopped('SOURCE_GAP: matching article response missing')
        item=self.body(response['id'],'/data/item')
        # DOM isolates original article text; comments, account data and page
        # requests remain in the browser and are never exported.
        for _ in range(8):
            value=self.call('evaluate',"({text:document.querySelector('[class*=ArticleWrapper] [class*=Document]')?.innerText||'',author:document.querySelector('[class*=AuthorCard]')?.innerText||''})",'--session',self.session)['value']
            if value['text'] and value['author']:break
            time.sleep(.25)
        if data['original_author'] not in value['author'] or '官方账号' not in value['author']:
            raise SourceStopped('SOURCE_GAP: original official author not confirmed on article')
        if item.get('title')!=data['title'] or not item.get('publishedAtTs') or not value['text']:
            raise SourceStopped('SOURCE_GAP: missing original title, time or full article text')
        data.update(text=value['text'],official_body=[value['text']],body_complete=True,
                    published=dt.datetime.fromtimestamp(int(item['publishedAtTs']),dt.timezone.utc).isoformat(),
                    published_precision='second',images=[i['url'] for i in item.get('imageList',[]) if i.get('url')])
        return data
