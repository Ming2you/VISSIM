"""Compare every candidate input with the bytes Git would check out from index."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = (ROOT / args.manifest).resolve()
    output = (ROOT / args.out).resolve()
    if not manifest_path.is_relative_to(ROOT / 'diagnostics') or not output.is_relative_to(ROOT / 'diagnostics'):
        parser.error('Manifest and output must be under diagnostics')
    index = Path(git('rev-parse', '--git-path', 'index').decode().strip())
    if not index.is_absolute():
        index = ROOT / index
    index_before = sha(index.read_bytes())
    attributes = (ROOT / '.gitattributes').read_bytes()
    staged_attributes = git('show', ':.gitattributes')
    if attributes.replace(b'\r\n', b'\n') != staged_attributes.replace(b'\r\n', b'\n'):
        raise ValueError('Checkout attributes contain unstaged rule changes')
    rel = manifest_path.relative_to(ROOT).as_posix()
    manifest_bytes = git('cat-file', '--filters', ':' + rel)
    if manifest_bytes != manifest_path.read_bytes():
        raise ValueError('Staged candidate manifest differs from working bytes')
    manifest = json.loads(manifest_bytes)
    expected = {p.replace('\\', '/'): h for p, h in manifest['source_sha256'].items()}
    expected.update({r['path'].replace('\\', '/'): r['sha256'] for r in manifest['outputs'].values()})
    rows = []
    for path, digest in sorted(expected.items()):
        resolved = (ROOT / path).resolve()
        if not resolved.is_relative_to(ROOT):
            raise ValueError('Manifest path escapes repository: ' + path)
        working = sha(resolved.read_bytes())
        checkout = sha(git('cat-file', '--filters', ':' + path))
        rows.append({'path': path, 'expected_sha256': digest,
                     'working_sha256': working, 'checkout_sha256': checkout,
                     'match': working == checkout == digest})
    index_after = sha(index.read_bytes())
    attributes_unchanged = attributes == (ROOT / '.gitattributes').read_bytes()
    result = {'schema': 'candidate-staged-checkout/v1',
              'manifest': rel, 'manifest_sha256': sha(manifest_bytes),
              'source_count': len(manifest['source_sha256']), 'output_count': len(manifest['outputs']),
              'checked_paths': len(rows), 'index_sha256_before': index_before,
              'index_sha256_after': index_after, 'index_unchanged': index_before == index_after,
              'staged_attributes_sha256': sha(staged_attributes),
              'attributes_unchanged': attributes_unchanged,
              'success': attributes_unchanged and index_before == index_after and all(r['match'] for r in rows),
              'rows': rows, 'method': 'Read-only git cat-file --filters from staged blobs, using current checkout attributes; no worktree or index writes.'}
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'method')}))
    if not result['success']:
        raise SystemExit('Candidate checkout differs from pinned runtime bytes')


if __name__ == '__main__':
    main()
