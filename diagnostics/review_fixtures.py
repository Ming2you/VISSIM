"""Portable, explicitly relocated historical inputs for diagnostic tests only.

The archive retains original bytes. Restored JSON copies change only absolute
workspace path aliases, with every replacement recorded outside the JSON.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'diagnostics/fixtures/control_area_v1.zip'
DEFAULT = ROOT/'.review-fixtures/control-area-v1'
ENVIRONMENT = 'VISSIM_REVIEW_FIXTURE_ROOT'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture_root():
    specified = os.environ.get(ENVIRONMENT)
    if specified:
        destination = Path(specified).resolve()
        if not (destination/'restoration.json').is_file():
            raise FileNotFoundError(f'{ENVIRONMENT} does not point to restored fixtures: {destination}')
        return destination
    return DEFAULT if (DEFAULT/'restoration.json').is_file() else None


def fixture_path(path):
    """Redirect historical run inputs only; never fall back when activated."""
    path = Path(path)
    if not path.is_absolute():
        path = ROOT/path
    location = fixture_root()
    if location is None:
        return path
    try:
        path.relative_to(location)
        return path
    except ValueError:
        pass
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return path
    if relative.parts[:2] != ('evaluation', 'runs'):
        return path
    redirected = location/'relocated'/relative
    if not redirected.exists():
        raise FileNotFoundError(f'Historical input is not included in the portable fixture: {relative}')
    return redirected


def reference_source(commit, path):
    location = fixture_root()
    if location is None:
        return None
    reference = location/'raw/reference_sources'/commit/path
    if not reference.is_file():
        raise FileNotFoundError(f'Fixed historical source absent from fixture: {commit}:{path}')
    return reference.read_text(encoding='utf-8')


def _safe_relative(value):
    # ZIP names are canonical POSIX paths. On Windows, a backslash embedded in
    # one POSIX component would become a separator when converted to Path.
    if not isinstance(value, str) or '\\' in value:
        raise ValueError(f'Unsafe archive path: {value}')
    relative = PurePosixPath(value)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or any(':' in part for part in relative.parts):
        raise ValueError(f'Unsafe archive path: {value}')
    return Path(*relative.parts)


def _relocate(document, old_roots, repo_root, relocated_root):
    changes = []
    def walk(value, pointer=''):
        if isinstance(value, dict):
            return {key: walk(item, pointer+'/'+str(key).replace('~', '~0').replace('/', '~1')) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item, pointer+'/'+str(index)) for index, item in enumerate(value)]
        if isinstance(value, str):
            # A whole string under the recorded workspace is a file-location
            # alias. Embedded commands/descriptions and other strings stay put.
            candidate = PureWindowsPath(value)
            for old_root in old_roots:
                try:
                    relative = candidate.relative_to(PureWindowsPath(old_root))
                except ValueError:
                    continue
                base = relocated_root if relative.parts[:2] == ('evaluation', 'runs') else repo_root
                replacement = str(base.joinpath(*relative.parts))
                if replacement != value:
                    changes.append({'pointer': pointer, 'before': value, 'after': replacement,
                                    'reason': 'absolute recorded workspace file-location alias'})
                return replacement
        return value
    return walk(document), changes


def restore(destination, *, archive=ARCHIVE, repo_root=ROOT):
    destination, repo_root = Path(destination).resolve(), Path(repo_root).resolve()
    if not destination.is_relative_to((ROOT/'.review-fixtures').resolve()):
        raise ValueError('Fixture destination must stay within this checkout .review-fixtures subtree')
    if destination.exists():
        raise FileExistsError(f'Refusing to overwrite fixture directory: {destination}')
    archive = Path(archive)
    archive_manifest = json.loads(archive.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    if sha(archive.read_bytes()) != archive_manifest['sha256']:
        raise ValueError('Compressed fixture archive fingerprint differs from its manifest')
    # Only an explicitly named subtree is created; there is no delete/replace.
    with zipfile.ZipFile(archive) as bundle:
        index = json.loads(bundle.read('index.json'))
        payloads = {}
        expected = {'index.json'} | {'raw/'+row['path'] for row in index['files']}
        if len(bundle.namelist()) != len(expected) or set(bundle.namelist()) != expected:
            raise ValueError('Archive entries differ from the exact fixture index')
        for row in index['files']:
            _safe_relative(row['path'])
            data = bundle.read('raw/'+row['path'])
            if sha(data) != row['sha256'] or len(data) != row['bytes']:
                raise ValueError(f'Fixture byte fingerprint differs: {row["path"]}')
            payloads[row['path']] = data
    destination.mkdir(parents=True, exist_ok=False)
    ignore = ROOT/'.review-fixtures/.gitignore'
    if not ignore.exists():
        ignore.write_text('*\n', encoding='utf-8')
    changes, relocated_hashes = {}, {}
    for name, data in payloads.items():
        relative = _safe_relative(name)
        raw = destination/'raw'/relative
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(data)
        if name.startswith('reference_sources/'):
            continue
        relocated = destination/'relocated'/relative
        relocated.parent.mkdir(parents=True, exist_ok=True)
        if relative.suffix.lower() == '.json':
            original = json.loads(data.decode('utf-8-sig'))
            updated, replacements = _relocate(original, index['original_workspace_roots'], repo_root, destination/'relocated')
            if replacements:
                data = (json.dumps(updated, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
                changes[name] = replacements
        relocated.write_bytes(data)
        relocated_hashes[name] = sha(data)
    result = {'archive_sha256': sha(Path(archive).read_bytes()), 'archive': str(Path(archive).resolve()),
              'fixture_root': str(destination), 'repo_root': str(repo_root),
              'raw_files': index['files'], 'path_relocations': changes,
              'relocated_sha256': relocated_hashes,
              'policy': 'Raw bytes retained; relocated copies alter only whole absolute workspace path strings. Run IDs, observation values, source hashes and controls are unchanged.'}
    (destination/'restoration.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=DEFAULT)
    args = parser.parse_args()
    output = restore(args.destination)
    print(json.dumps({'fixture_root': output['fixture_root'], 'raw_files': len(output['raw_files']),
                      'relocated_files': len(output['path_relocations']), 'archive_sha256': output['archive_sha256']}, indent=2))
