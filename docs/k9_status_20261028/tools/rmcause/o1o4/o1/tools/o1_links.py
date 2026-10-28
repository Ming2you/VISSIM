r"""O1 step 4: link-level 150 s series around the FW_E meters and the FW_W off-ramps that land on meter approaches
(RM, NC3, V-A, seeds 31/41), from the stage-1 scans already made (no FZP read).  Also the 1098 / 1099 uninserted
series (NC3 anchor, union UC from o1_metrics.json definitions) and FW_E zone / cell speeds.
python -B o1_links.py -> o1o4/o1/out/o1_links.json, o1_links_300s.csv"""
import csv
import io
import json
import os
import sys

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
O1 = os.path.dirname(HERE)
OUT = os.path.join(O1, 'out')
SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
STAGE1 = r'D:\VISSIM-merge\tools\stage1'
LINKS = [74, 10699, 2, 10613, 119, 10702, 24,          # FW_E mainline 7
         70, 10639, 68, 10681, 129, 10490, 31, 10484,  # FW_E on-ramp approach + meter connector
         10643, 126, 10682, 121, 10481, 127, 10483, 124,  # FW_E off-ramps + landings
         26, 10771, 120, 10479, 125, 10491, 10645, 123, 10638]  # FW_W mainline + off-ramps (10491->129, 10638->70)
GROUPS = {'M1_fwe7': [74, 10699, 2, 10613, 119, 10702, 24], 'link2': [2], 'fww26': [26], 'fww120': [120],
          'or_DW2_10491': [10491], 'ap129': [129], 'm10490': [10490], 'or_FW2_10638': [10638], 'ap70': [70],
          'm10639': [10639], 'ap68': [68], 'm10681': [10681], 'ap31': [31], 'm10484': [10484],
          'or_DE1_10481_127': [10481, 127], 'or_FE1_10643_126': [10643, 126]}


def jl(p):
    with io.open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def main():
    sys.path.insert(0, STAGE1)
    import stage1_common as C
    C.find_rule_policy = lambda run_dir: None
    import stage1_report as R
    met = jl(os.path.join(OUT, 'o1_metrics.json'))
    union, anchors = met['unions']['UC'], met['anchors_nc3']['UC']
    dirs = {'rm': os.path.join(O1, 'scans'), 'va': os.path.join(SP, 'k92', 'va', 'analysis', 'scans'),
            'nc3': os.path.join(SP, 'j1', 'analysis', 'scans')}
    res = {'groups': GROUPS, 'series': {}, 'frames_meterbound': {}}
    for s in (31, 41):
        for arm in ('rm', 'nc3', 'va'):
            tag = '%s_s%d' % (arm, s)
            d = os.path.join(dirs[arm], tag)
            sc, un = jl(os.path.join(d, 'scan.json')), jl(os.path.join(d, 'uninserted.json'))
            nb = sc['n_bins']
            ser = R.arm_series(sc, un, union, {k: v for k, v in anchors[str(s)].items()})
            lv = sc['link_vh']
            out = {}
            for g, ids in GROUPS.items():
                z = np.zeros(nb)
                for i in ids:
                    z = z + np.asarray(lv.get(str(i), [0.0] * nb), float)
                out[g] = [round(float(x), 3) for x in z]
            for k in ('unins_1098', 'unins_1099'):
                out[k] = [round(float(x), 3) for x in ser[k][0]]
            fs = sc['frame_series']
            t = np.asarray(fs['t'], float)
            mb = {m: np.asarray(fs['meterbound'][m], float) for m in ('RM_C10490', 'RM_C10484', 'RM_C10681', 'RM_C10639')}
            # meterbound vehicles at 150 s marks (frame nearest below each mark + 0.1)
            marks = list(range(150, 9000, 150))
            idx = [int(np.searchsorted(t, m + 0.2)) - 1 for m in marks]
            res['frames_meterbound'][tag] = {m: {'mean_per_bin': [round(float(np.mean(v[(t >= b * 150) & (t < (b + 1) * 150)])), 2)
                                                                  if np.any((t >= b * 150) & (t < (b + 1) * 150)) else None
                                                                  for b in range(nb)],
                                                 'max': float(v.max()), 'max_sec': float(t[int(np.argmax(v))])}
                                             for m, v in mb.items()}
            # FW_E zone and cell speeds per bin
            zs = {}
            for z_, rec in sc['speed']['zones'].items():
                if z_.startswith('FW_E'):
                    vh, vk = np.asarray(rec['veh_h'], float), np.asarray(rec['veh_km'], float)
                    zs[z_] = [round(float(k / h), 1) if h > 0 else None for h, k in zip(vh, vk)]
            out['zone_speed'] = zs
            cells = sc['speed']['cells']['FW_E']
            out['cell_bounds_m'] = cells['bounds_m']
            out['cell_speed'] = [[round(float(k / h), 1) if h > 0 else None for h, k in zip(hh, kk)]
                                 for hh, kk in zip(cells['veh_h'], cells['veh_km'])]
            out['link_full'] = {str(i): round(float(np.sum(lv.get(str(i), [0.0]))), 3) for i in LINKS}
            res['series'][tag] = out
    with io.open(os.path.join(OUT, 'o1_links.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    # 300 s table of selected groups (RM, NC3, V-A per seed)
    keys = ['M1_fwe7', 'link2', 'fww26', 'or_DW2_10491', 'ap129', 'm10490', 'ap31', 'm10484', 'ap68', 'm10681',
            'or_DE1_10481_127', 'unins_1098', 'unins_1099']
    with io.open(os.path.join(OUT, 'o1_links_300s.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        cols = [(tag, k) for tag in ('rm_s31', 'nc3_s31', 'va_s31', 'rm_s41', 'nc3_s41', 'va_s41') for k in keys]
        w.writerow(['t_start', 't_end'] + ['%s|%s' % c for c in cols])
        for b in range(0, 60, 2):
            w.writerow([b * 150, (b + 2) * 150] + ['%.2f' % sum(res['series'][tag][k][b:b + 2]) for tag, k in cols])
    print('ok')


if __name__ == '__main__':
    main()
