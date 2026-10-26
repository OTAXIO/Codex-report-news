"""Word-aware cue and line boundaries, preserving displayed numeric meaning."""
import functools,json,math,re
from pathlib import Path
ROOT=Path(__file__).parent
REPLACEMENTS={'十月二十六日':'10 月 26 日','二点一点三一零':'2.1.310','二十点一亿千瓦':'20.1 亿千瓦','六点三四亿千瓦时':'6.34 亿千瓦时','十二倍':'12 倍','九月底':'9 月底','九月中旬至十月中旬':'9 月中旬至 10 月中旬'}
REPLACEMENTS.update({'百分之五十五':'55%','三十五岁':'35 岁','三小时':'3 小时'})
PROTECTED=['人工智能','太阳能发电','累计装机','装机容量','实际发电量','中国新闻网','国家能源局','发射工位','发射前','全流程演练','上门照护','社区助餐','智能照护产品','居家养老','大熊猫','跨境电力','研究构思','存储系统','多租户','全球缓存','工程文章','保护研究合作','发电量','千瓦时','千瓦','尾音','关联到文献','转运到发射工位','训练与评估环境的隔离措施','发射前准备阶段']
PROTECTED+=['千问','千问编程助手','国内外重点新闻']
TOKEN=re.compile(r'Qwen Code|Claude Code|Hugging Face|OpenAI|Anthropic|Ai2|DeepSeek|MiniMax|LitPivot|\d+(?:\.\d+)*(?:\s*(?:亿|万)?(?:千瓦时|千瓦|倍|月(?:中旬|底)?|日|秒|小时|分钟|%))?|[\u4e00-\u9fff]+|[A-Za-z][A-Za-z0-9_-]*|.',re.S)

@functools.lru_cache(maxsize=1)
def dictionary():
    engine=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))['voice']['engine']
    path=Path(engine)/'runtime/Lib/site-packages/jieba/dict.txt'
    words={};total=0
    for line in path.read_text(encoding='utf-8').splitlines():
        fields=line.split()
        if len(fields)>=2:words[fields[0]]=int(fields[1]);total+=int(fields[1])
    for word in PROTECTED:words[word]=10_000_000
    return words,math.log(total)

def chinese_words(text):
    words,log_total=dictionary();score={len(text):(0,None)}
    for i in range(len(text)-1,-1,-1):
        choices=[(math.log(max(1,words.get(text[i:j],0)))-log_total+score[j][0],j) for j in range(i+1,min(len(text),i+24)+1) if j==i+1 or text[i:j] in words]
        score[i]=max(choices)
    result=[];i=0
    while i<len(text):j=score[i][1];result.append(text[i:j]);i=j
    return result

def tokens(text):
    result=[]
    for m in TOKEN.finditer(text):
        value=m.group()
        result.extend(chinese_words(value) if re.fullmatch(r'[\u4e00-\u9fff]+',value) else [value])
    return result

def width(text):
    return sum(1. if '\u4e00'<=c<='\u9fff' or c in '，。！？；：、（）“”' else .55 for c in text)

def normalize(text):
    output=[];weights=[];i=0
    while i<len(text):
        key=next((k for k in sorted(REPLACEMENTS,key=len,reverse=True) if text.startswith(k,i)),None)
        if key:
            value=REPLACEMENTS[key];output.append(value);weights.extend([len(key)/len(value)]*len(value));i+=len(key)
        else:output.append(text[i]);weights.append(1.);i+=1
    return ''.join(output),weights

def wrap(text,max_width=24):
    if width(text)<=max_width:return text.strip()
    pieces=tokens(text);possibilities=[];left=''
    for i,p in enumerate(pieces[:-1],1):
        left+=p;right=''.join(pieces[i:]);a=left.rstrip();b=right.lstrip()
        if not a or not b or b[0] in '，。！？；：、,.!?;:':continue
        if width(a)>max_width or width(b)>max_width:continue
        penalty=abs(width(a)-width(b))
        if a[-1] in '，；：,;:':penalty-=8
        if a[-1] in '的和与及在':penalty+=8
        possibilities.append((penalty,a,b))
    if not possibilities:raise ValueError('Caption cannot fit two complete-word lines: '+text)
    _,a,b=min(possibilities);return a+'\n'+b

def cues(text,max_width=24):
    display,weights=normalize(text);parts=[];start=0;end=0
    # Prefer clause boundaries; only an overlong clause uses dictionary words.
    clauses=list(re.finditer(r'[^，。！？；：,!?;:]+[，。！？；：,!?;:]?|[，。！？；：,!?;:]',display))
    for clause in clauses:
        a,b=clause.span()
        if end>start and width(display[start:b])>max_width:parts.append((start,end));start=a
        if width(display[a:b])>max_width:
            if end>start:parts.append((start,end))
            cursor=a;piece_start=a
            for token in tokens(display[a:b]):
                if cursor>piece_start and width(display[piece_start:cursor]+token)>max_width:
                    parts.append((piece_start,cursor));piece_start=cursor
                cursor+=len(token)
            start=piece_start;end=cursor
        else:end=b
    if end>start:parts.append((start,end))
    if not parts:parts=[(0,len(display))]
    # Avoid flashing a tiny tail or a short transition such as “英国方面，”.
    for i in range(1,len(parts)):
        a,mid=parts[i-1];_,b=parts[i]
        if min(width(display[a:mid]),width(display[mid:b]))>=6:continue
        cursor=a;choices=[]
        for token in tokens(display[a:b])[:-1]:
            cursor+=len(token);left=display[a:cursor].rstrip();right=display[cursor:b].lstrip()
            if not left or not right or right[0] in '，。！？；：、,.!?;:':continue
            wa,wb=width(left),width(right)
            if min(wa,wb)<6 or max(wa,wb)>max_width:continue
            score=abs(wa-wb)-(3 if left[-1] in '，；：,;:' else 0)
            choices.append((score,cursor))
        if choices:
            split=min(choices)[1];parts[i-1]=(a,split);parts[i]=(split,b)
    output=[];queue=list(parts)
    while queue:
        a,b=queue.pop(0)
        try:
            if width(display[a:b])>max_width:raise ValueError('Single caption line too wide')
            lines=display[a:b].strip()
        except ValueError:
            boundaries=[a+m.end() for m in re.finditer(r'[，；：,;:]',display[a:b]) if 0<m.end()<b-a]
            if not boundaries:
                pos=a;boundaries=[]
                for token in tokens(display[a:b])[:-1]:pos+=len(token);boundaries.append(pos)
            if not boundaries:raise
            split=min(boundaries,key=lambda p:abs(width(display[a:p])-width(display[p:b])))
            queue[:0]=[(a,split),(split,b)];continue
        output.append(dict(text=lines,weight=sum(weights[a:b]),display=display[a:b]))
    return output

def sentence_captions(sentence):
    pieces=cues(sentence['text']);total=sum(x['weight'] for x in pieces);offset=0;output=[]
    for piece in pieces:
        start=sentence['start']+(sentence['end']-sentence['start'])*offset/total;offset+=piece['weight']
        end=sentence['start']+(sentence['end']-sentence['start'])*offset/total
        output.append(dict(text=piece['text'],start=start,end=end))
    return output
