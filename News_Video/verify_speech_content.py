"""Local ASR/content gate; forced alignment is not proof of synthesized content."""
import argparse,difflib,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def comparable(text):return re.sub(r'[^\u4e00-\u9fffa-z0-9]','',text.lower())
def lexical_asr_text(text,readings):
    # Compare only explicit whole-word TTS homophones. This is not a tone
    # check and must never normalize arbitrary characters or ASR mistakes.
    for word,value in sorted(readings.items(),key=lambda row:len(row[0]),reverse=True):
        text=text.replace(value,word)
    return text
def compare_sentence(expected,heard,seconds):
    expected=comparable(expected);heard=comparable(heard)
    similarity=difflib.SequenceMatcher(None,expected,heard,autojunk=False).ratio()
    problems=[]
    if not heard or similarity<.65:problems.append('missing_or_changed_speech')
    if seconds>max(12,len(expected)/1.4):problems.append('abnormally_long_sentence')
    return dict(similarity=similarity,seconds=seconds,problems=problems)

def validate_review(directory):
    directory=Path(directory);report=json.loads((directory/'audio-content-review.json').read_text(encoding='utf-8'))
    if report.get('ok') is not True:raise ValueError('Speech content review did not pass')
    if report.get('narration_sha256')!=digest(directory/'narration.wav') or report.get('script_sha256')!=digest(directory/'spoken_script.txt'):raise ValueError('Speech content review is stale')
    timing=json.loads((directory/'timings.json').read_text(encoding='utf-8'))
    if len(report.get('sentences',[]))!=len(timing['sentences']):raise ValueError('Not every spoken sentence was checked')
    if any('aligned_cues' not in s for s in timing['sentences']):raise ValueError('Captions need final-PCM timestamp alignment')
    alignment=json.loads((directory/'caption-alignment.json').read_text(encoding='utf-8'))
    if alignment.get('narration_sha256')!=digest(directory/'narration.wav') or len(alignment['sentences'])!=len(timing['sentences']):raise ValueError('Caption alignment is stale')
    if any(a['cues']!=s['aligned_cues'] for a,s in zip(alignment['sentences'],timing['sentences'])):raise ValueError('Caption timeline differs from checked alignment')
    return report

def run(episode):
    import os,sys
    sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'../../Voice_Generate/tools'))
    from pronunciation import spoken_text
    from speech_text import prepare_text,READINGS
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    import torch,soundfile as sf,numpy as np
    from scipy.signal import resample_poly
    from funasr import AutoModel
    directory=ROOT/'episodes'/episode
    if not directory.resolve().is_relative_to((ROOT/'episodes').resolve()) or (directory/'release.json').exists():raise ValueError('Use an unarchived working episode')
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'));engine=Path(config['voice']['engine'])
    model_path=engine/'tools/asr/models/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'
    if not (model_path/'model.pt').is_file():raise ValueError('Existing local ASR model missing; do not silently skip')
    torch.set_num_threads(4);model=AutoModel(model=str(model_path),device='cpu',disable_update=True,disable_pbar=True)
    timing=json.loads((directory/'timings.json').read_text(encoding='utf-8'));audio,sr=sf.read(directory/'narration.wav',dtype='float32')
    if audio.ndim!=1:raise ValueError('Expected mono narration')
    scratch=directory/'speech-content-check';scratch.mkdir(exist_ok=True);rows=[]
    for i,sentence in enumerate(timing['sentences']):
        samples=audio[round(sentence['start']*sr):round(sentence['end']*sr)]
        wav=scratch/f'{i:03}.wav';sf.write(wav,resample_poly(samples,16000,sr),16000)
        results=model.generate(input=str(wav),disable_pbar=True)
        heard=results[0].get('text','') if results else ''
        expected_spoken=prepare_text(spoken_text(sentence['text'],config['voice'].get('pronunciations',{})))
        normalized=lexical_asr_text(heard,READINGS)
        normalized_expected=lexical_asr_text(expected_spoken,READINGS)
        row=compare_sentence(normalized_expected,normalized,len(samples)/sr);row.update(index=i,expected=sentence['text'],expected_spoken=expected_spoken,expected_lexical_normalized=normalized_expected,heard=heard,heard_lexical_normalized=normalized);rows.append(row)
    score=difflib.SequenceMatcher(None,comparable(''.join(r['expected_lexical_normalized'] for r in rows)),comparable(''.join(r['heard_lexical_normalized'] for r in rows)),autojunk=False).ratio()
    clipping=float(np.mean(np.abs(audio)>=.999));ok=not any(r['problems'] for r in rows) and score>=.9 and clipping<.0001 and bool(np.isfinite(audio).all())
    report=dict(ok=ok,method='local per-sentence ASR plus duration and waveform checks',narration_sha256=digest(directory/'narration.wav'),script_sha256=digest(directory/'spoken_script.txt'),overall_similarity=score,clipped_sample_fraction=clipping,sentences=rows,subjective_listening_performed=False)
    (directory/'audio-content-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(ok=ok,overall_similarity=score,sentences=len(rows)),ensure_ascii=False))
    if not ok:raise ValueError('Speech content gate failed; regenerate affected speech, not trim active audio or force fake timestamps')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');args=p.parse_args();run(args.episode)
