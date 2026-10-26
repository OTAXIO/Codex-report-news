"""Apply explicit scene-end reading holds to PCM narration and sentence timing."""
import wave


def sentence_scene_ids(episode):
    import re
    return [scene['id'] for scene in episode['scenes']
            for text in re.split(r'(?<=[。！？!?])\s*|(?<=\.)\s+|\n+',scene['narration']) if text.strip()]


def apply_scene_holds(path, meta, episode, default_pause):
    ids=sentence_scene_ids(episode)
    if len(ids)!=len(meta['sentences']):raise ValueError('Sentence/scene mismatch before hold insertion')
    holds={s['id']:s['hold_after_seconds'] for s in episode['scenes'] if 'hold_after_seconds' in s}
    if not holds:return meta
    with wave.open(str(path),'rb') as source:
        params=source.getparams();data=source.readframes(source.getnframes())
    if params.sampwidth!=2 or params.comptype!='NONE':raise ValueError('Scene holds require PCM16 narration')
    rate=params.framerate;stride=params.sampwidth*params.nchannels
    cursor=0;chunks=[];adjustments=[]
    for i,(entry,sid) in enumerate(zip(meta['sentences'],ids)):
        samples=entry['processed_samples'];chunks.append(data[cursor*stride:(cursor+samples)*stride]);cursor+=samples
        if i+1==len(ids):break
        old=int(entry.get('pause_after_samples',round(default_pause*rate)))
        desired=round(holds[sid]*rate) if sid!=ids[i+1] and sid in holds else old
        if desired<0:raise ValueError('Negative scene hold')
        gap=data[cursor*stride:(cursor+old)*stride]
        chunks.append(gap[:desired*stride] if desired<=old else gap+b'\0'*((desired-old)*stride))
        cursor+=old;entry['pause_after_samples']=desired
        if desired!=old:adjustments.append(dict(after_scene=sid,old_samples=old,new_samples=desired))
    if cursor*stride!=len(data):raise ValueError('Audio/metadata sample count mismatch')
    combined=b''.join(chunks)
    with wave.open(str(path),'wb') as output:
        output.setparams(params);output.writeframes(combined)
    meta['seconds']=len(combined)/stride/rate
    meta.setdefault('scene_hold_adjustments',[]).extend(adjustments)
    return meta
