"""Check actual decoded progress and active-item labels in a produced MP4."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).parent
FF=Path('D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/ffmpeg.exe')
PROBE=FF.with_name('ffprobe.exe')
def verify(episode):
    from episode_paths import episode_directory,release_movie
    directory=episode_directory(ROOT,episode);movie=release_movie(directory)
    spec=json.loads((directory/'progress.json').read_text(encoding='utf-8'))
    captures=directory/'verification-frames';captures.mkdir(exist_ok=True)
    rows=[]
    for i,chapter in enumerate(spec['chapters']):
        t=(chapter['start']+chapter['end'])/2;path=captures/f'{i:02d}.png'
        subprocess.run([str(FF),'-y','-hide_banner','-loglevel','error','-ss',str(t),'-i',str(movie),'-frames:v','1',str(path)],check=True)
        im=np.array(Image.open(path).convert('RGB'))
        mask=lambda a:(a[:,0]<80)&(a[:,1]>100)&(a[:,2]>180)
        fill=int(np.sum(mask(im[1048,192:1728,:])))
        expected=1536*t/spec['duration']
        active=np.flatnonzero(mask(im[1014,192:1728,:]))
        left=1536*chapter['start']/spec['duration'];right=1536*chapter['end']/spec['duration']
        if abs(fill-expected)>8:raise ValueError('Progress fill/time mismatch')
        if not len(active) or active.min()<left-3 or active.max()>right+3:raise ValueError('Wrong news item highlighted')
        if spec.get('modules'):
            module=next(m for m in spec['modules'] if m['start']<=t<m['end'])
            pixels=np.flatnonzero(mask(im[spec['module_highlight_y'],192:1728,:]))
            lo=1536*module['start']/spec['duration'];hi=1536*module['end']/spec['duration']
            if not len(pixels) or pixels.min()<lo-3 or pixels.max()>hi+3:raise ValueError('Wrong major module highlighted')
        rows.append(dict(item=chapter.get('id',chapter['label']),label=chapter['label'],time=t,fill_pixels=fill,expected_pixels=round(expected),correct_item_highlighted=True,frame=str(path)))
    probe=subprocess.run([str(PROBE),'-v','error','-show_entries','format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,duration','-of','json',str(movie)],capture_output=True,text=True,check=True)
    (directory/'ffprobe.json').write_text(probe.stdout,encoding='utf-8')
    with (directory/'decode-errors.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(FF),'-hide_banner','-loglevel','error','-i',str(movie),'-f','null','-'],stderr=log,check=True)
    if (directory/'decode-errors.log').stat().st_size:raise ValueError('Decode errors present')
    (directory/'progress-validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(items_verified=len(rows),decode_errors=0,media=json.loads(probe.stdout)),ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('episode');verify(p.parse_args().episode)
