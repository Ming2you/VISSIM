import csv, sys
label, T = sys.argv[1], int(sys.argv[2])
ref = sys.argv[3] if len(sys.argv) > 3 else 'recorded'
def path(l):
    if l == 'recorded': return 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_%06d.csv' % T
    return 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/%s/T%06d/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_%06d.csv' % (l, T, T)
a = list(csv.DictReader(open(path(label), encoding='utf-8')))
b = list(csv.DictReader(open(path(ref), encoding='utf-8')))
print('rows', len(a), len(b))
n = 0; kinds = {}
for i, (x, y) in enumerate(zip(a, b)):
    d = {k: (x[k], y[k]) for k in x if x[k] != y.get(k)}
    if d:
        n += 1; kinds[x['kind']] = kinds.get(x['kind'], 0) + 1
        if n <= 25: print(i, x['kind'], x['id'], x['sc_no'], d)
print('rows differing', n, kinds)
