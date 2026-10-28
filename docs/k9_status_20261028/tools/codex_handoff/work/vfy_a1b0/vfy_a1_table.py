# -*- coding: utf-8 -*-
"""VERIFY_A1_B0: A1 결과 표 독립 재계산 (codex 꼴 0-8100 s) + FZP 프레임 대조.

입력: vfy_fzp_scan.py 출력 4개(a1, joint, nc, lnc; --tmax 8100), 인계 정의 파일(읽기만).
codex 꼴: 프레임 k 의 링크 재고 n_k 를 다음 프레임까지 유지, 마지막 프레임은 8100 까지(빈 망에서 시작).
첫 관측 차분: S = sum_{t_first<=8100} (8100 - t_first)/3600, d4b(a-b) = S_b - S_a.
보고 값(A1_RESULT §4, A1_B0_RESULTS §1.3)은 아래 REPORTED 에 글자 그대로 옮김. 허용 0.06 veh·h.
"""
import json, gzip, sys, os, re, hashlib

OUT = sys.argv[1]
SC = os.path.dirname(OUT)
TEND = 8100.0
HO = 'D:/VISSIM_handoff/20261024/derived/'
RUN_ERR = {
    'a1': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_simulation_001.err',
    'joint': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_simulation_001.err',
}
NATIVE = {
    'a1': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/native_network_performance.json',
    'joint': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/native_network_performance.json',
}
PREFIX_CLAIM = 'f1a0b040b711e5974615873f334d28395e7aa037de356caeda101fafcc8fbcda'

# 보고 값: (A1, LNC, A1-LNC, joint, NC, joint-NC, A1-joint); None = 보고 없음
REPORTED = {
    'O701': (6900.5, 7406.2, -505.7, 6911.5, 7406.2, -494.7, -11.0),
    'O635': (6343.0, 6754.4, -411.4, 6346.5, 6754.4, -407.9, -3.5),
    'O701m635': (557.5, 651.8, -94.2, 565.0, 651.8, -86.8, -7.5),
    'L66': (203.7, 254.3, -50.5, 203.3, 254.3, -51.0, 0.5),
    'M4a': (8530.8, 8994.9, -464.1, 8545.9, 8994.9, -449.0, -15.1),
    'M4b': (16409.8, 16644.9, -235.1, 16423.6, 16644.9, -221.3, -13.8),
    'M4': (24940.6, 25639.8, -699.2, 24969.5, 25639.8, -670.3, -28.9),
    'OUTa701': (18040.1, 18233.6, -193.5, 18058.0, 18233.6, -175.6, -17.9),
    'OUTb701': (1630.3, 1588.8, 41.6, 1634.4, 1588.8, 45.7, -4.1),
    'OUTa635': (18597.6, 18885.4, -287.8, 18623.0, 18885.4, -262.4, -25.4),
    'OUTb635': (2187.8, 2240.5, -52.7, 2199.4, 2240.5, -41.1, -11.6),
    'M1': (1873.4, 2124.5, -251.1, 1840.9, 2124.5, -283.7, 32.5),
    'M2': (2165.6, 2347.4, -181.8, 2190.8, 2347.4, -156.6, -25.3),
    'B1098': (None, None, 94.8, None, None, 97.0, -2.1),
    'B1099': (None, None, -78.8, None, None, -69.2, -9.6),
    'Burban': (None, None, -251.1, None, None, -249.0, -2.1),
}
TOL = 0.06


def load(tag):
    with gzip.open(os.path.join(SC, 'scan_%s.json.gz' % tag), 'rt', encoding='utf-8') as g:
        return json.load(g)


def ttt(scan, links=None):
    fr = scan['frames']
    tot = 0.0
    for k, t in enumerate(fr):
        dt = (fr[k + 1] if k + 1 < len(fr) else TEND) - t
        if links is None:
            n = sum(c for _, c in scan['flc'][k])
        else:
            n = sum(c for l, c in scan['flc'][k] if l in links)
        tot += n * dt
    return tot / 3600.0


def firstobs(scan):
    s = {'all': 0.0, '74': 0.0, '26': 0.0, 'other': 0.0}
    cnt = {'74': 0, '26': 0, 'all': 0}
    for v, (t, l) in scan['first'].items():
        if t > TEND + 1e-9:
            continue
        w = (TEND - t) / 3600.0
        s['all'] += w
        cnt['all'] += 1
        key = '74' if l == 74 else ('26' if l == 26 else 'other')
        s[key] += w
        if key in cnt:
            cnt[key] += 1
    return s, cnt


def remain(path):
    out = {}
    with open(path, 'rb') as f:
        txt = f.read().decode('utf-8', 'replace')
    for m in re.finditer(r'Vehicle input (\d+):.*?remain: (\d+) vehicles', txt):
        out[m.group(1)] = int(m.group(2))
    return out


def main():
    om = json.load(open(HO + 'omega_membership_exact.json', encoding='utf-8'))
    O701 = set(int(x) for x in om['inside_links'])
    O635 = set(int(x) for x in om['controlled_intersection_expansion']['previous_inside_links'])
    scope = json.load(open(HO + 'scope_definitions.json', encoding='utf-8'))
    FW7 = set(scope['FW_E_7'])
    L19 = set(scope['local_19'])
    res = {'sets': {'O701': len(O701), 'O635': len(O635), 'O635_subset_O701': O635 <= O701, 'FW7': sorted(FW7),
                    'L19_n': len(L19)}}
    scans = {t: load(t) for t in ('a1', 'joint', 'nc', 'lnc')}
    res['scan_meta'] = {t: {k: s[k] for k in ('fzp', 'bytes', 'data_rows', 'skipped_010_rows', 'n_frames', 'first_frame',
                                              'last_frame', 'irregular_steps', 'off_grid_frames', 'n_vehicles',
                                              'prefix_le_895_1')} for t, s in scans.items()}
    # 프레임 대조
    fd = {}
    for a, b in (('a1', 'joint'), ('a1', 'lnc'), ('joint', 'lnc'), ('nc', 'lnc')):
        fa, fb = scans[a], scans[b]
        n = min(len(fa['frames']), len(fb['frames']))
        same_t = fa['frames'][:n] == fb['frames'][:n]
        diffs = [i for i in range(n) if fa['fh'][i] != fb['fh'][i]]
        pre = [i for i in range(n) if fa['frames'][i] <= 895.1 + 1e-9]
        fd['%s-%s' % (a, b)] = {'compared': n, 'same_times': same_t, 'n_diff': len(diffs),
                                'first_diff_t': fa['frames'][diffs[0]] if diffs else None,
                                'pre895_all_same': all(fa['fh'][i] == fb['fh'][i] for i in pre)}
    res['frame_diff'] = fd
    res['prefix_claim_match'] = {t: s['prefix_le_895_1']['sha256'] == PREFIX_CLAIM for t, s in scans.items()}
    # 지표
    lv = {}
    fo = {}
    for t, s in scans.items():
        lv[t] = {'O701': ttt(s, O701), 'O635': ttt(s, O635), 'L66': ttt(s, {66}), 'M4a': ttt(s),
                 'M1': ttt(s, FW7), 'M2': ttt(s, L19)}
        lv[t]['O701m635'] = lv[t]['O701'] - lv[t]['O635']
        fo[t] = firstobs(s)
    res['levels'] = lv
    res['firstobs'] = {t: {'S': fo[t][0], 'count': fo[t][1]} for t in fo}
    nat = {t: json.load(open(p, encoding='utf-8-sig'))['native'] for t, p in NATIVE.items()}
    res['native_delaylatent_h'] = {t: nat[t]['DelayLatent'] / 3600.0 for t in nat}
    res['remain'] = {t: remain(p) for t, p in RUN_ERR.items()}
    res['arrival_1099'] = {t: fo[t][1]['26'] + res['remain'][t].get('1099', 0) for t in RUN_ERR}

    def d4b(a, b, key='all'):
        return fo[b][0][key] - fo[a][0][key]

    pairs = {'A1-LNC': ('a1', 'lnc'), 'joint-NC': ('joint', 'nc'), 'A1-joint': ('a1', 'joint')}
    pd = {}
    for name, (a, b) in pairs.items():
        x = {}
        for c in ('O701', 'O635', 'O701m635', 'L66', 'M4a', 'M1', 'M2'):
            x[c] = lv[a][c] - lv[b][c]
        x['M4b'] = d4b(a, b)
        x['B1098'] = d4b(a, b, '74')
        x['B1099'] = d4b(a, b, '26')
        x['Burban'] = d4b(a, b, 'other')
        x['M4'] = x['M4a'] + x['M4b']
        x['OUTa701'] = x['M4'] - x['O701']
        x['OUTb701'] = x['M4a'] - x['O701']
        x['OUTa635'] = x['M4'] - x['O635']
        x['OUTb635'] = x['M4a'] - x['O635']
        pd[name] = x
    res['pairs'] = pd
    res['native_minus_firstobs_A1-joint'] = (res['native_delaylatent_h']['a1'] - res['native_delaylatent_h']['joint']) - pd['A1-joint']['M4b']
    # 대조
    cmp = []
    colmap = {2: 'A1-LNC', 5: 'joint-NC', 6: 'A1-joint'}
    levmap = {0: 'a1', 1: 'lnc', 3: 'joint', 4: 'nc'}
    for cell, rep in REPORTED.items():
        for idx, v in enumerate(rep):
            if v is None:
                continue
            if idx in colmap:
                mine = pd[colmap[idx]][cell]
                col = colmap[idx]
            else:
                run = levmap[idx]
                col = run
                if cell in lv[run]:
                    mine = lv[run][cell]
                elif cell == 'M4b':
                    mine = res['native_delaylatent_h'][run] if run in nat else None
                else:
                    mine = None
                if mine is None:
                    cmp.append({'cell': cell, 'col': col, 'reported': v, 'mine': None, 'status': 'not_recomputed'})
                    continue
            ok = abs(mine - v) <= TOL
            cmp.append({'cell': cell, 'col': col, 'reported': v, 'mine': round(mine, 4),
                        'diff': round(mine - v, 4), 'status': 'match' if ok else 'MISMATCH'})
    res['compare'] = cmp
    res['n_match'] = sum(1 for c in cmp if c['status'] == 'match')
    res['n_mismatch'] = sum(1 for c in cmp if c['status'] == 'MISMATCH')
    res['n_not_recomputed'] = sum(1 for c in cmp if c['status'] == 'not_recomputed')
    # 같은 부호 점검 (재계산한 짝 차로)
    res['same_sign_A1LNC_vs_jointNC'] = {c: (pd['A1-LNC'][c] > 0) == (pd['joint-NC'][c] > 0) for c in pd['A1-LNC']}
    res['ratio_pct'] = {c: 100.0 * abs(pd['A1-joint'][c]) / abs(pd['joint-NC'][c]) for c in pd['A1-joint'] if pd['joint-NC'][c]}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({'n_match': res['n_match'], 'n_mismatch': res['n_mismatch'], 'not': res['n_not_recomputed'],
                      'frame_diff': fd, 'prefix': res['prefix_claim_match']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
