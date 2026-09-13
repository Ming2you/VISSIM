"""Post-run fixed-command comparison. No COM, model, runner, or source mutation.

FZP comparison follows audit_observed_nc_trajectory's ordered payload contract,
but streams two files once to retain the first differing row. Small artifact SHA
uses that existing diagnostic helper. Sparse readbacks prove observed transitions,
not continuous holds. Native LSA COM coverage is an independent required verdict.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal
import hashlib
from itertools import zip_longest
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnostics.audit_observed_nc_trajectory import sha
from diagnostics.com_execution_equivalence.command_clock import CommandClock, native_options, native_clock_options

SG_FIELDS = ['sim_sec', 'sc_no', 'sg_no', 'requested_state', 'readback_state', 'ok', 'stage']
VSL_FIELDS = ['sim_sec', 'dsd_no', 'veh_class_no', 'requested_kph', 'readback_distribution_no', 'ok', 'stage']
STAGES = {'post_step': 0, 'immediate': 1}
STATES = {'RED', 'GREEN', 'AMBER', 'REDAMBER', 'OFF'}
STATE_KEYS = ('sim_sec', 'sim_period_sec', 'control_interval_sec', 'network_path', 'total_vehicles',
              'urban_vehicles', 'freeway_vehicles', 'ramp_vehicles', 'boundary_vehicles', 'other_vehicles',
              'mean_speed_kph', 'freeway_mean_speed_kph', 'stopped_vehicles', 'demand', 'ramp_counts',
              'local_observation', 'vehicle_records', 'vehicle_routes', 'freeway_segments')
CONTROL_KEYS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation')
FAILURE_COUNTERS = ('DECISIONS_FAILED', 'OBSERVATION_FAILURES', 'SIGNAL_FAILURES',
                    'ACTION_FORMAT_FAILURES', 'COM_FAILURES')
# No missing core source/config/network is accepted. This optional schema key is
# absent from the current r02 provenance, whose 17 file entries all exist.
OPTIONAL_MISSING_FILES = {'detector_mapping'}


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def path(value):
    p = Path(value)
    return (p if p.is_absolute() else ROOT / p).resolve(strict=True)


def pin(item):
    p = path(item['path'])
    require(re.fullmatch('[0-9a-f]{64}', item['sha256']) is not None, 'Invalid SHA: ' + str(p))
    require(sha(p) == item['sha256'], 'Artifact SHA differs: ' + str(p))
    return p


def ramp_meter_timing_authority(provenance, vbs_text):
    """Resolve meter clearance from pinned config + transport + native consumer.

    Historical sources have a literal one-second clearance. A new runtime hook
    requires the complete new proof even when the effective value remains one.
    CSV metadata never grants authority to select a different physical clock.
    """
    key = 'actuation.real_world_ramp_metering.amber_sec'
    env = provenance.get('env', {})
    proof = provenance.get('ramp_meter_timing')
    source = '\n'.join(line.strip() for line in vbs_text.splitlines()
                       if line.strip() and not line.lstrip().startswith("'"))
    marker = re.search(r'RW_RAMP_AMBER_SEC|ReadRuntimeRampAmberSec|runtimeRampAmberSec', source, re.I)
    legacy = proof is None and 'ramp_meter_timing' not in provenance and 'RW_RAMP_AMBER_SEC' not in env and not marker

    if not legacy:
        require(isinstance(proof, dict) and proof.get('config_key') == key,
                'Missing/invalid ramp meter timing manifest authority')
        require(type(proof.get('amber_sec')) in (int, float) and proof['amber_sec'] in (0, 1)
                and type(proof.get('declared')) is bool,
                'Ramp timing manifest requires numeric 0/1 and boolean declared')
        require(type(env.get('RW_RAMP_AMBER_SEC')) is str
                and env['RW_RAMP_AMBER_SEC'] == str(int(proof['amber_sec'])),
                'Ramp timing environment transport missing/differs from manifest')
        # This is a versioned source contract, not a general VBScript interpreter.
        # Require the real reader, startup assignment and shared meter consumer;
        # a variable name or an inert comment is not sufficient support.
        reader = '''Function ReadRuntimeRampAmberSec()
Dim value
value = EnvText("RW_RAMP_AMBER_SEC")
If value = "" Then
ReadRuntimeRampAmberSec = RAMP_AMBER_SEC
ElseIf value = "0" Or value = "1" Then
ReadRuntimeRampAmberSec = CLng(value)
Else
WScript.Echo "ERROR=INVALID_RAMP_AMBER_SEC value=" & value
WScript.Quit 2
End If
End Function'''
        meter = '''Function RampStateAt(greenSec, simSec)
Dim pos
pos = FMod(CDbl(simSec), RAMP_CYCLE_SEC)
If CDbl(greenSec) <= 0 Then
RampStateAt = "RED"
ElseIf pos < CDbl(greenSec) Then
RampStateAt = "GREEN"
ElseIf pos < CDbl(greenSec) + runtimeRampAmberSec Then
RampStateAt = "AMBER"
Else
RampStateAt = "RED"
End If
End Function'''
        for name, expected in (('ReadRuntimeRampAmberSec', reader), ('RampStateAt', meter)):
            bodies = re.findall(r'^Function ' + name + r'\([^\n]*\)\n.*?^End Function$', source, re.M | re.S)
            require(bodies == [expected], 'Unsupported native ramp timing function: ' + name)
        assignments = re.findall(r'^runtimeRampAmberSec\s*=.*$', source, re.M | re.I)
        require(assignments == ['runtimeRampAmberSec = ReadRuntimeRampAmberSec()'],
                'Missing/ambiguous native ramp timing startup assignment')
        outside_functions = re.sub(r'^(?:Function|Sub) [^\n]+\n.*?^End (?:Function|Sub)$', '', source, flags=re.M | re.S)
        require('runtimeRampAmberSec = ReadRuntimeRampAmberSec()' in outside_functions,
                'Ramp timing initialization is not at native startup')
        setter = '''Function ApplyRampMeterSignal(scNo, greenSec, simSec)
Dim state
signalTraceSimSec = CLng(simSec)
state = RampStateAt(greenSec, simSec)
ApplyRampMeterSignal = SetSignalGroupState(scNo, 1, state)
End Function'''
        consumers = re.findall(r'^Function ApplyRampMeterSignal\([^\n]*\)\n.*?^End Function$', source, re.M | re.S)
        require(consumers == [setter],
                'Native meter setter does not consume shared runtime ramp clock')

    tuning = provenance.get('files', {}).get('tuning')
    # Old synthetic fixtures may use non-JSON placeholders; retain their exact
    # legacy source contract. Actual JSON tuning must not silently declare a new
    # setting without the new runtime/manifest proof.
    if legacy and (tuning is None or Path(tuning['path']).suffix.lower() != '.json'):
        return {'amber_sec': 1, 'declared': False, 'authority': 'legacy_source_constant'}
    require(isinstance(tuning, dict), 'Ramp timing requires a pinned tuning file')
    current = pin(tuning); chain = [] if legacy else proof.get('config_chain')
    require(isinstance(chain, list) and (legacy or chain), 'Missing ramp timing config chain')
    seen = set(); observed = []; amber = 1; declared = False
    while True:
        require(current not in seen, 'Cyclic ramp timing config chain'); seen.add(current)
        if not legacy:
            i = len(observed)
            require(i < len(chain) and isinstance(chain[i], dict)
                    and Path(chain[i].get('path', '')).is_absolute(), 'Missing/invalid ramp timing config pin')
            require(pin(chain[i]) == current, 'Ramp timing config chain path/order differs')
        doc = read(current); require(isinstance(doc, dict), 'Ramp timing config must be an object')
        node = doc
        for name in ('actuation', 'real_world_ramp_metering'):
            node = node.get(name, {})
            require(isinstance(node, dict), 'Ramp timing config section must be an object')
        if not declared and 'amber_sec' in node:
            value = node['amber_sec']
            require(type(value) in (int, float) and value in (0, 1), 'Configured ramp amber must be numeric 0 or 1')
            amber = int(value); declared = True
        observed.append({'path': str(current), 'sha256': sha(current)})
        parent = doc.get('extends')
        if not parent: break
        require(isinstance(parent, str), 'Ramp timing config requires a single string extends path')
        candidate = Path(parent)
        current = (candidate if candidate.is_absolute() else current.parent / candidate).resolve(strict=True)
    if legacy:
        require(not declared, 'New ramp timing setting lacks manifest/transport/native support')
        return {'amber_sec': 1, 'declared': False, 'authority': 'legacy_source_constant'}
    require(len(observed) == len(chain), 'Extra ramp timing config chain entries')
    require(proof['declared'] == declared and proof['amber_sec'] == amber,
            'Effective configured ramp timing differs from manifest')
    return {'amber_sec': amber, 'declared': declared, 'config_key': key,
            'config_chain': observed, 'transport': env['RW_RAMP_AMBER_SEC'],
            'authority': 'pinned_config_chain_environment_and_native_runtime_hook'}


def output_path(arm, key):
    p = path(arm[key])
    require(p.is_relative_to(path(arm['run_directory'])), 'Run output resolves outside its run: ' + key)
    return p


def number(value):
    x = Decimal(str(value))
    require(x.is_finite(), 'Nonfinite numeric value')
    return x


def integer(value):
    x = number(value)
    require(x >= 0 and x == int(x), 'Expected nonnegative integer')
    return int(x)


def state(value):
    value = value.strip().upper().replace('/', '').replace('-', '').replace(' ', '')
    require(value in STATES, 'Unknown signal state: ' + value)
    return value


def completed(arm, end):
    """Consume the existing selected_control_completion receipt; never infer exit."""
    run = path(arm['run_directory'])
    receipt_path = pin(arm['completion'])
    require(receipt_path.is_relative_to(run), 'Completion receipt outside run')
    receipt = read(receipt_path)
    require(receipt.get('schema') == 'selected-control-completion/v1', 'Unsupported receipt schema')
    require(receipt.get('completed') is True and type(receipt.get('exit_code')) is int
            and receipt['exit_code'] == 0 and receipt.get('owned_native_alive') is False
            and receipt.get('cscript_exit_code', 'absent') is None
            and number(receipt['terminal_sec']) == end and not receipt.get('errors'),
            'Run is incomplete, failed, or native exit is unconfirmed')
    require(run.name == arm['name'] == receipt['name'] and path(receipt['run_directory']) == run
            and arm['run_id'] == receipt['run_id'] and bool(arm['run_id']), 'Run identity mismatch')
    pp = pin({'path': receipt['provenance_path'], 'sha256': receipt['provenance_sha256']})
    require(pp.is_relative_to(run), 'Provenance outside run')
    provenance = read(pp)
    require(provenance['name'] == arm['name'] and provenance['run_id'] == arm['run_id']
            and number(provenance['sim_period_sec']) == end, 'Provenance identity/end mismatch')
    log = path(receipt['runlog_path'])
    require(log.is_relative_to(run), 'Runlog outside run')
    lines = log.read_bytes().splitlines()
    require(lines.count(b'STAGE=SIM_DONE') == 1 and lines.count(f'SIM_SEC={end}'.encode()) == 1,
            'Terminal runlog markers missing or duplicate')
    for key in FAILURE_COUNTERS:
        require([r for r in lines if r.startswith((key + '=').encode())] == [(key + '=0').encode()],
                'Failure counter missing/nonzero: ' + key)
    require(not any(r.startswith(b'ERROR') for r in lines), 'Error in completed runlog')
    state_csv = path(receipt['state_csv_path'])
    require(state_csv.is_relative_to(run), 'State CSV outside run')
    last = -1
    with state_csv.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            sec = number(row['sim_sec'])
            require(last < sec <= end, 'State CSV nonmonotonic/outside period')
            last = sec
    require(last == end, 'State CSV terminal missing')
    return provenance


def provenance_comparison(a, b):
    """Compare recorded identities without rehashing a changing live checkout."""
    left, right = {}, {}
    scalar = ('seed', 'sim_period_sec', 'control_interval_sec', 'state_log_interval_sec',
              'demand_scale', 'controller', 'audit_anchors_sec', 'signal_observation')
    for key in scalar:
        require(key in a and key in b, 'Missing provenance field: ' + key)
        left[key], right[key] = a[key], b[key]
    for label, dest in ((a, left), (b, right)):
        if 'ramp_meter_timing' in label:
            dest['ramp_meter_timing'] = label['ramp_meter_timing']
        require({'network', 'tuning', 'demand_profile', 'main_vbs_runner'} <= label['files'].keys(),
                'Missing network/config/demand/source provenance')
        for key, item in label['files'].items():
            digest = item.get('sha256')
            if item.get('exists') is False:
                require(key in OPTIONAL_MISSING_FILES and digest == '' and isinstance(item.get('path'), str),
                        'Required or malformed missing file pin: ' + key)
                dest['files.' + key] = {'exists': False, 'path': item['path'], 'sha256': ''}
                continue
            require(item.get('exists') is True and isinstance(digest, str)
                    and re.fullmatch('[0-9a-f]{64}', digest), 'Invalid recorded file pin: ' + key)
            dest['files.' + key] = digest
        for group in ('controller_sources', 'signal_programs'):
            items = label[group]
            require(isinstance(items, list) and items, 'Empty recorded source inventory: ' + group)
            seen = set()
            for item in items:
                key = group + '.' + item['path']
                require(key not in seen and item.get('exists') is True
                        and re.fullmatch('[0-9a-f]{64}', item.get('sha256', '')), 'Invalid/duplicate source pin')
                seen.add(key); dest[key] = item['sha256']
        for key, value in label['env'].items():
            dest['env.' + key] = value
    require(left.keys() == right.keys(), 'Provenance field/inventory set differs')
    allowed = {'env.RW_SIGNAL_WRITE_ON_CHANGE': ('0', '1'),
               'env.RW_SIGNAL_READBACK_SEC': ('1', '0')}
    differences = []
    for key in left:
        if key in allowed:
            require((left[key], right[key]) == allowed[key], 'Wrong old/fast execution mode: ' + key)
            differences.append({'key': key, 'left': left[key], 'right': right[key],
                                'reason': 'Old repeated write/full audit versus changed-write/sparse audit'})
        else: require(left[key] == right[key], 'Source/config/input mismatch: ' + key)
    require(all(k in left for k in allowed), 'Execution environment flags missing')
    for key in a['files']:
        if key != 'generated_vbs_config':
            require(a['files'][key]['path'] == b['files'][key]['path'], 'Absolute input path differs: ' + key)

    return {'passed': True, 'recorded_fields_checked': len(left), 'exact_exceptions': differences,
            'optional_missing_files': [k for k, value in left.items() if isinstance(value, dict) and value.get('exists') is False],
            'scope': 'Pinned per-run provenance; no current checkout source inventory rehash.',
            'identity_exclusions': ['name', 'run_id', 'created_at', 'workspace/git metadata',
                                    'per-run generated file path when content SHA is identical']}


def data_rows(p, info):
    """Exact FZP data bytes excluding CR/LF and pre-data metadata only."""
    before = p.stat(); file_hash = hashlib.sha256(); payload_hash = hashlib.sha256()
    count = 0; header = None; previous = Decimal('-1'); first = None
    with p.open('rb') as stream:
        for raw in stream:
            file_hash.update(raw)
            row = raw.rstrip(b'\r\n')
            if header is None:
                if row.startswith(b'$VEHICLE:'):
                    header = row.decode('ascii'); info['header'] = header
                    require(header.split(';')[0] == '$VEHICLE:SIMSEC', 'FZP first column must be SIMSEC')
                continue
            if not row:
                continue
            require(not row.startswith((b'*', b'$')), 'Unexpected metadata inside FZP data')
            require(len(row.split(b';')) == len(header.split(';')), 'FZP data/header width differs')
            sec = number(row.split(b';', 1)[0].decode('ascii'))
            require(sec >= previous, 'FZP time order decreases')
            require(raw.endswith(b'\n'), 'Incomplete final FZP line')
            previous = sec
            if first is None: first = sec
            count += 1; payload_hash.update(row + b'\n')
            yield row, str(sec)
    after = p.stat()
    require(header is not None and count > 0, 'FZP header/data missing')
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'FZP changed during read')
    info.update(path=str(p), rows=count, bytes=after.st_size, file_sha256=file_hash.hexdigest(),
                data_sha256=payload_hash.hexdigest(), first_sec=str(first), last_sec=str(previous))


def fzp_comparison(a, b, start, end):
    info = [{}, {}]; first = None; different = 0
    for i, pair in enumerate(zip_longest(data_rows(a, info[0]), data_rows(b, info[1])), 1):
        x, y = pair
        if x != y:
            different += 1
            if first is None:
                first = {'ordered_row_one_based': i, 'left': None if x is None else x[0].decode('ascii'),
                         'right': None if y is None else y[0].decode('ascii'),
                         'left_sec': None if x is None else x[1], 'right_sec': None if y is None else y[1]}
    extent = all(number(r['first_sec']) == start and number(r['last_sec']) == end for r in info)
    return {'passed': different == 0 and info[0]['header'] == info[1]['header'] and extent,
            'extent_passed': extent, 'different_ordered_rows': different, 'first_difference': first,
            'records': info, 'excluded': 'Only pre-$VEHICLE metadata, blank lines and line-ending bytes.'}


def readbacks(p, fields, expected, *, command_check, numeric=False, distribution_ids=None, require_dense=False, control_interval=None):
    """Keep transition order including post-step before immediate at each second."""
    before = p.stat(); latest = {}; first = {}; last_post = {}; events = []; rows = 0
    previous = (-1, -1); duplicate_holds = 0; counts = Counter(); observed_writes = Counter(); writes = []; grids = {}; post_states = {}
    require(bool(expected), 'Empty expected readback address set')
    require(callable(command_check), 'Independent command clock checker is required')
    for key, window in expected.items():
        require(re.fullmatch(r'[1-9][0-9]*:[1-9][0-9]*', key), 'Invalid expected physical address')
        require(integer(window['end']) >= integer(window['start']), 'Invalid observation window')
    if numeric:
        require(distribution_ids, 'Explicit requested-kph to native distribution-ID map required')
        by_dsd = {}
        for key in expected:
            dsd, cls = key.split(':'); by_dsd.setdefault(dsd, set()).add(int(cls))
        require(all(v == {10, 20, 30, 70} for v in by_dsd.values()), 'All four actual VSL class addresses required')
    with p.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == fields, 'Unexpected readback CSV header')
        for i, row in enumerate(reader, 2):
            require(None not in row and all(v is not None for v in row.values()), 'Malformed CSV row')
            sec = integer(row['sim_sec']); stage = row['stage']
            require(stage in STAGES and (sec, STAGES[stage]) >= previous, 'Reordered pre/post readback rows')
            previous = sec, STAGES[stage]
            ids = ('dsd_no', 'veh_class_no') if numeric else ('sc_no', 'sg_no')
            key = ':'.join(str(integer(row[k])) for k in ids)
            require(key in expected, 'Unknown physical readback address: ' + key)
            window = expected[key]
            require(window['start'] <= sec <= window['end'], 'Readback outside declared address window')
            require(row['ok'] == '1', 'Failed readback row: ' + str(i))
            if numeric:
                requested = str(number(row['requested_kph']).normalize())
                actual = integer(row['readback_distribution_no'])
                require(number(requested) > 0 and requested in distribution_ids
                        and actual > 0 and actual == integer(distribution_ids[requested]), 'Unexpected VSL distribution reference')
                require(stage == 'immediate', 'VSL sidecar is a setter-immediate observation')
                value = (requested, str(actual))
                observed_writes[key, sec] += 1; writes.append((sec, stage, key, requested, str(actual)))
            else:
                requested, value = state(row['requested_state']), state(row['readback_state'])
                require(requested == value, 'Signal readback differs from requested state')
                require(not window.get('zero_window') or value == 'RED', 'Zero-window owned SG must remain RED: ' + key)
            command_check(row)
            first.setdefault(key, (sec, stage))
            if stage == 'post_step': last_post[key] = sec
            if stage == 'post_step': post_states[key, value] = post_states.get((key, value), 0) | (1 << (sec - window['start']))
            counts[key + '/' + stage] += 1; rows += 1
            grids[key, stage] = grids.get((key, stage), 0) | (1 << (sec - window['start']))
            if latest.get(key) != value:
                events.append((sec, stage, key, value))
                latest[key] = value
            else: duplicate_holds += 1
    require(set(first) == set(expected), 'Readback address coverage missing')
    for key, window in expected.items():
        require(first[key] == (window['start'], 'immediate'), 'Initial actual readback missing: ' + key)
        if numeric:
            times = window['apply_seconds']
            require(times and len(times) == len(set(times)) and times[0] == window['start'], 'Invalid VSL application schedule')
            require({t: n for (k, t), n in observed_writes.items() if k == key}
                    == {integer(t): 1 for t in times}, 'Missing/duplicate VSL setter readback: ' + key)
        else:
            if window['start'] < window['end']:
                require(last_post.get(key) == window['end'], 'Terminal post-step readback missing: ' + key)
            require(type(control_interval) is int and control_interval > 0, 'Primary control interval required')
            boundaries = range(((window['start'] // control_interval) + 1) * control_interval,
                               window['end'] + 1, control_interval)
            require(all(grids.get((key, 'post_step'), 0) & (1 << (t - window['start'])) for t in boundaries),
                    'Owned control-boundary post-step readback missing: ' + key)
            if require_dense:
                grid = (1 << (window['end'] - window['start'])) - 1
                require(grids.get((key, 'immediate'), 0) & grid == grid
                        and grids.get((key, 'post_step'), 0) & (grid << 1) == grid << 1,
                        'Dense reference has missing one-second readback: ' + key)
    if not numeric:
        # Like sigPendingPostCheck, the last changed request in the callback wins.
        pending = {(key, sec): value for sec, stage, key, value in events if stage == 'immediate'}
        for (key, sec), value in pending.items():
            if sec == expected[key]['end']: continue  # no simulation callback after terminal
            require(post_states.get((key, value), 0) & (1 << (sec + 1 - expected[key]['start'])),
                    f'Initial/changed request lacks matching next-step post: {key} at {sec}')
    digest = sha(p)
    after = p.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Readback file changed')
    return {'passed': True, 'path': str(p), 'sha256': digest, 'rows': rows,
            'unchanged_observation_rows': duplicate_holds, 'stage_counts': dict(counts), 'transitions': events,
            'setter_immediate_writes': writes if numeric else None,
            'dense_reference_grid_required': require_dense,
            'minimum_next_step_and_control_boundary_posts_required': not numeric,
            'independent_command_clock_rows_checked': rows,
            'continuous_hold_coverage_certified': False,
            'vsl_scope': 'DesSpeedDistr class reference ID, not observed vehicle speed; sequential per-class reads, not atomic four-class snapshot.' if numeric else None}


def transition_comparison(a, b):
    first = next(({'index': i, 'left': x, 'right': y}
                  for i, (x, y) in enumerate(zip_longest(a['transitions'], b['transitions']), 1) if x != y), None)
    writes_exact = a['setter_immediate_writes'] == b['setter_immediate_writes']
    return {'passed': first is None and writes_exact, 'first_difference': first,
            'setter_immediate_order_exact': writes_exact, 'left': a, 'right': b,
            'scope': 'Actual initial state and ordered state transitions; repeated holds removed per address. '
                     'Timing and pre/post stages of transitions remain exact. Sparse holds are not continuously verified.'}


def lsa_coverage(p, signals, end):
    """Coverage against ACTUAL readbacks, never command CSV or intended clocks."""
    before = p.stat(); events = set(); rows = 0; digest = hashlib.sha256(); previous = Decimal('-1')
    with p.open('rb') as stream:
        for raw in stream:
            digest.update(raw)
            if b';' not in raw and rows == 0: continue
            if not raw.strip(): continue
            parts = [v.strip() for v in raw.decode('ascii').rstrip('\r\n').split(';')]
            require(len(parts) == 9 and parts[-1] == '', 'Malformed native LSA event')
            sec = number(parts[0]); number(parts[1]); number(parts[5])
            require(previous <= sec <= end and sec >= 0, 'Invalid/reordered LSA event time')
            previous = sec; rows += 1
            key = str(integer(parts[2])) + ':' + str(integer(parts[3]))
            events.add((sec, key, state(parts[4])))
    require(rows > 0, 'Native LSA has no events')
    missing = [{'sim_sec': sec, 'stage': stage, 'group': key, 'actual_state': value}
               for sec, stage, key, value in signals['transitions'] if (Decimal(sec), key, value) not in events]
    after = p.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'LSA changed during read')
    return {'passed': not missing, 'path': str(p), 'sha256': digest.hexdigest(), 'native_event_rows': rows,
            'actual_com_events_checked': len(signals['transitions']), 'missing_com_events': missing,
            'coverage_source': 'actual signal_readback.csv; no action/command substitution',
            'limitation': 'LSA has no pre/post stage. Matching timestamps/states cannot prove stage order or unseen holds.'}


def expected_plan_groups(arm):
    """Read the runner's exact sibling plan, pinned by its preparation receipt."""
    receipt = read(pin(arm['completion']))
    prov = read(pin({'path': receipt['provenance_path'], 'sha256': receipt['provenance_sha256']}))
    config = Path(prov['files']['generated_vbs_config']['path'])
    require(config.suffix.lower() == '.vbs', 'Expected canonical generated VBS path')
    plan = config.with_name(config.stem + '_sgplan.vbs').resolve(strict=True)
    proof = read(pin(receipt['preparation_checks']))
    pins = [digest for scope in ('source_sha256', 'generated_sha256') for name, digest in proof.get(scope, {}).items()
            if Path(name).resolve() == plan]
    require(len(pins) == 1, 'Sibling SG plan must have one explicit preparation SHA')
    blob = plan.read_bytes()
    require(hashlib.sha256(blob).hexdigest() == pins[0], 'Pinned sibling SG plan changed')
    mainline_only = prov['env'].get('RW_MAINLINE_SG_ONLY') == '1'
    groups, excluded = _plan_groups(blob, mainline_only)
    return groups, {'path': str(plan), 'sha256': pins[0], 'mainline_only': mainline_only,
                    'excluded_midblock_groups': excluded, 'source': 'Pinned RW_SIGNAL_SG_EXPECTED; never inferred from readbacks'}


def _plan_groups(blob, mainline_only):
    """Same literal parser for receipt and fixed preparation authority."""
    text = re.sub(r'&\s*_\r?\n\s*', '&', blob.decode('utf-8-sig'))
    matches = re.findall(r'^RW_SIGNAL_SG_EXPECTED\s*=\s*((?:"[^"]*"\s*&\s*)*"[^"]*")\s*$', text, re.M)
    require(len(matches) == 1, 'Missing/ambiguous literal RW_SIGNAL_SG_EXPECTED')
    tokens = ''.join(re.findall(r'"([^"]*)"', matches[0])).split(',')
    groups = {}; seen = set(); excluded = []
    for token in tokens:
        require(re.fullmatch(r'[1-9][0-9]*:[1-9][0-9]*:[0-9]+', token), 'Malformed SG expected token')
        sc, sg, windows = map(int, token.split(':')); key = f'{sc}:{sg}'
        require(key not in seen, 'Duplicate SG expected token'); seen.add(key)
        if mainline_only and sg > 8: excluded.append(key)
        else: groups.setdefault(str(sc), {})[str(sg)] = windows
    return groups, excluded


def run_inputs(arms, end, interval, command_batches=None):
    """Fixed canonical filenames and named physical keys; no user field-selection DSL."""
    dirs = [path(a['run_directory']) / ('decisions_' + a['name']) for a in arms]
    require(interval > 0 and end % interval == 0, 'Primary stepwise period/cadence incompatible')
    expected = {1, *range(interval, end + 1, interval)}
    times = []
    for folder in dirs:
        require(folder.resolve().is_relative_to(folder.parent), 'Decision folder resolves outside run')
        clocks = {int(p.stem.split('_')[1]) for p in folder.glob('action_*.csv')}
        require(clocks and clocks == {int(p.stem.split('_')[1]) for p in folder.glob('action_*.json')}
                == {int(p.stem.split('_')[1]) for p in folder.glob('state_*.json')}, 'Missing action/state decision artifacts')
        times.append(clocks)
    require(times[0] == times[1] == expected, 'Exact primary decision cadence is incomplete')
    plans = [expected_plan_groups(arm) for arm in arms]
    require(plans[0] == plans[1], 'Pair sibling SG plan/pin differs')
    receipts = [read(pin(arm['completion'])) for arm in arms]
    groups = plans[0][0]
    rows = []; signals = {}; vsl = {}; distributions = {}; city_starts = {}
    batches = command_batches if command_batches is not None else [{}, {}]
    for t in sorted(times[0]):
        commands = []
        for folder in dirs:
            with (folder / f'action_{t:06d}.csv').open(encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f); data = list(reader)
            require(data and {'kind', 'dsd_no', 'sc_no', 'speed_kph', 'metadata'} <= set(reader.fieldnames), 'Missing action CSV schema')
            require(all(None not in r and all(v is not None for v in r.values()) for r in data), 'Malformed command row')
            commands.append((reader.fieldnames, data))
        for bucket, (_, data) in zip(batches, commands): bucket[t] = data
        physical = [[{k: val for k, val in row.items() if k != 'metadata'} for row in rows] for _, rows in commands]
        detail = {'sim_sec': t, 'commands_exact': commands[0][0] == commands[1][0] and physical[0] == physical[1],
                  'csv_metadata_exact': [r['metadata'] for r in commands[0][1]] == [r['metadata'] for r in commands[1][1]],
                  'csv_metadata_sha256': [hashlib.sha256(json.dumps([r['metadata'] for r in rows]).encode()).hexdigest() for _, rows in commands],
                  'artifacts': []}
        state_hashes = {}
        for kind, keys in (('state', STATE_KEYS), ('action', CONTROL_KEYS)):
            values = []; omitted = []
            for folder, arm, receipt in zip(dirs, arms, receipts):
                p = folder / f'{kind}_{t:06d}.json'; blob = p.read_bytes(); raw = json.loads(blob)
                identity = raw['run_provenance']
                manifest = path(receipt['provenance_path'])
                require(identity['run_id'] == arm['run_id'] and manifest
                        == path(arm['run_directory']) / ('run_provenance_' + arm['name'] + '.json'),
                        'Physical JSON run identity differs')
                if kind == 'state':
                    require(path(identity['manifest_path']) == manifest, 'State manifest path differs')
                    if 'manifest_sha256' in identity:
                        require(identity['manifest_sha256'] == receipt['provenance_sha256'], 'State manifest SHA differs')
                    state_hashes[arm['run_id']] = hashlib.sha256(blob).hexdigest()
                else:
                    # canonical build_run_provenance emits v2 input pins, not the
                    # compact state serializer's top-level manifest_path.
                    require(type(identity.get('schema_version')) is int and identity['schema_version'] == 2,
                            'Unsupported action provenance schema')
                    for key, expected_path, digest in (
                        ('run_manifest_json', manifest, receipt['provenance_sha256']),
                        ('state_json', folder / f'state_{t:06d}.json', state_hashes[arm['run_id']]),
                    ):
                        item = identity['inputs'][key]
                        require(item.get('exists') is True and path(item['path']) == expected_path
                                and item['sha256'] == digest, 'Action provenance input differs: ' + key)
                require(set(keys) <= raw.keys(), 'Required physical/history keys missing')
                if kind == 'state': require(set(raw) == set(keys) | {'run_provenance'}, 'Unclassified state input key')
                values.append({k: raw[k] for k in keys})
                omitted.append({k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest()
                                for k, v in raw.items() if k not in keys})
                detail['artifacts'].append({'path': str(p), 'sha256': hashlib.sha256(blob).hexdigest()})
            detail[kind + '_changed_keys'] = [k for k in keys if values[0][k] != values[1][k]]
            detail[kind + '_omitted_metadata_sha256'] = omitted
        for folder in dirs:
            p = folder / f'action_{t:06d}.csv'; detail['artifacts'].append({'path': str(p), 'sha256': sha(p)})
        rows.append(detail)
        for r in commands[0][1]:
            kind = r['kind']
            if kind in ('signal', 'signal_sg'):
                sc = str(integer(r['sc_no']))
                require(sc in groups, 'Command controller missing from pinned SG plan')
                city_starts.setdefault(sc, t)
                if kind == 'signal_sg':
                    sg = str(integer(r['dsd_no']))
                    require(sg in groups[sc] and groups[sc][sg] > 0, 'Unexpected command SG window')
            elif kind == 'ramp_meter':
                key = str(integer(r['sc_no'])) + ':1'
                signals.setdefault(key, {'start': t, 'end': end})
            elif kind == 'vsl':
                requested = integer(r['speed_kph'])
                require(requested > 0, 'Nonpositive VSL command')
                # Canonical setter uses the integral command as the distribution No.
                distributions[str(number(requested).normalize())] = requested
                for cls in (10, 20, 30, 70):
                    key = str(integer(r['dsd_no'])) + ':' + str(cls)
                    vsl.setdefault(key, {'start': t, 'end': end, 'apply_seconds': []})['apply_seconds'].append(t)
    for sc, start in city_starts.items():
        for sg, count in groups[sc].items():
            key = sc + ':' + sg
            require(key not in signals, 'Urban/meter ownership overlap')
            signals[key] = {'start': start, 'end': end, 'zero_window': count == 0}
    return {'passed': all(r['commands_exact'] and not r['state_changed_keys'] and not r['action_changed_keys'] for r in rows),
            'decisions': rows, 'signal_groups': signals, 'vsl_addresses': vsl,
            'sg_plan': plans[0][1], 'zero_window_owned_groups': [k for k, row in signals.items() if row.get('zero_window')],
            'vsl_distribution_ids': distributions,
            'command_scope': 'All ordered actual CSV actuator fields; metadata equality/hashes separately reported. Seven final JSON control fields.',
            'state_scope': 'All 19 named physical/history inputs; only checked run_provenance excluded.'}


def build_command_clock(arm, batches):
    receipt = read(pin(arm['completion']))
    prov = read(pin({'path': receipt['provenance_path'], 'sha256': receipt['provenance_sha256']}))
    sources = {}
    for key in ('main_vbs_runner', 'generated_vbs_config'):
        item = prov['files'][key]; p = path(item['path']); blob = p.read_bytes()
        require(hashlib.sha256(blob).hexdigest() == item['sha256'], 'Command clock native source pin changed: ' + key)
        sources[key] = blob.decode('utf-8-sig')
    groups, plan = expected_plan_groups(arm)
    capacities = native_options(sources['main_vbs_runner'], sources['generated_vbs_config'])
    native_clocks = native_clock_options(pin(plan).read_text(encoding='utf-8-sig'), groups)
    ramp_timing = ramp_meter_timing_authority(prov, sources['main_vbs_runner'])
    clock = CommandClock(batches, groups, capacities, native_clock_plans=native_clocks,
                         ramp_amber_sec=ramp_timing['amber_sec'])
    return clock, {'passed': True, 'native_source_pins': {k: prov['files'][k] for k in sources},
                   'sg_plan': plan, 'command_seconds': sorted(batches), 'ramp_meter_timing': ramp_timing,
                   'time_contract': 'Primary 1s only: immediate t uses latest command at t; post t uses latest command at t-1 and clock t-1.'}


def arm_from_run(run, receipt_sha):
    run = path(run); receipt = run / 'completion_receipt.json'; raw = read(receipt)
    folder = run / ('decisions_' + run.name)
    result = {'name': run.name, 'run_directory': str(run), 'run_id': raw['run_id'],
              'completion': {'path': str(receipt), 'sha256': receipt_sha},
              'signal_readback': str(folder / 'signal_readback.csv'), 'vsl_readback': str(folder / 'vsl_readback.csv')}
    for suffix in ('fzp', 'lsa'):
        matches = list((run / 'vissim_eval').glob('*.' + suffix))
        result[suffix] = str(matches[0]) if len(matches) == 1 else None
        result[suffix + '_file_count'] = len(matches)
    return result, integer(raw['terminal_sec'])


def verify(left, right, left_receipt_sha, right_receipt_sha):
    result = {'schema': 'com-execution-equivalence/v1', 'passed': False, 'checks': {},
              'actual_execution_equivalent': False, 'native_lsa_com_coverage_passed': False}
    checks = result['checks']; arms = []; end = []
    def check(name, function):
        try: value = function()
        except (OSError, ValueError, KeyError, TypeError, csv.Error, ArithmeticError) as exc:
            value = {'passed': False, 'error': type(exc).__name__ + ': ' + str(exc)}
        checks[name] = value
        return value
    def gates():
        for run, digest in ((left, left_receipt_sha), (right, right_receipt_sha)):
            arm, terminal = arm_from_run(run, digest); arms.append(arm); end.append(terminal)
        require(end[0] == end[1] and 1 < end[0] <= 5400, 'Pair period mismatch')
        require(path(left) != path(right) and arms[0]['run_id'] != arms[1]['run_id'], 'Same run substituted for independent pair')
        result['runs'] = arms
        prov = [completed(a, end[0]) for a in arms]
        result['control_interval_sec'] = integer(prov[0]['control_interval_sec'])
        return provenance_comparison(*prov)
    if not check('completion_and_provenance', gates)['passed']:
        result['payload_reads_skipped'] = True
        return result
    terminal = end[0]
    batches = [{}, {}]
    inputs = check('commands_and_state_inputs', lambda: run_inputs(arms, terminal, result['control_interval_sec'], batches))
    check('fzp', lambda: fzp_comparison(*(output_path(a, 'fzp') for a in arms), 1, terminal))
    if 'signal_groups' in inputs:
        clocks = {}
        for side, arm, batch in zip(('left', 'right'), arms, batches):
            def clock_setup(s=side, a=arm, b=batch):
                clock, proof = build_command_clock(a, b); clocks[s] = clock
                return proof
            check('command_clock_' + side, clock_setup)
        signal = []
        for side, arm in zip(('left', 'right'), arms):
            signal.append(check('signals_' + side, lambda a=arm, s=side: readbacks(output_path(a, 'signal_readback'), SG_FIELDS, inputs['signal_groups'], command_check=clocks[s].check_signal, require_dense=(s == 'left'), control_interval=result['control_interval_sec'])))
        if all(s['passed'] for s in signal):
            check('signal_transitions', lambda: transition_comparison(*signal))
            for side, arm, observed in zip(('left', 'right'), arms, signal):
                check('native_lsa_' + side, lambda a=arm, s=observed: lsa_coverage(output_path(a, 'lsa'), s, terminal))
        vsl = []
        for side, arm in zip(('left', 'right'), arms):
            vsl.append(check('vsl_' + side, lambda a=arm, s=side: readbacks(output_path(a, 'vsl_readback'), VSL_FIELDS, inputs['vsl_addresses'], command_check=clocks[s].check_vsl, numeric=True, distribution_ids=inputs['vsl_distribution_ids'])))
        if all(s['passed'] for s in vsl): check('vsl_transitions', lambda: transition_comparison(*vsl))
    physical = ('completion_and_provenance', 'commands_and_state_inputs', 'fzp', 'command_clock_left', 'command_clock_right', 'signal_transitions', 'vsl_transitions')
    result['actual_execution_equivalent'] = all(checks.get(k, {}).get('passed') is True for k in physical)
    result['native_lsa_com_coverage_passed'] = all(checks.get('native_lsa_' + s, {}).get('passed') is True for s in ('left', 'right'))
    result['passed'] = result['actual_execution_equivalent'] and result['native_lsa_com_coverage_passed']
    result['limitations'] = ['No causal performance attribution; both arms use the same instrumentation.',
                            'Equal fixed commands do not validate adaptive controller equivalence.',
                            'LSA coverage failure remains FAIL even if actual readbacks and FZP pass.']
    return result


def qualify_native_300(left, right):
    """Receipt-free record comparison for the fixed head-ON 300-second pair.

    This consumes canonical watchdog outputs after the owner confirms exit.
    Terminal log markers are required, but they never establish process exit.
    Completion/owned-process evidence remains the root's separate receipt.
    No synthetic receipt, model invocation or current source-inventory rehash.
    State JSON/history equivalence is outside this narrowly scoped entry point.
    """
    from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS

    result = {'schema': 'canonical-native-record-qualification/v1', 'passed': False,
              'payload_equivalent': False, 'actual_execution_equivalent': False,
              'completion_receipt_verified': False, 'process_exit_verified': False,
              'native_lsa_com_coverage_passed': False, 'checks': {}}
    checks = result['checks']; runs = []; provenance = []; batches = [{}, {}]
    groups = {}; meters = {}; prepared = {}; native_clocks = {}; ramp_timings = []
    expected_times = (1, 150, 300)

    def check(name, function):
        try: value = function()
        except (OSError, ValueError, KeyError, TypeError, csv.Error, ArithmeticError) as exc:
            value = {'passed': False, 'error': type(exc).__name__ + ': ' + str(exc)}
        checks[name] = value
        return value

    def source_gate():
        for folder in (left, right):
            run = path(folder); runs.append(run)
            p = run / ('run_provenance_' + run.name + '.json'); raw = read(p)
            require(raw['name'] == run.name and isinstance(raw['run_id'], str) and raw['run_id'],
                    'Canonical run/provenance identity differs')
            require(integer(raw['seed']) == 13 and integer(raw['sim_period_sec']) == 300
                    and integer(raw['control_interval_sec']) == 150
                    and raw['controller'] == 'diagnostic-signal-profile'
                    and raw['signal_observation']['options']['enabled'] is True
                    and raw['env']['RW_SIGNAL_OBSERVATION'] == '1',
                    'This entry point requires seed13, head-ON, fixed signal-profile and 300/150 seconds')
            log = run / ('runlog_' + run.name + '.txt'); lines = log.read_bytes().splitlines()
            require(lines.count(b'STAGE=SIM_DONE') == 1 and lines.count(b'SIM_SEC=300') == 1
                    and not any(row.startswith(b'ERROR') for row in lines), 'Missing/failed terminal runlog')
            for key in FAILURE_COUNTERS:
                require([r for r in lines if r.startswith((key+'=').encode())] == [(key+'=0').encode()],
                        'Failure counter missing/nonzero: ' + key)
            provenance.append(raw)
        require(runs[0] != runs[1] and provenance[0]['run_id'] != provenance[1]['run_id'],
                'Same run substituted for independent pair')
        comparison = provenance_comparison(*provenance)
        preflight_path = ROOT / 'diagnostics/com_execution_equivalence/native_all_sg_300_v1/preflight.json'
        prep = read(preflight_path)
        require(prep['schema'] == 'native-all-controlled-sg-recording-fixture/v1' and prep['prepared'] is True,
                'Wrong/unprepared native recording fixture')
        plan = pin(prep['actual_plan'])
        require(prep['actual_plan']['RW_MAINLINE_SG_ONLY'] == '1', 'Unexpected prepared SG scope')
        plan_groups, excluded = _plan_groups(plan.read_bytes(), True); groups.update(plan_groups)
        native_clocks.update(native_clock_options(plan.read_text(encoding='utf-8-sig'), groups))
        recorded = read(pin({'path': prep['recorded_groups_path'], 'sha256': prep['recorded_groups_sha256']}))
        inventory = {}
        for row in recorded:
            sc, sg = str(integer(row['sc_no'])), str(integer(row['sg_no'])); key = sc+':'+sg
            require(key not in inventory, 'Duplicate prepared SG address')
            inventory[key] = row
        for raw in provenance:
            require(raw['files']['network']['path'] == prep['network']
                    and raw['files']['network']['sha256'] == prep['network_sha256']
                    and raw['env']['RW_MAINLINE_SG_ONLY'] == '1', 'Run differs from prepared network/SG scope')
            config = pin(raw['files']['generated_vbs_config'])
            require(config.with_name(config.stem+'_sgplan.vbs').resolve() == plan,
                    'Prepared SG plan is not the recorded generated-config sibling')
            native_source = pin(raw['files']['main_vbs_runner']).read_text(encoding='utf-8-sig')
            native = native_options(native_source, config.read_text(encoding='utf-8-sig'))
            ramp_timings.append(ramp_meter_timing_authority(raw, native_source))
            require(not meters or meters == native, 'Native meter mapping differs between arms'); meters.update(native)
        require(ramp_timings[0] == ramp_timings[1], 'Ramp meter timing authority differs between arms')
        comparison['ramp_meter_timing'] = ramp_timings[0]
        expected = {sc+':'+sg: {'sc_no': int(sc), 'sg_no': int(sg), 'kind': 'urban',
                    'windows': n, 'red_only': n == 0} for sc, values in groups.items() for sg,n in values.items()}
        require(not (set(groups) & set(meters)), 'Urban/meter ownership overlap')
        expected.update({sc+':1': {'sc_no': int(sc), 'sg_no': 1, 'kind': 'meter', 'windows': 1,
                                 'red_only': False} for sc in meters})
        require(len(groups) == 17 and len(meters) == 8 and len(expected) == 144 and inventory == expected,
                'Prepared 136 urban + 8 meter catalog differs from pinned native sources')
        prepared.update(inventory)
        comparison['preparation'] = {'path': str(preflight_path), 'sha256': sha(preflight_path),
            'actual_plan': prep['actual_plan'], 'recorded_groups_sha256': prep['recorded_groups_sha256'],
            'expected_groups': len(expected), 'excluded_midblock_groups': excluded}
        comparison['run_pins'] = [{'run_directory': str(run), 'run_id': raw['run_id'],
            'provenance_sha256': sha(run / ('run_provenance_'+run.name+'.json')),
            'runlog_sha256': sha(run / ('runlog_'+run.name+'.txt'))} for run, raw in zip(runs, provenance)]
        return comparison

    if not check('recorded_provenance_and_terminal_logs', source_gate)['passed']:
        result['payload_reads_skipped'] = True
        return result

    def commands():
        # Native _segment_dsd_controls uses by-lane plus explicit extras.
        mapping_path = pin(provenance[0]['files']['control_mapping'])
        mapping = read(mapping_path)
        dsds = [integer(row['dsd_no']) for segment in mapping['segments']
                for row in [*segment['dsd_by_lane'].values(), *segment['extra_dsd_controls']]]
        require(dsds and min(dsds) > 0 and len(dsds) == len(set(dsds)), 'Missing/duplicate pinned DSD inventory')
        folders = [run / ('decisions_'+run.name) for run in runs]
        for folder in folders:
            require(folder.resolve(strict=True).is_relative_to(folder.parent), 'Decision directory outside run')
            require({p.name for p in folder.glob('action_*.csv')} ==
                    {f'action_{t:06d}.csv' for t in expected_times}, 'Missing/extra primary command time')
        comparisons = []; expected_vsl = {}; distributions = {}
        for t in expected_times:
            pair = []
            for side, folder in enumerate(folders):
                p = folder / f'action_{t:06d}.csv'
                with p.open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream); rows = list(reader)
                require(reader.fieldnames == list(ACTION_CSV_FIELDS) and rows
                        and all(None not in row and None not in row.values() for row in rows),
                        'Malformed/incomplete canonical action CSV')
                require(all(row['kind'] in ('signal', 'signal_sg', 'ramp_meter', 'vsl') for row in rows),
                        'Unknown physical command kind')
                delivered = [integer(row['dsd_no']) for row in rows if row['kind'] == 'vsl']
                require(len(delivered) == len(dsds) and set(delivered) == set(dsds), 'Missing/extra VSL command address')
                require(all(any(row['kind'] == kind for row in rows) for kind in ('signal', 'signal_sg', 'ramp_meter')),
                        'Missing physical command lever')
                require(Counter(str(integer(r['sc_no'])) for r in rows if r['kind'] == 'signal') ==
                        Counter({sc: 1 for sc in groups}) and
                        Counter(str(integer(r['sc_no'])) for r in rows if r['kind'] == 'ramp_meter') ==
                        Counter({sc: 1 for sc in meters}), 'Missing/duplicate/extra owned command controller')
                batches[side][t] = rows
                pair.append({'path': str(p), 'sha256': sha(p), 'rows': len(rows),
                    'physical': [{k: v for k,v in row.items() if k != 'metadata'} for row in rows],
                    'metadata_sha256': hashlib.sha256(json.dumps([r['metadata'] for r in rows]).encode()).hexdigest()})
            same = pair[0]['physical'] == pair[1]['physical']
            difference = next(({'row_one_based': i, 'left': a, 'right': b}
                for i,(a,b) in enumerate(zip_longest(pair[0]['physical'], pair[1]['physical']), 1) if a != b), None)
            comparisons.append({'sim_sec': t, 'passed': same, 'first_difference': difference,
                'artifacts': [{k:v for k,v in item.items() if k != 'physical'} for item in pair]})
            for row in batches[0][t]:
                if row['kind'] != 'vsl': continue
                speed = integer(row['speed_kph']); require(speed > 0, 'Nonpositive VSL command')
                distributions[str(number(speed).normalize())] = speed
                for cls in (10, 20, 30, 70):
                    key = str(integer(row['dsd_no']))+':'+str(cls)
                    expected_vsl.setdefault(key, {'start': 1, 'end': 300, 'apply_seconds': []})['apply_seconds'].append(t)
        return {'passed': all(row['passed'] for row in comparisons), 'decisions': comparisons,
                'mapping_pin': {'path': str(mapping_path), 'sha256': sha(mapping_path)},
                'vsl_addresses': expected_vsl, 'vsl_distribution_ids': distributions,
                'scope': 'Every ordered actual CSV physical field; metadata excluded and hashed separately. No state JSON comparison.'}

    inputs = check('action_csv_physical_fields', commands)
    def native_file(run, suffix):
        files = list((run / 'vissim_eval').glob('*.'+suffix))
        require(len(files) == 1 and files[0].resolve().is_relative_to(run), 'Missing/ambiguous native '+suffix)
        return files[0]
    check('fzp', lambda: fzp_comparison(native_file(runs[0], 'fzp'), native_file(runs[1], 'fzp'), 1, 300))
    if inputs.get('passed') is True:
        observed = []; signals = []; ldp_records = []
        for side, run, batch in zip(('left', 'right'), runs, batches):
            clock_result = check('clock_'+side, lambda batch=batch: {'passed': True, 'clock': CommandClock(
                batch, groups, meters, native_clock_plans=native_clocks, ramp_amber_sec=ramp_timings[0]['amber_sec'])})
            clock = clock_result.pop('clock', None)
            if clock is None: continue
            folder = run / ('decisions_'+run.name)
            observed.append(check('vsl_'+side, lambda: readbacks(folder / 'vsl_readback.csv', VSL_FIELDS,
                inputs['vsl_addresses'], command_check=clock.check_vsl, numeric=True,
                distribution_ids=inputs['vsl_distribution_ids'])))
            expected_sg = {key: {'start': 1, 'end': 300, 'zero_window': value['red_only']}
                           for key,value in prepared.items()}
            actual = check('signals_'+side, lambda: readbacks(folder / 'signal_readback.csv', SG_FIELDS,
                expected_sg, command_check=clock.check_signal, require_dense=side == 'left', control_interval=150))
            signals.append(actual)
            if actual['passed']:
                check('native_lsa_'+side, lambda: lsa_coverage(native_file(run, 'lsa'), actual, 300))
            def ldp_check():
                from diagnostics.validate_native_signal_record import read_ldp_frames, check_ldp_command_clock
                expected = {int(sc): [int(sg) for sg in values] for sc,values in groups.items()}
                expected.update({int(sc): [1] for sc in meters})
                stem = Path(provenance[0]['files']['network']['path']).stem
                candidates = list((run / 'vissim_eval').glob('*.ldp')); files = {}
                for sc in expected:
                    selected = [p for p in candidates if p.name == f'{stem}_{sc}_001.ldp']
                    require(len(selected) == 1 and selected[0].resolve().is_relative_to(run),
                            'Missing/ambiguous prepared native LDP controller: '+str(sc))
                    files[sc] = selected[0]
                record = read_ldp_frames(files, expected, 1, 300)
                ldp_records.append(record)
                clock_check = check_ldp_command_clock(record, clock, {key: 1 for key in prepared})
                return {**{k:v for k,v in record.items() if k != 'frames'}, 'passed': clock_check['passed'],
                    'command_clock': clock_check, 'excluded_unassessed_ldp_files':
                    [str(p) for p in candidates if p not in files.values()]}
            check('native_ldp_'+side, ldp_check)
        if len(observed) == 2 and all(row['passed'] for row in observed):
            check('vsl_apply_readbacks', lambda: transition_comparison(*observed))
        if len(signals) == 2 and all(row['passed'] for row in signals):
            check('signal_transitions', lambda: transition_comparison(*signals))
        if len(ldp_records) == 2:
            def compare_ldp():
                differences = [{'sim_sec': t, 'address': key, 'left': value,
                    'right': ldp_records[1]['frames'][t][key]} for t,row in ldp_records[0]['frames'].items()
                    for key,value in row.items() if value != ldp_records[1]['frames'][t][key]]
                return {'passed': not differences, 'different_samples': len(differences),
                        'first_difference': next(iter(differences), None), 'samples': 144*300,
                        'scope': 'All native frames including initial pre-COM frame; no receipt/process assertion'}
            check('native_ldp_pair', compare_ldp)
    result['payload_equivalent'] = all(checks.get(key, {}).get('passed') is True for key in
        ('recorded_provenance_and_terminal_logs', 'action_csv_physical_fields', 'fzp', 'vsl_apply_readbacks'))
    result['recorded_execution_equivalent'] = result['payload_equivalent'] and all(
        checks.get(key, {}).get('passed') is True for key in
        ('signal_transitions', 'native_ldp_left', 'native_ldp_right', 'native_ldp_pair'))
    result['native_lsa_com_coverage_passed'] = all(checks.get('native_lsa_'+side, {}).get('passed') is True
                                               for side in ('left', 'right'))
    result['passed'] = result['recorded_execution_equivalent'] and result['native_lsa_com_coverage_passed']
    result['limitations'] = ['Record qualification only; root must supply independent owned-process/completion evidence.',
        'First recorded command is at 1s; launcher ControlStartSec declaration is verified separately.',
        'State/head-history equivalence is not checked by this short entry point.',
        'Native all-SG LDP and LSA coverage are separate required checks, never inferred from command equality.']
    return result


def verify_native_execution(run, terminal):
    """Audit one completed canonical run, without FZP or process inference.

    Native LDP supplies continuous actual states; command rows supply only the
    independent expectation. Actual setter readbacks remain separate evidence.
    The caller owns watchdog exit/PID checks (including when composing a receipt).
    Existing pair/short qualifier verdicts are deliberately unchanged.
    """
    import xml.etree.ElementTree as ET
    from bisect import bisect_right
    from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS
    from diagnostics.validate_native_signal_record import read_ldp_frames, check_ldp_command_clock

    result = {'schema': 'single-run-native-execution/v1', 'passed': False,
              'native_execution_passed': False, 'native_lsa_com_coverage_passed': False,
              'process_exit_verified': False, 'completion_receipt_verified': False, 'checks': {}}
    checks = result['checks']; sources = {}; batches = {}; expected_sg = {}; expected_vsl = {}
    distributions = {}; groups = {}; meters = {}; native_clocks = {}; clock = None

    def check(name, function):
        try: value = function()
        except (OSError, ValueError, KeyError, TypeError, csv.Error, ArithmeticError, ET.ParseError) as exc:
            value = {'passed': False, 'error': type(exc).__name__ + ': ' + str(exc)}
        checks[name] = value
        return value

    def source_gate():
        nonlocal run, terminal
        run = path(run); terminal = integer(terminal)
        require(terminal > 1, 'Post-control terminal must exceed one second')
        pp = run / ('run_provenance_' + run.name + '.json'); prov = read(pp)
        require(prov['name'] == run.name and isinstance(prov['run_id'], str) and prov['run_id']
                and integer(prov['sim_period_sec']) == terminal, 'Run/provenance identity or terminal differs')
        log = run / ('runlog_' + run.name + '.txt'); lines = log.read_bytes().splitlines()
        require(lines.count(b'STAGE=SIM_DONE') == 1 and lines.count(f'SIM_SEC={terminal}'.encode()) == 1
                and not any(row.startswith(b'ERROR') for row in lines), 'Missing/failed terminal runlog')
        for key in FAILURE_COUNTERS:
            require([row for row in lines if row.startswith((key+'=').encode())] == [(key+'=0').encode()],
                    'Failure counter missing/nonzero: ' + key)
        native_paths = {key: pin(prov['files'][key]) for key in
                        ('network', 'main_vbs_runner', 'generated_vbs_config', 'control_mapping')}
        config = native_paths['generated_vbs_config']
        sibling = config.with_name(config.stem+'_sgplan.vbs').resolve(strict=True)
        plan_source = None
        if 'signal_group_plan' in prov['files']:
            plan = pin(prov['files']['signal_group_plan'])
            plan_source = {'kind': 'run_manifest.files.signal_group_plan', 'pin': prov['files']['signal_group_plan']}
        elif (run / 'completion_receipt.json').is_file():
            receipt = read(run / 'completion_receipt.json')
            require(path(receipt['provenance_path']) == pp and receipt['provenance_sha256'] == sha(pp),
                    'Plan preparation receipt is for another manifest')
            proof_path = pin(receipt['preparation_checks']); proof = read(proof_path)
            pins = [digest for scope in ('source_sha256', 'generated_sha256')
                    for name,digest in proof.get(scope, {}).items() if Path(name).resolve() == sibling]
            require(len(pins) == 1, 'Sibling plan needs one explicit preparation SHA')
            plan = pin({'path': str(sibling), 'sha256': pins[0]})
            plan_source = {'kind': 'existing_receipt_preparation', 'path': str(proof_path), 'sha256': sha(proof_path)}
        else:
            # Historical record-only fixtures predate the manifest sibling pin.
            prep_path = native_paths['network'].parent / 'preflight.json'; prep = read(prep_path)
            require(prep.get('schema') == 'native-all-controlled-sg-recording-fixture/v1'
                    and prep.get('prepared') is True and path(prep['network']) == native_paths['network']
                    and prep['network_sha256'] == prov['files']['network']['sha256'],
                    'No matching historical recording-fixture plan authority')
            plan = pin(prep['actual_plan'])
            plan_source = {'kind': 'historical_network_sibling_preflight', 'path': str(prep_path), 'sha256': sha(prep_path)}
        require(plan == sibling, 'Pinned SG plan is not actual generated-config sibling')
        parsed, excluded = _plan_groups(plan.read_bytes(), prov['env'].get('RW_MAINLINE_SG_ONLY') == '1')
        groups.update(parsed)
        native_clocks.update(native_clock_options(plan.read_text(encoding='utf-8-sig'), groups))
        meters.update(native_options(native_paths['main_vbs_runner'].read_text(encoding='utf-8-sig'),
                                     config.read_text(encoding='utf-8-sig')))
        ramp_timing = ramp_meter_timing_authority(prov, native_paths['main_vbs_runner'].read_text(encoding='utf-8-sig'))
        require(not (set(groups) & set(meters)), 'Urban/meter ownership overlap')
        mapping = read(native_paths['control_mapping'])
        require({str(integer(row['sc_no'])) for row in mapping['signals']} == set(groups),
                'Pinned mapping and sibling urban controller sets differ')
        require(Counter(str(integer(row['sc_no'])) for row in mapping['ramp_meters']) == Counter({sc:1 for sc in meters}),
                'Pinned mapping and native meter controllers differ')
        expected = {int(sc): [int(sg) for sg in values] for sc,values in groups.items()}
        expected.update({int(sc): [1] for sc in meters})
        network = ET.parse(native_paths['network']).getroot()
        output = network.find('./evaluation/scDetRec')
        require(output is not None and output.get('writeFile') == 'true', 'Actual network has no enabled native detector recording')
        for sc, sgs in expected.items():
            controller = network.find(f'./signalControllers/signalController[@no="{sc}"]')
            require(controller is not None, 'Recorded controller absent from actual network')
            configured = controller.findall('./scDetRecConf/signalOutputConfigurationElement')
            require([r.get('configName') for r in configured[:2]] == ['SIM_SEK','UML_SEK']
                    and len(configured) == len(sgs)+2
                    and all(r.get('configName') == 'SG_BILD' for r in configured[2:]),
                    'Actual network recording columns differ from all-owned SG catalog')
            addresses = [r.get('sg') for r in configured[2:]]
            require(len(addresses) == len(set(addresses)) and set(addresses) == {f'{sc} {sg}' for sg in sgs},
                    'Missing/duplicate/extra recorded SG address in actual network')
        sources.update(provenance=prov, expected_groups=expected, mapping=mapping, plan_path=plan,
                       ramp_meter_timing=ramp_timing)
        result.update(run_directory=str(run), run_id=prov['run_id'], terminal_sec=terminal)
        return {'passed': True, 'provenance': {'path': str(pp), 'sha256': sha(pp)},
                'runlog': {'path': str(log), 'sha256': sha(log)},
                'native_source_pins': {key:prov['files'][key] for key in native_paths},
                'ramp_meter_timing': ramp_timing,
                'plan': {'path': str(plan), 'sha256': sha(plan), 'authority': plan_source},
                'expected_recorded_groups': sum(map(len, expected.values())),
                'excluded_midblock_groups': excluded, 'network_scope': 'Actual loaded files.network; no source-network substitution'}

    if not check('sources_and_terminal_log', source_gate)['passed']: return result

    def commands():
        nonlocal clock
        folder = run / ('decisions_'+run.name)
        require(folder.resolve(strict=True).is_relative_to(run), 'Decision folder outside run')
        interval = integer(sources['provenance']['control_interval_sec']); require(interval > 0, 'Invalid control cadence')
        actual_files = list(folder.glob('action_*.csv'))
        times = [integer(p.stem.split('_')[1]) for p in actual_files]
        require(len(times) == len(set(times)) and set(times) == {1,*range(interval,terminal+1,interval)},
                'Missing/extra actual command application time')
        dsds = [integer(row['dsd_no']) for segment in sources['mapping']['segments']
                for row in [*segment['dsd_by_lane'].values(), *segment.get('extra_dsd_controls',[])]]
        require(dsds and len(dsds) == len(set(dsds)), 'Missing/duplicate mapped DSD address')
        city_started = False; artifacts = []
        for t in sorted(times):
            p = folder/f'action_{t:06d}.csv'
            with p.open(encoding='utf-8-sig',newline='') as stream:
                reader = csv.DictReader(stream); rows = list(reader)
            require(reader.fieldnames == list(ACTION_CSV_FIELDS) and rows
                    and all(None not in row and None not in row.values() for row in rows), 'Malformed canonical action CSV')
            require(Counter(integer(r['dsd_no']) for r in rows if r['kind']=='vsl') == Counter(dsds),
                    'Missing/duplicate/extra actual VSL command address')
            require(Counter(str(integer(r['sc_no'])) for r in rows if r['kind']=='ramp_meter') == Counter({sc:1 for sc in meters}),
                    'Missing/duplicate/extra actual meter command address')
            city = Counter(str(integer(r['sc_no'])) for r in rows if r['kind']=='signal')
            require(not city_started or bool(city), 'Urban command disappears after control starts')
            if city:
                require(city == Counter({sc:1 for sc in groups}), 'Partial/duplicate urban controller batch')
                city_started = True
                for sc, values in groups.items():
                    for sg,count in values.items(): expected_sg.setdefault(sc+':'+sg, {'start':t,'end':terminal,'zero_window':count==0})
            for sc in meters: expected_sg.setdefault(sc+':1', {'start':t,'end':terminal})
            for row in rows:
                if row['kind'] != 'vsl': continue
                speed = integer(row['speed_kph']); require(speed > 0, 'Nonpositive VSL command')
                distributions[str(number(speed).normalize())] = speed
                for cls in (10,20,30,70):
                    key = str(integer(row['dsd_no']))+':'+str(cls)
                    expected_vsl.setdefault(key, {'start':t,'end':terminal,'apply_seconds':[]})['apply_seconds'].append(t)
            batches[t] = rows
            artifacts.append({'sim_sec':t,'path':str(p),'sha256':sha(p),'rows':len(rows),'kinds':dict(Counter(r['kind'] for r in rows))})
        clock = CommandClock(batches, groups, meters, native_clock_plans=native_clocks,
                             ramp_amber_sec=sources['ramp_meter_timing']['amber_sec'])
        return {'passed':True,'decisions':artifacts,'first_control_sec_by_group':{k:v['start'] for k,v in expected_sg.items()},
                'controlled_signal_groups':len(expected_sg),'vsl_class_addresses':len(expected_vsl),
                'red_only_controlled_groups':[k for k,v in expected_sg.items() if v.get('zero_window')],
                'interval_sec':interval,'scope':'Actual CSV times and full mapped rows; no green/offset inferred from warmup JSON'}

    if not check('actual_commands', commands)['passed']: return result
    folder = run / ('decisions_'+run.name)
    signals = check('actual_signal_readbacks', lambda: readbacks(folder/'signal_readback.csv', SG_FIELDS, expected_sg,
        command_check=clock.check_signal, control_interval=checks['actual_commands']['interval_sec']))
    check('actual_vsl_apply_readbacks', lambda: readbacks(folder/'vsl_readback.csv', VSL_FIELDS, expected_vsl,
        command_check=clock.check_vsl, numeric=True, distribution_ids=distributions))

    def changed_writes():
        require(signals['passed'], 'Actual signal readback parser failed')
        actual = set()
        with (folder/'signal_readback.csv').open(encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream):
                if row['stage']=='immediate':
                    actual.add((integer(row['sim_sec']),row['sc_no']+':'+row['sg_no'],state(row['readback_state'])))
        needed = []
        for key, window in expected_sg.items():
            sc,sg = key.split(':'); last = None
            for t in range(window['start'],terminal+1):
                snapshot = clock.snapshots[bisect_right(clock.times,t)-1]
                value = (clock.expected_meter_state(snapshot['ramps'][sc],t) if sc in meters
                         else clock.expected_urban_state(sc,snapshot['signals'][sc],sg,t))
                if last != value: needed.append((t,key,value))
                last = value
        missing = [item for item in needed if item not in actual]
        return {'passed':not missing,'required_initial_or_changed_immediates':len(needed),'missing':missing,
                'scope':'Each initial application and command-clock state change needs an actual immediate row; unchanged setter skips are allowed'}
    check('actual_initial_and_changed_writes', changed_writes)

    def ldp():
        expected = sources['expected_groups']; candidates = list((run/'vissim_eval').glob('*.ldp')); files = {}
        stem = Path(sources['provenance']['files']['network']['path']).stem
        for sc in expected:
            matches = [p for p in candidates if p.name == f'{stem}_{sc}_001.ldp']
            require(len(matches)==1 and matches[0].resolve().is_relative_to(run), 'Missing/ambiguous actual native LDP SC '+str(sc))
            files[sc] = matches[0]
        record = read_ldp_frames(files,expected,1,terminal)
        require(all(count == terminal for count in record['file_row_count_by_sc'].values()),
                'Native LDP contains rows outside the completed run extent')
        controlled = {int(sc): [int(sg) for sg in sgs if sc+':'+sg in expected_sg]
                      for sc,sgs in {**groups,**{sc:{'1':1} for sc in meters}}.items()}
        controlled = {sc:sgs for sc,sgs in controlled.items() if sgs}
        subset = {**record,'expected_groups':controlled,
                  'frames':{t:{k:v for k,v in row.items() if k in expected_sg} for t,row in record['frames'].items()}}
        comparison = check_ldp_command_clock(subset,clock,{k:v['start'] for k,v in expected_sg.items()})
        return {**{k:v for k,v in record.items() if k!='frames'},'passed':comparison['passed'],
                'command_clock':comparison,'native_only_groups':[f'{sc}:{sg}' for sc,sgs in expected.items()
                    for sg in sgs if f'{sc}:{sg}' not in expected_sg],
                'excluded_unassessed_ldp_files':[str(p) for p in candidates if p not in files.values()]}
    check('native_ldp',ldp)
    def lsa():
        require(signals['passed'], 'Actual signal observations required for independent LSA check')
        candidates = list((run/'vissim_eval').glob('*.lsa'))
        require(len(candidates)==1 and candidates[0].resolve().is_relative_to(run), 'Missing/ambiguous native LSA')
        return lsa_coverage(candidates[0],signals,terminal)
    check('native_lsa',lsa)
    result['native_execution_passed'] = all(checks[k]['passed'] is True for k in
        ('sources_and_terminal_log','actual_commands','actual_signal_readbacks','actual_vsl_apply_readbacks',
         'actual_initial_and_changed_writes','native_ldp'))
    result['native_lsa_com_coverage_passed'] = checks['native_lsa']['passed'] is True
    result['passed'] = result['native_execution_passed'] and result['native_lsa_com_coverage_passed']
    result['limitations'] = ['Native execution evidence only; no FZP, model, policy quality or process-exit assertion.',
        'Canonical primary 1s stepping and its recorded decision cadence only; no event-mode generalization.',
        'LDP covers every source-owned SG at 1..terminal; command comparison begins after each actual first control.',
        'LDP t uses the t-1 post-step command clock; first-control immediate actual readbacks are separately mandatory.',
        'Native-only urban groups in meter-only diagnostics are covered but not assigned invented COM commands.',
        'Native LSA failure remains independent FAIL; no LDP/command substitution into LSA.']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--left', type=Path, required=True, help='Completed old-write/full-readback run')
    parser.add_argument('--right', type=Path, required=True, help='Completed changed-write/sparse-readback run')
    parser.add_argument('--left-receipt-sha256')
    parser.add_argument('--right-receipt-sha256')
    parser.add_argument('--native-record-300', action='store_true', help='Receipt-free 300s native record qualification; completion remains external')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'Output already exists; preserve previous evidence')
    if args.native_record_300:
        require(args.left_receipt_sha256 is None and args.right_receipt_sha256 is None, 'Receipt arguments do not belong to record-only mode')
        result = qualify_native_300(args.left, args.right)
    else:
        require(args.left_receipt_sha256 and args.right_receipt_sha256, 'Both receipt SHA arguments required for the existing pair verifier')
        result = verify(args.left, args.right, args.left_receipt_sha256, args.right_receipt_sha256)
    result['validator_sha256'] = sha(Path(__file__))
    result['command_clock_source_sha256'] = {str(p.relative_to(ROOT)): sha(p) for p in
        (Path(__file__).with_name('command_clock.py'), ROOT / 'diagnostics/live_beta0_first_interval_audit.py',
         ROOT / 'evaluation/controllers/signal_timing_oracle.py')}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')
    summary = {k: result[k] for k in ('passed', 'actual_execution_equivalent', 'native_lsa_com_coverage_passed')}
    if args.native_record_300: summary['recorded_execution_equivalent'] = result.get('recorded_execution_equivalent', False)
    print(json.dumps(summary))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__': main()
