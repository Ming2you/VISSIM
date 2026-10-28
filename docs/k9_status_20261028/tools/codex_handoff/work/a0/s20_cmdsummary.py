# command CSV summary vs reference: rows differing by kind, max |delta| per column
import csv, sys, json
label, T = sys.argv[1], int(sys.argv[2]); ref = sys.argv[3] if len(sys.argv) > 3 else 'recorded'
def path(l):
    if l == 'recorded': return 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_%06d.csv' % T
    return 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/%s/T%06d/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_%06d.csv' % (l, T, T)
a = list(csv.DictReader(open(path(label), encoding='utf-8'))); b = list(csv.DictReader(open(path(ref), encoding='utf-8')))
res = {'rows': [len(a), len(b)], 'differing_rows_by_kind': {}, 'max_abs_delta': {}, 'scs': set()}
for x, y in zip(a, b):
    diff = False
    for k in x:
        if x[k] != y[k]:
            diff = True
            try:
                d = abs(float(x[k]) - float(y[k])); res['max_abs_delta'][k] = round(max(res['max_abs_delta'].get(k, 0), d), 6)
            except ValueError:
                res['max_abs_delta'][k] = 'nonnumeric'
    if diff:
        res['differing_rows_by_kind'][x['kind']] = res['differing_rows_by_kind'].get(x['kind'], 0) + 1
        if x['sc_no']: res['scs'].add(x['sc_no'])
res['scs'] = sorted(res['scs'], key=lambda s: int(s))
print(json.dumps({'label': label, 'T': T, 'ref': ref, **res}))
