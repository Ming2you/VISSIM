"""Extra check for the local files that neither FILE_MANIFEST.csv nor any SHA256SUMS.txt lists (code/.git/*):
compare sha256 of the local copy with the shared drive copy (shared drive read only). Writes verify_unlisted.json."""
import hashlib, io, json, os, time

LOCAL = 'D:/VISSIM_handoff/20261024'
SHARED = 'Y:/99_임시휴지통/20261024'
HERE = os.path.dirname(os.path.abspath(__file__)).replace(chr(92), '/')
with io.open(HERE + '/verify_manifest.json', encoding='utf-8') as f:
    todo = json.load(f)['summary']['local_files_unchecked_by_manifest_or_sums']


def sha(p):
    h = hashlib.sha256()
    n = 0
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


t0 = time.time()
out = []
for rel in todo:
    assert not rel.startswith('sealed/')
    a, b = sha(LOCAL + '/' + rel), sha(SHARED + '/' + rel)
    out.append({'path': rel, 'bytes': a[1], 'local_sha256': a[0], 'shared_sha256': b[0], 'same': a == b})
res = {'checked_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'seconds': round(time.time() - t0, 1),
       'files': len(out), 'same': sum(r['same'] for r in out), 'bytes': sum(r['bytes'] for r in out), 'results': out}
with io.open(HERE + '/verify_unlisted.json', 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print('UNLISTED', res['files'], 'same', res['same'], 'bytes', res['bytes'], 'sec', res['seconds'])
