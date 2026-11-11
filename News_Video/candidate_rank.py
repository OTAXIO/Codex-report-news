"""Candidate ranking, same-event clusters and the review-coverage gate (2026-11-11).

Why: on 2026-11-11 the AI pool held 339 fresh candidates but only 17 were looked at; the Claude
usage reset (posted by bcherny) sat unread while a competitor led with it. Candidates are now
scored for what this audience acts on (resets, limits, bans, prices, new models), reports of the
same event are grouped, and import requires a decision (selected or a rejection reason) for every
one of the top `editorial.review_coverage.top_n` groups of the edition's series.

The score orders discovery only; it never selects a story or overrides a freshness/source gate.
"""
from __future__ import annotations
import datetime as dt,re

# (weight, label, pattern) — matched against title + the start of the summary, case-insensitive.
SIGNALS=[
    (30,'quota_reset_or_limits',r'\breset|重置|额度|usage limit|rate limit|weekly limit|\blimits?\b|限额|用量'),
    (30,'account_ban_or_policy',r'封号|封禁|\bban(?:s|ned)?\b|suspend|usage polic|acceptable use|terms of service|服务条款|使用政策'),
    (22,'price_or_free',r'price|pricing|降价|涨价|免费|\bfree\b|discount|优惠|半价|cheaper|\$\d'),
    (25,'release',r'introduc|launch|\breleas|now available|rolling out|发布|上线|开源|open[- ]?sourc|\bGA\b|正式版|推出'),
    (12,'preview_or_leak',r'preview|spotted|leak|灰度|曝光|内测|测试中|coming soon|即将'),
    (15,'major_model',r'GPT-?\d|\bo\d\b|Claude|Opus|Sonnet|Haiku|Fable|Mythos|Gemini|Grok|Qwen|千问|DeepSeek|Kimi|GLM|智谱|MiniMax|Llama|Muse|Codex|豆包|Seed|混元|Hunyuan|文心|ERNIE|Mistral|Scribe'),
    (10,'company_event',r'\bIPO\b|上市|funding|融资|valuation|估值|acqui|收购|lawsuit|诉讼|layoff|裁员'),
]
NOISE=r'周边|merch|giveaway|webinar|hiring|we.re hiring|招聘|how to |tips for|guide to|vs\.? .{0,20}how to choose|^RT @|^转发'
MODEL_TOKEN=re.compile(r'\b(gpt|claude|opus|sonnet|haiku|fable|gemini|grok|qwen|deepseek|kimi|glm|minimax|llama|muse|codex|scribe|ernie|hunyuan|seed|h\d)[\s-]*v?(\d+(?:\.\d+)*)'
                       r'(?:[\s-]+(pro|flash|max|mini|carbon|sol|luna|terra|astra|image|live|preview|ultra|lite|code))?',re.I)
STOP={'the','and','for','with','new','now','our','you','your','its','this','that','from','into','are','has','have','will','can','more','about','today','introducing'}

def text_of(item):
    return (item.get('title') or '')+' '+(item.get('summary') or '')[:300]

def model_tokens(text):
    return {' '.join(x for x in m.groups() if x).lower() for m in MODEL_TOKEN.finditer(text)}

def word_tokens(text):
    words={w for w in re.findall(r'[a-z0-9][a-z0-9.\-]{2,}',text.lower()) if w not in STOP}
    han=re.sub(r'[^一-鿿]','',text)
    return words|{han[i:i+2] for i in range(len(han)-1)}

def score(item,now):
    text=text_of(item);reasons=[];total=0
    for weight,label,pattern in SIGNALS:
        if re.search(pattern,text,re.I):total+=weight;reasons.append(label)
    if re.search(NOISE,item.get('title') or '',re.I):total-=25;reasons.append('noise')
    tier=item.get('priority_tier',2)
    total+={1:10,2:5}.get(tier,0)
    if item.get('rumor') and item.get('rumor_tier')=='A':total+=5
    try:
        age=(now-dt.datetime.fromisoformat(item['published'])).total_seconds()/3600
        total+=10 if age<12 else 5 if age<24 else 0
    except (KeyError,TypeError,ValueError):pass
    return total,reasons

PROPER=re.compile(r'\b([A-Z][A-Za-z0-9]+(?:[ -](?:[A-Z][A-Za-z0-9]+|v?\d+(?:\.\d+)*))+)')

def name_tokens(title):
    """The title's subject model version (the first one named, so "X beats Y" joins X's event only)
    plus its version-less proper names ("Muse Ember", "Claude Code")."""
    found=[(m.start(),' '.join(x for x in m.groups() if x).lower()) for m in MODEL_TOKEN.finditer(title)]
    names=set()
    for m in PROPER.finditer(title):
        text=m.group(1)
        if re.fullmatch(r'(?:The|A|An|New|Our|Today|How|Why|What)[ -].*',text):continue
        if re.search(r'\d',text):
            inner=MODEL_TOKEN.search(text)   # 'Claude Fable 5.2' and 'Fable 5.2' are one model
            found.append((m.start(),' '.join(x for x in inner.groups() if x).lower() if inner else text.lower()))
        else:names.add(text.lower())
    if found:names.add(min(found)[1])
    return names

# Platforms and surfaces named in many unrelated posts; sharing one says nothing about the event.
GENERIC={'claude code','claude platform','claude apps','github copilot','google cloud','google ai','ai studio','chatgpt','chatgpt plus',
         'openai','hugging face','gemini app','gemini api','meta ai','codex cli','vs code','aws bedrock','azure ai','google deepmind','agent mode',
         # people appear across unrelated stories
         'jensen huang','sam altman','elon musk','dario amodei','demis hassabis','sundar pichai','mark zuckerberg','satya nadella'}

def cluster(rows,hub=30):
    """Union items whose titles share a model version or proper name, or whose titles overlap strongly.
    A version-less name carried by more than `hub` titles ("Claude Code") says nothing about the event;
    a model version ("Fable 5.2") always does, however many reports carry it."""
    parent={r['id']:r['id'] for r in rows}
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    keys=[(r['id'],name_tokens(r.get('title') or ''),word_tokens(r.get('title') or '')) for r in rows]
    counts={}
    for _,names,_ in keys:
        for x in names:counts[x]=counts.get(x,0)+1
    first={}
    for rid,names,_ in keys:
        for x in names:
            if x in GENERIC or (counts[x]>hub and len(x.split())<2):continue   # product names ("Muse Ember") stay; platforms do not
            if x in first:parent[find(rid)]=find(first[x])
            else:first[x]=rid
    for i,(a,_,wa) in enumerate(keys):
        if len(wa)<4:continue
        for b,_,wb in keys[i+1:]:
            if len(wb)>=4 and len(wa&wb)/len(wa|wb)>=.5:parent[find(b)]=find(a)
    return {r['id']:find(r['id']) for r in rows}

def rank(rows,now=None):
    """Adds rank_score, rank_reasons, cluster (representative id) and cluster_size to every AI row."""
    now=now or dt.datetime.now(dt.timezone.utc)
    ai=[r for r in rows if r.get('kind')=='ai']
    for r in ai:r['rank_score'],r['rank_reasons']=score(r,now)
    groups={}
    for rid,root in cluster(ai).items():groups.setdefault(root,[]).append(rid)
    by_id={r['id']:r for r in ai}
    for members in groups.values():
        items=[by_id[m] for m in members]
        # The group is as hot as its best report plus how many distinct sources carry it.
        sources={i.get('source_id') for i in items}
        best=max(items,key=lambda i:(i['rank_score'],i.get('priority_tier',2)==1))
        bonus=min(8*(len(sources)-1),32)
        for i in items:
            i['cluster']=best['id'];i['cluster_size']=len(items);i['cluster_score']=best['rank_score']+bonus
    return rows

def ordered(rows):
    """AI groups by score (representative first, then its other reports); other kinds keep their place after."""
    ai=[r for r in rows if r.get('kind')=='ai' and 'cluster' in r];rest=[r for r in rows if r not in ai]
    reps=sorted({r['cluster'] for r in ai},key=lambda c:-next(r['cluster_score'] for r in ai if r['cluster']==c))
    out=[]
    for c in reps:
        members=sorted([r for r in ai if r['cluster']==c],key=lambda r:(r['id']!=c,-r['rank_score']))
        out+=members
    return rest+out if rest and rest[0].get('kind')=='games' else out+rest

def must_review(rows,top_n):
    """Representative ids of the top groups, best first."""
    seen=[]
    for r in rows:
        if r.get('kind')=='ai' and r.get('cluster') and r['cluster'] not in seen:seen.append(r['cluster'])
    return seen[:top_n]

def check_coverage(episode,rows,top_n):
    """Every top group needs a decision: one of its reports selected, or a rejection reason for one of them."""
    chosen={s.get('item_id') for s in episode['scenes']}|set((episode.get('rejections') or {}).keys())
    members={}
    for r in rows:
        if r.get('cluster'):members.setdefault(r['cluster'],set()).add(r['id'])
    missing=[c for c in must_review(rows,top_n) if not members.get(c,{c})&chosen]
    if missing:
        titles={r['id']:(r.get('title') or '')[:70] for r in rows}
        raise ValueError(f'REVIEW_COVERAGE: {len(missing)} of the top {top_n} candidate groups have no decision; '
                         'select one or add a reason under rejections (one reason covers the whole group): '
                         +'; '.join(f'{c} {titles.get(c,"")}' for c in missing[:12]))
    return dict(top_n=top_n,reviewed_groups=min(top_n,len(must_review(rows,top_n))))
