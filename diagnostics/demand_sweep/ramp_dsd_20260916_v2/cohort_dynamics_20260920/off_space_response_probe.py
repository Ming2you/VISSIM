"""Bounded causal receiving test on seed23's zero-exchange initial profile.

Uses only current measured lengths/positions, NC13 wave measurement and model
predicted drainage. Future composition is frozen at its current lane mean;
this approximation and lack of lateral-wave support prevent promotion here.
No production source/default changes and no benefit-fitted parameter.
"""
from pathlib import Path
import sys
import json
import copy
import hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_spatial_supply import ReceivingEnvelope
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
import canonical_harness as ch

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'off_space_response_v1';out.mkdir(exist_ok=False)
    recording=e.load(HERE/'vehicle_lengths_native_v1/analysis/frames.json')
    cutoff=2400
    # Discard all future frames BEFORE constructing physical observations.
    current=next(r['vehicles'] for r in recording['frames'] if r['time_s']==cutoff)
    del recording
    wave=e.load(HERE/'off_spatial_supply_v1/result.json')['wave_m_s']
    seed,folder,bank,start=CASES[1];assert seed==23 and start==cutoff
    config=HERE/'urban_boundary_rollout_lanes_v1/lane_config.json'
    params_file=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(params_file)['parameters'];profile=e.load(MODEL/'port_profile.json')
    data=e.ObservationData(folder);model=e.load_base_model(data.geometry,config);protocol=e.load(bank/'protocol.json')
    lanes=e.load(H/'lane_group_response_20260919/observations_v1/s23.json')
    origins=e.load(HERE/'port_positions_v1/s23.json')
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),HERE/'off_spatial_supply.py',config,params_file,e.CAL/'canonical_harness.py',
         H/'evaluate_response.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py']}
    result={};audits={}
    for mode in ('reference','current_lengths','wave_only','current_lengths_wave'):
        result[mode]={};audits[mode]={}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
            def commands(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            window=e.window(data,model,start,'history_forecast',profile,commands,port_origin_counts=origins['counts'])
            window['lane_group_dynamics']={'FW_E':{**lanes['geometry'],**lanes['cutoffs'][str(start)],
                'initial_ramp_origin':origins['counts'][str(start)],
                'initial_off_eligible':origins['eligible_before_off'][str(start)]}}
            for step in window['boundary_steps']:step['off_split_ratio']['10643']=1/6
            original_init=ch.LaneResolvedDelayedPort.__init__
            original_release=ch.DelayedPort.release
            original_advance=PhysicalLaneGroups.advance
            tracked=[];offers=[]
            def initialize(self,capacity,length_m,speed,cohorts,start_s,rates):
                original_init(self,capacity,length_m,speed,cohorts,start_s,rates)
                if 'wave' in mode:assert all(x==0 for row in rates for x in row),'Lateral sources need a separate wave law'
                assert start_s==start and not tracked
                assert sorted(cohorts)==sorted([p,v,l] for vid,l,p,v,size,kind in current)
                for lane,p in enumerate(self.lanes,1):
                    observed=[row for row in current if row[1]==lane]
                    spacing=length_m/p.capacity
                    if 'current_lengths' in mode:
                        spacing=sum(row[4] for row in observed)/len(observed)+1.5
                        p.capacity=length_m/spacing
                        assert p.stock<=p.capacity+1e-8
                    p._receiving_envelope=ReceivingEnvelope(length_m,spacing,speed/3.6,wave,[row[2] for row in observed])
                    p._departure_history=[0.];tracked.append(p)
                self.capacity=sum(p.capacity for p in self.lanes)
            def release(self,t,dt,q):
                if self in tracked and 'wave' in mode:
                    assert dt==1 and q/3600<=self._receiving_envelope.qmax+1e-8
                value=original_release(self,t,dt,q)
                if self in tracked:
                    assert dt==1
                    self._departure_history.append(self.departed)
                return value
            def advance(self,state,control,demand,cfg,**kw):
                if self.road=='FW_E' and 'wave' in mode:
                    assert len(tracked)==2
                    elapsed=int(state.time_sec-start);dt=int(self.sec)
                    amounts=[p._receiving_envelope.offer(elapsed+dt,dt,p.admitted,p._departure_history[:elapsed+1]) for p in tracked]
                    kw=copy.deepcopy(kw)
                    old=kw['offramp_group_capacity_veh_h']['10643']
                    new=[min(q,n*3600/dt) for q,n in zip(old[:2],amounts)]+[0.]
                    kw['offramp_group_capacity_veh_h']['10643']=new
                    kw['offramp_capacity_veh_h']['10643']=min(kw['offramp_capacity_veh_h']['10643'],sum(new))
                    offers.append({'time_s':state.time_sec,'old_vph':old,'new_vph':new,
                        'stock':[p.stock for p in tracked],'admitted':[p.admitted for p in tracked]})
                return original_advance(self,state,control,demand,cfg,**kw)
            if mode!='reference':
                ch.LaneResolvedDelayedPort.__init__=initialize
                ch.DelayedPort.release=release
                PhysicalLaneGroups.advance=advance
            try:pred=e.simulate(model,window,params)
            finally:
                ch.LaneResolvedDelayedPort.__init__=original_init
                ch.DelayedPort.release=original_release
                PhysicalLaneGroups.advance=original_advance
            old=e.load(HERE/f'configured_exit_ratio_v1/prediction_23_configured_ratio_lanes_{arm}.json')
            if mode=='reference':assert json.loads(json.dumps(pred))==old
            for key in ('cells','flows'):
                assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in old[key] if r['road']=='FW_W']
            for row in pred['ports']:assert abs(row['conservation_residual_veh'])<1e-7
            result[mode][arm]=parts(pred)
            audits[mode][arm]={'offers':offers,'lane_capacity':[p.capacity for p in tracked],
                'initial_projection_max_m':[p._receiving_envelope.projection_max_m for p in tracked],
                'nc_state_score':e.score_rollout(data,start,pred,'FW_E') if arm=='none' else None}
            e.save(out/f'prediction_{mode}_{arm}.json',pred)
        result[mode]['deltas']={a:{k:v-result[mode]['none'][k] for k,v in result[mode][a].items()} for a in ARMS[1:]}
        for d in result[mode]['deltas'].values():d['total']=sum(d.values())
        print(mode,{a:round(d['total'],6) for a,d in result[mode]['deltas'].items()},flush=True)
    for path,pin in pins.items():assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',{'results':result,'audits':audits,'pins':pins,'wave_m_s':wave,
        'future_native_inputs':False,'length_observation_s':start,'new_native_runs':0,'promoted':False,
        'limits':'One seed/state, frozen current lane composition, currently zero causal off-lane exchange only. Development diagnostic, not independent qualification.'})


if __name__=='__main__':main()
