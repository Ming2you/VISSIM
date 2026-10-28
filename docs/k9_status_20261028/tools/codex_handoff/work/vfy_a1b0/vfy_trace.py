# -*- coding: utf-8 -*-
"""VERIFY_A1_B0: A1 결정 파일 대 codex joint 기록 독립 대조 (저자 a1_trace.py 재사용 없음).

- 결정마다 action_T.csv 바이트 같음, 행별 차(행 순서 맞춤, 키 열 같음 확인), kind 별 수.
- 신호: p1-p4 녹색·offset 최대 |차|, 다른 SC, 녹색 차 >= 1 s 칸 수.
- 미터: id 별 (rate_vph, green_sec) 다른 것. VSL: 속도 다른 행, 속도 값 집합.
- 유지: action_T.json metadata.controller_status, 행 metadata 의 hold_previous_error=1 수, error.txt 마지막 줄.
- A0b T=1050-2550 CSV 와 R1.
- state_T.json, obs150/derived_T.json 잎 대조(T=1050,1200,1350): 경로·64hex·시각·부속 키를 뺀 '값' 잎 차 수.
- runlog CONTROLLER_DECISION wall_sec 합·최대.
"""
import json, os, sys, csv, io, re, hashlib, glob

OUT = sys.argv[1]
A1 = 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
JT = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
A0B = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/out/a0b_hsw/T%06d/files/sdmpc/decisions_sdmpc31_sdmpc8100_s29/action_%06d.csv'
RL = {'a1': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/runlog_sdmpc31_sdmpc8100_s29.txt',
      'joint': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/runlog_sdmpc31_sdmpc8100_s29.txt'}
KEYS = ('kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane')
GREENS = ('p1_green', 'p2_green', 'p3_green', 'p4_green')
HEX64 = re.compile(r'^[0-9a-fA-F]{64}$')
CLOCK = re.compile(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}|^\d{8}T\d{6}|^\d{10}(\.\d+)?$')
ACCESSORY = {'run_id', 'byte_start', 'byte_end', 'max_t_any'}


def rd(p):
    with open(p, 'rb') as f:
        return f.read()


def rows(b):
    r = list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
    return r


def fnum(x):
    try:
        return float(x)
    except Exception:
        return None


def cmp_csv(ba, bb):
    ra, rb = rows(ba), rows(bb)
    out = {'n_a': len(ra), 'n_b': len(rb), 'keys_aligned': len(ra) == len(rb) and all(
        tuple(x[k] for k in KEYS) == tuple(y[k] for k in KEYS) for x, y in zip(ra, rb))}
    if not out['keys_aligned']:
        return out
    kinds = {}
    diff_kinds = {}
    sc = set()
    gmax = 0.0
    omax = 0.0
    g1 = 0
    meters = {}
    vsl_diff = 0
    vsl_a, vsl_b = set(), set()
    vsl_diff_ids = set()
    hold_a = hold_b = 0
    nd = 0
    nd_ignore_hold = 0
    for x, y in zip(ra, rb):
        k = x['kind']
        kinds[k] = kinds.get(k, 0) + 1
        if 'hold_previous_error=1' in x.get('metadata', ''):
            hold_a += 1
        if 'hold_previous_error=1' in y.get('metadata', ''):
            hold_b += 1
        if x != y:
            nd += 1
            diff_kinds[k] = diff_kinds.get(k, 0) + 1
            xx = {kk: vv for kk, vv in x.items() if kk != 'metadata'}
            yy = {kk: vv for kk, vv in y.items() if kk != 'metadata'}
            if xx != yy:
                nd_ignore_hold += 1
        if k in ('signal', 'signal_sg'):
            dif = False
            for g in GREENS:
                a, b = fnum(x[g]), fnum(y[g])
                if a is not None and b is not None:
                    d = abs(a - b)
                    gmax = max(gmax, d)
                    if d >= 1.0:
                        g1 += 1
                    if d > 0:
                        dif = True
                elif (a is None) != (b is None):
                    dif = True
            a, b = fnum(x['offset']), fnum(y['offset'])
            if a is not None and b is not None:
                omax = max(omax, abs(a - b))
                if a != b:
                    dif = True
            if dif:
                sc.add(x['sc_no'])
        elif k == 'vsl':
            vsl_a.add(x['speed_kph'])
            vsl_b.add(y['speed_kph'])
            if fnum(x['speed_kph']) != fnum(y['speed_kph']):
                vsl_diff += 1
                vsl_diff_ids.add((x['id'], x['link'], x['lane'], x['speed_kph'], y['speed_kph']))
        elif 'meter' in k or k.startswith('ramp'):
            if (x['rate_vph'], x['green_sec']) != (y['rate_vph'], y['green_sec']):
                meters[x['id']] = [x['rate_vph'] + '/' + x['green_sec'], y['rate_vph'] + '/' + y['green_sec']]
    out.update({'kinds': kinds, 'n_diff_rows': nd, 'n_diff_rows_excl_metadata': nd_ignore_hold, 'diff_kinds': diff_kinds,
                'sc_diff': sorted(sc, key=lambda s: int(s) if s.isdigit() else 0), 'green_max': gmax,
                'offset_max': omax, 'green_ge1_cells': g1, 'meters_diff': meters, 'vsl_diff_rows': vsl_diff,
                'vsl_a': sorted(vsl_a), 'vsl_b': sorted(vsl_b), 'vsl_diff_ids': sorted(vsl_diff_ids),
                'hold_rows_a': hold_a, 'hold_rows_b': hold_b})
    return out


def flatten(x, p='', out=None):
    if out is None:
        out = {}
    if isinstance(x, dict):
        if not x:
            out[p + '/{}'] = '{}'
        for k, v in x.items():
            flatten(v, p + '/' + str(k), out)
    elif isinstance(x, list):
        if not x:
            out[p + '/[]'] = '[]'
        for i, v in enumerate(x):
            flatten(v, p + '/%d' % i, out)
    else:
        out[p] = x
    return out


def looks_path(s):
    return isinstance(s, str) and ('\\' in s or (':/' in s) or s.startswith('/')) and ('.' in s or '\\' in s or '/' in s)


def leafcmp(pa, pb):
    if not (os.path.isfile(pa) and os.path.isfile(pb)):
        return {'missing': [pa if not os.path.isfile(pa) else None, pb if not os.path.isfile(pb) else None]}
    fa = flatten(json.loads(rd(pa).decode('utf-8-sig')))
    fb = flatten(json.loads(rd(pb).decode('utf-8-sig')))
    ka, kb = set(fa), set(fb)
    cls = {'path': 0, 'hex64': 0, 'clock': 0, 'accessory': 0, 'value': 0, 'only_a': len(ka - kb), 'only_b': len(kb - ka)}
    ex = []
    num_max = 0.0
    top = {}
    for k in ka & kb:
        a, b = fa[k], fb[k]
        if a == b and type(a) == type(b):
            continue
        last = k.rsplit('/', 1)[-1]
        if last in ACCESSORY:
            cls['accessory'] += 1
        elif isinstance(a, str) and isinstance(b, str) and HEX64.match(a) and HEX64.match(b):
            cls['hex64'] += 1
        elif looks_path(a) and looks_path(b):
            cls['path'] += 1
        elif isinstance(a, str) and isinstance(b, str) and CLOCK.search(a) and CLOCK.search(b):
            cls['clock'] += 1
        else:
            cls['value'] += 1
            t = k.split('/')[1] if k.count('/') >= 1 else k
            top[t] = top.get(t, 0) + 1
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
                num_max = max(num_max, abs(a - b))
            if len(ex) < 12:
                ex.append([k, str(a)[:80], str(b)[:80]])
    return {'leaves_a': len(fa), 'leaves_b': len(fb), 'common': len(ka & kb), 'classes': cls, 'value_top': top,
            'value_num_max_abs': num_max, 'examples': ex}


def runlog(p):
    out = {}
    held = {}
    with open(p, 'rb') as f:
        for raw in f:
            line = raw.decode('utf-8', 'replace')
            if 'CONTROLLER_DECISION' in line:
                m1 = re.search(r'sim_sec=([0-9.]+)', line)
                m2 = re.search(r'wall(?:_sec)?=([0-9.]+)', line)
                m3 = re.search(r'exit=(-?\d+)', line)
                if m1:
                    out[int(float(m1.group(1)))] = {'wall': float(m2.group(1)) if m2 else None,
                                                    'exit': int(m3.group(1)) if m3 else None}
            if 'DECISION_HELD_PREVIOUS' in line:
                m1 = re.search(r'sim_sec=([0-9.]+)', line)
                if m1:
                    held[int(float(m1.group(1)))] = line.strip()[:200]
    return out, held


def main():
    res = {}
    ta = sorted(int(os.path.basename(p)[7:13]) for p in glob.glob(A1 + '/action_[0-9]*.csv'))
    tb = sorted(int(os.path.basename(p)[7:13]) for p in glob.glob(JT + '/action_[0-9]*.csv'))
    res['T_a1'] = ta
    res['T_joint_equal_set'] = ta == tb
    per = {}
    first_diff = None
    for T in ta:
        ba, bb = rd('%s/action_%06d.csv' % (A1, T)), rd('%s/action_%06d.csv' % (JT, T))
        r = {'R1_same': ba == bb}
        if ba != bb:
            if first_diff is None:
                first_diff = T
            r.update(cmp_csv(ba, bb))
        for side, d in (('a1', A1), ('joint', JT)):
            j = json.loads(rd('%s/action_%06d.json' % (d, T)).decode('utf-8-sig'))
            r['status_' + side] = j.get('metadata', {}).get('controller_status')
            r['selobj_' + side] = j.get('metadata', {}).get('selected_objective', j.get('diagnostics', {}).get('selected_objective') if isinstance(j.get('diagnostics'), dict) else None)
            e = '%s/action_%06d.error.txt' % (d, T)
            if os.path.isfile(e):
                lines = [l for l in rd(e).decode('utf-8', 'replace').splitlines() if l.strip()]
                r['error_last_' + side] = lines[-1][:200] if lines else ''
        per[T] = r
    res['per_T'] = per
    res['first_R1_diff_T'] = first_diff
    # A0b
    a0 = {}
    for T in range(1050, 2551, 150):
        p = A0B % (T, T)
        if not os.path.isfile(p):
            a0[T] = 'missing'
            continue
        b0 = rd(p)
        a0[T] = {'A0b_eq_joint': b0 == rd('%s/action_%06d.csv' % (JT, T)), 'A0b_eq_A1': b0 == rd('%s/action_%06d.csv' % (A1, T))}
        if not a0[T]['A0b_eq_A1']:
            c = cmp_csv(rd('%s/action_%06d.csv' % (A1, T)), b0)
            a0[T]['A1_vs_A0b_diff_rows'] = c.get('n_diff_rows')
        if not a0[T]['A0b_eq_joint']:
            c = cmp_csv(b0, rd('%s/action_%06d.csv' % (JT, T)))
            a0[T]['A0b_vs_joint'] = {k: c.get(k) for k in ('n_diff_rows', 'diff_kinds', 'green_max', 'offset_max', 'meters_diff', 'vsl_diff_rows', 'sc_diff', 'green_ge1_cells')}
    res['a0b'] = a0
    # 입력 잎
    st = {}
    for T in (1050, 1200, 1350):
        st[T] = {'state': leafcmp('%s/state_%06d.json' % (A1, T), '%s/state_%06d.json' % (JT, T)),
                 'derived': leafcmp('%s/obs150/derived_%06d.json' % (A1, T), '%s/obs150/derived_%06d.json' % (JT, T))}
    res['inputs'] = st
    # runlog
    rl = {}
    for side, p in RL.items():
        dec, held = runlog(p)
        ctrl = {T: v for T, v in dec.items() if T >= 900}
        walls = [v['wall'] for v in ctrl.values() if v['wall'] is not None]
        rl[side] = {'n_ctrl': len(ctrl), 'sum_wall': sum(walls), 'max_wall': max(walls) if walls else None,
                    'argmax': max(ctrl, key=lambda T: ctrl[T]['wall'] or -1) if ctrl else None,
                    'n_gt1500': sum(1 for w in walls if w > 1500), 'n_gt1800': sum(1 for w in walls if w > 1800),
                    'exit_nonzero_T': sorted(T for T, v in ctrl.items() if v['exit'] not in (0, None)),
                    'warm_sum': sum(v['wall'] or 0 for T, v in dec.items() if T < 900),
                    'held_lines_T': sorted(held), 'per_T': ctrl}
    res['runlog'] = rl
    # 요약
    ctrlT = [T for T in ta if T >= 900]
    summ = {'n_ctrl_T': len(ctrlT)}
    later = [T for T in ctrlT if T >= 1500]
    summ['T_ge1500_signal_all17_sg_all122'] = all(
        per[T].get('diff_kinds', {}).get('signal', 0) == per[T].get('kinds', {}).get('signal', -1) == 17 and
        per[T].get('diff_kinds', {}).get('signal_sg', 0) == per[T].get('kinds', {}).get('signal_sg', -1) == 122
        for T in later)
    mcounts = {T: len(per[T].get('meters_diff', {})) for T in ctrlT if T >= 1200}
    summ['meter_diff_counts_T_ge1200'] = mcounts
    summ['vsl_diff_T'] = sorted(T for T in ctrlT if per[T].get('vsl_diff_rows'))
    summ['hold_T_a1'] = sorted(T for T in ta if per[T]['status_a1'] not in ('ok', None))
    summ['hold_T_joint'] = sorted(T for T in ta if per[T]['status_joint'] not in ('ok', None))
    summ['status_values'] = sorted(set(str(per[T]['status_a1']) for T in ta) | set(str(per[T]['status_joint']) for T in ta))
    res['summary'] = summ
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    T12 = per.get(1200, {})
    print(json.dumps({'first_diff': first_diff, 'T1200': {k: T12.get(k) for k in ('n_diff_rows', 'diff_kinds', 'green_max', 'offset_max', 'meters_diff', 'sc_diff', 'vsl_diff_rows')},
                      'summary': summ, 'a0b': a0, 'inputs_value': {T: (st[T]['state'].get('classes'), st[T]['derived'].get('classes')) for T in st},
                      'runlog': {s: {k: rl[s][k] for k in ('n_ctrl', 'sum_wall', 'max_wall', 'argmax', 'n_gt1500', 'exit_nonzero_T', 'warm_sum')} for s in rl}},
                     ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
