"""Join completed native startup-arm receipts for the existing spatial analyzer.

Does not run COM, create a replacement execution certificate, or alter receipts.
Every arm's original certificate remains linked and is revalidated before use.
"""
import re

from diagnostics import run_fixed_beta300v3_route_experiment as d


def startup_stages(run):
    path = run / ('runlog_' + run.name + '.txt')
    # cscript emits the local codepage for paths. These observer records are
    # deliberately ASCII; decode those exact lines without lossy replacement.
    lines = [raw.decode('ascii') for raw in path.read_bytes().splitlines()
             if raw.startswith((b'STARTUP_STAGE=', b'DEMAND_WRITE_BEGIN ', b'DEMAND_WRITE_DONE '))]
    stages, begins, dones = {}, [], []
    for line in lines:
        match = re.fullmatch(r'STARTUP_STAGE=(\w+) timer_sec=([\d.]+)', line)
        if match:
            d.require(match[1] not in stages, 'Duplicate startup stage')
            stages[match[1]] = float(match[2])
        match = re.fullmatch(r'DEMAND_WRITE_BEGIN no=(\d+) time_int=([\d-]+) before=([\d.]+) target=([\d.]+) timer_sec=([\d.]+)', line)
        if match:
            begins.append(tuple(match.groups()))
        match = re.fullmatch(r'DEMAND_WRITE_DONE no=(\d+) time_int=([\d-]+) timer_sec=([\d.]+)', line)
        if match:
            dones.append(tuple(match.groups()))
    d.require(len(begins) == len(dones) == 204, 'Incomplete demand write observations')
    d.require([x[:2] for x in begins] == [x[:2] for x in dones], 'Demand write order differs')
    d.require(stages['GUI_SUSPEND_REQUESTED'] <= stages['DEMAND_BEGIN'] <= stages['DEMAND_DONE']
              <= stages['FIRST_STEP_BEGIN'] < stages['FIRST_STEP_DONE'], 'Invalid startup stage order')
    return {'log': d.relative(path), 'log_sha256': d.sha(path), 'stages_timer_sec': stages,
            'demand_duration_sec': round(stages['DEMAND_DONE'] - stages['DEMAND_BEGIN'], 3),
            'first_step_duration_sec': round(stages['FIRST_STEP_DONE'] - stages['FIRST_STEP_BEGIN'], 3),
            'demand_write_count': len(begins), 'demand_no_time_before_target': [list(x[:4]) for x in begins]}


def main():
    output = d.ROOT / 'diagnostics/startup_gui_three_arm_comparison_v1'
    d.require(not output.exists(), 'Fresh assembly directory required')
    pins, rows, receipts, stages = {}, [], {}, {}
    family_path = d.ROOT / 'diagnostics/performance_initial_clock_replay_v1/manifest.json'
    d.pin(pins, family_path, 'cca58af11e22fd3301003d61f412cb4c66ce3513262d83e80182ca7ddfde4a00')
    family = d.load(family_path)
    d.pin(pins, d.FLAT / 'manifest.json', '1e7544ee22fa52b0eed3a8eb23696a4b8b7117bd5fcf5daf75adf704da495367')
    flat = d.load(d.FLAT / 'manifest.json')
    for name, item in flat['outputs'].items():
        d.pin(pins, d.FLAT / name, item['destination_sha256'])
    baseline = None
    for arm in d.ARMS:
        suffix = '' if arm == 'baseline' else '_' + arm
        receipt_path = d.ROOT / ('diagnostics/startup_gui_actual' + suffix + '_v1/result.json')
        receipt = d.load(receipt_path)
        receipts[d.relative(receipt_path)] = d.pin(pins, receipt_path)
        d.require(receipt.get('schema') == 'startup-gui-actual-validation/v1'
                  and receipt.get('valid') is True and receipt.get('exit_code') == 0
                  and receipt.get('source_changes') == [] and receipt.get('natural_exit', {}).get('valid') is True
                  and receipt.get('natural_exit', {}).get('final_processes') == [], 'Incomplete arm receipt: ' + arm)
        if baseline is None:
            baseline = receipt
        else:
            d.require(receipt['reference'] == baseline['reference']
                      and receipt['baseline_validation_sha256'] == next(iter(receipts.values())),
                      'Arm used another baseline')
        for raw in family['source_sha256']:
            key = d.relative(d.workspace_path(raw))
            d.require(receipt['source_sha256'][key] == baseline['source_sha256'][key], 'Different runtime: ' + key)
            d.pin(pins, key, receipt['source_sha256'][key])
        run = d.workspace_path(receipt['run'])
        expected_name = 'codex_startup_gui' + suffix + '_s13_1050_v1'
        d.require(run == d.ROOT / 'evaluation/runs' / expected_name
                  and receipt.get('arm', 'baseline') == arm
                  and receipt['command'] == d.arm_command(expected_name, arm, run), 'Wrong arm command/run identity')
        ref_dir = d.workspace_path(baseline['reference']['run']) / ('decisions_' + baseline['reference']['source_run'])
        refs = {sec: ref_dir / f'action_{sec:06d}.csv' for sec in (1, 900)}
        checked = d.validate_run(run, run.name, arm, flat['outputs'][arm + '.inpx']['destination_sha256'], refs)
        d.require(checked == receipt['validation'], 'Execution readback certificate changed: ' + arm)
        stages[arm] = startup_stages(run)
        if arm != 'baseline':
            d.require(stages[arm]['demand_no_time_before_target'] == stages['baseline']['demand_no_time_before_target'],
                      'Actual demand writes differ across arms')
        row = {'arm': arm, 'run': receipt['run'], 'name': run.name, 'command': receipt['command'],
               'status': 'passed', 'completed': True, 'valid': True, 'exit_code': 0,
               'post_run_processes': [], 'network_sha256': flat['outputs'][arm + '.inpx']['destination_sha256'],
               'elapsed_sec': receipt['wall_sec'], 'validation': checked,
               'source_receipt': d.relative(receipt_path), 'source_receipt_sha256': receipts[d.relative(receipt_path)]}
        if arm == 'baseline':
            row['baseline_trajectory_comparison'] = receipt['trajectory']
            for record in (receipt['trajectory']['actual'], receipt['trajectory']['reference']):
                d.pin(pins, record['path'], record['file_sha256'])
            for path, expected in receipt['trajectory']['provenance_sha256'].items():
                d.pin(pins, path, expected)
        rows.append(row)
    report = {'schema': 'fixed-beta300v3-three-arm-experiment/v1',
              'assembly_scope': 'Read-only join of three independently completed native execution receipts; no new simulation.',
              'assembled_utc': d.utc(), 'producer_sha256': d.sha(__file__), 'source_receipts': receipts,
              'status': 'all_three_execution_and_readback_passed', 'completed': True, 'valid': True,
              'source_changes': [], 'source_sha256': pins, 'arms': rows,
              'baseline_trajectory_reference': baseline['reference'], 'startup_observations': stages}
    from diagnostics.analyze_fixed_route_arm_windows import baseline_trajectory_certificate
    baseline_trajectory_certificate(report)
    d.assert_pins(pins)
    output.mkdir()
    d.save(output / 'manifest.json', report)
    print(d.relative(output / 'manifest.json'))


if __name__ == '__main__':
    main()
