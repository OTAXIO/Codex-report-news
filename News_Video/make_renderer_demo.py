"""Offline comparison from archived material; never collect, mark used or upload."""
import argparse,copy,json,subprocess,wave,shutil,re
from pathlib import Path
from layout_policy import prepare_overview
from renderer_backends import load,save
from project_paths import release_root

ROOT=Path(__file__).resolve().parent

def make(suffix=''):
    if not re.fullmatch(r'[a-z0-9-]{0,30}',suffix):raise ValueError('Unsafe demo suffix')
    releases=release_root(ROOT);ff=load(ROOT/'config.json')['voice']['qwen3']['ffmpeg_executable']
    selections=[('2026_10_27_night','overview',None),('2026_10_27_night','coderabbit',None),
                ('previews/qwen3-voice-demo-context-v6','tibo-reminder',None),
                ('2026_10_27_temporary_163327_9743c6890cfac08bc51f','eth-research',2),
                ('2026_10_27_night','changchun-lhasa',None),('2026_10_27_night','nepal-water',None)]
    staging=ROOT/'.cache/renderer-demo-source';staging.mkdir(parents=True,exist_ok=True)
    scenes=[];sentences=[];chunks=[];provenance=[];offset=0
    for index,(folder,sid,count) in enumerate(selections):
        directory=releases/folder;ep=load(directory/'episode.json');timing=load(directory/'timings.json')
        scene=copy.deepcopy(next(s for s in ep['scenes'] if s['id']==sid))
        parts=[p for p in timing['sentences'] if p['scene_id']==sid]
        if count:parts=parts[:count]
        start=parts[0]['start'];end=min(timing['duration'],parts[-1]['end']+(.6 if index else 2))
        chunk=staging/f'{index}.wav'
        subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-i',str(directory/'narration.wav'),'-af',f'atrim=start={start}:end={end},asetpts=PTS-STARTPTS','-ar','24000','-ac','1','-c:a','pcm_s16le',str(chunk)],check=True)
        with wave.open(str(chunk),'rb') as w:audio=w.readframes(w.getnframes());length=len(audio)/2/24000
        chunks.append(audio)
        for part in parts:
            item=dict(part,start=part['start']-start+offset,end=part['end']-start+offset)
            if 'aligned_cues' in part:item['aligned_cues']=[dict(c,start=c['start']-start+offset,end=c['end']-start+offset) for c in part['aligned_cues']]
            sentences.append(item)
        scene['narration']=''.join(p['text'] for p in parts)
        if sid=='tibo-reminder':
            scene.update(speaker_name='tibo',speaker_identity='OpenAI · Codex / ChatGPT 团队',claim_type='experience')
        if sid=='eth-research':scene.update(scene_type='temporary_news',section='AI 动态',title='OpenAI 研究发布｜历史快讯片段')
        if sid=='changchun-lhasa':scene['diagram']=dict(type='route',stops=['长春','西安','拉萨'],source_url=scene['source_url'])
        if sid=='nepal-water':scene['diagram']=dict(type='metrics',source_url=scene['source_url'],items=[dict(value='6',unit='个流域',label='预警建设规划'),dict(value='4',unit='座冰湖',label='拟降低水位')])
        scenes.append(scene);provenance.append(dict(scene_id=sid,archive=str(directory),source_start=start,source_end=end,output_start=offset,output_end=offset+length))
        offset+=length
    episode=dict(id='demo',producer='Codex current conversation',edition_date='2026-10-27',edition_slot='preview',scenes=scenes,
                 title='视觉引擎验收 · 历史素材',footer_tag='历史素材 · 视觉验收 · 不投稿',upload_enabled=False,auto_publish=False,
                 usage_tracking=False,review_status='local_sample_renderer_comparison')
    scenes[0]['overview_generated']=True;prepare_overview(episode)
    ids=[]
    for backend,template,label in [('multiplane','editorial','a'),('multiplane','graphic','b'),('hyperframes','legacy','legacy')]:
        eid='renderer-demo-20261027-'+label+('-'+suffix if suffix else '');ids.append(eid);folder=ROOT/'episodes'/eid
        if (folder/'sample.mp4').exists() or (folder/'release.json').exists():raise ValueError('Completed demo already exists; use a new revision')
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'captions.json').unlink(missing_ok=True)  # Recreate only this unrendered technical fixture's derived captions.
        with wave.open(str(folder/'narration.wav'),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b''.join(chunks))
        ep=copy.deepcopy(episode);ep['id']=eid
        save(folder/'episode.json',ep);save(folder/'timings.json',dict(sample_rate=24000,duration=offset,sentences=sentences))
        save(folder/'demo-provenance.json',dict(historical_layout_comparison=True,clips=provenance))
        (folder/'script.txt').write_text('\n'.join(s['narration'] for s in ep['scenes']),encoding='utf-8')
        from build_film import build
        build(eid,backend,template if backend=='multiplane' else None)
    print(json.dumps(dict(episodes=ids,duration=offset),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--suffix',default='');make(p.parse_args().suffix)
