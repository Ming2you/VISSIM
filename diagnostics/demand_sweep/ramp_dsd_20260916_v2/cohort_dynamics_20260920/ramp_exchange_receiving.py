"""Isolate the10681 conflict-flow error after lane arrivals and exchanges."""
from pathlib import Path
import sys,json,hashlib,inspect,statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_exchange_identification import observed_profiles
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'ramp_exchange_v1/receiving_identification';out.mkdir(exist_ok=False)
    config=HERE/'ramp_exchange_v1/evaluation/config.json';param=HERE/'port_travel_fit_v1/selected_parameters.json'
    profile=e.load(MODEL/'port_profile.json');params=e.load(param)['parameters'];head=min(e.load(H/'controller_response_v1/heads.json')['10681'].values())
    files=[Path(__file__),config,param,MODEL/'port_profile.json',HERE/'ramp_exchange_identification.py',
        e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.ROOT/'evaluation/controllers/physical_ramp_boundary.py']
    files += [HERE/f'lane_blocking_audit_v1/s{s}_{a}_groups.csv' for s in (23,33) for a in ('none','vsl')]
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,new_native_runs=0,future_inputs=True,
        scope='Previously diagnosed future10681 lane arrivals/exchange plus actual whole-cell9 lane q=n*v/L solely for gap opportunities. No future receiving room, mainline state, accepted merge or discharge forced. No parameter fit.'))
    result={};exact=0
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        model=e.load_base_model(data.geometry,config);original_config=model._config
        def configured(road,p,original=original_config):
            cfg=original(road,p)
            if road=='FW_E':cfg.network.terminal_zero_gradient=True
            return cfg
        model._config=configured;costs={};values={}
        for arm in ('none','vsl'):
            fields=e.load(HERE/f'ramp_lane_inventory_v1/{seed}_{arm}.json')
            rows=e.rows(HERE/f'lane_blocking_audit_v1/s{seed}_{arm}_groups.csv')
            native={(int(r['time_s']),int(r['group'])):r for r in rows if int(r['cell'])==9}
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return {},{d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {}
            w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)],
                'initial_ramp_origin':origin['counts'][str(start)],'initial_off_eligible':origin['eligible_before_off'][str(start)]}}
            with observed_profiles(fields,'future_lane_arrival_and_exchange',head) as counts:
                for step in w['boundary_steps']:
                    t=int(step['window_start_s']);v=[sum(counts[t+i+1,g] for g in (1,2)) for i in range(10)]
                    step['ramp_arrival_vph']['RM_C10681']=sum(v)*360;step.setdefault('ramp_arrival_profile',{})['RM_C10681']=v
                reference=e.load(HERE/f'ramp_exchange_v1/identification/prediction_s{seed}_future_lane_arrival_and_exchange_{arm}.json')
                p=e.simulate(model,w,params);assert json.loads(json.dumps(p))==reference;exact+=1
                prior=PhysicalLaneGroups.ramp_lane_conditions;trace=[]
                def conditions(self,ramp,groups,cfg):
                    result=prior(self,ramp,groups,cfg)
                    if ramp!='RM_C10681':return result
                    frame=inspect.currentframe().f_back
                    assert Path(frame.f_code.co_filename).resolve()==e.CAL/'canonical_harness.py'
                    t=int(frame.f_locals['t']);del frame
                    for r in result:
                        g=r['group'];n=native[t,g];assert self.widths[9][g]==1.
                        q=float(n['n'])*float(n['v'] or 0)/self.lengths[9]
                        trace.append(dict(time_s=t,group=g,predicted_conflict=r['conflicting_vph'],native_conflict=q))
                        r['conflicting_vph']=q
                    return result
                PhysicalLaneGroups.ramp_lane_conditions=conditions
                try:p=e.simulate(model,w,params)
                finally:PhysicalLaneGroups.ramp_lane_conditions=prior
            assert len(trace)==90;audit(p,reference);costs[arm]=parts(p)
            rs=[r for r in p['ramps'] if r['ramp']=='RM_C10681'];lanes=[]
            for g in (0,1):
                lr=[r['lane_receipts'][g] for r in rs];tr=[r for r in trace if r['group']==g]
                lanes.append(dict(ttt=sum(r['connector_ttt_veh_h'] for r in lr),merges=sum(r['accepted_merge_veh'] for r in lr),
                    end_n=lr[-1]['end']['connector_veh'],native_conflict=statistics.mean(r['native_conflict'] for r in tr),
                    predicted_conflict=statistics.mean(r['predicted_conflict'] for r in tr)))
            values[arm]=lanes;e.save(out/f'prediction_s{seed}_{arm}.json',p);e.save(out/f'trace_s{seed}_{arm}.json',trace)
        delta={k:costs['vsl'][k]-costs['none'][k] for k in costs['vsl']};delta['total']=sum(delta.values())
        result[str(seed)]=dict(costs=costs,deltas=delta,lanes=values,port10681_ttt_delta=sum(r['ttt'] for r in values['vsl'])-sum(r['ttt'] for r in values['none']))
        print(seed,result[str(seed)],flush=True)
    for p,pin in pins.items():assert hashlib.sha256((e.ROOT/p).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=result,full_reference_json_exact=exact,forecasts=4,production_adopted=False,qualified=False))


if __name__=='__main__':main()
