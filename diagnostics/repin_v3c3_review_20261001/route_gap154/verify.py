"""Verify the already completed154 forecasts; never launch a replacement run."""
import ast
import copy
import csv
from pathlib import Path
from types import SimpleNamespace
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    from evaluation.controllers import offramp_routing as routing
    from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    assert not (HERE/'assessment.json').exists()
    pins = {}
    def read(p):
        pins[str(p)] = h.sha(p)
        return h.read(p)
    status = read(HERE/'forecast/status.json')
    assert status['status'] == 'complete_macro_gate_failed' and status['forecasts'] == 9
    assert all(read(HERE/'forecast/parity.json').values())
    preserved = read(HERE/'forecast/preservation.json')
    assert all(preserved[k] for k in ('core', 'inputs', 'STOP', 'hooks_restored'))
    protocol = read(HERE/'forecast/protocol.json')
    assert h.sha(h.__file__) == protocol['helper_sha256']
    source = read(HERE/'forecast/executed_function_sources.json')
    base_source = read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    assert source == h.route_gap154_source(base_source)
    assert [k for k in source if source[k] != base_source[k]] == ['RouteLaneRegion', 'rollout']
    def functions(s):
        return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(s).body if isinstance(n, ast.FunctionDef)}
    old_helper = functions((HERE/'helper_before.py.txt').read_text(encoding='utf-8'))
    new_helper = functions(Path(h.__file__).read_text(encoding='utf-8'))
    assert set(new_helper)-set(old_helper) == {'route_gap154_source'}
    assert all(new_helper[k] == v for k,v in old_helper.items() if k != 'validate_frozen132')
    old_methods = {n.name:ast.dump(n) for n in ast.parse(base_source['RouteLaneRegion']).body[0].body if isinstance(n,ast.FunctionDef)}
    new_methods = {n.name:ast.dump(n) for n in ast.parse(source['RouteLaneRegion']).body[0].body if isinstance(n,ast.FunctionDef)}
    assert all(new_methods[k] == v for k,v in old_methods.items())
    assert set(new_methods)-set(old_methods) == {'ramp_gap_context'}

    # The earlier fixture omitted rollout's compiled route runtime. Supply the
    # actual selected-network contract here; this is a method unit, not a run.
    contract = read(h.F/'route_inventory/contract.json')
    mapping = read(h.F/'route_inventory/mapping31.json')
    runtime = routing.compile_inventory(contract, mapping)
    cfg = SimpleNamespace(network=SimpleNamespace(offramp_route_inventory=runtime),
                          simulation=SimpleNamespace(T_f_h=1/3600))
    namespace = {}
    exec(compile(source['RouteLaneRegion'], '154_verified_class', 'exec'), namespace)
    obj = namespace['RouteLaneRegion'].__new__(namespace['RouteLaneRegion'])
    bounds = mapping['freeway_model_links']['FW_E']['segment_bounds_m']
    obj.lengths = [(b-a)/1000 for a,b in zip(bounds,bounds[1:])]
    obj.ramp_access = {'RM_C10490':0,'RM_C10484':0}
    obj.stocks = {20:[{'test|10483':4.,'test|OUT':6.},{'test|OUT':90.},{}],22:[{'test|OUT':5.},{},{}]}
    obj.v = {20:[20.,100.,100.],22:[30.,100.,100.]}
    unit = obj.ramp_gap_context('RM_C10490',cfg)
    assert abs(unit['conflicting_vph_per_lane']-6*20/obj.lengths[20]) < 1e-8
    assert unit['current_exiting_stock'] == 4 and unit['upstream_cell'] == 20
    changed = copy.deepcopy(obj)
    changed.stocks[20][0]['test|10483'] = 40.
    changed.stocks[20][1]['test|OUT'] = 900.
    assert changed.ramp_gap_context('RM_C10490',cfg)['conflicting_vph_per_lane'] == unit['conflicting_vph_per_lane']
    obj.v[22][0] = 10000.
    assert obj.ramp_gap_context('RM_C10484',cfg)['conflicting_vph_per_lane'] == 5*3600
    h.save(HERE/'unit_verification.json',dict(status='pass_after_fixture_repair',source_sha256=h.sha(HERE/'forecast/executed_function_sources.json'),
        selected_contract_runtime=True, original_methods_unchanged=True, original_helper_functions_unchanged=len(old_helper)-1,
        cases=['upstream target lane only','current exit destination excluded','irrelevant lane/exit stocks do not change conflict','one-step available-stock cap'],
        initial_failure="AttributeError: NetworkConfig has no attribute offramp_route_inventory. Unit setup called _config without rollout runtime compilation.",
        sequencing='Forecasts were launched before the failed unit check was repaired. They were not restarted. This post-run verification repairs the fixture and verifies actual executed records; it is not a passed preflight claim.'))
    (HERE/'executed_helper.py.txt').write_text(Path(h.__file__).read_text(encoding='utf-8'),encoding='utf-8')
    compare = read(HERE/'forecast/training_assessment.json')
    rows = read(HERE/'forecast/training/rows.json')
    assert len(rows) == 8
    context,_,_ = common.setup()
    nodes = context['component'].ramp_receiving_nodes
    records = {r['arm']:r for r in common.records(False)}
    max_mass = max_route = max_ramp = 0.
    annotations = part_checks = 0
    windows = []
    for row in rows:
        key = row['case']+'_'+row['arm']
        pred = read(HERE/'forecast/training'/(key+'.json.gz'))
        d = pred['diagnostics']['roads'][0]
        max_mass = max(max_mass,d['continuity_residual_max_veh'])
        max_route = max(max_route,d['joint_lane_region']['route_marginal_max_error'])
        assert d['negative_density_count'] == 0
        part_checks += row['spatial144']['samples']
        assert row['spatial144']['max_class_partition_error'] < 1e-8
        for r in pred['ramps']:
            max_ramp = max(max_ramp,abs(r['conservation_residual_veh']))
            node = r['receiving_node']
            if r['ramp'] not in obj.ramp_access:
                assert not node.get('joint_route_lane_gap',False)
                continue
            assert node['joint_route_lane_gap'] and node['lane'] == 1
            assert abs(node['current_total_stock']-node['current_exiting_stock']-node['current_through_stock']) < 1e-7
            config_node = nodes[r['ramp']]
            gap = gap_acceptance_supply_vph(node['conflicting_vph_per_lane'],config_node['critical_gap_sec'],config_node['followup_sec'])
            assert abs(gap-node['gap_supply_vph_per_lane']) < 1e-7
            assert abs(min(gap,node['unlimited_node_canonical_budget_vph'])/3600-r['receiving_budget_veh']) < 1e-7
            assert r['accepted_merge_veh'] <= r['receiving_budget_veh']+1e-7
            annotations += 1
        if row['case'] != 's67_late' or row['arm'] not in ('release','release_vsl90'): continue
        baseline = read(h.R/'spatial_context148/forecast/training'/(key+'.json.gz'))
        path = Path(records[row['arm']]['truth'])/'ports_30s.csv'
        pins[str(path)] = h.sha(path)
        actual = list(csv.DictReader(path.open(encoding='utf-8-sig')))
        for conn in ('10490','10484'):
            for start,end in ((2670.1,2700.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                item = dict(arm=row['arm'],connector=conn,start=start,end=end)
                a = [r for r in actual if r['connector']==conn and start+1e-6 < float(r['window_end_s']) <= end+1e-6]
                item['actual'] = dict(arrivals=sum(float(r['arrivals_veh']) for r in a),merges=sum(float(r['departures_veh']) for r in a),end_n=float(a[-1]['end_n_veh']))
                assert sum(float(r['unresolved_absences_veh']) for r in a) == 0
                for label,data in [('baseline',baseline),('candidate',pred)]:
                    z = [r for r in data['ramps'] if r['start']['connector_id']==conn and start+1e-6 < r['end_sec'] <= end+1e-6]
                    item[label] = dict(arrivals=sum(r['admitted_arrivals_veh'] for r in z),merges=sum(r['accepted_merge_veh'] for r in z),end_n=z[-1]['end']['connector_veh'],ttt=sum(r['connector_ttt_veh_h'] for r in z))
                windows.append(item)
    assert annotations == 7200 and part_checks == 21600
    assert max(max_mass,max_route,max_ramp) < 1e-7
    for p,digest in {**pins,**protocol['protected_sha256'],**preserved['input_sha256']}.items(): assert h.sha(p) == digest,p
    assert h.sha(protocol['STOP']['path']) == protocol['STOP']['sha256']
    result = dict(status='complete_rejected',scope=protocol['scope'],gates=compare['checks'],pairs=compare['candidate']['pairs'],
        scores={k:{x:compare[k][x] for x in ('absolute','local','response')} for k in ('baseline','candidate')},
        windows=windows,max_mass_error=max_mass,max_route_error=max_route,max_ramp_error=max_ramp,
        verified_gap_annotations=annotations,half_partition_checks=part_checks,forecasts=9,production_adopted=False,goal_complete=False,
        limitations=protocol['limits'],new_fits=0,native=0,FZP=0,full_run_analysis=0,push=0)
    h.save(HERE/'assessment.json',result)
    h.save(HERE/'assessment_pins.json',pins)
    print('VERIFIED',result['gates'],result['scores'],'conservation',max_mass,max_route,max_ramp)
    for w in windows:print(w)


if __name__ == '__main__': main()
