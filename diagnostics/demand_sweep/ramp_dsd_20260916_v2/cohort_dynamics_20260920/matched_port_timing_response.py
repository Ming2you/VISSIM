"""Test existing port geometry and branch partitions at shared2550 states."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_lane_response as l

K, e, m, r = l.K, l.e, l.m, l.r
OUT = K / 'matched_port_timing_response_v2'


def positions(path, data, model, lane):
    observer = l.lanes.Observer(data.geometry)
    snapshots = {}
    start, end = l.scanner.START, l.scanner.END
    l.scanner.START, l.scanner.END = m.START-150, m.START
    before = path.stat()
    try:
        for t, frame in l.scanner.frames(path, {v['link'] for v in data.geometry['chains']['FW_E']}):
            if t not in (m.START-150, m.START):
                continue
            selected = []
            for vid, row in frame.items():
                loc = observer.locate((row['link'], row['lane'], row['pos'], row['speed']))
                if loc is None:
                    continue
                selected.append(dict(vehicle=vid, cell=loc[1], group=l.lanes.group(loc[1], row['lane'], l.SPLIT),
                                     chain_position_m=loc[2], speed_kmh=row['speed']))
            snapshots[str(t)] = selected
    finally:
        l.scanner.START, l.scanner.END = start, end
    assert (before.st_size, before.st_mtime_ns) == (path.stat().st_size, path.stat().st_mtime_ns)
    assert set(snapshots) == {'2400', '2550'}
    ramps = {str(v['connector']): (key, v) for key, v in model.ramps.items() if v['road']=='FW_E'}
    offs = {key: v for key, v in model.offramps.items() if v['road']=='FW_E'}
    counts, eligible, partitions = {}, {}, {}
    for t, vehicles in snapshots.items():
        past = {}
        for event in data.events:
            if event['kind'] != 'departure' or event['connector'] not in ramps or float(event['time_s']) > int(t):
                continue
            vid, stamp = int(event['vehicle']), float(event['time_s'])
            key, spec = ramps[event['connector']]
            if vid not in past or stamp > past[vid][0]:
                past[vid] = (stamp, key, spec['to_cell'])
        counts[t] = {key: [0.]*len(lane['widths'][spec['to_cell']]) for key, spec in ramps.values()}
        eligible[t] = {key: [0.]*len(lane['widths'][spec['from_cell']]) for key, spec in offs.items()}
        for v in vehicles:
            old = past.get(v['vehicle'])
            if old is not None and old[2] == v['cell']:
                counts[t][old[1]][v['group']] += 1
            for key, spec in offs.items():
                if v['cell'] == spec['from_cell'] and v['chain_position_m'] <= spec['chain_pos_m']:
                    eligible[t][key][v['group']] += 1
        for cell in range(21):
            actual = next(v for v in data.cells[int(t)] if v['road']=='FW_E' and v['cell']==cell)
            assert sum(v['cell']==cell for v in vehicles) == actual['n_veh']
    current = snapshots[str(m.START)]
    for key, spec in offs.items():
        c, cut = spec['from_cell'], spec['chain_pos_m']
        partitions[key] = {}
        for side in ('pre','post'):
            values = []
            for group in range(len(lane['widths'][c])):
                rows = [v for v in current if v['cell']==c and v['group']==group
                        and (v['chain_position_m'] <= cut)==(side=='pre')]
                fallback = lane['initial_groups'][c][group]['v_kmh']
                if fallback is None:
                    fallback = next(v['v_kmh'] for v in data.cells[m.START] if v['road']=='FW_E' and v['cell']==c)
                values.append(dict(n_veh=len(rows), v_kmh=sum(v['speed_kmh'] for v in rows)/len(rows) if rows else fallback))
            partitions[key][side] = values
        for group, row in enumerate(lane['initial_groups'][c]):
            assert row['n_veh'] == sum(partitions[key][s][group]['n_veh'] for s in ('pre','post'))
    return dict(counts=counts, eligible_before_off=eligible, branch_partition_initial=partitions,
                current_vehicles=current, latest_observation_s=m.START,
                source_receipt=dict(path=path.relative_to(e.ROOT).as_posix(),bytes=before.st_size,mtime_ns=before.st_mtime_ns),
                future_routes_used=False)


def main():
    OUT.mkdir(exist_ok=False)
    begun = time.perf_counter()
    variants = {'port_timing': [], 'partition13': ['10483'], 'partition8_13': ['10643','10483']}
    base = e.load(l.OUT / 'lane.json')
    base['freeway'].update(physical_lane_destination_policy='clear_ending_lane',
        physical_port_travel_lengths=True, physical_port_initial_positions=True, physical_port_origin_split=True,
        physical_ramp_lane_coupling={'RM_C10681':[0,1]}, physical_ramp_conflict_through_inventory=['RM_C10681'],
        physical_offramp_lanes={'10643':dict(entry_groups=[0,1],history_sec=150)})
    configs = {}
    for name, ports in variants.items():
        config = copy.deepcopy(base)
        if ports:
            config['freeway'].update(physical_branch_partition=ports, physical_partition_speed_context=True,
                                     physical_partition_exchange=False)
        configs[name] = OUT / (name+'.json')
        e.save(configs[name], config)
    params = e.load(m.MODEL/'selected_parameters.json')['parameters']
    profile = e.load(m.MODEL/'port_profile.json')
    results = {}; interfaces = west_exact = reused = 0
    sources = [Path(__file__), Path(l.__file__), Path(r.__file__), m.MODEL/'selected_parameters.json',
        m.MODEL/'port_profile.json', e.CAL/'canonical_harness.py', K.parent/'evaluate_response.py',
        e.ROOT/'evaluation/controllers/physical_lane_groups.py',
        e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py']
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit
    for seed in (23, 33):
        bank = m.BANK if seed==23 else K.parent/'state_response_20260919/native_s33_v1'
        refarm = 'rm8' if seed==23 else 'rm_ramp'
        data = m.prepare_data(bank/'observations'/refarm); cut = r.cutoff_only(data)
        lane = e.load(l.OUT/f'initial_s{seed}.json')
        model = e.load_base_model(data.geometry, configs['port_timing'])
        initial = positions(bank/('run_'+refarm)/'vissim_eval/baseline_001.fzp', cut, model, lane)
        e.save(OUT/f'positions_s{seed}.json', initial)
        sources += [l.OUT/f'initial_s{seed}.json', OUT/f'positions_s{seed}.json']
        results[str(seed)] = {}
        for name, ports in variants.items():
            model = e.load_base_model(data.geometry, configs[name])
            cases = {}
            for arm, sequence in r.COMMANDS.items():
                command = lambda t: ({'RM_C10490':sequence[int((t-m.START)//150)]},{})
                w = e.window(cut,model,m.START,'history_forecast',profile,command,port_origin_counts=initial['counts'])
                assert w == e.window(data,model,m.START,'history_forecast',profile,command,port_origin_counts=initial['counts'])
                spec = copy.deepcopy(lane)
                spec.update(initial_ramp_origin=initial['counts']['2550'],initial_off_eligible=initial['eligible_before_off']['2550'])
                if ports:
                    spec['branch_partition_initial'] = {p:initial['branch_partition_initial'][p] for p in ports}
                w['lane_group_dynamics']={'FW_E':spec}
                old = K/'matched_port_timing_response_v1'
                if seed == 23 and name in ('port_timing', 'partition13'):
                    assert e.load(old/(name+'.json')) == e.load(configs[name])
                    assert w == e.load(old/f'window_s{seed}_{name}_{arm}.json')
                    pred = e.load(old/f'prediction_s{seed}_{name}_{arm}.json')
                    sources += [old/f'prediction_s{seed}_{name}_{arm}.json', old/f'window_s{seed}_{name}_{arm}.json',
                                old/'source_before_scope_fix.txt']
                    reused += 1
                else:
                    pred=e.simulate(model,w,params)
                e.save(OUT/f'prediction_s{seed}_{name}_{arm}.json',pred)
                e.save(OUT/f'window_s{seed}_{name}_{arm}.json',w)
                checks=audit(pred,e.load(r.OUT/f'prediction_s{seed}_step1_{arm}.json'))
                interfaces+=checks['lane_interface_checks'];west_exact+=1
                cases[arm]=dict(component=m.parts(pred),interface=checks,
                    terminal=sum(v['terminal_exits'] for v in pred['flows'] if v['road']=='FW_E'),
                    merges={v['ramp']:v['end']['cumulative_merge_veh'] for v in pred['ramps'] if v['road']=='FW_E' and v['end_sec']==m.END})
                print(json.dumps(dict(seed=seed,candidate=name,arm=arm,cost=cases[arm]['component'])),flush=True)
            for arm in ('rm6','rm_ramp'):
                delta={key:cases[arm]['component'][key]-cases['rm8']['component'][key] for key in ('mainline','on','off')}
                cases[arm]['delta_vs_g8']=dict(**delta,total=sum(delta.values()))
            results[str(seed)][name]=cases
            e.save(OUT/f'result_s{seed}_{name}.json',cases)
    e.save(OUT/'result.json',dict(qualified=False,future_inputs=False,fitted_parameters=0,native_runs=0,
        elapsed_sec=time.perf_counter()-begun,exact_west_cases=west_exact,lane_interface_checks=interfaces,cases=results,
        reused_exact_input_predictions=reused,
        scope='Existing optional geometry/lane implementations; not the old2400 urban-route coupled experiment.',
        limitations=['No current route labels or future routes inferred.', 'Past150s average off-drain service,not an urban network model.',
                     'Off10481 is in cell12 with a terminating lane; existing branch-partition code rejects this geometry. The first attempt is retained; no guard was bypassed.',
                     'Development states only; no adoption or holdout claim.'],
        source_pins={p.relative_to(e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}))


if __name__=='__main__':main()
