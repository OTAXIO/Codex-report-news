"""Build a local, credential-free DSH context/source bundle from an allowlist."""
import argparse,hashlib,json,sqlite3,tempfile,zipfile
from contextlib import closing
from pathlib import Path
from project_paths import workspace_root,release_root

ROOT=Path(__file__).resolve().parent;WORK=workspace_root(ROOT)

def digest(data):return hashlib.sha256(data).hexdigest()

def build(date='2026-10-26'):
    import datetime
    datetime.date.fromisoformat(date)
    out=WORK/'handoff';out.mkdir(exist_ok=True)
    target=out/f'DSH_NEWS_VIDEO_CONTEXT_{date.replace("-","_")}.zip'
    files={}
    def add(path,arc=None):
        path=Path(path)
        if not path.is_file():return
        arc=arc or path.relative_to(WORK).as_posix()
        if 'assets/music' in arc.replace('\\','/'):return  # User-supplied music is local-only.
        forbidden={'.env','cookies.json','node_modules','browser-profile','private','__pycache__','audit'}
        if any(part.lower() in forbidden for part in Path(arc).parts):raise ValueError('Private or generated path selected: '+arc)
        files[arc]=path
    for name in ['AGENTS.md','PROJECT_PROMPT.md','PROJECT_VERSION.json','handoff/START_HERE.md','handoff/DSH_PROMPT.md','handoff/CODEX_UPLOAD_SKILL_PROMPT.md']:add(WORK/name)
    for name in ['data/leader-collection-state.json','data/candidates.json','data/hourly-monitor-last.json']:add(ROOT/name)
    # Ship the matching public uploader source, so deployment checks work on a
    # new DSH machine without falling back to an older remote checkout.
    for p in (WORK/'codex-upload-video/codex-upload').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and (p.suffix in {'.py','.mjs','.md','.json','.yaml','.txt'} or p.name in {'LICENSE','NOTICE'}):add(p)
    for p in ROOT.glob('*.py'):add(p)
    for name in ['config.json','sources.json','leader_sources.json','package.json','pnpm-lock.yaml','pnpm-workspace.yaml','requirements.txt','README.md','.gitignore']:add(ROOT/name)
    for directory in ['renderers','docs','skills','logs/news-used','logs/releases','data/articles','data/collections','data/source-probes','data/leader-posts','data/reset-alerts','data/model-alerts']:
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and 'history' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts:add(p)
    for p in (ROOT/'assets').rglob('*'):
        if p.is_file() and 'fonts' not in p.parts:add(p)
    for p in (ROOT/'film').rglob('*'):
        if p.is_file() and '.hyperframes' not in p.parts and 'fonts' not in p.parts and p.suffix in {'.html','.json','.js'}:add(p)
    for p in (ROOT/'episodes').rglob('*'):
        if p.is_file() and p.suffix in {'.json','.txt'}:add(p)
    for name in ['generate_job.py','audio_cleanup.py','common.py','prosody.py','qwen_generate_job.py','prepare_qwen_dataset.py','download_qwen3.py','download_qwen3_modelscope.py','qwen_generate_context.py','context_alignment.py','download_alignment_model.py','speech_text.py']:add(WORK/'Voice_Generate/tools'/name)
    add(WORK/'Voice_Generate/requirements-qwen3.txt')
    add(WORK/'Voice_Generate/requirements-qwen3-training.txt')
    add(WORK/'Voice_Generate/README.md')
    for name in ['dataset.py','prepare_data.py','LICENSE']:add(WORK/'Voice_Generate/vendor/qwen3_official'/name)
    add(WORK/'Voice_Generate/docs/QWEN3_TTS_INTEGRATION.md')
    add(WORK/'Voice_Generate/docs/CONTEXTUAL_VOICE.md')
    add(WORK/'Voice_Generate/docs/SPEECH_POLICY.md')
    for name in ['test_speech_text.py','test_context_alignment.py']:add(WORK/'Voice_Generate/tests'/name)
    example=release_root(ROOT)/'2026_10_26_night'
    for p in example.iterdir():
        if p.is_file() and p.suffix in {'.mp4','.png','.jpg','.json','.txt','.md','.wav','.yaml'}:add(p)
    # Carry verified temporary metadata for recap/deduplication without shipping media.
    for receipt_path in release_root(ROOT).glob('*/release.json'):
        receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt.get('published') and receipt.get('edition_slot')=='temporary':
            for name in ['release.json','episode.json','publication-verified.json','publication.json','script.txt','title.txt','tags.txt']:
                add(receipt_path.parent/name)
    cache=ROOT/'.cache';cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='handoff-',dir=cache) as temp:
        staging=Path(temp).resolve()
        if not staging.is_relative_to(cache.resolve()):raise ValueError('Unsafe staging directory')
        snapshot=staging/'news.sqlite3'
        with closing(sqlite3.connect(ROOT/'data/news.sqlite3')) as source,closing(sqlite3.connect(snapshot)) as dest:source.backup(dest)
        add(snapshot,ROOT.relative_to(WORK).as_posix()+'/data/news.sqlite3')
        manifest=[]
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
            for arc,path in sorted(files.items()):
                data=path.read_bytes();z.writestr(arc,data);manifest.append(dict(file=arc,bytes=len(data),sha256=digest(data)))
            z.writestr('handoff/MANIFEST.json',json.dumps(dict(date=date,files=manifest,excluded=['credentials','browser profiles','model weights','node_modules','Microsoft fonts','old recovery ZIP']),ensure_ascii=False,indent=2))
        with zipfile.ZipFile(target) as z:
            if z.testzip():raise ValueError('Handoff ZIP CRC failure')
            for item in manifest:
                if digest(z.read(item['file']))!=item['sha256']:raise ValueError('Handoff ZIP hash failure')
    result=dict(path=str(target),files=len(manifest),bytes=target.stat().st_size,sha256=digest(target.read_bytes()),crc_and_hashes_verified=True)
    (out/'handoff-package.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--date',default='2026-10-26');a=p.parse_args();print(json.dumps(build(a.date),ensure_ascii=False,indent=2))
