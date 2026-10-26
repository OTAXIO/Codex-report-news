"""Offline local ASR timestamps for sentence-ending diagnosis and protection."""
import argparse, json, os, sys, wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from project_paths import workspace_root
ENGINE=Path('D:/others/TOOLS/GPT-SoVITS-v2pro-20250604')
sys.path.insert(0,str(workspace_root(ROOT)/'Voice_Generate/tools'))
from common import environment

def analyze(episode_id):
    out=ROOT/'episodes'/episode_id
    os.environ.update(environment(ENGINE,out))
    for p in [ENGINE,ENGINE/'GPT_SoVITS',ENGINE/'GPT_SoVITS/eres2net']:sys.path.insert(0,str(p))
    import numpy as np, librosa, torch
    from funasr import AutoModel
    torch.set_num_threads(4)
    model=AutoModel(model=str(ENGINE/'tools/asr/models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'),disable_update=True,device='cuda',disable_pbar=True)
    meta=json.loads((out/'narration.json').read_text(encoding='utf-8'))
    path=out/'narration_strong.wav'
    if not path.exists():path=out/'narration.wav'
    with wave.open(str(path),'rb') as h:
        rate=h.getframerate();audio=np.frombuffer(h.readframes(h.getnframes()),dtype='<i2').astype(np.float32)/32768
    cursor=0;rows=[];gap=int(rate*meta['job']['pause'])
    for i,s in enumerate(meta['sentences']):
        count=s['processed_samples'];clip=audio[cursor:cursor+count]
        asr=model.generate(input=librosa.resample(clip,orig_sr=rate,target_sr=16000),batch_size_s=60,disable_pbar=True)[0]
        frame=int(.02*rate);hop=int(.01*rate)
        starts=np.arange(0,len(clip)-frame+1,hop)
        rms=np.array([np.sqrt(np.mean(clip[p:p+frame]**2)) for p in starts])
        peak=float(rms.max());active=np.flatnonzero(rms>peak*.05)
        acoustic_end=float((starts[active[-1]]+frame)/rate) if len(active) else 0
        row=dict(index=i,text=s['sentence'],asr=asr.get('text'),timestamps=asr.get('timestamp'),seconds=count/rate,acoustic_end=acoustic_end)
        rows.append(row)
        (out/'tail-analysis.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(row,ensure_ascii=False),flush=True)
        cursor+=count+(gap if i+1<len(meta['sentences']) else 0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');analyze(p.parse_args().episode)
