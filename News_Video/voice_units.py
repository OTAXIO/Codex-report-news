"""Contextual Qwen narration with a per-unit audio cache.

Mirrors Voice_Generate/tools/qwen_generate_context.py (which stays unmodified)
but only synthesizes paragraph units whose text or generation settings changed.
This is exact, not approximate: with consistent_unit_seed every unit is seeded
identically before generation, so a unit generated alone equals the same unit
generated inside a full run. Alignment still runs over the whole narration.
"""
import hashlib,json,subprocess,wave
from pathlib import Path

CACHE_KEYS=['model_path','reference','reference_text','qwen_language','seed','consistent_unit_seed','temperature','top_p','top_k',
            'subtalker_temperature','subtalker_top_p','subtalker_top_k','speech_rate','max_new_tokens','ffmpeg_executable']
# Qwen3-TTS emits 12.5 codec frames per second; a unit this close to the token
# cap did not end on its own (trailing silence or skipped speech).
FRAMES_PER_SECOND=12.5

UNITS_HELPER='''
import json,sys
sys.path.insert(0,sys.argv[1])
from prosody import synthesis_units
from speech_text import prepare_text
from audio_cleanup import read_local_text
job=json.load(open(sys.argv[2],encoding='utf-8-sig'))
sentences=synthesis_units(prepare_text(read_local_text(job['text_file']),job.get('pronunciation_readings')))
counts=job.get('context_group_sentence_counts') or [len(sentences)]
if sum(counts)!=len(sentences) or any(x<=0 for x in counts):raise SystemExit('Context grouping must cover every sentence exactly')
grouped=[];cursor=0
for count in counts:grouped.append(''.join(sentences[cursor:cursor+count]));cursor+=count
spoken='\\n\\n'.join(grouped)
open(sys.argv[3],'w',encoding='utf-8').write(spoken)
units=synthesis_units(prepare_text(read_local_text(sys.argv[3]),job.get('pronunciation_readings')),'paragraph',220)
print(json.dumps(dict(sentences=sentences,counts=counts,units=units),ensure_ascii=False))
'''

def unit_key(unit,raw_job):
    settings={k:raw_job.get(k) for k in CACHE_KEYS}
    return hashlib.sha256(json.dumps(dict(unit=unit,settings=settings),ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:32]

def read_wav(path):
    with wave.open(str(path),'rb') as w:return w.getparams(),w.readframes(w.getnframes())

def write_wav(path,params,frames):
    with wave.open(str(path),'wb') as w:
        w.setparams(params);w.writeframes(frames)

def generate(job,job_path,python,repository,env,log,cache_dir,flags=0):
    """Returns dict(units, reused, generated). Writes job['output_file'] like the original worker."""
    tools=Path(repository)/'tools';run=Path(job_path).parent/'context-source';run.mkdir(exist_ok=True)
    cache_dir=Path(cache_dir);cache_dir.mkdir(parents=True,exist_ok=True)
    spoken=run/'spoken.txt'
    plan=json.loads(subprocess.run([str(python),'-B','-c',UNITS_HELPER,str(tools),str(job_path),str(spoken)],env=env,check=True,
                                   capture_output=True,text=True,encoding='utf-8',creationflags=flags).stdout)
    sentences,counts,units=plan['sentences'],plan['counts'],plan['units']
    (run/'normalized-sentences.txt').write_text('\n'.join(sentences),encoding='utf-8')
    raw_job=dict(job,text_file=str(spoken),output_file=str(run/'context.wav'),synthesis_unit='paragraph',max_context_chars=220,
                 speech_rate=1.0,pause=0,max_new_tokens=int(job.get('context_max_new_tokens',1024)))
    keys=[unit_key(u,raw_job) for u in units]
    missing=[i for i,k in enumerate(keys) if not (cache_dir/(k+'.wav')).is_file()]
    log.write(f'@@VOICE_UNITS total={len(units)} reuse={len(units)-len(missing)} generate={len(missing)}\n');log.flush()
    if missing:
        subset=run/'missing.txt';subset.write_text('\n\n'.join(units[i] for i in missing),encoding='utf-8')
        sub_job=dict(raw_job,text_file=str(subset),output_file=str(run/'missing.wav'))
        sub_path=run/'missing-job.json';sub_path.write_text(json.dumps(sub_job,ensure_ascii=False,indent=2),encoding='utf-8')
        subprocess.run([str(python),'-u','-B',str(tools/'qwen_generate_job.py'),'--job',str(sub_path)],cwd=str(repository),env=env,check=True,
                       stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        meta=json.loads((run/'missing.json').read_text(encoding='utf-8'))
        made=[s['sentence'] for s in meta['sentences']]
        if made!=[units[i] for i in missing]:raise ValueError('Partial synthesis re-segmented the text; rerun after deleting '+str(cache_dir))
        params,frames=read_wav(run/'missing.wav');width=params.sampwidth*params.nchannels;cursor=0
        limit=raw_job['max_new_tokens']/FRAMES_PER_SECOND*.97;degenerate=[]
        for i,entry in zip(missing,meta['sentences']):
            size=entry['processed_samples']*width;chunk=frames[cursor:cursor+size];cursor+=size
            if entry['processed_samples']/meta['sample_rate']>=limit:
                degenerate.append(f'unit {i+1} ({entry["processed_samples"]/meta["sample_rate"]:.1f}s): {units[i][:40]}');continue
            write_wav(cache_dir/(keys[i]+'.wav'),params,chunk)
            (cache_dir/(keys[i]+'.json')).write_text(json.dumps(dict(entry,sample_rate=meta['sample_rate']),ensure_ascii=False),encoding='utf-8')
        if cursor!=len(frames):raise ValueError('Partial synthesis audio length does not match its unit metadata')
        if degenerate:raise ValueError('Voice unit hit the generation cap (did not finish); reword it, the other units stay cached: '+'; '.join(degenerate))
    entries=[];chunks=[];params=None;rate=None
    for k in keys:
        p,frames=read_wav(cache_dir/(k+'.wav'));entry=json.loads((cache_dir/(k+'.json')).read_text(encoding='utf-8'))
        if params and (p.framerate,p.sampwidth,p.nchannels)!=(params.framerate,params.sampwidth,params.nchannels):raise ValueError('Cached unit audio format differs')
        params=p;rate=entry.pop('sample_rate');chunks.append(frames);entries.append(entry)
    write_wav(run/'context.wav',params,b''.join(chunks))
    seconds=sum(e['processed_samples'] for e in entries)/rate
    context_meta=dict(backend='qwen3-tts',model_path=str(raw_job.get('model_path')),job=raw_job,sentences=entries,sample_rate=rate,seconds=seconds,
                      raw_seconds=sum(e['raw_samples'] for e in entries)/rate,inference_seconds=None,
                      input_sha256=hashlib.sha256(spoken.read_bytes()).hexdigest(),raw_path=None,output_path=str(run/'context.wav'),
                      voice_quality_approved=False,unit_cache=dict(keys=keys,generated=[i+1 for i in missing]))
    (run/'context.json').write_text(json.dumps(context_meta,ensure_ascii=False,indent=2),encoding='utf-8')
    aligned_job=dict(job,pause=float(job.get('pause',.4)),paragraph_pause=float(job.get('paragraph_pause',.6)),
                     scene_break_after=[sum(counts[:i+1])-1 for i in range(len(counts)-1)])
    aligned=run/'aligned-job.json';aligned.write_text(json.dumps(aligned_job,ensure_ascii=False,indent=2),encoding='utf-8')
    align_python=Path(job['alignment_python']);align_model=Path(job['alignment_model'])
    if not align_python.is_file() or not (align_model/'model.pt').is_file():raise ValueError('Local alignment runtime/model missing')
    subprocess.run([str(align_python),'-u','-B',str(tools/'context_alignment.py'),'--source',str(run/'context.wav'),'--source-meta',str(run/'context.json'),
                    '--text',str(run/'normalized-sentences.txt'),'--job',str(aligned),'--output',job['output_file'],'--fa-model',str(align_model)],
                   cwd=str(repository),env=env,check=True,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
    return dict(units=len(units),reused=len(units)-len(missing),generated=len(missing))

def seed_cache(run_dir,cache_dir):
    """Store units from an existing successful context-source run (context.wav + context.json) in the cache."""
    run=Path(run_dir);meta=json.loads((run/'context.json').read_text(encoding='utf-8'));raw_job=meta['job']
    params,frames=read_wav(run/'context.wav');width=params.sampwidth*params.nchannels;cursor=0;stored=0
    cache_dir=Path(cache_dir);cache_dir.mkdir(parents=True,exist_ok=True)
    for entry in meta['sentences']:
        size=entry['processed_samples']*width;key=unit_key(entry['sentence'],raw_job)
        write_wav(cache_dir/(key+'.wav'),params,frames[cursor:cursor+size]);cursor+=size
        (cache_dir/(key+'.json')).write_text(json.dumps(dict(entry,sample_rate=meta['sample_rate']),ensure_ascii=False),encoding='utf-8');stored+=1
    if cursor!=len(frames):raise ValueError('context.wav length does not match context.json units')
    return stored
