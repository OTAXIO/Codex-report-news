"""Single-audience series for scheduled editions (2026-11-07).

Mornings carry one AI video; evenings carry one Arknights video and one
Endfield video. A scheduled episode without ``edition_series`` is a legacy
mixed edition and keeps its historical behaviour, so archived releases and
in-flight recoveries are unaffected.
"""
import re

SERIES={
    'ai':dict(slot='morning',kinds=('ai',),games=(),label='AI早报',short='AI早报',fixed_tags=('AI',)),
    'arknights':dict(slot='night',kinds=('games',),games=('arknights',),label='明日方舟情报',short='方舟情报',fixed_tags=('明日方舟',)),
    'endfield':dict(slot='night',kinds=('games',),games=('endfield',),label='终末地情报',short='终末地情报',fixed_tags=('明日方舟终末地','终末地')),
}
SLOT_SERIES={'morning':('ai',),'night':('arknights','endfield')}
LEGACY_FIXED_TAGS=('明日方舟','终末地')


def series_of(episode):
    value=(episode or {}).get('edition_series')
    if value is None:return None
    if value not in SERIES:raise ValueError('Unknown edition_series: '+str(value))
    return value


def spec(episode):
    series=series_of(episode)
    return SERIES[series] if series else None


def validate(episode):
    """Series must match its slot and its stories must all belong to it."""
    series=series_of(episode)
    if series is None:return None
    info=SERIES[series]
    if episode.get('edition_slot')!=info['slot']:
        raise ValueError(f'SERIES_SLOT_MISMATCH: {series} belongs to the {info["slot"]} edition')
    expected=episode_id(episode['edition_date'],series)
    base=re.sub(r'-v\d+$','',episode['id'])
    if base!=expected:raise ValueError('SERIES_ID_MISMATCH: use episode ID '+expected+' (optionally -vN)')
    for scene in episode.get('scenes',[]):
        if scene.get('scene_type')=='overview':continue
        if not accepts_scene(episode,scene):
            raise ValueError('SERIES_SCENE_MISMATCH: '+str(scene.get('id'))+' does not belong to series '+series)
    return series


def is_game_scene(scene):
    return bool(scene.get('game') or str(scene.get('section','')).startswith('游戏'))


def accepts_scene(episode,scene):
    info=spec(episode)
    if not info:return True
    if is_game_scene(scene):return scene.get('game') in info['games']
    return 'ai' in info['kinds']


def accepts_candidate(series,item):
    """Candidate rows carry kind; game rows carry game once their record is read."""
    if series is None:return True
    info=SERIES[series]
    if item.get('kind') not in info['kinds']:return False
    if info['games']:return item.get('game') in info['games']
    return True


def includes_ai(episode):
    info=spec(episode)
    return info is None or 'ai' in info['kinds']


def includes_games(episode):
    info=spec(episode)
    return info is None or 'games' in info['kinds']


def episode_id(date,series):
    compact=str(date).replace('-','')
    info=SERIES[series]
    return f'daily-{compact}-morning' if series=='ai' else f'daily-{compact}-{info["slot"]}-{series}'


def data_dir_name(date,series):
    compact=str(date).replace('-','')
    return f'morning-{compact}' if series=='ai' else f'night-{series}-{compact}'


def label(episode,default=None):
    info=spec(episode)
    return info['label'] if info else default


def fixed_tags(episode):
    info=spec(episode)
    return list(info['fixed_tags']) if info else list(LEGACY_FIXED_TAGS)
