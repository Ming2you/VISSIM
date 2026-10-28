# Review probe (read-only, 2026-10-27 KST): FO preflight provenance (s31, s41, s43) vs the B run provenance of the same
# seed, leaf diff after normalizing the two path prefixes (frozen tree, results root). Reports every remaining leaf.
import json, sys
BS = chr(92)
def leaves(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, p + '/' + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, p + '/' + str(i))
    else:
        yield p, x
FRZB1 = BS.join(['k8_gate_trees', 'codexhandoff', 'b1', 'frozen', 'sdmpc31_a49981ff_202610261410'])
FRZFO = BS.join(['k8_gate_trees', 'codexhandoff', 'fo', 'frozen', 'sdmpc31_a49981ff_202610271954'])
out = {}
for s in (31, 41, 43):
    fo_root = BS.join(['D:', 'VISSIM-merge', 'k8_gate_trees', 'codexhandoff', 'fo', 'runner_preflight', 's%d' % s])
    b_root = BS.join(['D:', 'VISSIM_runs', '20261026_codex_b_v3c3', 's%d' % s])
    fo = json.load(open(BS.join([fo_root, 'sdmpc', 'preflight', 'run_provenance_sdmpc31_sdmpc9000_s%d.json' % s]), encoding='utf-8-sig'))
    b = json.load(open(BS.join([b_root, 'sdmpc', 'run_provenance_sdmpc31_sdmpc9000_s%d.json' % s]), encoding='utf-8-sig'))

    def norm(v):
        if not isinstance(v, str):
            return v
        for a in (FRZB1, FRZFO):
            v = v.replace(a, 'FRZ').replace(a.replace(BS, '/'), 'FRZ')
        for a, r in ((BS.join([fo_root, 'sdmpc', 'preflight']), 'RUN'), (BS.join([b_root, 'sdmpc']), 'RUN'), (fo_root, 'ROOT'), (b_root, 'ROOT')):
            v = v.replace(a, r).replace(a.replace(BS, '/'), r)
        return v
    F = {k: norm(v) for k, v in leaves(fo)}
    B = {k: norm(v) for k, v in leaves(b)}
    d = sorted(k for k in set(F) | set(B) if F.get(k, '<none>') != B.get(k, '<none>'))
    rows = [(k, str(B.get(k, '<none>'))[:100], str(F.get(k, '<none>'))[:100]) for k in d]
    out['s%d' % s] = rows
    print('== s%d differing leaves after path normalization: %d' % (s, len(d)))
    for k, bv, fv in rows:
        print('  ', k, '| B:', bv, '| FO:', fv)
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
