# Diff the ramp_meter_timing / signal_observation / observation blocks of prov_cmp output after mapping the two frozen roots.
import json, sys
BS = chr(92)
d = json.load(open(sys.argv[1], encoding='utf-8'))
A = 'D:' + BS + 'VISSIM_runtime' + BS + '20261025_codex_a1' + BS + 'frozen' + BS + 'sdmpc31_a49981ff_202610251820'
C = 'D:' + BS + 'VISSIM_runtime' + BS + '20261012_adopted355_vsl_three' + BS + 'frozen' + BS + 'sdmpc31_ca181e84_202610121132'
def leaves(x, p=''):
    if isinstance(x, dict):
        for k, v in x.items(): yield from leaves(v, p + '/' + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x): yield from leaves(v, p + '/' + str(i))
    else:
        yield p, x
for key in ('ramp_meter_timing', 'signal_observation', 'observation'):
    la = dict(leaves(d[key + '_a1'])); lc = dict(leaves(d[key + '_codex']))
    diffs = []
    for k in sorted(set(la) | set(lc)):
        va, vc = la.get(k), lc.get(k)
        if isinstance(va, str): va2 = va.replace(A, 'ROOT').replace(A.replace(BS, '/'), 'ROOT')
        else: va2 = va
        if isinstance(vc, str): vc2 = vc.replace(C, 'ROOT').replace(C.replace(BS, '/'), 'ROOT')
        else: vc2 = vc
        if va2 != vc2: diffs.append((k, va, vc))
    print(key, 'leaves', len(la), len(lc), 'non-path diffs', len(diffs))
    for x in diffs[:10]: print('   ', x)
