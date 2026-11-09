"""Shared public-wording and community-content checks (2026-11-09 expansion).

Rumors may lead an AI edition, but they are never stated as fact; community
material is screened before it can become a quote. Everything here is a
deterministic check on text the producer wrote or collected.
"""
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def filter_terms(root=ROOT):
    path=Path(root or ROOT)/'content_filter.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else dict(categories={},public_banned=[])

def _hit(term,text):
    if re.fullmatch(r'[A-Za-z0-9 ]+',term):
        return re.search(r'(?<![A-Za-z0-9])'+re.escape(term)+r'(?![A-Za-z0-9])',text,re.I) is not None
    return term in text

def screen(text,root=ROOT,allow=()):
    """Categories a text hits; ``allow`` skips categories (e.g. a marked spoiler)."""
    text=str(text or '');hits=[]
    for category,terms in filter_terms(root).get('categories',{}).items():
        if category in allow:continue
        if any(_hit(t,text) for t in terms):hits.append(category)
    return hits

# --- Rumor wording ----------------------------------------------------------
# "尚未确认/未经证实" are required disclaimers; an affirmative "确认/实锤/官方已经"
# would present a rumor as settled fact.
NEGATED=re.compile(r'(?:尚未|未经|未|没有|并未|仍未|还没有?|暂未|无法)(?:被)?(?:官方)?(?:正式)?(?:确认|证实)')
AFFIRM=re.compile(r'实锤|板上钉钉|官方已经|已经官宣|确认|证实')

def rumor_affirmations(text):
    """Affirmative claims left after removing negated disclaimers."""
    return AFFIRM.findall(NEGATED.sub('',str(text or '')))

def sentences(text):
    return [p.strip() for p in re.split(r'(?<=[。！？!?])\s*',str(text or '')) if p.strip()]

ATTRIBUTION=re.compile(r'称|爆料|透露|发现|曝|声称|表示|据')
OFFICIAL_STATUS=re.compile(r'官方')
STATUS_WORDS={'未回应':re.compile(r'未回应|尚未回应|没有回应|未置评|尚未证实|尚未确认|未经证实|没有证实'),
              '已否认':re.compile(r'否认|辟谣'),
              '已部分确认':re.compile(r'部分')}
RUMOR_MARKERS=('曝','传','疑似')

def check_rumor_narration(narration,names,official_status):
    """First sentence names the source; last sentence states the official status."""
    parts=sentences(narration)
    if not parts:raise ValueError('RUMOR_NARRATION_EMPTY')
    first=parts[0].casefold()
    if not any(n and n.casefold() in first for n in names) or not ATTRIBUTION.search(parts[0]):
        raise ValueError('RUMOR_ATTRIBUTION_REQUIRED: the first sentence must name the source account/community and say it claims (称/爆料/发现)')
    last=parts[-1]
    if not OFFICIAL_STATUS.search(last) or not STATUS_WORDS[official_status].search(last):
        raise ValueError('RUMOR_OFFICIAL_STATUS_REQUIRED: the last sentence must state the official status ('+official_status+')')
    found=rumor_affirmations(narration)
    if found and official_status!='已部分确认':raise ValueError('RUMOR_STATED_AS_FACT: '+'、'.join(dict.fromkeys(found)))

def check_public_words(text,root=ROOT,rumor=False):
    """Clickbait and vulgar words never appear in public titles or narration."""
    text=str(text or '')
    banned=[w for w in filter_terms(root).get('public_banned',[]) if w in text]
    if banned:raise ValueError('PUBLIC_WORD_BANNED: '+'、'.join(banned))
    hits=screen(text,root,allow=('flamewar','spoiler'))
    if hits:raise ValueError('PUBLIC_CONTENT_FILTER: '+'、'.join(hits))
    if rumor and rumor_affirmations(text):raise ValueError('RUMOR_STATED_AS_FACT in title: '+'、'.join(rumor_affirmations(text)))
