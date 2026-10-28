# -*- coding: utf-8 -*-
"""VERIFY_A1_B0 추가 진단(규칙 밖, 밝힘): 진입 E·W 칸을 A1_RESULT 규칙 글에 적힌 정의로 다시 냄.
codex 분할 진입 E/W = reporting_partition.onramp_roads 의 FW_E/FW_W 커넥터.
우리 분할 진입 E/W = codex 분할 + 미터 상류 링크(E: 70·68·129·31, W: 124·32·121·69) (COMPARE_RULE_A1_FULL §C 글).
꼴 = 사다리꼴(TR, vfy_form_diag 가 codex 자체 수치로 가려낸 꼴). 보고값(A1_RESULT §4) 과 허용 0.06.
"""
import json, gzip, os, sys

OUT = sys.argv[1]
SC = os.path.dirname(OUT)
HO = 'D:/VISSIM_handoff/20261024/derived/'
TEND = 8100.0
REP = {  # (A1, LNC, A1-LNC, joint, NC, joint-NC, A1-joint)
    'E_codex': (176.6, 121.8, 54.9, 206.8, 121.8, 85.0, -30.2),
    'W_codex': (83.6, 77.4, 6.2, 87.9, 77.4, 10.6, -4.4),
    'E_ours': (262.2, 180.8, 81.4, 323.6, 180.8, 142.8, -61.4),
    'W_ours': (451.9, 446.1, 5.8, 481.4, 446.1, 35.3, -29.5),
}


def load(tag):
    with gzip.open(os.path.join(SC, 'scan_%s.json.gz' % tag), 'rt', encoding='utf-8') as g:
        return json.load(g)


def tr(scan, links):
    n = [sum(c for l, c in f if l in links) for f in scan['flc']]
    t = scan['frames']
    K = len(n) - 1
    v = n[0] * t[0] / 2 + sum((n[k] + n[k + 1]) / 2 * (t[k + 1] - t[k]) for k in range(K)) + n[K] * (TEND - t[K])
    return v / 3600


def main():
    rp = json.load(open(HO + 'reporting_partition.json', encoding='utf-8'))
    E = {int(k) for k, v in rp['onramp_roads'].items() if v == 'FW_E'}
    W = {int(k) for k, v in rp['onramp_roads'].items() if v == 'FW_W'}
    sets = {'E_codex': E, 'W_codex': W, 'E_ours': E | {70, 68, 129, 31}, 'W_ours': W | {124, 32, 121, 69}}
    scans = {t: load(t) for t in ('a1', 'lnc', 'joint', 'nc')}
    res = {'sets': {k: sorted(v) for k, v in sets.items()}, 'cells': []}
    for c, L in sets.items():
        lv = {t: tr(s, L) for t, s in scans.items()}
        mine = (lv['a1'], lv['lnc'], lv['a1'] - lv['lnc'], lv['joint'], lv['nc'], lv['joint'] - lv['nc'], lv['a1'] - lv['joint'])
        for i, (m, r) in enumerate(zip(mine, REP[c])):
            res['cells'].append({'cell': c, 'col': i, 'reported': r, 'mine': round(m, 3), 'status': 'match' if abs(m - r) <= 0.06 else 'MISMATCH'})
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == '__main__':
    main()
