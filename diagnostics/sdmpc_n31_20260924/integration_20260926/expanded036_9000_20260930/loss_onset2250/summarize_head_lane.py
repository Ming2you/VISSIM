"""Verify two bounded lane-aware initial-queue forecasts from saved files."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
I = HERE.parent.parent
U = I.parents[2]
OUT = HERE/'city_path'
DEC = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
pins = {}


def load(path):
    raw = path.read_bytes()
    pins[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


native = load(OUT/'native.json')['results']
native_ramp = {2250:load(HERE/'findings.json')['native_first150'],
               3600:load(HERE/'speed_binding/verification.json')['independent3600']['native150']}
results = {}
for at in (2250,3600):
    arms = {}
    arrival_times = {}
    for label in ('after','after_hl'):
        folder = OUT/f'{at}_{label}'
        initial = load(folder/'initial.json')['state']
        trace = load(folder/'trace.json.gz')
        item = load(I/f'closedloop_recorded{at}_lever450_RM_C10484_city{at}_{label}/held_actual.json')
        def flow(source=None,target=None):
            return sum(r['vehicles'] for r in trace['transfers'] if r['end_sec'] <= at+150
                and (source is None or r['source'] == source)
                and (target is None or r['target'] == target))
        flows = dict(upstream329=flow('movement:SC1002_E_SC101_to_W_SC1001'),
            downstream29=flow('movement:SC1001_E_SC1002_to_W_RAMP'),
            ramp_arrival=flow(target='ramp:RM_C10484'),
            ramp_merge=flow('ramp:RM_C10484','merge_pending:RM_C10484'))
        bins = [sum(r['vehicles'] for r in trace['transfers']
                    if r['source'] == 'movement:SC1002_E_SC101_to_W_SC1001'
                    and at+30*j <= r['start_sec'] < at+30*(j+1)) for j in range(5)]
        arrivals = {}
        for r in trace['transfers']:
            if r['end_sec'] <= at+150 and r['target'] == 'movement:SC1001_E_SC1002_to_W_RAMP':
                arrivals[r['end_sec']] = arrivals.get(r['end_sec'],0.)+r['vehicles']
        arrival_times[label] = arrivals
        mass = max(abs(r['residual']) for r in item['ramps'].values())
        assert mass < 1e-8
        assert abs(item['ttt_omega_veh_h']-trace['ttt']) < 1e-8
        arms[label] = dict(flows_first150=flows,upstream329_30s_bins=bins,ttt450=trace['ttt'],
            upstream329_service_vph=load(folder/'initial.json')['network']['movement_capacity_by_movement_veh_h']['SC1002_E_SC101_to_W_SC1001'],
            ramp_mass_max=mass,initial=initial,commands=item['commands'],
            initial_freeway=item['physical_cell_states'][0])
        if label == 'after_hl':
            receipt = load(folder/'receipt.json')
            assert receipt['forecast_count'] == 1
            assert receipt['future_observation_inputs'] is False
            assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h
                       for p,h in receipt['pins'].items())
    old,new = arms['after'],arms['after_hl']
    assert old['commands'] == new['commands']
    assert old['initial_freeway'] == new['initial_freeway']
    for field in ('storage','arrival_buffer','release_buffer','urban_link_speed_kph'):
        assert old['initial'][field] == new['initial'][field]
    proj = load(OUT/f'{at}_after_hl/projection.json')
    diag = proj['diagnostics']
    original = load(DEC/f'action_{at:06d}.json')['projection_diagnostics']
    a,b = diag['physical_stock_assignment_by_link'],original['physical_stock_assignment_by_link']
    changed = [k for k in a.keys()|b.keys() if a.get(k) != b.get(k)]
    assert set(changed) == {'29','329'},changed
    assert all(abs(sum(a[k].values())-sum(b[k].values())) < 1e-8 for k in a)
    assert diag['mass_balance_error_veh'] == original['mass_balance_error_veh']
    assert set(diag['head_phase_queue_attribution']) == {'29','329'}
    # Only six selected queues may change in the saved subset; no stock added.
    queue_delta = {k:[v,new['initial']['queue'][k]] for k,v in old['initial']['queue'].items()
                   if v != new['initial']['queue'][k]}
    assert abs(sum(old['initial']['queue'].values())-sum(new['initial']['queue'].values())) < 1e-8
    for arm in arms.values():
        del arm['initial'],arm['commands'],arm['initial_freeway']
    ramp = native_ramp[at]
    aa,bb = arrival_times['after_hl'],arrival_times['after']
    extra = {t:aa.get(t,0.)-bb.get(t,0.) for t in aa.keys()|bb.keys()
             if abs(aa.get(t,0.)-bb.get(t,0.)) > 1e-9}
    results[at] = dict(arms=arms,native_first150=dict(upstream329=native[str(at)]['native_upstream329'],
        downstream29=native[str(at)]['native_downstream29'],ramp_arrival=ramp['arrival'],
        ramp_merge=ramp.get('merge',ramp.get('merge_from_total_stock'))),
        queue_delta=queue_delta,changed_physical_links=sorted(changed),
        downstream_extra_arrivals_first150=extra,native_30s_bins=native[str(at)]['bins'],
        lane_projection=diag['head_phase_queue_attribution'],
        unchanged_legacy_projection_mass_residual=diag['mass_balance_error_veh'],
        total_initial_queue=sum(proj['queue'].values()),same_commands=True,same_freeway=True,
        unchanged_other_physical_assignments=True,same_storage_buffers_speeds=True)

unchanged = {}
for name,digest in load(HERE/'speed_binding/protocol.json')['pins'].items():
    path = Path(name)
    if path.name == 'lane_plant_runtime.py':
        digest = hashlib.sha256((HERE/'speed_binding/lane_plant_runtime_after.txt').read_bytes()).hexdigest()
    unchanged[name] = hashlib.sha256(path.read_bytes()).hexdigest() == digest
assert all(unchanged.values())
base = load(I/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json')
candidate = load(OUT/'head_lane_config.json')
assert candidate['urban']['queue'].pop('attribution') == 'head_phase'
assert candidate['urban']['queue'].pop('head_lane_contract').endswith('head_lane_support.json')
assert candidate == base
for name in ('observation_projection.py','runtime_setup.py','vissim_stackelberg_adapter.py'):
    source = U/'evaluation/controllers'/name
    data = source.read_bytes()
    pins[str(source)] = hashlib.sha256(data).hexdigest()
    (OUT/(name+'.after_lane.txt')).write_bytes(data)
contract = load(OUT/'head_lane_support.json')
report = dict(status='bounded_diagnosis_complete',goal='ACTIVE/NOT_QUALIFIED',
    adopted=False,new_forecasts=2,initialization_trials=3,tests_passed=17,
    native_runs=0,fzp_scans=0,coefficient_fits=0,live_polls=0,push=0,
    sessions={96547:'init_exit0_phase_only',61989:'init_exit0_global_head_phase_lane',
              2572:'init_exit0_scoped_lane',21016:'two_forecasts_exit0'},
    states=results,unchanged_pins=unchanged,source_pins=pins,
    scope='Initial queue attribution on roads29/329 only. Lane support approximates current head access, not future destination certainty.',
    qualification='No gain/SDMPC/NP/NUF/derivative qualification. First150 shares native commands; later native actions differ. Same seed29, not independent-seed validation.')
(OUT/'head_lane_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({at:{'arms':v['arms'],'native':v['native_first150'],
    'queue_delta':v['queue_delta'],'legacy_projection_residual':v['unchanged_legacy_projection_mass_residual']}
    for at,v in results.items()},indent=2))
