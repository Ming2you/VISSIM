# vhr_build_tree.py - build an independent replay code tree and check the A0 tree composition.
# Step 1 (robocopy of handoff code/ without .git) is done before this script.
# This script: (a) verifies SOURCE_FILES.csv in the new tree, (b) copies each RESTORED_FILES.json entry
# from the A0 tree only when its bytes equal the ORIGINAL freeze sha, (c) copies the 3 stand-ins,
# (d) lists A0-tree files that are in none of {handoff code, restored, stand-in, caches}.
import csv, hashlib, json, os, shutil, sys

HO = 'D:/VISSIM_handoff/20261024'
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
DST = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/code'
OUT = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/tree_check.json'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


res = {}
# (a) SOURCE_FILES.csv
rows = list(csv.DictReader(open(f'{HO}/code/handoff/SOURCE_FILES.csv', encoding='utf-8-sig')))
bad = [r['path'] for r in rows if not os.path.isfile(f'{DST}/{r["path"]}') or sha(f'{DST}/{r["path"]}') != r['sha256']]
res['source_files_rows'] = len(rows); res['source_files_mismatch'] = len(bad); res['source_files_mismatch_first'] = bad[:5]

freeze = json.load(open(f'{HO}/evidence/original_FREEZE.json', encoding='utf-8'))['files']
# (b) restored
rest = json.load(open(f'{A0}/RESTORED_FILES.json', encoding='utf-8'))
n_ok = 0; problems = []
for e in rest:
    p = e['path']; src = f'{A0}/code/{p}'; dst = f'{DST}/{p}'
    fz = freeze.get(p)
    if fz is None:
        problems.append((p, 'not_in_freeze')); continue
    if os.path.exists(dst):
        problems.append((p, 'already_in_handoff_code')); continue
    s = sha(src)
    if s != fz or s != e['sha256']:
        problems.append((p, 'sha_mismatch', s[:12], fz[:12])); continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    n_ok += 1
res['restored_listed'] = len(rest); res['restored_copied_freeze_sha_equal'] = n_ok
res['restored_problems'] = problems[:20]; res['restored_problem_count'] = len(problems)
res['restored_py_count'] = sum(e['path'].endswith('.py') for e in rest)
# (c) stand-ins
stand = json.load(open(f'{A0}/STANDIN_FILES.json', encoding='utf-8'))
sres = []
for e in stand:
    p = e['path']; src = f'{A0}/code/{p}'; dst = f'{DST}/{p}'
    s = sha(src)
    on_this_pc_original = False
    sres.append(dict(path=p, sha=s, listed=e['standin_sha256'], freeze=freeze.get(p), equal_listed=s == e['standin_sha256'],
                     equal_freeze=s == freeze.get(p), existed_in_handoff=os.path.exists(dst),
                     content=json.load(open(src, encoding='utf-8'))))
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(src, dst)
res['standins'] = sres
# (d) extras in A0 code tree
code_set = set()
for root, dirs, files in os.walk(f'{HO}/code'):
    if '.git' in dirs: dirs.remove('.git')
    for fn in files:
        code_set.add(os.path.relpath(os.path.join(root, fn), f'{HO}/code').replace('\\', '/'))
rest_set = {e['path'] for e in rest}; stand_set = {e['path'] for e in stand}
extras = []; cache = 0
for root, dirs, files in os.walk(f'{A0}/code'):
    for fn in files:
        rel = os.path.relpath(os.path.join(root, fn), f'{A0}/code').replace('\\', '/')
        if rel in code_set or rel in rest_set or rel in stand_set:
            continue
        if '/__pycache__/' in '/' + rel or '/__tangentcache__/' in '/' + rel or rel.endswith(('.pyc', '.nbi', '.nbc')):
            cache += 1; continue
        extras.append(rel)
res['a0_cache_files'] = cache; res['a0_extra_files'] = extras
# also: do handoff code files in A0 tree still match handoff bytes?
chg = []
for rel in sorted(code_set):
    a = f'{A0}/code/{rel}'
    if not os.path.isfile(a): chg.append((rel, 'missing_in_a0')); continue
    if os.path.getsize(a) != os.path.getsize(f'{HO}/code/{rel}') or sha(a) != sha(f'{HO}/code/{rel}'):
        chg.append((rel, 'differs'))
res['a0_handoff_files_changed'] = chg[:20]; res['a0_handoff_files_changed_count'] = len(chg); res['handoff_code_file_count'] = len(code_set)
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('standins',)}, ensure_ascii=False)[:3000])
print([(s['path'][-40:], s['equal_listed'], s['equal_freeze'], s['existed_in_handoff']) for s in sres])
