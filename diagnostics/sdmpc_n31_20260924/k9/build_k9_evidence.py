"""K9-1 evidence builder: the single source of the K9-1 values (K8_PREDECLARATION_AMENDMENT_19 r2 sections 2.1 / 2.2
/ 2.3, sha 4ccfd8fd...; user decisions K9_1_USER_DECISIONS_20261010 D-K9-1..3).  Diagnostics only; the runtime reads the
committed JSON (sha-pinned by the tuning key), never this script.

    python -B diagnostics/sdmpc_n31_20260924/k9/build_k9_evidence.py w1|w2a|f17b [--check]

w1   sc1001wout_saturation_v3c3_<date>.json (W1, section 2.1): the SC1001 -> W_RAMP signal movements E / N / S take
     C_m = s_g(m) x sum_{l in L(m)} b_m / sum_{m' in M(l)} b_m' (b = the decision's template beta at the hook).
     s_g = U4 F2 s_from_green_start_incl_startup_veh_h_lane of the head groups 29|p3 / 37|p1 / 40|p2 measured by the
     K8b-1 byte copies of the U4 measurers (k8b/u4/, sha 369c2fdb / 73565c5c) on the v3c3 NC fit seeds 31/41/43/47/53
     (D:/VISSIM_runs/20261001_v3c3/s<seed>_v3c3nc: FZP, .inpx, the SC1001 .sig the .inpx names; read only), unchanged
     constants (MIN_BINS 24, MIN_CYCLES 8, MIN_SEEDS 3, T_SU 5 s); the three groups from
     inputs/sc1001wout_head_groups_v3b_20260929.json (rows of the v3b contract, byte-equal JSON values), each head
     asserted equal (link, lane, SG, position +-1e-3 m) in the v3c3 network (else STOP).  Value rule: all measured ->
     each F2; some default -> default value = 1850 x mean_{g measured}(F2_g / s_unimpeded_g) of this measurement
     (unweighted, not rounded); all default -> the v3b U4 table values 1719.6 / 1514.9 / 1732.4.  Any value outside
     [1200, 2200] veh/h/lane -> STOP.  L(m) / M(l) (section 2.1 r2): from the s31 v3c3 NC .inpx connectors leaving
     links 29 / 37 / 40 and the contract's connector -> movement rows (members[].connector, non_members_with_flow);
     a connector departing a lane of U L(m) that maps to no or to several model movements -> STOP; a W1 movement
     departing a lane outside its group's head lanes -> STOP.
w2a  wout_side_handoff_v3c3_<date>.json (W2-A, section 2.2): side class (10703 lands on 31) destination split from
     the v3c3 NC fit seeds 31/41/43/47/53 with the K8b P-4 extract rule (k8b_decl/p4b_extract.py 85156269 = this
     builder's w2a_extract) and the episode rule k8b/wout_episodes.py (a0e92f7d); kept entry times [900, 9000),
     anomalies excluded; s_side[d] = n(side, d) / N_side, d in {R_D_E, R_D_W, free'} (free' = free + side_exit),
     unknown_dest excluded.  The counts must be 2,022 / 14 / 2,025 / side_exit 0 / unknown_dest 13 (else STOP).
     x_side = the 10703 landing position on 31 (toLinkEndPt pos, s31 v3c3 NC .inpx, rounded to 1 mm; must be
     350.718 +- 0.001 m else STOP); l_side_d = l_d(PAR boundary_out_ramp_position_m) - x_side, rounded to 1e-6 km
     (free = the R_D_W station, the P-4 rule).  Path 78 -> 10703 -> 31, lanes = the 10703 lane count.
f17b offramp_split_forecast_v3c3_<date>.json (F17b, section 2.3): the FW_W exit share forecast candidate
     selected by the P0-3 seed-crossing rule, recomputed here from the s41 / s53 v3c3 NC fit FZP (VISSIM side
     only) by k9/f17b_select.py (the rule of the K9-1 probe tool p0_3_f17b_select.py, moved unchanged); its
     result fields must equal the recorded P0-3 output inputs/f17b_selection_<date>.json (sha cb430b39...; else
     STOP); values = its runtime values (the candidate id, exits, windows; for C3 the pooled s41 + s53 prior).
--check re-derives and compares the committed file's `values` field bit for bit (canonical JSON); any difference
prints K9_EVIDENCE_STOP and exits 1 (section 2.0-3).
Committed evidence = the P0 file bytes of the K9-1 mini probe (K91_VALUES.json, sha 713d232e...; amendment 19 r2
section 4.2 B, r2 B-r1-10: the committed `values` must equal the P0 `values` bit for bit).  A rebuild may differ
from the committed file only in its meta: derivation.* paths, file sizes / row counts / cache paths of the
inputs, the date in the file name and any commit hash; never in `values` (--check compares `values` only).
"""
import ctypes
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
N31 = 'diagnostics/sdmpc_n31_20260924'
NC_ROOT = 'D:/VISSIM_runs/20261001_v3c3'
DATE = '20261009'
DECLARATION = {'amendment19_sha256': '4ccfd8fd1efb6f79c59161ab40d4aa9234fa729bc980c89c1c9ad3059cd420d8',
               'decisions_file': 'K9_1_USER_DECISIONS_20261010.md (D-K9-1..3), sha 32c73a47...'}
U4_SHA256 = {'derive_head_saturation.py': '369c2fdbf9939a2cc60a96ffaa656934d02258246f667d3c692ca21fae2ffabd',
             'urban_b2_evidence.py': '73565c5c259389112164290fac271fa55f2c796a38d1d32303a94c2feadef0f5'}
U4_DIR = ROOT / N31 / 'k8b' / 'u4'
INPX31 = '%s/s31_v3c3nc/prepared/network/baseline_s31_v3c3nc.inpx' % NC_ROOT
INPX31_SHA256 = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def below_normal():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:
        pass


def canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def u4_modules():
    for name, want in U4_SHA256.items():
        if sha(U4_DIR / name) != want:
            raise SystemExit(f'k8b/u4/{name} is not the pinned U4 measurer copy')
    sys.path.insert(0, str(U4_DIR))
    import urban_b2_evidence as E
    E.NC_ROOT = NC_ROOT
    E.nc_fzp = lambda seed: '%s/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (E.NC_ROOT, seed, seed)
    E.nc_inpx = lambda seed: '%s/s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (E.NC_ROOT, seed, seed)
    import derive_head_saturation as D
    return E, D


# ------------------------------------------------------------------------------------------------ W1
W1_OUT = HERE / f'sc1001wout_saturation_v3c3_{DATE}.json'
W1_GROUPS = HERE / 'inputs' / 'sc1001wout_head_groups_v3b_20260929.json'
W1_CONTRACT_SHA256 = '164016f99a51160ec0f53054fa1dfd4a5362906a658b28a104308425c17831dc'
W1_KEYS = ('29|p3', '37|p1', '40|p2')
W1_MEMBERS = {'E': 'SC1001_E_SC1002_to_W_RAMP', 'N': 'SC1001_N_SC2002_to_W_RAMP', 'S': 'SC1001_S_SC1003_to_W_RAMP'}
W1_GROUP_OF = {'E': '29|p3', 'N': '37|p1', 'S': '40|p2'}
W1_V3B = {'29|p3': 1719.6, '37|p1': 1514.9, '40|p2': 1732.4}     # v3b U4 table (sha 22384c00...) F2, all-default rule
W1_V3B_TABLE_SHA256 = '22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b'
W1_RANGE = (1200.0, 2200.0)
W1_STOPLINES = ('29', '37', '40')


def w1_values(rows):
    """Section 2.1 value rule on the three measured group rows (rows[k]['status'], rows[k]['measured'])."""
    st = {k: rows[k]['status'] for k in W1_KEYS}
    f2 = {k: rows[k]['measured']['s_from_green_start_incl_startup_veh_h_lane'] for k in W1_KEYS}
    meas = [k for k in W1_KEYS if st[k] == 'measured']
    if len(meas) == len(W1_KEYS):
        s = {k: f2[k] for k in W1_KEYS}
        rule = 'v3c3 F2 measured (all three groups)'
    elif meas:
        ratios = [rows[k]['measured']['s_from_green_start_incl_startup_veh_h_lane']
                  / rows[k]['measured']['s_unimpeded_veh_h_lane'] for k in meas]
        fill = 1850.0 * (sum(ratios) / len(ratios))
        s = {k: (f2[k] if st[k] == 'measured' else fill) for k in W1_KEYS}
        rule = ('default group(s) %s: 1850 x unweighted mean F2/s_unimpeded of the measured group(s) %s'
                % ([k for k in W1_KEYS if st[k] != 'measured'], meas))
    else:
        s = dict(W1_V3B)
        rule = 'v3b U4 table F2 (all three default)'
    return s, st, rule


def w1_lane_map(E, contract):
    """L(m), M(l) by the section 2.1 r2 rule (= <Q>/tools/p0_1_w1_map.py): returns (lanes, lane_members, report)."""
    net = E.Network(INPX31)
    c2m = {}
    for g in contract['groups']:
        for mem in g.get('members') or []:
            if mem.get('connector'):
                c2m.setdefault(str(mem['connector']), set()).add(mem['movement'])
    for row in contract.get('non_members_with_flow') or []:
        for cn in row.get('connectors') or []:
            c2m.setdefault(str(cn), set()).add(row['movement'])
    conns = {no: c for no, c in net.conn.items() if c['from'] in W1_STOPLINES}
    lanes = {}
    for key, mv in W1_MEMBERS.items():
        cs = sorted(no for no in conns if mv in c2m.get(no, ()))
        if len(cs) != 1:
            raise SystemExit(f'K9_EVIDENCE_STOP w1: {mv} has connectors {cs}')
        c = conns[cs[0]]
        lanes[key] = {'movement': mv, 'connector': cs[0], 'link': c['from'],
                      'lanes': list(range(c['from_lane'], c['from_lane'] + c['lanes']))}
    union = {(r['link'], l) for r in lanes.values() for l in r['lanes']}
    lane_members, listed = {}, []
    for no, c in sorted(conns.items(), key=lambda kv: int(kv[0])):
        dep = list(range(c['from_lane'], c['from_lane'] + c['lanes']))
        if not any((c['from'], l) in union for l in dep):
            listed.append([no, c['from'], dep, c['to'], sorted(c2m.get(no, ()))])
            continue
        mv = sorted(c2m.get(no, ()))
        if len(mv) != 1:
            raise SystemExit(f'K9_EVIDENCE_STOP w1: connector {no} maps to {mv}')
        for l in dep:
            if (c['from'], l) in union:
                lane_members.setdefault(f'{c["from"]}|{l}', set()).add(mv[0])
    lane_members = {k: sorted(v) for k, v in sorted(lane_members.items())}
    groups = {g['group_id']: g for g in contract['groups']}
    for key, r in lanes.items():
        hl = sorted(int(h['lane']) for h in groups[W1_GROUP_OF[key]]['heads'])
        if set(r['lanes']) - set(hl):
            raise SystemExit(f'K9_EVIDENCE_STOP w1: {r["movement"]} departs lanes outside {W1_GROUP_OF[key]} heads {hl}')
    return lanes, lane_members, {'connectors_listed_only': listed}


def derive_w1():
    E, D = u4_modules()
    sub = json.loads(W1_GROUPS.read_text(encoding='utf-8'))
    if sub['source']['sha256'] != W1_CONTRACT_SHA256:
        raise SystemExit('inputs/sc1001wout_head_groups_v3b_20260929.json: another contract')
    contract_path = Path(sub['source']['path'])
    contract = json.loads(contract_path.read_text(encoding='utf-8')) if contract_path.is_file() else None
    if contract is None or sha(contract_path) != W1_CONTRACT_SHA256:
        raise SystemExit('v3b contract not readable at its pinned path / sha differs')
    byid = {g['group_id']: g for g in contract['groups']}
    for g in sub['groups']:
        if canon(g) != canon(byid[g['group_id']]):
            raise SystemExit('inputs row %s differs from the contract row' % g['group_id'])
    if sha(INPX31) != INPX31_SHA256:
        raise SystemExit('v3c3 s31 .inpx sha differs')
    lanes, lane_members, lane_report = w1_lane_map(E, contract)
    t0 = time.time()
    net = E.Network(E.nc_inpx(31))
    groups = []
    for row in sub['groups']:
        if row['group_id'] not in W1_KEYS:
            continue
        heads = []
        for h in row['heads']:
            x = net.heads[h['head_id']]
            if (x['link'], x['lane'], x['sg']) != (row['stopline_link'], h['lane'], h['sg']) \
                    or 'SC' + x['sc'] != row['signal'] or abs(x['position_m'] - h['position_m']) > 1e-3:
                raise SystemExit('K9_EVIDENCE_STOP w1: %s head %s differs in the v3c3 network'
                                 % (row['group_id'], h['head_id']))
            heads.append(dict(x))
        groups.append({'group_id': row['group_id'], 'signal': row['signal'], 'phase': row['phase'],
                       'native_signal': row['native_signal'], 'observation_group': row['observation_group'],
                       'stopline_link': row['stopline_link'], 'heads': heads})
    if [g['group_id'] for g in groups] != list(W1_KEYS):
        raise SystemExit('head groups %s not found' % (W1_KEYS,))
    heads = [h for g in groups for h in g['heads']]
    trees, down, links, keep = D.build_trees(net, groups)
    scs = sorted({h['sc'] for h in heads}, key=int)
    windows, sig_meta = E.sig_windows(net, scs)
    sig_equal = {}
    for sc_ in scs:
        for seed in E.NC_SEEDS:
            ran = Path(E.nc_inpx(seed)).parent / sig_meta[sc_]['sig']
            sig_equal['SC%s_s%d' % (sc_, seed)] = E.sha256_file(ran) == sig_meta[sc_]['sig_sha256']
    import xml.etree.ElementTree as ET
    names = {}
    for sc_ in scs:
        node = net.controllers[sc_]
        r = ET.parse(str(net.path.parent / node.get('supplyFile2').replace('#data#', ''))).getroot()
        for sg in r.findall('./sgs/sg'):
            names['%s-%s' % (sc_, sg.get('id'))] = sg.get('name')
    runs, pins, signatures = {}, [], {}
    sig31 = net.signature()
    for seed in E.NC_SEEDS:
        signatures['s%d' % seed] = E.Network(E.nc_inpx(seed)).signature() == sig31
        arr, meta = E.stream_fzp(E.nc_fzp(seed), keep)
        out_heads, _st, _agree = D.analyze_run(arr, meta['itt_names'], heads, trees, down, links, windows, None)
        runs[seed] = out_heads
        pins.append({k: meta[k] for k in ('path', 'sha256', 'bytes', 'rows_total', 'rows_kept')} | {'seed': seed})
        print('w1 seed', seed, 'rows_kept', meta['rows_kept'], round(time.time() - t0, 1), flush=True)
        del arr
    rows = [D.group_row(g, runs, {}, names) for g in groups]
    by_key = {r['key']: r for r in rows}
    s, status, rule = w1_values(by_key)
    bad = {k: v for k, v in s.items() if not (W1_RANGE[0] <= v <= W1_RANGE[1])}
    values = {'members': dict(W1_MEMBERS), 'group_of': dict(W1_GROUP_OF),
              's_veh_h_lane': s, 'status': status, 'rule': rule,
              'lanes': {k: {'link': r['link'], 'lanes': r['lanes'], 'connector': r['connector']}
                        for k, r in lanes.items()},
              'lane_members': lane_members,
              'formula': 'C_m = s_g(m) x sum_{l in L(m)} b_m / sum_{m in M(l)} b_m (b = template beta at the hook, '
                         'runtime_setup.install_sc1001wout_saturation right after install_sc1002w_saturation)'}
    doc = {'schema': 'k9-sc1001wout-saturation/v1', 'values': values,
           'derivation': {'builder': N31 + '/k9/build_k9_evidence.py w1', 'measurer': dict(U4_SHA256),
                          'head_groups': {'path': N31 + '/k9/inputs/sc1001wout_head_groups_v3b_20260929.json',
                                          'sha256': sha(W1_GROUPS), 'source': sub['source']},
                          'network_s31': {'path': E.nc_inpx(31), 'sha256': E.sha256_file(E.nc_inpx(31))},
                          'network_signature_equal_s31': signatures, 'sig': sig_meta,
                          'sig_equal_in_nc_runs': sig_equal, 'nc_fzp': pins,
                          'parameters': {'T_SU': D.T_SU, 'MIN_BINS': D.MIN_BINS, 'MIN_CYCLES': D.MIN_CYCLES,
                                         'MIN_SEEDS': D.MIN_SEEDS, 'DEFAULT_VEH_H_LANE': D.DEFAULT_VEH_H_LANE,
                                         'window_s': [D.T_FROM, D.T_END]},
                          'groups': {r['key']: {'status': r['status'], 'flags': r.get('flags'),
                                                'measured': r['measured']} for r in rows},
                          'lane_map': lane_report, 'range_veh_h_lane': list(W1_RANGE),
                          'out_of_range': bad, 'v3b_table_sha256': W1_V3B_TABLE_SHA256},
           'declaration': dict(DECLARATION, section='2.1')}
    if bad:
        print('K9_EVIDENCE_STOP w1 values outside', W1_RANGE, bad)
        doc['stop'] = True
    return doc


# ------------------------------------------------------------------------------------------------ W2-A
W2A_OUT = HERE / f'wout_side_handoff_v3c3_{DATE}.json'
W2A_SEEDS = (31, 41, 43, 47, 53)
W2A_FZP_COLS = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'POSLAT', 'SPEED', 'TMINNETTOT', 'DELAYTM', 'DESSPEED',
                'LENGTH', 'ROUTDECNO', 'ROUTENO', 'ROUTDECTYPE', 'NEXTLINK', 'DESTLANE', 'LNCHG', 'INTERACTSTATE',
                'INTERACTTARGTYPE', 'INTERACTTARGNO', 'FX', 'FY', 'RX', 'RY', 'ACCEL']
W2A_USE = ['SIMSEC', 'NO', 'LINK', 'LANE', 'POS', 'SPEED', 'NEXTLINK']
W2A_KEEP_ALL = {31, 124, 119, 10483, 10774, 10119, 10121, 10698, 10703, 10704, 10484, 10480, 10775, 10702, 10491}
W2A_PARTIAL = {29: (300.0, 1e9), 37: (250.0, 1e9), 40: (1000.0, 1e9), 78: (250.0, 1e9), 79: (-1.0, 150.0),
               24: (-1.0, 400.0), 26: (3600.0, 4200.0), 125: (-1.0, 150.0)}
W2A_RAMP_OF = {'R_D_E': 'RM_C10484', 'R_D_W': 'RM_C10480'}
W2A_COUNTS = {'side|R_D_E': 2022, 'side|R_D_W': 14, 'side|free': 2025, 'side|side_exit': 0, 'side|unknown_dest': 13}
W2A_X_SIDE = 350.718
CORRIDOR_EVIDENCE = N31 + '/scenario/sc2001_corridor_nc13_2d0c62.json'
CORRIDOR_SHA256 = '4b6f0875b83e4a891ef65d3744945a155a524dbf8f0a9482cc795b6fe15c1562'
P4_EVIDENCE = N31 + '/k8b/wout_exit_v3c3_20261007.json'
P4_SHA256 = '314b5c8e5c7e637e0decd7d74a5745ef1d036f002c3e0d2852b27ca460ee3dfa'
EPISODES_SHA256 = 'a0e92f7dbe24fa9f68f38357702d26752748d4bdd349d2ecf4b5bbe9b17bcad1'


def w2a_extract(seed, cache_dir=None):
    """The K8b P-4 extract rule (k8b_decl/p4b_extract.py sha 85156269 = build_k8b_evidence.p4_extract)."""
    import numpy as np
    import pandas as pd
    fzp = Path(NC_ROOT) / f's{seed}_v3c3nc' / 'run' / 'vissim_eval' / f'baseline_s{seed}_v3c3nc_001.fzp'
    parts, nrows = [], 0
    it = pd.read_csv(fzp, sep=';', skiprows=38, header=None, names=W2A_FZP_COLS, usecols=W2A_USE,
                     chunksize=1_000_000, encoding='latin-1',
                     dtype={'SIMSEC': np.float64, 'NO': np.int64, 'LINK': np.int64, 'LANE': np.int16,
                            'POS': np.float64, 'SPEED': np.float64, 'NEXTLINK': 'Int64'})
    for ch in it:
        nrows += len(ch)
        L, P = ch['LINK'], ch['POS']
        m = L.isin(W2A_KEEP_ALL)
        for link, (lo, hi) in W2A_PARTIAL.items():
            m |= (L == link) & (P >= lo) & (P <= hi)
        parts.append(ch.loc[m, W2A_USE].copy())
    df = pd.concat(parts, ignore_index=True)
    meta = {'seed': seed, 'fzp': str(fzp), 'fzp_bytes': fzp.stat().st_size, 'rows_in': nrows, 'kept': int(len(df))}
    if cache_dir is not None:
        p = Path(cache_dir) / f'w_s{seed}.parquet'
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p, index=False)
        meta['cache'] = str(p)
        meta['cache_sha256'] = sha(p)
    return df, meta


def derive_w2a(cache_dir=None):
    from collections import Counter
    sys.path.insert(0, str(ROOT / N31 / 'k8b'))
    if sha(ROOT / N31 / 'k8b' / 'wout_episodes.py') != EPISODES_SHA256:
        raise SystemExit('k8b/wout_episodes.py is not the pinned episode rule')
    import wout_episodes as WE
    _E, _D = u4_modules()
    E = _E
    t0 = time.time()
    all_rows, inputs = [], []
    for seed in W2A_SEEDS:
        df, meta = w2a_extract(seed, cache_dir)
        all_rows += WE.seed_rows(df[['SIMSEC', 'NO', 'LINK', 'POS']], seed)
        inputs.append(meta)
        print('w2a seed', seed, meta['kept'], round(time.time() - t0, 1), flush=True)
    kept, anomalies, clean, pooled = WE.pooled_counter(all_rows)
    counts = {f'side|{d}': pooled.get(('side', d), 0) for d in ('R_D_E', 'R_D_W', 'free', 'side_exit', 'unknown_dest')}
    if counts != W2A_COUNTS:
        print('K9_EVIDENCE_STOP w2a side counts', counts, 'declared', W2A_COUNTS)
        raise SystemExit(1)
    n_free2 = counts['side|free'] + counts['side|side_exit']
    N = counts['side|R_D_E'] + counts['side|R_D_W'] + n_free2
    s_side = {'R_D_E': counts['side|R_D_E'] / N, 'R_D_W': counts['side|R_D_W'] / N, 'free': n_free2 / N}
    if abs(sum(s_side.values()) - 1.0) > 1e-12:
        raise SystemExit('w2a: side shares do not sum to 1')
    if sha(INPX31) != INPX31_SHA256:
        raise SystemExit('v3c3 s31 .inpx sha differs')
    net = E.Network(INPX31)
    c = net.conn['10703']
    if c['from'] != '78' or c['to'] != '31':
        raise SystemExit('K9_EVIDENCE_STOP w2a: connector 10703 is not 78 -> 31')
    x_side = round(float(c['to_pos']), 3)
    if abs(x_side - W2A_X_SIDE) > 1e-3 + 1e-12:
        print('K9_EVIDENCE_STOP w2a x_side', x_side, 'declared', W2A_X_SIDE)
        raise SystemExit(1)
    params = json.loads((ROOT / 'evaluation' / 'parameters.json').read_text(encoding='utf-8-sig'))
    pos = params['runtime']['network']['boundary_out_ramp_position_m']['SC1001_W_out']
    l_side = {'R_D_E': round((float(pos['R_D_E']) - x_side) / 1000.0, 6),
              'R_D_W': round((float(pos['R_D_W']) - x_side) / 1000.0, 6),
              'free': round((float(pos['R_D_W']) - x_side) / 1000.0, 6)}
    if sha(ROOT / CORRIDOR_EVIDENCE) != CORRIDOR_SHA256 or sha(ROOT / P4_EVIDENCE) != P4_SHA256:
        raise SystemExit('w2a: corridor / P-4 evidence sha differs')
    # report only: .inpx-based residence lengths (31 / 10774 / 124 geometry, the P-4 handover rule)
    hand = round(float(net.conn['10774']['from_pos']), 3)
    rep = {'link31_length_m': round(float(net.links['31']['length']), 3), 'link31_handover_m': hand,
           'r_d_e_from_31_m': round(float(net.conn['10484']['from_pos']), 3) if '10484' in net.conn else None,
           'r_d_w_from_124_m': round(float(net.conn['10480']['from_pos']), 3) if '10480' in net.conn else None,
           'free_124_end_m': round(float(net.links['124']['length']), 3)}
    if rep['r_d_e_from_31_m'] is not None:
        rep['inpx_l_side_m'] = {'R_D_E': round(rep['r_d_e_from_31_m'] - x_side, 3),
                                'R_D_W': round(hand - x_side + rep['r_d_w_from_124_m'], 3),
                                'free': round(hand - x_side + rep['free_124_end_m'], 3)}
    lanes = int(net.links['10703']['lanes'])
    values = {'link': 'SC1001_W_out', 'class': 'side', 'ramp_of': dict(W2A_RAMP_OF),
              'shares': s_side, 'counts': counts, 'x_side_m': x_side, 'l_km': l_side,
              'path': ['78', '10703', '31'], 'lanes': lanes, 'branch': 'wout_handover', 'prior_share': 1.0,
              'target': 'SC1001_W_out', 'receiving': 'uqm._effective_available_space(SC1001_W_out)'}
    hours = (9000.0 - 900.0) / 3600.0 * len(W2A_SEEDS)
    doc = {'schema': 'k9-wout-side-handoff/v1', 'values': values,
           'derivation': {'builder': N31 + '/k9/build_k9_evidence.py w2a',
                          'rule': 'wout_episodes.py (a0e92f7d) on the P-4 extract rows (p4b_extract.py 85156269)',
                          'inputs': inputs, 'episodes_total': len(all_rows), 'episodes_kept_window': len(kept),
                          'anomalies': dict(anomalies),
                          'class_dest_counts_pooled': {f'{c_}|{d}': v for (c_, d), v in sorted(pooled.items())},
                          'side_flow_veh_h_mean': sum(v for (cc, _), v in pooled.items() if cc == 'side') / hours,
                          'per_seed_side': {str(s_): {d: sum(1 for r in clean if r[0] == s_ and r[2] == 'side'
                                                             and r[3] == d)
                                                      for d in ('R_D_E', 'R_D_W', 'free', 'side_exit',
                                                                'unknown_dest')} for s_ in W2A_SEEDS},
                          'geometry': {'inpx': INPX31, 'inpx_sha256': INPX31_SHA256, 'x_side_m': x_side,
                                       'boundary_out_ramp_position_m': pos, 'report_inpx_lengths': rep},
                          'corridor_evidence': {'path': CORRIDOR_EVIDENCE, 'sha256': CORRIDOR_SHA256},
                          'p4_evidence': {'path': P4_EVIDENCE, 'sha256': P4_SHA256},
                          'p4b_split_reference_sha256': 'd17dca885bf6353b5a61a16ab3d464f07bb5ab0a7e69c4a04e6c6619ad0d5178'},
           'declaration': dict(DECLARATION, section='2.2')}
    return doc


# ------------------------------------------------------------------------------------------------ F17b
F17B_OUT = HERE / f'offramp_split_forecast_v3c3_{DATE}.json'
F17B_SELECTION = HERE / 'inputs' / f'f17b_selection_{DATE}.json'


F17B_SELECTION_SHA256 = 'cb430b390c8a1018054016621537e6f45b4b67c13d261a00ec9c3999eca856fd'


def derive_f17b():
    """The F17b evidence: the P0-3 selection recomputed from the s41 / s53 FZP by k9/f17b_select.py (VISSIM side
    only), its result fields checked against the recorded P0-3 output inputs/f17b_selection_<date>.json, and its
    runtime values."""
    sys.path.insert(0, str(HERE))
    import f17b_select as F
    if sha(F17B_SELECTION) != F17B_SELECTION_SHA256:
        raise SystemExit('inputs/f17b_selection_%s.json is not the recorded P0-3 output' % DATE)
    rec = json.loads(F17B_SELECTION.read_text(encoding='utf-8'))
    t0 = time.time()
    sel = F.select(log=lambda *a: print(*a, round(time.time() - t0, 1), flush=True))
    got, want = F.result_of(sel), F.result_of(rec)
    if canon(got) != canon(want):
        bad = sorted(k for k in want if canon(got.get(k)) != canon(want.get(k)))
        print('K9_EVIDENCE_STOP f17b: the recomputed selection differs from the P0-3 record in', bad)
        raise SystemExit(1)
    v = sel['runtime_values']
    doc = {'schema': 'k9-offramp-split-forecast/v1', 'values': v,
           'derivation': {'builder': N31 + '/k9/build_k9_evidence.py f17b', 'rule': N31 + '/k9/f17b_select.py',
                          'selection': {'path': N31 + f'/k9/inputs/f17b_selection_{DATE}.json',
                                        'sha256': sha(F17B_SELECTION)},
                          'selected': sel.get('selected'), 'L': sel.get('L')},
           'declaration': dict(DECLARATION, section='2.3')}
    return doc


# ------------------------------------------------------------------------------------------------ main
PARTS = {'w1': (derive_w1, W1_OUT), 'w2a': (derive_w2a, W2A_OUT), 'f17b': (derive_f17b, F17B_OUT)}


def main():
    a = sys.argv[1:]
    if not a or a[0] not in PARTS:
        print(__doc__)
        return 2
    below_normal()
    fn, out = PARTS[a[0]]
    kw = {}
    if a[0] == 'w2a' and '--cache' in a:
        kw['cache_dir'] = a[a.index('--cache') + 1]
    doc = fn(**kw)
    if doc.get('stop'):
        out_stop = out.with_suffix('.STOP.json')
        out_stop.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode('utf-8'))
        print('K9_EVIDENCE_STOP', a[0], 'record', out_stop)
        return 1
    if '--check' in a:
        old = json.loads(out.read_text(encoding='utf-8'))
        if canon(old['values']) != canon(doc['values']):
            print('K9_EVIDENCE_STOP', a[0], 'values differ from', out)
            print('committed', canon(old['values'])[:2000])
            print('derived  ', canon(doc['values'])[:2000])
            return 1
        print('K9_EVIDENCE_CHECK_OK', a[0], out.name, sha(out))
        return 0
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode('utf-8'))
    print('K9_EVIDENCE_WROTE', a[0], out, sha(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
