"""VerifyGates 2 — F recomputed (amendment 24 section 5.3, amendment 30 sections 2 / 4.2 / 4.3).  No harness / driver /
judge import (vg3lib only).  Runs only when the J / F values are fixed (sha of OUTK/judge/f.json and jb.json in
KB/LOG.md, amendment 30 section 4.5); every opening is logged in KB/LOG.md by the operator before the run.

  steps     OUTK/steps.jsonl: the 24 F steps of the base run rc 0 with VISSIM 0 before / after, f_persist rc 1; the
            amendment-30 F steps judge_fcount, f_persist30, judge_f rc 0.
  counts    per arm OFF / W / B1 and group (s47 primary 22, s31 8, s43 8): job folders, summary.json ok true,
            k92_record.json present, its errors empty, capture.json present with ok not false (D-K9-57 5).
  rows      job TL3_<T>[_s<seed>]_SAF_OBS_H3 of the arm root, usable iff summary ok true, record present with empty
            errors, VISSIM state present with m1_T450; model = record horizon m1_chain_T450 / m2_w_dep_T450 /
            m3_l_dep_T450 (and T150); VISSIM = OUTK/f_vref k92_vissim_ref.json seeds.s<seed>.states[T] m1/m2/m3_T450.
  model x   the horizon numbers re-derived: M1 from blocks[k].chain (math.fsum of the three chain keys) and from
            k92_series.npz (last row ending at T+150 / T+450, fsum of the three chain columns); M2 / M3 = fsum of the
            block departures of SC109_W_SC108_to_E / SC109_W_SC108_to_N_SC16.  Bit equality reported.
  VISSIM x  M1 (P0-3 chain links, 13) counted again from the NC FZP of the seed at the frames T+150.1 / T+450.1 (and
            T+0.1 for the persistence states): rows of LANE\\LINK\\NO in the chain at SIMSEC = 5 k + 0.1; per link too.
            M2 / M3 (head passages, U4 measurer) are NOT recounted here (declared limitation).  FZP sha = VR record.
            Network identity of the .inpx (raw sha; randSeed value emptied -> normalized sha) recomputed.
  judge     e = model - VISSIM; MAE = fsum|e| / n, bias = fsum(e) / n; F-1 MAE_B1(M1_450) <= MAE_OFF(M1_450); F-2
            |bias_B1(M2_450)| <= |bias_OFF(M2_450)|; F-3 bias_B1(M3_450) - bias_OFF(M3_450) <= +5; n = 22.  PASS iff
            all three and n = 22; INCOMPLETE when an OFF / B1 primary row is missing or the s47 identity fails.
            Variant (report): F-1 with the FZP-recounted VISSIM M1.
  persist   amendment 30 section 2.2 / 2.4: measured iff T - 450 >= 900 (21), T = 1050 'not measurable (T_FROM=900)';
            persistence error = VR(f_persist30) m1_T450 of state T-450 - OFF VISSIM M1_450 of T; complete = identity
            1895ca30, integer keys = the 21 declared, integer m1_T450 for all, the 15 overlaps equal to f_vref.
  agree     vs OUTK/judge/f.json and f_jobs.json: verdicts / booleans / n / counts / labels exact; MAE / bias within
            1e-9 x max(1, |x|) (summation order).
Output OUTV/f.json (aggregates, flags; no per-state value)."""
import json
import math
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

ARMS = {'OFF': V.OUTK / 'f_off', 'W': V.OUTK / 'f_w', 'B1': V.OUTK / 'f_b1'}
GROUPS = (('s47_primary', 47, V.F_PRIMARY), ('s31_second', 31, V.F_SECOND[31]), ('s43_second', 43, V.F_SECOND[43]))
F_STEPS_RC0 = (['prep_%s_s%d' % (a, s) for a in ('f_off', 'f_w', 'f_b1') for s in (31, 43, 47)]
               + ['arms_ja_f', 'arms_f_b1']
               + ['f_%s_%s' % (a, x) for a in ('f_off', 'f_w', 'f_b1') for x in ('cap_s47', 'cap_s31', 'cap_s43', 'jobs')]
               + ['f_vref'])
MEASURED = tuple(T for T in V.F_PRIMARY if T - 450 >= 900)
NOT_MEASURABLE = tuple(T for T in V.F_PRIMARY if T - 450 < 900)
VR_STATES = tuple(T - 450 for T in MEASURED)
OVERLAP = tuple(t for t in VR_STATES if t in V.F_PRIMARY)
LABEL_EN = 'not measurable (T_FROM=900)'
W, L = V.W_KEY, V.L_KEY
TOL = 1e-9


def lab(seed, T):
    return 'TL3_%d%s_SAF_OBS_H3' % (T, '' if seed == 31 else '_s%d' % seed)


def jdir(root, seed, T):
    return Path(root) / 'sa' / 'jobs' / V.LABEL / lab(seed, T)


def cdir(root, seed, T):
    return Path(root) / 'sa' / 'cap' / V.LABEL / 'TL3' / ('%06d' % T + ('' if seed == 31 else '_s%d' % seed)) / 'SAF'


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


# ------------------------------------------------------------------------------------------------ steps / counts
def steps_check():
    rows = [json.loads(x) for x in (V.OUTK / 'steps.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    first = rows[:59]
    by = {}
    for r in first:
        by.setdefault(r['name'], []).append(r)
    rc0 = {n: [(r.get('rc'), r.get('vissim_pre'), r.get('vissim_post')) for r in by.get(n, [])] == [(0, 0, 0)]
           for n in F_STEPS_RC0}
    persist = [r.get('rc') for r in by.get('f_persist', [])] == [1]
    names = sorted(n for n in by if n.startswith(('f_', 'prep_f_')) or n in ('arms_ja_f', 'arms_f_b1'))
    later = {}
    for r in rows[59:]:
        if r['name'] in ('judge_fcount', 'f_persist30', 'judge_f'):
            later.setdefault(r['name'], []).append(r.get('rc'))
    return {'n_lines': len(rows), 'f_steps_rc0_vissim0': all(rc0.values()), 'bad': [n for n, v in rc0.items() if not v],
            'f_persist_rc1': persist, 'names_declared': names == sorted(F_STEPS_RC0 + ['f_persist']),
            'a30_steps': later, 'a30_steps_rc0': later == {'judge_fcount': [0], 'f_persist30': [0], 'judge_f': [0]}}


def job_counts():
    out = {}
    for arm, root in ARMS.items():
        row = {}
        for name, seed, Ts in GROUPS:
            c = {'planned': len(Ts), 'job_dirs': 0, 'summary_ok_true': 0, 'record_present': 0,
                 'record_errors_empty': 0, 'capture_ok': 0}
            for T in Ts:
                d = jdir(root, seed, T)
                c['job_dirs'] += d.is_dir()
                c['summary_ok_true'] += (V.rjson(d / 'summary.json') or {}).get('ok') is True
                rec = V.rjson(d / 'k92_record.json')
                if isinstance(rec, dict):
                    c['record_present'] += 1
                    c['record_errors_empty'] += not rec.get('errors')
                cap = V.rjson(cdir(root, seed, T) / 'capture.json')
                c['capture_ok'] += isinstance(cap, dict) and cap.get('ok') is not False
            c['all_ok'] = all(c[k] == c['planned'] for k in ('job_dirs', 'summary_ok_true', 'record_present',
                                                              'record_errors_empty', 'capture_ok'))
            row[name] = c
        out[arm] = row
    return out


# ------------------------------------------------------------------------------------------------ model side
def series_m1(d, t_end):
    import numpy as np
    p = d / 'k92_series.npz'
    if not p.is_file():
        return None
    z = np.load(V.lp(p), allow_pickle=True)
    keys = [str(k) for k in z['keys']]
    te = z['t_end']
    idx = [i for i in range(len(te)) if abs(float(te[i]) - t_end) < 1e-6]
    if not idx or any(k not in keys for k in V.CHAIN_KEYS):
        return None
    row = z['model'][idx[-1]]
    vals = [float(row[keys.index(k)]) for k in V.CHAIN_KEYS]
    if any(v != v for v in vals):
        return None
    return math.fsum(vals)


def model_check(rec, d, T):
    hz, b = rec.get('horizon') or {}, rec.get('blocks') or []
    out = {}
    try:
        out['m1_450_blocks'] = math.fsum(b[2]['chain'][k] for k in V.CHAIN_KEYS) == hz.get('m1_chain_T450')
        out['m1_150_blocks'] = math.fsum(b[0]['chain'][k] for k in V.CHAIN_KEYS) == hz.get('m1_chain_T150')
        out['m2_450_blocks'] = math.fsum(b[i]['departures'][W] for i in range(3)) == hz.get('m2_w_dep_T450')
        out['m3_450_blocks'] = math.fsum(b[i]['departures'][L] for i in range(3)) == hz.get('m3_l_dep_T450')
        out['m2_150_blocks'] = b[0]['departures'][W] == hz.get('m2_w_dep_T150')
        out['m3_150_blocks'] = b[0]['departures'][L] == hz.get('m3_l_dep_T150')
    except (IndexError, KeyError, TypeError):
        out['blocks_unreadable'] = True
    s450, s150 = series_m1(d, T + 450.0), series_m1(d, T + 150.0)
    out['m1_450_series'] = s450 is not None and s450 == hz.get('m1_chain_T450')
    out['m1_150_series'] = s150 is not None and s150 == hz.get('m1_chain_T150')
    out['all'] = all(v is True for k, v in out.items() if k != 'all')
    return out


def rows_of(root, seed, Ts, vref):
    rows, missing, mchk = {}, [], {}
    vs_all = ((vref.get('seeds') or {}).get('s%d' % seed) or {}).get('states') or {}
    for T in Ts:
        d = jdir(root, seed, T)
        summ = V.rjson(d / 'summary.json') or {}
        rec = V.rjson(d / 'k92_record.json')
        vs = vs_all.get(str(T))
        if (not isinstance(rec, dict) or summ.get('ok') is not True or rec.get('errors') or not isinstance(vs, dict)
                or vs.get('m1_T450') is None):
            missing.append(T)
            continue
        hz = rec.get('horizon') or {}
        r = {'M1_450': (hz.get('m1_chain_T450'), vs.get('m1_T450')), 'M2_450': (hz.get('m2_w_dep_T450'), vs.get('m2_T450')),
             'M3_450': (hz.get('m3_l_dep_T450'), vs.get('m3_T450')), 'M1_150': (hz.get('m1_chain_T150'), vs.get('m1_T150')),
             'M2_150': (hz.get('m2_w_dep_T150'), vs.get('m2_T150')), 'M3_150': (hz.get('m3_l_dep_T150'), vs.get('m3_T150'))}
        if any(x is None for pair in r.values() for x in pair):
            missing.append(T)
            continue
        rows[T] = r
        mchk[T] = model_check(rec, d, T)
    return rows, missing, mchk


def stats(rows, m):
    e = [r[m][0] - r[m][1] for r in rows.values()]
    n = len(e)
    return {'n': n, 'mae': math.fsum(abs(x) for x in e) / n if n else None, 'bias': math.fsum(e) / n if n else None}


def table(rows):
    return {m: stats(rows, m) for m in ('M1_450', 'M2_450', 'M3_450', 'M1_150', 'M2_150', 'M3_150')}


def judge(off, b1, suffix='450'):
    m1, m2, m3 = 'M1_' + suffix, 'M2_' + suffix, 'M3_' + suffix
    so, sb = table(off), table(b1)
    return {'F-1': sb[m1]['mae'] <= so[m1]['mae'], 'F-2': abs(sb[m2]['bias']) <= abs(so[m2]['bias']),
            'F-3': sb[m3]['bias'] - so[m3]['bias'] <= V.F3_LIMIT, 'n': so[m1]['n'],
            'numbers': {'mae_M1_b1': sb[m1]['mae'], 'mae_M1_off': so[m1]['mae'], 'abs_bias_M2_b1': abs(sb[m2]['bias']),
                        'abs_bias_M2_off': abs(so[m2]['bias']), 'bias_M3_b1_minus_off': sb[m3]['bias'] - so[m3]['bias']}}


# ------------------------------------------------------------------------------------------------ VISSIM side (FZP)
def fzp_counts(seed, frames):
    """{k: {link: n}} of the chain links at the frame indices `frames` (SIMSEC = 5 k + 0.1) + file sha / anomalies."""
    import hashlib
    path = V.NC3 / ('s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (seed, seed))
    keep = {str(x).encode(): x for x in V.CHAIN_LINKS}
    want = set(int(k) for k in frames)
    counts = {k: {x: 0 for x in V.CHAIN_LINKS} for k in want}
    h = hashlib.sha256()
    idx, n, odd = None, 0, 0
    with open(V.lp(path), 'rb', buffering=16 * 1024 * 1024) as f:
        for line in f:
            h.update(line)
            if idx is None:
                if line.startswith(b'$VEHICLE:'):
                    names = line[len(b'$VEHICLE:'):].strip().decode('latin-1').split(';')
                    idx = (names.index('SIMSEC'), names.index('LANE\\LINK\\NO'))
                continue
            if not line.strip() or line[:1] in (b'*', b'$'):
                continue
            p = line.split(b';')
            lk = keep.get(p[idx[1]].strip())
            if lk is None:
                continue
            t = float(p[idx[0]])
            k = int(round((t - 0.1) / 5.0))
            if abs(t - (5.0 * k + 0.1)) > 1e-6:
                odd += 1
                continue
            n += 1
            if k in want:
                counts[k][lk] += 1
    return {'path': str(path), 'sha256': h.hexdigest(), 'chain_rows': n, 'odd_time_rows': odd, 'counts': counts}


def inpx_identity(seed):
    path = V.NC3 / ('s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (seed, seed))
    b = open(V.lp(path), 'rb').read()
    ms = list(re.finditer(rb'(?<![A-Za-z0-9_])randSeed="([0-9]+)"', b))
    norm = V.sha_bytes(b[:ms[0].start()] + b'randSeed=""' + b[ms[0].end():]) if len(ms) == 1 else None
    return {'raw_sha256': V.sha_bytes(b), 'normalized_sha256': norm, 'randSeed_count': len(ms),
            'randSeed': ms[0].group(1).decode() if len(ms) == 1 else None,
            'raw_ok': V.sha_bytes(b) == V.INPX_RAW[seed], 'normalized_ok': norm == V.INPX_NORM}


def main():
    fixed, which = V.jf_fixed()
    if not fixed:
        raise SystemExit('J / F values are not fixed in the LOG (%s): the F data are not opened' % which)
    out = {'schema': 'vg3-f/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)),
           'lib_sha256': V.sha_file(Path(V.__file__)), 'jf_fixed': which}
    out['steps'] = steps_check()
    jc = job_counts()
    out['job_counts'] = jc
    out['fcount_verdict'] = 'PASS' if all(g['all_ok'] for r in jc.values() for g in r.values()) else 'INCOMPLETE'
    vref_p = V.OUTK / 'f_vref' / 'sa' / 'k92_vissim_ref.json'
    pers_p = V.OUTK / 'f_persist30' / 'sa' / 'k92_vissim_ref.json'
    vref, pers = V.rjson(vref_p) or {}, V.rjson(pers_p) or {}
    out['vref_sha256'], out['persist_sha256'] = V.sha_file(vref_p), V.sha_file(pers_p)
    ident = {}
    for s in (47, 31, 43):
        rec = ((vref.get('seeds') or {}).get('s%d' % s) or {}).get('network_identity') or {}
        mine = inpx_identity(s)
        ident['s%d' % s] = {'vref_raw_ok': rec.get('raw_sha256') == V.INPX_RAW[s],
                    'vref_norm_ok': rec.get('normalized_sha256') == V.INPX_NORM,
                    'recomputed_raw_ok': mine['raw_ok'], 'recomputed_norm_ok': mine['normalized_ok'],
                    'recomputed_equals_vref': mine['raw_sha256'] == rec.get('raw_sha256'),
                    'randSeed': mine['randSeed']}
    pid = (((pers.get('seeds') or {}).get('s47') or {}).get('network_identity') or {})
    ident['persist_s47_raw_ok'] = pid.get('raw_sha256') == V.INPX_RAW[47]
    out['network_identity'] = ident
    # rows
    prim, miss, mchk = {}, {}, {}
    for arm, root in ARMS.items():
        prim[arm], miss[arm], mchk[arm] = rows_of(root, 47, V.F_PRIMARY, vref)
    out['n_primary'] = {a: len(prim[a]) for a in prim}
    out['missing'] = miss
    out['model_crosscheck'] = {a: {'states': len(mchk[a]), 'all_bit_equal': all(x['all'] for x in mchk[a].values()),
                                   'failing': sorted(T for T, x in mchk[a].items() if not x['all'])}
                               for a in mchk}
    complete = all(not miss[a] and len(prim[a]) == 22 for a in ('OFF', 'B1')) and ident['s47']['vref_raw_ok'] and \
        ident['s47']['vref_norm_ok']
    if complete:
        fj = judge(prim['OFF'], prim['B1'])
        out['f_judge'] = fj
        out['verdict'] = 'PASS' if (fj['F-1'] and fj['F-2'] and fj['F-3'] and fj['n'] == 22) else 'FAIL'
        out['table'] = {a: table(prim[a]) for a in prim if len(prim[a]) == 22}
        out['report_T150'] = judge(prim['OFF'], prim['B1'], '150')
        if len(prim['W']) == 22:
            out['report_W_vs_OFF'] = judge(prim['OFF'], prim['W'])
    else:
        out['verdict'] = 'INCOMPLETE'
    # FZP recount of VISSIM M1
    fz = {}
    vstates = {s: ((vref.get('seeds') or {}).get('s%d' % s) or {}).get('states') or {} for s in (47, 31, 43)}
    pstates = ((pers.get('seeds') or {}).get('s47') or {}).get('states') or {}
    for s, Ts in ((47, V.F_PRIMARY), (31, V.F_SECOND[31]), (43, V.F_SECOND[43])):
        frames = {(T + 150) // 5 for T in Ts} | {(T + 450) // 5 for T in Ts}
        if s == 47:
            frames |= {T // 5 for T in MEASURED}
        res = fzp_counts(s, frames)
        rec_fzp = ((vref.get('seeds') or {}).get('s%d' % s) or {}).get('fzp') or {}
        chk = {'fzp_sha_equals_vref': res['sha256'] == rec_fzp.get('sha256'), 'odd_time_rows': res['odd_time_rows'],
               'chain_rows': res['chain_rows'], 'm1_equal': 0, 'm1_differ': [], 'by_link_equal': 0, 'by_link_differ': []}
        for T in Ts:
            vs = vstates[s].get(str(T)) or {}
            for dd in (150, 450):
                k = (T + dd) // 5
                mine = sum(res['counts'][k].values())
                if vs.get('m1_T%d' % dd) == mine:
                    chk['m1_equal'] += 1
                else:
                    chk['m1_differ'].append([T, dd])
                bl = vs.get('m1_by_link_T%d' % dd) or {}
                if {str(x): res['counts'][k][x] for x in V.CHAIN_LINKS} == {str(k2): v for k2, v in bl.items()}:
                    chk['by_link_equal'] += 1
                else:
                    chk['by_link_differ'].append([T, dd])
        if s == 47:
            chk['persist_equal'], chk['persist_differ'] = 0, []
            for T in MEASURED:
                a = (pstates.get(str(T - 450)) or {}).get('m1_T450')
                if a == sum(res['counts'][T // 5].values()):
                    chk['persist_equal'] += 1
                else:
                    chk['persist_differ'].append(T)
            if complete:
                fzp_off = {T: dict(r, M1_450=(r['M1_450'][0], sum(res['counts'][(T + 450) // 5].values())))
                           for T, r in prim['OFF'].items()}
                fzp_b1 = {T: dict(r, M1_450=(r['M1_450'][0], sum(res['counts'][(T + 450) // 5].values())))
                          for T, r in prim['B1'].items()}
                out['variant_F1_with_fzp_m1'] = judge(fzp_off, fzp_b1)['F-1']
        fz['s%d' % s] = chk
    out['fzp_m1'] = fz
    # persistence (amendment 30 section 2)
    pe, states, missing_p = [], {}, []
    for T in V.F_PRIMARY:
        if T in NOT_MEASURABLE:
            states[str(T)] = LABEL_EN
            continue
        a = (pstates.get(str(T - 450)) or {}).get('m1_T450')
        b = ((prim.get('OFF') or {}).get(T) or {}).get('M1_450', (None, None))[1]
        if isinstance(a, int) and not isinstance(a, bool) and b is not None:
            pe.append(a - b)
            states[str(T)] = 'measured'
        else:
            states[str(T)] = 'missing'
            missing_p.append(T)
    keys = sorted(pstates)
    bad_keys = [k for k in keys if not str(k).isdigit()]
    got = sorted(int(k) for k in keys if str(k).isdigit())
    ov = {str(t): (pstates.get(str(t)) or {}).get('m1_T450') is not None and
          (pstates.get(str(t)) or {}).get('m1_T450') == (vstates[47].get(str(t)) or {}).get('m1_T450') for t in OVERLAP}
    pr = {'n': len(pe), 'mae': math.fsum(abs(x) for x in pe) / len(pe) if pe else None, 'states': states,
          'measured': [T for T in V.F_PRIMARY if states[str(T)] == 'measured'],
          'not_measurable': {str(T): LABEL_EN for T in NOT_MEASURABLE}, 'missing': missing_p,
          'vr_states_equal_declared': got == sorted(VR_STATES), 'vr_state_keys_not_int': bad_keys,
          'overlap_with_f_vref': {'n': len(ov), 'n_equal': sum(1 for v in ov.values() if v)},
          'identity_ok': ident['persist_s47_raw_ok']}
    pr['complete'] = (pr['identity_ok'] and not bad_keys and pr['vr_states_equal_declared'] and not missing_p
                      and len(pe) == len(MEASURED) and all(ov.values()))
    out['persistence'] = pr
    # second sample (report)
    sec = {}
    for arm, root in ARMS.items():
        allr, allm = {}, []
        for seed, Ts in V.F_SECOND.items():
            r, m, _x = rows_of(root, seed, Ts, vref)
            allr.update({'s%d_%d' % (seed, T): v for T, v in r.items()})
            allm += ['s%d_%d' % (seed, T) for T in m]
        sec[arm] = {'n': len(allr), 'missing': allm, 'table': table(allr) if allr else None}
    out['second_sample'] = sec
    # agreement with the recorded files
    rec = V.rjson(V.OUTK / 'judge' / 'f.json') or {}
    rjc = V.rjson(V.OUTK / 'judge' / 'f_jobs.json') or {}
    ag = {}
    rf = rec.get('f_judge') or {}
    ag['verdict'] = rec.get('verdict') == out['verdict']
    ag['f123n'] = all(rf.get(k) == (out.get('f_judge') or {}).get(k) for k in ('F-1', 'F-2', 'F-3', 'n'))
    ag['table'] = all(close((rec.get('table') or {}).get(a, {}).get(m, {}).get(x), out['table'][a][m][x])
                      and (rec.get('table') or {}).get(a, {}).get(m, {}).get('n') == out['table'][a][m]['n']
                      for a in out.get('table', {}) for m in out['table'][a] for x in ('mae', 'bias'))
    ag['T150'] = all((rec.get('report_T150') or {}).get(k) == out['report_T150'].get(k)
                     for k in ('F-1', 'F-2', 'F-3', 'n')) if 'report_T150' in out else False
    ag['W_vs_OFF'] = all((rec.get('report_W_vs_OFF') or {}).get(k) == out['report_W_vs_OFF'].get(k)
                         for k in ('F-1', 'F-2', 'F-3', 'n')) if 'report_W_vs_OFF' in out else False
    rp = rec.get('report_persistence_M1_450') or {}
    ag['persistence'] = (rp.get('n') == pr['n'] and close(rp.get('mae'), pr['mae']) and rp.get('states') == pr['states']
                         and rp.get('measured') == pr['measured'] and rp.get('not_measurable') == pr['not_measurable']
                         and rp.get('complete') == pr['complete'] and rp.get('overlap_with_f_vref') == pr['overlap_with_f_vref']
                         and rp.get('vr_states_equal_declared') == pr['vr_states_equal_declared']
                         and rp.get('identity_ok') == pr['identity_ok'] and rp.get('missing') == pr['missing'])
    ag['job_counts_f'] = rec.get('job_counts') == jc
    ag['job_counts_fcount'] = rjc.get('job_counts') == jc and rjc.get('verdict') == out['fcount_verdict']
    ag['n_primary'] = rec.get('n_primary') == out['n_primary']
    ag['missing'] = {a: list(v) for a, v in (rec.get('missing') or {}).items()} == {a: list(v) for a, v in miss.items()}
    rs = rec.get('report_second_sample') or {}
    ag['second_sample'] = all(
        (rs.get(a) or {}).get('n') == sec[a]['n'] and (rs.get(a) or {}).get('missing') == sec[a]['missing'] and all(
            close(((rs.get(a) or {}).get('table') or {}).get(m, {}).get(x), sec[a]['table'][m][x])
            for m in sec[a]['table'] for x in ('mae', 'bias')) for a in sec if sec[a]['table'])
    ag['network_identity_ok'] = (rec.get('network_identity_ok') or {}) == {
        str(s): (ident['s%d' % s]['vref_raw_ok'] and ident['s%d' % s]['vref_norm_ok']) for s in (47, 31, 43)}
    ag['persist_identity_ok'] = rec.get('persist_identity_ok') == ident['persist_s47_raw_ok']
    out['recorded'] = {'f_sha256': V.sha_file(V.OUTK / 'judge' / 'f.json'),
                       'f_jobs_sha256': V.sha_file(V.OUTK / 'judge' / 'f_jobs.json'), 'verdict': rec.get('verdict')}
    out['agreement'] = ag
    out['agree_all'] = all(ag.values())
    V.wjson(V.OUTV / 'f.json', out)
    fj = out.get('f_judge') or {}
    print('VG3_F verdict=%s F1=%s F2=%s F3=%s n=%s fcount=%s persist_complete=%s n=%s agree=%s bad=%s' % (
        out['verdict'], fj.get('F-1'), fj.get('F-2'), fj.get('F-3'), fj.get('n'), out['fcount_verdict'],
        pr['complete'], pr['n'], out['agree_all'], [k for k, v in ag.items() if not v]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
