"""Current news delivery rules, shared by export and upload boundaries."""
import json,math,subprocess
from pathlib import Path

FIXED_TAGS=['明日方舟','终末地']

def config(root):
    path=Path(root)/'config.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}

def tags(values):
    # Reserve two mandatory tags and one platform activity slot.
    return FIXED_TAGS+list(dict.fromkeys(t for t in values if t not in FIXED_TAGS))[:7]

def validate_video(root,video):
    cfg=config(root)
    if not cfg.get('production',{}).get('minimum_duration_exclusive_seconds'):return None
    ff=cfg.get('voice',{}).get('qwen3',{}).get('ffmpeg_executable','ffmpeg')
    probe=Path(ff).with_name('ffprobe.exe' if str(ff).endswith('.exe') else 'ffprobe')
    p=subprocess.run([str(probe),'-v','error','-show_entries','format=duration:stream=codec_type,duration','-of','json',str(video)],capture_output=True,text=True,check=True)
    data=json.loads(p.stdout);duration=float(data['format']['duration'])
    video_stream=next((s for s in data.get('streams',[]) if s.get('codec_type')=='video'),None)
    if video_stream is None:raise ValueError('Formal news needs an actual video stream')
    actual=min(duration,float(video_stream.get('duration',duration)))
    minimum=cfg['production']['minimum_duration_exclusive_seconds']
    if not math.isfinite(actual) or actual<=minimum:raise ValueError('Formal news MP4 must exceed 30.0 seconds; enrich the sourced content and regenerate, never pad or edit metadata')
    return dict(duration=actual,minimum_exclusive=minimum,ok=True)

def validate_content(episode):
    if episode.get('edition_slot') not in {'morning','night'}:return
    body=[s for s in episode['scenes'] if s.get('scene_type')!='overview']
    if any(s.get('section','').startswith(('国内','国际')) for s in body):raise ValueError('New main editions contain AI and game news only; social news removed')
    seen={};game_started=False
    for s in body:
        event=s.get('event_key') or s.get('item_id') or s.get('id')
        if event in seen:
            previous=seen[event]
            if not (s.get('game') and s.get('item_id') and s.get('item_id')==previous.get('item_id') and isinstance(s.get('page_number'),int) and isinstance(previous.get('page_number'),int) and s['page_number']>previous['page_number']):raise ValueError('Duplicate event across sources/languages; same-story pages need explicit page numbers')
        seen[event]=s
        if s.get('game') or s.get('section','').startswith('游戏'):
            game_started=True
            if not s.get('event_key'):raise ValueError('Game news needs a reviewed cross-source event key; translated announcements are one event')
            if s.get('game') not in {'arknights','endfield'}:raise ValueError('Unsupported game')
            if not s.get('game_region') or s.get('game_topic') not in {'update','event','other'}:raise ValueError('Game news needs verified region and topic')
        elif game_started:raise ValueError('AI news must precede the game module')
    first=next((s for s in body if s.get('game')),None)
    if first and not first['narration'].startswith('接下来是游戏资讯'):
        first['narration']='接下来是游戏资讯，先来看'+('明日方舟。' if first['game']=='arknights' else '明日方舟：终末地。')+first['narration']

def modules(episode,offsets,duration):
    if episode.get('edition_slot')=='temporary':return [('temporary','临时新闻',0,duration)]
    game=next((i for i,s in enumerate(episode['scenes']) if s.get('game') or s.get('section','').startswith('游戏')),None)
    if game is not None:
        return ([('ai','AI 动态',0,offsets[game]['start'])] if game else [])+[('games','游戏资讯',offsets[game]['start'],duration)]
    # Historical layouts stay readable; new imports reject social stories.
    social=next((i for i,s in enumerate(episode['scenes']) if s.get('section','').startswith(('国内','国际'))),None)
    if social is None:return [('ai','AI 动态',0,duration)]
    return ([('ai','AI 动态',0,offsets[social]['start'])] if social else [])+[('news','国内外重点新闻',offsets[social]['start'],duration)]
