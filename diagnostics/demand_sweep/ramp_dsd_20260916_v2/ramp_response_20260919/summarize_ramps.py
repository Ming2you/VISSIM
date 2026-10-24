"""Per-port decomposition; keep 30s scoring separate from native 1s residence."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.verify import CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.calibrate_ramps import *


def trap30(values):
    return sum((a+b)*30/7200 for a,b in zip(values,values[1:]))


def main():
    out = HERE/'decomposition_v1'
    out.mkdir(exist_ok=False)
    result = {}
    for seed, folder, bank, start in CASES:
        nc = prepare_data(folder)
        model = e.load_base_model(nc.geometry, BASE/'config.json')
        rows = {}
        for arm in ['none','rm_ramp']:
            data = nc if arm == 'none' else prepare_data(bank/'observations'/arm)
            variants = {name: e.load(HERE/'arrival_v1/gap84'/f'prediction_{seed}_{label}_{arm}.json')
                        for name, label in [('baseline','baseline'),('gap84','spatial')]}
            rows[arm] = {}
            definitions = [(str(r['connector']), mid, 'on', r['road']) for mid,r in model.ramps.items()]
            definitions += [(c, c, 'off', r['road']) for c,r in model.offramps.items()]
            for c, mid, kind, road in definitions:
                native = {'ttt_30s_trapezoid_veh_h': trap30([
                    len(data.port_cohorts[str(t)][c]) for t in range(start,start+451,30)]),
                    'arrivals_veh': sum(data.arrivals[t,c] for t in range(start+1,start+451)),
                    'departures_veh': sum(data.departures[t,c] for t in range(start+1,start+451)),
                    'end_veh': len(data.port_cohorts[str(start+450)][c])}
                if kind == 'on':
                    native.update(head_crossings_veh=sum(data.head_counts[t,c] for t in range(start+1,start+451)))
                    for field, source in [('prehead','prehead_n'),('posthead','posthead_n')]:
                        # Native1s right-end stock integral; no 30s resampling.
                        native[field+'_ttt_1s_right_veh_h'] = sum(
                            float(data.headstocks[t,c][source]) for t in range(start+1,start+451))/3600
                records = {'kind':kind,'road':road,'native':native}
                for name, pred in variants.items():
                    if kind == 'on':
                        rs = [r for r in pred['ramps'] if r['ramp']==mid]
                        at = {r['end_sec']:r['end']['connector_veh'] for r in rs}
                        end = rs[-1]['end']
                        val = {'ttt_1s_left_veh_h':sum(r['connector_ttt_veh_h'] for r in rs),
                            'arrivals_veh':end['cumulative_admitted_veh'],
                            'requests_veh':end['cumulative_requested_veh'],
                            'head_crossings_veh':end['cumulative_head_service_veh'],
                            'departures_veh':end['cumulative_merge_veh'],
                            'end_veh':end['connector_veh'],
                            'outside_backlog_veh':end['outside_component_backlog_veh']}
                    else:
                        rs = [r for r in pred['ports'] if r['connector']==c]
                        at = {r['time_s']:r['n_veh'] for r in rs}
                        end = rs[-1]
                        val = {'arrivals_veh':end['admitted_veh'],
                            'departures_veh':end['departed_veh'],'end_veh':end['n_veh']}
                    at[start] = len(nc.port_cohorts[str(start)][c])
                    val['ttt_30s_trapezoid_veh_h'] = trap30([at[t] for t in range(start,start+451,30)])
                    records[name] = val
                rows[arm][c] = records
        deltas = {}
        for c, row in rows['none'].items():
            deltas[c] = {'kind':row['kind'],'road':row['road']}
            for name in ['native','baseline','gap84']:
                deltas[c][name] = {k: rows['rm_ramp'][c][name][k]-v for k,v in row[name].items()}
        result[str(seed)] = {'start_sec':start,'end_sec':start+450,'arms':rows,'rm_minus_nc':deltas}
        print(seed, {c:{n:round(d[n]['ttt_30s_trapezoid_veh_h'],6) for n in ['native','baseline','gap84']}
                     for c,d in deltas.items() if d['road']=='FW_E'}, flush=True)
    write(out/'per_port.json', result)
    write(out/'definitions.json', {
        'scope':'Individual on/off connectors; not Omega. Counts are native connector crossings, not desired demand.',
        'score':'TTT from identical30s stock trapezoids used in prior reports.',
        'native_1s':'Separately reported sum of post-step stocks. Prehead includes travelling and waiting upstream of meter.',
        'model_1s':'Separately reported integration of beginning-of-step stock; endpoint convention differs from native.',
        'selection':'RM−NC first450s; paired initial conditions; mainline coefficients unchanged.'})


if __name__ == '__main__':
    main()
