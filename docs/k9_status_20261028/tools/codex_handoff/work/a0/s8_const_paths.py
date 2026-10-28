# List path constants (ROOT/WORKSPACE_ROOT/... / "relative") in controller modules and check presence
# in a0/code and in the original freeze record.
import json, os, re
CODE = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code'
FRZ = json.load(open('D:/VISSIM_handoff/20261024/evidence/original_FREEZE.json', encoding='utf-8'))['files']
pat = re.compile(r'(?:ROOT|WORKSPACE_ROOT|REPO_ROOT|_ROOT|root|repo)\s*/\s*["\']([^"\']+\.[A-Za-z0-9]{2,6})["\']')
rows = []
for d in ('evaluation/controllers', 'evaluation'):
    for f in sorted(os.listdir(CODE + '/' + d)):
        if not f.endswith('.py'):
            continue
        txt = open(CODE + '/' + d + '/' + f, encoding='utf-8', errors='ignore').read()
        for m in pat.finditer(txt):
            rel = m.group(1).replace(chr(92), '/')
            present = os.path.exists(CODE + '/' + rel)
            infrz = rel in FRZ
            if not present:
                rows.append((d + '/' + f, rel, infrz))
for r in sorted(set(rows)):
    print(('IN_FREEZE ' if r[2] else 'not_in_freeze ') + r[1] + '   <- ' + r[0])
