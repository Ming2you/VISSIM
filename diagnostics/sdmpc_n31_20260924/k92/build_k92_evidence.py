"""K9-2 bundle 1 evidence builder: the single source of the K9-2 bundle-1 values (K8_PREDECLARATION_AMENDMENT_24,
fixed version sha d46db6dc...; user decisions D-K9-34..36 of K9_1_J1_NOTES_20261013.md).  Diagnostics only; the
runtime reads the committed JSON (sha-pinned by the tuning key), never this script.

    python -B diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py w|hb [--check] [--root R] [--out-dir D]

w   sc109w_through_saturation_v3b_u4_<date>.json (W, amendment 24 section 2.1): the SC109 west through movement
    SC109_W_SC108_to_E takes the group capacity C = round(s x lanes, 1) (the U4 group rule, build_table.py:363) with
    s = the U4 table (sha 22384c00..., schema u4-saturation-table/v1) row groups[27] '173|p3' F2 statistic
    measured.s_from_green_start_incl_startup_veh_h_lane (1736.6) and lanes = 3 -> 5209.8 (repr '5209.8'; the float
    product 1736.6 x 3 = 5209.799999999999 is never used).  Input copy: inputs/u4_row_173_p3_v3b.json (the row,
    canonical-JSON equal to the table's groups[27], A8).  Builder assertions (else K92_EVIDENCE_STOP, exit 1):
      A1 C / lanes <= 2000; A2 the U4 row's model members of 173|p3 = {SC109_W_SC108_to_E} and C <= lanes x 2000;
      A3 s in [1200, 2200]; A4 lanes 3 = the U4 row heads = U4 n_lanes = movement_lanes_perimeter_20260824.json =
      the v3c3 .inpx (sha 3de889f0...) lane set {1, 2, 3} of the link 173 heads of SG '109 2';
      A8 input row = U4 groups[27] (canonical JSON); A9 the v3c3 .inpx heads 1090201 / 1090202 / 1090203 = the U4
      row heads (link 173, lanes 3 / 2 / 1, '109 2' <-> signal SC109 + sg '2', position +-1e-3 m; allVehTypes true
      checked in the .inpx only); A10 the left-turn heads 1090501 / 1090502 stand on lanes 5 / 4 (no shared lane);
      A11 values.statistic = 's_from_green_start_incl_startup', values.s_veh_h_lane = the row F2, values.capacity_veh_h
      = round(s x lanes, 1), repr(capacity) = values.capacity_repr = '5209.8'.
hb  head_floor_seed_v3c3_robs_<date>.json (H-b, amendment 24 section 2.2): the (173, p4) left-turn head floor seed
    s = the median of the two-window supported values of the v3c3 R-obs NC fit-seed runs sdmpc31_v3c3_nc_s{31,43,47}
    (decision JSONs; consecutive decisions 150 s apart that both carry a (173, p4) candidate
    head_candidate_rate_173_p4_* with the earlier head_candidate_end_173_p4_* = the earlier decision time = the later
    window start; support = min of the two candidates).  Only the (173, p4) candidate / end / floor keys are read out
    of the decision JSONs.  Re-derivation (P0-2 (b)): for v3c3-s31 and v3c3-s43 only, the same rule recomputed from
    obs150/derived_<T>.json head_window rows of the heads 1090501 / 1090502 only (green >= 30 s per head, qualified
    sum >= 5, rate = sum over heads in the SHO physical-group order of 3600 x qualified / green) must equal the
    recorded candidates and supports exactly (else STOP).  v3c3-s47: decision JSON (173, p4) keys only, obs150 never
    opened.  Assertions: B1 s <= 4000; B2 s > base 413.0612244897959; B3 the .inpx (173, p4) heads = {1090501 lane 5,
    1090502 lane 4}, SG '109 5', allVehTypes true; B4 the distribute members of (173, p4) = {SC109_W_SC108_to_N_SC16}
    (the attribution hook E1 movement specs of S1_A0h: signal SC109, phase SC109_p4, kind internal, origin in
    link_to_origins['173'] of the detector mapping); B6 urban.capacity.head_observation = {enabled true,
    min_green_sec 30, min_crossings 5} in CFG and SAF-K91; B7 (report) s <= 2493.4; B8 repr(s) = '1045.1612903225805'
    and that repr is in the R-obs v3c3-s31 / s43 support repr set.
--check re-derives and compares the committed file's `values` field bit for bit (canonical JSON); any difference
prints K92_EVIDENCE_STOP and exits 1.  A rebuild may differ from the committed file only in its meta: derivation
paths (root, out dir), file sizes and the commit hash; never in `values` (--check compares `values` only).
Amendment 25 (D-K9-42): the W input row `source` and the W evidence `sources` carry file names and sha256 only,
never a path string (the adapter source-pin step opens every .json / .inpx path string reachable from the
tuning; the old U4 table path pulled in the v3b decision chains).  The H-b evidence is unchanged.
"""
import argparse
import ctypes
import glob
import hashlib
import json
import os
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
N31 = 'diagnostics/sdmpc_n31_20260924'
DATE = '20261016'
DECLARATION = {'amendment24_sha256': 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc',
               'decisions_file': 'K9_1_J1_NOTES_20261013.md (D-K9-34..36), sha bf6f01ab...'}
U4_TABLE = (r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
            r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2/u4_saturation_table.json')
U4_TABLE_SHA256 = '22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b'
U4_SCHEMA = 'u4-saturation-table/v1'
U4_MEASURER_SHA256 = {'build_table.py': '57ef2e5167d6bd7b90218aadd9fb768fddb5a1d0d98cf2909df43a98892487ef',
                      'analyze_run.py': '54958a324e6217708022d67c2b1593bd7790a3ab101cc314eeec729f4db6bc29'}
INPX = r'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/prepared/network/baseline_s31_v3c3nc.inpx'
INPX_SHA256 = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
LANES_REL = 'outputs/movement_lanes_perimeter_20260824.json'
LANES_SHA256 = '444a3047e872d972398c82e716426e797d3c09e321504fc109db0aeb27344cda'
MAP_REL = 'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'
MAP_SHA256 = 'f8c90e5769c7c92e8c698134dbf61b5f35f2205bf634841f4562f37967e72b3e'
SHO_REL = 'evaluation/controllers/signal_head_observation.py'
SHO_SHA256 = 'd9bd53920eea89ace2b71a589d780069c3c7191be889aca894994ddf65bcc106'
TUNING_CHECK = {'diagnostics/sdmpc_n31_20260924/config_n31_v2.json':
                'd0f9ef395d4f9c51e6c68412f7c33abd546217e0d8cdc59d3c620183fa7aaec6',
                'diagnostics/sdmpc_n31_20260924/config_n31_v2_stopline_observed_full_k91.json':
                '5f0d0e40a39e44b3c7601f23177afbad8c2eee23d4421626482f2244a86c3341'}

# ------------------------------------------------------------------------------------------------ W
W_SCHEMA = 'k92-sc109w-through-saturation/v1'
W_OUT = f'sc109w_through_saturation_v3b_u4_{DATE}.json'
W_INPUT = 'inputs/u4_row_173_p3_v3b.json'
W_INPUT_SCHEMA = 'k92-u4-row/v1'
W_MOVEMENT = 'SC109_W_SC108_to_E'
W_GROUP = '173|p3'
W_GROUP_INDEX = 27
W_HEADS = ('1090201', '1090202', '1090203')
W_LANES_EXPECTED = 3
W_STAT = 's_from_green_start_incl_startup'
W_STAT_KEY = 's_from_green_start_incl_startup_veh_h_lane'
W_CAPACITY_REPR = '5209.8'
W_VALUE_RULE = 'round(s_veh_h_lane * lanes, 1) (U4 build_table.py:363)'
W_REPORT_ONLY = {
    's_unimpeded': 1900.2,
    's_unimpeded_capacity': {'value': 5700.6, 'label': 'D-K9-30 원래 값, 몫 가르기 CW 값, 보고 팔 Wu'},
    'exact_s31': 1909.7,
    'sensitivity': {'value': 5927.0,
                    'label': 'J1 사후 자료 — 같은 시드 폐루프, 원인 분석·몫 가르기에 이미 씀, 독립 근거 아님'},
    'decision': 'D-K9-34 (F2, 몫 가르기 뒤 선택)'}
LEFT_HEADS = ('1090501', '1090502')

# ------------------------------------------------------------------------------------------------ H-b
HB_SCHEMA = 'k92-head-floor-seed/v1'
HB_OUT = f'head_floor_seed_v3c3_robs_{DATE}.json'
HB_GROUP = ['173', 'p4']
HB_MEMBER = 'SC109_W_SC108_to_N_SC16'
HB_SEED_REPR = '1045.1612903225805'
HB_BASE = 413.0612244897959
HB_OPTIONS = {'enabled': True, 'min_green_sec': 30, 'min_crossings': 5}
RO = r'D:/VISSIM_runs/20261001_sdmpc31_v3c3'
HB_RUNS = {'v3c3-s31': 'sdmpc31_v3c3_nc_s31', 'v3c3-s43': 'sdmpc31_v3c3_nc_s43', 'v3c3-s47': 'sdmpc31_v3c3_nc_s47'}
HB_OBS150_RUNS = ('v3c3-s31', 'v3c3-s43')          # P0-2 (b): v3c3-s47 obs150 is never opened
HB_E1 = r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_attrib/hook/S1_A0h'
HB_REPORT_ONLY = {
    'Hb-2': {'value': 812.9032258064516, 'source': 'R-obs v3c3-s31/s43/s47 900 s held floor median'},
    'Hb-3': {'value': 1384.6153846153848, 'source': 'J1 v3c3-s31 rerun T=3,900 recorded floor (= attribution H1)',
             'label': 'J1 사후 자료 — 결과를 본 값, 민감도 보고 팔 B1s'},
    'Hb-4': {'value': 2493.4, 'source': "U4 '173|p4' s_unimpeded x 2 (the 'pin table' literal reading)"},
    'Hb-5': {'value': 2090.32, 'source': 'R-obs three runs 9,000 s held floor median (approx.)'}}
CAND = 'head_candidate_rate_173_p4_'
END = 'head_candidate_end_173_p4_'
FLOOR = 'head_discharge_floor_173_p4_'


class Stop(Exception):
    pass


def require(cond, msg):
    if not cond:
        raise Stop(msg)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def below_normal():
    try:
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    except Exception:  # noqa: BLE001
        pass


def json_bytes(doc):
    return (json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode('utf-8')


def write_json(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json_bytes(doc)
    path.write_bytes(data)
    return sha(path)


def inpx_heads(want):
    """The <signalHead> attributes of the wanted head ids in the pinned v3c3 .inpx (regex on the attribute tag)."""
    require(sha(INPX) == INPX_SHA256, 'v3c3 .inpx sha256 differs: %s' % INPX)
    text = Path(INPX).read_text(encoding='utf-8', errors='replace')
    out = {}
    for hid in want:
        tags = re.findall(r'<signalHead [^>]*\bno="%s"[^>]*>' % hid, text)
        require(len(tags) == 1, 'head %s: %d <signalHead> tags in the .inpx' % (hid, len(tags)))
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', tags[0]))
        link, lane = attrs['lane'].split()
        out[hid] = {'link': link, 'lane': int(lane), 'sg': attrs['sg'], 'pos': float(attrs['pos']),
                    'allVehTypes': attrs.get('allVehTypes')}
    return out


# ------------------------------------------------------------------------------------------------ W
def w_input_doc(table):
    row = table['groups'][W_GROUP_INDEX]
    require(row.get('key') == W_GROUP, 'U4 groups[%d] is %r, not %s' % (W_GROUP_INDEX, row.get('key'), W_GROUP))
    return {'schema': W_INPUT_SCHEMA,
            'source': {'name': U4_TABLE.replace('\\', '/').rsplit('/', 1)[-1], 'sha256': U4_TABLE_SHA256,
                       'schema': table['schema'],
                       'generated_by': table['generated_by'].replace('\\', '/').rsplit('/', 1)[-1],
                       'network': table.get('network'),
                       'group_index': W_GROUP_INDEX, 'measurer_sha256': dict(U4_MEASURER_SHA256)},
            'row': row}


def w_build(root):
    root = Path(root)
    require(sha(U4_TABLE) == U4_TABLE_SHA256, 'U4 table sha256 differs: %s' % U4_TABLE)
    table = json.loads(Path(U4_TABLE).read_text(encoding='utf-8'))
    require(table.get('schema') == U4_SCHEMA, 'U4 table schema %r' % table.get('schema'))
    inp = w_input_doc(table)
    row = inp['row']
    # A8: the input row is the table's groups[27] (canonical JSON)
    require(canon(row) == canon(table['groups'][W_GROUP_INDEX]), 'A8 input row != U4 groups[27]')
    require(row['signal'] == 'SC109' and row['phase'] == 'p3' and row['stopline_link'] == '173', 'U4 row identity')
    require(row['status'] == 'measured', 'U4 row status %r' % row['status'])
    s = row['measured'][W_STAT_KEY]
    lanes = int(row['n_lanes'])
    cap = round(s * lanes, 1)
    # A3
    require(1200.0 <= s <= 2200.0, 'A3 s %r outside [1200, 2200]' % s)
    # A1
    require(cap / lanes <= 2000.0, 'A1 C / lanes %r > 2000' % (cap / lanes))
    # A2 (U4 row model members of 173|p3)
    members = sorted((row.get('plant') or {}).get('base', {}).get('members', {}))
    require(members == [W_MOVEMENT], 'A2 model members of 173|p3 %s' % members)
    require(cap <= lanes * 2000.0, 'A2 C %r > lanes x 2000' % cap)
    # A4 / A9 / A10
    require(sha(root / LANES_REL) == LANES_SHA256, 'lanes file sha256 differs')
    lane_file = json.loads((root / LANES_REL).read_text(encoding='utf-8'))
    lanes_file = lane_file['movement_lanes_perimeter'][W_MOVEMENT]
    heads = inpx_heads(W_HEADS + LEFT_HEADS)
    through = {h: heads[h] for h in W_HEADS}
    require(all(v['link'] == '173' and v['sg'] == '109 2' and v['allVehTypes'] == 'true' for v in through.values()),
            'A4/A9 .inpx through heads %s' % through)
    inpx_lanes = sorted(v['lane'] for v in through.values())
    row_heads = {str(h['head_id']): h for h in row['heads']}
    require(sorted(row_heads) == sorted(W_HEADS), 'A9 U4 row head ids %s' % sorted(row_heads))
    for hid, v in through.items():
        rh = row_heads[hid]
        require(rh['lane'] == v['lane'] and str(rh['sg']) == '2' and row['signal'] == 'SC' + v['sg'].split()[0]
                and abs(float(rh['position_m']) - v['pos']) <= 1e-3, 'A9 head %s %s vs %s' % (hid, rh, v))
    require(lanes == W_LANES_EXPECTED == len(row['heads']) == float(lanes_file) == len(inpx_lanes)
            and inpx_lanes == [1, 2, 3], 'A4 lanes %s / heads %d / file %r / inpx %s' % (
                lanes, len(row['heads']), lanes_file, inpx_lanes))
    left = {h: heads[h] for h in LEFT_HEADS}
    require(sorted(v['lane'] for v in left.values()) == [4, 5] and not set(v['lane'] for v in left.values())
            & set(inpx_lanes), 'A10 left-turn head lanes %s' % left)
    values = {'movement': W_MOVEMENT, 'group': W_GROUP, 'lanes': lanes,
              'heads': [{'head_id': hid, 'link': '173', 'lane': through[hid]['lane'], 'sg': '109 2',
                         'position_m': row_heads[hid]['position_m']} for hid in W_HEADS],
              'statistic': W_STAT, 's_veh_h_lane': s, 'capacity_veh_h': cap, 'capacity_repr': repr(cap),
              'value_rule': W_VALUE_RULE, 'network_value_source': 'v3b',
              'network_deployed': 'v3c3 ' + INPX_SHA256}
    # A11
    require(values['statistic'] == W_STAT and values['s_veh_h_lane'] == row['measured'][W_STAT_KEY]
            and values['capacity_veh_h'] == round(s * lanes, 1) and repr(values['capacity_veh_h']) == W_CAPACITY_REPR
            and values['capacity_repr'] == W_CAPACITY_REPR, 'A11 %s' % values)
    doc = {'schema': W_SCHEMA, 'declaration': DECLARATION, 'values': values, 'report_only': W_REPORT_ONLY,
           'sources': {'u4_table': inp['source'],
                       'input_row': {'name': W_INPUT.rsplit('/', 1)[-1],
                                     'sha256': hashlib.sha256(json_bytes(inp)).hexdigest()},
                       'inpx': {'name': INPX.rsplit('/', 1)[-1], 'sha256': INPX_SHA256},
                       'lanes_file': {'name': LANES_REL.rsplit('/', 1)[-1], 'sha256': LANES_SHA256,
                                      'value': lanes_file}},
           'assertions': {'A1': cap / lanes, 'A2': {'members': members, 'capacity': cap, 'limit': lanes * 2000.0},
                          'A3': s, 'A4': {'lanes': lanes, 'inpx_lanes': inpx_lanes, 'lanes_file': lanes_file},
                          'A8': True, 'A9': {h: {k: through[h][k] for k in ('link', 'lane', 'sg', 'pos')}
                                              for h in W_HEADS},
                          'A10': {h: left[h]['lane'] for h in LEFT_HEADS},
                          'A11': {'float_product_repr': repr(s * lanes), 'capacity_repr': repr(cap)}}}
    return inp, doc


# ------------------------------------------------------------------------------------------------ H-b
def hb_keys(path):
    """(173, p4) candidate / end / floor of one decision JSON and its sim_sec (nothing else is kept)."""
    d = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    md = {**(d.get('diagnostics') or {}), **(d.get('metadata') or {})}
    if md.get('sim_sec') is None:
        return None
    cand = [v for k, v in md.items() if k.startswith(CAND)]
    end = [v for k, v in md.items() if k.startswith(END)]
    floor = [v for k, v in md.items() if k.startswith(FLOOR)]
    require(len(cand) <= 1 and len(end) <= 1 and len(floor) <= 1, '%s: several (173, p4) keys' % path)
    return (float(md['sim_sec']), cand[0] if cand else None, end[0] if end else None, floor[0] if floor else None)


def hb_supports(rows):
    """Two-window supports of consecutive decisions (amendment 24 section 2.2 statistic)."""
    out = []
    for i in range(1, len(rows)):
        (t0, c0, e0, _f0), (t1, c1, _e1, _f1) = rows[i - 1], rows[i]
        if c0 is not None and c1 is not None and e0 == t0 and t1 - t0 == 150.0:
            out.append((t1, min(c0, c1)))
    return out


def hb_rows(run):
    folder = Path(RO) / run / ('decisions_' + run)
    rows = []
    for f in sorted(glob.glob(str(folder / 'action_*.json'))):
        r = hb_keys(f)
        if r is not None:
            rows.append(r)
    rows.sort()
    return folder, rows


def left_group_order(root):
    """(173, p4) heads in the SHO physical-group order (SHO.physical_groups of the pinned SHO bytes)."""
    require(sha(Path(root) / SHO_REL) == SHO_SHA256, 'SHO bytes differ from the rule code sha')
    sys.path.insert(0, str(Path(root)))
    import importlib.util
    spec = importlib.util.spec_from_file_location('k92_sho_rule', str(Path(root) / SHO_REL))
    sho = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sho)
    cfg = json.loads((Path(root) / 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json').read_text(encoding='utf-8'))
    plan = json.loads((Path(root) / cfg['urban']['plan']['actuation_plan_json']).read_text(encoding='utf-8'))
    groups = sho.physical_groups(INPX, plan)
    heads = groups[('173', 'p4')]
    return [h['head_id'] for h in heads], heads


def hb_obs150_candidates(run, order):
    """P0-2 (b): the SHO candidate rule recomputed from obs150 head_window rows of the left-turn heads only."""
    folder = Path(RO) / run / ('decisions_' + run) / 'obs150'
    out = {}
    for f in sorted(glob.glob(str(folder / 'derived_*.json'))):
        doc = json.loads(Path(f).read_text(encoding='utf-8-sig'))
        hw = doc.get('head_window') or {}
        if not hw:
            continue
        rows = {str(r['head_id']): r for r in hw.get('heads') or [] if str(r.get('head_id')) in LEFT_HEADS}
        del doc
        end = float(hw['end_sec'])
        start = float(hw['start_sec'])
        if hw.get('clock_complete') is not True or any(h not in rows for h in order):
            out[end] = (start, None)
            continue
        rates, count, enough = [], 0.0, True
        for h in order:
            r = rows[h]
            green, q = float(r['green_sec']), float(r['qualified_crossings'])
            if green < HB_OPTIONS['min_green_sec']:
                enough = False
            rates.append(3600 * q / green if green > 0 else 0.0)
            count += q
        rate = sum(rates)
        cand = rate if (enough and count >= HB_OPTIONS['min_crossings'] and rate > 0) else None
        out[end] = (start, cand)
    return out


def hb_build(root):
    root = Path(root)
    order, geo_heads = left_group_order(root)
    require(sorted(order) == sorted(LEFT_HEADS), 'B3 SHO group heads %s' % order)
    heads = inpx_heads(LEFT_HEADS)
    require(all(heads[h]['link'] == '173' and heads[h]['sg'] == '109 5' and heads[h]['allVehTypes'] == 'true'
                for h in LEFT_HEADS) and {heads['1090501']['lane'], heads['1090502']['lane']} == {5, 4}
            and heads['1090501']['lane'] == 5 and heads['1090502']['lane'] == 4, 'B3 %s' % heads)
    # B6
    for rel, want in TUNING_CHECK.items():
        require(sha(root / rel) == want, 'tuning %s sha differs' % rel)
        t = json.loads((root / rel).read_text(encoding='utf-8'))
        require(t['urban']['capacity']['head_observation'] == HB_OPTIONS, 'B6 %s head_observation' % rel)
    # B4 (attribution hook E1 of S1_A0h: SC109 movement specs; detector mapping link_to_origins['173'])
    require(sha(root / MAP_REL) == MAP_SHA256, 'detector mapping sha differs')
    lto = json.loads((root / MAP_REL).read_text(encoding='utf-8'))['link_to_origins'].get('173') or []
    e1 = sorted(glob.glob(os.path.join(HB_E1, 'e1_*.json')))
    require(len(e1) == 1, 'B4 E1 record of S1_A0h: %s' % e1)
    specs = json.loads(Path(e1[0]).read_text(encoding='utf-8'))['sc109_movements']
    members = sorted(m for m, s in specs.items() if s.get('phase') == 'SC109_p4' and s.get('kind') == 'internal'
                     and s.get('origin') in lto)
    require(members == [HB_MEMBER], 'B4 distribute members of (173, p4): %s' % members)
    w_origin = specs.get('SC109_W_SC108_to_E', {}).get('origin')
    require(specs[HB_MEMBER]['origin'] == w_origin == 'SC108_to_SC109', 'coupling origin %s / %s' % (
        specs[HB_MEMBER]['origin'], w_origin))
    # statistic
    per_seed, pooled, runs, rederive = {}, [], {}, {}
    for name, run in HB_RUNS.items():
        folder, rows = hb_rows(run)
        sup = hb_supports(rows)
        require(sup, '%s: no two-window support' % name)
        vals = [v for _t, v in sup]
        per_seed[name] = {'n': len(vals), 'median': statistics.median(vals)}
        pooled += vals
        runs[name] = {'run': run, 'decisions': str(folder).replace('\\', '/'), 'n_decisions': len(rows)}
        if name in HB_OBS150_RUNS:
            obs = hb_obs150_candidates(run, order)
            rec_c = {t: c for (t, c, _e, _f) in rows if t >= 150.0}
            obs_c = {t: c for t, (_s, c) in obs.items()}
            same_c = set(rec_c) == set(obs_c) and all(rec_c[t] == obs_c[t] for t in rec_c)
            obs_rows = [(t, obs_c[t], (t if obs_c[t] is not None else None), None) for t in sorted(obs_c)]
            starts_ok = all(obs[t][0] == t - 150.0 for t in obs if t > 150.0)
            sup_obs = hb_supports(obs_rows)
            same_s = sup_obs == [(t, v) for t, v in sup if t >= 150.0]
            rederive[name] = {'candidates_equal': same_c, 'supports_equal': same_s, 'window_starts_t_minus_150':
                              starts_ok, 'n_candidates': sum(1 for v in rec_c.values() if v is not None),
                              'n_supports': len(sup_obs), 'supports': [[t, v] for t, v in sup_obs]}
            require(same_c and same_s and starts_ok, 'P0-2 (b) %s: obs150 re-derivation differs (%s)' % (
                name, {k: v for k, v in rederive[name].items() if k != 'supports'}))
        else:
            rederive[name] = {'obs150': 'not opened (v3c3-s47, blind)'}
    s = statistics.median(pooled)
    require(repr(s) == HB_SEED_REPR, 'B8 median repr %r != %s' % (s, HB_SEED_REPR))
    support_reprs = sorted({repr(v) for name in HB_OBS150_RUNS for _t, v in hb_supports(hb_rows(HB_RUNS[name])[1])})
    require(HB_SEED_REPR in support_reprs, 'B8 seed repr not among the s31 / s43 support reprs')
    require(s <= 4000.0, 'B1 s %r > 4000' % s)
    require(s > HB_BASE, 'B2 s %r <= base' % s)
    values = {'group': HB_GROUP, 'heads': [{'head_id': h, 'link': '173', 'lane': heads[h]['lane'], 'sg': '109 5'}
                                           for h in order],
              'members': [HB_MEMBER], 'seed': s, 'seed_repr': repr(s), 'statistic': 'robs_two_window_support_median',
              'per_seed': per_seed, 'options': {'min_green_sec': 30, 'min_crossings': 5},
              'rule_code_sha256': SHO_SHA256, 'runs': runs, 'learning': 'kept (D-K9-36)'}
    doc = {'schema': HB_SCHEMA, 'declaration': DECLARATION, 'values': values, 'report_only': HB_REPORT_ONLY,
           'sources': {'inpx': {'path': INPX, 'sha256': INPX_SHA256}, 'b4_e1': e1[0].replace('\\', '/'),
                       'detector_mapping': {'path': MAP_REL, 'sha256': MAP_SHA256}},
           'assertions': {'B1': s, 'B2': {'seed': s, 'base': HB_BASE}, 'B3': {h: heads[h] for h in LEFT_HEADS},
                          'B4': members, 'B6': HB_OPTIONS, 'B7_report': {'seed': s, 'limit': 2493.4,
                                                                        'holds': s <= 2493.4},
                          'B8': {'seed_repr': repr(s), 'support_reprs_s31_s43_n': len(support_reprs)},
                          'pooled_n': len(pooled), 'p0_2_b': rederive}}
    return doc


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('part', choices=('w', 'hb'))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--root', default=str(HERE.parents[2]))
    ap.add_argument('--out-dir', default=str(HERE))
    args = ap.parse_args()
    below_normal()
    out = Path(args.out_dir)
    try:
        if args.part == 'w':
            inp, doc = w_build(args.root)
            target, inp_target = out / W_OUT, out / W_INPUT
            if args.check:
                old = json.loads(target.read_text(encoding='utf-8'))
                old_inp = json.loads(inp_target.read_text(encoding='utf-8'))
                require(canon(old['values']) == canon(doc['values']), 'w --check: values differ')
                require(canon(old_inp['row']) == canon(inp['row']), 'w --check: input row differs (A8)')
                print('K92_EVIDENCE_CHECK_OK w values_sha256=%s file_sha256=%s' % (
                    hashlib.sha256(canon(doc['values']).encode()).hexdigest(), sha(target)))
                return 0
            s_in = write_json(inp_target, inp)
            require(s_in == doc['sources']['input_row']['sha256'], 'input row bytes differ from the evidence pin')
            s_out = write_json(target, doc)
            print('K92_EVIDENCE_OK w %s sha256=%s input=%s sha256=%s capacity_repr=%s' % (
                target, s_out, inp_target, s_in, doc['values']['capacity_repr']))
        else:
            doc = hb_build(args.root)
            target = out / HB_OUT
            if args.check:
                old = json.loads(target.read_text(encoding='utf-8'))
                require(canon(old['values']) == canon(doc['values']), 'hb --check: values differ')
                print('K92_EVIDENCE_CHECK_OK hb values_sha256=%s file_sha256=%s' % (
                    hashlib.sha256(canon(doc['values']).encode()).hexdigest(), sha(target)))
                return 0
            s_out = write_json(target, doc)
            print('K92_EVIDENCE_OK hb %s sha256=%s seed_repr=%s n=%s' % (
                target, s_out, doc['values']['seed_repr'], doc['assertions']['pooled_n']))
    except Stop as e:
        print('K92_EVIDENCE_STOP %s: %s' % (args.part, e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
