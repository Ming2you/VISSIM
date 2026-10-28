# -*- coding: utf-8 -*-
"""O4 (2026-10-24): final joins and summaries. Reads o1o4/out/o4_rows.csv, o1o4/model/model2_*.json,
o1o4/fzp/*_split.json. Writes o1o4/out/o4_final.json and o1o4/out/o4_final_rows.csv. Read-only otherwise."""
import csv, json, math, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGS = ['va_s31', 'va_s41', 'va_s43', 'j1_s31r', 'j1_s41', 'j1_s43']
RAMPS = ['RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
BINS = [(0, 1800), (1800, 3600), (3600, 5400), (5400, 7200), (7200, 9001)]


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def qtl(xs, p):
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {'n': len(xs), 'min': min(xs), 'p10': qtl(xs, .1), 'median': statistics.median(xs),
            'p90': qtl(xs, .9), 'max': max(xs), 'mean': statistics.fmean(xs)}


def cnt(ev, a, b):
    return sum(1 for e in ev if a < e[0] <= b)


def main():
    below_normal()
    rows = list(csv.DictReader(open(os.path.join(BASE, 'out', 'o4_rows.csv'), encoding='utf-8')))
    # FZP records end before 9000 s; windows ending after 9000 s (T = 8700, 8850, 9000) are excluded.
    rows = [x for x in rows if float(x['win_end']) <= 9000.0]
    M2 = {t: {r['T']: r for r in json.load(open(os.path.join(BASE, 'model', 'model2_%s.json' % t), encoding='utf-8'))['records']}
          for t in TAGS}
    SP = {t: json.load(open(os.path.join(BASE, 'fzp', '%s_split.json' % t), encoding='utf-8')) for t in TAGS}
    out_rows = []
    for x in rows:
        tag, T, r = x['tag'], int(x['T']), x['ramp']
        m2 = M2[tag][T]
        w0, w1 = float(x['win_start']), float(x['win_end'])
        dur = w1 - w0
        a, b = w0 + 0.1, w1 + 0.1
        # closest tangent record for an internally consistent mass balance
        best, bd = None, None
        for td in m2['tds']:
            if any(td['pred_veh'].get(k) is None for k in RAMPS):
                continue
            dd = sum(abs(td['pred_veh'][k] - m2['final_pred_veh'][k]) for k in RAMPS)
            if bd is None or dd < bd:
                best, bd = td, dd
        y = dict(x)
        y['td_used'] = best['index'] if best else None
        y['td_pred_minus_final_veh'] = (best['pred_veh'][r] - m2['final_pred_veh'][r]) if best else None
        init = fnum(x['init_stock_model'])
        if best and init is not None and best['queues'].get(r):
            ends = sorted(best['queues'][r], key=float)
            qe = best['queues'][r][ends[-1]]
            q0 = best['queues'][r][ends[0]]
            arr = best['pred_veh'][r] + qe - init
            y['td_end_stock'] = qe
            y['td_q_b0'] = q0
            y['td_arrival_rate'] = arr * 3600.0 / dur
            ve = fnum(x['vis_entry_rate'])
            y['ratio_arrival_td'] = (arr * 3600.0 / dur) / ve if ve else None
        else:
            y['td_end_stock'] = y['td_q_b0'] = y['td_arrival_rate'] = y['ratio_arrival_td'] = None
        fl = (best or {}).get('flows', {})
        if r == 'RM_C10681':
            y['model_wout1004_in_rate'] = sum(v for k, v in fl.items() if k.startswith('movement:SC1004_') and k.endswith('_to_W')) * 3600.0 / dur
            y['model_legsplit1004_rate'] = fl.get('legsplit:SC1004_W_out', 0.0) * 3600.0 / dur
            y['vis_link68_entry_rate'] = cnt(SP[tag]['entries']['68'], a, b) * 3600.0 / dur
            y['vis_link68_dep_rate'] = cnt(SP[tag]['departures']['68'], a, b) * 3600.0 / dur
        elif r == 'RM_C10490':
            y['model_sc1001_onE_rate'] = fl.get('movement:SC1001_W_to_onE', 0.0) * 3600.0 / dur
            y['model_sc1001_onE_arrival_rate'] = fl.get('arrival:SC1001_W_to_onE', 0.0) * 3600.0 / dur
            y['vis_link129_dep_rate'] = cnt(SP[tag]['departures']['129'], a, b) * 3600.0 / dur
        elif r == 'RM_C10639':
            y['model_shared69_to_10639_rate'] = fl.get('storage:shared_69->ramp:RM_C10639', 0.0) * 3600.0 / dur
            y['model_sc1004_onE_rate'] = fl.get('movement:SC1004_W_to_onE', 0.0) * 3600.0 / dur
        elif r == 'RM_C10484':
            y['model_legsplit1001_rate'] = fl.get('legsplit:SC1001_W_out', 0.0) * 3600.0 / dur
            y['vis_link31_dep_rate'] = cnt(SP[tag]['departures']['31'], a, b) * 3600.0 / dur
        out_rows.append(y)
    keys = []
    for y in out_rows:
        for k in y:
            if k not in keys:
                keys.append(k)
    with open(os.path.join(BASE, 'out', 'o4_final_rows.csv'), 'w', encoding='utf-8', newline='') as h:
        w = csv.DictWriter(h, fieldnames=keys)
        w.writeheader(); w.writerows(out_rows)
    res = {'per_run': {}, 'bins_10681': {}, 'checks': {}}
    def F(y, k):
        return fnum(y.get(k))
    for r in RAMPS:
        for grp in TAGS + ['VA', 'J1', 'all']:
            sel = [y for y in out_rows if y['ramp'] == r and (grp == 'all' or y['tag'] == grp or
                   (grp == 'VA' and y['tag'].startswith('va')) or (grp == 'J1' and y['tag'].startswith('j1')))]
            d = {k: summ([F(y, k) for y in sel]) for k in (
                'ratio_merge', 'pred_rate', 'vis_merge_rate', 'td_arrival_rate', 'vis_entry_rate', 'ratio_arrival_td',
                'td_end_stock', 'end_stock_vis', 'init_stock_vis', 'td_q_b0', 'vis_merge_rate_b0', 'up_q_avg_lane',
                'up_q_lane1', 'gap_avg_lane', 'gap_lane1', 'vis_feed_share_to_ramp', 'obs_prev150_arrival_rate',
                'far_link_volume', 'dNUF_dz_b0', 'dNUF_dz_b1', 'dNUF_dz_b2', 'grad_total_b0', 'grad_total_b1',
                'grad_fwe_b0', 'grad_fwe_b1', 'td_pred_minus_final_veh', 'model_wout1004_in_rate',
                'model_legsplit1004_rate', 'vis_link68_entry_rate', 'vis_link68_dep_rate', 'model_sc1001_onE_rate',
                'vis_link129_dep_rate', 'model_shared69_to_10639_rate', 'model_legsplit1001_rate', 'vis_link31_dep_rate')}
            d = {k: v for k, v in d.items() if v is not None}
            d['n_rows'] = len(sel)
            d['n_ratio_gt1'] = sum(1 for y in sel if (F(y, 'ratio_merge') or 0) > 1)
            d['n_abs_dNUF_gt_1'] = sum(1 for y in sel for k in ('dNUF_dz_b0', 'dNUF_dz_b1', 'dNUF_dz_b2') if abs(F(y, k) or 0) > 1)
            d['max_abs_dNUF'] = max((abs(F(y, k) or 0) for y in sel for k in ('dNUF_dz_b0', 'dNUF_dz_b1', 'dNUF_dz_b2')), default=None)
            d['n_abs_grad_gt_1e-6'] = sum(1 for y in sel for k in ('grad_total_b0', 'grad_total_b1', 'grad_total_b2') if abs(F(y, k) or 0) > 1e-6)
            d['max_abs_grad'] = max((abs(F(y, k) or 0) for y in sel for k in ('grad_total_b0', 'grad_total_b1', 'grad_total_b2')), default=None)
            d['max_pred_over_g10'] = max(((F(y, 'pred_rate') or 0) / F(y, 'g10_service') for y in sel), default=None)
            d['n_td_end_stock_lt3'] = sum(1 for y in sel if F(y, 'td_end_stock') is not None and F(y, 'td_end_stock') < 3)
            d['n_td_end_stock'] = sum(1 for y in sel if F(y, 'td_end_stock') is not None)
            d['n_vis_end_stock_lt3'] = sum(1 for y in sel if F(y, 'end_stock_vis') is not None and F(y, 'end_stock_vis') < 3)
            res['per_run']['%s|%s' % (r, grp)] = d
    for grp in ('VA', 'J1'):
        for lo, hi in BINS:
            sel = [y for y in out_rows if y['ramp'] == 'RM_C10681' and y['tag'].lower().startswith(grp.lower()) and lo <= int(y['T']) < hi]
            res['bins_10681']['%s|%d-%d' % (grp, lo, hi)] = {k: summ([F(y, k) for y in sel]) for k in (
                'ratio_merge', 'pred_rate', 'vis_merge_rate', 'td_arrival_rate', 'vis_entry_rate', 'td_end_stock', 'end_stock_vis')}
    a681 = [F(y, 'td_arrival_rate') for y in out_rows if y['ramp'] == 'RM_C10681' and F(y, 'td_arrival_rate') is not None]
    res['checks']['10681_arrival_within_5_of_206.53'] = sum(1 for v in a681 if abs(v - 206.53) <= 5)
    res['checks']['10681_arrival_n'] = len(a681)
    res['checks']['10681_arrival_summary'] = summ(a681)
    # decisions where the model's 10490 NUF derivative is nonzero
    res['checks']['10490_nonzero_dNUF_rows'] = [
        {k: y.get(k) for k in ('run', 'T', 'pred_rate', 'vis_merge_rate', 'td_q_b0', 'td_end_stock', 'end_stock_vis',
                               'dNUF_dz_b0', 'dNUF_dz_b1', 'dNUF_dz_b2', 'grad_total_b0', 'grad_total_b1', 'grad_total_b2')}
        for y in out_rows if y['ramp'] == 'RM_C10490' and any(abs(F(y, k) or 0) > 1 for k in ('dNUF_dz_b0', 'dNUF_dz_b1', 'dNUF_dz_b2'))]
    # rows for the worked example
    res['checks']['example_va_s31_1950'] = [y for y in out_rows if y['tag'] == 'va_s31' and int(y['T']) == 1950]
    json.dump(res, open(os.path.join(BASE, 'out', 'o4_final.json'), 'w', encoding='utf-8'), indent=1, default=str)
    print('ok', len(out_rows))


if __name__ == '__main__':
    main()
