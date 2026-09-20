"""NC-only stage exchange calibration and predeclared450s response checks."""
from pathlib import Path
import sys,hashlib,json,subprocess
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import ramp_lane_inventory_audit as native
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit

HERE=Path(__file__).resolve().parent


def fit(out):
    _,folder,_,_=CASES[0];data=e.ObservationData(folder)
    manifest=e.load(folder/'manifest.json');path=Path(manifest['source_run'])/'vissim_eval/baseline_001.fzp'
    head=min(e.load(H/'controller_response_v1/heads.json')['10681'].values())
    port=next(r for r in data.geometry['boundaries'] if r['connector']==10681)
    old=(native.START,native.END);native.START,native.END=900,2100
    try:fields=native.extract(path,head,port['length_m'])
    finally:native.START,native.END=old
    expected=Counter((int(float(r['time_s'])),int(r['vehicle']),r['kind'],int(r['lane']))
        for r in e.rows(folder/'port_events.csv') if r['connector']=='10681' and 900<float(r['time_s'])<=2100)
    assert expected==Counter((r['time_s'],r['vehicle'],r['kind'],r['lane']) for r in fields['events'])
    counts={stage:[[0.,0.],[0.,0.]] for stage in ('prehead','posthead')}
    exposure={stage:[0.,0.] for stage in counts};ambiguities=0
    for row in fields['rows'][:-1]:
        for r in row['lanes']:
            exposure['prehead'][r['lane']-1]+=r['prehead']
            exposure['posthead'][r['lane']-1]+=r['n']-r['prehead']
    for r in fields['exchanges']:
        stage='prehead' if r['from_position_m']<head else 'posthead'
        counts[stage][r['from_lane']-1][r['to_lane']-1]+=1
        ambiguities+=stage!=r['stage']
    rates={stage:[[n/exposure[stage][i] if exposure[stage][i] else 0. for n in row]
        for i,row in enumerate(matrix)] for stage,matrix in counts.items()}
    for stage,matrix in counts.items():
        for i,row in enumerate(matrix):assert not sum(row) or exposure[stage][i]>0
    e.save(out/'training_fields.json',fields)
    result=dict(seed=13,start=900,end=2100,counts=counts,donor_vehicle_seconds=exposure,rates_per_sec=rates,
        crossing_and_lane_change_in_same_second=ambiguities,
        definition='Observed exchange count / start-frame donor stage vehicle-seconds. Stage from previous position, matching transfer before longitudinal motion. Fixed NC-only rates; no control gains used.',
        source=fields['source'],boundary_events_exact=True,native_lane_checks=fields['lane_conservation_checks'])
    e.save(out/'calibration.json',result);print('NC_ONLY_RATES',result,flush=True)
    return rates


def main():
    out=HERE/'ramp_exchange_v1/evaluation';out.mkdir(exist_ok=False)
    rates=fit(out);base=HERE/'ramp_lane_coupling_v1/evaluation/config.json';config=out/'config.json'
    cfg=e.load(base);cfg['freeway']['physical_ramp_lane_exchange']={'RM_C10681':rates};e.save(config,cfg)
    param=HERE/'port_travel_fit_v1/selected_parameters.json';params=e.load(param)['parameters'];profile=e.load(MODEL/'port_profile.json')
    files=[Path(__file__),HERE/'ramp_lane_inventory_audit.py',HERE/'ramp_lane_coupling_check.py',base,config,param,MODEL/'port_profile.json',
        e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        e.ROOT/'evaluation/controllers/physical_lane_groups.py',H/'evaluate_response.py']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,fit='One NC-only stage-rate estimate; no sweep and no gain fit',
        new_native_runs=0,future_inputs=False,training_seed=13,inspected_development_seeds=[13,23,33],
        state_guard='12 objectives <=1.10 established internal_cost, not candidate reference. Must also repair lane costs and gain, not only conservation.'))
    checked=subprocess.run([sys.executable,'-B','-X','utf8',str(e.ROOT/'scripts/verify_parameters.py'),str(config)],
        cwd=e.ROOT,encoding='utf-8',capture_output=True)
    e.save(out/'parameter_check.json',dict(returncode=checked.returncode,stdout=checked.stdout,stderr=checked.stderr));assert checked.returncode==0
    established=e.load(HERE/'open_speed_fit_v2/results.json')['baseline_state_scores'];results={};exact=interfaces=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origins=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json');models={}
        for name,path in [('reference',base),('candidate',config)]:
            model=e.load_base_model(data.geometry,path);original=model._config
            def configured(road,p,original=original):
                cfg=original(road,p)
                if road=='FW_E':cfg.network.terminal_zero_gradient=True
                return cfg
            model._config=configured;models[name]=model
        def window(model,t,command):
            w=e.window(data,model,t,'history_forecast',profile,command,port_origin_counts=origins['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)],
                'initial_ramp_origin':origins['counts'][str(t)],'initial_off_eligible':origins['eligible_before_off'][str(t)]}}
            return w
        guards={}
        for t in (900,1650,2400,3600):
            p=e.simulate(models['candidate'],window(models['candidate'],t,lambda _: ({},{})),params)
            score=e.score_rollout(data,t,p,'FW_E');assert not score['invalid']
            guards[str(t)]=dict(score=score,ratio=score['objective']/established[str(seed)][str(t)]['objective'])
        costs={};lane_results={}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            reference=e.load(HERE/f'ramp_lane_coupling_v1/evaluation/prediction_s{seed}_{arm}.json')
            reference['diagnostics']['dynamic_ramp_boundary']['metadata']['RM_C10681'].update(
                lane_supply='Explicit lane receiving budgets; accepted merges retain their physical target group',lane_to_mainline_group=[0,1])
            p=e.simulate(models['reference'],window(models['reference'],start,command),params)
            assert json.loads(json.dumps(p))==reference;exact+=1
            p=e.simulate(models['candidate'],window(models['candidate'],start,command),params)
            interfaces+=audit(p,reference)['lane_interface_checks'];costs[arm]=parts(p)
            rs=[r for r in p['ramps'] if r['ramp']=='RM_C10681'];lanes=[]
            for g in (0,1):
                local=[r['lane_receipts'][g] for r in rs];a,z=local[0]['start'],local[-1]['end']
                assert abs(a['connector_veh']+sum(r['admitted_arrivals_veh']-r['accepted_merge_veh'] for r in local)+
                    z['cumulative_lane_entry_veh']-z['cumulative_lane_exit_veh']-z['connector_veh'])<1e-7
                lanes.append(dict(arrivals=sum(r['admitted_arrivals_veh'] for r in local),merges=sum(r['accepted_merge_veh'] for r in local),
                    ttt=sum(r['connector_ttt_veh_h'] for r in local),initial_n=a['connector_veh'],end_n=z['connector_veh'],
                    lane_in=z['cumulative_lane_entry_veh'],lane_out=z['cumulative_lane_exit_veh']))
            lane_results[arm]=lanes;e.save(out/f'prediction_s{seed}_{arm}.json',p)
        delta={a:{k:v-costs['none'][k] for k,v in row.items()} for a,row in costs.items() if a!='none'}
        for row in delta.values():row['total']=sum(row.values())
        results[str(seed)]=dict(guards=guards,guards_passed=sum(r['ratio']<=1.1 for r in guards.values()),costs=costs,deltas=delta,lanes=lane_results)
        print(seed,'guards',results[str(seed)]['guards_passed'],'delta',delta,'lanes',lane_results,flush=True)
    for name,pin in pins.items():assert hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,reference_json_exact=exact,lane_interface_checks=interfaces,
        candidate_forecasts=12,state_guard_forecasts=12,production_adopted=False,qualified=False,source_pins_verified=True))


if __name__=='__main__':main()
