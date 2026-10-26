"""Create upload metadata from release; no login, cookies, network or submission."""
import argparse,json
from pathlib import Path
from episode_paths import release_movie
from project_paths import release_root

ROOT=Path(__file__).resolve().parent

def plan(directory,root=ROOT):
    directory=Path(directory).resolve();release=release_root(root)
    if not directory.is_relative_to(release):raise ValueError('Uploads must use a release directory')
    receipt=json.loads((directory/'release.json').read_text(encoding='utf-8'))
    if receipt.get('published'):raise ValueError('Already published; refusing duplicate upload plan')
    pub=json.loads((directory/'publication.json').read_text(encoding='utf-8'))
    for name in ['cover-4x3.png','cover-16x9.png']:
        if not (directory/name).is_file():raise ValueError('Missing upload cover')
    video=release_movie(directory)
    if not video.is_file():raise ValueError('Missing named release video')
    from release_manager import digest
    recorded=next((x for x in receipt.get('archive_files',[]) if x['file']==video.name),None)
    if not recorded or digest(video)!=recorded['sha256']:raise ValueError('Release video hash not verified')
    tags=pub.get('tags',[])
    if len(tags)>10 or len(set(tags))!=len(tags) or any(not isinstance(x,str) or not 1<=len(x)<=20 for x in tags):raise ValueError('Invalid upload tags')
    if not 1<=len(pub['title'])<=80 or len(pub.get('description',''))>2000:raise ValueError('Upload title/description too long')
    meta=dict(video=str(video),title=pub['title'],cover=str(directory/'cover-16x9.png'),
        cover_4x3=str(directory/'cover-4x3.png'),creation_statement='含AI生成内容',
        partition='科技数码',tags=pub.get('tags',[]),description=pub.get('description',''),visibility='public')
    (directory/'upload.web-skill.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    instructions=dict(state='manual_or_browser_fill_only',upload_metadata='upload.web-skill.json',
        required_additional_checks=['同时勾选创作声明内的内容为自制；不能只填写原创标签',
            '选择或核实 News 为账号中的合集/分类；本次界面未发现独立 News 分类字段，不能伪称已设置',
            '选择与本期内容相关的热门活动；科技猎手是 2026-10-26 的实际例子，不固定套用',
            '逐项读回 AI 声明、原创声明、双封面、标签，发现缺项不得提交',
            '网页 skill 自身禁止最终提交；不得修改或绕过其点击守卫'],
        final_submit='Human, or a separate explicitly authorized and verified compatible tool; this script never submits')
    from upload_bridge import settings,prepare
    if settings(root).get('enabled'):
        prepared=prepare(directory,root)
        instructions=dict(state='ready_for_codex_upload',upload_metadata='upload.codex.json',backend='codex-upload',
            required_readback=['title','dual covers','tags including selected activity','original and AI declarations','actual collection ID','partition','visibility'],
            final_submit='codex-upload performs the authorized final submit; this plan command remains read-only')
        metadata=prepared['manifest']
    else:metadata=str(directory/'upload.web-skill.json')
    (directory/'upload-checklist.json').write_text(json.dumps(instructions,ensure_ascii=False,indent=2),encoding='utf-8')
    return dict(metadata=metadata,checklist=str(directory/'upload-checklist.json'),submitted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');a=p.parse_args();print(json.dumps(plan(a.directory),ensure_ascii=False,indent=2))
