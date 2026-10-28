# -*- coding: utf-8 -*-
"""O4 (2026-10-24 rmcause): join model predictions (model_<tag>.json) with VISSIM FZP events (<tag>.json,
<tag>_split.json) in exactly the decision windows. Reads only the o1o4 outputs. Writes o1o4/out/*.
Window: decision T applies at sim T (action_<T>.json.applied first field = T); the model window is
final_constraints.physical_ramp_merge [start_sec, end_sec] = [T, T+450]. FZP frames are at t = 5k + 0.1, an event
detected at frame t happened in (t-5, t]; counting detect times in (T+0.1, T+450.1] covers [T, T+450] up to 0.1 s.
"""
import csv, json, math, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGS = ['va_s31', 'va_s41', 'va_s43', 'j1_s31r', 'j1_s41', 'j1_s43']
LABEL = {'va_s31': 'V-A v3c3-s31', 'va_s41': 'V-A v3c3-s41', 'va_s43': 'V-A v3c3-s43',
         'j1_s31r': 'J1 v3c3-s31r', 'j1_s41': 'J1 v3c3-s41', 'j1_s43': 'J1 v3c3-s43'}
RAMPS = {'RM_C10639': '10639', 'RM_C10681': '10681', 'RM_C10490': '10490', 'RM_C10484': '10484'}
FEED = {'RM_C10639': ('70', 10639), 'RM_C10681': ('68', 10681), 'RM_C10490': ('129', 10490), 'RM_C10484': ('31', 10484)}
NODE = {'RM_C10681': (3.0, 2.0), 'RM_C10484': (2.5, 2.5)}   # config_n31_v2.json:8105-8116 / REF:8013-8024
LANES = {'RM_C10681': 2}
G10 = {r: LANES.get(r, 1) * 4.2 * 360.0 for r in RAMPS}     # service table g10 (veh/h), CFG:7525-7535


def gap(q, tc, tf):
    if q <= 0:
        return 3600.0 / tf
    return q * math.exp(-q * tc / 3600.0) / -math.expm1(-q * tf / 3600.0)


def cnt(ev, a, b):
    return sum(1 for e in ev if a < e[0] <= b)


def q(xs, p):
    s = sorted(xs)
    if not s:
        return None
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def summ(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    if not xs:
        return None
    return {'n': len(xs), 'min': min(xs), 'p10': q(xs, .1), 'median': statistics.median(xs), 'p90': q(xs, .9),
            'max': max(xs), 'mean': statistics.fmean(xs)}


def main():
    below_normal()
    os.makedirs(os.path.join(BASE, 'out'), exist_ok=True)
    rows = []
    for tag in TAGS:
        mp = os.path.join(BASE, 'model', 'model_%s.json' % tag)
        fp = os.path.join(BASE, 'fzp', '%s.json' % tag)
        sp = os.path.join(BASE, 'fzp', '%s_split.json' % tag)
        if not (os.path.isfile(mp) and os.path.isfile(fp)):
            print('missing', tag); continue
        M = json.load(open(mp, encoding='utf-8'))
        F = json.load(open(fp, encoding='utf-8'))
        S = json.load(open(sp, encoding='utf-8')) if os.path.isfile(sp) else None
        for rec in M['records']:
            T = rec['T']
            w0, w1 = rec['window']
            dur = w1 - w0
            a, b = w0 + 0.1, w1 + 0.1
            b0 = w0 + 150.1
            for r, c in RAMPS.items():
                mer, ent, hed = F['merges'][c], F['entries'][c], F['heads'][c]
                vm = cnt(mer, a, b); ve = cnt(ent, a, b); vh = cnt(hed, a, b)
                vm0 = cnt(mer, a, b0); ve0 = cnt(ent, a, b0)
                def stock(t):
                    s = F['snapshots'].get('%.1f' % (t + 0.1), {}).get(c)
                    if s is None:
                        return None
                    return sum(v[0] + v[1] for v in s.values())
                def slow(t):
                    s = F['snapshots'].get('%.1f' % (t + 0.1), {}).get(c)
                    return None if s is None else sum(v[2] for v in s.values())
                s0, s1 = stock(w0), stock(w1)
                cr = F['cross'][c]
                lane_q = {l: cnt([e for e in cr if e[1] == l], a, b) * 3600.0 / dur for l in (1, 2, 3, 4)}
                nl = sum(1 for l in lane_q if lane_q[l] > 0) or 1
                q_avg = sum(lane_q.values()) / nl
                node = NODE.get(r)
                pr = rec['pred_rate'][r]
                pv = rec['pred_veh'][r]
                qs = (rec.get('queues_selected') or {}).get(r) or {}
                ends = sorted(qs, key=float)
                qend = qs[ends[-1]] if ends else None
                init = (rec.get('init') or {}).get(r) or {}
                i0 = init.get('total')
                arr = pv + qend - i0 if (qend is not None and i0 is not None) else None
                share = None
                if S is not None:
                    fl, cc = FEED[r]
                    deps = [e for e in S['departures'][fl] if a < e[0] <= b]
                    if deps:
                        share = sum(1 for e in deps if e[1] == cc) / len(deps)
                    feed_rate = len(deps) * 3600.0 / dur
                else:
                    feed_rate = None
                g = (rec.get('grad') or {}).get(r) or {}
                row = {'run': LABEL[tag], 'tag': tag, 'T': T, 'ramp': r, 'win_start': w0, 'win_end': w1,
                       'pred_rate': pr, 'pfo_rate': rec['pfo_rate'][r], 'vis_merge_rate': vm * 3600.0 / dur,
                       'ratio_merge': pr / (vm * 3600.0 / dur) if vm else None,
                       'pred_minus_vis_veh': pv - vm,
                       'model_arrival_rate': arr * 3600.0 / dur if arr is not None else None,
                       'vis_entry_rate': ve * 3600.0 / dur,
                       'ratio_arrival': (arr * 3600.0 / dur) / (ve * 3600.0 / dur) if (arr is not None and ve) else None,
                       'vis_head_rate': vh * 3600.0 / dur,
                       'init_stock_model': i0, 'init_stock_vis': s0, 'init_posthead': init.get('posthead'),
                       'end_stock_model': qend, 'end_stock_vis': s1, 'end_slow_vis': slow(w1),
                       'q_b0_model': qs.get(ends[0]) if ends else None, 'stock_b0_vis': stock(w0 + 150),
                       'vis_merge_rate_b0': vm0 * 24.0, 'vis_entry_rate_b0': ve0 * 24.0,
                       'vis_balance_err': (s0 + ve - vm - s1) if (s0 is not None and s1 is not None) else None,
                       'obs_prev150_arrival_rate': (((rec.get('obs150') or {}).get(r) or {}).get('ramp_arrival_cross') or 0) * 24.0 if (rec.get('obs150') or {}).get(r) else None,
                       'far_link_volume': (rec.get('far_link_volume_veh_h') or {}).get(c),
                       'up_q_lane1': lane_q[1], 'up_q_avg_lane': q_avg,
                       'gap_lane1': gap(lane_q[1], *node) if node else None,
                       'gap_avg_lane': gap(q_avg, *node) if node else None,
                       'g10_service': G10[r],
                       'feed_departure_rate': feed_rate, 'vis_feed_share_to_ramp': share,
                       'dNUF_dz_b0': (g.get('0') or {}).get('dNUF_dz_veh_h'),
                       'dNUF_dz_b1': (g.get('1') or {}).get('dNUF_dz_veh_h'),
                       'dNUF_dz_b2': (g.get('2') or {}).get('dNUF_dz_veh_h'),
                       'grad_total_b0': (g.get('0') or {}).get('total'),
                       'grad_total_b1': (g.get('1') or {}).get('total'),
                       'grad_total_b2': (g.get('2') or {}).get('total'),
                       'grad_fwe_b0': ((g.get('0') or {}).get('cost_components_anchor') or {}).get('FW_E'),
                       'grad_fwe_b1': ((g.get('1') or {}).get('cost_components_anchor') or {}).get('FW_E'),
                       'grad_fwe_b2': ((g.get('2') or {}).get('cost_components_anchor') or {}).get('FW_E'),
                       'grad_components_b0': json.dumps((g.get('0') or {}).get('cost_components_anchor') or {}),
                       'grad_components_b1': json.dumps((g.get('1') or {}).get('cost_components_anchor') or {})}
                rows.append(row)
    with open(os.path.join(BASE, 'out', 'o4_rows.csv'), 'w', encoding='utf-8', newline='') as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    summary = {}
    for r in RAMPS:
        for grp, keyf in (('all', lambda x: True), ('VA', lambda x: x['tag'].startswith('va')),
                          ('J1', lambda x: x['tag'].startswith('j1'))) + tuple(
                (t, (lambda tt: (lambda x: x['tag'] == tt))(t)) for t in TAGS):
            sel = [x for x in rows if x['ramp'] == r and keyf(x)]
            if not sel:
                continue
            summary['%s|%s' % (r, grp)] = {k: summ([x[k] for x in sel]) for k in (
                'ratio_merge', 'ratio_arrival', 'pred_rate', 'vis_merge_rate', 'model_arrival_rate', 'vis_entry_rate',
                'end_stock_model', 'end_stock_vis', 'init_stock_vis', 'vis_balance_err', 'vis_feed_share_to_ramp',
                'gap_avg_lane', 'gap_lane1', 'up_q_avg_lane', 'up_q_lane1', 'vis_merge_rate_b0', 'obs_prev150_arrival_rate',
                'dNUF_dz_b0', 'dNUF_dz_b1', 'dNUF_dz_b2', 'grad_total_b0', 'grad_total_b1', 'grad_fwe_b0', 'feed_departure_rate')}
            summary['%s|%s' % (r, grp)]['n_pred_gt_vis'] = sum(1 for x in sel if x['ratio_merge'] and x['ratio_merge'] > 1)
            summary['%s|%s' % (r, grp)]['n_abs_dNUF_gt_1'] = sum(1 for x in sel for k in ('dNUF_dz_b0', 'dNUF_dz_b1', 'dNUF_dz_b2') if x[k] is not None and abs(x[k]) > 1)
            summary['%s|%s' % (r, grp)]['n_abs_grad_gt_1e-6'] = sum(1 for x in sel for k in ('grad_total_b0', 'grad_total_b1', 'grad_total_b2') if x[k] is not None and abs(x[k]) > 1e-6)
    json.dump(summary, open(os.path.join(BASE, 'out', 'o4_summary.json'), 'w', encoding='utf-8'), indent=1)
    print('rows', len(rows))
    for k, v in summary.items():
        if k.split('|')[1] in ('all', 'VA', 'J1'):
            print(k, 'ratio_merge', {kk: round(vv, 3) for kk, vv in (v['ratio_merge'] or {}).items()},
                  'ratio_arrival', {kk: round(vv, 3) for kk, vv in (v['ratio_arrival'] or {}).items()})


if __name__ == '__main__':
    main()
