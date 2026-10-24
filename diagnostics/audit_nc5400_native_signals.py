"""Compare complete native signal event payloads for completed NC5400 arms."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from diagnostics import run_no_control_network_arms as n

d = n.d


def used_signal_programs(provenance):
    """Resolve actual INPX SC supplyFile2 references, not directory inventory."""
    network = d.workspace_path(provenance['files']['network']['path'])
    d.require(d.sha(network) == provenance['files']['network']['sha256'], 'Recorded network changed')
    inventory = {}
    for row in provenance['signal_programs']:
        path = d.workspace_path(row['path'])
        d.require(path not in inventory, 'Duplicate SIG provenance path')
        inventory[path] = row
    selected, without_program, sources, used_paths = {}, {}, {d.relative(network): d.sha(network)}, set()
    for sc in ET.parse(network).getroot().findall('./signalControllers/signalController'):
        number = sc.get('no'); supply = sc.get('supplyFile2') or ''
        d.require(number and number not in selected and number not in without_program, 'Duplicate/missing controller number')
        identity = {key: sc.get(key) for key in ('active', 'type', 'progNo', 'offset')}
        if not supply:
            without_program[number] = identity
            continue
        d.require(supply.startswith('#data#') and len(supply) > 6, 'Unsupported native SIG path base')
        path = d.workspace_path(network.parent / supply[6:])
        row = inventory.get(path)
        d.require(path.is_relative_to(network.parent) and row is not None and row.get('exists') is True,
                  'Used SIG is absent from actual provenance')
        digest = d.sha(path)
        d.require(digest == row['sha256'], 'Used SIG differs from actual provenance')
        selected[number] = {**identity, 'sha256': digest}
        sources[d.relative(path)] = digest
        used_paths.add(path)
    d.require(len(selected) == 42 and set(without_program) == {str(x) for x in range(9101, 9109)},
              'Expected42 native SIG controllers and8 separately written meters')
    return {'selected_by_sc': selected, 'without_program': without_program, 'source_sha256': sources,
            'inventory_count': len(inventory), 'ignored_unreferenced_files': len(inventory) - len(used_paths)}


def events(path):
    before = path.stat()
    file_hash, event_hash, preamble_hash = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    preamble_bytes, excluded_preamble_lines = 0, Counter()
    counts, states, modes = Counter(), Counter(), Counter()
    first, last, previous = None, None, Decimal('-1')
    rows = 0
    with path.open('rb') as stream:
        for raw in stream:
            file_hash.update(raw)
            if rows == 0 and (b';' not in raw or raw.startswith((b'File:', b'Date:', b'Comment:'))):
                if raw.startswith((b'File:', b'Date:')):
                    excluded_preamble_lines[raw.split(b':', 1)[0].decode('ascii')] += 1
                else:
                    preamble_hash.update(raw)
                    preamble_bytes += len(raw)
                continue
            if not raw.strip():
                continue
            parts = [p.strip() for p in raw.decode('ascii').rstrip('\r\n').split(';')]
            d.require(len(parts) == 9 and parts[-1] == '', 'Unexpected LSA event shape')
            sec, cycle, duration = (Decimal(parts[i]) for i in (0, 1, 5))
            d.require(all(x.is_finite() for x in (sec, cycle, duration)) and 0 <= sec and previous <= sec <= 5400,
                      'Invalid/reordered native event time')
            sc, sg = int(parts[2]), int(parts[3])
            d.require(sc > 0 and sg > 0 and parts[4] and parts[6], 'Invalid signal event address/state')
            previous, last = sec, sec
            if first is None:
                first = sec
            counts[f'{sc}:{sg}'] += 1
            states[parts[4]] += 1
            modes[parts[6]] += 1
            rows += 1
            event_hash.update(raw)
    after = path.stat()
    d.require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'Native signal file changed')
    d.require(first == 1 and last == 5400 and rows > 0, 'Incomplete NC5400 event extent')
    return dict(path=d.relative(path), bytes=after.st_size, file_sha256=file_hash.hexdigest(),
                preamble_sha256=preamble_hash.hexdigest(), preamble_bytes=preamble_bytes,
                excluded_preamble_lines=excluded_preamble_lines,
                event_sha256=event_hash.hexdigest(), rows=rows, first_sec=float(first), last_sec=float(last),
                group_event_counts=counts, states=states, modes=modes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    manifest = d.workspace_path(args.manifest)
    output = d.workspace_path(args.output)
    d.require(not output.exists(), 'New output required')
    batch = d.load(manifest)
    d.require(batch.get('schema') == 'no-control-network-arms5400/v1' and batch.get('valid') is True
              and batch.get('completed') is True and batch.get('status') == 'all_three_passed'
              and batch.get('source_changes') == [], 'Completed valid NC5400 batch required')
    arms = batch.get('arms')
    d.require(isinstance(arms, list) and [row.get('arm') for row in arms] == list(d.ARMS), 'Exactly three ordered arms required')
    arm_runs = []
    review_pins = {}
    for row in arms:
        run = d.workspace_path(row['run'])
        expected_name = f"codex_nc5400_{manifest.parent.name}_{row['arm']}_s13"
        if row.get('reused_from'):
            review_path = d.workspace_path(row['reused_from'])
            d.pin(review_pins, review_path, row['reused_review_sha256']); review = d.load(review_path)
            d.require(row['arm'] == 'baseline' and review.get('schema') == 'reviewed-nc5400-baseline/v1'
                      and review.get('valid') is True and review.get('source_changes') == []
                      and all(row[k] == review['receipt'][k] for k in ('name', 'run', 'command', 'validation', 'trajectory', 'native_signal_reference')),
                      'Reused baseline differs from its explicit reviewer certificate')
            expected_name = review['receipt']['name']
        d.require(row.get('status') == 'passed' and row.get('valid') is True and row.get('completed') is True
                  and row.get('exit_code') == 0 and row.get('validation', {}).get('valid') is True,
                  'Individual arm execution/validation incomplete')
        d.require(run.parent == d.ROOT / 'evaluation/runs' and row.get('name') == run.name == expected_name,
                  'Arm name/path does not identify its expected run')
        arm_runs.append(run)
    d.require(len(set(arm_runs)) == 3 and n.OLD not in arm_runs, 'Duplicate/reference run substituted for an arm')
    pins = {d.relative(p): d.sha(p) for p in (manifest, Path(__file__), Path(n.__file__), Path(d.__file__))}
    pins.update(review_pins)
    runs = [n.OLD, *arm_runs]
    records, programs = [], []
    for index, run in enumerate(runs):
        provenance_path = run / ('run_provenance_' + run.name + '.json')
        log_path = run / ('runlog_' + run.name + '.txt')
        provenance = d.load(provenance_path)
        expected_provenance_sha = n.OLD_SHA if index == 0 else arms[index - 1]['validation']['provenance_sha256']
        d.require(d.sha(provenance_path) == expected_provenance_sha and provenance.get('name') == run.name,
                  'Actual provenance differs from the completed run certificate')
        d.require(all(provenance[k] == v for k, v in n.EXPECTED.items()), 'Wrong NC source')
        d.require(b'STAGE=SIM_DONE' in log_path.read_bytes(), 'Completed run required')
        for p in (provenance_path, log_path):
            pins[d.relative(p)] = d.sha(p)
        paths = list(run.rglob('*.lsa'))
        d.require(len(paths) == 1, 'Ambiguous LSA')
        d.require(paths[0].resolve().is_relative_to(run.resolve()), 'LSA outside its run')
        if index:
            expected_lsa = arms[index - 1]['validation']['native_outputs']['.lsa']
            d.require(len(expected_lsa) == 1 and d.workspace_path(expected_lsa[0]['path']) == paths[0].resolve()
                      and expected_lsa[0]['bytes'] == paths[0].stat().st_size, 'LSA path/bytes differs from arm validation')
        record = events(paths[0]); records.append(record)
        pins[record['path']] = record['file_sha256']
        program = used_signal_programs(provenance)
        pins.update(program['source_sha256'])
        programs.append(program)
    fields = ('event_sha256', 'rows', 'group_event_counts', 'states', 'modes', 'first_sec', 'last_sec')
    equal = all(all(r[k] == records[0][k] for k in fields) for r in records)
    header_equal = all((r['preamble_sha256'], r['preamble_bytes']) ==
                       (records[0]['preamble_sha256'], records[0]['preamble_bytes']) for r in records)
    program_equal = all(p['selected_by_sc'] == programs[0]['selected_by_sc'] and
                        p['without_program'] == programs[0]['without_program'] for p in programs)
    d.assert_pins(pins)
    result = dict(valid=equal and program_equal and header_equal, native_ordered_events_exact=equal,
                  nonvolatile_preamble_exact=header_equal,
                  used_signal_programs_by_sc_exact=program_equal, signal_programs=programs,
                  records=records, source_sha256=pins, source_changes=[],
                  limitations=['Only pre-event raw File: and Date: lines are excluded from preamble equality; all other header bytes, including head geometry, are compared.',
                               'After the first event, every nonblank line must parse as an event; blank inter-event lines are ignored.',
                               'LSA records state changes. Initial state before the first event of each group is not inferred.',
                               'This compares applied native signals; it does not infer discharge capacity or traffic benefit.'])
    d.save(output, result)
    d.require(result['valid'], 'Native signal/program mismatch')
    print({'valid': True, 'rows_per_run': records[0]['rows'], 'groups': len(records[0]['group_event_counts'])})


if __name__ == '__main__':
    main()
