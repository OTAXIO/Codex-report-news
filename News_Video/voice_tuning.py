"""Soften only quiet phrase releases; never remove samples or alter pitch."""
import json, shutil, wave
from pathlib import Path
import numpy as np

def soften_release(audio,rate):
    y=np.array(audio,dtype=np.float32,copy=True)
    report={'applied':False,'seconds':0.,'gain_at_end':1.}
    frame=max(1,int(.02*rate));hop=max(1,int(.01*rate))
    if len(y)<frame*10:return y,report
    starts=np.arange(0,len(y)-frame+1,hop)
    rms=np.array([np.sqrt(np.mean(y[p:p+frame]**2)) for p in starts])
    peak=float(rms.max())
    if peak<1e-5:return y,report
    tail_rms=float(np.sqrt(np.mean(y[-int(.08*rate):]**2)))
    # Loud final vowels/consonants are protected. The new reference controls
    # prosody; this extra pass treats low-volume release/breath only.
    if tail_rms>peak*.32:return y,report
    voiced_level=np.flatnonzero(rms>=peak*.25)
    if not len(voiced_level):return y,report
    start=max(int(starts[voiced_level[-1]]+frame+.02*rate),len(y)-int(.14*rate))
    if start>=len(y)-int(.03*rate):return y,report
    y[start:]*=np.linspace(1.,.15,len(y)-start,dtype=np.float32)
    fade=min(int(.008*rate),len(y)-start)
    y[-fade:]*=np.linspace(1.,0.,fade,dtype=np.float32)
    report.update(applied=True,seconds=(len(y)-start)/rate,gain_at_end=.15)
    return y,report

def soften_file(wav_path,metadata_path):
    wav_path=Path(wav_path);metadata_path=Path(metadata_path)
    meta=json.loads(metadata_path.read_text(encoding='utf-8'))
    if meta.get('soft_release'):raise ValueError('Refuse to soften the same audio twice')
    with wave.open(str(wav_path),'rb') as handle:
        params=handle.getparams()
        if params.sampwidth!=2 or params.nchannels!=1:raise ValueError('Expected mono PCM16 audio')
        audio=np.frombuffer(handle.readframes(params.nframes),dtype='<i2').astype(np.float32)/32768
    cursor=0;gap=int(params.framerate*float(meta['job']['pause']));reports=[]
    for i,s in enumerate(meta['sentences']):
        count=s['processed_samples'];processed,report=soften_release(audio[cursor:cursor+count],params.framerate)
        audio[cursor:cursor+count]=processed;s['soft_release']=report;reports.append(report)
        cursor+=count+(gap if i+1<len(meta['sentences']) else 0)
    if cursor!=len(audio):raise ValueError('Audio metadata frame mismatch')
    backup=wav_path.with_name(wav_path.stem+'_strong.wav');shutil.copyfile(wav_path,backup)
    with wave.open(str(wav_path),'wb') as handle:
        handle.setparams(params);handle.writeframes(np.round(np.clip(audio,-1,1-1/32768)*32768).astype('<i2').tobytes())
    meta['soft_release']={'applied_phrases':sum(r['applied'] for r in reports),'sample_count_unchanged':True,'strong_backup':str(backup),'max_release_seconds':.14}
    metadata_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    return meta['soft_release']
