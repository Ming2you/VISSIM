"""WP-B1 V0-1, V0-2, V0-10 on the saved probe run (plan 7 V0; no VISSIM).

Data (read only): PR = D:\\VISSIM_runs\\20260923_obs150\\probe\\run_20260924_000152
- raw_snapshots\\t<T>__obs150_probe_001.mer: the .mer as a shared read saw it at each stop,
- vissim_eval\\obs150_probe_001.mer: the final file, err\\obs150_probe_001.err: the final .err,
- results.jsonl 'd'/'d_mid': Vehs(Current,k,All) read at the stops, gt_veh.csv: 0.1 s truth 750-900.

The probe installed its 18 points as 950001-950018; the contract range is
960001-969999. ``remap_mer`` rewrites only those point numbers (same digit
count, so every byte offset is unchanged) and the table below is the probe
config in contract form. Everything else is the probe's bytes.

The chain feeds ``obs150_capture.capture`` the snapshot of each decision stop,
exactly as the runner would call it, and the tests compare what the capture
and ``obs150_contract.assign_window`` say with the final file and the truth.
Other B1 tests (clock, head window) import the helpers of this module.
"""
from __future__ import annotations

import atexit
import csv
import json
import os
import random
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures  # noqa: E402,F401  (puts the worktree root on sys.path)
from contract_fixtures import c as oc  # noqa: E402
from evaluation.controllers import obs150_capture as cap  # noqa: E402

PR = Path(r'D:\VISSIM_runs\20260923_obs150\probe\run_20260924_000152')
PT = Path(r'D:\VISSIM-merge\tools\obs150_probe')
PROBE_CONFIG = PR.parent / 'config'
PROBE_NETWORK = PR.parent / 'network'
HAVE_PROBE = (PR / 'raw_snapshots' / 'index.jsonl').is_file() and (PROBE_CONFIG / 'detectors.csv').is_file()
SKIP_REASON = 'probe run data not present: ' + str(PR)
# V1 (integration) sets OBS150_REQUIRE_PROBE=1: the V0 probe tests must then run, not skip.
if os.environ.get('OBS150_REQUIRE_PROBE') == '1' and not HAVE_PROBE:
    raise RuntimeError('OBS150_REQUIRE_PROBE=1 but the probe run data are missing: ' + str(PR))
STEM = 'obs150_probe_001'
DECISION_STOPS = (1, 150, 300, 450, 600, 750, 900, 1050, 1200)
GT_WINDOW = (750, 900)
PROBE_KEY_OFFSET = 10000          # 9500NN -> 9600NN
_KEY = re.compile(rb'(?m)^(Data collection point\s+|[ \t]*)95(00[0-9][0-9])([:;])')


def remap_mer(data):
    """Probe point numbers 9500NN -> 9600NN in the header and the first data column."""
    return _KEY.sub(lambda m: m[1] + b'96' + m[2] + m[3], data)


def _geometry(length, lanes, offset=None):
    result = {'link_length_m': length, 'lane_count': lanes}
    if offset is not None:
        result['offset_from_end_m'] = offset
    return result


@lru_cache(maxsize=None)
def probe_table():
    """The probe's 18 points as contract DetectorRows (keys 960001-960018)."""
    manifest = json.loads((PROBE_CONFIG / 'config_manifest.json').read_text(encoding='utf-8'))
    lanes = {int(k): v['lanes'] for k, v in manifest['geometry'].items()}
    rows = []
    with open(PROBE_CONFIG / 'detectors.csv', newline='', encoding='ascii') as handle:
        for r in csv.DictReader(handle):
            key = int(r['dcp_no']) + PROBE_KEY_OFFSET
            link, lane = int(r['link']), int(r['lane'])
            pos, length = round(float(r['pos_request']), 6), round(float(r['link_length_m']), 6)
            kind = r['role']
            if kind == 'head':
                match = re.fullmatch(r'head([0-9]+)\|SC([0-9]+)-SG([0-9]+)', r['ref'])
                spec = ('head', f'{match[1]}|{match[2]}-{match[3]}', 'exact', 'at', (), _geometry(length, lanes[link]))
            elif kind == 'ramp_arrival':
                spec = ('ramp_arrival', f'RM_C{link}', 'exact', 'down',
                        (oc.SegmentPiece(link, 0.0, pos, (lane,)),), _geometry(length, lanes[link]))
            elif kind == 'off_exit':
                offset = round(length - pos, 6)
                spec = ('x10643_exit', str(link), 'end_minus', 'up',
                        (oc.SegmentPiece(link, pos, length, (lane,)),), _geometry(length, lanes[link], offset))
            elif kind == 'destination':
                spec = ('destination', str(link), 'exact', 'down',
                        (oc.SegmentPiece(link, 0.0, pos, (lane,)),), _geometry(length, lanes[link]))
            elif kind == 'origin_station':
                spec = ('source', 'FW_W', 'exact', 'down',
                        (oc.SegmentPiece(link, 0.0, pos, (lane,)),), _geometry(length, lanes[link]))
            else:
                raise AssertionError('unknown probe role ' + kind)
            role, ref, mode, orientation, segment, geometry = spec
            rows.append(oc.DetectorRow(key, key, role, ref, link, lane, pos, mode, orientation,
                                       oc.expected_boundary_ref(role, ref), segment, geometry))
    return oc.validate_detector_rows(rows)


@lru_cache(maxsize=None)
def results():
    """{T: {dcm: Vehs(Current,k,All)}} at decision stops and {T: {dcm: (k_open, open count)}} at mid stops."""
    closed, opened = defaultdict(dict), defaultdict(dict)
    for line in (PR / 'results.jsonl').read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        dcm = record.get('dcm')
        if not isinstance(dcm, int) or not 950001 <= dcm <= 950018:
            continue
        key = str(dcm + PROBE_KEY_OFFSET)
        if record['check'] == 'd' and float(record['sim_sec']).is_integer():
            closed[int(record['sim_sec'])][key] = record['vehs_k']
        elif record['check'] == 'd_mid':
            opened[int(record['sim_sec'])][key] = (record['k_open'], record['vehs_open'])
    return dict(closed), dict(opened)


def cumulative_vehs():
    """{T: C_k} over the decision stops (C at t=1 is the open interval count, 0 here: first entry 3.21 s).

    The probe's source station is at 40 m. The operational one at 1.0 m can count 1 at t=1
    with no .mer row yet; test_capture_t1 covers that decision.
    """
    closed, _ = results()
    keys = [str(r.dcm_no) for r in probe_table()]
    total = {k: 0 for k in keys}
    out = {1: dict(total)}
    for t in DECISION_STOPS[1:]:
        for k in keys:
            total[k] += closed[t][k]
        out[t] = dict(total)
    return out


@lru_cache(maxsize=None)
def snapshot_bytes(tag):
    return remap_mer((PR / 'raw_snapshots' / f'{tag}__{STEM}.mer').read_bytes())


@lru_cache(maxsize=None)
def final_mer_bytes():
    return remap_mer((PR / 'vissim_eval' / f'{STEM}.mer').read_bytes())


@lru_cache(maxsize=None)
def final_err_bytes():
    return (PR / 'err' / f'{STEM}.err').read_bytes()


def err_prefix_at(sim_sec):
    """The final .err up to the first line that names a Simulation second after sim_sec."""
    data = final_err_bytes()
    offset = 0
    for raw in data.splitlines(keepends=True):
        match = cap.ERR_SIM_SECOND.search(raw.decode('cp949'))
        if match and float(match[1]) > sim_sec:
            break
        offset += len(raw)
    return data[:offset]


def scan_mer(data, table):
    """(entry rows by dcp in ordinal order, all stored rows, max time of all rows) of the complete lines."""
    header = cap._mer_header(_BytesFile(data), len(data))
    end = data.rfind(b'\n') + 1
    records = {r.dcp_no: 0 for r in table}
    if header['data_start'] is None or end <= header['data_start']:
        return defaultdict(list), [], None
    rows, max_t = cap.parse_mer_rows(data[header['data_start']:end], header['columns'], 0,
                                     set(records), records)
    entries = defaultdict(list)
    for row in rows:
        if row.ordinal is not None:
            entries[row.dcp].append(row)
    return entries, rows, max_t


class _BytesFile:
    """Just enough of a binary file for obs150_capture._mer_header."""
    def __init__(self, data):
        self.data, self.position = data, 0

    def seek(self, position, whence=0):
        self.position = position if whence == 0 else len(self.data) + position

    def read(self, size=-1):
        end = len(self.data) if size < 0 else self.position + size
        block = self.data[self.position:end]
        self.position += len(block)
        return block


@lru_cache(maxsize=None)
def final_scan():
    return scan_mer(final_mer_bytes(), probe_table())


def new_workspace(prefix):
    root = Path(tempfile.mkdtemp(prefix=prefix))
    atexit.register(shutil.rmtree, root, True)
    for name in ('vissim_eval', 'network', 'decisions'):
        (root / name).mkdir()
    return root


def capture_stop(root, sim_sec, mer_bytes, err_bytes, table):
    """Write the files as VISSIM holds them at the stop, then run the capture like the VBS does."""
    (root / 'vissim_eval' / f'{STEM}.mer').write_bytes(mer_bytes)
    err_path = root / 'network' / f'{STEM}.err'
    if err_bytes is not None:
        err_path.write_bytes(err_bytes)
    return cap.capture(root / 'vissim_eval', err_path, root / 'decisions' / 'obs150', sim_sec, table)


@lru_cache(maxsize=None)
def probe_chain(last=1200):
    """Run the capture at every decision stop up to `last` on the probe snapshots: (root, {T: meta})."""
    root = new_workspace('obs150_b1_chain_')
    metas = {}
    for t in DECISION_STOPS:
        if t > last:
            break
        metas[t] = capture_stop(root, t, snapshot_bytes(f't{t}'), err_prefix_at(t), probe_table())
    return root, metas


def chain_chunk(root, meta):
    return oc.load_mer_chunk(root / 'decisions' / Path(*meta['mer']['chunk'].split('/')), meta['mer']['chunk_sha256'])


def bundle_obs(sim_sec, meta):
    """The raw fields assign_window/build read, from the probe truth and the capture meta."""
    closed, _ = results()
    cum = cumulative_vehs()
    detectors = {k: 0 for k in cum[1]} if sim_sec == 1 else dict(closed[sim_sec])
    return {'sim_sec': sim_sec, 'detectors': detectors, 'detectors_cum': dict(cum[sim_sec]), 'mer': meta['mer']}


@lru_cache(maxsize=None)
def ground_truth_events():
    """check_probe.gt_crossings over gt_veh.csv for the 18 points: [(dcp, veh, t_cross, t_step_end, kind)]."""
    sys.dont_write_bytecode = True
    if str(PT) not in sys.path:
        sys.path.insert(0, str(PT))
    import check_probe
    frames = check_probe.load_gt(PR)
    manifest = json.loads((PROBE_CONFIG / 'config_manifest.json').read_text(encoding='utf-8'))
    detectors = [dict(dcp=r.dcp_no, link=r.link, lane=r.lane, pos=r.pos) for r in probe_table()]
    events, _, _ = check_probe.gt_crossings(frames, detectors, manifest['geometry'])
    return tuple(e for e in events if GT_WINDOW[0] < e[3] <= GT_WINDOW[1] + 1e-9)


@lru_cache(maxsize=None)
def ground_truth_signal():
    """{'<sc>-<sg>': {t10: STATE}}: the SigState read at each 0.1 s pause 750.0-900.0 (gt_sig.csv)."""
    out = defaultdict(dict)
    with open(PR / 'gt_sig.csv', newline='', encoding='latin-1') as handle:
        for r in csv.DictReader(handle):
            out[f"{r['sc']}-{r['sg']}"][int(r['t10'])] = r['sig_state'].strip().upper()
    return dict(out)


@lru_cache(maxsize=None)
def probe_sig_files():
    """{sc: (path, progNo)} of the native probe SCs from the probe inpx (supplyFile2 #data#...)."""
    out = {}
    for _, node in ET.iterparse(PROBE_NETWORK / 'obs150_probe.inpx'):
        if node.tag == 'signalController' and node.get('no') in ('1004', '5'):
            name = node.get('supplyFile2')
            assert name.startswith('#data#'), name
            out[node.get('no')] = (PROBE_NETWORK / name[len('#data#'):], int(node.get('progNo')))
        if node.tag == 'signalControllers':
            break
    return out


@lru_cache(maxsize=None)
def meter_writes():
    """The runner-side write log of SC9106 SG1 in 750-900 (results 'f_write': readback-confirmed)."""
    out = []
    for line in (PR / 'results.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            record = json.loads(line)
            if record['check'] == 'f_write':
                assert record['ok'] and record['readback'] == record['state']
                out.append([int(record['t10']) // 10, str(record['sc']), str(record['sg']), 'write', record['state']])
    return out


def step_index_range(t):
    """Steps (s-0.1, s] (as 10 s) a .mer time rounded to 0.01 can belong to."""
    import math
    lo = math.ceil(round((t - oc.BOUNDARY_EPS_S) * 10, 6))
    hi = math.ceil(round((t + oc.BOUNDARY_EPS_S) * 10, 6))
    return lo, hi


# ==========================================================================
@unittest.skipUnless(HAVE_PROBE, SKIP_REASON)
class V01OrdinalAssignment(unittest.TestCase):
    """V0-1: the ordinal assignment reproduces Vehs(Current,k,All) for 18 points, k=1..8."""

    def test_table_is_contract_valid_and_matches_the_mer_header(self):
        rows = probe_table()
        self.assertEqual(len(rows), 18)
        self.assertEqual(oc.parse_detector_csv(oc.format_detector_csv(rows)), rows)
        header = cap._mer_header(_BytesFile(final_mer_bytes()), len(final_mer_bytes()))
        cap._check_header_points(header['points'], rows, True)

    def test_capture_chain_meta_and_index(self):
        root, metas = probe_chain()
        self.assertEqual(tuple(metas), DECISION_STOPS)
        index = oc.validate_mer_index(json.loads((root / 'decisions' / 'obs150' / 'mer_index.json').read_text()))
        previous_end = 0
        for t, meta in metas.items():
            oc.validate_capture_meta(meta, t)
            with self.subTest(t=t):
                self.assertEqual((root / 'decisions' / Path(*oc.capture_meta_path(t).split('/'))).read_bytes(),
                                 oc.capture_meta_bytes(meta, t))
                self.assertEqual(index[t]['entry_sha256'], meta['mer']['index_sha256'])
                self.assertEqual(meta['mer']['byte_start'], previous_end)
                previous_end = meta['mer']['byte_end']
                oc.load_err_chunk(root / 'decisions' / Path(*meta['err']['chunk'].split('/')), meta['err']['chunk_sha256'])
        # the chunks together are exactly the stored rows of the file up to the last stop
        stored = [row for t in DECISION_STOPS for row in chain_chunk(root, metas[t])]
        _, final_rows, _ = final_scan()
        self.assertEqual(stored, [r for r in final_rows if r.seq <= stored[-1].seq])
        self.assertEqual(metas[1200]['mer']['records_cum_by_dcp'],
                         {str(r.dcm_no): len(final_scan()[0][r.dcp_no]) for r in probe_table()})

    def test_ordinals_reproduce_vehs_for_every_point_and_window(self):
        root, metas = probe_chain()
        entries, _, _ = final_scan()
        closed, _ = results()
        cum = cumulative_vehs()
        differences, outside = 0, 0
        for t in DECISION_STOPS[1:]:
            assignment = oc.assign_window(bundle_obs(t, metas[t]), chain_chunk(root, metas[t]))
            self.assertTrue(assignment.lag_ok)
            for r in probe_table():
                key = str(r.dcm_no)
                c_prev, c_now = cum[t][key] - closed[t][key], cum[t][key]
                by_ordinal = [x for x in entries[r.dcp_no] if c_prev < x.ordinal <= c_now]
                by_time = [x for x in entries[r.dcp_no] if t - 150 < x.t_entry <= t]
                outside += sum(not (t - 150 - oc.BOUNDARY_EPS_S <= x.t_entry <= t + oc.BOUNDARY_EPS_S)
                               for x in by_ordinal)
                differences += abs(len(by_time) - closed[t][key]) + (by_time != by_ordinal)
                # rows of the interval present at T are exactly the capture's window entries
                self.assertEqual(list(assignment.entries[r.dcp_no]),
                                 [x for x in by_ordinal if x.ordinal <= metas[t]['mer']['records_cum_by_dcp'][key]])
                self.assertEqual(assignment.tails[r.dcp_no] + len(assignment.entries[r.dcp_no]), closed[t][key])
        self.assertEqual((differences, outside), (0, 0))

    def test_step_order_premise_holds_in_the_final_file(self):
        """NEW-5: steps are written in order (rows inside one step are in vehicle order)."""
        header = cap._mer_header(_BytesFile(final_mer_bytes()), len(final_mer_bytes()))
        data = final_mer_bytes()[header['data_start']:]
        running_lo, violations, rows = 0, 0, 0
        for line in data.splitlines():
            parts = [p.strip() for p in line.decode('ascii').split(';')]
            times = [float(v) for v in (parts[1], parts[2]) if v != '-1.00']
            lo, hi = step_index_range(max(times))
            violations += hi < running_lo
            running_lo = max(running_lo, lo)
            rows += 1
        self.assertGreater(rows, 100000)
        self.assertEqual(violations, 0)
        # at most one entry per point and step (the ordinal = time order premise of B3)
        entries, _, _ = final_scan()
        same_step = 0
        for rows_of_point in entries.values():
            steps = [step_index_range(x.t_entry) for x in rows_of_point]
            same_step += sum(a == b and a[0] == a[1] for a, b in zip(steps, steps[1:]))
            self.assertEqual([x.t_entry for x in rows_of_point], sorted(x.t_entry for x in rows_of_point))
        self.assertEqual(same_step, 0)

    def test_window_six_vehicles_equal_the_ground_truth(self):
        """Vehicle level against gt_veh.csv (PRB f: one GT lane-change ambiguity on link 26, station exact)."""
        entries, _, _ = final_scan()
        closed, _ = results()
        cum = cumulative_vehs()
        events = ground_truth_events()
        station_ours, station_truth = set(), set()
        for r in probe_table():
            key = str(r.dcm_no)
            ours = {x.veh for x in entries[r.dcp_no] if cum[900][key] - closed[900][key] < x.ordinal <= cum[900][key]}
            truth = {e[1] for e in events if e[0] == r.dcp_no}
            ambiguous = {e[1] for e in events if e[0] == r.dcp_no and e[4] == 'ambiguous_lane_change'}
            with self.subTest(point=r.dcp_no):
                self.assertEqual(len(ours), closed[900][key])
                self.assertEqual(ours ^ truth, (truth - ours) & ambiguous)
            if r.role == 'source':
                station_ours |= ours
                station_truth |= truth
        self.assertEqual(station_ours, station_truth)


@unittest.skipUnless(HAVE_PROBE, SKIP_REASON)
class V02LagRule(unittest.TestCase):
    """V0-2: at every stop copy, the lag rule's verdict and the tail position agree with the final file."""

    def stops(self):
        """(tag, T, C(T) by dcm) for every snapshot with a COM-read cumulative count."""
        closed, opened = results()
        cum = cumulative_vehs()
        out = [('t1', 1, cum[1])] + [(f't{t}', t, cum[t]) for t in DECISION_STOPS[1:]]
        previous_stop = {37: 1, 451: 450, 1112: 1050}
        for t, values in sorted(opened.items()):
            # an open interval reads the count since its start: (0, 37], (450, 451], (1050, 1112]
            self.assertEqual({v[0] for v in values.values()}, {oc.window_of_time(t)})
            base = cum[previous_stop[t]] if t != 37 else {k: 0 for k in cum[1]}
            tag = 't1111.5' if t == 1112 else f't{t}'
            out.append((tag, t, {k: base[k] + values[k][1] for k in base}))
        return out

    def test_rule_verdict_and_tail_position(self):
        final_entries, _, _ = final_scan()
        exercised = 0
        for tag, t, c_now in self.stops():
            entries, _, max_t_any = scan_mer(snapshot_bytes(tag), probe_table())
            tails = {}
            for r in probe_table():
                present = len(entries[r.dcp_no])
                tails[r.dcp_no] = c_now[str(r.dcm_no)] - present
                self.assertGreaterEqual(tails[r.dcp_no], 0, (tag, r.dcp_no))
                self.assertEqual(entries[r.dcp_no], final_entries[r.dcp_no][:present])
            sum_tail = sum(tails.values())
            rule = oc.lag_ok(max_t_any, t, sum_tail)
            tail_times = [x.t_entry for r in probe_table()
                          for x in final_entries[r.dcp_no][len(entries[r.dcp_no]):c_now[str(r.dcm_no)]]]
            truth = all(t - 1 - oc.BOUNDARY_EPS_S < x <= t + oc.BOUNDARY_EPS_S for x in tail_times)
            with self.subTest(stop=tag, sum_tail=sum_tail, max_t_any=max_t_any):
                self.assertEqual(len(tail_times), sum_tail)
                self.assertTrue(rule)            # PRB h: the .mer lags at most 0.81 s
                self.assertTrue(truth)           # and then every tail passage lies in (T-1, T]
            exercised += sum_tail > 0
        self.assertGreater(exercised, 0)         # t150: one tail entry at 149.78, file max 149.19

    def test_lagging_file_raises_ObsLagError(self):
        """The t900 copy cut before the last step with a point entry: tail > 0 and max_t_any <= T-1+0.005."""
        root = new_workspace('obs150_b1_lag_')
        for t in DECISION_STOPS[:6]:
            capture_stop(root, t, snapshot_bytes(f't{t}'), err_prefix_at(t), probe_table())
        data = snapshot_bytes('t900')
        entries, _, _ = scan_mer(data, probe_table())
        last = max(x.t_entry for rows in entries.values() for x in rows)
        cut_time = min(898.0, last - 0.2)
        header = cap._mer_header(_BytesFile(data), len(data))
        offset = header['data_start']
        for raw in data[offset:].splitlines(keepends=True):
            parts = [p.strip() for p in raw.decode('ascii').split(';')]
            if max(float(v) for v in (parts[1], parts[2]) if v != '-1.00') > cut_time:
                break
            offset += len(raw)
        meta = capture_stop(root, 900, data[:offset], err_prefix_at(900), probe_table())
        self.assertLessEqual(meta['mer']['max_t_any'], 900 - oc.LAG_MARGIN_S + oc.BOUNDARY_EPS_S)
        with self.assertRaises(oc.ObsLagError):
            oc.assign_window(bundle_obs(900, meta), chain_chunk(root, meta))


@unittest.skipUnless(HAVE_PROBE, SKIP_REASON)
class V010ErrIncrements(unittest.TestCase):
    """V0-10: .err captured at arbitrary byte cuts gives the same rows and the same 12 removals."""

    TABLE_EXTRA = ('headfree', '71', 71, 1, 78.980074)   # a synthetic offset boundary on link 71 [0, 78.98)

    def table(self):
        role, ref, link, lane, pos = self.TABLE_EXTRA
        extra = oc.DetectorRow(960019, 960019, role, ref, link, lane, pos, 'exact', 'down',
                               oc.expected_boundary_ref(role, ref), (oc.SegmentPiece(link, 0.0, pos, None),),
                               _geometry(82.602857, 5))
        return oc.validate_detector_rows(probe_table() + (extra,))

    def header_only_mer(self, table):
        lines = [b'', b'Data Collection (Raw Data)', b'']
        for r in table:
            lines.append(b'Data collection point %8d: Link %5d lane %d at %11.3f m.' % (r.dcp_no, r.link, r.lane, r.pos))
        lines += [b'', b' Measurem.;  t(Entry);   t(Exit);    VehNo; Vehicle type;    Line; v[km/h]; b[m/s2];'
                        b'   Occ; Pers; tQueue; VehLength[m];']
        return b'\r\n'.join(lines) + b'\n'

    def cuts(self, data):
        rng = random.Random(150)
        cuts = {rng.randrange(1, len(data)) for _ in range(25)}
        crlf = [m.start() + 1 for m in re.finditer(rb'\r\n', data)]
        cuts |= {crlf[3], crlf[40], crlf[-2]}                           # between CR and LF
        multibyte = [m.start() + 1 for m in re.finditer(rb'[\x80-\xff]{2}', data)]
        cuts |= set(multibyte[:3]) | set(multibyte[-3:])               # inside a cp949 character
        line_starts = [m.end() for m in re.finditer(rb'\n', data)]
        cuts |= {line_starts[10], line_starts[68]}                       # exactly at line starts
        return sorted(cuts | {len(data)})

    def test_same_rows_at_any_cut(self):
        data = final_err_bytes()
        table = self.table()
        full, complete, full_max = cap.parse_err_increment(data, 0)
        self.assertEqual(complete, len(data))
        removals = [r for r in full if r['kind'] == 'lane_change_removal']
        self.assertEqual(len(removals), 12)
        root = new_workspace('obs150_b1_err_')
        mer = self.header_only_mer(table)
        cuts = self.cuts(data)
        self.assertGreater(len(cuts), 30)
        rows, meta, t, previous = [], None, oc.FIRST_DECISION_SEC, b''

        def stop(t, prefix):
            meta = capture_stop(root, t, mer, prefix, table)
            err = meta['err']
            return meta, oc.load_err_chunk(root / 'decisions' / Path(*err['chunk'].split('/')), err['chunk_sha256'])

        for cut in cuts:
            # A stop never sees a Simulation second after itself (the capture refuses that file), so
            # each cut is captured at the first decision stop not before its last complete line;
            # the stops in between read the previous cut again (no new bytes).
            need = cap.parse_err_increment(data[:cut], 0)[2] or 0
            while t < need:
                meta, chunk = stop(t, previous)
                self.assertEqual(meta['err']['byte_end'] + meta['err']['partial_tail_bytes'], len(previous))
                rows += chunk
                t = oc.DECISION_INTERVAL_SEC if t == oc.FIRST_DECISION_SEC else t + oc.DECISION_INTERVAL_SEC
            meta, chunk = stop(t, data[:cut])
            err = meta['err']
            with self.subTest(cut=cut):
                self.assertEqual(err['byte_end'] + err['partial_tail_bytes'], cut)
                self.assertTrue(err['byte_end'] == 0 or data[err['byte_end'] - 1:err['byte_end']] == b'\n')
                self.assertLessEqual(err['max_sim_sec'] or 0, t)
            rows += chunk
            previous = data[:cut]
            t = oc.DECISION_INTERVAL_SEC if t == oc.FIRST_DECISION_SEC else t + oc.DECISION_INTERVAL_SEC
        self.assertEqual(rows, full)
        self.assertEqual(meta['err']['max_sim_sec'], full_max)
        self.assertEqual(full_max, 1192.6)
        expected = {ref: len(oc.removals_in_boundary(full, group))
                    for ref, group in oc.group_boundaries(table).items() if group[0].orientation != 'at'}
        self.assertEqual(meta['err']['removals_cum_by_boundary'], expected)
        # link 71 removals at 73.4, 71.9, 76.2, 73.4, 76.2 m (vehicles 1485, 2063, 3689, 191, 6341)
        self.assertEqual(expected['headfree:71'], 5)

    def test_chain_totals_match_the_final_err(self):
        root, metas = probe_chain()
        rows = []
        for t in DECISION_STOPS:
            err = metas[t]['err']
            rows += oc.load_err_chunk(root / 'decisions' / Path(*err['chunk'].split('/')), err['chunk_sha256'])
        full, _, _ = cap.parse_err_increment(final_err_bytes(), 0)
        self.assertEqual(rows, full)
        self.assertEqual(sum(metas[t]['err']['removals'] for t in DECISION_STOPS), 12)


if __name__ == '__main__':
    unittest.main()
