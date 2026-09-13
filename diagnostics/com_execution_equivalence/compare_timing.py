"""Completed-receipt PERF comparison only. No runner, model or native data reads.

Example: python compare_timing.py --old-receipt OLD/completion_receipt.json
    [--new-receipt NEW/completion_receipt.json] --out NEW_REPORT_STEM
The output is timing evidence, never a physical-equivalence verdict.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Pure recorded-provenance comparison; no run_inputs/readbacks/FZP calls.
from diagnostics.com_execution_equivalence.verify_pair import provenance_comparison

FAILURES = ('DECISIONS_FAILED', 'OBSERVATION_FAILURES', 'SIGNAL_FAILURES',
            'ACTION_FORMAT_FAILURES', 'COM_FAILURES')
PERF = re.compile(rb'PERF name=([a-z0-9_.]+) sec=(\S+) n=(\S+)$')
MARKER = re.compile(rb'DEMAND_WRITE_(BEGIN|DONE) no=(\d+) time_int=(\S+).*? timer_sec=(\S+)$')
GROUPS = {
    'startup_load': ['startup.load_net'],
    'startup_demand_inclusive': ['startup.demand', 'startup.demand.volume_before_read',
                                 'startup.demand.volume_set', 'startup.demand.volume_after_read'],
    'startup_control_observer_setup': ['startup.control_setup', 'startup.head_init'],
    'actual_simulation_calls': ['sim.first_step', 'sim.step', 'sim.continuous'],
    'controller_inclusive': ['decision.total', 'state.json', 'decision.python', 'action.apply'],
    'observer_inclusive': ['head.capture', 'head.history', 'head.seal',
                           'scan.vehicles', 'head.signal_capture'],
    'runtime_actuation_and_verification': ['signals.runtime', 'rampmeters.runtime', 'signals.readback'],
    'state_csv_logging': ['log.state_csv'],
}
LIMITS = [
    'Wall is wrapper started->finished: startup, run, watchdog polling, exit observation and cleanup are included. It is not simulation-only or CPU time.',
    'PERF uses VBScript Timer wall seconds with midnight rollover; rounding/resolution limits small buckets. com.* sec=0 is an untimed count, not zero COM latency.',
    'Nested buckets must not be summed as exclusive wall time. startup.demand contains before/set/after; decision.total contains state.json/python/action.apply; head.capture contains scan.vehicles and signal capture; head.seal also contains signal capture. Vehicle scan is also called by state/log writers.',
    'Counted COM scope is only named instrumentation sites. It excludes enumeration/GetAll, object resolution, uninstrumented ownership/count/time getters, error-path attempts and other COM calls. Returned bulk counters are not vehicle counts.',
    'DONE->next BEGIN demand gaps include prior after-read, bookkeeping and next before-read. They localize a wait interval, not a single getter duration. Only the aggregate after-read PERF bucket identifies its total measured time.',
    'No independently timed postprocessing bucket exists here. Report it as unavailable; do not recover it by summing nested buckets or subtracting their sum from wall.',
    'Both arms use the same source/VSL sidecar and RW_PERF=1. Allowed switch differences are SG readback cadence and write-on-change only. Savings are conservative for the SG loop and do not separately estimate removed legacy VSL summary reads.',
    'Timing and source/config provenance do not certify identical physical commands, observations or trajectories. Use the separate completed pair verifier; no FZP/LSA/ERR/state payload is consumed here.',
    'One old/new pair is a descriptive observation, not a stable speedup benchmark. A startup readback wait can dominate wall independently of the SG-loop change.',
]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid number') from exc
    require(result.is_finite() and result >= 0, 'Nonfinite/negative number')
    return result


def count(value):
    result = number(value)
    require(result == int(result), 'Noninteger count')
    return int(result)


def timer_gap(before, after):
    require(0 <= before < 86400 and 0 <= after < 86400, 'Timer outside one day')
    return (after - before) % Decimal(86400) if after >= before else after - before + 86400


def parse_log(blob, end):
    # Canonical Windows logs may contain CP949 Korean paths. Only ASCII-tagged
    # byte lines are parsed, preserving all original bytes in the source SHA.
    lines = blob.splitlines()
    require(lines.count(b'STAGE=SIM_DONE') == 1 and
            lines.count(('SIM_SEC=' + str(end)).encode()) == 1, 'Missing/duplicate terminal marker')
    for key in FAILURES:
        found = [r for r in lines if r.startswith((key + '=').encode())]
        require(found == [(key + '=0').encode()], 'Missing/nonzero failure counter: ' + key)
    require(not any(r.startswith(b'ERROR') for r in lines), 'Completed run contains ERROR')
    perf, markers = {}, []
    modes = [r.split(b'=', 1)[1].decode('ascii') for r in lines if r.startswith(b'RUN_MODE=')]
    require(len(modes) == 1, 'Missing/duplicate RUN_MODE')
    for index, row in enumerate(lines, 1):
        if row.startswith(b'PERF'):
            match = PERF.fullmatch(row)
            require(match is not None, 'Malformed PERF row')
            name = match[1].decode('ascii')
            require(name not in perf, 'Duplicate PERF bucket: ' + name)
            sec, n = number(match[2].decode()), count(match[3].decode())
            require(not name.startswith('com.') or sec == 0, 'Count-only COM bucket has seconds')
            perf[name] = {'sec': float(sec), 'n': n,
                          'kind': 'count_only' if name.startswith('com.') else 'inclusive_wall_timer'}
        if row.startswith(b'DEMAND_WRITE_'):
            match = MARKER.fullmatch(row)
            require(match is not None, 'Malformed demand marker')
            markers.append({'line': index, 'stage': match[1].decode(), 'input': match[2].decode(),
                            'interval': match[3].decode(), 'timer': number(match[4].decode())})
    required = {'startup.load_net', 'startup.demand', 'startup.demand.volume_before_read',
                'startup.demand.volume_set', 'startup.demand.volume_after_read',
                'com.input_volume.read', 'com.input_volume.setter', 'sim.first_step', 'decision.total'}
    require(required <= perf.keys(), 'Missing expected instrumented buckets')
    require('sim.step' in perf or 'sim.continuous' in perf, 'No post-first simulation timing')
    require(len(markers) % 2 == 0 and markers, 'Missing/unpaired demand markers')
    writes, gaps, seen = [], [], set()
    for index in range(0, len(markers), 2):
        begin, done = markers[index:index+2]
        key = (begin['input'], begin['interval'])
        require(begin['stage'] == 'BEGIN' and done['stage'] == 'DONE' and
                key == (done['input'], done['interval']) and key not in seen, 'Demand marker order/key collision')
        seen.add(key)
        writes.append(float(timer_gap(begin['timer'], done['timer'])))
        if index + 2 < len(markers):
            nxt = markers[index+2]
            gaps.append({'after_input': done['input'], 'after_interval': done['interval'],
                         'done_log_line': done['line'], 'done_timer_sec': float(done['timer']),
                         'next_input': nxt['input'], 'next_interval': nxt['interval'],
                         'begin_log_line': nxt['line'], 'begin_timer_sec': float(nxt['timer']),
                         'gap_sec': float(timer_gap(done['timer'], nxt['timer']))})
    for key in ('startup.demand.volume_before_read', 'startup.demand.volume_set',
                'startup.demand.volume_after_read', 'com.input_volume.setter'):
        require(perf[key]['n'] == len(writes), 'Demand timer/count/marker mismatch: ' + key)
    require(perf['com.input_volume.read']['n'] == 2 * len(writes), 'Demand read count mismatch')
    return {'run_mode': modes[0], 'perf': perf, 'demand_marker_rows': len(markers),
            'completed_interval_setters': len(writes), 'marker_setter_total_sec_rounded': sum(writes),
            'largest_between_setter_gaps': sorted(gaps, key=lambda r: -r['gap_sec'])[:5],
            'simulation_call_total_sec': sum(perf[k]['sec'] for k in GROUPS['actual_simulation_calls'] if k in perf),
            'postprocessing_sec': None}


def read_completed(receipt_path):
    files = {}

    def read(p, digest=None):
        p = Path(p).resolve(strict=True)
        raw = p.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        require(digest is None or digest == actual, 'SHA mismatch: ' + str(p))
        files[p] = raw
        return raw

    def obj(p, digest=None):
        return json.loads(read(p, digest).decode('utf-8-sig'))

    receipt_path = Path(receipt_path).resolve(strict=True)
    r = obj(receipt_path)
    # Reject incomplete/failed receipts before touching any run output.
    require(r.get('schema') == 'selected-control-completion/v1' and r.get('completed') is True
            and type(r.get('exit_code')) is int and r['exit_code'] == 0
            and r.get('owned_native_alive') is False and r.get('errors') == [], 'Run not completed successfully')
    run = Path(r['run_directory']).resolve(strict=True)
    require(receipt_path.parent == run and run.name == r['name'] and r['run_id'], 'Receipt/run identity mismatch')

    def output(value):
        p = Path(value).resolve(strict=True)
        require(p.is_relative_to(run), 'Output outside completed run')
        return p

    w = obj(output(r['wrapper_observation']['path']), r['wrapper_observation']['sha256'])
    require(type(w.get('watchdog_exit_code')) is int and w['watchdog_exit_code'] == 0
            and w.get('owned_native_alive') is False and w.get('ownership_ambiguous') is False
            and w.get('owned_native') == r.get('owned_native') and w.get('owned_native'),
            'Wrapper completion/ownership not established')
    start, finish = (datetime.fromisoformat(w[k].replace('Z', '+00:00')) for k in ('started', 'finished'))
    require(start.utcoffset() is not None and finish.utcoffset() is not None and finish >= start,
            'Invalid wrapper timestamps')
    prov = obj(output(r['provenance_path']), r['provenance_sha256'])
    end = count(r['terminal_sec'])
    require(end > 0 and prov['name'] == r['name'] and prov['run_id'] == r['run_id']
            and count(prov['sim_period_sec']) == end and prov['env'].get('RW_PERF') == '1',
            'Provenance identity/end/PERF differs')
    log = parse_log(read(output(r['runlog_path'])), end)
    log.update({'name': r['name'], 'run_id': r['run_id'], 'terminal_sec': end,
                'wrapper_wall_sec': (finish-start).total_seconds(), 'wrapper_observation': w,
                'receipt_path': str(receipt_path), 'provenance': prov,
                'source_sha256': {str(p): hashlib.sha256(b).hexdigest() for p,b in files.items()}})
    require(all(p.read_bytes() == b for p,b in files.items()), 'Completed evidence changed while reading')
    return log


def compare(old, new):
    require(old['terminal_sec'] == new['terminal_sec'] and old['run_mode'] == new['run_mode'],
            'Period/runtime mode differs')
    provenance = provenance_comparison(old['provenance'], new['provenance'])
    keys = sorted(old['perf'].keys() | new['perf'].keys())
    delta = {}
    for key in keys:
        a,b = old['perf'].get(key),new['perf'].get(key)
        # Missing buckets are unknown, not measured zero.
        delta[key] = {'old': a, 'new': b,
                      'delta_sec': b['sec']-a['sec'] if a and b else None,
                      'delta_count': b['n']-a['n'] if a and b else None}
    adjusted = {}
    for label, keys in [('excluding_demand_after_read', ['startup.demand.volume_after_read']),
                        ('excluding_whole_demand', ['startup.demand']),
                        ('excluding_load_and_whole_demand', ['startup.load_net', 'startup.demand'])]:
        a = old['wrapper_wall_sec']-sum(old['perf'][k]['sec'] for k in keys)
        b = new['wrapper_wall_sec']-sum(new['perf'][k]['sec'] for k in keys)
        adjusted[label] = {'subtracted_buckets': keys, 'old_sec': a, 'new_sec': b,
                           'delta_sec': b-a, 'interpretation': 'Derived wall remainder only; still includes startup/setup/cleanup and other work. Not a pure SG-loop or simulation speedup.'}
    return {'recorded_provenance': provenance, 'buckets': delta,
            'wall_delta_sec': new['wrapper_wall_sec']-old['wrapper_wall_sec'],
            'startup_confound_sensitivity': adjusted,
            'physical_equivalence_verdict': 'not_evaluated_by_timing_helper'}


def markdown(report):
    arms = [report['old']] + ([report['new']] if report['new'] else [])
    lines = ['Completed execution timing; no physical-equivalence verdict.', '',
             'Failed old signal r01 is excluded. Only explicitly supplied successful receipts are consumed.', '']
    for a in arms:
        p=a['perf']; lines += [a['name'], '', f"Wrapper wall: {a['wrapper_wall_sec']:.6f} s; terminal {a['terminal_sec']} s; {a['run_mode']}.", '',
                               '| Bucket (nested/inclusive unless count-only) | Seconds | Calls/count |', '|---|---:|---:|']
        for group, keys in GROUPS.items():
            for k in keys:
                if k in p: lines.append(f"| {k} | {p[k]['sec']:.6f} | {p[k]['n']} |")
        lines += ['', f"Actual simulation call total: {a['simulation_call_total_sec']:.6f} s (first + subsequent calls only).", '',
                  '| Counted COM site; not total COM inventory | Count |', '|---|---:|']
        lines += [f"| {k} | {v['n']} |" for k,v in p.items() if k.startswith('com.')]
        g=a['largest_between_setter_gaps'][0]
        lines += ['', f"Largest demand gap: input {g['after_input']} interval {g['after_interval']} DONE (line {g['done_log_line']}) → input {g['next_input']} interval {g['next_interval']} BEGIN (line {g['begin_log_line']}): {g['gap_sec']:.6f} s.",
                  f"Whole demand {p['startup.demand']['sec']:.6f} s; before reads {p['startup.demand.volume_before_read']['sec']:.6f}, setter/error handling {p['startup.demand.volume_set']['sec']:.6f}, after reads {p['startup.demand.volume_after_read']['sec']:.6f} s. The gap does not isolate a single getter.", '']
    if report['comparison']:
        lines += ['| Matched bucket | New − old seconds | New − old count |', '|---|---:|---:|']
        for k,v in report['comparison']['buckets'].items():
            lines.append(f"| {k} | {v['delta_sec'] if v['delta_sec'] is not None else 'unavailable'} | {v['delta_count'] if v['delta_count'] is not None else 'unavailable'} |")
        lines += ['', f"Wrapper wall delta: {report['comparison']['wall_delta_sec']:.6f} s. No stable speedup estimate is certified.", '']
        lines += ['| Derived wall remainder (not a pure speedup) | Old seconds | New seconds | New − old seconds |', '|---|---:|---:|---:|']
        for k,v in report['comparison']['startup_confound_sensitivity'].items():
            lines.append(f"| {k} | {v['old_sec']:.6f} | {v['new_sec']:.6f} | {v['delta_sec']:.6f} |")
        lines.append('')
    else:
        lines += ['New arm is pending: no new-arm files were requested or read; no speedup is reported.', '']
    lines += ['Interpretation limits:', ''] + ['- '+s for s in LIMITS]
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-receipt', required=True, type=Path)
    parser.add_argument('--new-receipt', type=Path)
    parser.add_argument('--out', required=True, type=Path, help='New output stem; refuses overwrites')
    args=parser.parse_args()
    outputs=[Path(str(args.out)+s) for s in ('.json','.md')]
    require(not any(p.exists() for p in outputs), 'Output already exists')
    old=read_completed(args.old_receipt)
    new=read_completed(args.new_receipt) if args.new_receipt else None
    report={'schema':'completed-com-timing/v1','old':old,'new':new,
            'comparison':compare(old,new) if new else None,'limits':LIMITS,
            'physical_equivalence_evaluated':False,
            'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    outputs[0].parent.mkdir(parents=True,exist_ok=True)
    outputs[0].write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    outputs[1].write_text(markdown(report),encoding='utf-8')
    print(json.dumps({'outputs':[str(p) for p in outputs], 'old_wall_sec':old['wrapper_wall_sec'],
                      'new_supplied':new is not None, 'physical_equivalence_evaluated':False}))


if __name__ == '__main__':
    main()
