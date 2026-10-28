# -*- coding: utf-8 -*-
"""gd_render.py — fill table placeholders {{Tn}} of a narrative markdown from data.json. Read-only; writes <out.md>.
Usage: python -B gd_render.py <data.json> <narrative.md> <out.md>
"""
import json
import sys

ARMN = {'NC3': 'NC3', 'VSL': 'VSL-only', 'VA': 'V-A', 'B': 'B'}
ORDER = ['NC3', 'VSL', 'VA', 'B']
SEEDS = ['s31', 's41', 's43']
KINDN = {'approach_lane': '머리 차로', 'feeder_lane': '공급 차로', 'meter_prehead_lane': '미터 머리 앞', 'meter_approach_lane': '미터 접근',
         'offramp_landing_lane': '진출 착지', 'special': 'D5'}


def rn(run):
    a, s = run.split('_')
    return '%s v3c3-%s' % (ARMN[a], s)


def runs_by_arm():
    return [(a, ['%s_%s' % (a, s) for s in SEEDS]) for a in ORDER]


def f(x, nd=2):
    if x is None:
        return '–'
    if isinstance(x, float):
        return ('%.' + str(nd) + 'f') % x
    return str(x)


def tsec(x):
    return '–' if x is None else '%d' % round(x)


def T_sources(d):
    out = ['| 런 | FZP 이름 | FZP sha256 앞 16 | 프레임 | 행 | 스캔 출력 npz sha256 앞 16 |', '|---|---|---|---:|---:|---|']
    for a, rs in runs_by_arm():
        for r in rs:
            z = d['sources']['fzp'][r]
            out.append('| %s | `%s` | `%s` | %d | %d | `%s` |' % (rn(r), z['name'], z['sha256'][:16], z['frames'], z['rows'], d['sources']['npz'][r][:16]))
    return '\n'.join(out)


def T_xcheck(d):
    out = ['| 런 | 결정 수 | 칸(구간 × 결정) | 같은 몫 | 차(FZP − 제어기) 분포 |', '|---|---:|---:|---:|---|']
    for r, v in d['xcheck_controller'].items():
        out.append('| %s | %d | %d | %.4f | %s |' % (rn(r), v['decisions'], v['cells'], v['equal_share'],
                                                   ', '.join('%s: %d' % (k, n) for k, n in sorted(v['diff_hist'].items(), key=lambda kv: int(kv[0])))))
    return '\n'.join(out)


def T_atS(d):
    out = ['| 종류 | 런 | 번짐 프레임 점유 6 m (10 / 50 / 90 %) | 길이 점유 (10 / 50 / 90 %) | 6 m ≥ 1.0 몫 | 6 m ≥ 0.9 몫 | 길이 ≥ 1.0 몫 |',
           '|---|---|---|---|---:|---:|---:|']
    for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane'):
        for a, rs in runs_by_arm():
            for r in rs:
                v = d['arm_summary'][r].get(kind, {})
                if 'occ6_at_S_q10_50_90' not in v:
                    out.append('| %s | %s | 번짐 없음 | | | | |' % (KINDN[kind], rn(r)))
                    continue
                out.append('| %s | %s | %s | %s | %.2f | %.2f | %.2f |' % (
                    KINDN[kind], rn(r), ' / '.join(f(x) for x in v['occ6_at_S_q10_50_90']), ' / '.join(f(x) for x in v['occL_at_S_q10_50_90']),
                    v['share_S_frames_occ6_ge1'], v['share_S_frames_occ6_ge09'], v['share_S_frames_occL_ge1']))
    return '\n'.join(out)


def T_arm(d):
    out = ['| 종류(용량 2대 이상) | 런 | 구간 수 | 결정 중 하나라도 켜짐 (6 m ≥ 1.0 / 6 m ≥ 0.9 / 길이 ≥ 1.0) | 한 번이라도 켜진 구간 (같은 순서) | 5 s 프레임 중 6 m ≥ 1.0 있는 초 | 번짐 있는 구간 | 번짐 초 합 |',
           '|---|---|---:|---|---|---:|---:|---:|']
    for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane'):
        for a, rs in runs_by_arm():
            for r in rs:
                v = d['arm_summary'][r][kind]
                out.append('| %s | %s | %d | %d / %d / %d | %d / %d / %d | %d | %d | %d |' % (
                    KINDN[kind], rn(r), v['n_seg'], v['dec_any_lane6_1'], v['dec_any_lane6_09'], v['dec_any_laneL_1'],
                    v['seg_ever_lane6_1'], v['seg_ever_lane6_09'], v['seg_ever_laneL_1'], v['frames_any_ge1_6_s'], v['seg_with_spill'], v['spill_s']))
    return '\n'.join(out)


def T_cmp(d, kinds=('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane')):
    RN = {'lane6_1.0': '차로 6 m ≥ 1.0', 'lane6_0.9': '차로 6 m ≥ 0.9', 'laneL_1.0': '차로 길이 ≥ 1.0', 'link6_1.0': '링크 6 m ≥ 1.0',
          'link6_0.9': '링크 6 m ≥ 0.9', 'linkL_1.0': '링크 길이 ≥ 1.0'}
    out = ['| 종류 | 문턱 | ' + ' | '.join(rn(r) for a, rs in runs_by_arm() for r in rs) + ' |', '|---|---|' + '---|' * 12]
    for kind in kinds:
        for rule in ('lane6_1.0', 'lane6_0.9', 'laneL_1.0', 'link6_1.0', 'link6_0.9'):
            cells = []
            for a, rs in runs_by_arm():
                for r in rs:
                    v = d['agg_compare']['%s|%s|%s' % (r, kind, rule)]
                    cells.append('%d: %d/%d/%d · 켜짐 %d (헛 %d)' % (v['n_ep30'], v['lead30'], v['late30'], v['miss30'], v['n_trig'], v['false_trig']))
            out.append('| %s | %s | %s |' % (KINDN[kind], RN[rule], ' | '.join(cells)))
    return '\n'.join(out)


def T_cmp_lead(d):
    out = ['| 종류 | 문턱 | 앞섬 중앙 s (런 순서) | 늦음 중앙 s (런 순서) |', '|---|---|---|---|']
    for kind in ('approach_lane', 'feeder_lane'):
        for rule in ('lane6_1.0', 'lane6_0.9', 'laneL_1.0'):
            ls, gs = [], []
            for a, rs in runs_by_arm():
                for r in rs:
                    v = d['agg_compare']['%s|%s|%s' % (r, kind, rule)]
                    ls.append(tsec(v['lead_s_median']))
                    gs.append(tsec(v['lag_s_median']))
            out.append('| %s | %s | %s | %s |' % (KINDN[kind], rule, ' / '.join(ls), ' / '.join(gs)))
    return '\n'.join(out)


def T_chain(d, chain, ids=None):
    rows = d['chains'][chain]
    first = rows[list(rows)[0]]
    ids = ids or [x['id'] for x in first]
    out = ['| 구간 | ' + ' | '.join(rn(r) for a, rs in runs_by_arm() for r in rs) + ' |', '|---|' + '---|' * 12]
    for sid in ids:
        cells = []
        for a, rs in runs_by_arm():
            for r in rs:
                x = [y for y in rows[r] if y['id'] == sid][0]
                if sid.startswith('W:'):
                    cells.append('%s · %d s' % (tsec(x['first_spill']), x['spill_s']))
                else:
                    cells.append('%s · %d s · %s / %s / %s · max %s' % (tsec(x['first_spill']), x['spill_s'], tsec(x['first_lane6_1']), tsec(x['first_lane6_09']),
                                                                    tsec(x['first_laneL_1']), f(x['max_occ6'])))
        tag = ' (짧음, %.1f대)' % d['per_segment'][sid]['cap_veh']['6'] if (not sid.startswith('W:') and d['per_segment'][sid]['short']) else ''
        out.append('| `%s`%s | %s |' % (sid, tag, ' | '.join(cells)))
    return '\n'.join(out)


def T_fw(d):
    out = ['| 진출 (도로) | ' + ' | '.join(rn(r) for a, rs in runs_by_arm() for r in rs) + ' |', '|---|' + '---|' * 12]
    for w in ('W:10481', 'W:10643', 'W:10483', 'W:10682', 'W:10491', 'W:10638'):
        cells = []
        road = None
        for a, rs in runs_by_arm():
            for r in rs:
                v = d['freeway'][r][w]
                road = v['road']
                cells.append('%d s (%s) · S0 %d · 느림 %d' % (v['block_s'], tsec(v['first_block']), v['offramp_S0_s'], v['slow_last100_s']))
        out.append('| %s (%s) | %s |' % (w[2:], road, ' | '.join(cells)))
    return '\n'.join(out)


def T_ub(d):
    out = ['| 런 | 위 경계가 정지선인 공급 차로 | 번짐 있는 차로 | 번짐 초 합 | 많은 순 5개 (구간 · 초 · 사건 · 첫 시각) |', '|---|---:|---:|---:|---|']
    for a, rs in runs_by_arm():
        for r in rs:
            v = d['upstream_block'][r]
            out.append('| %s | %d | %d | %d | %s |' % (rn(r), v['n_feeder_lanes'], v['n_with_spill'], v['total_spill_s'],
                                                     ' · '.join('`%s` %d s/%d/%s' % (x[0], x[1], x[2], tsec(x[3])) for x in v['top'][:5])))
    return '\n'.join(out)


def T_usg(d):
    out = ['| B 시드 | 결정 | 발동 결정 | 발동 차로·결정 (짧은 / 긴) | 점수 > 0 | 받는 쪽 모두 참(−1) | 긴 구간: 6 m ≥ 1.0 | 긴 구간: 길이 ≥ 1.0 | 긴 구간: [T − 150, T + 300] 번짐 | 링크 6 m ≥ 1.0 | 대수 같음 | 반공간 행 constrained |',
           '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---:|']
    for s in SEEDS:
        v = d['usg']['B_' + s]
        out.append('| v3c3-%s | %d | %d | %d (%d / %d) | %d | %d | %d | %d | %d | %d | %d/%d | %d |' % (
            s, v['decisions'], v['decisions_fired'], v['lane_fires'], v['fires_short'], v['fires_long'], v['fires_score_pos'], v['fires_all_full'],
            v['fires_long_lane6_ge1'], v['fires_long_laneL_ge1'], v['fires_long_spill_near'], v['fires_link6_ge1'], v['veh_match']['equal'], v['veh_match']['total'],
            v['receipts'].get('constrained', 0)))
    return '\n'.join(out)


def T_usg_lanes(d, top=14):
    out = ['| B 시드 | 신호 · 현시 · 링크:차로 | 짧은 구간 | 발동 수 | 6 m ≥ 1.0 | 길이 ≥ 1.0 | 번짐 가까이 | −1 | 첫·끝 T |', '|---|---|---|---:|---:|---:|---:|---:|---|']
    for s in SEEDS:
        v = d['usg']['B_' + s]['by_lane']
        for k, x in sorted(v.items(), key=lambda kv: (-kv[1]['n'], kv[0]))[:top]:
            sig, ph, ll = k.split('|')
            out.append('| v3c3-%s | %s · %s · %s | %s | %d | %d | %d | %d | %d | %d–%d |' % (s, sig, ph.split('_')[-1], ll, '예' if x.get('short') else '아니오', x['n'], x['ge1_6'], x['ge1_L'],
                                                                                  x['spill_near'], x['all_full'], min(x['T']), max(x['T'])))
    return '\n'.join(out)


def T_va(d, top=45):
    rows = []
    for sid, r in d['va_triggers'].items():
        m = d['per_segment'][sid]['meta']
        tot = sum(v[0] + v[1] + v[2] for v in r.values())
        rows.append((tot, sid, m, r))
    rows.sort(key=lambda x: (-x[0], x[1]))
    out = ['| 구간 | 종류 · 분할 | 용량 대 (6 m) | V-A v3c3-s31 (6 m ≥ 1.0 / ≥ 0.9 / 길이 ≥ 1.0 · 번짐 s) | V-A v3c3-s41 | V-A v3c3-s43 |',
           '|---|---|---:|---|---|---|']
    for tot, sid, m, r in rows[:top]:
        cap = d['per_segment'][sid]['cap_veh']['6']
        out.append('| `%s` | %s · %s | %.1f | %s |' % (sid, KINDN.get(m['kind'], m['kind']), m.get('part') or m.get('road') or '–', cap,
                                                     ' | '.join('%d / %d / %d · %d' % tuple(r[k]) for k in ('VA_s31', 'VA_s41', 'VA_s43'))))
    return '\n'.join(out), len(rows)


def T_top_spill(d, arm, top=20):
    rows = []
    for sid, e in d['per_segment'].items():
        if e['short'] or e['meta']['kind'] == 'special':
            continue
        sp = [e['runs']['%s_%s' % (arm, s)]['spill_s'] for s in SEEDS]
        if sum(sp):
            rows.append((sum(sp), sid, e))
    rows.sort(key=lambda x: (-x[0], x[1]))
    out = ['| 구간 | 종류 · 분할 | 용량 대 | 번짐 s (s31 / s41 / s43) | 결정 최대 점유 6 m | 차로 6 m ≥ 1.0 켜진 결정 | ≥ 0.9 | 길이 ≥ 1.0 | 번짐 프레임 점유 6 m 중앙 |',
           '|---|---|---:|---|---|---|---|---|---|']
    for tot, sid, e in rows[:top]:
        rr = [e['runs']['%s_%s' % (arm, s)] for s in SEEDS]
        out.append('| `%s` | %s · %s | %.1f | %s | %s | %s | %s | %s | %s |' % (
            sid, KINDN.get(e['meta']['kind'], e['meta']['kind']), e['meta'].get('part') or e['meta'].get('road') or '–', e['cap_veh']['6'],
            ' / '.join(str(x['spill_s']) for x in rr), ' / '.join(f(x.get('max_occ6')) for x in rr),
            ' / '.join(str(x.get('n_lane6_1.0')) for x in rr), ' / '.join(str(x.get('n_lane6_0.9')) for x in rr),
            ' / '.join(str(x.get('n_laneL_1.0')) for x in rr), ' / '.join(f((x.get('occ6_at_S_q') or [None, None])[1]) for x in rr)))
    return '\n'.join(out)


def T_short(d):
    out = ['| 런 | 짧은 구간 수 (용량 < 2대) | 번짐 있는 수 | 6 m ≥ 1.0 이 한 번이라도 |', '|---|---:|---:|---:|']
    for a, rs in runs_by_arm():
        for r in rs:
            v = d['arm_summary'][r]['short_cap_lt2']
            out.append('| %s | %d | %d | %d |' % (rn(r), v['n_seg'], v['seg_with_spill'], v['seg_ever_lane6_1']))
    return '\n'.join(out)


def T_series(d, sid, key='bin_spill_s'):
    out = ['| 런 | ' + ' | '.join(str(b) for b in d['bins']) + ' |', '|---|' + '---:|' * len(d['bins'])]
    for a, rs in runs_by_arm():
        for r in rs:
            v = d['series'][sid][r][key]
            out.append('| %s | %s |' % (rn(r), ' | '.join(f(x, 2) if isinstance(x, float) else str(x) for x in v)))
    return '\n'.join(out)


def T_fwspeed(d, w):
    out = ['| 런 | ' + ' | '.join(str(b) for b in d['bins']) + ' |', '|---|' + '---:|' * len(d['bins'])]
    for a, rs in runs_by_arm():
        for r in rs:
            v = d['freeway'][r][w]['bin_mean_speed']
            out.append('| %s | %s |' % (rn(r), ' | '.join('–' if x is None else '%.0f' % x for x in v)))
    return '\n'.join(out)


def T_grp(d):
    rows = []
    for g, e in d['per_group'].items():
        if g.startswith('F:') or g == 'D5':
            continue
        tot = sum(e['runs'][r]['n_link6_0.9'] + e['runs'][r]['n_linkL_1.0'] for r in e['runs'])
        if tot:
            rows.append((tot, g, e))
    rows.sort(key=lambda x: (-x[0], x[1]))
    out = ['| 묶음(링크 단위) | 용량 대 (6 m) | ' + ' | '.join(ARMN[a] + ' (6 m ≥ 1.0 · ≥ 0.9 · 길이 ≥ 1.0 결정 수, s31/s41/s43)' for a in ORDER) + ' |',
           '|---|---:|' + '---|' * 4]
    for tot, g, e in rows:
        cells = []
        for a in ORDER:
            rr = [e['runs']['%s_%s' % (a, s)] for s in SEEDS]
            cells.append('%s · %s · %s' % ('/'.join(str(x['n_link6_1.0']) for x in rr), '/'.join(str(x['n_link6_0.9']) for x in rr),
                                          '/'.join(str(x['n_linkL_1.0']) for x in rr)))
        out.append('| `%s` | %.1f | %s |' % (g, e['cap6'], ' | '.join(cells)))
    return '\n'.join(out)


def T_elem(d):
    """element-level coverage: non-short elements with >= 1 spill episode >= 30 s vs ever triggered (decision snapshots)."""
    out = ['| 종류 | 런 | 번짐(≥ 30 s 사건) 있는 구간 | 그중 한 번이라도 켜짐: 6 m ≥ 1.0 / 6 m ≥ 0.9 / 길이 ≥ 1.0 | 켜졌는데 번짐 0 인 구간 (같은 순서) | 첫 켜짐 − 첫 번짐 중앙 s (6 m ≥ 1.0 / ≥ 0.9) |',
           '|---|---|---:|---|---|---|']
    for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane'):
        for a in ORDER:
            for s in SEEDS:
                r = '%s_%s' % (a, s)
                sp = 0
                cov = [0, 0, 0]
                fal = [0, 0, 0]
                dl = [[], []]
                for sid, e in d['per_segment'].items():
                    if e['meta']['kind'] != kind or e['short'] or not e['len_m'] > 0:
                        continue
                    x = e['runs'][r]
                    has = x['cmp']['lane6_1.0']['n_ep30'] > 0
                    trig = [x['n_lane6_1.0'] > 0, x['n_lane6_0.9'] > 0, x['n_laneL_1.0'] > 0]
                    if has:
                        sp += 1
                        for k in range(3):
                            cov[k] += int(trig[k])
                        for k, key in enumerate(('first_lane6_1.0', 'first_lane6_0.9')):
                            if x[key] is not None and x['first_spill'] is not None:
                                dl[k].append(x[key] - x['first_spill'])
                    if x['spill_s'] == 0:
                        for k in range(3):
                            fal[k] += int(trig[k])
                med = []
                for v in dl:
                    v = sorted(v)
                    med.append('–' if not v else '%d' % round(v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2))
                out.append('| %s | %s | %d | %d / %d / %d | %d / %d / %d | %s |' % (KINDN[kind], rn(r), sp, cov[0], cov[1], cov[2], fal[0], fal[1], fal[2], ' / '.join(med)))
    return '\n'.join(out)


def T_cmpq(d):
    out = ['| 종류 | 문턱 | ' + ' | '.join(rn(r) for a, rs in runs_by_arm() for r in rs) + ' |', '|---|---|' + '---|' * 12]
    for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane'):
        for rule in ('lane6_1.0', 'lane6_0.9', 'laneL_1.0'):
            cells = []
            for a, rs in runs_by_arm():
                for r in rs:
                    v = d['agg_compare_strict']['%s|%s|%s' % (r, kind, rule)]
                    cells.append('%d: %d/%d/%d' % (v['n_ep30'], v['lead30'], v['late30'], v['miss30']))
            out.append('| %s | %s | %s |' % (KINDN[kind], rule, ' | '.join(cells)))
    return '\n'.join(out)


def T_atSQ(d):
    out = ['| 종류 | 런 | 엄격 번짐 초 (구간 수) | 엄격 번짐 프레임 점유 6 m (10 / 50 / 90 %) | 6 m ≥ 1.0 몫 | 6 m ≥ 0.9 몫 | 길이 ≥ 1.0 몫 |', '|---|---|---|---|---:|---:|---:|']
    for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane'):
        for a, rs in runs_by_arm():
            for r in rs:
                v = d['arm_summary'][r][kind]
                if 'occ6_at_SQ_q10_50_90' not in v:
                    out.append('| %s | %s | 0 (0) | – | – | – | – |' % (KINDN[kind], rn(r)))
                    continue
                out.append('| %s | %s | %d (%d) | %s | %.2f | %.2f | %.2f |' % (KINDN[kind], rn(r), v['spill_q_s'], v['seg_with_spill_q'],
                                                                         ' / '.join(f(x) for x in v['occ6_at_SQ_q10_50_90']), v['share_SQ_frames_occ6_ge1'],
                                                                         v['share_SQ_frames_occ6_ge09'], v['share_SQ_frames_occL_ge1']))
    return '\n'.join(out)


def main():
    d = json.loads(open(sys.argv[1], 'rb').read().decode('utf-8'))
    txt = open(sys.argv[2], encoding='utf-8').read()
    va_tab, va_n = T_va(d)

    def T_sens():
        out = ['| 런 | 머리 차로 (6 m ≥ 1.0 / ≥ 0.9 / 길이 ≥ 1.0) | 공급 차로 (같은 순서) | 머리+공급, 용량 ≥ 5대 | 머리+공급, 용량 ≥ 10대 |', '|---|---|---|---|---|']
        for a in ORDER:
            for s_ in SEEDS:
                r = '%s_%s' % (a, s_)
                A = d['arm_summary'][r]
                ap, fd, c5, c10 = A['approach_lane'], A['feeder_lane'], A['cap_ge_5'], A['cap_ge_10']
                out.append('| %s | %d / %d / %d | %d / %d / %d | %d / %d / %d (%d구간) | %d / %d / %d (%d구간) |' % (
                    rn(r), ap['dec_any_lane6_1'], ap['dec_any_lane6_09'], ap['dec_any_laneL_1'], fd['dec_any_lane6_1'], fd['dec_any_lane6_09'],
                    fd['dec_any_laneL_1'], c5['dec_any_lane6_1'], c5['dec_any_lane6_09'], c5['dec_any_laneL_1'], c5['n_seg'],
                    c10['dec_any_lane6_1'], c10['dec_any_lane6_09'], c10['dec_any_laneL_1'], c10['n_seg']))
        return '\n'.join(out)

    def T_persc():
        scs = sorted(d['arm_summary']['VA_s31']['per_sc'], key=lambda x: int(x[2:]))
        out = ['| SC | ' + ' | '.join(ARMN[a] + ' (6 m ≥ 1.0 · ≥ 0.9 · 길이 ≥ 1.0, s31/s41/s43)' for a in ORDER) + ' |', '|---|' + '---|' * 4]
        for sc in scs:
            cells = []
            for a in ORDER:
                rr = [d['arm_summary']['%s_%s' % (a, s_)]['per_sc'][sc] for s_ in SEEDS]
                cells.append('%s · %s · %s' % ('/'.join(str(x[0]) for x in rr), '/'.join(str(x[1]) for x in rr), '/'.join(str(x[2]) for x in rr)))
            out.append('| %s | %s |' % (sc, ' | '.join(cells)))
        return '\n'.join(out)

    T = {'T_SENS': T_sens(), 'T_PERSC': T_persc(),'T_SOURCES': T_sources(d), 'T_XCHECK': T_xcheck(d), 'T_ATS': T_atS(d), 'T_ARM': T_arm(d), 'T_CMP': T_cmp(d),
         'T_CMPLEAD': T_cmp_lead(d), 'T_C127': T_chain(d, 'c127'), 'T_C10643': T_chain(d, 'c10643'), 'T_C10483': T_chain(d, 'c10483'),
         'T_C10682': T_chain(d, 'c10682'), 'T_RM10484': T_chain(d, 'rm10484'), 'T_RM10490': T_chain(d, 'rm10490'),
         'T_RM10639': T_chain(d, 'rm10639'), 'T_RM10681': T_chain(d, 'rm10681'), 'T_FW': T_fw(d), 'T_UB': T_ub(d), 'T_USG': T_usg(d),
         'T_USGL': T_usg_lanes(d), 'T_VA': va_tab, 'N_VA': str(va_n), 'T_SHORT': T_short(d), 'T_GRP': T_grp(d), 'T_ELEM': T_elem(d), 'T_CMPQ': T_cmpq(d), 'T_ATSQ': T_atSQ(d),
         'T_TOP_NC3': T_top_spill(d, 'NC3'), 'T_TOP_VSL': T_top_spill(d, 'VSL'), 'T_TOP_VA': T_top_spill(d, 'VA'), 'T_TOP_B': T_top_spill(d, 'B'),
         'T_S127': T_series(d, 'A:127:1:2'), 'T_S127O': T_series(d, 'A:127:1:2', 'bin_mean_occ6'), 'T_SD5': T_series(d, 'D5:129:1'),
         'T_S10491': T_series(d, 'F:10491:1'), 'T_W10491V': T_fwspeed(d, 'W:10491'), 'T_SL10481': T_series(d, 'L:10481:127:1'),
         'T_SM10639': T_series(d, 'M:RM_C10639:1'), 'T_SM10681': T_series(d, 'M:RM_C10681:2'), 'T_S71': T_series(d, 'A:71:3:2'),
         'T_W2V': T_fwspeed(d, 'W:10481'), 'T_W10643V': T_fwspeed(d, 'W:10643'), 'T_W10682V': T_fwspeed(d, 'W:10682')}
    for k, v in T.items():
        txt = txt.replace('{{%s}}' % k, v)
    open(sys.argv[3], 'w', encoding='utf-8').write(txt)
    left = [x for x in T if '{{%s}}' % x in txt]
    print('placeholders left', left)


if __name__ == '__main__':
    main()
