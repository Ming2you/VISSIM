"""Verify split archive, every unique object, and manifest references in memory."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent


def digest(stream):
    h = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
        size += len(block)
        h.update(block)
    return size, h.hexdigest()


def main():
    manifest = json.loads((HERE / 'evidence_manifest.json').read_text(encoding='utf-8'))
    objects = {row['sha256']: row['bytes'] for row in manifest['files']}
    assert len({row['path'] for row in manifest['files']}) == len(manifest['files'])
    with tempfile.TemporaryFile() as merged:
        for part in manifest['parts']:
            with (HERE / part['name']).open('rb') as f:
                assert digest(f) == (part['bytes'], part['sha256'])
                f.seek(0)
                shutil.copyfileobj(f, merged)
        merged.seek(0)
        with zipfile.ZipFile(merged) as z:
            assert set(z.namelist()) == {'objects/' + key for key in objects}
            for key, size in objects.items():
                with z.open('objects/' + key) as f:
                    assert digest(f) == (size, key), key
    print(json.dumps({'passed': True, 'parts_verified': len(manifest['parts']),
                      'unique_objects_verified': len(objects), 'manifest_files': len(manifest['files']),
                      'new_native_runs': 0, 'new_forecasts': 0}))


if __name__ == '__main__':
    main()
