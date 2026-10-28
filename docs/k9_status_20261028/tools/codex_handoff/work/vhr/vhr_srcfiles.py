# vhr_srcfiles.py - SOURCE_FILES.csv check with Windows long-path prefix, four trees.
import csv, hashlib, json, os
PFX = chr(92) * 2 + '?' + chr(92)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


rows = list(csv.DictReader(open('D:/VISSIM_handoff/20261024/code/handoff/SOURCE_FILES.csv', encoding='utf-8-sig')))
res = {}
for root in ['D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/code', 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code',
             'D:/VISSIM_handoff/20261024/code', 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff']:
    bad = 0; miss = 0; longp = 0
    for r in rows:
        p = os.path.abspath(root + '/' + r['path'])
        if len(p) >= 250:
            longp += 1
        lp = PFX + p
        if not os.path.isfile(lp):
            miss += 1; continue
        if sha(lp) != r['sha256']:
            bad += 1
    res[root] = dict(rows=len(rows), missing=miss, sha_diff=bad, long_paths=longp)
print(json.dumps(res, indent=1))
json.dump(res, open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/srcfiles_check.json', 'w'), indent=1)
