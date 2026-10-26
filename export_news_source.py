"""Export an allowlisted source snapshot; never move the live production tree."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(source, destination):
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or not destination.is_relative_to(source):
        raise ValueError('Destination must be a separate child of the source workspace')
    destination.mkdir(exist_ok=True)
    existing = [p for p in destination.iterdir() if p.name != '.git']
    if existing:
        raise ValueError('Refusing to overwrite a nonempty snapshot')
    files = set()
    def add(path):
        if not path.is_file():
            raise FileNotFoundError(path)
        files.add(path.relative_to(source))
    news = source / 'News_Video'
    for path in news.glob('*.py'):
        add(path)
    for name in ('config.json', 'sources.json', 'leader_sources.json', 'package.json',
                 'pnpm-lock.yaml', 'pnpm-workspace.yaml', 'requirements.txt',
                 '.gitignore'):
        add(news / name)
    for path in (news / 'assets/logos').iterdir():
        if path.is_file() and path.suffix in {'.png', '.json'}:
            add(path)
    # These public sample JSONs are required by existing regression tests.
    for name in ('sample-20261026/episode.json', 'sample-20261026/timings.json',
                 'sample-20261026/captions.json', 'sample-20261026-v5/episode.json'):
        add(news / 'episodes' / name)
    for name in ('generate_job.py', 'audio_cleanup.py', 'common.py'):
        add(source / 'Voice_Generate/tools' / name)
    for name in ('LICENSE',):
        add(source / 'Voice_Generate' / name)
    add(source / 'export_news_source.py')
    forbidden = {'.git', '.env', 'node_modules', '__pycache__', '.cache', 'private',
                 'browser-profile', 'admin_retrain', 'admin_voice_study'}
    entries = []
    for relative in sorted(files):
        if forbidden.intersection(relative.parts):
            raise ValueError('Forbidden path selected: ' + str(relative))
        original = source / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        if sha(original) != sha(target):
            raise ValueError('Copy mismatch: ' + str(relative))
        change = None
        if relative.as_posix() == 'News_Video/test_pipeline.py':
            text = target.read_text(encoding='utf-8')
            text = text.replace('    def test_white_theme_and_source_mapping(self):',
                "    @unittest.skipUnless((Path(__file__).parent/'data/news.sqlite3').is_file(), "
                "'Production news database is excluded from the source snapshot')\n"
                '    def test_white_theme_and_source_mapping(self):')
            target.write_text(text, encoding='utf-8')
            change = 'Skip the production database mapping check when the private local database is absent.'
        entries.append({'file': relative.as_posix(), 'bytes': target.stat().st_size,
                        'source_sha256': sha(original), 'export_sha256': sha(target),
                        **({'change': change} if change else {})})
    result = {'snapshot_date': '2026-10-26', 'files': entries,
              'excluded': ['internal instructions, handoff documents, historical state and skill snapshots',
                           'credentials and browser profiles', 'model weights and training projects',
                           'reference audio', 'news database and collection history', 'release videos',
                           'generated film and audio', 'node_modules and runtimes', 'Microsoft fonts'],
              'note': 'Source snapshot, not a self-contained TTS installation. See README.md.'}
    (destination / 'SOURCE_MANIFEST.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(entries), 'bytes': sum(x['bytes'] for x in entries),
                      'destination': str(destination), 'copy_hashes_verified': True}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    export(args.source, args.destination)
