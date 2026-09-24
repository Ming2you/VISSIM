"""obs150 capture (WP-B1, plan B2): the .mer / .err increments of one decision.

Called once per decision stop T (t=1 and every 150 s) while VISSIM is paused,
through ``scripts/obs150_capture.py`` (VBS A7.4). It reads each file from the
previous call's end offset up to its LAST COMPLETE LINE, stores the rows of the
generated detector points (.mer) and every parsed event (.err) as LF JSONL
chunks under ``<decisionDir>/obs150`` and returns the capture meta of
CONTRACT.md 4.4. Nothing is approximated: a row that does not parse, a removal
line ERRP cannot read, a header that disagrees with the detector table or a
broken index chain ends the capture with ObsContractError.

Cursor state lives only in files this module wrote and pinned:
- .mer: the sha-chained ``obs150/mer_index.json`` (byte_end, max_t_any,
  records_cum_by_dcp of the previous entry). The file-wide data-row number of
  the first new row (``seq``) is recounted from the file prefix, so the index
  keeps exactly the contract keys.
- .err: the previous ``obs150/capture_<T'>.json`` (byte_end, max_sim_sec,
  removals_cum_by_boundary), validated by ``validate_capture_meta``.

The t=1 capture reads the .mer header only, so the rows of window 1 are all in
the T=150 chunk. A .err that names a second after the stop is refused.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_contract import ObsContractError

_BLOCK = 16 << 20
_HEADER_LIMIT = 8 << 20
MER_POINT_LINE = re.compile(rb'^Data collection point\s+([1-9][0-9]*): Link\s+([1-9][0-9]*) lane ([1-9][0-9]*)'
                            rb' at\s+([0-9]+\.[0-9]+) m\.$')
MER_COLUMN_MARK = b'Measurem.'
MER_COLUMNS = {'dcp': 'Measurem.', 't_entry': 't(Entry)', 't_exit': 't(Exit)', 'veh': 'VehNo',
               'vtype': 'Vehicle type', 'v_kmh': 'v[km/h]', 'length_m': 'VehLength[m]'}
MER_TIME = re.compile(r'-1\.00|(?:0|[1-9][0-9]*)\.[0-9]{2}')
MER_HEADER_POS_TOL_M = 0.0005 + 1e-9     # the header prints the point position with 3 decimals
# CONTRACT 4.2: every ERRP row that names a link carries it as an int. route_next_link_not_found
# (a vehicle at a link end without the next link of its route) also names that next link.
ERR_LINK_INT_KINDS = ('lane_change_removal', 'ignored_static_routing', 'ignored_desired_speed',
                      'route_next_link_not_found')
ERR_EXTRA_INT_FIELDS = {'route_next_link_not_found': ('next_link',)}
ERR_SUFFIX = '_001.err'
# CONTRACT 4.4 err.max_sim_sec: the largest "Simulation second" anywhere in the
# file, whatever ERRP classified the line as (D11 measures .err lag with it).
ERR_SIM_SECOND = re.compile(r'Simulation second ([0-9]+(?:\.[0-9]+)?)', re.I)
ERR_TIME_FUZZ_S = 1e-6                   # .err seconds are step ends (0.1 s): none can follow the stop


def _require(condition, message):
    if not condition:
        raise ObsContractError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _previous_stop(sim_sec):
    _require(oc.is_decision_stop(sim_sec), 'Captures exist only at t=1 and multiples of 150 s')
    if sim_sec == oc.FIRST_DECISION_SEC:
        return None
    return oc.FIRST_DECISION_SEC if sim_sec == oc.DECISION_INTERVAL_SEC else sim_sec - oc.DECISION_INTERVAL_SEC


def _write_new(path, data):
    """Create-once write through a temporary name; an existing file is a replay error."""
    _require(not path.exists(), 'obs150 file already exists: ' + str(path))
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(data)
    temporary.replace(path)


def _jsonl(values):
    """ASCII LF JSONL (ensure_ascii keeps U+2028 and friends out of the line structure)."""
    return b''.join(json.dumps(v, ensure_ascii=True, sort_keys=True, separators=(',', ':'),
                               allow_nan=False).encode('ascii') + b'\n'
                    for v in values)


# --------------------------------------------------------------------------
# .mer
# --------------------------------------------------------------------------
def find_mer_source(eval_dir):
    """The one raw data collection file of the run (EvalOutDir\\<stem>_*.mer)."""
    files = sorted(p for p in Path(eval_dir).glob('*.mer') if p.is_file())
    _require(len(files) == 1, f'Exactly one .mer file expected in {eval_dir}, found {len(files)}')
    return files[0].resolve()


def _mer_header(handle, size):
    """Parse the header: {'points': {dcp: (link, lane, pos)}, 'columns': [...], 'data_start': int|None}.

    Only complete lines count. data_start is the byte after the column line, None
    while the header itself is still being written (PR t1: the file stopped mid-header).
    """
    handle.seek(0)
    head = b''
    while True:
        block = handle.read(min(1 << 20, size - len(head)))
        head += block
        if not block or MER_COLUMN_MARK in head or len(head) >= min(size, _HEADER_LIMIT):
            break
    points, columns, data_start, offset = {}, None, None, 0
    for raw in head.splitlines(keepends=True):
        if not raw.endswith(b'\n'):
            break
        line = raw.rstrip(b'\r\n').strip()
        offset += len(raw)
        if line.startswith(b'Data collection point'):
            match = MER_POINT_LINE.match(line)
            _require(match is not None, '.mer point header line does not parse: ' + repr(line[:120]))
            dcp = int(match[1])
            _require(dcp not in points, f'.mer header repeats point {dcp}')
            points[dcp] = (int(match[2]), int(match[3]), float(match[4]))
        elif MER_COLUMN_MARK in line:
            names = [p.strip().decode('ascii') for p in line.split(b';')]
            _require(names and names[-1] == '', '.mer column line must end with ;')
            columns = names[:-1]
            data_start = offset
            break
    if data_start is None:
        _require(len(head) < _HEADER_LIMIT, '.mer header exceeds the scan limit')
    return {'points': points, 'columns': columns, 'data_start': data_start}


def _check_header_points(points, table, complete):
    """Every generated point of the table is in the header with its link, lane and position."""
    for row in table:
        found = points.get(row.dcp_no)
        if found is None:
            _require(not complete, f'.mer header lacks generated point {row.dcp_no}')
            continue
        link, lane, pos = found
        _require((link, lane) == (row.link, row.lane) and abs(pos - row.pos) <= MER_HEADER_POS_TOL_M,
                 f'.mer header point {row.dcp_no} ({link}, {lane}, {pos}) differs from the table')


def _count_lines(handle, start, end):
    handle.seek(start)
    count, remaining = 0, end - start
    while remaining > 0:
        block = handle.read(min(_BLOCK, remaining))
        _require(block, '.mer file shrank while counting rows')
        count += block.count(b'\n')
        remaining -= len(block)
    return count


def _mer_time(text):
    _require(MER_TIME.fullmatch(text) is not None, '.mer time must be written with two decimals: ' + repr(text))
    value = float(text)
    return None if value == -1.0 else value


def _mer_number(text, what):
    try:
        value = float(text)
    except ValueError as error:
        raise ObsContractError(f'.mer {what} is not a number: {text!r}') from error
    _require(math.isfinite(value), f'.mer {what} must be finite')
    return value


def _mer_int(text, what):
    _require(re.fullmatch(r'-?(0|[1-9][0-9]*)', text) is not None, f'.mer {what} is not an integer: {text!r}')
    return int(text)


def parse_mer_rows(data, columns, first_seq, table_keys, records_cum):
    """Parse complete data lines; return (stored MerRow list, max time over ALL rows or None).

    records_cum ({dcp: entry rows so far}) is advanced in place; entry rows of a
    generated point get the next 1-based ordinal of that point.
    """
    index = {}
    for key, name in MER_COLUMNS.items():
        _require(columns.count(name) == 1, f'.mer column {name!r} missing or repeated')
        index[key] = columns.index(name)
    width = len(columns) + 1
    stored, max_t = [], None
    seq = first_seq
    for raw in data.splitlines():
        line = raw.strip()
        _require(line, 'Blank line inside the .mer data section')
        try:
            text = line.decode('ascii')
        except UnicodeDecodeError as error:
            raise ObsContractError('.mer data line is not ASCII') from error
        parts = [p.strip() for p in text.split(';')]
        _require(len(parts) == width and parts[-1] == '', f'.mer row width differs at seq {seq}: {text[:120]!r}')
        t_entry, t_exit = _mer_time(parts[index['t_entry']]), _mer_time(parts[index['t_exit']])
        _require(t_entry is not None or t_exit is not None, f'.mer row {seq} has neither entry nor exit time')
        latest = max(t for t in (t_entry, t_exit) if t is not None)
        max_t = latest if max_t is None else max(max_t, latest)
        dcp = _mer_int(parts[index['dcp']], 'point number')
        if dcp in table_keys:
            ordinal = None
            if t_entry is not None:
                ordinal = records_cum[dcp] + 1
                records_cum[dcp] = ordinal
            veh = _mer_int(parts[index['veh']], 'vehicle number')
            _require(veh > 0, '.mer vehicle number must be positive')
            stored.append(oc.MerRow(seq, dcp, t_entry, t_exit, veh, _mer_int(parts[index['vtype']], 'vehicle type'),
                                    _mer_number(parts[index['v_kmh']], 'speed'),
                                    _mer_number(parts[index['length_m']], 'vehicle length'), ordinal))
        seq += 1
    return stored, max_t


def _load_index(path, source, previous_stop):
    if previous_stop is None:
        _require(not path.exists(), 'The t=1 capture starts a new mer index: ' + str(path))
        return {'schema': oc.MER_INDEX_SCHEMA, 'source': source, 'entries': []}, None
    _require(path.exists(), 'mer index of the previous capture is missing: ' + str(path))
    document = json.loads(path.read_text(encoding='utf-8'))
    oc.validate_mer_index(document)
    _require(document['source'] == source, 'The .mer source changed between captures')
    _require(document['entries'] and document['entries'][-1]['sim_sec'] == previous_stop,
             f'mer index must end at the previous decision {previous_stop}')
    return document, document['entries'][-1]


def capture_mer(eval_dir, decision_dir, sim_sec, table):
    """(meta, chunk bytes, index document) of the .mer increment; nothing is written here.

    At t=1 the cursor stops at the column line: the chunk is empty, records 0 and
    max_t_any null even when the file already holds rows.
    """
    source_path = find_mer_source(eval_dir)
    source = str(source_path)
    index_path = oc.resolve({'directory': str(decision_dir)}, oc.MER_INDEX_PATH)
    document, previous = _load_index(index_path, source, _previous_stop(sim_sec))
    keys = {row.dcp_no for row in table}
    records = {dcp: 0 for dcp in keys}
    byte_start, max_t_any = 0, None
    if previous is not None:
        byte_start, max_t_any = previous['byte_end'], previous['max_t_any']
        _require(set(previous['records_cum_by_dcp']) == {str(k) for k in keys},
                 'mer index points differ from the detector table')
        records = {int(k): v for k, v in previous['records_cum_by_dcp'].items()}
    with open(source_path, 'rb') as handle:          # default share mode: VISSIM keeps writing
        handle.seek(0, 2)
        size = handle.tell()
        _require(size >= byte_start, '.mer file shrank below the previous capture end')
        _require_line_start(handle, byte_start, '.mer')
        header = _mer_header(handle, size)
        # VISSIM writes the header at the start; mid-header is a t=1 buffering state only (PR t1).
        _require(sim_sec == oc.FIRST_DECISION_SEC or header['data_start'] is not None,
                 f'.mer header is still incomplete at {sim_sec} s: not the file of this run')
        _check_header_points(header['points'], table, header['data_start'] is not None)
        handle.seek(byte_start)
        tail = handle.read(size - byte_start)
        byte_end = byte_start + tail.rfind(b'\n') + 1
        stored = []
        data_start = header['data_start']
        if sim_sec == oc.FIRST_DECISION_SEC and data_start is not None:
            # t=1 consumes the header only (CONTRACT 4.4). Every row of window 1,
            # (0, 1] included, then lands in the T=150 chunk, which assign_window
            # needs whole; t=1 itself closes no window and reads no row.
            byte_end = min(byte_end, data_start)
        if data_start is not None and byte_end > data_start:
            parse_from = max(byte_start, data_start)
            first_seq = _count_lines(handle, data_start, parse_from) if parse_from > data_start else 0
            stored, chunk_max = parse_mer_rows(tail[parse_from - byte_start:byte_end - byte_start],
                                               header['columns'], first_seq, keys, records)
            if chunk_max is not None:
                max_t_any = chunk_max if max_t_any is None else max(max_t_any, chunk_max)
    chunk_bytes = _jsonl([list(row) for row in stored])
    chunk_rel = oc.mer_chunk_path(sim_sec)
    records_json = {str(k): records[k] for k in sorted(keys)}
    entry = {'sim_sec': sim_sec, 'chunk': chunk_rel, 'chunk_sha256': _sha(chunk_bytes), 'byte_start': byte_start,
             'byte_end': byte_end, 'max_t_any': max_t_any, 'records_cum_by_dcp': records_json,
             'prev_entry_sha256': None if previous is None else previous['entry_sha256']}
    entry['entry_sha256'] = oc.mer_index_entry_sha256(entry)
    document['entries'].append(entry)
    oc.validate_mer_index(document)
    meta = {'source': source, 'chunk': chunk_rel, 'chunk_sha256': entry['chunk_sha256'],
            'index': oc.MER_INDEX_PATH, 'index_sha256': entry['entry_sha256'],
            'prev_index_sha256': entry['prev_entry_sha256'], 'byte_start': byte_start, 'byte_end': byte_end,
            'max_t_any': max_t_any, 'records_cum_by_dcp': records_json}
    return meta, chunk_bytes, document


# --------------------------------------------------------------------------
# .err
# --------------------------------------------------------------------------
def _errp_parse_bytes():
    from diagnostics.capture_native_runtime_errors import parse_bytes
    return parse_bytes


def normalize_err_event(event, byte_start):
    """ERRP event -> chunk row: absolute byte_offset, no line_number, integer link (and next_link) numbers."""
    row = {k: v for k, v in event.items() if k != 'line_number'}
    row['byte_offset'] = byte_start + event['byte_offset']
    if row['kind'] in ERR_LINK_INT_KINDS:
        for field in ('link',) + ERR_EXTRA_INT_FIELDS.get(row['kind'], ()):
            _require(re.fullmatch(r'[1-9][0-9]*', str(row[field])) is not None, f'err {field} must be a link number')
            row[field] = int(row[field])
    return oc.validate_err_row(row)


def parse_err_increment(data, byte_start):
    """(rows, complete_bytes, max_sim_sec|None) of the complete lines in data (read from byte_start).

    max_sim_sec is the largest "Simulation second" on any complete line, parsed
    or not (CONTRACT 4.4); the partial tail is left for the next call.
    """
    parsed = _errp_parse_bytes()(data)
    _require(not parsed['unparsed_removal_lines'],
             f"{len(parsed['unparsed_removal_lines'])} removal line(s) did not parse")
    rows = [normalize_err_event(e, byte_start) for e in parsed['events']]
    times = [float(m) for r in rows for m in ERR_SIM_SECOND.findall(r['message'])]
    return rows, parsed['complete_line_prefix_bytes'], (max(times) if times else None)


def same_path(a, b):
    """Windows paths compare without case (the .err may not exist yet when the first capture names it)."""
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def _check_err_source(err_path):
    path = Path(err_path)
    _require(path.name.lower().endswith(ERR_SUFFIX), 'The runtime error file is <network stem>_001.err')
    stem = path.name[:-len(ERR_SUFFIX)]
    others = [p for p in path.parent.glob(stem + '_*.err') if not same_path(p.resolve(), path.resolve())]
    _require(not others, 'Another runtime error file of this network exists: ' + ', '.join(p.name for p in others))
    return path.resolve() if path.exists() else path.parent.resolve() / path.name


def _previous_err(decision_dir, previous_stop, source):
    """(byte_end, max_sim_sec, removals_cum_by_boundary, source spelling) of the previous capture."""
    if previous_stop is None:
        return 0, None, None, source
    path = oc.resolve({'directory': str(decision_dir)}, oc.capture_meta_path(previous_stop))
    _require(path.exists(), 'Capture meta of the previous decision is missing: ' + str(path))
    meta = json.loads(path.read_bytes().decode('ascii'))
    oc.validate_capture_meta(meta, previous_stop)
    err = meta['err']
    _require(same_path(err['source'], source), 'The .err source changed between captures')
    return err['byte_end'], err['max_sim_sec'], err['removals_cum_by_boundary'], err['source']


def _require_line_start(handle, offset, what):
    """The previous capture ended after a complete line: the byte before its end offset is LF."""
    if offset > 0:
        handle.seek(offset - 1)
        _require(handle.read(1) == b'\n', f'{what} byte before the previous capture end is not a line end: '
                                          'the file changed between captures')


def capture_err(err_path, decision_dir, sim_sec, table):
    """(meta, chunk bytes) of the .err increment; nothing is written here."""
    source_path = _check_err_source(err_path)
    # the run keeps the first capture's spelling of the path (same_path)
    byte_start, max_sim_sec, previous_cum, source = _previous_err(decision_dir, _previous_stop(sim_sec),
                                                                  str(source_path))
    refs = oc.offset_boundary_refs(table)
    if previous_cum is None:
        previous_cum = {ref: 0 for ref in refs}
    _require(set(previous_cum) == set(refs), 'removals_cum_by_boundary keys differ from the offset boundaries')
    data = b''
    if source_path.exists():
        with open(source_path, 'rb') as handle:
            handle.seek(0, 2)
            size = handle.tell()
            _require(size >= byte_start, '.err file shrank below the previous capture end')
            _require_line_start(handle, byte_start, '.err')
            handle.seek(byte_start)
            data = handle.read(size - byte_start)
    else:
        _require(byte_start == 0, '.err file disappeared after it was read')
    rows, complete, chunk_max = parse_err_increment(data, byte_start)
    if chunk_max is not None:
        max_sim_sec = chunk_max if max_sim_sec is None else max(max_sim_sec, chunk_max)
    # The .err has no count to check it against (the .mer has Vehs). A line from
    # after this stop means another run's file (a stale _001.err) and would slip
    # its removals into R.
    _require(max_sim_sec is None or max_sim_sec <= sim_sec + ERR_TIME_FUZZ_S,
             f'.err names Simulation second {max_sim_sec} after the stop {sim_sec}: not this run')
    groups = oc.group_boundaries(table)
    cum = {ref: previous_cum[ref] + len(oc.removals_in_boundary(rows, groups[ref])) for ref in refs}
    chunk_bytes = _jsonl(rows)
    meta = {'source': source, 'chunk': oc.err_chunk_path(sim_sec), 'chunk_sha256': _sha(chunk_bytes),
            'byte_start': byte_start, 'byte_end': byte_start + complete, 'partial_tail_bytes': len(data) - complete,
            'max_sim_sec': max_sim_sec, 'removals': sum(r['kind'] == 'lane_change_removal' for r in rows),
            'unparsed_removal_lines': 0, 'removals_cum_by_boundary': dict(sorted(cum.items()))}
    return meta, chunk_bytes


# --------------------------------------------------------------------------
# Contract interface (plan 1.9)
# --------------------------------------------------------------------------
def capture(eval_dir, err_path, out_dir, sim_sec, detector_table):
    """Capture the .mer/.err increments at decision stop sim_sec; write chunks, index and capture_<T>.json.

    out_dir is <decisionDir>/obs150; detector_table is the DetectorRow tuple of
    the pinned CSV. Returns the meta dict {"mer": ..., "err": ...} (CONTRACT 4.4),
    byte-identical to the capture file.
    """
    _require(type(sim_sec) is int and oc.is_decision_stop(sim_sec), 'sim_sec must be t=1 or a multiple of 150')
    table = oc.validate_detector_rows(detector_table)
    out = Path(out_dir)
    _require(out.name == 'obs150', 'out_dir must be <decisionDir>/obs150')
    out.mkdir(parents=True, exist_ok=True)
    decision_dir = out.parent.resolve()
    context = {'directory': str(decision_dir)}
    for relative in (oc.mer_chunk_path(sim_sec), oc.err_chunk_path(sim_sec), oc.capture_meta_path(sim_sec)):
        _require(not oc.resolve(context, relative).exists(), 'obs150 chunk already exists: ' + relative)
    # Read and validate everything first; a failure leaves no file of this stop behind.
    err, err_chunk = capture_err(err_path, decision_dir, sim_sec, table)
    mer, mer_chunk, index = capture_mer(eval_dir, decision_dir, sim_sec, table)
    meta = {'mer': mer, 'err': err}
    meta_bytes = oc.capture_meta_bytes(meta, sim_sec)
    _write_new(oc.resolve(context, err['chunk']), err_chunk)
    _write_new(oc.resolve(context, mer['chunk']), mer_chunk)
    index_path = oc.resolve(context, oc.MER_INDEX_PATH)
    temporary = index_path.with_name(index_path.name + '.tmp')
    temporary.write_bytes(oc.canonical_json_bytes(index) + b'\n')
    temporary.replace(index_path)
    # The capture file is written last: its presence commits the stop (VBS reads it).
    _write_new(oc.resolve(context, oc.capture_meta_path(sim_sec)), meta_bytes)
    return meta


def capture_file_sha256(out_dir, sim_sec):
    return oc.file_sha256(Path(out_dir).parent / Path(*oc.capture_meta_path(sim_sec).split('/')))
