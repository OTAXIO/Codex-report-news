"""Render the clean, held news cards through HyperFrames snapshots + FFmpeg.

Workaround for Windows Chrome --version preflight in hyperframes 0.8.196.
Captions are actual HTML pixels, never a separate subtitle stream.
"""
import json, os, subprocess
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NODE=Path('C:/Users/35303/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
CLI=ROOT/'node_modules/hyperframes/bin/hyperframes.mjs'
FFMPEG=Path('D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/ffmpeg.exe')
def render(episode_id):
    episode=ROOT/'episodes'/episode_id
    if (episode/'release.json').exists():raise ValueError('Published edition is archived; create a new revision before rendering')
    timing=json.loads((episode/'timings.json').read_text(encoding='utf-8'))
    captions=json.loads((episode/'captions.json').read_text(encoding='utf-8'))
    scenes=json.loads((episode/'scene-timings.json').read_text(encoding='utf-8'))
    # Held cards: every caption and scene boundary is retained; entrance motion
    # stays available in the editable preview, final sample uses direct cuts.
    progress_path=episode/'progress.json'
    progress=json.loads(progress_path.read_text(encoding='utf-8')) if progress_path.exists() else None
    clock_ticks=list(range(1,math.ceil(timing['duration']))) if progress else []
    cuts=sorted(set([0,timing['duration']]+clock_ticks+[v for c in captions+scenes for v in (c['start'],c['end'])]))
    spans=[(a,b) for a,b in zip(cuts,cuts[1:]) if b-a>.00001]
    moments=[]
    for a,b in spans:
        midpoint=(a+b)/2
        scene=next(s for s in scenes if s['start']<=midpoint<s['end'])
        # Seek after 0.2 s scene entrance whenever it has no caption boundary.
        moments.append(min(b-.000001,max(midpoint,scene['start']+.21)))
    output=episode/'render-frames'; output.mkdir(exist_ok=True)
    env=os.environ.copy();env.update(HYPERFRAMES_NO_TELEMETRY='1',HYPERFRAMES_BROWSER_PATH='C:/Program Files/Google/Chrome/Application/chrome.exe',HYPERFRAMES_FONT_CACHE_DIR=str(ROOT/'.cache/fonts'))
    command=[str(NODE),str(CLI),'snapshot',str(ROOT/'film'),'--at',','.join(f'{v:.6f}' for v in moments),'--no-end','--describe','false','--output',str(output),'--json']
    result=subprocess.run(command,env=env,capture_output=True,text=True,encoding='utf-8')
    (episode/'snapshot-render.log').write_text(result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stderr[-2000:])
    report=json.loads(result.stdout);(episode/'snapshot-render.json').write_text(result.stdout,encoding='utf-8')
    paths=[Path(x['path']).as_posix() for x in report['frames']]
    if len(paths)!=len(spans):raise RuntimeError('Snapshot count does not match timeline spans')
    concat=[]
    for path,(a,b) in zip(paths,spans):concat.extend([f"file '{path}'",f'duration {b-a:.9f}'])
    concat.append(f"file '{paths[-1]}'")
    manifest=episode/'render-frames.ffconcat';manifest.write_text('\n'.join(concat)+'\n',encoding='utf-8')
    args=[str(FFMPEG),'-y','-hide_banner','-loglevel','warning','-f','concat','-safe','0','-i',str(manifest),'-i',str(episode/'narration.wav'),'-map','0:v:0','-map','1:a:0','-vf','fps=30,format=yuv420p','-c:v','h264_mf','-b:v','4M','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-t',str(timing['duration']),'-movflags','+faststart',str(episode/'sample.mp4')]
    if progress:
        bar=progress['bar'];blue=progress['blue'].lstrip('#');r,g,b=(int(blue[i:i+2],16) for i in (0,2,4))
        # Actual frame time drives the final MP4 fill; snapshots alone would
        # freeze it between caption cuts. The clock is sampled on second ticks.
        graph=(f"[0:v]fps=30,format=yuv420p,drawbox=x={bar['x']}:y={bar['y']}:w={bar['width']}:h={bar['height']}:color=0xE4E7EB:t=fill[base];"
               f"color=c=0x{blue}:s={bar['width']}x{bar['height']}:r=30:d={timing['duration']},format=rgba,geq=r={r}:g={g}:b={b}:a='if(lte(X/W,T/{timing['duration']}),255,0)'[bar];"
               f"[base][bar]overlay=x={bar['x']}:y={bar['y']}:shortest=1,format=yuv420p[video]")
        index=args.index('-vf');del args[index:index+2]
        args[args.index('0:v:0')]='[video]'
        args[args.index('-map'):args.index('-map')]=['-filter_complex',graph]
    with (episode/'encode.log').open('w',encoding='utf-8') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
    from verify_progress_video import verify
    verify(episode_id)
    from used_news import record_export
    record_export(episode,ROOT)
    from release_manager import prepare
    ready=prepare(episode_id)
    ep=json.loads((episode/'episode.json').read_text(encoding='utf-8'))
    if ep.get('alert_id'):
        from reset_alerts import mark_release
        mark_release(ep['alert_id'],ready['directory'])
    print(Path(ready['directory'])/ready['video_filename'])
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('episode');render(p.parse_args().episode)
