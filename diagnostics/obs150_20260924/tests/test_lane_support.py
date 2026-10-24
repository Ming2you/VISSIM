"""Support for the WP-B2 tests (no tests here): probe-run loaders and a synthetic disk bundle.

Probe run (PR, read-only): D:\\VISSIM_runs\\20260923_obs150\\probe\\run_20260924_000152, the
v2 network f475ce42 at SimRes 10 with 0.1 s ground truth over (750, 900]. Its 18
probe points 950001-950018 are renumbered 960001-960018 (the contract key range)
and described as contract DetectorRows; the .mer chunk of the decision T=900 is
cut exactly as obs150_capture would: complete lines between the t750 and t900
raw copies, file-wide seq, per-point entry ordinals from the file start.

The synthetic bundle writes a complete obs150-raw/v1 state (chunks, sha-chained
mer index, frames, provenance) for the contract_fixtures table so the whole
derive -> merge -> lane_observation path runs on disk.
"""
from __future__ import annotations

from collections import defaultdict
import copy
import csv
import dataclasses
import functools
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c  # noqa: E402

ROOT = fx.ROOT
PROBE = Path(r'D:\VISSIM_runs\20260923_obs150\probe\run_20260924_000152')
NET = Path(r'D:\VISSIM_runs\20260923_stage1\s31_v2nc\prepared\network\baseline_s31_v2nc.inpx')
OLD_STATE_900 = Path(r'D:\VISSIM_runs\20260923_sdmpc\sdmpc_lp_9000c\decisions_sdmpc_lp_9000c\state_000900.json')
B110_OBSERVATIONS = Path(r'D:\VISSIM-merge\sim3\diagnostics\demand_sweep\user_native_20260914'
                         r'\metanet_calibration_v1\res10_b110_20260923\observations\s31_v2nc_observations')
KEY_SHIFT = 10000          # probe 9500xx -> contract 9600xx
GT_ROUTE_DEST = {1: 10635, 2: 10634, 3: 10642}   # check_probe.ROUTE_DEST (RD 1126, inpx)


def probe_available():
    return PROBE.is_dir() and NET.is_file()


def sha(data):
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Probe: detector table, .mer, frames, .err, detector values, ground truth
# --------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def network():
    from evaluation.controllers import obs150_observation as ob
    return ob.InpxNetwork(NET)


def probe_rows():
    """The 18 probe points as contract DetectorRows (keys +10000)."""
    net = network()
    specs = []
    for line in (PROBE.parent / 'config' / 'detectors.csv').read_text(encoding='ascii').splitlines()[1:]:
        dcp, _, role, ref, link, lane, pos, mode, _ = line.split(',')
        specs.append((int(dcp), role, ref, int(link), int(lane), float(pos), mode))
    rows = []
    for dcp, role, ref, link, lane, pos, mode in specs:
        x = net.links[link]
        geometry = {'link_length_m': x.length_m, 'lane_count': x.lanes}
        key = dcp + KEY_SHIFT
        if role == 'head':
            head, sgkey = ref[len('head'):].split('|')
            sc, sg = sgkey[len('SC'):].split('-SG')
            role, ref = ('meter_head' if sc.startswith('91') else 'head'), f'{head}|{sc}-{sg}'
            segment, orientation = (), 'at'
        elif role == 'ramp_arrival':
            ref, orientation = 'RM_C%d' % link, 'down'
            segment = (c.SegmentPiece(link, 0.0, pos, (lane,)),)
            geometry['linkeval_segment_m'] = x.eval_segment_m
        elif role == 'off_exit':
            role, ref, orientation = 'x10643_exit', '10643', 'up'
            geometry['offset_from_end_m'] = round(x.length_m - pos, 6)
            pos = round(x.length_m - geometry['offset_from_end_m'], 6)
            segment = (c.SegmentPiece(link, pos, round(x.length_m + 5e-7, 6), (lane,)),)
        elif role == 'destination':
            ref, orientation = str(link), 'down'
            segment = (c.SegmentPiece(link, 0.0, pos, (lane,)),)
        elif role == 'origin_station':
            role, ref, orientation = 'source', 'FW_W', 'down'
            segment = (c.SegmentPiece(link, 0.0, pos, (lane,)),)
        else:
            raise AssertionError(role)
        rows.append(c.DetectorRow(key, key, role, ref, link, lane, pos, mode, orientation,
                                  c.expected_boundary_ref(role, ref), segment, geometry))
    return c.validate_detector_rows(rows)


def _mer_bytes(tag):
    data = (PROBE / 'raw_snapshots' / f'{tag}__obs150_probe_001.mer').read_bytes()
    return data[:data.rfind(b'\n') + 1]


@functools.lru_cache(maxsize=4)
def probe_mer(end_tag='t900', start_tag='t750'):
    """(chunk MerRows, records_cum_by_dcp, max_t_any) of the capture at end_tag (from start_tag's end)."""
    full, before = _mer_bytes(end_tag), _mer_bytes(start_tag)
    assert full.startswith(before), 'the .mer is append-only'
    keys = {r.dcp_no for r in probe_rows()}
    lines = full.splitlines(keepends=True)
    offset, columns = 0, None
    for i, raw in enumerate(lines):
        offset += len(raw)
        if b'Measurem.' in raw:
            columns = [p.strip().decode('ascii') for p in raw.split(b';')][:-1]
            first = i + 1
            break
    index = {name: columns.index(name) for name in ('Measurem.', 't(Entry)', 't(Exit)', 'VehNo', 'Vehicle type',
                                                    'v[km/h]', 'VehLength[m]')}
    records = {k: 0 for k in keys}
    rows, max_t, seq = [], None, 0
    for raw in lines[first:]:
        start = offset
        offset += len(raw)
        parts = [p.strip() for p in raw.decode('ascii').split(';')]
        t_entry, t_exit = float(parts[index['t(Entry)']]), float(parts[index['t(Exit)']])
        t_entry = None if t_entry == -1.0 else t_entry
        t_exit = None if t_exit == -1.0 else t_exit
        latest = max(t for t in (t_entry, t_exit) if t is not None)
        max_t = latest if max_t is None else max(max_t, latest)
        dcp = int(parts[index['Measurem.']]) + KEY_SHIFT
        if dcp in keys:
            ordinal = None
            if t_entry is not None:
                records[dcp] += 1
                ordinal = records[dcp]
            if start >= len(before):
                rows.append(c.MerRow(seq, dcp, t_entry, t_exit, int(parts[index['VehNo']]),
                                     int(parts[index['Vehicle type']]), float(parts[index['v[km/h]']]),
                                     float(parts[index['VehLength[m]']]), ordinal))
        seq += 1
    return tuple(rows), {str(k): v for k, v in sorted(records.items())}, max_t


@functools.lru_cache(maxsize=1)
def probe_vehs():
    """{t: {dcm (contract key) str: Vehs(Current,k,All)}} from the probe results (check d)."""
    document = json.loads((PROBE / 'results.json').read_text(encoding='utf-8'))
    out = defaultdict(dict)
    for record in document['checks']['d']:
        out[int(record['t'])][str(int(record['dcm']) + KEY_SHIFT)] = record['vehs_k']
    return dict(out)


def probe_obs(t=900):
    """The obs150 fields assign_window/evaluate_boundaries read, for the probe points at T."""
    vehs = probe_vehs()
    keys = [str(r.dcm_no) for r in probe_rows()]
    detectors = {k: vehs[t][k] for k in keys}
    cumulative = {k: sum(vehs[s][k] for s in vehs if s <= t) for k in keys}
    rows, records, max_t = probe_mer(f't{t}', f't{t - 150}')
    return {'sim_sec': t, 'detectors': detectors, 'detectors_cum': cumulative,
            'mer': {'records_cum_by_dcp': records, 'max_t_any': max_t}}, rows


def _int(text):
    return int(float(text)) if text not in ('', None) else None


@functools.lru_cache(maxsize=4)
def probe_frame(t):
    """snapshots/snap_<t>.csv as lane-plant-frame/v1."""
    vehicles = []
    with open(PROBE / 'snapshots' / f'snap_{t}.csv', newline='', encoding='latin-1') as handle:
        for r in csv.DictReader(handle):
            link, lane = r['Lane'].rsplit('-', 1)
            vehicles.append([int(r['No']), int(link), int(lane), float(r['Pos']), max(0.0, float(r['Speed'])),
                             float(r['Length']), _int(r['RoutDecNo']), _int(r['RouteNo']), r['RoutDecType'] or None,
                             _int(r['NextLink\\No']), None, None, None, None, None])
    frame = {'schema': c.FRAME_SCHEMA, 'complete': True, 'time_s': t, 'run_id': 'probe', 'vehicles': vehicles}
    c.validate_frame(frame, t)
    return frame


@functools.lru_cache(maxsize=1)
def probe_err_rows():
    """The probe .err parsed by ERRP and normalized as obs150 err chunk rows."""
    from diagnostics.capture_native_runtime_errors import parse_bytes
    parsed = parse_bytes((PROBE / 'err' / 'obs150_probe_001.err').read_bytes())
    assert not parsed['unparsed_removal_lines']
    rows = []
    for event in parsed['events']:
        row = {k: v for k, v in event.items() if k != 'line_number'}
        if row['kind'] in ('lane_change_removal', 'ignored_static_routing', 'ignored_desired_speed'):
            row['link'] = int(row['link'])
        rows.append(c.validate_err_row(row))
    return tuple(rows)


@functools.lru_cache(maxsize=1)
def gt_frames():
    """{t10: {veh: (link, lane, pos, speed, route)}} over the ground-truth window (tracked links)."""
    frames = defaultdict(dict)
    with open(PROBE / 'gt_veh.csv', newline='', encoding='latin-1') as handle:
        reader = csv.reader(handle)
        next(reader)
        for row in reader:
            link, lane = row[2].rsplit('-', 1)
            frames[int(row[0])][int(float(row[1]))] = (int(link), int(lane), float(row[3]), float(row[4] or 0),
                                                        _int(row[5]))
    return dict(frames)


def gt_10643_exits():
    """{(veh, lane, destination)} of vehicles leaving 10643 in (750, 900] (check_probe (f) definition)."""
    frames = gt_frames()
    times = sorted(frames)
    out = set()
    for a, b in zip(times, times[1:]):
        for veh, pa in frames[a].items():
            if pa[0] == 10643:
                pb = frames[b].get(veh)
                if pb is None or pb[0] != 10643:
                    out.add((veh, pa[1], GT_ROUTE_DEST.get(pa[4])))
    return out


def gt_first_appearances(link, start10=7500, end10=9000):
    """Vehicles first seen on link (inserted there) in (start, end]."""
    frames = gt_frames()
    seen, out = set(frames[start10]), set()
    for t in sorted(frames):
        if t <= start10 or t > end10:
            continue
        for veh, p in frames[t].items():
            if veh not in seen:
                seen.add(veh)
                if p[0] == link:
                    out.add(veh)
    return out


def gt_entries(link, start10=7500, end10=9000):
    """Vehicles entering link (absent from it in the previous 0.1 s frame) in (start, end]."""
    frames = gt_frames()
    times = sorted(t for t in frames if start10 <= t <= end10)
    count = 0
    for a, b in zip(times, times[1:]):
        for veh, pb in frames[b].items():
            pa = frames[a].get(veh)
            if pb[0] == link and (pa is None or pa[0] != link):
                count += 1
    return count


def probe_context():
    """A duck-typed context with the fields the 10643 ledger and source identity read."""
    from types import SimpleNamespace
    from evaluation.controllers import obs150_observation as ob
    rows = probe_rows()
    net = network()
    return SimpleNamespace(
        detectors=rows, boundaries=c.group_boundaries(rows), x10643_exit_ref='x10643_exit:10643',
        destination_refs={x: 'destination:' + x for x in c.DESTINATION_CONNECTORS_10643},
        lane_map_10643=ob.lane_map_10643(net), route_destinations_10643=ob.route_destinations_10643(net))


# --------------------------------------------------------------------------
# Synthetic world on the contract_fixtures table
# --------------------------------------------------------------------------
def fixture_rows():
    return fx.detector_rows()


def key_of(rows, ref, lane):
    matches = [r for r in rows if r.boundary_ref == ref and r.lane == lane]
    assert len(matches) == 1, (ref, lane)
    return matches[0].dcp_no


# The native SCs of the fixture signal log (1004-2, 1004-5, 5-2): program 1 as
# (offset_s, cycle_s, {sg: green spans [a, b) in program seconds}). 1004 is the
# contract_fixtures program; write_bundle puts real .sig files of these programs
# into the run network folder, so derive re-checks the copies (CONTRACT 6, B4).
FIXTURE_SIGS = {'1004': (75, 150, {'2': ((0, 40),), '5': ((50, 90),)}),
                '5': (36, 150, {'2': ((0, 47),)})}
FIXTURE_NETWORK_NAME = 'fixture.inpx'


def fixture_sig_bytes(sc):
    """A minimal real .sig (Red-Green sequence, program 1) of FIXTURE_SIGS[sc]; LF, ASCII."""
    offset, cycle, green = FIXTURE_SIGS[sc]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<sc version="201602" id="{sc}" name="" frequency="1" steps="0" defaultIntergreenMatrix="0">',
             '  <signaldisplays>',
             '    <display id="1" name="Red" state="RED" />',
             '    <display id="3" name="Green" state="GREEN" />',
             '  </signaldisplays>',
             '  <signalsequences>',
             '    <signalsequence id="2" name="Red-Green">',
             '      <state display="1" isFixedDuration="false" isClosed="true" defaultDuration="1000" />',
             '      <state display="3" isFixedDuration="false" isClosed="false" defaultDuration="5000" />',
             '    </signalsequence>',
             '  </signalsequences>',
             '  <sgs>']
    lines += [f'    <sg id="{sg}" name="SG{sg}" defaultSignalSequence="2" />' for sg in sorted(green, key=int)]
    lines += ['  </sgs>', '  <progs>',
              f'    <prog id="1" cycletime="{cycle * 1000}" switchpoint="0" offset="{offset * 1000}" name="fixture">',
              '      <sgs>']
    for sg in sorted(green, key=int):
        lines += [f'        <sg sg_id="{sg}" signal_sequence="2">', '          <cmds>']
        for a, b in green[sg]:
            lines += [f'            <cmd display="3" begin="{a * 1000}" />',
                      f'            <cmd display="1" begin="{b * 1000}" />']
        lines += ['          </cmds>', '        </sg>']
    lines += ['      </sgs>', '    </prog>', '  </progs>', '</sc>']
    return ('\n'.join(lines) + '\n').encode('ascii')


def fixture_sig_table():
    return {sc: c.SigProgram(sc, 'C:\\n\\%s.sig' % sc, sha(fixture_sig_bytes(sc)), 1, offset, cycle, green)
            for sc, (offset, cycle, green) in FIXTURE_SIGS.items()}


def fixture_context(rows=None):
    """contract_fixtures.context with the .sig programs of the fixture signal log, pinned to real bytes."""
    context = fx.context(rows)
    table = dict(context.sig_table)
    table.update(fixture_sig_table())
    return dataclasses.replace(context, sig_table=table)


def write_run_network(directory):
    """The run network folder of a synthetic bundle: the .sig copies; returns the network_path."""
    network = Path(directory).resolve() / 'network'
    network.mkdir(parents=True, exist_ok=True)
    for sc in FIXTURE_SIGS:
        (network / f'{sc}.sig').write_bytes(fixture_sig_bytes(sc))
    return network / FIXTURE_NETWORK_NAME


class World:
    """One decision T of a synthetic run on the fixture table: counts, frames, chunk rows, removals.

    Vehs defaults to 0 everywhere; set(ref, lane, vehs, records=None, prior=100) fixes a
    point: C_{k-1} = prior, C_k = prior + vehs, records in the file = C_k - tail.
    Entry rows at a point are added with entry(ref, lane, veh, t) in time order.
    """

    def __init__(self, t=900, rows=None):
        self.t = t
        self.rows = fixture_rows() if rows is None else rows
        start, end, k = c.bundle_interval(t)
        self.start, self.end, self.k = start, end, k
        self.vehs, self.prior, self.tail = {}, {}, {}
        self.entries = defaultdict(list)       # dcp -> [(t, veh)]
        self.frame_end, self.frame_start = [], []
        self.removals = []

    def set(self, ref, lane, vehs, *, tail=0, prior=None):
        key = key_of(self.rows, ref, lane)
        self.vehs[key] = vehs
        self.tail[key] = tail
        self.prior[key] = (0 if self.k is None else 100) if prior is None else prior
        return key

    def entry(self, ref, lane, veh, t):
        self.entries[key_of(self.rows, ref, lane)].append((t, veh))

    def remove(self, veh, t, link, pos, decision=1126, route=1):
        self.removals.append((t, veh, link, pos, decision, route))

    def detectors(self):
        out, cum = {}, {}
        for r in self.rows:
            key = r.dcm_no
            out[str(key)] = self.vehs.get(key, 0)
            cum[str(key)] = self.prior.get(key, 0 if self.k is None else 100) + out[str(key)]
        return out, cum

    def mer_rows(self):
        """Chunk rows: late rows of the previous interval first, then this interval, seq order."""
        detectors, cum = self.detectors()
        events = []
        for r in self.rows:
            key = r.dcp_no
            c_now = cum[str(key)]
            present = c_now - self.tail.get(key, 0)
            mine = sorted(self.entries.get(key, []))
            first = present - len(mine) + 1
            for i, (t, veh) in enumerate(mine):
                events.append((t, key, veh, first + i))
        events.sort()
        rows = []
        for seq, (t, key, veh, ordinal) in enumerate(events, start=1000):
            rows.append(c.MerRow(seq, key, float(t), None, veh, 100, 50.0, 4.5, ordinal))
        return rows

    def records(self):
        detectors, cum = self.detectors()
        return {k: cum[k] - self.tail.get(int(k), 0) for k in cum}

    def err_rows(self):
        rows = []
        for i, (t, veh, link, pos, decision, route) in enumerate(sorted(self.removals)):
            message = f'Simulation second {t}: removed {veh}'
            rows.append({'kind': 'lane_change_removal', 'message': message, 'byte_offset': 100 * (i + 1),
                         'raw_line_sha256': sha(message.encode()), 'time_sec': float(t), 'wait_sec': 45.0,
                         'vehicle_id': veh, 'route_decision': decision, 'route_index': route, 'link': link,
                         'position_m': float(pos)})
        return rows

    def frames(self):
        return make_frame(self.end, self.frame_end), make_frame(self.start, self.frame_start)


def make_frame(t, vehicles):
    """lane-plant-frame/v1 of full 15-field rows or (veh, link, lane, pos[, speed]) tuples."""
    frame = fx.frame(t, [v for v in vehicles if len(v) < c.FRAME_ROW_WIDTH])
    frame['vehicles'] += [list(v) for v in vehicles if len(v) == c.FRAME_ROW_WIDTH]
    frame['vehicles'].sort(key=lambda row: row[0])
    c.validate_frame(frame, t)
    return frame


def frame_row(veh, link, lane, pos, *, decision=None, route=None, kind=None, next_link=None, speed=40.0):
    return [veh, link, lane, float(pos), speed, 4.5, decision, route, kind, next_link, None, None, None, None, None]


def write_bundle(world, directory, *, ground_truth=True, signal_log=None):
    """Write the complete obs150 bundle of world under directory; return the state (raw).

    The state carries network_path in <directory>/network, which holds the .sig
    copies of FIXTURE_SIGS (write_run_network).
    """
    directory = Path(directory)
    (directory / 'obs150').mkdir(parents=True, exist_ok=True)
    (directory / 'lane_observations').mkdir(parents=True, exist_ok=True)
    t = world.t
    frame_end, frame_start = world.frames()
    frame_end['run_id'] = frame_start['run_id'] = 'run1'
    paths = {}
    for frame in (frame_end, frame_start):
        data = json.dumps(frame).encode('utf-8')
        path = directory / Path(c.frame_path(frame['time_s']))
        path.write_bytes(data)
        paths[frame['time_s']] = sha(data)
    mer_rows = world.mer_rows()
    chunk = b''.join(json.dumps(list(r), separators=(',', ':')).encode() + b'\n' for r in mer_rows)
    (directory / Path(c.mer_chunk_path(t))).write_bytes(chunk)
    records = world.records()
    detectors, cum = world.detectors()
    max_t = max([r.t_file for r in mer_rows], default=None)
    if world.k is not None:
        max_t = max(max_t or 0.0, world.end - 0.4)
    entries = []
    previous = None
    if world.k is not None:
        prev = {'sim_sec': world.start if world.start >= 150 else 1, 'chunk': c.mer_chunk_path(world.start or 1),
                'chunk_sha256': fx.SHA_A, 'byte_start': 0, 'byte_end': 10, 'max_t_any': float(world.start),
                'records_cum_by_dcp': {k: world.prior.get(int(k), 100) for k in cum}, 'prev_entry_sha256': None}
        prev['entry_sha256'] = c.mer_index_entry_sha256(prev)
        entries.append(prev)
        previous = prev['entry_sha256']
    entry = {'sim_sec': t, 'chunk': c.mer_chunk_path(t), 'chunk_sha256': sha(chunk), 'byte_start': 10,
             'byte_end': 20 + len(chunk), 'max_t_any': max_t, 'records_cum_by_dcp': records,
             'prev_entry_sha256': previous}
    if world.k is None:
        entry['byte_start'] = 0
    entry['entry_sha256'] = c.mer_index_entry_sha256(entry)
    entries.append(entry)
    (directory / Path(c.MER_INDEX_PATH)).write_bytes(
        c.canonical_json_bytes({'schema': c.MER_INDEX_SCHEMA, 'source': 'x.mer', 'entries': entries}) + b'\n')
    err_rows = world.err_rows()
    err_chunk = b''.join(json.dumps(r, sort_keys=True, separators=(',', ':')).encode() + b'\n' for r in err_rows)
    (directory / Path(c.err_chunk_path(t))).write_bytes(err_chunk)
    raw = fx.raw_obs(t, world.rows)
    raw['detector_config']['sha256'] = fixture_context(world.rows).detector_csv_sha256
    groups = c.group_boundaries(world.rows)
    removals_cum = {ref: len(c.removals_in_boundary(err_rows, groups[ref])) for ref in c.offset_boundary_refs(world.rows)}
    sources = {road: sum(cum[str(r.dcm_no)] for r in world.rows if r.role == 'source' and r.ref == road)
               for road in c.ROADS}
    raw.update({'directory': str(directory), 'detectors': detectors, 'detectors_cum': cum,
                'ground_truth_windows': [[750, 900]] if ground_truth else [],
                'source_cumulative_vehs': sources,
                'frames': {'current': {'path': c.frame_path(world.end), 'sha256': paths[world.end],
                                       'vehicles': len(frame_end['vehicles'])},
                           'previous': {'path': c.frame_path(world.start), 'sha256': paths[world.start]}}})
    raw['mer'].update({'chunk_sha256': sha(chunk), 'index_sha256': entry['entry_sha256'],
                       'prev_index_sha256': entry['prev_entry_sha256'], 'byte_start': entry['byte_start'],
                       'byte_end': entry['byte_end'], 'max_t_any': max_t, 'records_cum_by_dcp': records})
    raw['err'].update({'chunk_sha256': sha(err_chunk), 'removals': len(err_rows),
                       'removals_cum_by_boundary': removals_cum,
                       'max_sim_sec': max([r['time_sec'] for r in err_rows], default=None)})
    if signal_log is not None:
        raw['signal_log'] = signal_log
    provenance = directory / 'provenance.json'
    provenance.write_text(json.dumps({'run_id': 'run1', 'signal_observation': {
        'config_chain': [{'path': 'x', 'sha256': fx.SHA_C}]}}), encoding='utf-8')
    state = fx.state(t)
    state['network_path'] = str(write_run_network(directory))           # VBS:2817 writes it in every state
    state['run_provenance'] = {'run_id': 'run1', 'manifest_path': str(provenance)}
    state[c.RAW_STATE_KEY] = raw
    return state


def clone(value):
    return copy.deepcopy(value)
