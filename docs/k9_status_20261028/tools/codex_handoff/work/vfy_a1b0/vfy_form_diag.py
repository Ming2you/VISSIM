# -*- coding: utf-8 -*-
"""VERIFY_A1_B0 진단(규칙 밖, 자료를 본 뒤 더함 — 밝힘).

까닭: vfy_a1_table.py 의 codex 꼴(앞으로 유지 step)이 수준값에서 보고값보다 1.4-1.8 veh·h 작게 나옴.
codex 꼴 정의를 codex 자체 수치(인계 derived/metrics_0_8100.json, nc·joint 조건)로 가려냄. 세 꼴:
  F  (앞으로 유지)  : sum_{k<K} n_k*5 + n_K*(8100-t_K)        [규칙에 고정했던 꼴]
  BK (뒤로 표본)    : sum_k n_k*5 + n_K*(8100-t_K)             [각 5 s 표본 + 마지막 4.9 s 유지]
  TR (사다리꼴)     : 0->t_0 선형, 프레임 사이 선형, 마지막 유지
codex 자체 값과 1e-3 veh·h 안에서 맞는 꼴로 A1 표의 링크 칸(수준·짝 차)을 다시 내어 보고값과 대조(허용 0.06).
"""
import json, gzip, os, sys

OUT = sys.argv[1]
SC = os.path.dirname(OUT)
HO = 'D:/VISSIM_handoff/20261024/derived/'
TEND = 8100.0
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vfy_a1_table import REPORTED, TOL  # 보고 값 표만 가져옴(계산 함수는 쓰지 않음)


def load(tag):
    with gzip.open(os.path.join(SC, 'scan_%s.json.gz' % tag), 'rt', encoding='utf-8') as g:
        return json.load(g)


def series(scan, links):
    return [sum(c for l, c in f if links is None or l in links) for f in scan['flc']]


def forms(scan, links):
    n = series(scan, links)
    t = scan['frames']
    K = len(n) - 1
    tail = TEND - t[K]
    F = sum(n[k] * (t[k + 1] - t[k]) for k in range(K)) + n[K] * tail
    BK = sum(n[k] * 5.0 for k in range(K + 1)) + n[K] * tail
    TR = n[0] * t[0] / 2 + sum((n[k] + n[k + 1]) / 2 * (t[k + 1] - t[k]) for k in range(K)) + n[K] * tail
    return {'F': F / 3600, 'BK': BK / 3600, 'TR': TR / 3600, 'n0': n[0], 'nK': n[K]}


def main():
    om = json.load(open(HO + 'omega_membership_exact.json', encoding='utf-8'))
    O701 = set(int(x) for x in om['inside_links'])
    O635 = set(int(x) for x in om['controlled_intersection_expansion']['previous_inside_links'])
    sc = json.load(open(HO + 'scope_definitions.json', encoding='utf-8'))
    sets = {'O701': O701, 'O635': O635, 'L66': {66}, 'M4a': None, 'M1': set(sc['FW_E_7']), 'M2': set(sc['local_19'])}
    codex = {}
    for r in json.load(open(HO + 'metrics_0_8100.json', encoding='utf-8-sig')):
        codex[(r['condition'], r['metric'])] = r['veh_h']
    cmap = {'O701': 'Omega701', 'M4a': 'network_sampled_residence', 'M1': 'FW_E_7', 'M2': 'local_19'}
    scans = {t: load(t) for t in ('a1', 'joint', 'nc', 'lnc')}
    lv = {t: {c: forms(s, L) for c, L in sets.items()} for t, s in scans.items()}
    anchor = []
    for cond, tag in (('nc', 'nc'), ('joint', 'joint')):
        for c, m in cmap.items():
            if (cond, m) in codex:
                v = codex[(cond, m)]
                anchor.append({'cond': cond, 'metric': m, 'codex': v,
                               **{f: round(lv[tag][c][f] - v, 6) for f in ('F', 'BK', 'TR')}})
    best = None
    for f in ('F', 'BK', 'TR'):
        if all(abs(a[f]) <= 1e-3 for a in anchor):
            best = f
    res = {'anchor_vs_codex_own': anchor, 'form_matching_codex_own': best,
           'n0_nK': {t: {c: [lv[t][c]['n0'], lv[t][c]['nK']] for c in sets} for t in lv}}
    if best:
        L = {t: {c: lv[t][c][best] for c in sets} for t in lv}
        for t in L:
            L[t]['O701m635'] = L[t]['O701'] - L[t]['O635']
        fo = json.load(open(os.path.join(SC, 'a1_table.json'), encoding='utf-8'))['pairs']
        pd = {}
        for name, (a, b) in {'A1-LNC': ('a1', 'lnc'), 'joint-NC': ('joint', 'nc'), 'A1-joint': ('a1', 'joint')}.items():
            x = {c: L[a][c] - L[b][c] for c in L[a]}
            x['M4b'] = fo[name]['M4b']  # 첫 관측 차분은 꼴과 무관(vfy_a1_table 값)
            for k in ('B1098', 'B1099', 'Burban'):
                x[k] = fo[name][k]
            x['M4'] = x['M4a'] + x['M4b']
            x['OUTa701'] = x['M4'] - x['O701']
            x['OUTb701'] = x['M4a'] - x['O701']
            x['OUTa635'] = x['M4'] - x['O635']
            x['OUTb635'] = x['M4a'] - x['O635']
            pd[name] = x
        cmp = []
        colmap = {2: 'A1-LNC', 5: 'joint-NC', 6: 'A1-joint'}
        levmap = {0: 'a1', 1: 'lnc', 3: 'joint', 4: 'nc'}
        for cell, rep in REPORTED.items():
            for idx, v in enumerate(rep):
                if v is None:
                    continue
                if idx in colmap:
                    mine = pd[colmap[idx]].get(cell)
                    col = colmap[idx]
                else:
                    col = levmap[idx]
                    mine = L[col].get(cell)
                if mine is None:
                    continue
                cmp.append({'cell': cell, 'col': col, 'reported': v, 'mine': round(mine, 4), 'diff': round(mine - v, 4),
                            'status': 'match' if abs(mine - v) <= TOL else 'MISMATCH'})
        res['compare_in_codex_form'] = cmp
        res['n_match'] = sum(1 for c in cmp if c['status'] == 'match')
        res['n_mismatch'] = sum(1 for c in cmp if c['status'] == 'MISMATCH')
        res['pairs'] = pd
        res['levels'] = L
        res['same_sign_A1LNC_vs_jointNC'] = {c: (pd['A1-LNC'][c] > 0) == (pd['joint-NC'][c] > 0) for c in pd['A1-LNC']}
        res['ratio_pct'] = {c: 100.0 * abs(pd['A1-joint'][c]) / abs(pd['joint-NC'][c]) for c in pd['A1-joint'] if pd['joint-NC'][c]}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: res.get(k) for k in ('form_matching_codex_own', 'n_match', 'n_mismatch')}, ensure_ascii=False))
    print(json.dumps(anchor, ensure_ascii=False))
    for c in res.get('compare_in_codex_form', []):
        if c['status'] != 'match':
            print('MISMATCH', c)


if __name__ == '__main__':
    main()
