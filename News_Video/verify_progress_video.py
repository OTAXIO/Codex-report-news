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
        if spec.get('full_bleed_edges'):
            for edge in [im[:,0,:],im[:,-1,:]]:
                if float(np.mean(np.all(edge>245,axis=1)))>.02:raise ValueError('White sidebar detected in full-bleed video')
        mask=lambda a:(a[:,0]<80)&(a[:,1]>100)&(a[:,2]>180)
        if spec.get('right_block_width'):
            edge=im[:,-spec['right_block_width']:,:].reshape(-1,3)
            if float(np.mean(mask(edge)))<.98:raise ValueError('Right edge block is not solid blue')
        bar=spec['bar'];x,w=bar['x'],bar['width']
        if spec.get('bottom_edge_aligned') and bar['y']+bar['height']!=im.shape[0]:raise ValueError('Progress bar does not touch the actual video bottom edge')
        blue_pixels=np.flatnonzero(mask(im[bar['y']+3,x:x+w,:]))
        # Chapter markers cut small black gaps into the blue bar. Its leading
        # edge, rather than blue-pixel count, measures the actual video progress.
        fill=int(blue_pixels[-1]+1) if len(blue_pixels) else 0
        expected=w*t/spec['duration']
        active=np.flatnonzero(mask(im[spec.get('chapter_highlight_y',1014),x:x+w,:]))
        bounds=spec.get('chapter_bounds')
        left=(bounds[i]['x']-x) if bounds else w*chapter['start']/spec['duration']
        right=left+bounds[i]['width'] if bounds else w*chapter['end']/spec['duration']
        if abs(fill-expected)>8:raise ValueError('Progress fill/time mismatch')
        if not len(active) or active.min()<left-3 or active.max()>right+3:raise ValueError('Wrong news item highlighted')
        if spec.get('modules'):
            module=next(m for m in spec['modules'] if m['start']<=t<m['end'])
            pixels=np.flatnonzero(mask(im[spec['module_highlight_y'],x:x+w,:]))
            lo=w*module['start']/spec['duration'];hi=w*module['end']/spec['duration']
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
