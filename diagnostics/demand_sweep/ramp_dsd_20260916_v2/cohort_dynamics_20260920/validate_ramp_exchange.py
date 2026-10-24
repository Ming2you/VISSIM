"""Final compatibility, provenance and stage/physical-lane conservation receipt."""
from pathlib import Path
import sys,json,hashlib,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'ramp_exchange_v1/validation.json'
    if out.exists():raise FileExistsError(out)
    archives={};source_checks=0;archived=[]
    for directory in ('source_before','source_before_lane_profile'):
        for name,item in e.load(HERE/f'ramp_exchange_v1/{directory}/manifest.json').items():
            path=HERE/f'ramp_exchange_v1/{directory}'/item['snapshot']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
            archives[Path(name).as_posix(),item['sha256']]=str(path.relative_to(e.ROOT))
    for name in ('evaluation','identification','receiving_identification'):
        protocol=e.load(HERE/f'ramp_exchange_v1/{name}/protocol.json')
        for file,pin in protocol['pins'].items():
            if hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()!=pin:
                identity=Path(file).as_posix(),pin;assert identity in archives,(name,file)
                archived.append(dict(protocol=name,file=file,source_snapshot=archives[identity]))
            source_checks+=1
    test=e.load(HERE/'ramp_exchange_v1/tests_v2.json');assert test['passed'] and test['tests']==123
    optimized=subprocess.run([sys.executable,'-B','-O','-X','utf8','-m','unittest',
        'diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.test_ramp_exchange'],cwd=e.ROOT,encoding='utf-8',capture_output=True)
    assert optimized.returncode==0
    config=HERE/'ramp_exchange_v1/evaluation/config.json'
    verified=subprocess.run([sys.executable,'-B','-X','utf8',str(e.ROOT/'scripts/verify_parameters.py'),str(config)],cwd=e.ROOT,encoding='utf-8',capture_output=True)
    assert verified.returncode==0 and 'PASS' in verified.stdout
    params=e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    exact=Counter=0;active=0;interfaces=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        for variant,path in [('original',HERE/'port_origin_split_v1/config.json'),('candidate',config)]:
            model=e.load_base_model(data.geometry,path);prior=model._config
            def configured(road,p,prior=prior):
                cfg=prior(road,p)
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
                p=e.simulate(model,w,params)
                reference=e.load(HERE/(f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json' if variant=='original'
                                      else f'ramp_exchange_v1/evaluation/prediction_s{seed}_{arm}.json'))
                assert json.loads(json.dumps(p))==reference,(seed,arm,variant)
                if variant=='original':exact+=1
                else:active+=1;interfaces+=audit(p,reference)['lane_interface_checks']
        print('EXACT_FINAL',seed,exact,active,flush=True)
    forecast_checks=0;lane_balances=0;timing=[]
    for directory in ('evaluation','identification','receiving_identification'):
        for path in sorted((HERE/f'ramp_exchange_v1/{directory}').glob('prediction_*.json')):
            pred=e.load(path)
            for road in pred['diagnostics']['roads']:
                assert road['continuity_residual_max_veh']<1e-7 and road['negative_density_count']==road['jam_density_exceedance_count']==0
            for row in pred['ports']+pred['ramps']:assert abs(row['conservation_residual_veh'])<1e-7
            for row in pred['ramps']:
                if row['ramp']!='RM_C10681':continue
                a,z=row['start'],row['end']
                assert abs(z['cumulative_lane_entry_veh']-z['cumulative_lane_exit_veh'])<1e-7
                for lane in row['lane_receipts']:
                    a,z=lane['start'],lane['end']
                    assert abs(z['connector_veh']-a['connector_veh']-lane['admitted_arrivals_veh']+lane['accepted_merge_veh']-
                        (z['cumulative_lane_entry_veh']-a['cumulative_lane_entry_veh'])+
                        (z['cumulative_lane_exit_veh']-a['cumulative_lane_exit_veh']))<1e-7
                    lane_balances+=1
            forecast_checks+=1
    for seed in (23,33):
        for arm in ('none','vsl'):
            fields=e.load(HERE/f'ramp_lane_inventory_v1/{seed}_{arm}.json')
            p=e.load(HERE/f'ramp_exchange_v1/receiving_identification/prediction_s{seed}_{arm}.json')
            for start in (2400,2550,2700):
                observed=sum(r['kind']=='departure' and r['lane']==2 and start<r['time_s']<=start+150 for r in fields['events'])
                predicted=sum(r['lane_receipts'][1]['accepted_merge_veh'] for r in p['ramps'] if r['ramp']=='RM_C10681' and start<r['end_sec']<=start+150)
                timing.append(dict(seed=seed,arm=arm,start=start,end=start+150,actual_lane2_merges=observed,predicted_lane2_merges=predicted))
    assert forecast_checks==28 and lane_balances==2520
    evaluation=e.load(HERE/'ramp_exchange_v1/evaluation/result.json')
    files=[Path(__file__),e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        HERE/'ramp_exchange_v1/evaluation/calibration.json',HERE/'ramp_exchange_v1/evaluation/training_fields.json',
        HERE/'test_ramp_exchange.py',H/'controller_response_v1/heads.json',config]
    e.save(out,dict(status='VERIFICATION_PASS_GAIN_NOT_QUALIFIED',new_native_runs=0,production_adopted=False,
        tests=test,optimized_tests=dict(returncode=optimized.returncode,stdout=optimized.stdout,stderr=optimized.stderr),
        parameter_check=dict(returncode=verified.returncode,stdout=verified.stdout,stderr=verified.stderr),
        original_disabled_json_exact=exact,final_active_json_exact=active,final_lane_interface_checks=interfaces,
        forecast_conservation_checks=forecast_checks,stage_lane_balance_checks=lane_balances,
        source_pin_checks=source_checks,archived_pins=archived,state_guards_passed=sum(r['guards_passed'] for r in evaluation['results'].values()),
        receiving_oracle_lane2_timing=timing,source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        caveats=['The stage rates use seed13 NC900..2100 only, not controlled gains. State guards on13 are development checks, not unseen forecasts.',
            'Future lane entries, exchange fractions and conflict flows are diagnostic only; core defaults do not supply them.',
            'Stage-homogeneous proportional exchange and aggregate stage room are approximations, not microscopic gap feasibility.',
            'Current calibration still fails gains and two NC guards; no production or full-GNE qualification.']))


if __name__=='__main__':main()
