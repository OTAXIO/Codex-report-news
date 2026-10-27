"""Offline, speech-first looping music shared by Studio and MP4 rendering."""
import hashlib,json,math,subprocess,tempfile,wave
from pathlib import Path
import numpy as np

SAMPLE_RATE=48000
MIX_VERSION=4

def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()

def read_pcm(path):
    with wave.open(str(path),'rb') as f:
        if f.getsampwidth()!=2 or f.getframerate()!=SAMPLE_RATE or f.getnchannels()!=2:
            raise ValueError('Mix stems must be 48kHz stereo PCM16')
        return np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').reshape(-1,2).astype(np.float64)/32768

def write_pcm(path,audio):
    with wave.open(str(path),'wb') as f:
        f.setparams((2,2,SAMPLE_RATE,0,'NONE','not compressed'))
        f.writeframes(np.round(np.clip(audio,-1,1)*32767).astype('<i2').tobytes())

def loop_music(audio,frames,repeat_from_seconds=0):
    """Play the intro once; every subsequent pass starts at the given offset."""
    offset=round(float(repeat_from_seconds)*SAMPLE_RATE)
    if offset<0 or offset>=len(audio):raise ValueError('Music repeat offset must be inside the source track')
    if frames<=len(audio):return audio[:frames].copy()
    tail=audio[offset:];remaining=frames-len(audio)
    repeats=math.ceil(remaining/len(tail))
    return np.concatenate([audio,np.tile(tail,(repeats,1))[:remaining]])

def speech_first_mix(voice,music,policy):
    """Choose one fixed gain against representative speech, never ducking.

    Use the median active-window ratio, not the single quietest syllable. A
    minimum-window policy silences the whole music bed due to a weak tail.
    Pauses never turn music up; only the opening/closing fades vary the gain.
    """
    size=len(voice);window=9600
    if size!=len(music) or not size:raise ValueError('Stem lengths must match')
    gap=float(policy.get('reference_voice_gap_db',18))
    gate=10**(-35/20);caps=[];active=[]
    for start in range(0,size,window):
        end=min(start+window,size)
        vr=float(np.sqrt(np.mean(voice[start:end]**2)))
        mr=float(np.sqrt(np.mean(music[start:end]**2)))
        speaking=vr>=gate;active.append((start,end,vr,speaking))
        if speaking:caps.append(vr/(10**((gap+.5)/20)*max(mr,1e-12)))
    if not caps:raise ValueError('No audible narration; refuse a music-only news export')
    gain=min(1.,float(np.median(caps)))
    music=music*gain
    envelope=np.ones(size)
    fade=min(int(.35*SAMPLE_RATE),size//2)
    if fade:
        envelope[:fade]*=np.linspace(0,1,fade)
        envelope[-fade:]*=np.linspace(1,0,fade)
    music=music*envelope[:,None]
    peak_cap=10**(float(policy.get('music_peak_dbfs',-24))/20)
    peak=float(np.max(np.abs(music)))
    if peak>peak_cap:
        gain*=peak_cap/peak;music*=peak_cap/peak
    mixed=voice+music
    headroom=min(1.,10**(-1/20)/max(float(np.max(np.abs(mixed))),1e-12))
    voice*=headroom;music*=headroom;mixed*=headroom
    gaps=[]
    for start,end,_,speaking in active:
        if speaking:
            vr=float(np.sqrt(np.mean(voice[start:end]**2)))
            mr=float(np.sqrt(np.mean(music[start:end]**2)))
            if mr>1e-12:gaps.append(20*math.log10(vr/mr))
    report=dict(gain_mode='constant',ducking=False,constant_music_gain=gain,
                voice_gap_measure='active_window_median',
                reference_measured_voice_gap_db=float(np.median(gaps)) if gaps else None,
                analysis_window_ms=200,voice_activity_gate_dbfs=-35,
                active_voice_windows=sum(x[3] for x in active),
                minimum_measured_voice_gap_db=min(gaps) if gaps else None,
                music_peak_dbfs=20*math.log10(max(float(np.max(np.abs(music))),1e-12)),
                final_peak_dbfs=20*math.log10(max(float(np.max(np.abs(mixed))),1e-12)),headroom_gain=headroom)
    if not report['active_voice_windows']:raise ValueError('No audible narration; refuse a music-only news export')
    if gaps and np.median(gaps)<gap-.01:raise ValueError('Background music masks speech; mix rejected')
    return mixed,music,report

def ensure_soundtrack(root,episode,duration,ffmpeg=None):
    root=Path(root);episode=Path(episode)
    cfg=json.loads((root/'config.json').read_text(encoding='utf-8'))
    policy=cfg.get('background_music',{})
    narration=episode/'narration.wav'
    if not policy.get('enabled'):return narration
    receipt=episode/'release.json'
    if receipt.exists() and json.loads(receipt.read_text(encoding='utf-8')).get('published'):
        raise ValueError('Published soundtrack is immutable; use a new edition')
    target=float(policy.get('target_lufs',-32));gap=float(policy.get('reference_voice_gap_db',18))
    if not -50<=target<=-30 or not math.isfinite(gap) or gap<16 or not -60<=float(policy.get('music_peak_dbfs',-24))<=-24:
        raise ValueError('Unsafe background music levels; retain speech-first limits')
    if not math.isfinite(duration) or duration<=0:raise ValueError('Invalid soundtrack duration')
    source=(root/policy['file']).resolve()
    if not source.is_file():raise FileNotFoundError('Configured background music missing: '+str(source))
    source_hash=digest(source)
    if policy.get('sha256') and policy['sha256']!=source_hash:raise ValueError('Background music hash mismatch')
    identity=dict(version=MIX_VERSION,narration_sha256=digest(narration),music_sha256=source_hash,
                  duration=duration,policy=policy)
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    output=episode/'soundtrack.wav';report_path=episode/'audio-mix.json'
    if output.exists() and report_path.exists():
        previous=json.loads(report_path.read_text(encoding='utf-8'))
        if previous.get('cache_key')==key and previous.get('soundtrack_sha256')==digest(output):return output
    executable=str(ffmpeg or cfg.get('voice',{}).get('qwen3',{}).get('ffmpeg_executable') or 'ffmpeg')
    frames=round(duration*SAMPLE_RATE)
    repeat_from=float(policy.get('repeat_from_seconds',0))
    if not math.isfinite(repeat_from) or repeat_from<0:raise ValueError('Invalid music repeat offset')
    with tempfile.TemporaryDirectory(prefix='audio-mix-',dir=episode) as folder:
        folder=Path(folder);stems=[]
        source_frames=None
        for name,path,level in [('voice',narration,-16),('music',source,target)]:
            out=folder/(name+'.wav')
            args=[executable,'-y','-hide_banner','-loglevel','error']
            # loudnorm's TP range is -9..0. Normalize first, then apply a fixed
            # music attenuation rather than asking loudnorm for invalid -30 TP.
            filters=f'loudnorm=I=-16:TP=-2:LRA=7,volume={level+16}dB,aresample={SAMPLE_RATE}'
            if name=='voice':filters+=f',apad,atrim=end_sample={frames}'
            args+=['-i',str(path),'-vn','-af',filters,
                   '-ar',str(SAMPLE_RATE),'-ac','2','-c:a','pcm_s16le']
            if name=='voice':args+=['-t',str(duration)]
            args.append(str(out))
            subprocess.run(args,check=True,capture_output=True)
            pcm=read_pcm(out)
            if name=='music':
                source_frames=len(pcm);pcm=loop_music(pcm,frames,repeat_from)
            stems.append(pcm)
        mixed,music,levels=speech_first_mix(stems[0],stems[1],policy)
        temp=folder/'soundtrack.wav';write_pcm(temp,mixed);temp.replace(output)
    report=dict(enabled=True,cache_key=key,track=policy.get('title',source.name),music_sha256=source_hash,
                narration_sha256=identity['narration_sha256'],duration=len(mixed)/SAMPLE_RATE,
                loop_to_video_end=True,intro_play_count=1,repeat_from_seconds=repeat_from,
                source_duration_seconds=source_frames/SAMPLE_RATE,voice_target_lufs=-16,music_target_lufs=target,
                required_reference_voice_gap_db=gap,**levels,soundtrack_sha256=digest(output))
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return output

def validate_release_mix(episode,requirement,duration):
    """New editions pin the requested soundtrack; legacy exports stay resumable."""
    if not requirement:return
    episode=Path(episode);report_path=episode/'audio-mix.json';soundtrack=episode/'soundtrack.wav'
    if not report_path.is_file() or not soundtrack.is_file():raise ValueError('Required background music has not been mixed')
    report=json.loads(report_path.read_text(encoding='utf-8'))
    expected=dict(enabled=True,music_sha256=requirement['sha256'],repeat_from_seconds=requirement['repeat_from_seconds'],
                  intro_play_count=1,gain_mode='constant',ducking=False)
    if any(report.get(k)!=v for k,v in expected.items()):raise ValueError('Background music does not match the edition requirements')
    if abs(report.get('duration',0)-duration)>.001 or report.get('soundtrack_sha256')!=digest(soundtrack):
        raise ValueError('Soundtrack duration or hash mismatch')
    measure=requirement.get('voice_gap_measure','worst_window')
    metric='reference_measured_voice_gap_db' if measure=='active_window_median' else 'minimum_measured_voice_gap_db'
    if measure=='active_window_median' and report.get('voice_gap_measure')!=measure:raise ValueError('Wrong speech reference for music validation')
    required=requirement.get('reference_voice_gap_db',requirement.get('minimum_voice_gap_db',20))
    if report.get(metric,0)<required-.01 or report.get('music_peak_dbfs',0)>requirement.get('music_peak_dbfs',-24)+.01:
        raise ValueError('Background music speech-priority check failed')
