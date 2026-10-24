"""Diagnostic future10681 arrivals/exchange fractions, without state resets."""
from pathlib import Path
import sys,json,hashlib,math
from collections import Counter
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary

HERE=Path(__file__).resolve().parent


@contextmanager
def observed_profiles(fields,mode,head):
    arrivals=Counter((r['time_s'],r['lane']) for r in fields['events'] if r['kind']=='arrival')
    changes=Counter((r['time_s']-1,'prehead' if r['from_position_m']<head else 'posthead',r['from_lane']-1,r['to_lane']-1)
        for r in fields['exchanges'])
    states={r['time_s']:r['lanes'] for r in fields['rows']}
    advance=LaneResolvedRampBoundary.advance_local_interval;exchange=LaneResolvedRampBoundary._exchange_lanes
    def lane_arrivals(self,**kwargs):
        if self.connector_id=='10681' and mode!='causal':
            t=int(kwargs['start_sec']);seconds=int(kwargs['duration_sec'])
            kwargs['request_arrivals_by_lane_second']=[[arrivals[t+i+1,g] for i in range(seconds)] for g in (1,2)]
        return advance(self,**kwargs)
    def lane_exchange(self):
        if self.connector_id!='10681' or mode!='future_lane_arrival_and_exchange':return exchange(self)
        t=int(self._lane_buffers[0].time_sec);rates={}
        for stage in ('prehead','posthead'):
            matrix=[]
            for i in (0,1):
                n=states[t][i]['prehead'] if stage=='prehead' else states[t][i]['n']-states[t][i]['prehead']
                row=[]
                for j in (0,1):
                    q=changes[t,stage,i,j]
                    assert q<=n
                    f=q/n if n else 0.
                    # Exact probability1 is represented to machine precision,
                    # not by an arbitrary physical maximum transition rate.
                    row.append(-math.log1p(-min(f,1.-sys.float_info.epsilon)))
                matrix.append(row)
            rates[stage]=matrix
        old=self.lane_exchange_rates;self.lane_exchange_rates=rates
        try:return exchange(self)
        finally:self.lane_exchange_rates=old
    LaneResolvedRampBoundary.advance_local_interval=lane_arrivals;LaneResolvedRampBoundary._exchange_lanes=lane_exchange
    try:yield arrivals
    finally:
        LaneResolvedRampBoundary.advance_local_interval=advance;LaneResolvedRampBoundary._exchange_lanes=exchange


def main():
    out=HERE/'ramp_exchange_v1/identification';out.mkdir(exist_ok=False)
    config=HERE/'ramp_exchange_v1/evaluation/config.json';param=HERE/'port_travel_fit_v1/selected_parameters.json'
    profile=e.load(MODEL/'port_profile.json');params=e.load(param)['parameters']
    head=min(e.load(H/'controller_response_v1/heads.json')['10681'].values())
    files=[Path(__file__),config,param,MODEL/'port_profile.json',e.CAL/'canonical_harness.py',
        e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',
        H/'evaluate_response.py']+[HERE/f'ramp_lane_inventory_v1/{s}_{a}.json' for s in (23,33) for a in ('none','vsl')]
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,new_native_runs=0,fit_evaluations=0,
        scope='Only10681 future lane-specific entries, then also actual1s stage exchange fractions applied to predicted donor stocks and finite target room. Other ports and source use history. No future stock or merge resets, no gain fit.',
        modes=['causal','future_lane_arrival','future_lane_arrival_and_exchange']))
    result={};exact=0
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        model=e.load_base_model(data.geometry,config);original=model._config
        def configured(road,p,original=original):
            cfg=original(road,p)
            if road=='FW_E':cfg.network.terminal_zero_gradient=True
            return cfg
        model._config=configured;results={}
        for mode in ('causal','future_lane_arrival','future_lane_arrival_and_exchange'):
            costs={};port_values={}
            for arm in ('none','vsl'):
                fields=e.load(HERE/f'ramp_lane_inventory_v1/{seed}_{arm}.json')
                seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
                def command(t):
                    i=int((t-start)//150)
                    return {},{d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {}
                w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origin['counts'])
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)],
                    'initial_ramp_origin':origin['counts'][str(start)],'initial_off_eligible':origin['eligible_before_off'][str(start)]}}
                with observed_profiles(fields,mode,head) as counts:
                    if mode!='causal':
                        for step in w['boundary_steps']:
                            t=int(step['window_start_s']);v=[sum(counts[t+i+1,g] for g in (1,2)) for i in range(10)]
                            step['ramp_arrival_vph']['RM_C10681']=sum(v)*360
                            step.setdefault('ramp_arrival_profile',{})['RM_C10681']=v
                    pred=e.simulate(model,w,params)
                reference=e.load(HERE/f'ramp_exchange_v1/evaluation/prediction_s{seed}_{arm}.json')
                if mode=='causal':assert json.loads(json.dumps(pred))==reference;exact+=1
                audit(pred,reference);costs[arm]=parts(pred)
                rows=[r for r in pred['ramps'] if r['ramp']=='RM_C10681'];lanes=[]
                for g in (0,1):
                    rs=[r['lane_receipts'][g] for r in rows];end=rs[-1]['end']
                    lanes.append(dict(arrivals=sum(r['admitted_arrivals_veh'] for r in rs),
                        requested=sum(r['requested_arrivals_veh'] for r in rs),departures=sum(r['accepted_merge_veh'] for r in rs),
                        ttt=sum(r['connector_ttt_veh_h'] for r in rs),end_n=end['connector_veh'],
                        lane_in=end['cumulative_lane_entry_veh'],lane_out=end['cumulative_lane_exit_veh']))
                    if mode!='causal':assert lanes[-1]['requested']==sum(counts[t,g+1] for t in range(2401,2851))
                port_values[arm]=lanes;e.save(out/f'prediction_s{seed}_{mode}_{arm}.json',pred)
            delta={k:costs['vsl'][k]-costs['none'][k] for k in costs['vsl']};delta['total']=sum(delta.values())
            results[mode]=dict(costs=costs,delta=delta,lanes=port_values,
                port10681_ttt_delta=sum(r['ttt'] for r in port_values['vsl'])-sum(r['ttt'] for r in port_values['none']))
            print(seed,mode,results[mode],flush=True)
        result[str(seed)]=results
    for p,pin in pins.items():assert hashlib.sha256((e.ROOT/p).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=result,causal_json_exact=exact,forecasts=12,production_adopted=False,qualified=False,source_pins_verified=True))


if __name__=='__main__':main()
