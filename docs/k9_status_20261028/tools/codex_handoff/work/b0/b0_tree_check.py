# B0: compare the b0 code tree with the A1 frozen tree's FREEZE.json file table (read-only on both).
# usage: python -B b0_tree_check.py <out.json>
import hashlib, json, os, sys
BS = chr(92)
B0 = BS*2 + '?' + BS + 'D:' + BS + 'VISSIM-merge' + BS + 'k8_gate_trees' + BS + 'codexhandoff' + BS + 'b0' + BS + 'code'
FRZ = 'D:/VISSIM_runtime/20261025_codex_a1/frozen/sdmpc31_a49981ff_202610251820/FREEZE.json'
EXCL = {'__pycache__', '.pytest_cache', '.git', '__tangentcache__'}
ref = json.load(open(FRZ, encoding='utf-8'))['files']
cur = {}
for root, dirs, files in os.walk(B0):
    dirs[:] = [d for d in dirs if d not in EXCL]
    for f in files:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, B0).replace(BS, '/')
        cur[rel] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
changed = sorted(k for k in cur if k in ref and cur[k] != ref[k])
added = sorted(k for k in cur if k not in ref)
removed = sorted(k for k in ref if k not in cur)
out = {'b0': B0, 'ref': FRZ, 'n_b0': len(cur), 'n_ref': len(ref),
       'changed': [{'path': k, 'ref': ref[k], 'b0': cur[k]} for k in changed],
       'added': [{'path': k, 'b0': cur[k]} for k in added], 'removed': removed}
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('n_b0', len(cur), 'n_ref', len(ref), 'changed', len(changed), 'added', len(added), 'removed', len(removed))
