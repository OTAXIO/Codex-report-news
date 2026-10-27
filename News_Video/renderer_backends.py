"""Pinned render selection and local Multiplane jobs; publishing stays elsewhere."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path

BACKENDS={'hyperframes','multiplane'}
TEMPLATES={'editorial','graphic'}

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def settings(root):return load(Path(root)/'config.json').get('rendering',{})

def shot_fingerprint(root,shot):
    shot=Path(shot);digest=hashlib.sha256()
    for path in sorted(shot.parent.rglob('*')):
        if not path.is_file() or 'covers' in path.relative_to(shot.parent).parts:continue
        digest.update(path.relative_to(shot.parent).as_posix().encode());digest.update(path.read_bytes())
    digest.update((Path(root)/'renderers/audit-shot.mjs').read_bytes())
    return digest.hexdigest()

def select_plan(root,episode,backend=None,template=None):
    root=Path(root);episode=Path(episode);path=episode/'render-plan.json'
    if (episode/'release.json').exists():raise ValueError('Archived editions cannot change renderer')
    if path.exists():
        plan=load(path)
        package=root/'node_modules'/plan['backend']/'package.json'
        if not package.is_file() or load(package)['version']!=plan['version']:raise ValueError('Pinned renderer version changed; restore its locked dependency')
        if (backend and backend!=plan['backend']) or (template and template!=plan['template']):
            raise ValueError('Render plan is pinned; use a new episode/revision to change renderer or template')
        return plan
    cfg=settings(root)
    legacy=(episode/'scene-timings.json').exists()
    backend=backend or ('hyperframes' if legacy else cfg.get('default_backend','hyperframes'))
    if backend not in BACKENDS:raise ValueError('Unknown renderer')
    template=(template or cfg.get('default_template','editorial')) if backend=='multiplane' else 'legacy'
    if backend=='multiplane' and template not in TEMPLATES:raise ValueError('Unknown Multiplane template')
    package=root/'node_modules'/('multiplane' if backend=='multiplane' else 'hyperframes')/'package.json'
    if not package.is_file():raise ValueError('Install the locked renderer dependency first')
    version=load(package)['version']
    options=dict(cfg.get('multiplane',{})) if backend=='multiplane' else dict(encoder='h264_mf',video_bitrate='4M',fps=30,capture='held_cards',ffmpeg='D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/ffmpeg.exe')
    plan=dict(schema_version=1,backend=backend,version=version,template=template,options=options,
              artifact_directory=(episode/'visuals'/(backend+'-'+template)).relative_to(root).as_posix(),
              fallback_used=False)
    content=load(episode/'episode.json') if (episode/'episode.json').exists() else {}
    fallback=content.get('rendering_fallback')
    if fallback:
        if fallback.get('from_backend') not in BACKENDS or not fallback.get('reason'):raise ValueError('Fallback must record its original backend and actual reason')
        plan.update(fallback_used=True,fallback_from=fallback['from_backend'],fallback_reason=fallback['reason'])
    save(path,plan);return plan

def run_multiplane(root,command,shot=None,extra=(),report=None,plan=None):
    root=Path(root);cfg=settings(root);options=(plan or {}).get('options',cfg.get('multiplane',{}))
    node=cfg.get('node_executable') or shutil.which('node')
    if not node:raise ValueError('Node 24+ is required')
    cli=root/'node_modules/multiplane/bin/multiplane'
    args=[str(node),str(cli),command]
    if shot:args.append(str(shot))
    args+=['--json']
    if command in {'render','doctor'}:args+=['--ffmpeg',str((root/options.get('ffmpeg','.tools/ffmpeg/ffmpeg.exe')).resolve())]
    if shot and command in {'render','stills','verify','inspect','lint'}:args+=['--root',str(Path(shot).parent)]
    if command in {'render','stills','verify','status','resume','wait','cancel'}:args+=['--job-dir',str(root/'.cache/multiplane-jobs')]
    args+=list(extra)
    env=os.environ.copy();env.update(MULTIPLANE_HOME=str(root/'.cache/multiplane-home'),MULTIPLANE_NO_INDEX='1')
    temporary=root/'.cache/render-temp';temporary.mkdir(parents=True,exist_ok=True)
    env.update(TEMP=str(temporary),TMP=str(temporary))
    env['PLAYWRIGHT_BROWSERS_PATH']=str(root/'.cache/playwright')
    result=subprocess.run(args,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    events=[]
    for line in result.stdout.splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:pass
    final=next((e for e in reversed(events) if e.get('type')=='result'),None)
    if report:
        report=Path(report);save(report,dict(command=args,exit_code=result.returncode,result=final,events=events))
        report.with_suffix('.stderr.log').write_text(result.stderr,encoding='utf-8')
    if result.returncode or not final or final.get('ok') is not True:
        raise RuntimeError('Multiplane '+command+' failed: '+str((final or {}).get('code','missing_result'))+'; '+str((final or {}).get('message',result.stderr[-500:])))
    return final

def check_multiplane(root,episode,plan):
    episode=Path(episode);shot=Path(root)/plan['artifact_directory']/'index.html'
    fingerprint=shot_fingerprint(root,shot)
    cached=episode/'check.json'
    if cached.exists():
        previous=load(cached)
        if previous.get('ok') is True and previous.get('input_sha256')==fingerprint:return previous['determinism']
    duration=load(episode/'timings.json')['duration']
    scenes=load(episode/'scene-timings.json')
    points=sorted({round(min(duration-1/30,max(0,(s['start']+s['end'])/2))*30)/30 for s in scenes})
    at=','.join(f'{t:.9f}' for t in points)
    out=episode/'render-checks';out.mkdir(exist_ok=True)
    common=['--workers',str(plan['options'].get('workers',2))]
    lint=run_multiplane(root,'lint',shot,report=out/'lint.json',plan=plan)
    inspect=run_multiplane(root,'inspect',shot,report=out/'inspect.json',plan=plan)
    stills=run_multiplane(root,'stills',shot,['--at',at,'--out',str(out/'stills'),'--overwrite'],out/'stills.json',plan)
    env=os.environ.copy();temp=root/'.cache/render-temp';temp.mkdir(parents=True,exist_ok=True)
    env.update(PLAYWRIGHT_BROWSERS_PATH=str(root/'.cache/playwright'),TEMP=str(temp),TMP=str(temp))
    audit=subprocess.run([str(settings(root)['node_executable']),str(root/'renderers/audit-shot.mjs'),str(shot),str(episode/'layout-audit.json')],env=env,capture_output=True,text=True,encoding='utf-8')
    if audit.returncode:raise RuntimeError('Multiplane layout audit failed: '+audit.stdout[-1000:]+audit.stderr[-300:])
    verified=run_multiplane(root,'verify',shot,['--at',at]+common,out/'verify.json',plan)
    save(episode/'check.json',dict(ok=True,backend='multiplane',input_sha256=fingerprint,lint=lint,inspect=inspect,stills=stills,layout=load(episode/'layout-audit.json'),determinism=verified))
    return verified

def render_multiplane(root,episode,plan,resume=False):
    from audio_mix import ensure_soundtrack
    root=Path(root);episode=Path(episode);shot=root/plan['artifact_directory']/'index.html'
    duration=load(episode/'timings.json')['duration']
    audio=ensure_soundtrack(root,episode,duration)
    from audio_mix import digest
    input_sha256=hashlib.sha256((shot_fingerprint(root,shot)+digest(audio)).encode()).hexdigest()
    options=plan['options'];output=episode/'sample.mp4'
    job=episode/'render-job.json'
    # A stored interrupted job must be resumed deliberately, never silently
    # started a second time with different resources/parameters.
    if job.exists():
        previous=load(job)
        if previous.get('ok'):
            if not output.is_file():raise ValueError('Completed render output is missing')
            if previous.get('input_sha256')!=input_sha256 or previous.get('video_sha256')!=digest(output):raise ValueError('Completed render inputs/output changed; use a new revision')
            return output  # Re-run application validation without re-rendering.
        if not resume or not previous.get('job_id'):raise ValueError('Interrupted render exists; use --resume-render after inspecting its job')
        result=run_multiplane(root,'resume',previous['job_id'],report=episode/'multiplane-render.json',plan=plan)
        save(job,dict(ok=True,backend='multiplane',job_id=result.get('jobId'),input_sha256=input_sha256,video_sha256=digest(output),result=result))
        save(episode/'render-validation.json',dict(ok=bool(result.get('data',{}).get('outputCheck')),backend='multiplane',result=result))
        return output
    check_multiplane(root,episode,plan)
    args=['--audio',str(audio),'--out',str(output),'--workers',str(options.get('workers',2)),
          '--encoder',options.get('encoder','x264'),'--quality',options.get('quality','standard')]
    try:result=run_multiplane(root,'render',shot,args,episode/'multiplane-render.json',plan)
    except RuntimeError:
        report=load(episode/'multiplane-render.json')
        event=next((e for e in reversed(report['events']) if e.get('jobId')),{} )
        save(job,dict(ok=False,backend='multiplane',job_id=event.get('jobId'),result=report['result']))
        raise
    save(job,dict(ok=True,backend='multiplane',job_id=result.get('jobId'),input_sha256=input_sha256,video_sha256=digest(output),result=result))
    save(episode/'render-validation.json',dict(ok=bool(result.get('data',{}).get('outputCheck')),backend='multiplane',output_check=result.get('data',{}).get('outputCheck'),result=result))
    return output

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['doctor','check']);parser.add_argument('episode',nargs='?');args=parser.parse_args()
    root=Path(__file__).resolve().parent
    if args.command=='doctor':print(json.dumps(run_multiplane(root,'doctor'),ensure_ascii=False))
    else:
        if not args.episode:parser.error('check requires an episode ID')
        from episode_paths import episode_directory
        folder=episode_directory(root,args.episode);plan=select_plan(root,folder)
        if plan['backend']=='multiplane':print(json.dumps(check_multiplane(root,folder,plan),ensure_ascii=False))
        else:
            cfg=settings(root);env=os.environ.copy();env.update(HYPERFRAMES_NO_TELEMETRY='1',HYPERFRAMES_BROWSER_PATH='C:/Program Files/Google/Chrome/Application/chrome.exe',HYPERFRAMES_FONT_CACHE_DIR=str(root/'.cache/fonts'))
            result=subprocess.run([cfg['node_executable'],str(root/'node_modules/hyperframes/bin/hyperframes.mjs'),'check',str(root/plan['artifact_directory']),'--json'],env=env,capture_output=True,text=True,encoding='utf-8')
            (folder/'check.json').write_text(result.stdout,encoding='utf-8');print(result.stdout)
            raise SystemExit(result.returncode)
