"""K9-2 bundle 1 evidence builder: the single source of the K9-2 bundle-1 values (K8_PREDECLARATION_AMENDMENT_24,
fixed version sha d46db6dc...; user decisions D-K9-34..36 of K9_1_J1_NOTES_20261013.md).  Diagnostics only; the
runtime reads the committed JSON (sha-pinned by the tuning key), never this script.

    python -B diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py w [--check] [--root R] [--out-dir D]

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


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('part', choices=('w',))
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
    except Stop as e:
        print('K92_EVIDENCE_STOP %s: %s' % (args.part, e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
