"""Resolve finalized editions without leaving duplicate media in the work tree."""
import json
from pathlib import Path
from project_paths import release_root

def episode_directory(root,episode_id):
    root=Path(root).resolve();work=root/'episodes'/episode_id;pointer=work/'release.json'
    if not pointer.exists():return work
    data=json.loads(pointer.read_text(encoding='utf-8'))
    release=release_root(root)
    target=((release/data['relative_directory']).resolve() if data.get('relative_directory') else Path(data['directory']).resolve())
    if not target.is_relative_to(release) or not target.is_dir():raise ValueError('Invalid release directory')
    return target

def release_movie(directory):
    directory=Path(directory);receipt=directory/'release.json'
    name=json.loads(receipt.read_text(encoding='utf-8')).get('video_filename','sample.mp4') if receipt.exists() else 'sample.mp4'
    if Path(name).name!=name:raise ValueError('Invalid release video filename')
    return directory/name
