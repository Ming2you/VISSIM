r"""VERIFY_N2: meter green vs head discharge per 150 s block (fresh code, from v2_scan outputs + decision_<T>.json).
Block [T, T+150): green g = decision_<T>.json meters.<id>.green_sec. Crossings detected at frames in (T+0.1, T+150.1].
Q = every frame of the block (t in [T, T+150)) has >= 1 vehicle within 50 m before the head with speed < 15 km/h.
B = block mean of slow (< 15 km/h) vehicles after the head < 50 % of (connector length - head) / 6 m.
Also reports the looser 'Q only' and the model table 360 x per_lane_veh_per_cycle (read from CFG 7524-7534)."""
import io
import json
import os
import statistics as st

import numpy as np

VN2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(VN2, 'out')
ROOT = r'D:\VISSIM_runs\20261001_v3c3'
HEAD = {'10639': 314.83469380887993, '10681': 290.72003141146473, '10490': 272.60355928160652, '10484': 377.11076285480539}
LANES = {'10639': 1, '10681': 2, '10490': 1, '10484': 1}


def main():
    cfg = json.load(io.open(os.path.join(VN2, 'src', 'config_n31_v2.json'), encoding='utf-8'))
    res = {'blocks': []}
    for arm, sub in (('rm', 'rm'), ('r1', 'rm10681')):
        for s in (31, 41):
            tag = '%s_s%d' % (arm, s)
            z = np.load(os.path.join(OUT, 'scan_%s.npz' % tag), allow_pickle=True)
            meta = json.load(io.open(os.path.join(OUT, 'scan_%s.json' % tag)))
            order = meta['meter_order']
            t = z['frames_t']
            cr = z['cross']
            for T in range(900, 9000, 150):
                d = json.load(io.open(os.path.join(ROOT, 's%d_v3c3%s' % (s, sub), 'run', 'decision_%d.json' % T), encoding='utf-8-sig'))
                fm = (t >= T) & (t < T + 150)
                for mid, conn in (('RM_C10490', '10490'), ('RM_C10484', '10484'), ('RM_C10681', '10681'), ('RM_C10639', '10639')):
                    if mid not in d['meters']:
                        continue
                    g = d['meters'][mid]['green_sec']
                    mi = order.index(conn)
                    storage = (meta['conn_maxpos'][conn] - HEAD[conn]) / 6.0
                    for ln in range(1, LANES[conn] + 1):
                        qn = z['qnear_%s_%d' % (conn, ln)][fm]
                        qp = z['qpost_%s_%d' % (conn, ln)][fm]
                        n = int(np.sum((cr[:, 0] == mi) & (cr[:, 1] == ln) & (cr[:, 2] > T + 0.1) & (cr[:, 2] <= T + 150.1)))
                        res['blocks'].append({'run': tag, 'T': T, 'meter': conn, 'lane': ln, 'g': g, 'n': n, 'rate': n * 24,
                                              'Q': bool(len(qn) == 30 and np.all(qn >= 1)), 'q_frames': int(np.sum(qn >= 1)),
                                              'B': bool(np.mean(qp) < 0.5 * storage), 'post_slow_mean': round(float(np.mean(qp)), 2),
                                              'storage': round(storage, 1)})
    summ = {}
    for b in res['blocks']:
        k = '%s|lane%d|g%d' % (b['meter'], b['lane'], b['g'])
        e = summ.setdefault(k, {'all': 0, 'QB': [], 'QB_runs': [], 'Q': []})
        e['all'] += 1
        if b['Q']:
            e['Q'].append(b['rate'])
        if b['Q'] and b['B']:
            e['QB'].append(b['rate'])
            e['QB_runs'].append('%s@%d' % (b['run'], b['T']))
    table = {}
    for k, e in sorted(summ.items()):
        table[k] = {'blocks': e['all'], 'QB_n': len(e['QB']), 'QB_median': st.median(e['QB']) if e['QB'] else None,
                    'QB_min': min(e['QB']) if e['QB'] else None, 'QB_max': max(e['QB']) if e['QB'] else None,
                    'Q_n': len(e['Q']), 'Q_median': st.median(e['Q']) if e['Q'] else None, 'QB_runs': e['QB_runs']}
    res['table'] = table
    with io.open(os.path.join(OUT, 'v2_discharge.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    for k, v in table.items():
        if v['QB_n'] or v['Q_n']:
            print(k, {kk: vv for kk, vv in v.items() if kk != 'QB_runs'}, sorted(set(r.split('@')[0] for r in v['QB_runs'])))


if __name__ == '__main__':
    main()
