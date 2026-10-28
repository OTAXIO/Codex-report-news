"""Compact stage router over the existing production commands.

Editorial and visual judgment stay with the producer. Deterministic stages
reuse existing CLIs and their own quality gates; this module stores no second
copy of episode or publication state.
"""
import argparse,json,re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def status(episode_id=None,root=ROOT):
    root=Path(root)
    if not episode_id:
        return dict(stage='collect',next=['news_video.py','collect','--kind','all'],
                    then=['news_video.py','candidates','--compact','--limit','12','--cursor','0'])
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,95}',episode_id):
        raise ValueError('Invalid episode ID')
    source=root/'episodes'/episode_id
    if (source/'release.json').is_file() and not (source/'episode.json').is_file():
        return dict(episode_id=episode_id,stage='complete',directory=load(source/'release.json').get('directory'))
    if not (source/'episode.json').is_file():
        return dict(episode_id=episode_id,stage='editorial_required',evidence='data/candidates.json')
    ep=load(source/'episode.json')
    if ep.get('id')!=episode_id:raise ValueError('Episode identity mismatch')
    base=dict(episode_id=episode_id,edition_slot=ep.get('edition_slot'),
              renderer=load(source/'render-plan.json').get('backend') if (source/'render-plan.json').is_file() else None)
    target_pointer=source/'release-target.json'
    if target_pointer.is_file():
        target=Path(load(target_pointer)['directory']).resolve()
        from project_paths import release_root
        if not target.is_relative_to(release_root(root).resolve()):raise ValueError('Unsafe release pointer')
        receipt_path=target/'release.json'
        if receipt_path.is_file():
            receipt=load(receipt_path);base.update(directory=str(target),release_state=receipt.get('state'))
            if receipt.get('published'):return dict(base,stage='complete')
            if receipt.get('upload_policy')=='diagnostic_hold':return dict(base,stage='held')
            if receipt.get('upload_policy')!='automatic':return dict(base,stage='resume_export')
            if receipt.get('state') in {'unknown','submitted','reviewing','upload_failed','ready_for_upload'}:
                if not (target/'used-news-record.json').is_file():return dict(base,stage='resume_export')
                return dict(base,stage='recover_upload')
        return dict(base,stage='resume_export')
    if not (source/'publication.json').is_file() or not (source/'script.txt').is_file():
        return dict(base,stage='editorial_required',reason='Publication and script must be finalized before voice')
    if not (source/'narration.wav').is_file():return dict(base,stage='voice')
    if not (source/'cover-4x3.png').is_file() or not (source/'cover-16x9.png').is_file():
        return dict(base,stage='cover' if (source/'cover.json').is_file() else 'cover_brief_required')
    if (source/'sample.mp4').is_file():return dict(base,stage='resume_export')
    return dict(base,stage='render')

def execute(stage,episode_id=None,root=ROOT):
    root=Path(root)
    commands={
        'collect':[['news_video.py','collect','--kind','all'],['news_video.py','candidates','--compact','--limit','12','--cursor','0']],
        'voice':[['news_video.py','voice',episode_id]],
        'cover':[['cover_generator.py',episode_id]],
        'render':[['render_sample.py',episode_id]],
        'resume_export':[['render_sample.py',episode_id,'--resume-export']],
    }
    if stage=='recover_upload':
        target=status(episode_id,root)['directory']
        commands[stage]=[['upload_bridge.py','recover',target]]
    if stage not in commands:raise ValueError('Stage requires editorial input or is complete: '+stage)
    for command in commands[stage]:
        subprocess.run([sys.executable,'-B',str(root/command[0]),*command[1:]],cwd=root,check=True)

def advance(episode_id=None,root=ROOT):
    history=[]
    for _ in range(6):
        before=status(episode_id,root);stage=before['stage']
        if stage in {'complete','held','editorial_required','cover_brief_required'}:
            return dict(**before,executed=history)
        execute(stage,episode_id,root);history.append(stage)
        after=status(episode_id,root)
        # A submission or reconciliation is attempted at most once per call.
        if stage in {'collect','render','resume_export','recover_upload'}:
            return dict(**after,executed=history)
        if after['stage']==stage:raise RuntimeError('Stage made no progress: '+stage)
    raise RuntimeError('Stage loop exceeded safe bound')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['plan','status','advance','resume'])
    p.add_argument('episode',nargs='?')
    a=p.parse_args();result=advance(a.episode) if a.command in {'advance','resume'} else status(a.episode)
    print(json.dumps(result,ensure_ascii=False))
