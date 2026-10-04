"""Summarize three completed forecasts against completed native caches; no simulation."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent.parent
U = I.parents[2]
D = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
OUT = I / 'closedloop_recorded2250_lever450_RM_C10484_trace10484_loss_onset_s29_v1'
CACHE = HERE.parent / 'loss_diagnosis'
RAMP = 'RM_C10484'
pins = {}


def raw(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return data


def js(path):
    return json.loads(raw(path))


def rows(path):
    return list(csv.DictReader(raw(path).decode('utf-8-sig').splitlines()))


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def close(a, b):
    assert abs(a-b) < 1e-8, (a, b)


def main():
    protocol = js(HERE / 'protocol.json')
    saved = js(OUT / 'summary.json')
    results = saved['results']
    held = results['held_actual']
    command = held['commands'][0]
    actual = js(D / 'action_002250.json')
    for key in ('green_times', 'offsets', 'vsl'):
        assert command[key] == actual[key], key
    command_checks = {'action_green_offset_vsl_exact': True}
    counts = {}
    for row in rows(D / 'action_002250.csv'):
        kind = row['kind']
        counts[kind] = counts.get(kind, 0) + 1
        if kind == 'signal':
            for phase in range(1, 5):
                close(float(row[f'p{phase}_green']), command['green_times'][f"{row['id']}_p{phase}"])
            close(float(row['offset']), command['offsets'][row['id']])
        elif kind == 'ramp_meter':
            close(float(row['green_sec']), command['meters'][row['id']])
        elif kind == 'vsl':
            direction, segment = row['id'].removeprefix('RW_').rsplit('_S', 1)
            close(float(row['speed_kph']), command['vsl'][f'{direction}__seg{segment}'])
    command_checks.update(csv_rows=counts, csv_signal_vsl_meter_exact=True)
    assert counts['signal'] == 17 and counts['ramp_meter'] == 8 and counts['vsl'] == 66
    state = js(D / 'state_002400.json')
    meta = state['obs150']['mer']
    mer_path = D / meta['chunk']
    mer_data = raw(mer_path)
    assert pins[str(mer_path)] == meta['chunk_sha256']
    mer = [json.loads(line) for line in mer_data.decode('utf-8').splitlines()]
    detectors = rows(CACHE / 'detector_windows_150s.csv')
    links = rows(CACHE / 'link_snapshots_150s.csv')
    postheads = rows(CACHE / 'ramp_posthead_stock.csv')

    def stock(t):
        found = [r for r in links if r['arm'] == 'sdmpc' and float(r['sim_sec']) == t and r['link'] == '10484']
        assert len(found) == 1
        return int(found[0]['n'])

    def posthead(t):
        found = [r for r in postheads if r['arm'] == 'sdmpc' and float(r['sim_sec']) == t and r['connector'] == '10484']
        assert len(found) == 1
        return int(found[0]['posthead_n'])

    def native_count(dcp, start, end):
        return sum(r[1] == dcp and r[2] is not None and start <= r[2] < end for r in mer)

    native = {'initial_stock': stock(2250), 'final_stock': stock(2400),
              'arrival': native_count(960271, 2250, 2400), 'head': native_count(960220, 2250, 2400)}
    for dcp, key in ((960271, 'arrival'), (960220, 'head')):
        found = [r for r in detectors if r['arm'] == 'sdmpc' and float(r['sim_sec']) == 2400 and int(r['dcm_no']) == dcp]
        assert len(found) == 1
        close(native[key], int(found[0]['count']))
    native['merge_from_total_stock'] = native['initial_stock'] + native['arrival'] - native['final_stock']
    native['merge_from_posthead_stock'] = native['head'] + posthead(2250) - posthead(2400)
    close(native['merge_from_total_stock'], native['merge_from_posthead_stock'])
    # Native absence of connector removals was checked in the preceding loss diagnosis.
    table, blocks, timing = [], [], []
    for name, result in results.items():
        assert result['validation']['all_actuator_and_step_constraints_checked']
        assert max(abs(r['residual']) for r in result['ramps'].values()) < 1e-8
        trace = json.loads(gzip.decompress(raw(OUT / f'{name}_{RAMP}_trace.json.gz')))
        assert not trace['future_observation_inputs']
        close(trace['initial_stock']['connector_veh'], native['initial_stock'])
        for cmd in result['commands']:
            for key in ('green_times', 'offsets', 'vsl'):
                assert cmd[key] == command[key]
            assert all(v == command['meters'][k] for k, v in cmd['meters'].items() if k != RAMP)
        greens = [cmd['meters'][RAMP] for cmd in result['commands']]
        assert all(abs(b-a) <= 2 for a, b in zip([10]+greens, greens))

        def flow(start, end, kind):
            if kind == 'head':
                return sum(r['accepted_total_veh'] for r in trace['resources'] if r['kind'] == 'physical_ramp_head_service' and start <= r['start_sec'] < end)
            return sum(r['vehicles'] for r in trace['transfers'] if start <= r['start_sec'] < end and
                       ((kind == 'arrival' and r['target'] == 'ramp:'+RAMP) or
                        (kind == 'merge' and r['source'] == 'ramp:'+RAMP and r['target'] == 'merge_pending:'+RAMP)))

        initial = native['initial_stock']
        for start in (2250, 2400, 2550):
            b = {'case': name, 'start': start, 'end': start+150, 'initial_stock': initial}
            b.update({kind: flow(start, start+150, kind) for kind in ('arrival', 'head', 'merge')})
            b['final_stock'] = initial + b['arrival'] - b['merge']
            endpoint = {r['ramp_veh'] for r in trace['residence'] if r['end_sec'] == start+150}
            assert len(endpoint) == 1
            close(b['final_stock'], endpoint.pop())
            b['resource_equality_seconds'] = {
                kind: sum(r['end_sec']-r['start_sec'] for r in trace['resources'] if r['kind'] == kind and start <= r['start_sec'] < start+150 and abs(r['available_veh']-r['accepted_total_veh']) < 1e-8)
                for kind in ('physical_ramp_merge_physical_receiving', 'physical_ramp_merge_eligible', 'physical_ramp_head_service')}
            blocks.append(b)
            initial = b['final_stock']
        close(initial, result['ramps'][RAMP]['final_stock'])
        t = {'case': name, 'green_sequence': greens, 'omega_ttt': result['ttt_omega_veh_h'],
             'delta_omega_ttt': result['ttt_omega_veh_h']-held['ttt_omega_veh_h'],
             'delta_outside_ttt': result['tracked_outside_residence_veh_h']-held['tracked_outside_residence_veh_h'],
             'ramp': result['ramps'][RAMP], 'wall_sec': result['wall_sec']}
        for key, label in (('freeway:FW_E','east'), ('freeway:FW_W','west'), ('ramp:'+RAMP,'ramp10484')):
            t['delta_'+label+'_ttt'] = result['cost_by_stock'][key] - held['cost_by_stock'][key]
        table.append(t)
        if name == 'held_actual':
            for start in range(2250, 2400, 30):
                timing.append({'start':start,'end':start+30,
                    'actual_arrival':native_count(960271,start,start+30), 'predicted_arrival':flow(start,start+30,'arrival'),
                    'actual_head':native_count(960220,start,start+30), 'predicted_head':flow(start,start+30,'head')})
            service = trace['head_service_by_green']
            initial_buffer = {k:v for k,v in trace['initial_buffer'].items() if k != 'initial_cohorts'}
    first = blocks[0]
    errors = {'arrival': first['arrival']-native['arrival'], 'merge':first['merge']-native['merge_from_total_stock'],
              'final_stock':first['final_stock']-native['final_stock'], 'head':first['head']-native['head']}
    close(errors['final_stock'], errors['arrival']-errors['merge'])
    pin_checks = {}
    for name, expected in protocol['pins_before'].items():
        path = Path(name) if Path(name).is_absolute() else U / name
        expected = protocol['helper_sha256'] if name.endswith('probe_selected_arrival_path.py') else expected
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
        pin_checks[name] = expected
    result = dict(status='completed',native_gain_qualified=False,command_checks=command_checks,
        scope='First150 baseline matched native command; later native actions change.450 candidate differences are autonomous model responses only.',
        quantity_constraints='N_P/N_UF feasibility NOT evaluated; actuator and interblock changes checked.',
        resource_equality_caveat='Equality counts include ties/zero availability; not exclusive causal bottleneck attribution.',
        native_first150=native,predicted_first150=first,first150_errors=errors,
        cases=table,model_blocks=blocks,arrival_head_timing=timing,head_service_vph=service,
        initial_buffer=initial_buffer,core_tuning_stop_pins=pin_checks,
        next_priority='Separate upstream dispatch/travel timing from ramp transit/receiving; do not fit a gain bonus or infer general RM ineffectiveness.')
    write('findings.json', result)
    with (HERE/'arrival_head_30s.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(timing[0]));w.writeheader();w.writerows(timing)
    write('source_pins.json',pins)
    protocol.update(stage='completed',exec_session=45775,exit_code=0,forecasts_completed=3,
                    new_native_runs=0,new_fzp_scans=0,coefficient_fits=0,live_status_polls=0,
                    core_tuning_stop_unchanged=True,goal_status='ACTIVE/NOT_QUALIFIED')
    write('protocol.json',protocol)
    print(json.dumps({'status':'completed','first150_errors':errors,'cases':table},ensure_ascii=False))


if __name__ == '__main__':
    main()
