"""Keep only the last few days of finished editions (user rule, 2026-11-19).

Dry run by default; `--apply` deletes permanently. Run once per edition after the
upload has been recovered, before clearing the recycle bin.

Deleted, for editions dated before the window (Beijing dates; --days 3 keeps today
and the two days before):
  - release/<date>_* folders whose release.json is published (anything still
    submitted/reviewing/unknown/unpublished is kept and reported)
  - release/previews entries, episodes/<...date...> work folders,
    data/collections/<date>T* snapshots
  - .cache/render-temp, .cache/multiplane-jobs, .cache/frames* scratch
  - .cache/voice-units files not touched within the window
Anything modified in the last 6 hours is left alone, so a run cannot pull files
from under an edition that is still being made.
Never touched: Voice_Generate, media-library, private browser profiles, data/*.sqlite3,
ledgers, .cache/playwright, node_modules.
"""
import argparse,datetime as dt,json,os,re,shutil,stat,time
from pathlib import Path
from project_paths import release_root

ROOT=Path(__file__).resolve().parent
BEIJING=dt.timezone(dt.timedelta(hours=8))
FRESH_SECONDS=6*3600
SCRATCH=['render-temp','multiplane-jobs']

def date_of(name):
    m=re.search(r'(20\d{2})[_-]?(\d{2})[_-]?(\d{2})',name)
    return ''.join(m.groups()) if m else None

def newest_mtime(path):
    path=Path(path)
    if path.is_file():return path.stat().st_mtime
    times=[p.stat().st_mtime for p in path.rglob('*')]
    return max(times+[path.stat().st_mtime])

def size(path):
    path=Path(path)
    return path.stat().st_size if path.is_file() else sum(p.stat().st_size for p in path.rglob('*') if p.is_file())

def plan(root=ROOT,days=3,now=None):
    root=Path(root);now=now or time.time()
    cutoff=(dt.datetime.fromtimestamp(now,BEIJING).date()-dt.timedelta(days=days-1)).strftime('%Y%m%d')
    delete,kept=[],[]
    fresh=lambda p:now-newest_mtime(p)<FRESH_SECONDS
    releases=release_root(root)
    if releases.is_dir():
        for d in sorted(releases.iterdir()):
            if not d.is_dir():continue
            if d.name=='previews':
                delete+=[p for p in d.iterdir() if not fresh(p)];continue
            day=date_of(d.name)
            if not day or day>=cutoff or fresh(d):continue
            receipt=d/'release.json'
            state=json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else {}
            if state.get('published') is True:delete.append(d)
            else:kept.append((d,'not published: '+str(state.get('state'))))
    for folder in [root/'episodes',root/'data/collections']:
        if folder.is_dir():
            delete+=[d for d in sorted(folder.iterdir()) if (date_of(d.name) or '99999999')<cutoff and not fresh(d)]
    cache=root/'.cache'
    if cache.is_dir():
        for name in SCRATCH:
            if (cache/name).is_dir():delete+=[p for p in (cache/name).iterdir() if not fresh(p)]
        delete+=[p for p in cache.glob('frames*') if not fresh(p)]
        units=cache/'voice-units'
        if units.is_dir():delete+=[p for p in units.iterdir() if now-p.stat().st_mtime>days*86400]
    return cutoff,delete,kept

def remove(path):
    def writable(func,target,_):
        os.chmod(target,stat.S_IWRITE);func(target)
    if path.is_dir():shutil.rmtree(path,onexc=writable)
    else:os.chmod(path,stat.S_IWRITE);path.unlink()

def main():
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--days',type=int,default=3);p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    cutoff,delete,kept=plan(days=a.days)
    total=sum(size(x) for x in delete)
    print(json.dumps(dict(keep_from=cutoff,delete=len(delete),bytes=total,kept_unpublished=[f'{d.name}: {why}' for d,why in kept]),ensure_ascii=False))
    if not a.apply:
        for x in delete[:40]:print('  would delete',x)
        return
    failed=[]
    for x in delete:
        try:remove(x)
        except OSError as error:failed.append(f'{x}: {error}')
    print(json.dumps(dict(deleted=len(delete)-len(failed),failed=failed),ensure_ascii=False))

if __name__=='__main__':main()
