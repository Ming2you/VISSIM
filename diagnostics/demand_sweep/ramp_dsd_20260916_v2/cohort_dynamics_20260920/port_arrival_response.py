"""Port residence identities and paired/common future-arrival identification.

Future arrivals are diagnostic exposures only, never deployable predictions.
No head or merge is forced, so actual actuator/receiving/storage rules survive.
"""
from pathlib import Path
import sys,json,hashlib
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.rm_attribution import model_ports

HERE=Path(__file__).resolve().parent
START,END=2400,2850
RAMPS=('10639','10681','10490','10484')


def native(folder):
    table={(int(float(r['window_end_s'])),r['connector']):r for r in e.rows(folder/'ports_30s.csv') if r['road']=='FW_E'}
    connectors=sorted({c for t,c in table});counts=Counter()
    for r in e.rows(folder/'port_events.csv'):
        t=int(float(r['time_s']));c=r['connector']
        if START<t<=END and c in connectors:
            assert float(r['time_s'])==t and r['kind'] in ('arrival','departure'),r
            counts[t,c,r['kind']]+=1
    heads={(int(r['time_s']),r['ramp']):r for r in e.rows(folder/'head_stock_1s.csv')}
    result={};checks=0
    for c in connectors:
        n=initial=int(float(table[START,c]['end_n_veh']));ttt=0.;am=dm=0.;trace=[]
        for t in range(START+1,END+1):
            a,d=counts[t,c,'arrival'],counts[t,c,'departure'];n+=a-d
            assert n>=0
            am+=a*(END+1-t)/3600;dm+=d*(END+1-t)/3600;ttt+=n/3600
            if c in RAMPS:assert n==int(heads[t,c]['prehead_n'])+int(heads[t,c]['posthead_n']);checks+=1
            if t%30==0:
                assert n==float(table[t,c]['end_n_veh']) and float(table[t,c]['unresolved_absences_veh'])==0
                checks+=1;trace.append(dict(time_s=t,n=n,ttt=ttt,arrival_moment=am,departure_moment=dm))
        assert abs(ttt-initial*(END-START)/3600-am+dm)<1e-8
        result[c]=dict(kind=table[END,c]['kind'],initial_n=initial,end_n=n,ttt_veh_h=ttt,
            arrivals=sum(counts[t,c,'arrival'] for t in range(START+1,END+1)),
            departures=sum(counts[t,c,'departure'] for t in range(START+1,END+1)),
            arrival_moment=am,departure_moment=dm,trace=trace)
        if c in RAMPS:
            result[c].update(prehead_ttt=sum(int(heads[t,c]['prehead_n']) for t in range(START+1,END+1))/3600,
                posthead_ttt=sum(int(heads[t,c]['posthead_n']) for t in range(START+1,END+1))/3600)
            assert abs(ttt-result[c]['prehead_ttt']-result[c]['posthead_ttt'])<1e-8
    return result,counts,checks


def difference(arms):
    return {arm:{c:{key:row[key]-arms['none'][c][key] for key in
        ('arrivals','departures','end_n','ttt_veh_h','arrival_moment','departure_moment','prehead_ttt','posthead_ttt') if key in row}
        for c,row in ports.items()} for arm,ports in arms.items() if arm!='none'}


def main():
    out=HERE/'port_arrival_response_v1';out.mkdir(exist_ok=False)
    config=HERE/'port_origin_split_v1/config.json';param=HERE/'port_travel_fit_v1/selected_parameters.json'
    profile=e.load(MODEL/'port_profile.json');params=e.load(param)['parameters']
    files=[Path(__file__),config,param,MODEL/'port_profile.json',HERE/'rm_attribution.py',
        e.CAL/'canonical_harness.py',H/'evaluate_response.py',
        e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    results={};checks=exact=0
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        assert start==START
        native_arms={};events={}
        for arm in ARMS:
            f=folder if arm=='none' else bank/'observations'/arm
            native_arms[arm],events[arm],n=native(f);checks+=n
            for name in ['port_events.csv','ports_30s.csv','head_stock_1s.csv']:
                p=f/name;pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
            for c,row in native_arms[arm].items():assert row['initial_n']==native_arms['none'][c]['initial_n']
        delta=difference(native_arms)
        print('NATIVE',seed,{a:{c:{key:round(row[key],6) for key in ['arrival_moment','departure_moment','ttt_veh_h','prehead_ttt','posthead_ttt']}
            for c,row in ports.items() if c in RAMPS} for a,ports in delta.items()},flush=True)
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        model=e.load_base_model(data.geometry,config);original=model._config
        def configured(road,p):
            cfg=original(road,p)
            if road=='FW_E':cfg.network.terminal_zero_gradient=True
            return cfg
        model._config=configured
        modes={}
        for mode in ['history','common_nc_future','paired_future']:
            costs={};ports={};exposures={}
            for arm in ARMS:
                seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
                def command(t):
                    i=int((t-START)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {})
                w=e.window(data,model,START,'history_forecast',profile,command,port_origin_counts=origin['counts'])
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(START)],
                    'initial_ramp_origin':origin['counts'][str(START)],'initial_off_eligible':origin['eligible_before_off'][str(START)]}}
                if mode!='history':
                    sample=events[arm if mode=='paired_future' else 'none']
                    for step in w['boundary_steps']:
                        step.setdefault('ramp_arrival_profile',{})
                        for c in RAMPS:
                            arrival=[sample[t,c,'arrival'] for t in range(int(step['window_start_s'])+1,int(step['window_end_s'])+1)]
                            step['ramp_arrival_profile']['RM_C'+c]=arrival
                            step['ramp_arrival_vph']['RM_C'+c]=sum(arrival)*360
                pred=e.simulate(model,w,params)
                reference=e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
                if mode=='history':assert json.loads(json.dumps(pred))==reference;exact+=1
                for key in ['cells','flows']:
                    assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
                for r in pred['diagnostics']['roads']:
                    assert r['continuity_residual_max_veh']<1e-7 and r['negative_density_count']==r['jam_density_exceedance_count']==0
                for r in pred['ports']+pred['ramps']:assert abs(r['conservation_residual_veh'])<1e-7
                ports[arm]=model_ports(pred);costs[arm]=parts(pred)
                exposures[arm]={c:dict(requested=sum(r['requested_arrivals_veh'] for r in pred['ramps'] if r['ramp']=='RM_C'+c),
                    admitted=ports[arm][c]['arrivals']) for c in RAMPS}
                if mode!='history':
                    refarm=arm if mode=='paired_future' else 'none'
                    for c in RAMPS:assert abs(exposures[arm][c]['requested']-native_arms[refarm][c]['arrivals'])<1e-8
                e.save(out/f'prediction_s{seed}_{mode}_{arm}.json',pred)
            cost_delta={a:{key:v-costs['none'][key] for key,v in row.items()} for a,row in costs.items() if a!='none'}
            for row in cost_delta.values():row['total']=sum(row.values())
            modes[mode]=dict(costs=costs,port_values=ports,port_deltas=difference(ports),deltas=cost_delta,exposures=exposures)
            print('MODEL',seed,mode,cost_delta,flush=True)
        results[str(seed)]=dict(native=native_arms,native_deltas=delta,modes=modes)
    for f,pin in pins.items():assert hashlib.sha256((e.ROOT/f).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,pins=pins,native_stock_checks=checks,history_json_exact=exact,
        new_native_runs=0,production_adopted=False,qualified=False,
        native_scope='End-frame1s connector residence; arrival/departure moments use END+1-t exactly. Accounting contributions are not independent causal effects.',
        model_scope='Original lane-group/open-outlet candidate. Future connector entry counts are diagnostic requests, finite admission and actual modeled head/merge remain; any rejected request is reported.',
        prediction_scope='Common NC future isolates control response under one incoming profile; paired future also includes actual arm-specific arrival changes. Neither is an online prediction.'))


if __name__=='__main__':main()
