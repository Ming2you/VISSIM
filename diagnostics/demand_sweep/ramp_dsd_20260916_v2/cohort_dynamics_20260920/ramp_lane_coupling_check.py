"""Bounded no-fit qualification of connector-lane to mainline-lane coupling."""
from pathlib import Path
import sys,json,hashlib
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.rm_attribution import model_ports

HERE=Path(__file__).resolve().parent


def audit(pred,reference,*,same_time_step=True):
    for key in ['cells','flows']:
        if same_time_step:
            assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
    for r in pred['diagnostics']['roads']:
        assert r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==r['jam_density_exceedance_count']==0
    for r in pred['ports']+pred['ramps']:assert abs(r['conservation_residual_veh'])<1e-7
    groups={(r['time_s'],r['cell'],r['group']):r for r in pred['lane_groups']['FW_E']}
    totals=[0.,0.];checks=0
    for receipt in pred['ramps']:
        if receipt['ramp']!='RM_C10681':continue
        assert receipt['receiving_node']['physical_lane_coupling']
        accepted=[r['accepted_merge_veh'] for r in receipt['lane_receipts']]
        applied=receipt['applied_group_merge_vph'];dt=receipt['duration_sec']/3600
        for g,x in enumerate(accepted):
            assert abs(applied[g]*dt-x)<1e-8
            assert abs(groups[receipt['end_sec'],9,g]['merge_in_veh']-x)<1e-8
            totals[g]+=x;checks+=1
        assert applied[2]==0 and abs(sum(accepted)-receipt['accepted_merge_veh'])<1e-8
        for r in receipt['lane_receipts']:assert abs(r['conservation_residual_veh'])<1e-7
    step=pred['ramps'][0]['duration_sec']
    assert all(r['duration_sec']==step for r in pred['ramps'])
    assert checks==2*450/step
    return dict(lane_interface_checks=checks,accepted_merges_by_lane=totals)


def main():
    out=HERE/'ramp_lane_coupling_v1/evaluation';out.mkdir(exist_ok=False)
    base=HERE/'port_origin_split_v1/config.json';config=out/'config.json'
    tuning=e.load(base);tuning['freeway']['physical_ramp_lane_coupling']={'RM_C10681':[0,1]}
    e.save(config,tuning)
    param=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(param)['parameters'];profile=e.load(MODEL/'port_profile.json')
    files=[Path(__file__),base,config,param,MODEL/'port_profile.json',H/'evaluate_response.py',
        e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',
        e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
        HERE/'ramp_lane_coupling_v1/geometry_mapping.json',HERE/'ramp_lane_coupling_v1/tests.json']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,new_native_runs=0,fit_evaluations=0,future_inputs=False,
        scope='Only explicit10681 ramp-lane to mainline-group coupling. Gap law and calibrated coefficients unchanged. Open physical downstream boundary retained from reference.',
        state_guard='All12 NC objectives <=1.10 established internal_cost. Seeds are inspected development data, not held-out.',
        acceptance='Conservation and exact disabled JSON required but insufficient; also inspect component gain signs, magnitudes, costs and state guard. No production adoption by this script.'))
    established=e.load(HERE/'open_speed_fit_v2/results.json')['baseline_state_scores']
    results={};exact=checks=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        models={}
        for name,path in [('reference',base),('candidate',config)]:
            model=e.load_base_model(data.geometry,path);original=model._config
            def configured(road,p,original=original):
                cfg=original(road,p)
                if road=='FW_E':cfg.network.terminal_zero_gradient=True
                return cfg
            model._config=configured;models[name]=model
        def window(model,t,command):
            w=e.window(data,model,t,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)],
                'initial_ramp_origin':origin['counts'][str(t)],'initial_off_eligible':origin['eligible_before_off'][str(t)]}}
            return w
        guards={}
        for t in [900,1650,2400,3600]:
            p=e.simulate(models['candidate'],window(models['candidate'],t,lambda _: ({},{})),params)
            score=e.score_rollout(data,t,p,'FW_E');assert not score['invalid']
            guards[str(t)]=dict(score=score,ratio=score['objective']/established[str(seed)][str(t)]['objective'])
        costs={};ports={};audits={};native={}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            reference=e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
            r=e.simulate(models['reference'],window(models['reference'],start,command),params)
            assert json.loads(json.dumps(r))==reference;exact+=1
            p=e.simulate(models['candidate'],window(models['candidate'],start,command),params)
            audits[arm]=audit(p,reference);checks+=audits[arm]['lane_interface_checks']
            costs[arm]=parts(p);ports[arm]=model_ports(p)
            folder_arm=folder if arm=='none' else bank/'observations'/arm
            events=Counter((r['kind'],int(r['lane'])) for r in e.rows(folder_arm/'port_events.csv')
                if r['connector']=='10681' and start<float(r['time_s'])<=start+450)
            native[arm]={kind:[events[kind,g] for g in (1,2)] for kind in ('arrival','departure')}
            e.save(out/f'prediction_s{seed}_{arm}.json',p)
        delta={a:{key:v-costs['none'][key] for key,v in row.items()} for a,row in costs.items() if a!='none'}
        for row in delta.values():row['total']=sum(row.values())
        results[str(seed)]=dict(guards=guards,guards_passed=sum(r['ratio']<=1.1 for r in guards.values()),
            costs=costs,deltas=delta,ports=ports,interface=audits,native10681=native)
        print(seed,'guards',results[str(seed)]['guards_passed'],'delta',delta,flush=True)
        print(seed,'lane merges',{a:r['accepted_merges_by_lane'] for a,r in audits.items()},'native',native,flush=True)
    for f,pin in pins.items():assert hashlib.sha256((e.ROOT/f).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,reference_json_exact=exact,lane_interface_checks=checks,
        candidate_forecasts=12,state_guard_forecasts=12,source_pins_verified=True,qualified=False,production_adopted=False))


if __name__=='__main__':main()
