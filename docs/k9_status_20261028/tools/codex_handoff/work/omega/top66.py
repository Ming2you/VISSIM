# top contributors among the 66 links added in Omega701 (Omega701 - Omega635), per seed, ours 0-9000 (read only)
import csv, json, collections, sys
sys.dont_write_bytecode = True
ex = json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8-sig'))
added = ex['controlled_intersection_expansion']['added_links']
print('added type', type(added[0]).__name__, str(added[:2])[:400])
in701 = set(map(int, ex['inside_links']))
prev = set(map(int, ex['controlled_intersection_expansion']['previous_inside_links']))
A = in701 - prev
val = collections.defaultdict(float)
with open('omega701_per_link.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['convention_window'] == 'ours_9000' and int(r['link']) in A:
            val[(r['run'], int(r['link']))] = float(r['veh_h'])
rows = []
for l in sorted(A):
    d = {}
    for p, a, b in (('VA-NC3', 'va', 'nc3'), ('J1-NC3', 'j1', 'nc3')):
        for s in (31, 41, 43):
            d[(p, s)] = val[('%s_s%d' % (a, s), l)] - val[('%s_s%d' % (b, s), l)]
    lv = [val[('nc3_s%d' % s, l)] for s in (31, 41, 43)]
    rows.append((l, d, lv))
rows.sort(key=lambda r: -sum(abs(r[1][('VA-NC3', s)]) for s in (31, 41, 43)))
tot = {k: sum(r[1][k] for r in rows) for k in rows[0][1]}
print('total', {k: round(v, 1) for k, v in tot.items()})
for l, d, lv in rows[:12]:
    print(l, 'NC3', [round(x, 1) for x in lv], 'VA-NC3', [round(d[('VA-NC3', s)], 1) for s in (31, 41, 43)],
          'J1-NC3', [round(d[('J1-NC3', s)], 1) for s in (31, 41, 43)])
json.dump({'added_66': sorted(A), 'rows': [(l, {'%s|s%d' % k: v for k, v in d.items()}, lv) for l, d, lv in rows]},
          open('top66.json', 'w', encoding='utf-8'), indent=0)
