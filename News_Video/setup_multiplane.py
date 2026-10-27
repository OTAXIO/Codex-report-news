"""Prepare project-local Multiplane browser/FFmpeg without changing global apps."""
import argparse,hashlib,json,os,subprocess,urllib.request,zipfile
from pathlib import Path
from renderer_backends import run_multiplane,settings
ROOT=Path(__file__).resolve().parent

def install_runtime():
    if os.name!='nt':raise ValueError('On this OS install FFmpeg separately and configure rendering.multiplane.ffmpeg')
    with urllib.request.urlopen('https://pypi.org/pypi/imageio-ffmpeg/0.6.0/json') as response:info=json.load(response)
    wheel=next(f for f in info['urls'] if f['filename'].endswith('win_amd64.whl'))
    folder=ROOT/'.cache/downloads';folder.mkdir(parents=True,exist_ok=True);target=folder/wheel['filename']
    if not target.exists():urllib.request.urlretrieve(wheel['url'],target)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=wheel['digests']['sha256']:raise ValueError('FFmpeg wheel hash mismatch')
    out=ROOT/'.tools/ffmpeg';out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target) as z:
        for name in z.namelist():
            if name.endswith('.exe'):
                data=z.read(name);binary=out/'ffmpeg.exe'
                if not binary.exists() or hashlib.sha256(binary.read_bytes()).digest()!=hashlib.sha256(data).digest():binary.write_bytes(data)
            elif 'LICENSE' in name.upper() or 'COPYING' in name.upper():(out/Path(name).name).write_bytes(z.read(name))
    env=os.environ.copy();env.update(PLAYWRIGHT_BROWSERS_PATH=str(ROOT/'.cache/playwright'),TEMP=str(ROOT/'.cache/render-temp'),TMP=str(ROOT/'.cache/render-temp'))
    (ROOT/'.cache/render-temp').mkdir(parents=True,exist_ok=True)
    # Use exactly the Playwright dependency of the locked Multiplane package.
    script="const p=require('path'),r=require.resolve('playwright/package.json',{paths:[require.resolve('multiplane')]});process.stdout.write(p.join(p.dirname(r),'cli.js'))"
    node=settings(ROOT)['node_executable'];cli=subprocess.check_output([node,'-e',script],cwd=ROOT,text=True)
    subprocess.run([node,cli,'install','chromium'],cwd=ROOT,env=env,check=True)
    (out/'PROVENANCE.json').write_text(json.dumps(dict(distribution='imageio-ffmpeg',version='0.6.0',wheel=wheel['filename'],sha256=wheel['digests']['sha256']),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--install-runtime',action='store_true');args=p.parse_args()
    if args.install_runtime:install_runtime()
    result=run_multiplane(ROOT,'doctor',report=ROOT/'.cache/multiplane-doctor.json');print(json.dumps(result,ensure_ascii=False))
