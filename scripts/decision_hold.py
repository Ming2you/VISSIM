r"""K8-8: hold the previous applied command when a decision dies on an exception (runtime.decision_error_policy).

Called only by run_real_world_stackelberg_controller.vbs (RunDecisionHold), after the adapter exited 1 with the
decision failure report of decision_failure_report.py, and only when the tuning key
runtime.decision_error_policy = "hold_previous_on_exception" (K8 amendment 21, P-1 .. P-12, section 3).

    python decision_hold.py --state-json <state_T.json> --failed-action-json <action_T.json>
        --failed-action-csv <action_T.csv> --previous-action-json <action_S.json> --tuning-json <tuning>
        --control-start-sec <n> --decision-exit 1

What it does (amendment 21 section 3.1 "helper 출력 순서"):
  1. eligibility E1-E10 (section 3.2); any refusal -> stderr 'DECISION_HOLD_REFUSED reason=<E> detail=<..>',
     action_T.hold_error.txt, exit 3, and no file is changed;
  2. partial outputs of the failed decision -> <name>.failed_decision;
  3. held CSV action_T.csv = the previous CSV bytes (temp file + os.replace);
  4. held JSON action_T.json = the previous JSON without prediction / prediction_error / projection_diagnostics /
     diagnostics.sdmpc_prediction_sequence and with a small metadata (P-6), json.dumps(ensure_ascii=False,
     indent=2) written like the adapter (text mode, UTF-8);
  5. receipt action_T.hold.json (last);
  6. stdout one line 'HOLD_OK sim_sec=T source_sim_sec=S origin_sim_sec=O chain=n csv_sha256=.. json_sha256=..
     type=<outer> root_type=<root>', exit 0.
A helper exception -> full traceback in action_T.hold_error.txt, stderr 'DECISION_HOLD_EXCEPTION type=..', exit 1.
Standard library only (no evaluation, no numpy).  No deadline of its own; wall clock only in receipt['wall'].
The held JSON and CSV bytes depend only on (previous JSON, previous CSV bytes, T, policy constants).
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys
import traceback
from pathlib import Path

SCHEMA = 'hold-on-exception/v1'
RECEIPT_SCHEMA = 'hold-on-exception-receipt/v1'
POLICY = 'hold_previous_on_exception'
STRICT = 'strict'
VALID_POLICIES = (STRICT, POLICY)
CONTROL_INTERVAL_SEC = 150
DERIVED_SCHEMA = 'obs150-derived/v1'          # evaluation.controllers.obs150_contract.DERIVED_SCHEMA
# evaluation.controllers.action_csv_schema.ACTION_CSV_FIELDS (scripts/tests/test_decision_hold.py pins equality)
ACTION_CSV_FIELDS = ('kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane', 'speed_kph', 'p1_green', 'p2_green',
                     'p3_green', 'p4_green', 'offset', 'rate_vph', 'green_sec', 'metadata')
# P-4 (amendment 21, D-K9-13 + D-K9-17 Q-H3 + correction 1): exactly these eight names stop the run.
EXCLUDED_TYPES = ('DecisionDeadline', 'TimeoutError',
                  'MemoryError', 'KeyboardInterrupt', 'GeneratorExit', 'BrokenProcessPool',
                  'BrokenPipeError', 'ConnectionResetError')
# P-5: (file name, function name) of the previous-command / history contract, and the message.
CONTRACT_PAIRS = (('vissim_stackelberg_adapter.py', 'load_joint_historical_reference'),
                  ('vissim_stackelberg_adapter.py', 'joint_runtime_source_pins'),
                  ('vissim_stackelberg_adapter.py', 'control_from_json'),
                  ('sdmpc.py', 'load_prices'),
                  ('physical_ramp_branches.py', 'read_recorded_control'),
                  ('physical_ramp_branches.py', 'held_actual_reference'),
                  ('lane_plant_runtime.py', 'applied_vsl_from_previous'),
                  ('offramp_split_forecast.py', 'window_counts'),
                  ('area_meter_finalization.py', 'configure'))
CONTRACT_MESSAGES = ('Invalid applied central multiplier warm start',)
REMOVED = ('prediction', 'prediction_error', 'projection_diagnostics', 'diagnostics.sdmpc_prediction_sequence')
CARRIED_PREFIXES = ('far_rate_est_', 'sat_est_')
PARTIAL_SUFFIXES = ('.json', '.csv', '.json.sdmpc_pending', '.joint_written.json')
HEADER_RE = re.compile(r'^[A-Za-z_][\w.]*(: .*|:)?$')
TRACEBACK_HEAD = 'Traceback (most recent call last):'
FRAME_RE = re.compile(r'^\s*File "(.+)", line \d+, in (.+?)\s*$')
SUMMARY_PREFIX = 'DECISION_FAILED type='
ACTION_RE = re.compile(r'^action_(\d{6})\.json$')
EXIT_REFUSED = 3
EXIT_EXCEPTION = 1


class Refusal(Exception):
    def __init__(self, code, detail):
        super().__init__(f'{code} {detail}')
        self.code, self.detail = code, detail


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def file_pin(path):
    path = Path(path)
    data = path.read_bytes()
    return {'name': path.name, 'sha256': sha256_bytes(data), 'size': len(data)}


def safe(text):
    """One output line that never carries the runner's failure marker (amendment 21 P-7, section 4.1 K8)."""
    return ' '.join(str(text).replace('DECISION_FAILED', 'DECISION-FAILED').split())


def lists_sha256():
    doc = {'excluded_types': list(EXCLUDED_TYPES), 'contract_pairs': [list(p) for p in CONTRACT_PAIRS],
           'contract_messages': list(CONTRACT_MESSAGES)}
    return sha256_bytes(json.dumps(doc, sort_keys=True, separators=(',', ':')).encode('utf-8'))


# ------------------------------------------------------------------ tuning (same chain rule as WD / LP)
def read_policy_chain(tuning_path):
    """(effective policy, chain) of runtime.decision_error_policy along the extends chain, child first.

    Every file of the chain is read.  A runtime deadline key, a non-object runtime, or a declared policy
    that is not a string in VALID_POLICIES raises ValueError.  The child-most declared value is effective; no
    declaration anywhere = 'strict'.  Same rule as WD Read-DecisionErrorPolicy and LP decision_error_policy."""
    path = Path(tuning_path).resolve()
    seen, chain, effective = set(), [], None
    while True:
        if not path.is_file():
            raise ValueError(f'tuning file missing: {path}')
        key = str(path).lower()
        if key in seen:
            raise ValueError(f'cyclic tuning extends: {path}')
        seen.add(key)
        doc = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(doc, dict):
            raise ValueError(f'tuning is not an object: {path}')
        chain.append(str(path))
        if 'runtime' in doc:
            runtime = doc['runtime']
            if not isinstance(runtime, dict):
                raise ValueError(f'runtime is not an object: {path}')
            if 'decision_timeout_sec' in runtime:
                raise ValueError(f'runtime has a decision deadline key (refused, amendment 21 P-1): {path}')
            if 'decision_error_policy' in runtime:
                value = runtime['decision_error_policy']
                if not isinstance(value, str) or value not in VALID_POLICIES:
                    raise ValueError(f'runtime.decision_error_policy={value!r} is not one of {VALID_POLICIES}: {path}')
                if effective is None:
                    effective = value
        parent = doc.get('extends')
        if not parent:
            break
        parent = Path(str(parent))
        path = (parent if parent.is_absolute() else path.parent / parent).resolve()
    return (effective or STRICT), chain


# ------------------------------------------------------------------ failure report parsing
def read_lines_replace(path):
    """Bytes split on LF, each line decoded UTF-8 with errors='replace', trailing CR removed (amendment 21 E2)."""
    return [raw.decode('utf-8', errors='replace').rstrip('\r') for raw in Path(path).read_bytes().split(b'\n')]


def parse_summary(line):
    rest = line[len(SUMMARY_PREFIX):]
    head, sep, traceback_path = rest.rpartition(' traceback=')
    if not sep:
        return None
    outer, _, rest2 = head.partition(' message=')
    message, _, root = rest2.partition(' root_error=')
    return {'type': outer.strip(), 'message': message.strip(), 'root_error': root.strip(),
            'traceback': traceback_path.strip()}


def norm_path(text):
    return str(text).strip().replace('\\', '/').lower()


def header_type(line):
    """Exception type name of a column-0 exception header line, else None (amendment 21 P-4)."""
    if line == TRACEBACK_HEAD or not HEADER_RE.match(line):
        return None
    return line.split(':', 1)[0].split('.')[-1]


def chain_types(error_lines, summary):
    types = [t for t in (header_type(line) for line in error_lines) if t]
    extra = [summary.get('type', ''), summary.get('root_error', '')] if summary else []
    types += [t for t in (header_type(line) for line in extra if line) if t]
    return types


def frames(error_lines):
    out = []
    for line in error_lines:
        m = FRAME_RE.match(line)
        if m:
            out.append((re.split(r'[\\/]', m.group(1))[-1], m.group(2).strip()))
    return out


# ------------------------------------------------------------------ eligibility E1-E10
def check(args):
    """Every check before any file changes. Returns the facts the writer needs; raises Refusal."""
    failed_json = Path(args.failed_action_json)
    m = ACTION_RE.match(failed_json.name)
    if m is None:
        raise ValueError(f'--failed-action-json is not action_<T6>.json: {failed_json}')
    T = int(m.group(1))
    if Path(args.failed_action_csv) != failed_json.with_suffix('.csv'):
        raise ValueError('--failed-action-csv is not the CSV beside --failed-action-json')
    if args.decision_exit != 1:
        raise ValueError(f'--decision-exit must be 1 (exception path only), got {args.decision_exit}')
    folder = failed_json.parent
    t6 = '%06d' % T
    facts = {'T': T, 't6': t6, 'folder': folder, 'checks': {}}

    # E1 tuning policy
    try:
        policy, chain = read_policy_chain(args.tuning_json)
    except (ValueError, OSError) as error:
        raise Refusal('E1', f'tuning: {error}')
    if policy != POLICY:
        raise Refusal('E1', f'runtime.decision_error_policy={policy} (not {POLICY})')
    facts['tuning_chain'] = chain
    facts['checks']['E1'] = 'pass'

    # E2 the decision's own exception report
    error_txt = failed_json.with_suffix('.error.txt')
    stderr_txt = folder / f'action_{t6}.stderr.txt'
    stdout_txt = folder / f'action_{t6}.stdout.txt'
    if not error_txt.is_file():
        raise Refusal('E2', f'{error_txt.name} missing')
    if not stderr_txt.is_file():
        raise Refusal('E2', f'{stderr_txt.name} missing')
    summaries = [line for line in read_lines_replace(stderr_txt) if line.startswith(SUMMARY_PREFIX)]
    if len(summaries) != 1:
        raise Refusal('E2', f'{stderr_txt.name} summary_lines={len(summaries)} (need exactly 1)')
    summary = parse_summary(summaries[0])
    if summary is None or norm_path(summary['traceback']) != norm_path(error_txt):
        raise Refusal('E2', f'summary traceback path is not {error_txt.name}')
    error_lines = read_lines_replace(error_txt)
    facts.update(error_txt=error_txt, stderr_txt=stderr_txt, stdout_txt=stdout_txt, summary=summary,
                 summary_line=summaries[0], error_lines=error_lines)
    facts['checks']['E2'] = 'pass'

    # E3 excluded types anywhere in the chain
    types = chain_types(error_lines, summary)
    hit = sorted({t for t in types if t in EXCLUDED_TYPES})
    if hit:
        raise Refusal('E3', 'excluded exception type(s) ' + ','.join(hit))
    facts['chain_types'] = types
    facts['checks']['E3'] = 'pass'

    # E4 previous-command / history contract failures
    pairs = frames(error_lines)
    contract = sorted({'%s:%s' % p for p in pairs if p in CONTRACT_PAIRS})
    text = '\n'.join(error_lines)
    messages = [msg for msg in CONTRACT_MESSAGES if msg in text]
    if contract or messages:
        raise Refusal('E4', 'contract frame(s) ' + ','.join(contract + messages))
    facts['frames'] = pairs
    facts['checks']['E4'] = 'pass'

    # E5 range
    state_path = Path(args.state_json)
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    S = T - CONTROL_INTERVAL_SEC
    cs = int(args.control_start_sec)
    sim_sec, interval = state.get('sim_sec'), state.get('control_interval_sec')
    if (not isinstance(sim_sec, (int, float)) or isinstance(sim_sec, bool) or float(sim_sec) != float(T)
            or not isinstance(interval, (int, float)) or isinstance(interval, bool)
            or float(interval) != float(CONTROL_INTERVAL_SEC) or cs < 0 or S < cs):
        raise Refusal('E5', f'state sim_sec/control_interval_sec or range: T={T} S={S} control_start_sec={cs}')
    facts.update(state_path=state_path, state=state, S=S)
    facts['checks']['E5'] = 'pass'

    # E6 previous command = the immediately preceding action of this run (ADP load_joint_historical_reference)
    prev_json = Path(args.previous_action_json)
    if not prev_json.is_file():
        raise Refusal('E6', f'previous action missing: {prev_json.name}')
    prev_bytes = prev_json.read_bytes()
    prev = json.loads(prev_bytes.decode('utf-8-sig'))
    run_id = (state.get('run_provenance') or {}).get('run_id')
    if (not isinstance(prev, dict) or not isinstance(prev.get('metadata'), dict)
            or prev['metadata'].get('sim_sec') != float(S)
            or not isinstance(run_id, str) or not run_id
            or (prev.get('run_provenance') or {}).get('run_id') != run_id
            or (prev['metadata'].get('run_provenance') or {}).get('run_id') != run_id):
        raise Refusal('E6', f'previous action is not the action at S={S} of this run')
    facts.update(prev_json=prev_json, prev_bytes=prev_bytes, prev=prev)
    facts['checks']['E6'] = 'pass'

    # E7 source kind
    md = prev['metadata']
    prev_receipt = prev_json.with_name(prev_json.name[:-len('.json')] + '.hold.json')
    if md.get('sdmpc_active') is True:
        kind = 'sdmpc'
    elif md.get('controller_status') == POLICY and prev_receipt.is_file():
        kind = 'hold'
    else:
        raise Refusal('E7', 'previous action is neither an SDMPC decision nor a hold record')
    facts.update(source_kind=kind, prev_receipt=prev_receipt)
    facts['checks']['E7'] = 'pass'

    # E8 the previous command was actually applied
    prev_csv = prev_json.with_suffix('.csv')
    if not prev_csv.is_file():
        raise Refusal('E8', f'previous CSV missing: {prev_csv.name}')
    prev_csv_bytes = prev_csv.read_bytes()
    with open(prev_csv, encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.reader(handle))
    if not rows or tuple(rows[0]) != ACTION_CSV_FIELDS or len(rows) < 2:
        raise Refusal('E8', f'previous CSV header or rows: {prev_csv.name}')
    applied = Path(str(prev_json) + '.applied')
    if kind == 'sdmpc':
        if not applied.is_file():
            raise Refusal('E8', f'{applied.name} missing')
        lines = applied.read_text(encoding='utf-16').splitlines()
        try:
            ok = (len(lines) == 3 and float(lines[0]) == float(S)
                  and Path(lines[1]).resolve() == prev_csv.resolve() and int(lines[2]) == len(prev_csv_bytes))
        except (ValueError, OSError):
            ok = False
        if not ok:
            raise Refusal('E8', f'{applied.name} does not bind {prev_csv.name} at S={S}')
    else:
        try:
            receipt = json.loads(prev_receipt.read_text(encoding='utf-8'))
            want = receipt['held_output']['action_csv']['sha256']
        except (ValueError, KeyError, TypeError, OSError):
            want = None
        if want != sha256_bytes(prev_csv_bytes):
            raise Refusal('E8', f'{prev_receipt.name} does not pin {prev_csv.name}')
    facts.update(prev_csv=prev_csv, prev_csv_bytes=prev_csv_bytes, applied=applied)
    facts['checks']['E8'] = 'pass'

    # E9 the T window document exists (the next decision's C4 history needs it)
    obs = state.get('obs150')
    derived = None
    if isinstance(obs, dict) and isinstance(obs.get('directory'), str):
        derived = Path(obs['directory']) / 'obs150' / f'derived_{t6}.json'
    try:
        doc = json.loads(derived.read_text(encoding='utf-8')) if derived is not None and derived.is_file() else None
    except ValueError:
        doc = None
    if (not isinstance(doc, dict) or doc.get('schema') != DERIVED_SCHEMA or doc.get('sim_sec') != T
            or doc.get('run_id') != obs.get('run_id')
            or doc.get('window') != {'start_s': T - CONTROL_INTERVAL_SEC, 'end_s': T}):
        raise Refusal('E9', f'obs150/derived_{t6}.json missing or not this run/window')
    facts['obs_dir'] = Path(obs['directory'])
    facts['checks']['E9'] = 'pass'

    # E10 never overwrite a .failed_decision
    targets = [folder / f'action_{t6}{suffix}.failed_decision' for suffix in PARTIAL_SUFFIXES]
    present = [p.name for p in targets if p.exists()]
    if present:
        raise Refusal('E10', 'already present: ' + ','.join(present))
    facts['checks']['E10'] = 'pass'
    if (folder / f'action_{t6}.hold.json').exists():
        raise ValueError(f'action_{t6}.hold.json already exists')
    return facts


# ------------------------------------------------------------------ outputs
def held_document(prev, T, S, kind, prev_json, prev_json_sha, prev_csv, prev_csv_sha, origin, chain_length, t6):
    md = prev['metadata']
    small = {'sim_sec': float(T), 'controller': md.get('controller')}
    carried = ['controller', 'run_provenance']
    if 'controller_variant' in md:
        small['controller_variant'] = md['controller_variant']
        carried.append('controller_variant')
    small['controller_status'] = POLICY
    small['run_provenance'] = md.get('run_provenance')
    for key, value in md.items():
        if key.startswith(CARRIED_PREFIXES):
            small[key] = value
            carried.append(key)
    small['hold_previous_on_exception'] = {
        'schema': SCHEMA, 'policy': POLICY, 'sim_sec': T, 'source_sim_sec': S, 'origin_sim_sec': origin,
        'chain_length': chain_length,
        'source_action_json': {'name': prev_json.name, 'sha256': prev_json_sha},
        'source_action_csv': {'name': prev_csv.name, 'sha256': prev_csv_sha},
        'carried_metadata_keys': sorted(carried), 'removed': list(REMOVED), 'price_state': 'restart',
        'receipt': f'action_{t6}.hold.json'}
    out = {}
    for key, value in prev.items():
        if key in ('prediction', 'prediction_error', 'projection_diagnostics'):
            continue
        if key == 'metadata':
            out[key] = small
        elif key == 'diagnostics' and isinstance(value, dict):
            out[key] = {k: v for k, v in value.items() if k != 'sdmpc_prediction_sequence'}
        else:
            out[key] = value
    return out


def write_bytes_atomic(target, data):
    tmp = target.with_name(target.name + '.hold_tmp')
    with open(tmp, 'wb') as handle:
        handle.write(data)
    os.replace(tmp, target)


def write_text_atomic(target, text):
    """Text mode, UTF-8: the bytes Path.write_text(text, encoding='utf-8') gives (the adapter's form)."""
    tmp = target.with_name(target.name + '.hold_tmp')
    with open(tmp, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.replace(tmp, target)


def evidence(facts):
    t6, folder, obs_dir = facts['t6'], facts['folder'], facts['obs_dir']
    named = {facts['state_path'].name: facts['state_path'],
             f'action_{t6}.joint.json': folder / f'action_{t6}.joint.json',
             f'action_{t6}.joint.progress.jsonl': folder / f'action_{t6}.joint.progress.jsonl',
             f'action_{t6}.decision_budget.json': folder / f'action_{t6}.decision_budget.json'}
    for rel in (f'obs150/capture_{t6}.json', f'obs150/derived_{t6}.json', f'obs150/mer_{t6}.jsonl',
                f'obs150/err_{t6}.jsonl', f'lane_observations/frame_{t6}.json'):
        named[rel] = obs_dir / Path(*rel.split('/'))
    return {name: (sha256_file(path) if Path(path).is_file() else 'absent') for name, path in sorted(named.items())}


def run(args):
    wall_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    facts = check(args)
    T, S, t6, folder = facts['T'], facts['S'], facts['t6'], facts['folder']
    prev_json, prev_csv, kind = facts['prev_json'], facts['prev_csv'], facts['source_kind']
    prev_json_sha, prev_csv_sha = sha256_bytes(facts['prev_bytes']), sha256_bytes(facts['prev_csv_bytes'])
    if kind == 'hold':
        hold = facts['prev']['metadata']['hold_previous_on_exception']
        origin, chain_length = int(hold['origin_sim_sec']), int(hold['chain_length']) + 1
    else:
        origin, chain_length = S, 1
    document = held_document(facts['prev'], T, S, kind, prev_json, prev_json_sha, prev_csv, prev_csv_sha,
                             origin, chain_length, t6)
    held_text = json.dumps(document, ensure_ascii=False, indent=2)

    # 2. partial outputs of the failed decision
    partials = []
    for suffix in PARTIAL_SUFFIXES:
        source = folder / f'action_{t6}{suffix}'
        if source.is_file():
            target = source.with_name(source.name + '.failed_decision')
            digest = sha256_file(source)
            os.replace(source, target)
            partials.append({'from': source.name, 'to': target.name, 'sha256': digest})
    # 3. held CSV = previous CSV bytes; 4. held JSON
    held_csv, held_json = folder / f'action_{t6}.csv', folder / f'action_{t6}.json'
    write_bytes_atomic(held_csv, facts['prev_csv_bytes'])
    write_text_atomic(held_json, held_text)
    csv_sha, json_sha = sha256_file(held_csv), sha256_file(held_json)
    if csv_sha != prev_csv_sha:
        raise RuntimeError('held CSV differs from the previous CSV bytes')

    summary = facts['summary']
    root_type = header_type(summary['root_error']) or ''
    error_txt, stderr_txt, stdout_txt = facts['error_txt'], facts['stderr_txt'], facts['stdout_txt']
    source = {'kind': kind, 'action_json': file_pin(prev_json), 'action_csv': file_pin(prev_csv)}
    if kind == 'sdmpc':
        source['applied'] = {'name': facts['applied'].name, 'sha256': sha256_file(facts['applied'])}
    else:
        source['receipt'] = {'name': facts['prev_receipt'].name, 'sha256': sha256_file(facts['prev_receipt'])}
    receipt = {
        'schema': RECEIPT_SCHEMA,
        'hold_previous_on_exception': document['metadata']['hold_previous_on_exception'],
        'decision': {'exit_code': 1, 'stdout': file_pin(stdout_txt) if stdout_txt.is_file() else 'absent',
                     'stderr': file_pin(stderr_txt), 'decision_failed_line': facts['summary_line'],
                     'error_txt': file_pin(error_txt)},
        'exception': {'type': summary['type'], 'message_first_line': summary['message'][:240],
                      'root_error': summary['root_error'][:400], 'root_type': root_type,
                      'chain_header_types': facts['chain_types'],
                      'traceback_functions_last20': [func for _, func in facts['frames']][-20:]},
        'eligibility': {'checks': facts['checks'], 'excluded_types': list(EXCLUDED_TYPES),
                        'contract_pairs': [list(p) for p in CONTRACT_PAIRS],
                        'contract_messages': list(CONTRACT_MESSAGES), 'lists_sha256': lists_sha256()},
        'source': source,
        'held_output': {'action_json': {'name': held_json.name, 'sha256': json_sha},
                        'action_csv': {'name': held_csv.name, 'sha256': csv_sha}},
        'failed_partials': sorted(partials, key=lambda p: p['from']),
        'evidence': evidence(facts),
        'inputs': {'tuning': {'path': str(Path(args.tuning_json)), 'sha256': sha256_file(args.tuning_json),
                              'chain': facts['tuning_chain']},
                   'helper': {'path': str(Path(__file__).resolve()), 'sha256': sha256_file(Path(__file__).resolve())},
                   'python': sys.version, 'argv': list(sys.argv)},
        'wall': {'start_utc': wall_start, 'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()},
    }
    # 5. receipt last
    write_text_atomic(folder / f'action_{t6}.hold.json', json.dumps(receipt, ensure_ascii=False, indent=2))
    line = (f'HOLD_OK sim_sec={T} source_sim_sec={S} origin_sim_sec={origin} chain={chain_length} '
            f'csv_sha256={csv_sha} json_sha256={json_sha} type={summary["type"]} root_type={root_type}')
    return safe(line)[:1000]


def hold_error_path(args):
    try:
        return Path(args.failed_action_json).with_suffix('.hold_error.txt')
    except Exception:  # noqa: BLE001
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state-json', required=True)
    parser.add_argument('--failed-action-json', required=True)
    parser.add_argument('--failed-action-csv', required=True)
    parser.add_argument('--previous-action-json', required=True)
    parser.add_argument('--tuning-json', required=True)
    parser.add_argument('--control-start-sec', required=True, type=int)
    parser.add_argument('--decision-exit', required=True, type=int)
    args = parser.parse_args(argv)
    try:
        line = run(args)
    except Refusal as refusal:
        path = hold_error_path(args)
        if path is not None:
            path.write_text(f'DECISION_HOLD_REFUSED reason={refusal.code}\n{refusal.detail}\n', encoding='utf-8')
        sys.stderr.write(safe(f'DECISION_HOLD_REFUSED reason={refusal.code} detail={refusal.detail}')[:1000] + '\n')
        sys.stderr.flush()
        return EXIT_REFUSED
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001 - every helper failure is a failed hold (run invalid)
        path = hold_error_path(args)
        if path is not None:
            try:
                path.write_text(''.join(traceback.format_exception(type(error), error, error.__traceback__)),
                                encoding='utf-8', errors='replace')
            except OSError:
                pass
        sys.stderr.write(safe(f'DECISION_HOLD_EXCEPTION type={type(error).__name__} message={error}')[:1000] + '\n')
        sys.stderr.flush()
        return EXIT_EXCEPTION
    sys.stdout.write(line + '\n')
    sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
