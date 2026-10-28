"""Review r2 edit script (one-off, scratch): direction basis, X1 summary and table columns in vp_analyze.py."""
import sys

p = sys.argv[1]
s = open(p, encoding='utf-8').read()


def rep(a, b, count=1):
    global s
    assert s.count(a) == count, (a[:80], s.count(a))
    s = s.replace(a, b)


rep("""            s[name][mname] = {'n_defined': n, 'n_R_ge_0.5': n_hi, 'n_R_le_-0.2': sum(1 for x in Rs if x <= -0.2),""",
    """            s[name][mname] = {'n_states': sum(1 for r in states if (r.get('ablations') or {}).get(name)),
                              'n_defined': n, 'n_R_ge_0.5': n_hi, 'n_R_le_-0.2': sum(1 for x in Rs if x <= -0.2),""")

rep("""# ------------------------------------------------------------------------------------------------ tables
def fmt(x, nd=2):""", """def direction_basis(p1fzp, pp):
    \"\"\"PRE_VP_FIXED 5.4 reading columns (computed, not a stop rule).  Per metric zone (cells 8-25 only):
    C1: mean over cells with a C1 value of (plant FD speed at the NC3 low-density median k - NC3 median speed);
    C2: number of cells whose NC3 median (over the three seeds) k at the max 60 s per-lane flow exceeds the plant
        rho_crit, out of the cells with all three NC3 values; basis = more than half.\"\"\"
    if not pp:
        return None
    cells = pp.get('cells') or {}
    nc3 = [v['all'] for k, v in sorted((p1fzp or {}).items()) if v and k.startswith('NC3_')]
    out = {}
    for mname, (zone, _q) in METRICS.items():
        idx = [i for i in C.ZONES[zone] if i in FOCUS]
        gaps = [cells[str(i)]['plant_fd_speed_at_k_med'] - cells[str(i)]['vissim_s_med'] for i in idx
                if (cells.get(str(i)) or {}).get('plant_fd_speed_at_k_med') is not None
                and cells[str(i)].get('vissim_s_med') is not None]
        n = above = 0
        for i in idx:
            ks = [p[str(i)]['k_at_qmax'] for p in nc3 if (p.get(str(i)) or {}).get('k_at_qmax') is not None]
            rc = (cells.get(str(i)) or {}).get('rho_crit')
            if nc3 and len(ks) == len(nc3) and rc is not None:
                n += 1
                above += int(statistics.median(ks) > float(rc))
        out[mname] = {'zone': zone, 'C1_fd_minus_vissim_low_speed_mean': (sum(gaps) / len(gaps)) if gaps else None,
                      'C1_cells': len(gaps), 'C2_cells_kqmax_above_rhoc': above, 'C2_cells': n,
                      'C2_basis': bool(n > 0 and 2 * above > n)}
    return out


def x1_summary(p1):
    \"\"\"X1: number of P1 states whose base (EXEC) rollout has >= 1 blocked vehicle at each FW_E off-ramp (w450).\"\"\"
    out = {}
    for o in EXITS:
        vals = [((r.get('exits_base') or {}).get('blocked_veh') or {}).get(o) for r in (p1 or {}).get('states', [])
                if r.get('base')]
        got = [x for x in vals if x is not None]
        out[o] = {'n_states': len(vals), 'n_available': len(got), 'n_ge_1veh': sum(1 for x in got if x >= 1.0),
                  'range_veh': [min(got), max(got)] if got else None}
    return out


# ------------------------------------------------------------------------------------------------ tables
def fmt(x, nd=2):""")

rep("""    p1 = res.get('P1') or {}
    L.append('## 표 P1-F — FZP 저밀도""", """    L.append('## 표 B5 — 탐침 B: 실행 계획 plant 의 출구 막힘·출구 차량 (veh, w450; X1·X2, VISSIM 출구는 못 잼)')
    L.append('')
    L.append('| 상태 | T | 묶음 | ' + ' | '.join('%s 막힘' % o for o in EXITS) + ' | '
             + ' | '.join('%s 출구' % o for o in EXITS) + ' |')
    L.append('|---|---:|---|' + '---:|' * (2 * len(EXITS)))
    for r in ab.get('states', []):
        x = (r.get('exits') or {}).get('EXEC_scalar')
        L.append('| %s | %d | %s | %s | %s |' % (
            r['label'], r['T'], r.get('tag'),
            ' | '.join(fmt(((x or {}).get('blocked_veh') or {}).get(o), 1) for o in EXITS),
            ' | '.join(fmt(((x or {}).get('exit_veh') or {}).get(o), 1) for o in EXITS)))
    L.append('')
    p1 = res.get('P1') or {}
    L.append('## 표 P1-F — FZP 저밀도""")

rep("""    L.append("| 상태 | T | VSa 속도 | VS0' 속도 | M1 속도 | VSb 재고 | VSb 속도 | 시작 VSa 속도 | 시작 VSb 재고 |")
    L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')""", """    L.append("| 상태 | T | VSa 속도 | VS0' 속도 | M1 속도 | VSb 재고 | VSb 속도 | 시작 VSa 속도 | 시작 VSb 재고 |"
             " X1 10481 막힘 veh | X1 10483 막힘 veh |")
    L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')""")

rep("""        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s |' % (
            r['label'], r['T'], fmt(z['VSa']['e']['speed'], 1), fmt(z["VS0'"]['e']['speed'], 1),
            fmt(z['M1']['e']['speed'], 1), fmt(z['VSb']['e']['stock'], 1), fmt(z['VSb']['e']['speed'], 1),
            fmt((ib.get('VSa') or {}).get('e_speed'), 1), fmt((ib.get('VSb') or {}).get('e_stock'), 1)))
    L.append('')""", """        xb = (r.get('exits_base') or {}).get('blocked_veh') or {}
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r['label'], r['T'], fmt(z['VSa']['e']['speed'], 1), fmt(z["VS0'"]['e']['speed'], 1),
            fmt(z['M1']['e']['speed'], 1), fmt(z['VSb']['e']['stock'], 1), fmt(z['VSb']['e']['speed'], 1),
            fmt((ib.get('VSa') or {}).get('e_speed'), 1), fmt((ib.get('VSb') or {}).get('e_stock'), 1),
            fmt(xb.get('10481'), 1), fmt(xb.get('10483'), 1)))
    L.append('')
    L.append('- X1 요약(기준 굴림, w450, 막힘 ≥ 1 veh 인 상태 수 / 낸 상태 수): ' + ', '.join(
        '%s %s/%s' % (o, v['n_ge_1veh'], v['n_available']) for o, v in (res.get('P1_X1') or {}).items()))
    L.append('')""")

rep("""    L.append('| 후보 | 지표 | 정의된 상태 | R ≥ 0.5 | R ≤ −0.2 | 중앙 R | 띠 | 가리킴 규칙 | 기준과 비트 같음 |')
    L.append('|---|---|---:|---:|---:|---:|---|---|---:|')
    for name, ms in (p1.get('summary') or {}).items():
        for mname, v in ms.items():
            L.append('| %s | %s | %d | %d | %d | %s | %s | %s | %d |' % (
                name, mname, v['n_defined'], v['n_R_ge_0.5'], v['n_R_le_-0.2'], fmt(v['median_R'], 2),
                v['band'] or '—', '충족' if v['points_to_term'] else '미충족', v['n_bit_identical']))
    L.append('')""", """    L.append('| 후보 | 지표 | 정의된 상태 | R ≥ 0.5 | R ≤ −0.2 | 중앙 R | 띠 | 가리킴 규칙 | 기준과 비트 같음 | 방향 근거 |')
    L.append('|---|---|---:|---:|---:|---:|---|---|---:|---|')
    db = res.get('P1_direction') or {}
    for name, ms in (p1.get('summary') or {}).items():
        for mname, v in ms.items():
            lab = '충족' if v['points_to_term'] else '미충족'
            if name == 'C2_rhocrit' and v['points_to_term']:
                lab = '충족(×1.2 민감도)'
            if v.get('n_states') and v['n_bit_identical'] == v['n_states']:
                lab += ' · 구조상 0'
            d = db.get(mname) or {}
            if name == 'C1_vfree':
                basis = 'FD−VISSIM 저밀도 %s km/h (%d셀)' % (fmt(d.get('C1_fd_minus_vissim_low_speed_mean'), 1),
                                                            d.get('C1_cells') or 0)
            elif name == 'C2_rhocrit':
                basis = 'k_qmax > ρ_c %s/%s 셀%s' % (d.get('C2_cells_kqmax_above_rhoc'), d.get('C2_cells'),
                                                   ' (근거 있음)' if d.get('C2_basis') else ' (근거 없음)')
            else:
                basis = '—'
            L.append('| %s | %s | %d | %d | %d | %s | %s | %s | %d | %s |' % (
                name, mname, v['n_defined'], v['n_R_ge_0.5'], v['n_R_le_-0.2'], fmt(v['median_R'], 2),
                v['band'] or '—', lab, v['n_bit_identical'], basis))
    L.append('')""")

rep("""    res['P1_params'] = p1_params(res['P1'], C.read_json(C.OUT / 'p1_specs' / 'p1_inputs.json'))
    C.write_json(out_json, res)""", """    res['P1_params'] = p1_params(res['P1'], C.read_json(C.OUT / 'p1_specs' / 'p1_inputs.json'))
    res['P1_direction'] = direction_basis(res['P1_FZP'], res['P1_params'])
    res['P1_X1'] = x1_summary(res['P1'])
    C.write_json(out_json, res)""")

open(p, 'w', encoding='utf-8').write(s)
print('edited')
