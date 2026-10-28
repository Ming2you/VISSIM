# fin_calc.py — A1_B0_RESULTS r2 마무리용 산술 (읽기만, 2026-10-26 KST)
# 규칙(실행 전 LOG 고정):
#  (1) 비 % = 100 * |pairs['a1-joint'][k]| / |pairs['joint-nc'][k]|, 반올림 전 값(a1_table.json)으로, 표시는 0.1 자리.
#      줄 목록은 A1_B0_RESULTS r1 §1.3 의 19줄 + Omega701_minus_635·onramps_E_codex·onramps_W_codex 3줄.
#  (2) 부호 같음 = sign(pairs['a1-lnc'][k]) == sign(pairs['joint-nc'][k]) (22줄).
#  (3) SC 수 열 분해: trace.json per_T[T].rows.sc_with_diff 를 sc_no 가 '91' 로 시작(램프 미터 행) / 그 밖(신호 SC)으로 나눔.
# 입력: work/a1/full/a1_table.json (6c9671ef…), work/a1/full/trace.json (69277e6c…). 출력: work/fin_a1b0/fin_calc.json
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FULL = os.path.join(HERE, '..', 'a1', 'full')
TAB = os.path.join(FULL, 'a1_table.json')
TRC = os.path.join(FULL, 'trace.json')

ROWS = ['Omega701', 'Omega635', 'a4', 'b4_first_obs', 'four', 'out_a_Omega701', 'out_a_Omega635',
        'out_b_Omega701', 'out_b_Omega635', 'FW_E7', 'local19', 'link66', 'urban_roads_codex',
        'urban_roads_ours', 'onramps_E_ours', 'onramps_W_ours', 'b4_1098', 'b4_1099', 'b4_urban',
        'Omega701_minus_635', 'onramps_E_codex', 'onramps_W_codex']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def sgn(x):
    return (x > 0) - (x < 0)


def main():
    tab = json.load(open(TAB, encoding='utf-8'))
    trc = json.load(open(TRC, encoding='utf-8'))
    P = tab['pairs']
    rows = []
    for k in ROWS:
        a = P['a1-lnc'][k]
        j = P['joint-nc'][k]
        d = P['a1-joint'][k]
        rows.append({'row': k, 'a1_lnc': a, 'joint_nc': j, 'a1_joint': d,
                     'ratio_pct': 100.0 * abs(d) / abs(j) if j else None,
                     'ratio_pct_1dp': round(100.0 * abs(d) / abs(j), 1) if j else None,
                     'same_sign': sgn(a) == sgn(j)})
    sc = []
    for T, v in trc['per_T'].items():
        lst = (v.get('rows') or {}).get('sc_with_diff') or []
        meters = [s for s in lst if str(s).startswith('91')]
        sigs = [s for s in lst if not str(s).startswith('91')]
        sc.append({'T': int(T), 'n_sc_col': len(lst), 'n_signal_sc': len(sigs), 'n_meter_scno': len(meters),
                   'meter_scno': meters, 'by_kind': (v.get('rows') or {}).get('by_kind')})
    sc.sort(key=lambda r: r['T'])
    ge1500 = [r for r in sc if r['T'] >= 1500]
    out = {
        'inputs': {'a1_table.json': sha(TAB), 'trace.json': sha(TRC)},
        'ratio_rows': rows,
        'all_22_same_sign': all(r['same_sign'] for r in rows),
        'sc_split': sc,
        'sc_split_summary': {
            'T1200': next((r for r in sc if r['T'] == 1200), None),
            'T1350': next((r for r in sc if r['T'] == 1350), None),
            'ge1500_signal_sc_min_max': [min(r['n_signal_sc'] for r in ge1500), max(r['n_signal_sc'] for r in ge1500)] if ge1500 else None,
            'ge1500_meter_scno_min_max': [min(r['n_meter_scno'] for r in ge1500), max(r['n_meter_scno'] for r in ge1500)] if ge1500 else None,
            'ge1500_sc_col_min_max': [min(r['n_sc_col'] for r in ge1500), max(r['n_sc_col'] for r in ge1500)] if ge1500 else None,
        },
    }
    op = os.path.join(HERE, 'fin_calc.json')
    with open(op, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('ok', sha(op))
    for r in rows:
        print('%-20s %+10.3f %+10.3f %+9.3f %6.2f %s' % (r['row'], r['a1_lnc'], r['joint_nc'], r['a1_joint'], r['ratio_pct'] or -1, r['same_sign']))
    print(json.dumps(out['sc_split_summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
