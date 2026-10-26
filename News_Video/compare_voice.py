"""Create listening comparisons from actual phrase boundaries, not guessed cuts."""
import argparse, json, wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent

def load_phrases(episode):
    directory=ROOT/'episodes'/episode
    meta=json.loads((directory/'narration.json').read_text(encoding='utf-8'))
    with wave.open(str(directory/'narration.wav'),'rb') as h:
        if h.getnchannels()!=1 or h.getsampwidth()!=2:raise ValueError('Expected mono PCM16')
        rate=h.getframerate();audio=np.frombuffer(h.readframes(h.getnframes()),dtype='<i2')
    cursor=0;phrases=[];gap=int(rate*meta['job']['pause'])
    for i,s in enumerate(meta['sentences']):
        n=s['processed_samples'];phrases.append((s['sentence'],audio[cursor:cursor+n]))
        cursor+=n+(gap if i+1<len(meta['sentences']) else 0)
    if cursor!=len(audio):raise ValueError('Phrase frame boundaries do not match audio')
    return rate,phrases

def compare(old,new):
    rate,a=load_phrases(old);rate_b,b=load_phrases(new)
    if rate!=rate_b:raise ValueError('Sample rates differ')
    parts=[];manifest=[]
    for i in (0,7,23):
        if a[i][0]!=b[i][0]:raise ValueError('Comparison texts must match')
        parts.extend([a[i][1],np.zeros(round(.7*rate),dtype='<i2'),b[i][1],np.zeros(rate,dtype='<i2')])
        manifest.append(dict(index=i,text=a[i][0],old_seconds=len(a[i][1])/rate,new_seconds=len(b[i][1])/rate,order='old then new'))
    output=ROOT/'episodes'/new/'voice-comparison-old-new.wav'
    with wave.open(str(output),'wb') as h:
        h.setnchannels(1);h.setsampwidth(2);h.setframerate(rate);h.writeframes(np.concatenate(parts).tobytes())
    output.with_suffix('.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(output)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('old');p.add_argument('new');a=p.parse_args();compare(a.old,a.new)
