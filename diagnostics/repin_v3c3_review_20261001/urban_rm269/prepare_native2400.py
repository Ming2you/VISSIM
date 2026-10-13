"""Prepare a bounded paired execution of the already verified2400 commands.

No model fitting, optimizer invocation, native launch, or future input. Prefix
commands remain byte-identical; native prefix/state equality is a later gate.
"""
import csv
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
OUT = I / 'native_urbanrm269_2400'
F = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
CHECK = HERE / 'selection2400_discrete'


def read(p):
    return json.loads(p.read_bytes())


def save(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def physical_rows(p):
    with p.open(encoding='utf-8-sig', newline='') as stream:
        return [{k: v for k, v in r.items() if k != 'metadata'} for r in csv.DictReader(stream)]


def main():
    assert not OUT.exists(), 'Preserve previously prepared or attempted experiment'
    summary = read(CHECK / 'summary.json')
    assert summary['status'] == 'two_discrete_predictions_complete'
    assert summary['selected_model_caps_feasible']
    assert read(CHECK / 'completion.json')['status'] == 'complete'
    pins = {}
    for name, expected in summary['source_pins'].items():
        p = ROOT / name
        assert sha(p) == expected, name
        pins[str(p)] = expected
    for p in (Path(__file__), CHECK / 'summary.json', CHECK / 'completion.json'):
        pins[str(p)] = sha(p)

    provenance_path = next(F.parent.glob('run_provenance_*.json'))
    provenance = read(provenance_path)
    assert provenance['seed'] == 29
    network = I / 'selected/network/native_seed29.inpx'
    for key, p in (
        ('network', network),
        ('generated_vbs_config', I / 'selected/scenario/lane_native_b110.vbs'),
        ('demand_profile', I / 'selected/scenario/profile.csv'),
    ):
        assert sha(p) == provenance['files'][key]['sha256'], key
        pins[str(p)] = sha(p)
    pins[str(provenance_path)] = sha(provenance_path)
    prefix_times = [1, *range(150, 2400, 150)]
    required = 2 * sum((F / f'action_{t:06d}{suffix}').stat().st_size
                       for t in prefix_times for suffix in ('.json', '.csv'))
    required += 2 * sum(p.stat().st_size for p in CHECK.glob('*/action_*.json'))
    assert shutil.disk_usage(ROOT).free > required + 2 * 1024**3, 'Insufficient preparation headroom'
    OUT.mkdir()
    prefix, commands = [], []
    for arm in ('hold', 'selected'):
        dest = OUT / arm / 'commands'
        dest.mkdir(parents=True)
        for sec in prefix_times:
            record = {'arm': arm, 'sim_sec': sec}
            for suffix in ('.json', '.csv'):
                src = F / f'action_{sec:06d}{suffix}'
                target = dest / src.name
                expected = pins.setdefault(str(src), sha(src))
                shutil.copy2(src, target)
                assert sha(target) == expected
                pins[str(target)] = expected
                record[suffix[1:]] = {'source': str(src), 'destination': str(target), 'sha256': expected}
            prefix.append(record)
        for sec in (2400, 2550, 2700, 2850):
            original_sec = min(sec, 2700)
            for suffix in ('.csv', '.json'):
                src = CHECK / arm / f'action_{original_sec:06d}{suffix}'
                target = dest / f'action_{sec:06d}{suffix}'
                pins[str(src)] = sha(src)
                if sec == 2850 and suffix == '.json':
                    data = read(src)
                    data['metadata']['sim_sec'] = sec
                    save(target, data)
                else:
                    shutil.copy2(src, target)
                    assert sha(target) == pins[str(src)]
                pins[str(target)] = sha(target)
            rows = physical_rows(dest / f'action_{sec:06d}.csv')
            assert rows == physical_rows(CHECK / arm / f'action_{original_sec:06d}.csv')
            command = {'arm': arm, 'sim_sec': sec, 'rows': len(rows),
                       'csv_sha256': pins[str(dest / f'action_{sec:06d}.csv')]}
            commands.append(command)
        print('COMMANDS_PREPARED', arm, flush=True)

    protocol = dict(
        start_sec=2400, end_sec=2850, seed=29, arms=['hold', 'selected'],
        control_start_sec=900, controller='wu-link',
        network=str(network), network_sha256=sha(network), command_pins=pins,
        controlled_prefix_evidence=prefix, native_authorization_pending=False,
        native_authorization='User authorized necessary native validation for the active calibration goal',
        max_native_runs=2, automatic_retries=0, sim_resolution=10,
        vehicle_record_interval_sec=5, observation_interval_sec=150,
        future_observation_inputs=False, controller_optimization=False,
        physical_command_check=commands, prediction_summary=str(CHECK / 'summary.json'),
        qualification_requires_exact_native_prefix=True, native_started=False,
        scope='Same realized prevention prefix through2250, then held physical commands versus already selected three blocks. Multiple urban/RM changes; not10681-only. No optimization during replay.',
        constraints='Same selected NP/NUF caps passed in both discrete predictions; native shared quantities remain to be measured.',
        terminal_command='2850 repeats final block for runner completeness; no post2850 traffic performance is counted.',
    )
    save(OUT / 'protocol.json', protocol)
    save(HERE / 'native2400_preparation.json', dict(
        status='prepared_not_launched', protocol=str(OUT / 'protocol.json'),
        protocol_sha256=sha(OUT / 'protocol.json'), prefix_count_per_arm=len(prefix_times),
        horizon_sec=450, sim_period_sec=2850, native_runs=0, forecasts=0,
        model_delta_omega_ttt_veh_h=summary['delta_omega_ttt_veh_h'],
        note='Native prefix equality to each other and saved2400 state, LDP/VSL, conservation and sameOmega performance required before claiming gain.',
    ))
    print('PAIRED_PROTOCOL_READY', OUT, flush=True)


if __name__ == '__main__':
    main()
