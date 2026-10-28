# fd_pack.py — FACTS_DATA.json 묶기 + 부록 표(md 조각). 읽기만.
# 결정 JSON 표본 14개는 "관측 키" 값만 정규식으로 읽음(온라인 관측 대조). 출력 = ../FACTS_DATA.json, ../out/appendix_tables.md
import os, re, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.dirname(HERE)
OUTD = os.path.join(GUARD, 'out')

DEC = []
for s in (31, 41, 43):
    for T in (2400, 3000, 4500, 6000):
        DEC.append(('B', s, T, 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc/decisions_sdmpc31_sdmpc9000_s%d/action_%06d.json' % (s, s, T)))
for T in (2400, 4500):
    DEC.append(('V-A', 31, T, 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/action_%06d.json' % T))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def f(x, n=1):
    if x is None:
        return '–'
    if isinstance(x, int):
        return str(x)
    return ('%.' + str(n) + 'f') % x


def main():
    ps = os.path.join(OUTD, 'fd_series.json'); po = os.path.join(OUTD, 'fd_onset.json')
    S = json.load(open(ps, encoding='utf-8')); O = json.load(open(po, encoding='utf-8'))
    # online observation sample
    online = []
    for arm, s, T, p in DEC:
        t = open(p, encoding='utf-8').read()
        def grab(pat):
            m = re.search(pat, t, re.S)
            return float(m.group(1)) if m else None
        rec = {'arm': arm, 'seed': s, 'T': T, 'file': os.path.basename(p), 'sha256': sha(p),
               'obs_10491': grab(r'"physical_branch_projection_provenance":\s*\{.*?"10491":\s*\{[^}]*?"observed_veh":\s*([0-9.]+)'),
               'obs_129_in_SC1001_W': grab(r'"physical_stock_assignment_by_link":\s*\{.*?"129":\s*\{\s*"storage:in_SC1001_W":\s*([0-9.]+)'),
               'mainline_origin_queue_observed': grab(r'"mainline_origin_queue_total_veh":\s*\{[^}]*?"observed":\s*([0-9.eE+-]+)')}
        rk = ('b%d' if arm == 'B' else 'va%d') % s
        sn = S['runs'][rk]['snap_decision'][str(T)]
        rec['fzp_snapshot_T+0.1'] = sn
        q = S['runs'][rk]['entrance']['Q_hat_end_of_bin']
        rec['Q_hat_near_T'] = q[T // 300 - 1] if T % 300 == 0 else None
        online.append(rec)
    out = {
        'title': 'FACTS_DATA — 사슬 300 s 계열 (NC3·V-A·B × v3c3-s31·s41·s43)',
        'note': '판정 낱말 없음. 시작 칸 규칙과 문턱 후보는 모두 데이터 뒤.',
        'inputs_sha256': S['inputs_sha256'],
        'tools_sha256': {'fd_series.py': S['tool_sha256'], 'fd_onset.py': O['tool_sha256'], 'fd_pack.py': sha(os.path.abspath(__file__))},
        'outputs_sha256': {'out/fd_series.json': sha(ps), 'out/fd_onset.json': sha(po)},
        'onset_rule_data_after': O['rule'],
        'onset': {rk: {k: o[k] for k in ('arm', 'seed', 'onset_O1', 'first_127_start_lt20', 'first_129L1_slow_ge3', 'first_10491_slow_ge5', 'first_tail0')} for rk, o in O['runs'].items()},
        'around_onset': {rk: o['around_onset'] for rk, o in O['runs'].items() if o['around_onset']},
        'snap_around_onset': {rk: o.get('snap_around_onset') for rk, o in O['runs'].items() if o.get('snap_around_onset')},
        'pre_chain_max': {rk: o['pre_chain_max'] for rk, o in O['runs'].items()},
        'va_reference': O['va_reference'],
        'snap_cross_data_after': {rk: o['snap_cross'] for rk, o in O['runs'].items()},
        'snap_max': {rk: o['snap_max'] for rk, o in O['runs'].items()},
        'queue_estimate': S['queue_est'],
        'online_observation_sample': online,
        'series_300s': {rk: {'bins_start_s': S['bins_start_s'],
                             'sg2_green_s': r['sg2']['green_s_bin'][3:], 'sg2_green_per_cycle': r['sg2']['green_per_cycle_mean'][3:],
                             'sg2_cycle_mean': r['sg2']['cycle_mean'][3:],
                             'c10491_mean': r['c10491']['mean'][3:], 'c10491_max5s': r['c10491']['max5s'][3:],
                             'c10491_slow_mean': r['c10491']['slow_mean'][3:],
                             'l129L1_100_302_mean': r['l129']['l1_100_302_mean'][3:], 'l129L1_100_302_slow_mean': r['l129']['l1_100_302_slow_mean'][3:],
                             'l129_link_mean': r['l129']['link_mean'][3:],
                             'l127_mean': r['l127']['mean'][3:], 'l127_max5s': r['l127']['max5s'][3:], 'l127_start_l12_speed': r['l127']['start0_50_l12_speed'][3:],
                             'l26L1_3200_3700_mean': r['l26_l1_end']['mean'][3:], 'l26L1_3200_3700_speed': r['l26_l1_end']['speed'][3:],
                             'l26L1_tail_from_m': r['l26_l1_end']['tail_from_m'][3:],
                             'in1099_inserted': r['entrance']['n_ins_bin'][3:],
                             'in1099_Q_hat_at_bin_end': r['entrance']['Q_hat_end_of_bin'][3:],
                             'in1099_deficit_vs_nc3_cum_at_bin_end': r['entrance']['deficit_vs_nc3_cum'][3:],
                             'err_remain_end': r['R_end'], 'A_T': r['A_T']}
                       for rk, r in S['runs'].items()},
    }
    with open(os.path.join(GUARD, 'FACTS_DATA.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    # appendix tables
    L = []
    lab = {'nc': 'NC3', 'b': 'B', 'va': 'V-A'}
    for s in (31, 41, 43):
        for a in ('nc', 'b', 'va'):
            rk = '%s%d' % (a, s); r = S['runs'][rk]
            L.append('\n#### %s v3c3-s%d\n' % (lab[a], s))
            L.append('| 칸 시작 s | SG2 GREEN s/칸 | SG2 GREEN s/주기 (주기 s) | 127 평균 대 (5 s 최대) | 129 차로1 100–302 m 평균 대 (느린) | 10491 평균 대 (5 s 최대) | 26 차로1 3,200–3,700 m 평균 대 · km/h | 꼬리 시작 m | 1099 넣음 대 | 1099 남은 줄 추정 대 (칸 끝) | NC3 대비 덜 넣음 누적 대 |')
            L.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
            for k in range(3, 30):
                L.append('| %d | %s | %s (%s) | %s (%s) | %s (%s) | %s (%s) | %s · %s | %s | %d | %s | %s |' % (
                    k * 300, f(r['sg2']['green_s_bin'][k], 0), f(r['sg2']['green_per_cycle_mean'][k]), f(r['sg2']['cycle_mean'][k], 0),
                    f(r['l127']['mean'][k]), f(r['l127']['max5s'][k], 0),
                    f(r['l129']['l1_100_302_mean'][k]), f(r['l129']['l1_100_302_slow_mean'][k]),
                    f(r['c10491']['mean'][k]), f(r['c10491']['max5s'][k], 0),
                    f(r['l26_l1_end']['mean'][k]), f(r['l26_l1_end']['speed'][k], 0),
                    '–' if r['l26_l1_end']['tail_from_m'][k] is None else str(r['l26_l1_end']['tail_from_m'][k]),
                    r['entrance']['n_ins_bin'][k], f(r['entrance']['Q_hat_end_of_bin'][k], 0), f(r['entrance']['deficit_vs_nc3_cum'][k], 0)))
    with open(os.path.join(OUTD, 'appendix_tables.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    for rec in online:
        print(rec['arm'], rec['seed'], rec['T'], rec['obs_10491'], rec['obs_129_in_SC1001_W'], rec['mainline_origin_queue_observed'], rec['fzp_snapshot_T+0.1'], rec['Q_hat_near_T'], rec['sha256'][:8])
    print('PACK_DONE')


if __name__ == '__main__':
    main()
