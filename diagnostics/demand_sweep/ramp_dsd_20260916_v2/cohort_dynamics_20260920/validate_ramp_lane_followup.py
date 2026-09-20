"""Preserve earlier source pins and verify final lane-coupling metadata patch."""
from pathlib import Path
import sys,json,hashlib,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'ramp_lane_followup_validation_v1.json'
    if out.exists():raise FileExistsError(out)
    archives={};archive_checks=0
    for folder in ['ramp_lane_coupling_v1/source_before','ramp_lane_coupling_v1/source_before_metadata']:
        for original,row in e.load(HERE/folder/'manifest.json').items():
            p=HERE/folder/row['snapshot'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
            archives[Path(original).as_posix(),row['sha256']]=str(p.relative_to(e.ROOT));archive_checks+=1
    pinchecks=0;archived_pins=[]
    for path,key in [('port_arrival_response_v1/result.json','pins'),('merge_cell_transport_v1/result.json','pins'),
                     ('ramp_lane_coupling_v1/evaluation/protocol.json','pins'),('ramp_lane_inventory_v1/result.json','pins')]:
        for name,pin in e.load(HERE/path)[key].items():
            if hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest()!=pin:
                identity=(Path(name).as_posix(),pin)
                assert identity in archives,(path,name)
                archived_pins.append(dict(result=path,source=name,snapshot=archives[identity]))
            pinchecks+=1
    config=HERE/'ramp_lane_coupling_v1/evaluation/config.json'
    checked=subprocess.run([sys.executable,'-B','-X','utf8',str(e.ROOT/'scripts/verify_parameters.py'),str(config)],
        cwd=e.ROOT,encoding='utf-8',capture_output=True)
    assert checked.returncode==0 and 'PASS' in checked.stdout
    params=e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    exact=0;interfaces=0;replayed=[]
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        model=e.load_base_model(data.geometry,config);original=model._config
        def configured(road,p,original=original):
            cfg=original(road,p)
            if road=='FW_E':cfg.network.terminal_zero_gradient=True
            return cfg
        model._config=configured
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)],
                'initial_ramp_origin':origin['counts'][str(start)],'initial_off_eligible':origin['eligible_before_off'][str(start)]}}
            predicted=e.simulate(model,w,params)
            reference=e.load(HERE/f'ramp_lane_coupling_v1/evaluation/prediction_s{seed}_{arm}.json')
            interfaces+=audit(predicted,reference)['lane_interface_checks']
            expected=reference['diagnostics']['dynamic_ramp_boundary']['metadata']['RM_C10681']
            expected.update(lane_supply='Explicit lane receiving budgets; accepted merges retain their physical target group',lane_to_mainline_group=[0,1])
            assert json.loads(json.dumps(predicted))==reference;exact+=1
            replayed.append(dict(seed=seed,arm=arm,json_sha256=hashlib.sha256(json.dumps(predicted,sort_keys=True).encode()).hexdigest()))
        print('FINAL_METADATA_REPLAY',seed,'exact',exact,flush=True)
    test=e.load(HERE/'ramp_lane_coupling_v1/tests.json');assert test['passed'] and test['tests']==113
    evaluation=e.load(HERE/'ramp_lane_coupling_v1/evaluation/result.json')
    assert evaluation['reference_json_exact']==12 and evaluation['lane_interface_checks']==1080
    ports=e.load(HERE/'port_arrival_response_v1/result.json');assert ports['native_stock_checks']==15360 and ports['history_json_exact']==8
    inventory=e.load(HERE/'ramp_lane_inventory_v1/result.json');assert inventory['checks']==3728
    transport_checks=0;transport_snapshots=0
    for seed in (23,33):
        for arm in ('none','rm10484'):
            rows=e.load(HERE/f'merge_cell_transport_v1/fields_s{seed}_{arm}.json')
            transport_checks+=rows['native_lane_conservation_checks'];transport_snapshots+=len([r for r in rows['rows'] if r['t']%30==0])
    assert transport_checks==5400 and transport_snapshots==64
    sources=[e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        e.ROOT/'evaluation/controllers/physical_lane_groups.py',config,Path(__file__)]
    e.save(out,dict(status='VERIFICATION_PASS_GAIN_NOT_QUALIFIED',new_native_runs=0,production_adopted=False,
        tests=test,parameter_check=dict(returncode=checked.returncode,stdout=checked.stdout,stderr=checked.stderr),
        final_metadata_only_exact=exact,replays=replayed,final_lane_interface_checks=interfaces,
        original_disabled_exact=12,source_pin_checks=pinchecks,source_archive_checks=archive_checks,archived_pins=archived_pins,
        native_port_stock_checks=15360,native_ramp_lane_checks=3728,native_merge_cell_lane_checks=5400,native_merge_cell_snapshot_checks=64,
        state_guards_passed=sum(r['guards_passed'] for r in evaluation['results'].values()),state_guard_count=12,
        final_source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        limitations=['Historical future-arrival and transport exposures are diagnostic only.',
            'Per-lane mainline coupling fixes an interface; independent ramp lanes still omit observed internal exchange.',
            'Canonical harness metadata was corrected after the evaluation. All12 full JSONs revalidated with that metadata-only difference.',
            'No coefficient calibration, fresh native validation, full GNE or whole-Omega qualification in this checkpoint.']))


if __name__=='__main__':main()
