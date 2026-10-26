"""Resolve workspace resources independently of the source checkout depth."""
import json
from pathlib import Path


def project_config(root):
    path = Path(root) / 'config.json'
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}


def workspace_root(root):
    root = Path(root).resolve()
    value = project_config(root).get('workspace_directory', '..')
    return (root / value).resolve()


def release_root(root):
    root = Path(root).resolve()
    value = project_config(root).get('release', {}).get('directory')
    return (root / value).resolve() if value else workspace_root(root) / 'release'
