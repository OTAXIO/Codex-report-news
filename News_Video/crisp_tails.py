"""Pitch-preserving compression of detected voiced releases, with provenance."""
import argparse, copy, json, os, re, shutil, wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent

def read_wav(path):
    with wave.open(str(path),'rb') as h:
        if h.getnchannels()!=1 or h.getsampwidth()!=2:raise ValueError('Mono PCM16 required')
        return np.frombuffer(h.readframes(h.getnframes()),dtype='<i2').astype(np.float32)/32768,h.getframerate()

def write_wav(path,audio,rate):
    with wave.open(str(path),'wb') as h:
        h.setnchannels(1);h.setsampwidth(2);h.setframerate(rate)
        h.writeframes(np.round(np.clip(audio,-1,1-1/32768)*32768).astype('<i2').tobytes())

def crisp_release(audio,rate,stretch_factor=1.6):
    from librosa.effects import time_stretch
    x=np.asarray(audio,dtype=np.float32);frame=max(1,int(.025*rate));hop=max(1,int(.01*rate))
    report=dict(applied=False,source_samples=len(x),processed_samples=len(x),factor=stretch_factor)
    if len(x)<int(.5*rate):return x.copy(),report
    starts=np.arange(0,len(x)-frame+1,hop)
    rms=np.array([np.sqrt(np.mean(x[p:p+frame]**2)) for p in starts])
    peak=float(rms.max())
    if peak<1e-5:return x.copy(),report
    # Activity threshold determines silence endpoint, not a final-word boundary.
    active=np.flatnonzero(rms>max(peak*.04,10**(-48/20)))
    if not len(active):return x.copy(),report
    acoustic_end=min(len(x),int(starts[active[-1]]+frame))
    endpoint=min(len(x),acoustic_end+int(.045*rate))
    voiced=[]
    for p,level in zip(starts,rms):
        if p<acoustic_end-int(.9*rate) or p>=acoustic_end or level<peak*.10:continue
        segment=x[p:p+frame];segment=segment-segment.mean();segment=segment[::max(1,rate//16000)]
        rs=rate/max(1,rate//16000)
        spectrum=np.fft.rfft(segment,n=2**int(np.ceil(np.log2(len(segment)*2))))
        ac=np.fft.irfft(spectrum*np.conj(spectrum))[:len(segment)]
        lo=max(1,int(rs/450));hi=min(len(ac)-1,int(rs/70))
        periodic=float(ac[lo:hi].max()/max(ac[0],1e-12)) if hi>lo else 0.
        if periodic>=.42:voiced.append(int(p))
    voice_end=min(acoustic_end,voiced[-1]+frame) if voiced else acoustic_end
    # Only the terminal voiced run: preserve its attack, all earlier speech,
    # and any final unvoiced consonant. No word/character timing is claimed.
    run_start=voiced[-1] if voiced else voice_end
    for p in reversed(voiced[:-1]):
        if run_start-p>int(.035*rate):break
        run_start=p
    start=max(run_start+int(.035*rate),voice_end-int(.40*rate))
    method='terminal_voiced_run'
    if voice_end-start<int(.14*rate):
        # Breathy endings can have intermittent pitch and no stable voiced run.
        # Compress the terminal activity window instead of claiming syllable
        # alignment. All its content remains; this is not a fixed-tail cut.
        voice_end=acoustic_end
        start=max(0,voice_end-int(.32*rate))
        method='terminal_activity_window'
    region=x[start:voice_end]
    compressed=time_stretch(region,rate=stretch_factor,n_fft=512,hop_length=128).astype(np.float32)
    # Crossfade original edges into the shorter vowel to avoid phase clicks.
    blend=min(int(.012*rate),len(compressed)//4)
    w=np.linspace(0,1,blend,dtype=np.float32)
    compressed[:blend]=region[:blend]*(1-w)+compressed[:blend]*w
    compressed[-blend:]=compressed[-blend:]*(1-w)+region[-blend:]*w
    # Audible voiced-release gain, rather than only fading following silence.
    release=min(len(compressed),int(.13*rate))
    compressed[-release:]*=np.linspace(1.,.60,release,dtype=np.float32)
    suffix=x[voice_end:endpoint].copy()
    if len(suffix):suffix*=np.linspace(.60,0.,len(suffix),dtype=np.float32)
    else:compressed[-min(int(.008*rate),len(compressed)):]*=np.linspace(1,0,min(int(.008*rate),len(compressed)),dtype=np.float32)
    y=np.concatenate([x[:start],compressed,suffix])
    report.update(applied=True,method=method,processed_samples=len(y),voiced_region_start=start/rate,voiced_region_end=voice_end/rate,source_voiced_seconds=len(region)/rate,processed_voiced_seconds=len(compressed)/rate,retained_post_activity_seconds=(endpoint-acoustic_end)/rate,removed_seconds=(len(x)-len(y))/rate,terminal_gain=.60,prefix_samples_unchanged=start)
    return y,report

def process(source_id,target_id):
    os.environ.update(NUMBA_CACHE_DIR=str(ROOT/'.cache/numba'),MPLCONFIGDIR=str(ROOT/'.cache/mpl'),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    source=ROOT/'episodes'/source_id;target=ROOT/'episodes'/target_id
    target.mkdir(exist_ok=True)
    meta=json.loads((source/'narration.json').read_text(encoding='utf-8'))
    if meta.get('crisp_release'):raise ValueError('Refuse to compress already processed audio twice')
    src=source/'narration.wav' if source.resolve()==target.resolve() else source/'narration_strong.wav'
    if not src.exists():src=source/'narration.wav'
    audio,rate=read_wav(src)
    old_soft,_=read_wav(source/'narration.wav')
    ep=json.loads((source/'episode.json').read_text(encoding='utf-8'));ep['id']=target_id
    (target/'episode.json').write_text(json.dumps(ep,ensure_ascii=False,indent=2),encoding='utf-8')
    if source.resolve()!=target.resolve():shutil.copyfile(source/'script.txt',target/'script.txt')
    shutil.copyfile(src,target/'narration_source.wav')
    ids=[]
    for scene in ep['scenes']:
        ids.extend([scene['id']]*len([p for p in re.split(r'(?<=[。！？!?])\s*|(?<=\.)\s+|\n+',scene['narration']) if p.strip()]))
    if len(ids)!=len(meta['sentences']):raise ValueError('Scene and voice sentence count mismatch')
    original_timings={'sentences':[{'scene_id':key} for key in ids]}
    cursor=0;current=0;gap=np.zeros(int(rate*meta['job']['pause']),dtype=np.float32)
    parts=[];sentences=[];timings=[];comparisons=[];reports=[]
    for i,s in enumerate(meta['sentences']):
        count=s['processed_samples'];x=audio[cursor:cursor+count]
        y,report=crisp_release(x,rate);report.update(index=i,text=s['sentence']);reports.append(report)
        record=copy.deepcopy(s);record.pop('soft_release',None);record['crisp_release']=report
        record['mode']='strong+crisp';record['processed_samples']=len(y);record['removed_seconds']=record['raw_samples']/rate-len(y)/rate
        sentences.append(record);parts.append(y)
        timings.append(dict(text=s['sentence'],scene_id=original_timings['sentences'][i]['scene_id'],start=current,end=current+len(y)/rate,cleanup='strong+crisp'))
        if i in (0,5,23):comparisons.extend([old_soft[cursor:cursor+count],np.zeros(int(.6*rate),dtype=np.float32),y,np.zeros(int(1.*rate),dtype=np.float32)])
        current+=len(y)/rate
        if i+1<len(meta['sentences']):parts.append(gap);current+=len(gap)/rate
        cursor+=count+(len(gap) if i+1<len(meta['sentences']) else 0)
    if cursor!=len(audio):raise ValueError('Source sentence frame mapping mismatch')
    merged=np.concatenate(parts);write_wav(target/'narration.wav',merged,rate)
    write_wav(target/'tail-comparison-old-new.wav',np.concatenate(comparisons),rate)
    meta.pop('soft_release',None);meta.update(sentences=sentences,seconds=len(merged)/rate,output_path=str(target/'narration.wav'),postprocess_source=str(target/'narration_source.wav'),crisp_release=dict(source_episode=source_id,factor=1.6,max_voiced_window_seconds=.40,applied_phrases=sum(r['applied'] for r in reports)))
    meta['job'].update(output_file=str(target/'narration.wav'),text_file=str(target/'script.txt'))
    for name,data in [('narration.json',meta),('tail-processing.json',reports),('timings.json',dict(sample_rate=rate,duration=len(merged)/rate,sentences=timings))]:
        (target/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(seconds=meta['seconds'],processing=meta['crisp_release'],reports=reports),ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('target');a=p.parse_args();process(a.source,a.target)
