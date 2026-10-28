# -*- coding: utf-8 -*-
"""rb_discharge.py (c_port/readback, 2026-10-27 KST) - meter discharge per green from rb_fzp_scan output, rule RB_RULE.md K7-K9.

Usage: python -B rb_discharge.py <out_json> <config_json> <group>:<tag>=<run_dir>|<scan_json>|<inpx_json> [...]
  group = 'B' or 'VA' (tables are pooled within a group; per-seed counts are kept).
Read-only; writes only <out_json>.

Block definitions = N34 sec 3.1 (N34_FLOWS.md:191-196), applied unchanged:
  block = [T, T+150] for T = 900, 1050, ..., 8850; green = action CSV green_sec at T; frames (T+0.1, T+150.1] (30 frames).
  pass rate = head crossings x 24 = veh/h/lane.
  Q = all 30 frames have >= 1 vehicle on that lane within 50 m before the head at < 15 km/h.
  B = block mean of slow (< 15 km/h) vehicles after the head on that lane < 50 % of storage after head (length after head / 6.0 m).
  primary = Q and B; secondary = (>= 24 Q frames) and B.
Comparisons: model table 360 x per_lane_veh_per_cycle[g] (config); runner rate 90 g per meter (per lane 90 g / lanes);
N34 rule-RM primary medians (N34_FLOWS.md:203-216, different controller, same v3c3 network) as reference only.
"""
import collections
import csv
import glob
import hashlib
import json
import os
import statistics
import sys

N34_REF = {('10490', 1, 2): 360, ('10490', 1, 3): 600, ('10490', 1, 4): 696, ('10490', 1, 5): 984,
           ('10484', 1, 2): 360, ('10484', 1, 3): 480, ('10484', 1, 4): 708, ('10484', 1, 5): 960,
           ('10681', 2, 4): 648, ('10681', 2, 5): 816, ('10681', 2, 6): 840}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def parse_meta(s):
    d = {}
    for part in (s or '').split(';'):
        if '=' in part:
            k, v = part.split('=', 1)
            d[k] = v
    return d


def med(xs):
    return statistics.median(xs) if xs else None


def main():
    out, cfgp = sys.argv[1], sys.argv[2]
    cfg = json.load(open(cfgp, encoding='utf-8'))
    rm = cfg['actuation']['real_world_ramp_metering']
    tbl = {int(k): float(v) for k, v in rm['per_lane_veh_per_cycle'].items()}
    meter_lanes_cfg = rm.get('meter_lanes', {})
    res = {'tool': 'rb_discharge.py', 'config': [cfgp, sha256(cfgp)], 'per_lane_veh_per_cycle': tbl,
           'model_table_vph_per_lane': {str(g): 360.0 * v for g, v in sorted(tbl.items())}, 'meter_lanes_cfg': meter_lanes_cfg,
           'runs': {}, 'groups': {}}
    blocks_by_group = collections.defaultdict(list)
    for spec in sys.argv[3:]:
        grp, rest = spec.split(':', 1)
        tag, paths = rest.split('=', 1)
        rd, scanp, inpxp = paths.split('|')
        act = sorted(glob.glob(rd + '/action_*.csv'))[0]
        sc = json.load(open(scanp, encoding='utf-8'))
        ij = json.load(open(inpxp, encoding='utf-8'))
        lanes = {c: sorted(int(x) for x in m['heads']) for c, m in ij['meters'].items()}
        storage = {(c, int(ln)): h['storage_after_head_veh'] for c, m in ij['meters'].items() for ln, h in m['heads'].items()}
        cmd = {}
        k0b = {'rows': 0, 'group_rate_eq_table_x_lanes': 0, 'examples': []}
        with open(act, newline='', encoding='utf-8', errors='replace') as fh:
            for row in csv.DictReader(fh):
                if row['kind'] != 'ramp_meter':
                    continue
                T = int(float(row['sim_sec']))
                c = row['id'].replace('RM_C', '')
                g = float(row['green_sec'])
                md = parse_meta(row.get('metadata'))
                grpr = float(md['group_rate_vph']) if 'group_rate_vph' in md else None
                cmd[(c, T)] = (g, float(row['rate_vph']), grpr)
                k0b['rows'] += 1
                gi = int(round(g))
                exp = 360.0 * tbl.get(gi, float('nan')) * len(lanes[c])
                if grpr is not None and abs(grpr - exp) < 1e-6:
                    k0b['group_rate_eq_table_x_lanes'] += 1
                elif len(k0b['examples']) < 10:
                    k0b['examples'].append([c, T, g, grpr, exp])
        cross = collections.Counter()
        for k, c, ln, n in sc['cross']:
            cross[(k, str(c), ln)] += n
        entry = collections.Counter()
        for k, c, ln, n in sc['cross_entry']:
            entry[(k, str(c), ln)] += n
        mf = {}
        for row in sc['mframe']:
            mf[(row[0], str(row[1]), row[2])] = row[3:]
        leave = collections.Counter()
        for k, c, ln, nx, n in sc['leave']:
            leave[(k, str(c))] += n
        run = {'run_dir': rd, 'action_csv': [act, sha256(act)], 'scan': [scanp, sha256(scanp)], 'inpx_json': [inpxp, sha256(inpxp)],
               'fzp_sha256': sc['sha256'], 'header_ok': sc['header_ok'], 'K0b_group_rate': k0b, 'blocks': [], 'checks': {}}
        for c in lanes:
            # K9 check over control frames (900.1, 9000.1]
            ks = range(900 // 5 + 1, 9000 // 5 + 1)
            ncr = sum(cross[(k, c, ln)] for k in ks for ln in [0] + lanes[c])
            nen = sum(entry[(k, c, ln)] for k in ks for ln in [0] + lanes[c])
            nlv = sum(leave[(k, c)] for k in ks)
            run['checks'][c] = {'cross': ncr, 'entry_past_head': nen, 'leave': nlv, 'cross_plus_entry_minus_leave': ncr + nen - nlv,
                                'cross_lane0': sum(cross[(k, c, 0)] for k in ks),
                                'maxpos': {str(r[1]): r[2] for r in sc['maxpos'] if str(r[0]) == c}}
            for T in range(900, 9000, 150):
                if (c, T) not in cmd:
                    continue
                g, rate, grpr = cmd[(c, T)]
                kk = range(T // 5 + 1, T // 5 + 31)
                meter_n = 0
                meter_e = 0
                for ln in lanes[c]:
                    n = sum(cross[(k, c, ln)] for k in kk)
                    e = sum(entry[(k, c, ln)] for k in kk)
                    fr = [mf.get((k, c, ln), [0, 0, 0, 0, 0]) for k in kk]
                    qf = sum(1 for x in fr if x[1] >= 1)
                    ps = sum(x[4] for x in fr) / 30.0
                    pre = sum(x[0] for x in fr) / 30.0
                    st = storage[(c, ln)]
                    bok = ps < 0.5 * st
                    b = {'run': tag, 'meter': c, 'lane': ln, 'T': T, 'g': g, 'cmd_rate_vph': rate, 'model_group_rate_vph': grpr,
                         'n_cross': n, 'n_entry_past_head': e, 'rate_vph_lane': n * 24, 'q_frames': qf, 'pre_mean': round(pre, 3),
                         'post_slow_mean': round(ps, 3), 'storage_after_head': round(st, 2), 'B': bok,
                         'primary': (qf == 30 and bok), 'secondary': (qf >= 24 and bok)}
                    run['blocks'].append(b)
                    blocks_by_group[grp].append(b)
                    meter_n += n
                    meter_e += e
                run['blocks'].append({'run': tag, 'meter': c, 'lane': 'all', 'T': T, 'g': g, 'cmd_rate_vph': rate,
                                      'model_group_rate_vph': grpr, 'n_cross': meter_n, 'n_entry_past_head': meter_e,
                                      'meter_rate_vph': (meter_n + meter_e) * 24})
                blocks_by_group[grp].append(run['blocks'][-1])
        res['runs'][tag] = run
    # tables
    for grp, bl in blocks_by_group.items():
        lane_rows = [b for b in bl if b['lane'] != 'all']
        all_rows = [b for b in bl if b['lane'] == 'all']
        tab = []
        keys = sorted({(b['meter'], b['lane'], int(round(b['g']))) for b in lane_rows})
        for c, ln, g in keys:
            xs = [b for b in lane_rows if b['meter'] == c and b['lane'] == ln and int(round(b['g'])) == g]
            pr = [b for b in xs if b['primary']]
            se = [b for b in xs if b['secondary']]
            nl = len({b2['lane'] for b2 in lane_rows if b2['meter'] == c})
            mt = 360.0 * tbl[g]
            pm = med([b['rate_vph_lane'] for b in pr])
            per_seed = collections.Counter(b['run'] for b in xs)
            per_seed_p = collections.Counter(b['run'] for b in pr)
            tab.append({'meter': c, 'lane': ln, 'g': g, 'blocks': len(xs), 'blocks_by_run': dict(per_seed),
                        'primary': len(pr), 'primary_by_run': dict(per_seed_p),
                        'primary_median': pm, 'primary_min': min((b['rate_vph_lane'] for b in pr), default=None),
                        'primary_max': max((b['rate_vph_lane'] for b in pr), default=None),
                        'veh_per_cycle': (pm / 360.0) if pm is not None else None,
                        'model_table_vph_lane': mt, 'ratio_table': (pm / mt) if pm is not None else None,
                        'cmd_90g_per_lane': 90.0 * g / nl, 'ratio_90g': (pm / (90.0 * g / nl)) if pm is not None else None,
                        'secondary': len(se), 'secondary_median': med([b['rate_vph_lane'] for b in se]),
                        'n34_ref_primary_median': N34_REF.get((c, ln, g)),
                        'q_blocks': sum(1 for b in xs if b['q_frames'] == 30),
                        'q_blocks_not_B': sum(1 for b in xs if b['q_frames'] == 30 and not b['B']),
                        'entry_past_head_in_primary': sum(b['n_entry_past_head'] for b in pr),
                        'all_block_median_rate_lane': med([b['rate_vph_lane'] for b in xs]),
                        'median_pre_mean': med([b['pre_mean'] for b in xs])})
        mtab = []
        for c, g in sorted({(b['meter'], int(round(b['g']))) for b in all_rows}):
            xs = [b for b in all_rows if b['meter'] == c and int(round(b['g'])) == g]
            r = [b['meter_rate_vph'] for b in xs]
            mtab.append({'meter': c, 'g': g, 'blocks': len(xs), 'blocks_by_run': dict(collections.Counter(b['run'] for b in xs)),
                         'cmd_rate_vph': xs[0]['cmd_rate_vph'], 'model_group_rate_vph': xs[0]['model_group_rate_vph'],
                         'median_meter_rate_vph': med(r), 'min': min(r), 'max': max(r),
                         'median_ratio_to_cmd': med([b['meter_rate_vph'] / b['cmd_rate_vph'] for b in xs if b['cmd_rate_vph'] > 0]),
                         'median_ratio_to_model': med([b['meter_rate_vph'] / b['model_group_rate_vph'] for b in xs if b['model_group_rate_vph']]),
                         'blocks_above_cmd': sum(1 for b in xs if b['meter_rate_vph'] > b['cmd_rate_vph']),
                         'blocks_above_model': sum(1 for b in xs if b['model_group_rate_vph'] and b['meter_rate_vph'] > b['model_group_rate_vph'])})
        res['groups'][grp] = {'lane_table': tab, 'meter_table': mtab}
    with open(out + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(res, g, indent=1)
    os.replace(out + '.tmp', out)
    for grp, d in res['groups'].items():
        print('==', grp)
        for t in d['lane_table']:
            if t['primary'] or t['q_blocks']:
                print(' ', t['meter'], t['lane'], 'g%d' % t['g'], 'blk', t['blocks'], 'prim', t['primary'], t['primary_by_run'], 'med', t['primary_median'],
                      'tbl', t['model_table_vph_lane'], 'r', None if t['ratio_table'] is None else round(t['ratio_table'], 2), 'sec', t['secondary'], t['secondary_median'],
                      'qnotB', t['q_blocks_not_B'])


if __name__ == '__main__':
    main()
