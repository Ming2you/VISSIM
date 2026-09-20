"""Causal initial off-ramp queue-wave gate in the existing component harness.

This covers only the queue already observed at the cutoff. It is NOT a complete
closure-onset model. Keep a front-position storage allowance, not zero flow.
"""
from pathlib import Path
import sys,json,hashlib,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_queue_release import predict
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'off_initial_wave_response_v1';out.mkdir(exist_ok=False)
    config=HERE/'merge10681_conflict_v1/evaluation/through_only.json'
    params=e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    lag=e.load(HERE/'off_queue_release_v1/result.json')['pair_lag_s']
    established=e.load(HERE/'open_speed_fit_v2/results.json')['baseline_state_scores']
    files=[Path(__file__),HERE/'off_queue_release.py',HERE/'off_queue_release_v1/result.json',config,
        e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.CAL/'canonical_harness.py']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,no_gain_fitting=True,new_native_runs=0,
        input='Only cutoff10643 lane positions/speeds. Delay=number of stopped vehicles to CURRENT moving front times frozen2s pair lag.',
        allowance='Entrance front position / existing nominal jam spacing; subtract actual accepted entries until startup wave reaches entrance.',
        scope='Diagnostic-only initial queue recovery; no subsequent new blockage inferred. Full450s qualification must not be claimed from startup alone.'))
    results={};exact=interfaces=0;advance=PhysicalLaneGroups.advance
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        model=e.load_base_model(data.geometry,config);prior=model._config
        def configured(road,p):
            cfg=prior(road,p)
            if road=='FW_E':cfg.network.terminal_zero_gradient=True
            return cfg
        model._config=configured;port=model.offramps['10643']
        spacing=port['length_m']*port['lanes']/port['storage_capacity_veh']
        def run(t0,command,active):
            vehicles=[[i,int(l),float(p),float(v)] for i,(p,v,l) in enumerate(data.port_cohorts[str(t0)]['10643'])]
            states=[predict(vehicles,l,lag) for l in (1,2)]
            gates={g:dict(until=t0+r['predicted_restart_delay_s'],allowance=r['entry_pos']/spacing,used=0.)
                   for g,r in enumerate(states) if r and r['status']=='moving_front_observed'}
            trace=[]
            def gated(self,state,control,demand,cfg,**kwargs):
                binding=[]
                if active and self.road=='FW_E':
                    limits=copy.deepcopy(kwargs.get('offramp_group_capacity_veh_h') or {})
                    cap=limits.get('10643',[kwargs['offramp_capacity_veh_h']['10643']]*len(self.n[8]))
                    for g,item in gates.items():
                        closed=min(self.sec,max(0.,item['until']-state.time_sec))
                        if closed<=0:continue
                        left=max(0.,item['allowance']-item['used'])
                        old=cap[g];cap[g]=min(old,left/self.dt+old*(1-closed/self.sec))
                        binding.append(dict(group=g,closed_seconds=closed,prefix_remaining_veh=left,old_vph=old,new_vph=cap[g]))
                    if binding:
                        limits['10643']=cap;kwargs['offramp_group_capacity_veh_h']=limits
                result=advance(self,state,control,demand,cfg,**kwargs)
                if active and self.road=='FW_E':
                    for g,item in gates.items():item['used']+=self.last_off_sent['10643'][g]
                    if binding:trace.append(dict(time_s=state.time_sec,limits=binding,actual_sent=list(self.last_off_sent['10643'])))
                return result
            w=e.window(data,model,t0,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t0)],
                'initial_ramp_origin':origin['counts'][str(t0)],'initial_off_eligible':origin['eligible_before_off'][str(t0)]}}
            try:
                PhysicalLaneGroups.advance=gated
                p=e.simulate(model,w,params)
            finally:PhysicalLaneGroups.advance=advance
            return p,dict(current_states=states,nominal_spacing_m=spacing,trace=trace)
        guards={};costs={};receipts={}
        for t in (900,1650,2400,3600):
            p,receipt=run(t,lambda _: ({},{}),True);score=e.score_rollout(data,t,p,'FW_E')
            assert not score['invalid']
            guards[str(t)]=dict(score=score,ratio=score['objective']/established[str(seed)][str(t)]['objective'],receipt=receipt)
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            baseline=e.load(HERE/f'merge10681_conflict_v1/evaluation/prediction_s{seed}_through_only_{arm}.json')
            plain,_=run(start,command,False);assert json.loads(json.dumps(plain))==baseline;exact+=1
            p,receipt=run(start,command,True);interfaces+=audit(p,baseline)['lane_interface_checks']
            costs[arm]=parts(p);receipts[arm]=receipt;e.save(out/f'prediction_s{seed}_{arm}.json',p)
        delta={a:{k:v-costs['none'][k] for k,v in row.items()} for a,row in costs.items() if a!='none'}
        for d in delta.values():d['total']=sum(d.values())
        results[str(seed)]=dict(guards=guards,guards_passed=sum(r['ratio']<=1.1 for r in guards.values()),costs=costs,deltas=delta,receipts=receipts)
        print(seed,'guards',results[str(seed)]['guards_passed'],'deltas',delta,flush=True)
    for file,pin in pins.items():assert hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,disabled_json_exact=exact,lane_interface_checks=interfaces,
        source_pins_verified=True,production_adopted=False,qualified=False,new_native_runs=0))


if __name__=='__main__':main()
