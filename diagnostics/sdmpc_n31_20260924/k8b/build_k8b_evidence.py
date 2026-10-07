"""K8b evidence builder: the single source of the K8b values (K8_PREDECLARATION_AMENDMENT_16 r2 section 2.0-3, as
corrected by AMENDMENT_17; user decisions K8B_USER_DECISIONS_20261007 D-K8b-1..4).  Diagnostics only; the runtime
reads the committed JSON (sha-pinned by the tuning key), never this script.

    python -B diagnostics/sdmpc_n31_20260924/k8b/build_k8b_evidence.py p1 [--check]

p1  sc1002w_saturation_v3c3_20261007.json  (P-1, section 2.1): SC1002 W head groups 30|p3 / 30|p4, U4 value rule F2
    s_from_green_start_incl_startup_veh_h_lane measured by the byte copies of the U4 measurers in u4/
    (derive_head_saturation.py sha 369c2fdb..., urban_b2_evidence.py sha 73565c5c...) on the v3c3 NC fit seeds
    31/41/43/47/53 (D:/VISSIM_runs/20261001_v3c3/s<seed>_v3c3nc: FZP, .inpx, the SC1002 .sig the .inpx names; read
    only, BELOW_NORMAL), unchanged constants (MIN_BINS 24, MIN_CYCLES 8, MIN_SEEDS 3, T_SU 5 s); the two head groups
    from inputs/sc1002w_head_groups_v3b_20260929.json (rows of the v3b contract, source sha recorded), each head
    asserted equal in the v3c3 network; the R-obs-b exact validation (.mer) is not carried (as the probe,
    tools/p1_derive.py sha 3c39e102).  Value rule (probe make_values.p1_values): both measured -> F2 of each; one
    default -> 1850 x F2 / s_unimpeded of the measured one; both default -> the v3b proxy 1646.7 / 1685.5.
    Runtime formula (runtime_setup.install_sc1002w_saturation): C(E) = lanes_p3 s_p3 b_E / (b_E + b_S),
    C(S) = lanes_p3 s_p3 b_S / (b_E + b_S), C(N) = lanes_p4 s_p4, b = the decision's template beta.
--check re-derives and compares the committed file's `values` field bit for bit (canonical JSON); any difference
prints K8B_EVIDENCE_STOP and exits 1 (section 2.0-3: the judging stage does not start)."""
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
P1_OUT = HERE / 'sc1002w_saturation_v3c3_20261007.json'
P1_GROUPS = HERE / 'inputs' / 'sc1002w_head_groups_v3b_20260929.json'
P1_GROUPS_SHA256 = 'cfc2b7bb3ef0bb136ccb9e372ba5a9376c6a26e101c4d9cef3b863b8be3f3924'
U4_SHA256 = {'derive_head_saturation.py': '369c2fdbf9939a2cc60a96ffaa656934d02258246f667d3c692ca21fae2ffabd',
             'urban_b2_evidence.py': '73565c5c259389112164290fac271fa55f2c796a38d1d32303a94c2feadef0f5'}
P1_KEYS = ('30|p3', '30|p4')
P1_MEMBERS = {'E': 'SC1002_W_SC1001_to_E_SC101', 'S': 'SC1002_W_SC1001_to_S_SC105',
              'N': 'SC1002_W_SC1001_to_N_SC2004'}
DECLARATION = {'amendment16_sha256': 'e8ad8a346d93fcb23eea4428eca213163860dc02a48e4c6e022bf0180263cbc4',
               'amendment17_sha256': '5bb431346755ee45386746a0e926adba73a69e86ed3a342bdc8340a2ccc507b4',
               'decisions_file': 'K8B_USER_DECISIONS_20261007.md (D-K8b-1..4, variant A)'}


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


# ------------------------------------------------------------------------------------------------ P-1
def p1_values(rows):
    """The probe value rule (make_values.p1_values) on the two measured group rows."""
    f2 = {k: rows[k]['measured']['s_from_green_start_incl_startup_veh_h_lane'] for k in P1_KEYS}
    st = {k: rows[k]['status'] for k in P1_KEYS}
    rule = 'v3c3 F2 measured (both groups)'
    if st['30|p3'] != 'measured' and st['30|p4'] != 'measured':
        f2 = {'30|p3': 1646.7, '30|p4': 1685.5}
        rule = 'v3b proxy (both default)'
    elif st['30|p3'] != 'measured':
        r = rows['30|p4']['measured']
        f2['30|p3'] = 1850.0 * r['s_from_green_start_incl_startup_veh_h_lane'] / r['s_unimpeded_veh_h_lane']
        rule = '30|p3 default: 1850 x F2/s_unimpeded of 30|p4'
    elif st['30|p4'] != 'measured':
        r = rows['30|p3']['measured']
        f2['30|p4'] = 1850.0 * r['s_from_green_start_incl_startup_veh_h_lane'] / r['s_unimpeded_veh_h_lane']
        rule = '30|p4 default: 1850 x F2/s_unimpeded of 30|p3'
    return {'s_p3_veh_h_lane': f2['30|p3'], 's_p4_veh_h_lane': f2['30|p4'], 'lanes_p3': 2, 'lanes_p4': 1,
            'members': dict(P1_MEMBERS), 'status': st, 'rule': rule,
            'formula': 'C_E = lanes_p3 s_p3 b_E/(b_E+b_S); C_S = lanes_p3 s_p3 b_S/(b_E+b_S); C_N = lanes_p4 s_p4 '
                       '(b = template beta at the hook, runtime_setup after install_measured_movement_capacity)'}


def derive_p1():
    for name, want in U4_SHA256.items():
        if sha(HERE / 'u4' / name) != want:
            raise SystemExit(f'u4/{name} is not the pinned U4 measurer copy')
    if sha(P1_GROUPS) != P1_GROUPS_SHA256:
        raise SystemExit('inputs/sc1002w_head_groups_v3b_20260929.json changed')
    sys.path.insert(0, str(HERE / 'u4'))
    import urban_b2_evidence as E
    E.NC_ROOT = NC_ROOT
    E.nc_fzp = lambda seed: '%s/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (E.NC_ROOT, seed, seed)
    E.nc_inpx = lambda seed: '%s/s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (E.NC_ROOT, seed, seed)
    import derive_head_saturation as D
    t0 = time.time()
    contract = json.loads(P1_GROUPS.read_text(encoding='utf-8'))
    net = E.Network(E.nc_inpx(31))
    groups = []
    for row in contract['groups']:
        if row['group_id'] not in P1_KEYS:
            continue
        heads = []
        for h in row['heads']:
            x = net.heads[h['head_id']]
            if (x['link'], x['lane'], x['sg']) != (row['stopline_link'], h['lane'], h['sg']) \
                    or 'SC' + x['sc'] != row['signal'] or abs(x['position_m'] - h['position_m']) > 1e-3:
                raise SystemExit('%s: head %s differs in the v3c3 network' % (row['group_id'], h['head_id']))
            heads.append(dict(x))
        groups.append({'group_id': row['group_id'], 'signal': row['signal'], 'phase': row['phase'],
                       'native_signal': row['native_signal'], 'observation_group': row['observation_group'],
                       'stopline_link': row['stopline_link'], 'heads': heads})
    if [g['group_id'] for g in groups] != list(P1_KEYS):
        raise SystemExit('head groups 30|p3 / 30|p4 not found')
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
        print('p1 seed', seed, 'rows_kept', meta['rows_kept'], round(time.time() - t0, 1), flush=True)
        del arr
    rows = [D.group_row(g, runs, {}, names) for g in groups]
    by_key = {r['key']: r for r in rows}
    doc = {'schema': 'k8b-sc1002w-saturation/v1', 'values': p1_values(by_key),
           'derivation': {'builder': N31 + '/k8b/build_k8b_evidence.py p1', 'measurer': dict(U4_SHA256),
                          'head_groups': {'path': N31 + '/k8b/inputs/sc1002w_head_groups_v3b_20260929.json',
                                          'sha256': P1_GROUPS_SHA256, 'source': contract['source']},
                          'network_s31': {'path': E.nc_inpx(31), 'sha256': E.sha256_file(E.nc_inpx(31))},
                          'network_signature_equal_s31': signatures, 'sig': sig_meta,
                          'sig_equal_in_nc_runs': sig_equal, 'nc_fzp': pins,
                          'parameters': {'T_SU': D.T_SU, 'MIN_BINS': D.MIN_BINS, 'MIN_CYCLES': D.MIN_CYCLES,
                                         'MIN_SEEDS': D.MIN_SEEDS, 'DEFAULT_VEH_H_LANE': D.DEFAULT_VEH_H_LANE,
                                         'window_s': [D.T_FROM, D.T_END]},
                          'groups': {r['key']: {'status': r['status'], 'flags': r.get('flags'),
                                                'measured': r['measured']} for r in rows}},
           'declaration': dict(DECLARATION, section='2.1')}
    return doc


# ------------------------------------------------------------------------------------------------ main
PARTS = {'p1': (derive_p1, P1_OUT)}


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('p1', 'p2', 'p4'):
        print(__doc__)
        return 2
    if a[0] not in PARTS:
        raise SystemExit(f'{a[0]}: not built by this commit')
    below_normal()
    fn, out = PARTS[a[0]]
    doc = fn()
    if '--check' in a:
        old = json.loads(out.read_text(encoding='utf-8'))
        if canon(old['values']) != canon(doc['values']):
            print('K8B_EVIDENCE_STOP', a[0], 'values differ from', out)
            print('committed', canon(old['values'])[:2000])
            print('derived  ', canon(doc['values'])[:2000])
            return 1
        print('K8B_EVIDENCE_CHECK_OK', a[0], out.name, sha(out))
        return 0
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode('utf-8'))
    print('K8B_EVIDENCE_WROTE', a[0], out, sha(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
