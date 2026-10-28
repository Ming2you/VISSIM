# A0b pre-flight (read-only): is a0/code still the A0 tree?
# 1) SOURCE_FILES.csv 3,638 rows sha, 2) RESTORED_FILES.json entries sha, 3) STANDIN_FILES.json standin sha,
# 4) files not in any of the three lists (caches __pycache__/__tangentcache__ and *.pyc counted separately).
import csv, hashlib, json, os, sys
BS = chr(92)
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
CODE = A0 + '/code'


def longp(p):
    return BS + BS + '?' + BS + os.path.abspath(p).replace('/', BS)


def sha(p):
    h = hashlib.sha256()
    with open(longp(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def check(entries, key):
    ok, bad = 0, []
    for path, want in entries:
        try:
            got = sha(CODE + '/' + path)
        except FileNotFoundError:
            bad.append(('missing', path)); continue
        if got == want:
            ok += 1
        else:
            bad.append(('bad', path))
    return {'list': key, 'n': len(entries), 'ok': ok, 'bad': len(bad), 'examples': bad[:10]}


src = [(r['path'], r['sha256']) for r in csv.DictReader(open('D:/VISSIM_handoff/20261024/code/handoff/SOURCE_FILES.csv', encoding='utf-8-sig'))]
rst = [(r['path'], r['sha256']) for r in json.load(open(A0 + '/RESTORED_FILES.json', encoding='utf-8'))]
sti = [(r['path'], r['standin_sha256']) for r in json.load(open(A0 + '/STANDIN_FILES.json', encoding='utf-8'))]
out = {'manifest_sha256': {'RESTORED_FILES.json': sha(A0 + '/RESTORED_FILES.json'), 'STANDIN_FILES.json': sha(A0 + '/STANDIN_FILES.json')},
       'checks': [check(src, 'SOURCE_FILES.csv'), check(rst, 'RESTORED_FILES.json'), check(sti, 'STANDIN_FILES.json')]}
known = {p for p, _ in src} | {p for p, _ in rst} | {p for p, _ in sti}
extra, cache = [], 0
for dp, dn, fn in os.walk(longp(CODE)):
    for f in fn:
        full = os.path.join(dp, f)
        rel = full[len(longp(CODE)) + 1:].replace(BS, '/')
        if rel.startswith('.git/'):
            continue
        if '/__pycache__/' in '/' + rel or '/__tangentcache__/' in '/' + rel or rel.endswith('.pyc'):
            cache += 1; continue
        if rel not in known:
            extra.append(rel)
out['files_outside_lists'] = {'n': len(extra), 'list': sorted(extra)[:50]}
out['cache_files'] = cache
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:2000])
