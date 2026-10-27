import os,sys,json,re,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root));sys.path.insert(0,str(root/'../../Voice_Generate/tools'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
import torch,soundfile as sf
from funasr import AutoModel
from context_alignment import alignment_tokens
from caption_layout import cues
from pronunciation import spoken_text
import news_video

import argparse
p=argparse.ArgumentParser();p.add_argument('episode');args=p.parse_args()
target=root/'episodes'/args.episode
if not target.resolve().is_relative_to((root/'episodes').resolve()) or (target/'release.json').exists():raise ValueError('Use an unarchived working episode')
timing=json.loads((target/'timings.json').read_text(encoding='utf-8'));wave,sr=sf.read(target/'narration.wav',dtype='float32');torch.set_num_threads(4)
model=AutoModel(model=str(root/'../../Voice_Generate/models/fa-zh'),device='cpu',disable_update=True,disable_pbar=True)
audit=[]
for i,sentence in enumerate(timing['sentences']):
    parts=cues(sentence['text']);sets=[alignment_tokens(spoken_text(p['text'],news_video.config()['voice'].get('pronunciations',{}))) for p in parts]
    tokens=[v for part in sets for v in part];start=round(sentence['start']*sr);end=round(sentence['end']*sr)
    wav=target/f'caption-align-{i}.wav';txt=wav.with_suffix('.txt');sf.write(wav,wave[start:end],sr);txt.write_text('utterance '+' '.join(tokens),encoding='utf-8')
    result=model.generate(input=(str(wav),str(txt)),data_type=('sound','text'),disable_pbar=True)[0]['timestamp']
    assert len(result)==len(tokens)
    boundaries=[max(sentence['start'],sentence['start']+result[0][0]/1000)];cursor=0
    for subset in sets[:-1]:
        cursor+=len(subset);boundaries.append(sentence['start']+(result[cursor-1][1]+result[cursor][0])/2000)
    boundaries.append(min(sentence['end'],sentence['start']+result[-1][1]/1000))
    sentence['aligned_cues']=[dict(text=p['text'],start=boundaries[j],end=boundaries[j+1]) for j,p in enumerate(parts)]
    audit.append(dict(sentence=i,timestamps=result,tokens=tokens,cues=sentence['aligned_cues']))
(target/'timings.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'caption-alignment.json').write_text(json.dumps(dict(method='local forced alignment on final PCM per caption; separately ASR checked',narration_sha256=hashlib.sha256((target/'narration.wav').read_bytes()).hexdigest(),sentences=audit),ensure_ascii=False,indent=2),encoding='utf-8')
print('aligned',len(audit),'sentences')
