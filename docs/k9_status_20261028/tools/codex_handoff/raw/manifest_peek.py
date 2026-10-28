"""Count-only look at FILE_MANIFEST.csv on the shared drive (read only). Never prints sealed/ path names."""
import csv, io, collections
ROOT = 'Y:/99_임시휴지통/20261024'
BS = chr(92)


def norm(p):
    return p.replace(BS, '/')


with io.open(ROOT + '/FILE_MANIFEST.csv', encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
print('rows', len(rows), 'cols', list(rows[0].keys()))
sealed = [r for r in rows if norm(r['path']).startswith('sealed/')]
other = [r for r in rows if not norm(r['path']).startswith('sealed/')]
print('sealed_rows', len(sealed), 'sealed_bytes', sum(int(r['bytes']) for r in sealed))
print('nonsealed_rows', len(other), 'nonsealed_bytes', sum(int(r['bytes']) for r in other))
nested = [r['path'] for r in other if 'sealed' in [p.lower() for p in norm(r['path']).split('/')[:-1]]]
print('nonsealed rows with a dir component named sealed', len(nested))
for p in nested[:20]:
    print('  ', p)
top = collections.Counter(norm(r['path']).split('/')[0] if '/' in norm(r['path']) else '<root>' for r in other)
print('top', dict(top))
print('root files in manifest', [r['path'] for r in other if '/' not in norm(r['path'])])
sums = [r['path'] for r in other if r['path'].endswith('SHA256SUMS.txt')]
print('SHA256SUMS.txt rows (non-sealed)', len(sums))
print('backslash paths', sum(BS in r['path'] for r in rows), 'dup paths', len(rows) - len(set(r['path'] for r in rows)))
print('bad sha', sum(len(r['sha256']) != 64 for r in rows))
