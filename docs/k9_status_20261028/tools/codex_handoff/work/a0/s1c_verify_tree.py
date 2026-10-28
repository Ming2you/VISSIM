# verify a tree against SOURCE_FILES.csv (all 3638 rows); print counts
import csv, hashlib, os, sys
ROOT = sys.argv[1]
BS = chr(92)


def longp(p):
    return BS + BS + '?' + BS + os.path.abspath(p).replace('/', BS)


def sha(p):
    h = hashlib.sha256()
    with open(longp(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


rows = list(csv.DictReader(open('D:/VISSIM_handoff/20261024/code/handoff/SOURCE_FILES.csv', encoding='utf-8-sig')))
ok = bad = miss = 0
badl = []
for r in rows:
    p = ROOT + '/' + r['path']
    try:
        s = sha(p)
    except FileNotFoundError:
        miss += 1
        badl.append('missing ' + r['path'])
        continue
    if s == r['sha256']:
        ok += 1
    else:
        bad += 1
        badl.append('bad ' + r['path'])
pyc = []
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        if f.endswith('.pyc'):
            pyc.append(os.path.join(dp, f))
print('rows', len(rows), 'ok', ok, 'bad', bad, 'missing', miss, badl[:10], 'pyc_files', len(pyc), pyc[:5])
