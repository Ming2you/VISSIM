# fd_onset.py — FACTS_DATA: 사슬 시작 칸, 시작 직전 칸 값, 결정 시각 스냅숏, 문턱 넘김 표 (데이터 뒤)
# 읽기만. 입력 = ../out/fd_series.json + w1099/out/<run>.json (5 s 프레임 계열). 사용: python -B fd_onset.py → ../out/fd_onset.json
import os, json, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.dirname(HERE)
OUTD = os.path.join(GUARD, 'out')
SP = os.path.normpath(os.path.join(GUARD, '..', '..', '..'))
W = os.path.join(SP, 'c_port', 'w1099', 'out')
K0, NTB, TB = 3, 30, 300.0

# 규칙 (데이터 뒤 — INPUT1099 표를 이미 본 뒤 정함)
RULE = {
    'onset_O1': '26 차로1 3,200-3,700 m 점유 가중 평균 속도 < 40 km/h 인 첫 300 s 칸 (900 s 부터)',
    'up_127': '127 시작 0-50 m 차로1·2 평균 속도 < 20 km/h 인 첫 칸',
    'up_129': '129 차로1 100-302 m 느린 차(<10 km/h) 시간평균 >= 3 대인 첫 칸',
    'up_10491': '10491 느린 차 시간평균 >= 5 대인 첫 칸',
    'tail0': '26 차로1 꼬리(3,600 m 칸부터 40 km/h 미만 연속)가 0 m 에 닿은 첫 칸',
}
TH_10491 = [8, 12, 16, 20, 24]
TH_129 = [15, 20, 25, 30]
TH_127 = [120, 140, 160]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def first(cond):
    for k in range(K0, NTB):
        if cond(k):
            return k * 300
    return None


def main():
    fp = os.path.join(OUTD, 'fd_series.json')
    d = json.load(open(fp, encoding='utf-8'))
    out = {'rule': RULE, 'input_fd_series_sha256': sha(fp), 'runs': {}}
    lt = lambda x, v: (x is not None) and x < v
    ge = lambda x, v: (x is not None) and x >= v
    for rk, r in d['runs'].items():
        o = {'arm': r['arm'], 'seed': r['seed']}
        o['onset_O1'] = first(lambda k: lt(r['l26_l1_end']['speed'][k], 40))
        o['first_127_start_lt20'] = first(lambda k: lt(r['l127']['start0_50_l12_speed'][k], 20))
        o['first_129L1_slow_ge3'] = first(lambda k: ge(r['l129']['l1_100_302_slow_mean'][k], 3))
        o['first_10491_slow_ge5'] = first(lambda k: ge(r['c10491']['slow_mean'][k], 5))
        o['first_tail0'] = first(lambda k: r['l26_l1_end']['tail_from_m'][k] == 0)
        ks = o['onset_O1']
        rows = {}
        if ks is not None:
            kb = ks // 300
            for kk in (kb - 2, kb - 1, kb):
                rows[str(kk * 300)] = {
                    'c10491_mean': r['c10491']['mean'][kk], 'c10491_slow_mean': r['c10491']['slow_mean'][kk],
                    'c10491_max5s': r['c10491']['max5s'][kk], 'c10491_p90_5s': r['c10491']['p90_5s'][kk],
                    'l129L1_100_302_mean': r['l129']['l1_100_302_mean'][kk], 'l129L1_100_302_slow_mean': r['l129']['l1_100_302_slow_mean'][kk],
                    'l129L1_150_302_slow_max5s': r['l129']['l1_150_302_slow_max5s'][kk],
                    'l129_link_mean': r['l129']['link_mean'][kk], 'l129_link_max5s': r['l129']['link_max5s'][kk],
                    'l127_mean': r['l127']['mean'][kk], 'l127_max5s': r['l127']['max5s'][kk],
                    'l26E_mean': r['l26_l1_end']['mean'][kk], 'l26E_speed': r['l26_l1_end']['speed'][kk],
                    'sg2_green_s': r['sg2']['green_s_bin'][kk], 'sg2_per_cycle': r['sg2']['green_per_cycle_mean'][kk],
                    'n_ins': r['entrance']['n_ins_bin'][kk], 'Q_hat_end': r['entrance']['Q_hat_end_of_bin'][kk]}
        o['around_onset'] = rows
        # decision snapshots around onset
        sn = r['snap_decision']
        if ks is not None:
            o['snap_around_onset'] = {T: sn[str(T)] for T in range(ks - 450, ks + 301, 150) if str(T) in sn}
        # pre-chain (bins before onset-2) maxima
        kend = (ks // 300 - 2) if ks is not None else NTB
        pre = range(K0, max(K0, kend))
        def mx(a):
            v = [a[k] for k in pre if a[k] is not None]
            return max(v) if v else None
        o['pre_chain_max'] = {'bins': [K0 * 300, kend * 300], 'c10491_mean': mx(r['c10491']['mean']), 'c10491_max5s': mx(r['c10491']['max5s']),
                              'l129L1_100_302_mean': mx(r['l129']['l1_100_302_mean']), 'l129_link_max5s': mx(r['l129']['link_max5s']),
                              'l127_mean': mx(r['l127']['mean'])}
        # snapshot crossing: first decision T (>=900) with snapshot >= theta
        Ts = sorted(int(t) for t in sn)
        chain = set(k for k in range(K0, NTB) if lt(r['l26_l1_end']['speed'][k], 40))
        cross = {}
        for name, ths in (('10491', TH_10491), ('129', TH_129), ('127', TH_127)):
            cross[name] = {}
            for th in ths:
                hit = [T for T in Ts if sn[str(T)][name] is not None and sn[str(T)][name] >= th]
                # 같은 300 s 칸 또는 다음 칸이 26 끝 막힘 칸(O1 조건)인가
                with_chain = [T for T in hit if (T // 300) in chain or (T // 300 + 1) in chain]
                cross[name][str(th)] = {'first_T': hit[0] if hit else None, 'n_decisions': len(hit), 'n_total': len(Ts),
                                        'n_with_chain_same_or_next_bin': len(with_chain),
                                        'n_without_chain': len(hit) - len(with_chain)}
        # 사슬 칸을 놓친 결정: 사슬 칸 시작 결정 시각과 그 전 결정(칸 시작 −150 s)이 모두 문턱 밑인 사슬 칸 수
        for name, ths in (('10491', TH_10491), ('129', TH_129), ('127', TH_127)):
            for th in ths:
                miss = 0
                for k in sorted(chain):
                    Tk = [k * 300 - 150, k * 300]
                    v = [sn[str(T)][name] for T in Tk if str(T) in sn and sn[str(T)][name] is not None]
                    if v and max(v) < th:
                        miss += 1
                cross[name][str(th)]['chain_bins_missed_at_T_minus150_and_T'] = miss
                cross[name][str(th)]['n_chain_bins'] = len(chain)
        o['snap_cross'] = cross
        o['snap_max'] = {name: max(sn[str(T)][name] for T in Ts if sn[str(T)][name] is not None) for name in ('10491', '129', '127')}
        out['runs'][rk] = o
    # no-chain reference: V-A all bins
    ref = {}
    for rk, r in d['runs'].items():
        if r['arm'] != 'V-A':
            continue
        b = range(K0, NTB)
        ref[rk] = {'c10491_mean_max': max(r['c10491']['mean'][k] for k in b), 'c10491_max5s_max': max(r['c10491']['max5s'][k] for k in b),
                   'l129L1_100_302_mean_max': max(r['l129']['l1_100_302_mean'][k] for k in b),
                   'l129_link_max5s_max': max(r['l129']['link_max5s'][k] for k in b),
                   'l127_mean_max': max(r['l127']['mean'][k] for k in b),
                   'l26E_speed_min': min(r['l26_l1_end']['speed'][k] for k in b)}
    out['va_reference'] = ref
    out['tool_sha256'] = sha(os.path.abspath(__file__))
    with open(os.path.join(OUTD, 'fd_onset.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    print('ONSET_DONE')


if __name__ == '__main__':
    main()
