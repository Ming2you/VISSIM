"""Causal lane drainage timing at unchanged past-cycle mean service.

Tests whether averaging all150s erases the off-ramp blocking/recovery sequence.
The empirical service schedule is an identified boundary, not a saturation
capacity or a full urban model. Its samples stop at the prediction cutoff.
"""
from pathlib import Path
import sys,copy,hashlib,json,math
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_spatial_supply import ReceivingEnvelope
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_receiving_probe import dataset
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
import canonical_harness as ch

HERE=Path(__file__).resolve().parent


def phase_service(events,cutoff,cycle=150,step=10):
    assert cutoff%cycle==0 and cycle%step==0
    counts=Counter()
    for r in events:
        t=float(r['time_s'])
        if r['connector']=='10643' and r['kind']=='departure' and cutoff-cycle<t<=cutoff:
            assert t==int(t)
            counts[(int(t)-1)%cycle//step,int(r['lane'])]+=1
    return [[counts[b,l]*3600/step for l in (1,2)] for b in range(cycle//step)]


def main():
    out=HERE/'phase_drainage_v1';out.mkdir(exist_ok=False)
    config=HERE/'urban_boundary_rollout_lanes_v1/lane_config.json'
    param=HERE/'port_travel_fit_v1/selected_parameters.json';params=e.load(param)['parameters']
    profile=e.load(MODEL/'port_profile.json');wave=e.load(HERE/'off_spatial_supply_v1/result.json')['wave_m_s']
    files=[Path(__file__),config,param,MODEL/'port_profile.json',HERE/'off_spatial_supply.py',
           e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    results={};exact=0;truncations=0
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origins=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        _urban,program,_offset=dataset(HERE/f'urban_drain_observations_v5/s{seed}_none.csv',HERE/f'urban_drain_observations_v5/s{seed}_none_evidence.json')
        assert program.cycle_length_sec==150
        del _urban
        events=e.rows(folder/'port_events.csv');past=[r for r in events if float(r['time_s'])<=start]
        service=phase_service(past,start)
        assert service==phase_service(events,start);truncations+=1
        del events
        model=e.load_base_model(data.geometry,config);original_config=model._config
        def configured(road,p):
            c=original_config(road,p)
            if road=='FW_E':c.network.terminal_zero_gradient=True
            return c
        model._config=configured;results[str(seed)]={}
        modes=['history','phase']+(['wave_history','wave_phase'] if seed==23 else [])
        e.save(out/f's{seed}_causal_boundary.json',dict(cutoff_s=start,source_cycle_s=[start-150,start],services_vph=service,
            unchanged_cycle_mean_vph=[sum(q[l] for q in service)/len(service) for l in (0,1)],signal_cycle_s=150,
            wave_supported=seed==23,reason='Finite-wave envelope currently requires zero lateral exchange; seed33 retains observed nonzero lane exchange in point stores.'))
        for mode in modes:
            arms={};audits={}
            for arm in ARMS:
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {})
                w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origins['counts'])
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)],
                    'initial_ramp_origin':origins['counts'][str(start)],'initial_off_eligible':origins['eligible_before_off'][str(start)]}}
                base=w['boundary_steps'][0]['off_lane_drain_vph']['10643']
                assert all(abs(base[l]-sum(q[l] for q in service)/len(service))<1e-9 for l in (0,1))
                if 'phase' in mode:
                    for row in w['boundary_steps']:
                        q=service[int(row['window_start_s'])%150//10]
                        row['off_lane_drain_vph']['10643']=list(q);row['off_drain_vph']['10643']=sum(q)
                init=ch.LaneResolvedDelayedPort.__init__;release=ch.DelayedPort.release;advance=PhysicalLaneGroups.advance
                tracked=[];offers=[]
                def initialize(self,capacity,length,speed,cohorts,t,rates):
                    init(self,capacity,length,speed,cohorts,t,rates)
                    if mode.startswith('wave'):
                        assert all(x==0 for row in rates for x in row),'Do not erase observed lateral exchange'
                        for l,p in enumerate(self.lanes,1):
                            p._envelope=ReceivingEnvelope(length,length/p.capacity,speed/3.6,wave,[x for x,v,g in cohorts if g==l])
                            p._departures=[0.];tracked.append(p)
                def drain(self,t,dt,q):
                    if self in tracked:
                        assert dt==1 and q/3600<=self._envelope.qmax+1e-8
                    amount=release(self,t,dt,q)
                    if self in tracked:self._departures.append(self.departed)
                    return amount
                def step(self,state,control,demand,cfg,**kw):
                    if mode.startswith('wave') and self.road=='FW_E':
                        assert len(tracked)==2
                        elapsed=int(state.time_sec-start);duration=int(self.sec)
                        amounts=[p._envelope.offer(elapsed+duration,duration,p.admitted,p._departures[:elapsed+1]) for p in tracked]
                        old=kw['offramp_group_capacity_veh_h']['10643']
                        new=[min(q,n*3600/duration) for q,n in zip(old[:2],amounts)]+[0.]
                        kw['offramp_group_capacity_veh_h']['10643']=new
                        kw['offramp_capacity_veh_h']['10643']=min(kw['offramp_capacity_veh_h']['10643'],sum(new))
                        offers.append(dict(time_s=state.time_sec,offer_vph=new,stock=[p.stock for p in tracked]))
                    return advance(self,state,control,demand,cfg,**kw)
                if mode.startswith('wave'):
                    ch.LaneResolvedDelayedPort.__init__=initialize;ch.DelayedPort.release=drain;PhysicalLaneGroups.advance=step
                try:pred=e.simulate(model,w,params)
                finally:
                    ch.LaneResolvedDelayedPort.__init__=init;ch.DelayedPort.release=release;PhysicalLaneGroups.advance=advance
                if mode=='history':
                    again=e.simulate(model,w,params)
                    assert json.loads(json.dumps(again))==json.loads(json.dumps(pred));exact+=1
                else:
                    reference=e.load(out/f'prediction_{seed}_history_{arm}.json')
                    for key in ['cells','flows']:
                        assert [x for x in pred[key] if x['road']=='FW_W']==[x for x in reference[key] if x['road']=='FW_W']
                for r in pred['diagnostics']['roads']:
                    assert r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==r['jam_density_exceedance_count']==0
                for r in pred['ports']:assert abs(r['conservation_residual_veh'])<1e-7
                arms[arm]=parts(pred);audits[arm]=dict(offers=offers,score=e.score_rollout(data,start,pred,'FW_E') if arm=='none' else None)
                e.save(out/f'prediction_{seed}_{mode}_{arm}.json',pred)
            deltas={arm:{k:v-arms['none'][k] for k,v in row.items()} for arm,row in arms.items() if arm!='none'}
            for row in deltas.values():row['total']=sum(row.values())
            results[str(seed)][mode]=dict(arms=arms,deltas=deltas,audits=audits)
            print(seed,mode,deltas,flush=True)
    for f,pin in pins.items():assert hashlib.sha256((e.ROOT/f).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,pins=pins,full_reference_repeat_exact=exact,phase_future_truncation_checks=truncations,
        future_inputs=False,qualified=False,production_adopted=False,new_native_runs=0,
        scope='Same450s conserved component model, service timing changes at unchanged past150s mean. Phase repetition does not predict evolving urban state or prove saturation service; wave mode limited to causal zero-exchange seed23.'))


if __name__=='__main__':main()
