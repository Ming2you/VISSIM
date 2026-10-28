# -*- coding: utf-8 -*-
"""fwe_synth.py - D-K9-106 L5 synthesis (2026-10-27 KST).

PRE_FWE.md section 6.1 (mechanism-candidate flags) and 6.2 (C1 FW_E reference line, report-only fields).
Reads ONLY pinned JSON outputs of R1-R4 and existing fwe_scan caches (JSON, no FZP). No VISSIM, no COM.

  python -B fwe_synth.py run    -> out/FWE_ATTRIB.json, out/FWE_REF_C1.json, out/FWE_REF_C1.md

Rules (fixed in PRE_FWE section 6 before any number; interpretation logged LOG 17:2x):
  G       = gain windows (d1 <= -2.0 veh.h, >= 900 s), from R3 sec6_inputs_over_G.
  C-RM    = some FW_E meter m: G tight fraction >= 0.30 (numeric only) AND merge_m G dvph <= -60
            AND downstream zone d1 <= -1.0 (10639,10681 -> B1; 10490,10484 -> B2).
  C-OFF1  = d stock 10643 (G) <= -1.0 AND d1 (U+B1) (G) <= -1.0.
  C-OFF2  = d stock 10481 (G) <= -1.0 AND d1 (M+B2) (G) <= -1.0.
  C-VSL   = V-A: VSL<110 decisions overlapping G >= 1; VSL arm: always true; B: always false;
            other pairs: not defined (None, value reported).
  C-ENT   = d u1098 (G) >= +1.0 AND d1 U (G) <= -1.0.
  C-NONE  = all of the above false (None counts as false).
RF9 arm spill minutes: tails.py (pinned) applied to the fwe_scan cache of each arm; NC3 values must equal R1.
P-BVA RF5-RF8: same-seed P-B minus P-VA (shared NC3 base, checked identical).
"""
import hashlib, importlib.util, json, os, sys, time

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
FD = SP + '/fwe_decomp'
PINS = {
    FD + '/PRE_FWE.md': 'c7cc0e6cc629da156b3ada7278af0fd95a0be4bf80d86ac6532b09e21656ce94',
    FD + '/out/R1_nc.json': 'd2dc870be1546d5518a2ab8e75415e1736cd5e21f8bbcf65bec3d846809537ac',
    FD + '/out/R2_pairs.json': 'c80860d217d3d77dafac807d97610a14b2a2a7adc63c437f869b62ce6fc4a12a',
    FD + '/out/R2_after.json': 'b25c30ad753dec7520ad7828f1cbba1703aa38317a6434a256c496307719ebb9',
    FD + '/out/R3_meters.json': 'e8e4d5db8c8e1423f88b09e6a1c06edff6e8fd16b2dbbc04102c197af554a8a1',
    FD + '/out/R4_codex.json': 'e85a5734036c2b443a1a5ef976c0c22550a7684f9850795795fd6dbd6eb67bc6',
    SP + '/rmcause/o1o4/work/tails.py': 'cb6c0bd4407fbaad8b403ccc34fc2bcfb1f9b9af318a67ee963b120a8bfb5569',
}
SEEDS = (31, 41, 43)
METERS = ('10639', '10681', '10490', '10484')
RM = {m: 'RM_C' + m for m in METERS}
DOWN = {'10639': 'd1_B1_G', '10681': 'd1_B1_G', '10490': 'd1_B2_G', '10484': 'd1_B2_G'}
EXITS = ('10643', '10682', '10481', '10483')
ZONES5 = ('U', 'B1', 'M', 'B2', 'D')
TH = {'tight': 0.30, 'dvph': -60.0, 'dz': -1.0, 'stock': -1.0, 'd1': -1.0, 'u1098': 1.0, 'vsl': 1}
# R2 pair key -> R3 pair key
R3KEY = {}
for s in SEEDS:
    for p in ('P-VA', 'P-B', 'P-VSL'):
        R3KEY['%s|v3c3-s%d' % (p, s)] = '%s v3c3-s%d' % (p, s)
    R3KEY['P-J1|v3c3-s%d' % s] = 'P-J1 v3c3-s%d (참고)' % s
R3KEY.update({'Q-joint|64cf-s29': 'Q-joint 64cf-s29', 'Q-window|64cf-s29': 'Q-window 64cf-s29',
              'Q-off|64cf-s29': 'Q-off 64cf-s29', 'Q-fw|64cf-s29': 'Q-fw 64cf-s29', 'Q-urb|64cf-s29': 'Q-urb 64cf-s29',
              'Q-A1|64cf-s29': 'Q-A1 (A1 − LNC) 64cf-s29 (참고)', 'Q-A1j|64cf-s29': 'Q-A1 (A1 − joint) 64cf-s29 (참고)',
              'Q-VSL64|64cf-s29': 'Q-VSL64 (vsl_repro vsl − LNC) 64cf-s29 (참고, bin 꼴)'})
ARMS_V3 = ('NC3', 'VA', 'B', 'VSL', 'J1')


# ---------------------------------------------------------------- io
def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def pinned(p, want=None):
    want = want or PINS[p]
    got = sha256(p)
    if got != want:
        raise SystemExit('PIN MISMATCH %s %s != %s' % (p, got, want))
    return got


def jload(p, want=None):
    pinned(p, want)
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def load_module(name, p):
    pinned(p)
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- pure functions (selftest imports these)
def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def flags(kind, s6):
    """kind in {'P-VA','P-B','P-VSL','P-J1','Q-VSL64','Q-other'}; s6 = R3 sec6_inputs_over_G dict."""
    gn = (s6 or {}).get('G_n', 0)
    res = {'G_n': gn, 'C-RM': False, 'C-RM_meters': [], 'C-OFF1': False, 'C-OFF2': False, 'C-ENT': False}
    # C-VSL is defined by kind, independent of G for the VSL arm (PRE 6.1 "늘 참")
    vov = (s6 or {}).get('vsl_lt110_decisions_overlapping_G')
    if kind == 'P-VA':
        res['C-VSL'] = bool(gn) and is_num(vov) and vov >= TH['vsl']
    elif kind in ('P-VSL', 'Q-VSL64'):
        res['C-VSL'] = True
    elif kind == 'P-B':
        res['C-VSL'] = False
    else:
        res['C-VSL'] = None          # not defined in PRE 6.1; value reported
    res['vsl_overlap_value'] = vov
    if gn:
        for m in METERS:
            tf = s6.get('%s_G_tight_frac' % RM[m])
            dv = s6.get('merge_%s_G_dvph' % m)
            dz = s6.get(DOWN[m])
            if is_num(tf) and tf >= TH['tight'] and is_num(dv) and dv <= TH['dvph'] and is_num(dz) and dz <= TH['dz']:
                res['C-RM_meters'].append(m)
        res['C-RM'] = bool(res['C-RM_meters'])
        res['C-OFF1'] = s6['d_stock_10643_G'] <= TH['stock'] and s6['d1_U_B1_G'] <= TH['d1']
        res['C-OFF2'] = s6['d_stock_10481_G'] <= TH['stock'] and s6['d1_M_B2_G'] <= TH['d1']
        res['C-ENT'] = s6['d_u1098_G'] >= TH['u1098'] and s6['d1_U_G'] <= TH['d1']
    res['C-NONE'] = not any(res[k] is True for k in ('C-RM', 'C-OFF1', 'C-OFF2', 'C-VSL', 'C-ENT'))
    return res


def group900(a, how='sum'):
    """300 s windows -> 900 s windows (sum for veh.h, mean for veh/h). None -> None."""
    out = []
    for k in range(0, len(a) - len(a) % 3, 3):
        t = a[k:k + 3]
        if any(x is None for x in t):
            out.append(None)
        else:
            out.append(sum(t) if how == 'sum' else sum(t) / 3.0)
    return out


def vsub(a, b):
    return [None if (x is None or y is None) else x - y for x, y in zip(a, b)]


def spill_from_scan(T, d):
    s = T.summary(d)
    nw900 = (len(s['b1_tail_m']) + 14) // 15
    b1w = s['b1_spill_windows']
    mw = s['m_spill_windows']
    return {'b1_spill_min_lt4500': s['b1_spill_min_lt4500'], 'm_spill_min_lt6800': s['m_spill_min_lt6800'],
            'b1_tail_min_m': s['b1_tail_min_m'], 'b1_tail_min_at_s': s['b1_tail_min_at_s'], 'b2_tail_min_m': s['b2_tail_min_m'],
            'b1_spill_min_900': [sum(1 for w in b1w if 15 * k <= w < 15 * k + 15) for k in range(min(nw900, 10))],
            'm_spill_min_900': [sum(1 for w in mw if 15 * k <= w < 15 * k + 15) for k in range(min(nw900, 10))]}


def ramp_d300(rp):
    """meter-side stock (connector + approach link) d per 300 s window, and queue d."""
    st = vsub([a + b for a, b in zip(rp['conn_stock']['arm'], rp['from_stock']['arm'])],
              [a + b for a, b in zip(rp['conn_stock']['base'], rp['from_stock']['base'])])
    q = vsub([a + b for a, b in zip(rp['conn_q']['arm'], rp['from_q']['arm'])],
             [a + b for a, b in zip(rp['conn_q']['base'], rp['from_q']['base'])])
    return st, q


def ramp_arm300(rp, side='arm'):
    return [a + b for a, b in zip(rp['conn_stock'][side], rp['from_stock'][side])]


def r1(x, nd=1):
    return None if x is None else round(x, nd)


# ---------------------------------------------------------------- build
def build():
    t0 = time.time()
    R1 = jload(FD + '/out/R1_nc.json')
    R2 = jload(FD + '/out/R2_pairs.json')
    RA = jload(FD + '/out/R2_after.json')
    R3 = jload(FD + '/out/R3_meters.json')
    R4 = jload(FD + '/out/R4_codex.json')
    pinned(FD + '/PRE_FWE.md')
    T = load_module('tails', SP + '/rmcause/o1o4/work/tails.py')
    for J, nm in ((R2, 'R2'), (R3, 'R3'), (R4, 'R4')):
        if J.get('pre_fwe_sha256', J.get('checks', {}).get('pre_sha')) not in (PINS[FD + '/PRE_FWE.md'], None):
            raise SystemExit('%s built from another PRE' % nm)
    stops, checks = [], {}

    # ---------- RF9 arm spill (tails on fwe_scan caches; cache sha = R3 arms record)
    spills = {}
    for s in SEEDS:
        for a in ARMS_V3:
            ar = R3['arms']['%s-s%d' % (a, s)]
            if ar.get('seed') != s:
                raise SystemExit('seed mismatch %s-s%d' % (a, s))
            d = jload(ar['fwe_file'], ar['fwe_file_sha256'])
            if d.get('fzp_sha256') and ar.get('fwe_fzp_sha256') and d['fzp_sha256'] != ar['fwe_fzp_sha256']:
                raise SystemExit('fzp sha inside cache differs %s-s%d' % (a, s))
            spills['%s-s%d' % (a, s)] = dict(spill_from_scan(T, d), cache=ar['fwe_file'], cache_sha256=ar['fwe_file_sha256'],
                                             fzp_sha256=ar.get('fwe_fzp_sha256'))
        r1t = R1['arms']['v3c3-s%d' % s]['R1']['R1f_tails']
        mine = spills['NC3-s%d' % s]
        ok = all(mine[k] == r1t[k] for k in ('b1_spill_min_lt4500', 'm_spill_min_lt6800', 'b1_tail_min_m', 'b2_tail_min_m'))
        checks['RF9_NC3_equals_R1_s%d' % s] = ok
        if not ok:
            stops.append('RF9 NC3 v3c3-s%d differs from R1' % s)

    # ---------- section 6.1 attribution table
    attrib = {}
    for k2, k3 in R3KEY.items():
        p2, p3 = R2['pairs'][k2], R3['pairs'][k3]
        pk = k2.split('|')[0]
        kind = pk if pk in ('P-VA', 'P-B', 'P-VSL', 'P-J1', 'Q-VSL64') else 'Q-other'
        s6 = p3.get('sec6_inputs_over_G') or {'G_n': 0}
        fl = flags(kind, s6)
        form = 'ours_9000' if p2['net'] == 'v3c3' else 'codex_8100'
        a2 = p2['R2a'][form] if form in p2['R2a'] else None
        if a2 is None:            # vsl_repro: bin form only
            form = 'bin_8100'
            a2 = p2['R2a']['bin_8100']
        zone = {z: r1(sum(p2['R2c']['zones5'][z]['d_veh_h'])) for z in ZONES5}
        mt = {}
        for m in METERS:
            ma = p3['meter_arm'].get(RM[m]) if isinstance(p3['meter_arm'], dict) else None
            if not isinstance(ma, dict) or 'n_cycles' not in ma:
                mt[m] = {'state': 'read', 'note': (p3['meter_arm'] or {}).get('note') if isinstance(p3['meter_arm'], dict) else None}
            elif ma.get('state_none'):
                mt[m] = {'state': 'state_none'}
            else:
                mt[m] = {'state': 'ldp_or_readback', 'n_tight10': ma['n_tight10'], 'n_cycles': ma['n_cycles'], 'T_tight10': ma['T_tight10']}
        attrib[k2] = {
            'pair': pk, 'net': p2['net'], 'seed': p2['seed'], 'role': p2.get('role'), 'form_total': form,
            'd1_total': r1(a2.get('S7')), 'd1_codex_8100': r1(p2['R2a'].get('codex_8100', {}).get('S7')),
            'd1_zones5_900_end': zone,
            'd_entry': r1(a2['ENTRY']) if 'ENTRY' in a2 else r1(sum(p2['R2e']['group_d_300s']['ENTRY'])) if 'R2e' in p2 else None,
            'd_exit': r1(a2['EXIT']) if 'EXIT' in a2 else r1(sum(p2['R2e']['group_d_300s']['EXIT'])) if 'R2e' in p2 else None,
            'd_u1098': r1(p3['totals'].get('u1098')), 'O701': r1(a2.get('O701')), 'A4': r1(a2.get('A4')),
            'outa': r1(a2.get('outa')), 'outb': r1(a2.get('outb')),
            'meters_tight': mt, 'G_inputs': s6, 'flags': fl}

    # ---------- data-after (S-12): cell 5-9 share from R2_after (report only, not in flags/ref line)
    after = {}
    for k, v in RA['pairs'].items():
        after[k] = v
    # ---------- section 6.2 reference line
    ref = {'fields': ['RF1', 'RF2', 'RF3', 'RF4', 'RF5', 'RF6', 'RF7', 'RF8', 'RF9', 'RF10', 'RF11', 'WITH'], 'seeds': {}}
    for s in SEEDS:
        sd = {}
        pv = R3['pairs']['P-VA v3c3-s%d' % s]
        pb = R3['pairs']['P-B v3c3-s%d' % s]
        r3p = {'P-VA': pv, 'P-B': pb, 'P-VSL': R3['pairs']['P-VSL v3c3-s%d' % s], 'P-J1': R3['pairs']['P-J1 v3c3-s%d (참고)' % s]}
        # shared base check (P-B and P-VA use the same NC3)
        for m in METERS:
            if pb['merge_vph'][m]['base'] != pv['merge_vph'][m]['base']:
                stops.append('merge base differs P-B/P-VA s%d %s' % (s, m))
        for pk in ('P-VA', 'P-B', 'P-VSL', 'P-BVA', 'P-J1'):
            p2 = R2['pairs']['%s|v3c3-s%d' % (pk, s)]
            row = {}
            row['RF1'] = {'ours_9000': r1(p2['R2a']['ours_9000']['S7']), 'codex_8100': r1(p2['R2a']['codex_8100']['S7'])}
            row['RF2'] = {'ours_9000': r1(p2['R2a']['ours_9000']['S19']), 'codex_8100': r1(p2['R2a']['codex_8100']['S19'])}
            row['RF3'] = {z: [r1(x) for x in group900(p2['R2c']['zones5'][z]['d_veh_h'])] for z in ZONES5}
            row['WITH'] = {f: {k: r1(p2['R2a'][f][k]) for k in ('O701', 'A4', 'outa', 'outb')} for f in ('ours_9000', 'codex_8100')}
            row['RF11'] = {'T_gain_a_s': p2['R2f']['T_gain_a_s'], 'T_gain_b_s': p2['R2f']['T_gain_b_s'], 'T_half_s': p2['R2f']['T_half_s'],
                           'cum_d1_900_end': r1(p2['R2f']['final_cum_900_end'])}
            if pk == 'P-BVA':
                A, Bq = pb, pv           # B - V-A = (B - NC3) - (V-A - NC3)
                row['RF5'] = {m: [r1(x, 0) for x in group900(vsub(A['merge_vph'][m]['arm'], Bq['merge_vph'][m]['arm']), 'mean')] for m in METERS}
                row['RF6'] = {}
                for m in METERS:
                    sa, qa = ramp_d300(A['ramp'][m])
                    sb, qb = ramp_d300(Bq['ramp'][m])
                    row['RF6'][m] = {'stock_d': r1(sum(sa) - sum(sb)), 'queue_d': r1(sum(qa) - sum(qb)),
                                     'stock_d_900': [r1(x) for x in group900(vsub(sa, sb))]}
                u = vsub(A['u1098_win'], Bq['u1098_win'])
                row['RF7'] = {'total': r1(sum(u)), 'w900': [r1(x) for x in group900(u)]}
                row['RF8'] = {e: r1(A['exit'][e]['d_total'] - Bq['exit'][e]['d_total']) for e in EXITS}
                row['RF4'] = 'B 팔 값(P-B RF4) 대 V-A 팔 값(P-VA RF4)을 나란히'
                row['RF9'] = {'B1_d': spills['B-s%d' % s]['b1_spill_min_lt4500'] - spills['VA-s%d' % s]['b1_spill_min_lt4500'],
                              'M_d': spills['B-s%d' % s]['m_spill_min_lt6800'] - spills['VA-s%d' % s]['m_spill_min_lt6800']}
                row['RF10'] = 'B 0 결정(110 고정) 대 V-A 결정 수(P-VA RF10)'
                row['RF11']['T_gain_minus_T_tight10_B'] = {m: (None if p2['R2f']['T_gain_a_s'] is None else p2['R2f']['T_gain_a_s'] - 900) for m in METERS}
                row['how'] = '[계산] 같은 시드 P-B − P-VA (기준 NC3 같음; 첫 관측 차분·재고·유량 모두 선형)'
            else:
                p3 = r3p[pk]
                arm = {'P-VA': 'VA', 'P-B': 'B', 'P-VSL': 'VSL', 'P-J1': 'J1'}[pk]
                row['RF5'] = {m: {'d': [r1(x, 0) for x in group900(p3['merge_vph'][m]['d'], 'mean')],
                                  'arm': [r1(x, 0) for x in group900(p3['merge_vph'][m]['arm'], 'mean')]} for m in METERS}
                row['RF6'] = {}
                for m in METERS:
                    st, q = ramp_d300(p3['ramp'][m])
                    row['RF6'][m] = {'stock_d': r1(p3['ramp'][m]['meter_side_total_d']), 'queue_d': r1(p3['ramp'][m]['meter_side_q_total_d']),
                                     'stock_d_900': [r1(x) for x in group900(st)],
                                     'qmax_arm_base': [max(p3['ramp'][m]['ramp_qmax']['arm'][3:]), max(p3['ramp'][m]['ramp_qmax']['base'][3:])]}
                row['RF7'] = {'total': r1(p3['u1098_sum']), 'w900': [r1(x) for x in group900(p3['u1098_win'])]}
                row['RF8'] = {e: r1(p3['exit'][e]['d_total']) for e in EXITS}
                rf4 = {}
                for m in METERS:
                    ma = p3['meter_arm'].get(RM[m]) if isinstance(p3['meter_arm'], dict) else None
                    if not isinstance(ma, dict) or 'n_cycles' not in ma:
                        rf4[m] = {'state': '기록 없음(읽음: 61결정 × 미터 8개 내내 녹색 10)'}
                    elif ma.get('state_none'):
                        rf4[m] = {'state': '상태 기록 없음(LDP 빈칸) — 조임 아님'}
                    else:
                        rf4[m] = {'n_tight10': ma['n_tight10'], 'n_cycles': ma['n_cycles'], 'T_tight10': ma['T_tight10'],
                                  'T_tight6': ma['T_tight6'], 'green_hist': ma['green_hist'],
                                  'mean_green': r1(ma.get('green_seconds_total', 0) / ma['n_cycles'], 2)}
                row['RF4'] = rf4
                row['RF9'] = {'arm_B1': spills['%s-s%d' % (arm, s)]['b1_spill_min_lt4500'], 'arm_M': spills['%s-s%d' % (arm, s)]['m_spill_min_lt6800'],
                              'NC3_B1': spills['NC3-s%d' % s]['b1_spill_min_lt4500'], 'NC3_M': spills['NC3-s%d' % s]['m_spill_min_lt6800'],
                              'arm_B1_tail_min_m': spills['%s-s%d' % (arm, s)]['b1_tail_min_m'], 'arm_B2_tail_min_m': spills['%s-s%d' % (arm, s)]['b2_tail_min_m']}
                vf = R3['arms']['%s-s%d' % (arm, s)].get('vsl_fwe')
                if pk == 'P-VSL':
                    row['RF10'] = {'n_decisions_lt110': 'n/a', 'note': '900 s 부터 91 고정 [읽음 VSL_RESULTS §1.8]'}
                elif isinstance(vf, dict):
                    row['RF10'] = {'n_decisions_lt110': len(vf['decisions_lt110']), 'times_s': vf['decisions_lt110']}
                else:
                    row['RF10'] = {'n_decisions_lt110': None}
                row['RF11']['T_gain_minus_T_tight10'] = p3['timing']
            sd[pk] = row
        # levels (NC3 and arm) for context
        r1a = R1['R1a']['v3c3-s%d' % s]
        lv = {'NC3_d1_level': {'ours_9000': r1(r1a['fwe7_ours_9000']), 'codex_8100': r1(r1a['fwe7_codex_8100'])}}
        for pk, arm in (('P-VA', 'V-A'), ('P-B', 'B'), ('P-VSL', 'VSL')):
            lv['%s_d1_level_ours_9000' % arm] = r1(r1a['fwe7_ours_9000'] + R2['pairs']['%s|v3c3-s%d' % (pk, s)]['R2a']['ours_9000']['S7'])
        lv['NC3_merge_vph_900'] = {m: [r1(x, 0) for x in group900(pv['merge_vph'][m]['base'], 'mean')] for m in METERS}
        lv['NC3_meter_side_stock_900'] = {m: [r1(x) for x in group900(ramp_arm300(pv['ramp'][m], 'base'))] for m in METERS}
        lv['NC3_exit_queue_0_9000'] = R1['arms']['v3c3-s%d' % s]['R1']['R1g']['analyse_offramp_queued_veh_h']
        lv['NC3_meters'] = '기록 없음(v3c3 NC3: 미터 LDP·readback 없음)'
        lv['spill_minutes'] = {a: {'B1': spills['%s-s%d' % (a, s)]['b1_spill_min_lt4500'], 'M': spills['%s-s%d' % (a, s)]['m_spill_min_lt6800']} for a in ARMS_V3}
        sd['levels'] = lv
        ref['seeds']['v3c3-s%d' % s] = sd
    # side column: 64cf joint - NC (not subtracted from v3c3)
    qj2, qj3 = R2['pairs']['Q-joint|64cf-s29'], R3['pairs']['Q-joint 64cf-s29']
    nc_sp = R4['physics_levels']['lnc']['spill']
    jt_sp = R4['physics_levels']['joint']['spill']
    side = {'RF1': {'codex_8100': r1(qj2['R2a']['codex_8100']['S7'])}, 'RF2': {'codex_8100': r1(qj2['R2a']['codex_8100']['S19'])},
            'RF3': {z: [r1(x) for x in group900(qj2['R2c']['zones5'][z]['d_veh_h'])] for z in ZONES5},
            'RF5': {m: [r1(x, 0) for x in group900(qj3['merge_vph'][m]['d'], 'mean')] for m in METERS},
            'RF6': {m: r1(qj3['ramp'][m]['meter_side_total_d']) for m in METERS},
            'RF7': {'total': r1(qj3['u1098_sum']), 'w900': [r1(x) for x in group900(qj3['u1098_win'])]},
            'RF8': {e: r1(qj3['exit'][e]['d_total']) for e in EXITS},
            'RF4': {m: {'n_tight10': qj3['meter_arm'][RM[m]]['n_tight10'], 'n_cycles': qj3['meter_arm'][RM[m]]['n_cycles'],
                        'T_tight10': qj3['meter_arm'][RM[m]]['T_tight10'], 'T_tight6': qj3['meter_arm'][RM[m]]['T_tight6']} for m in METERS},
            'RF9': {'arm_B1': jt_sp['b1_spill_min_lt4500'], 'arm_M': jt_sp['m_spill_min_lt6800'], 'NC_B1': nc_sp['b1_spill_min_lt4500'], 'NC_M': nc_sp['m_spill_min_lt6800'],
                    'window': '0-8100 s (R4)'},
            'RF10': {'n_decisions_lt110': 0, 'note': '[읽음 R3 표 V2] joint FW_E VSL<110 결정 0'},
            'RF11': {'T_gain_a_s': qj2['R2f']['T_gain_a_s'], 'T_gain_b_s': qj2['R2f']['T_gain_b_s'], 'T_half_s': qj2['R2f']['T_half_s'],
                     'cum_d1_900_end': r1(qj2['R2f']['final_cum_900_end']), 'T_gain_minus_T_tight10': qj3['timing']},
            'WITH': {'codex_8100': {k: r1(qj2['R2a']['codex_8100'][k]) for k in ('O701', 'A4', 'outa', 'outb')}},
            'NC_d1_level_codex_8100': r1(R1['R1a']['64cf-s29 codex NC']['fwe7_codex_8100'])}
    ref['side_64cf_joint_minus_NC'] = side
    # derived arithmetic on declared fields (labelled; residual uses data-after cell 5-9 share)
    derived = {'pct_d1_of_NC_level': {}, 'BVA_B1_plus_B2_900_end': {}, 'data_after_residual': {}}
    for s in SEEDS:
        lvl = R1['R1a']['v3c3-s%d' % s]['fwe7_ours_9000']
        for pk in ('P-VA', 'P-B', 'P-VSL', 'P-BVA'):
            d1 = R2['pairs']['%s|v3c3-s%d' % (pk, s)]['R2a']['ours_9000']['S7']
            derived['pct_d1_of_NC_level']['%s|v3c3-s%d' % (pk, s)] = r1(100.0 * d1 / lvl, 2)
        z = R2['pairs']['P-BVA|v3c3-s%d' % s]['R2c']['zones5']
        derived['BVA_B1_plus_B2_900_end']['v3c3-s%d' % s] = r1(sum(z['B1']['d_veh_h']) + sum(z['B2']['d_veh_h']))
    qlvl = R1['R1a']['64cf-s29 codex NC']['fwe7_codex_8100']
    for qk in ('Q-joint', 'Q-window', 'Q-off', 'Q-fw', 'Q-urb'):
        derived['pct_d1_of_NC_level']['%s|64cf-s29' % qk] = r1(100.0 * R2['pairs']['%s|64cf-s29' % qk]['R2a']['codex_8100']['S7'] / qlvl, 2)
    for k, row in RA['pairs'].items():
        if k.endswith('64cf-s29'):
            lv = qlvl
        else:
            lv = R1['R1a'][k.split('|')[1]]['fwe7_ours_9000']
        derived['data_after_residual'][k] = {'cells5_9_900_end': r1(row['cells5_9_900_end']), 'd1_rest': r1(row['d1_rest']),
                                             'rest_pct_of_NC_level': r1(100.0 * row['d1_rest'] / lv, 2)}
    derived['label'] = '[계산] 고정 칸의 산술. data_after_residual 은 데이터 뒤(셀 5–9 몫을 뺀 것, S-12)'
    ref['derived'] = derived
    # consistency checks against values printed in R3 tables (C1 / R2 / E1)
    chk = ref['seeds']['v3c3-s31']['P-B']
    checks['R3_tableC1_PB_s31_10639_1800'] = chk['RF5']['10639']['d'][2] == -144
    checks['R3_tableR2_PB_s31_2700'] = abs(sum(chk['RF6'][m]['stock_d_900'][3] for m in METERS) - 17.1) < 0.11
    checks['R3_tableE1_PB_s43_total'] = ref['seeds']['v3c3-s43']['P-B']['RF7']['total'] == -113.5
    checks['R2_PBVA_d1_s41'] = ref['seeds']['v3c3-s41']['P-BVA']['RF1']['ours_9000'] == -105.5
    for k, v in checks.items():
        if v is not True:
            stops.append('check failed: ' + k)
    meta = {'tool': os.path.abspath(__file__).replace('\\', '/'), 'tool_sha256': sha256(os.path.abspath(__file__)),
            'pre_fwe_sha256': PINS[FD + '/PRE_FWE.md'], 'inputs_sha256': dict(PINS),
            'made_kst': time.strftime('%Y-%m-%d %H:%M:%S'), 'thresholds': TH, 'checks': checks, 'stops': stops,
            'seconds': round(time.time() - t0, 1)}
    return meta, attrib, after, spills, ref


# ---------------------------------------------------------------- markdown (numbers only from ref/attrib)
def fs(x, nd=1):
    if x is None:
        return '—'
    if isinstance(x, str):
        return x
    v = round(x, nd)
    if v == 0:
        return '0' if nd == 0 else '0.' + '0' * nd
    s = ('%.' + str(nd) + 'f') % abs(v)
    if nd == 0:
        s = '{:,}'.format(int(round(abs(v))))
    return ('+' if v > 0 else '−') + s


W900 = ['0–900', '900–1800', '1800–2700', '2700–3600', '3600–4500', '4500–5400', '5400–6300', '6300–7200', '7200–8100', '8100–9000']


def md(meta, attrib, ref, spills):
    L = ['<!-- generated by tools/fwe_synth.py (sha256 %s) -->' % meta['tool_sha256'], '']
    L.append('# FWE_REF_C1 — C1 FW_E 기준 줄 (PRE_FWE §6.2, 보고 전용 칸, 판정 문턱 없음)')
    L.append('')
    L.append('- 값은 모두 `out/FWE_REF_C1.json` 에서 옮겼습니다. 단위 veh·h(유량은 veh/h, 번짐은 분). 시드마다 따로, 평균 없음. 64cf 는 옆 열로만(빼지 않음).')
    L.append('- 짝: P-VA = V-A − NC3, P-B = B − NC3, P-VSL = VSL − NC3, P-BVA = B − V-A, P-J1 = J1 − NC3(참고). 0–900 s 는 제어 전.')
    L.append('')
    pairs = ('P-VA', 'P-B', 'P-BVA', 'P-VSL', 'P-J1')
    S = ['v3c3-s%d' % s for s in SEEDS]
    # RF1/RF2/WITH
    L.append('## RF1·RF2·함께 — 총합 (우리 꼴 [0, 9000] / codex 꼴 [0, 8100])')
    L.append('')
    L.append('| 짝 | 시드 | RF1 d① 우리 | RF1 d① codex | RF2 d② 우리 | RF2 d② codex | Ω701 우리 | ④ 우리 | Ω 밖 (a) 우리 | Ω 밖 (b) 우리 | Ω701 codex | ④ codex | Ω 밖 (a) codex | Ω 밖 (b) codex |')
    L.append('|---|---|' + '---:|' * 12)
    for pk in pairs:
        for sname in S:
            r = ref['seeds'][sname][pk]
            w0, w1 = r['WITH']['ours_9000'], r['WITH']['codex_8100']
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                pk, sname, fs(r['RF1']['ours_9000']), fs(r['RF1']['codex_8100']), fs(r['RF2']['ours_9000']), fs(r['RF2']['codex_8100']),
                fs(w0['O701']), fs(w0['A4']), fs(w0['outa']), fs(w0['outb']), fs(w1['O701']), fs(w1['A4']), fs(w1['outa']), fs(w1['outb'])))
    sd = ref['side_64cf_joint_minus_NC']
    L.append('| 옆 열: codex joint − NC | 64cf-s29 | — | %s | — | %s | — | — | — | — | %s | %s | %s | %s |' % (
        fs(sd['RF1']['codex_8100']), fs(sd['RF2']['codex_8100']), fs(sd['WITH']['codex_8100']['O701']), fs(sd['WITH']['codex_8100']['A4']),
        fs(sd['WITH']['codex_8100']['outa']), fs(sd['WITH']['codex_8100']['outb'])))
    L.append('')
    L.append('- 수준: NC3 ① 우리 꼴 ' + ' / '.join(fs(ref['seeds'][x]['levels']['NC3_d1_level']['ours_9000']).lstrip('+') for x in S) +
             ', V-A ' + ' / '.join(fs(ref['seeds'][x]['levels']['V-A_d1_level_ours_9000']).lstrip('+') for x in S) +
             ', B ' + ' / '.join(fs(ref['seeds'][x]['levels']['B_d1_level_ours_9000']).lstrip('+') for x in S) +
             ' veh·h [계산 = NC3 수준 + d]. 64cf NC ① codex 꼴 ' + fs(sd['NC_d1_level_codex_8100']).lstrip('+') + '.')
    L.append('')
    # RF3
    L.append('## RF3 — d① 다섯 구역 × 900 s (bin 꼴)')
    L.append('')
    L.append('| 짝 | 시드 | 구역 | ' + ' | '.join(W900) + ' |')
    L.append('|---|---|---|' + '---:|' * 10)
    for pk in pairs[:4]:
        for sname in S:
            for z in ZONES5:
                L.append('| %s | %s | %s | %s |' % (pk, sname, z, ' | '.join(fs(x) for x in ref['seeds'][sname][pk]['RF3'][z])))
    for z in ZONES5:
        L.append('| 옆 열 joint − NC | 64cf-s29 | %s | %s | — |' % (z, ' | '.join(fs(x) for x in sd['RF3'][z])))
    L.append('')
    # RF4
    L.append('## RF4 — FW_E 미터 GREEN (GREEN 초만; "GREEN<10 주기/전체 · T_tight10 · T_tight6 · 평균 GREEN 초")')
    L.append('')
    L.append('| 팔 | 시드 | RM_C10639 | RM_C10681 | RM_C10490 | RM_C10484 |')
    L.append('|---|---|---|---|---|---|')
    for pk, nm in (('P-VA', 'V-A'), ('P-B', 'B'), ('P-VSL', 'VSL'), ('P-J1', 'J1(참고)')):
        for sname in S:
            cells = []
            for m in METERS:
                v = ref['seeds'][sname][pk]['RF4'][m]
                if 'state' in v:
                    cells.append(v['state'])
                else:
                    cells.append('%d/%d · %s · %s · %.2f' % (v['n_tight10'], v['n_cycles'], v['T_tight10'] or '—', v['T_tight6'] or '—', v['mean_green']))
            L.append('| %s | %s | %s |' % (nm, sname, ' | '.join(cells)))
    L.append('| NC3 | 세 시드 | ' + ' | '.join([ref['seeds'][S[0]]['levels']['NC3_meters']] * 4) + ' |')
    L.append('| 옆 열 codex joint | 64cf-s29 | ' + ' | '.join('%d/%d · %s · %s' % (sd['RF4'][m]['n_tight10'], sd['RF4'][m]['n_cycles'], sd['RF4'][m]['T_tight10'], sd['RF4'][m]['T_tight6']) for m in METERS) + ' |')
    L.append('')
    L.append('- GREEN 초 분포(B, 주기 수): ' + '; '.join('%s %s %s' % (sname, m, ' '.join('%s:%d' % (g, c) for g, c in ref['seeds'][sname]['P-B']['RF4'][m]['green_hist'].items() if c))
                                                        for sname in S for m in METERS) + '.')
    L.append('')
    # RF5
    L.append('## RF5 — 합류 유량 차 × 900 s (veh/h, 300 s 창 셋의 평균; 괄호 = 팔 수준)')
    L.append('')
    L.append('| 짝 | 시드 | 합류 | ' + ' | '.join(W900[1:]) + ' |')
    L.append('|---|---|---|' + '---:|' * 9)
    for pk in ('P-VA', 'P-B', 'P-BVA', 'P-VSL'):
        for sname in S:
            for m in METERS:
                v = ref['seeds'][sname][pk]['RF5'][m]
                if pk == 'P-BVA':
                    cells = [fs(x, 0) for x in v[1:]]
                else:
                    cells = ['%s (%s)' % (fs(d, 0), fs(a, 0).lstrip('+')) for d, a in zip(v['d'][1:], v['arm'][1:])]
                L.append('| %s | %s | %s | %s |' % (pk, sname, m, ' | '.join(cells)))
    for sname in S:
        for m in METERS:
            L.append('| NC3 수준 | %s | %s | %s |' % (sname, m, ' | '.join(fs(x, 0).lstrip('+') for x in ref['seeds'][sname]['levels']['NC3_merge_vph_900'][m][1:])))
    for m in METERS:
        L.append('| 옆 열 joint − NC | 64cf-s29 | %s | %s | — |' % (m, ' | '.join(fs(x, 0) for x in sd['RF5'][m][1:])))
    L.append('')
    # RF6
    L.append('## RF6 — 미터 쪽 재고(연결로 커넥터 + 접근 링크) 차 (veh·h, 0–끝 합 · 대기 = 속도<15 · 창 최대 대기 대수 팔/NC3)')
    L.append('')
    L.append('| 짝 | 시드 | 10639 (←70) | 10681 (←68) | 10490 (←129) | 10484 (←31) | 넷 합 |')
    L.append('|---|---|---|---|---|---|---:|')
    for pk in ('P-VA', 'P-B', 'P-BVA', 'P-VSL'):
        for sname in S:
            v = ref['seeds'][sname][pk]['RF6']
            cells = []
            for m in METERS:
                c = '%s / %s' % (fs(v[m]['stock_d']), fs(v[m]['queue_d']))
                if 'qmax_arm_base' in v[m]:
                    c += ' / %d:%d' % tuple(v[m]['qmax_arm_base'])
                cells.append(c)
            L.append('| %s | %s | %s | %s |' % (pk, sname, ' | '.join(cells), fs(sum(v[m]['stock_d'] for m in METERS))))
    L.append('| 옆 열 joint − NC | 64cf-s29 | ' + ' | '.join(fs(sd['RF6'][m]) for m in METERS) + ' | %s |' % fs(sum(sd['RF6'][m] for m in METERS)))
    L.append('')
    # RF7
    L.append('## RF7 — 입구 대기 ④b 1098 (첫 관측 차분, veh·h, 합 · 900 s 칸)')
    L.append('')
    L.append('| 짝 | 시드 | 합 | ' + ' | '.join(W900) + ' |')
    L.append('|---|---|---:|' + '---:|' * 10)
    for pk in ('P-VA', 'P-B', 'P-BVA', 'P-VSL'):
        for sname in S:
            v = ref['seeds'][sname][pk]['RF7']
            L.append('| %s | %s | %s | %s |' % (pk, sname, fs(v['total']), ' | '.join(fs(x) for x in v['w900'])))
    L.append('| 옆 열 joint − NC | 64cf-s29 | %s | %s | — |' % (fs(sd['RF7']['total']), ' | '.join(fs(x) for x in sd['RF7']['w900'])))
    L.append('')
    # RF8
    L.append('## RF8 — 진출 커넥터 재고 차 (veh·h, 0–끝 합)')
    L.append('')
    L.append('| 짝 | 시드 | 10643 (신호 배수) | 10682 | 10481 (신호 배수) | 10483 |')
    L.append('|---|---|---:|---:|---:|---:|')
    for pk in ('P-VA', 'P-B', 'P-BVA', 'P-VSL'):
        for sname in S:
            v = ref['seeds'][sname][pk]['RF8']
            L.append('| %s | %s | %s |' % (pk, sname, ' | '.join(fs(v[e]) for e in EXITS)))
    L.append('| 옆 열 joint − NC | 64cf-s29 | ' + ' | '.join(fs(sd['RF8'][e]) for e in EXITS) + ' |')
    L.append('- NC3 진출 대기 수준(0–9000, veh·h): ' + '; '.join('%s %s' % (sname, ' · '.join('%s %.1f' % (e, ref['seeds'][sname]['levels']['NC3_exit_queue_0_9000'][e]) for e in EXITS)) for sname in S) + '.')
    L.append('')
    # RF9
    L.append('## RF9 — B1·M 번짐 분 (tails.py; B1 꼬리 < 4,500 m, B2 꼬리 < 6,800 m; 0–9,060 s)')
    L.append('')
    L.append('| 시드 | NC3 B1 / M | V-A B1 / M | B B1 / M | VSL B1 / M | J1(참고) B1 / M |')
    L.append('|---|---|---|---|---|---|')
    for sname in S:
        lv = ref['seeds'][sname]['levels']['spill_minutes']
        L.append('| %s | %s |' % (sname, ' | '.join('%d / %d' % (lv[a]['B1'], lv[a]['M']) for a in ARMS_V3)))
    L.append('| 64cf-s29 (옆, 0–8,100 s) | NC %d / %d | — | — | — | codex joint %d / %d |' % (sd['RF9']['NC_B1'], sd['RF9']['NC_M'], sd['RF9']['arm_B1'], sd['RF9']['arm_M']))
    L.append('')
    # RF10
    L.append('## RF10 — FW_E VSL < 110 결정 (run action CSV)')
    L.append('')
    L.append('| 팔 | 시드 | 결정 수 | 시각 (s) |')
    L.append('|---|---|---:|---|')
    for pk, nm in (('P-VA', 'V-A'), ('P-B', 'B'), ('P-J1', 'J1(참고)')):
        for sname in S:
            v = ref['seeds'][sname][pk]['RF10']
            L.append('| %s | %s | %s | %s |' % (nm, sname, v['n_decisions_lt110'], ', '.join(str(t) for t in v.get('times_s', [])) or '—'))
    L.append('| VSL | 세 시드 | — | 900 s 부터 91 고정 [읽음] |')
    L.append('| 옆 열 codex joint | 64cf-s29 | 0 | — |')
    L.append('')
    # RF11
    L.append('## RF11 — 때 (300 s 창 시작 s; 누적은 900 s 부터)')
    L.append('')
    L.append('| 짝 | 시드 | 누적 d① | T_gain_a | T_gain_b | T_half | T_gain_a − T_tight10 (미터 넷) |')
    L.append('|---|---|---:|---:|---:|---:|---|')
    for pk in pairs[:4]:
        for sname in S:
            v = ref['seeds'][sname][pk]['RF11']
            if pk == 'P-BVA':
                x = v['T_gain_minus_T_tight10_B']['10639']
                tm = 'a−: %s (B 미터 넷 T_tight10 = 900, V-A 조임 없음)' % (x if x is not None else '—')
            else:
                tt = v['T_gain_minus_T_tight10']
                vals = set(json.dumps(tt[RM[m]], ensure_ascii=False) for m in METERS)
                tm = (tt[RM['10639']] if isinstance(tt[RM['10639']], str) else 'a−: %s · b−: %s' % (tt[RM['10639']]['a_minus'], tt[RM['10639']]['b_minus'])) if len(vals) == 1 else json.dumps(tt, ensure_ascii=False)
            L.append('| %s | %s | %s | %s | %s | %s | %s |' % (pk, sname, fs(v['cum_d1_900_end']), v['T_gain_a_s'] or '없음', v['T_gain_b_s'] or '없음', v['T_half_s'] or '없음', tm))
    jt = sd['RF11']['T_gain_minus_T_tight10']
    L.append('| 옆 열 joint − NC | 64cf-s29 | %s | %s | %s | %s | %s |' % (
        fs(sd['RF11']['cum_d1_900_end']), sd['RF11']['T_gain_a_s'], sd['RF11']['T_gain_b_s'], sd['RF11']['T_half_s'],
        ' · '.join('%s a−: %s · b−: %s' % (m, jt[RM[m]]['a_minus'], jt[RM[m]]['b_minus']) for m in METERS)))
    L.append('')
    return '\n'.join(L) + '\n'


def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'run':
        print(__doc__)
        return
    meta, attrib, after, spills, ref = build()
    out = FD + '/out'
    with open(out + '/FWE_ATTRIB.json', 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'attrib': attrib, 'spills_v3c3': spills,
                   'data_after_cell5_9': {'label': '데이터 뒤 (S-12): 깃발·기준 줄에 쓰지 않음', 'source': 'out/R2_after.json', 'pairs': after}},
                  f, ensure_ascii=False, indent=1)
    with open(out + '/FWE_REF_C1.json', 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'ref': ref}, f, ensure_ascii=False, indent=1)
    with open(out + '/FWE_REF_C1.md', 'w', encoding='utf-8') as f:
        f.write(md(meta, attrib, ref, spills))
    print(json.dumps({'checks': meta['checks'], 'stops': meta['stops'], 'seconds': meta['seconds']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
