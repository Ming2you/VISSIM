"""Four fixed seed43 responses: completed native caches versus four frozen forecasts."""
import csv
import hashlib
import json
import argparse
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=ROOT.parent/'control-full-review/diagnostics'
PRED=HERE.parent/'closedloop_recorded2250_lever450_gate_full_four_s43_v3'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prediction-dir',type=Path)
parser.add_argument('--output',type=Path)
args=parser.parse_args()
if bool(args.prediction_dir)!=bool(args.output):
    parser.error('Provide both prediction-dir and a new output; saved results cannot be replaced')
if args.prediction_dir:PRED=args.prediction_dir.resolve()
pins={}
def read(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest();return data
def load(path):return json.loads(read(path))
def rows(path):return list(csv.DictReader(read(path).decode('utf-8-sig').splitlines()))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

target=args.output.resolve() if args.output else HERE/'comparison.json'
assert not target.exists(),'Preserve completed results'
proof=load(HERE/'analysis_v2/observation_reuse.json');assert proof['passed']
pred=load(PRED/'summary.json')
assert pred['start_sec']==2250 and pred['duration_sec']==450
assert pred['future_observation_inputs'] is False and pred['optimizer_iterations']==0
assert pred['prediction_conditioned_on_executed_commands']
assert set(pred['results'])=={'held_actual','rm','vsl','both'}
geometry=load(OLD/'metanet_net_gain_goal_20260924/heldout43/observations/rm/geometry.json')
cells={(r['road'],r['cell']):r for r in geometry['cells']}
costs={};ramps=[];snapshots=[]
for arm,key in [('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both')]:
    stock=rows(HERE/f'analysis_v2/{arm}_area_stocks_5s.csv')
    assert len(stock)==91
    native={k:sum((float(a[k])+float(b[k]))*.5*(float(b['time_s'])-float(a['time_s']))/3600
                  for a,b in zip(stock,stock[1:])) for k in ('omega_n','network_n')}
    model=pred['results'][key]
    costs[arm]=dict(native_omega_veh_h=native['omega_n'],native_inserted_network_veh_h=native['network_n'],
        native_outside_omega_veh_h=native['network_n']-native['omega_n'],
        predicted_omega_veh_h=model['ttt_omega_veh_h'],predicted_tracked_total_veh_h=model['ttt_with_tracked_outside_veh_h'],
        native_end_omega_vehicles=int(stock[-1]['omega_n']),native_end_network_vehicles=int(stock[-1]['network_n']))
    folder=(OLD/'dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none' if arm=='nc'
            else OLD/f'metanet_net_gain_goal_20260924/heldout43/observations/{arm}')
    manifest=load(folder/'manifest.json')
    port_rows=rows(folder/'ports_30s.csv');cell_rows=rows(folder/'cells_30s.csv')
    if arm!='nc':
        for name in ('ports_30s.csv','cells_30s.csv'):assert pins[str(folder/name)]==manifest['files'][name]
    for ramp,value in model['ramps'].items():
        selected=[r for r in port_rows if r['connector']==ramp.removeprefix('RM_C') and r['kind']=='ramp'
                  and float(r['window_start_s'])>=2250.1-1e-7 and float(r['window_end_s'])<=2700.1+1e-7]
        assert len(selected)==15
        for r in selected:
            assert float(r['conservation_residual_veh'])==0 and float(r['unresolved_absences_veh'])==0
        actual=dict(initial_stock=float(selected[0]['start_n_veh']),final_stock=float(selected[-1]['end_n_veh']),
            arrival=sum(float(r['arrivals_veh']) for r in selected),merge=sum(float(r['departures_veh']) for r in selected))
        assert actual['initial_stock']+actual['arrival']-actual['merge']==actual['final_stock']
        assert abs(value['residual'])<1e-7
        ramps.append(dict(arm=arm,ramp=ramp,actual=actual,predicted=value,
                          error={k:value[k]-actual[k] for k in ('arrival','merge','final_stock')}))
    for at,state in zip((2250,2400,2550,2700),model['physical_cell_states']):
        assert state['time_sec']==at
        for road in ('FW_E','FW_W'):
            assert len(state['density'][road])==31
            for cell in range(31):
                native_cell=[r for r in cell_rows if r['road']==road and int(r['cell'])==cell
                             and abs(float(r['time_s'])-(at+.1))<1e-6]
                assert len(native_cell)==1;actual=native_cell[0]
                n=state['density'][road][cell]*state['effective_lanes'][road][cell]*cells[(road,cell)]['length_km']
                snapshots.append(dict(arm=arm,road=road,cell=cell,time_sec=at,native_time_sec=at+.1,
                    actual_stock=float(actual['n_veh']),predicted_stock=n,
                    actual_speed_kmh=float(actual['v_kmh']) if actual['v_kmh'] else None,
                    predicted_speed_kmh=state['speed_kmh'][road][cell]))

for arm,row in costs.items():
    row['delta_vs_nc']={k:row[k]-costs['nc'][k] for k in ('native_omega_veh_h','predicted_omega_veh_h',
        'native_inserted_network_veh_h','predicted_tracked_total_veh_h','native_outside_omega_veh_h')}
rank={kind:sorted(costs,key=lambda a:costs[a][field]) for kind,field in
      [('native','native_omega_veh_h'),('prediction','predicted_omega_veh_h')]}
best=rank['prediction'][0]
regret=costs[best]['native_omega_veh_h']-min(x['native_omega_veh_h'] for x in costs.values())
mae={k:sum(abs(r['error'][k]) for r in ramps)/len(ramps) for k in ('arrival','merge','final_stock')}
read(Path(__file__))
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==h for path,h in pins.items())
save(target,dict(seed=43,native_window_sec=[2250.1,2700.1],prediction_window_sec=[2250,2700],
    stock_integration='Trapezoid between91 consecutive5s native frames; no extrapolation',
    costs=costs,omega_rank=rank,selected_native_regret_veh_h=regret,ramp_mae_vehicles=mae,ramps=ramps,
    cell_endpoint_snapshots=snapshots,source_pins=pins,coefficient_fit=False,forecast_count=4,
    new_native_runs=0 if args.prediction_dir else 1,goal_complete=False,
    prediction_source_dir=str(PRED),
    limitations=['Executed commands condition predictions; this is not autonomous ALINEA/rule-policy forecasting.',
        'Seed43 was previously inspected; not pristine blind holdout.',
        'Native uninserted delay integral is unavailable for the matched2250-2700 window; whole-cost qualification incomplete.',
        'Native sampled stock costs and model1s integration differ by0.1s phase and discretization.',
        'NC port/cell CSVs have no historical per-file hash; their current hashes are pinned, and the native raw prefix is reverified.',
        '150s endpoint speed errors do not identify exact recovery onset or its cause.',
        'Physical/writer bounds checked; this fixed-response test is not NP/NUF feasibility or actual SDMPC selection.']))
print(json.dumps(dict(costs=costs,rank=rank,regret=regret,ramp_mae=mae),ensure_ascii=False))
