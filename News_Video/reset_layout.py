"""Lossless original-post pagination; reviewed Chinese narration stays separate."""
import re

def original_pages(text):
    # Preserve all characters, including newlines. Layout never truncates a post.
    pages=[];page=''
    for token in re.findall(r'[A-Za-z0-9][A-Za-z0-9_:/?.#=&%+\-]*|\s+|.',text):
        if page and len(page)+len(token)>140:pages.append(page);page=''
        while len(token)>140:pages.append(token[:140]);token=token[140:]
        page+=token
    if page:pages.append(page)
    if ''.join(pages)!=text:raise ValueError('Original post pagination lost characters')
    return pages

def detailed_pages(original,review):
    narration=review['narration'].strip()
    sentences=[s for s in re.split(r'(?<=[。！？!?])\s*',narration) if s.strip()]
    if len(narration)<120 or len(sentences)<3:raise ValueError('Reset narration needs a detailed attributed explanation, not one sentence (at least 120 characters and 3 sentences); final video must exceed 30 seconds')
    pages=original_pages(original)
    if len(sentences)<len(pages):raise ValueError('Provide enough reviewed narration for each readable full-post page')
    return [(page,''.join(sentences[i*len(sentences)//len(pages):(i+1)*len(sentences)//len(pages)])) for i,page in enumerate(pages)]

def context_groups(scenes):
    """Keep detailed reset explanations in short contexts without cutting speech."""
    counts=[]
    for scene in scenes:
        count=0;length=0
        for sentence in (s for s in re.split(r'(?<=[。！？!?])\s*|(?<=\.)\s+|\n+',scene['narration']) if s.strip()):
            if count and length+len(sentence)>80:counts.append(count);count=0;length=0
            count+=1;length+=len(sentence)
        if count:counts.append(count)
    return counts
