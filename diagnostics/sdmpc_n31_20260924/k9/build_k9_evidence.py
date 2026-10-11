"""K9-1 evidence builder: the single source of the K9-1 values (K8_PREDECLARATION_AMENDMENT_19 r2 sections 2.1 / 2.2
/ 2.3, sha 4ccfd8fd...; user decisions K9_1_USER_DECISIONS_20261010 D-K9-1..3).  Diagnostics only; the runtime reads the
committed JSON (sha-pinned by the tuning key), never this script.

    python -B diagnostics/sdmpc_n31_20260924/k9/build_k9_evidence.py w1 [--check]

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
w2a / f17b  the W2-A side handoff and F17b forecast parts are added by the commits K9-1-2 / K9-1-3 (amendment 19
     r2 section 4.1).
--check re-derives and compares the committed file's `values` field bit for bit (canonical JSON); any difference
prints K9_EVIDENCE_STOP and exits 1 (section 2.0-3).
Committed evidence = the P0 file bytes of the K9-1 mini probe (K91_VALUES.json, sha 713d232e...; amendment 19 r2
section 4.2 B, r2 B-r1-10: the committed `values` must equal the P0 `values` bit for bit).  A rebuild may differ
from the committed file only in its meta: derivation.* paths, file sizes / row counts of the inputs, the date in
the file name and any commit hash; never in `values` (--check compares `values` only).
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


# ------------------------------------------------------------------------------------------------ main
PARTS = {'w1': (derive_w1, W1_OUT)}


def main():
    a = sys.argv[1:]
    if not a or a[0] not in PARTS:
        print(__doc__)
        return 2
    below_normal()
    fn, out = PARTS[a[0]]
    doc = fn()
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
