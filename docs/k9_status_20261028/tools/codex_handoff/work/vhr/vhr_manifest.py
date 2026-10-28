# vhr_manifest.py - fresh re-verification of the local handoff copy against FILE_MANIFEST.csv and folder SHA256SUMS.txt.
# Rows under sealed/ are only counted (path prefix test), never resolved, opened or hashed.
import csv, hashlib, json, os, time

ROOT = 'D:/VISSIM_handoff/20261024'
OUT = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/manifest_out.json'
PFX = chr(92) * 2 + '?' + chr(92)
t0 = time.time()


def lp(rel):
    return PFX + os.path.abspath(ROOT + '/' + rel)


def is_sealed(rel):
    r = rel.replace(chr(92), '/').lstrip('./')
    return r == 'sealed' or r.startswith('sealed/')


H = {}


def sha(rel):
    if rel not in H:
        h = hashlib.sha256()
        with open(lp(rel), 'rb') as f:
            for b in iter(lambda: f.read(1 << 22), b''):
                h.update(b)
        H[rel] = h.hexdigest()
    return H[rel]


res = {}
rows = 0; sealed_rows = 0; ok = 0; size_diff = 0; hash_diff = 0; missing = 0; nb = 0; listed = set()
with open(ROOT + '/FILE_MANIFEST.csv', encoding='utf-8-sig', newline='') as f:
    rd = csv.reader(f); hdr = next(rd)
    for r in rd:
        rows += 1
        rel = r[0]
        if is_sealed(rel):
            sealed_rows += 1; continue
        listed.add(rel.replace(chr(92), '/'))
        nb += int(r[1])
        p = lp(rel)
        if not os.path.isfile(p):
            missing += 1; continue
        if os.path.getsize(p) != int(r[1]):
            size_diff += 1; continue
        if sha(rel) != r[2].lower():
            hash_diff += 1; continue
        ok += 1
res['manifest'] = dict(header=hdr, rows=rows, sealed_rows_skipped=sealed_rows, nonsealed_rows=rows - sealed_rows, ok=ok, size_diff=size_diff,
                       hash_diff=hash_diff, missing=missing, nonsealed_bytes=nb)
# local tree inventory and per-folder SHA256SUMS.txt
files = []; total = 0
for root, dirs, fns in os.walk(PFX + os.path.abspath(ROOT)):
    rr = os.path.relpath(root, PFX + os.path.abspath(ROOT)).replace(chr(92), '/')
    if rr == '.':
        rr = ''
    if 'sealed' in dirs and rr == '':
        dirs.remove('sealed')
    for fn in fns:
        rel = (rr + '/' + fn) if rr else fn
        files.append(rel); total += os.path.getsize(os.path.join(root, fn))
res['local_tree'] = dict(files=len(files), bytes=total, sealed_dir_exists=os.path.exists(ROOT + '/sealed'),
                         unlisted=len([x for x in files if x not in listed]),
                         unlisted_by_top=dict(sorted({k: sum(1 for x in files if x not in listed and (x.split('/')[0] if '/' in x else '.') == k) for k in set((x.split('/')[0] if '/' in x else '.') for x in files if x not in listed)}.items())))
sums = [x for x in files if x.endswith('SHA256SUMS.txt')]
ent = 0; ent_ok = 0; ent_bad = 0; ent_missing = 0; ent_sealed = 0; malformed = 0
for s in sums:
    base = os.path.dirname(s)
    for line in open(lp(s), encoding='utf-8-sig'):
        line = line.rstrip('\r\n')
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            malformed += 1; continue
        h, name = parts[0].lower(), parts[1].lstrip('*')
        rel = (base + '/' + name) if base else name
        rel = os.path.normpath(rel).replace(chr(92), '/')
        if is_sealed(rel):
            ent_sealed += 1; continue
        ent += 1
        if not os.path.isfile(lp(rel)):
            ent_missing += 1; continue
        if sha(rel) == h:
            ent_ok += 1
        else:
            ent_bad += 1
res['sha256sums'] = dict(files=len(sums), entries=ent, ok=ent_ok, bad=ent_bad, missing=ent_missing, sealed_entries_skipped=ent_sealed, malformed=malformed)
res['hashed_files'] = len(H); res['seconds'] = round(time.time() - t0, 1)
json.dump(res, open(OUT, 'w'), indent=1)
print(json.dumps(res, indent=1))
