"""Read-only static scan for the C1 declaration (no file is written outside stdout).

Which c20aff1d documents named by the OUC runtime strings (codex prepare_next.py:61-63 selection)
mention, as a path string, one of the Omega-bound seeds or a document that mentions one
(fixpoint, the same reachability that prepare_next.py:96-104 iterates). Reads blobs with
`git show c20aff1d:<path>`; prints the closure with the referring JSON pointers and whether
each reference is a {path, sha256} object or a plain string.
"""
import json, subprocess, sys

GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
REV = 'c20aff1d'
BS = chr(92)
SEEDS = ['diagnostics/sdmpc_n31_20260924/scenario/control_area_membership_213a5d.json',
         'diagnostics/control_area_route_contract_physical_routes.json',
         'diagnostics/sdmpc_n31_20260924/scenario/physical_projection_support_635_proposal_ec2393.json']


def blob(path):
    return subprocess.run(['git', '-C', GWT8, 'show', REV + ':' + path], capture_output=True, check=True).stdout


def strings(x, p=''):
    if isinstance(x, str):
        yield p, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from strings(v, p + '/' + k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from strings(v, p + '/' + str(i))


cfg = json.loads(blob('diagnostics/sdmpc_n31_20260924/config_n31_v2.json'))
for k in ('_repin', 'notes', '_n31_note', '_canonical', '_canon_note', '_ver2_note', 'description'):
    cfg.pop(k, None)
docs = sorted({v.replace(BS, '/') for _, v in strings(cfg) if v.endswith('.json')})
loaded = {}
for d in docs:
    try:
        loaded[d] = json.loads(blob(d))
    except Exception as exc:  # not a file at this revision
        print('SKIP', d, type(exc).__name__)
targets = set(SEEDS)
changed = True
hits = {}
while changed:
    changed = False
    for d, doc in loaded.items():
        if d in SEEDS:
            continue
        for ptr, v in strings(doc):
            if v.replace(BS, '/') in targets:
                parent = ptr.rsplit('/', 1)
                kind = 'path+sha' if parent[1] == 'path' else 'string'
                hits.setdefault(d, set()).add((ptr, v.replace(BS, '/'), kind))
                if d not in targets:
                    targets.add(d)
                    changed = True
print('OUC runtime .json docs:', len(docs), 'loaded:', len(loaded))
for d in sorted(hits):
    print('DOC', d)
    for ptr, v, kind in sorted(hits[d]):
        print('   ', ptr, '->', v, '[' + kind + ']')
