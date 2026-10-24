"""Can conserved stocks/flows explain gain if every future group speed is known?

Diagnostic oracle only. Never a candidate/controller result. Separates the
velocity law from the uniform-within-cell flux approximation and boundaries.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.interruption_oracle import moments
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
from src.models import metanet as mn
from contextlib import contextmanager
import argparse
from collections import Counter

HERE=Path(__file__).resolve().parent;LANE=H/'lane_group_response_20260919'


def observed_external(w, data, model, channels):
    """One-channel oracle, never an online boundary forecast or a state reset."""
    counts=Counter((int(float(r['time_s'])),str(r['connector']),r['kind'],int(r['lane']))
                   for r in e.rows(data.folder/'port_events.csv'))
    for step in w['boundary_steps']:
        a,b=step['window_start_s'],step['window_end_s'];end=(a//30+1)*30
        if 'source' in channels:
            for name,spec in data.definitions.items():
                if spec['kind']=='source':
                    step['source_demand_vph'][spec['road']]=float(data.boundaries[end,name]['crossings'])*120.
        if 'arrival' in channels:
            for ramp,spec in model.ramps.items():
                connector=str(spec['connector'])
                profile=[sum(counts[t,connector,'arrival',lane] for lane in range(1,spec['lanes']+1))
                         for t in range(a+1,b+1)]
                step['ramp_arrival_vph'][ramp]=sum(profile)*3600/(b-a)
                if ramp in step.get('ramp_arrival_profile',{}):step['ramp_arrival_profile'][ramp]=profile
        if 'drain' in channels:
            for off,spec in model.offramps.items():
                if off in model.offramp_lanes:
                    service=[sum(counts[t,off,'departure',lane] for t in range(end-29,end+1))*120.
                             for lane in (1,2)]
                    step['off_lane_drain_vph'][off]=service;step['off_drain_vph'][off]=sum(service)
                else:step['off_drain_vph'][off]=float(data.ports[end,off]['departures_veh'])*120.
        if 'direct_upper' in channels:
            for off in ['10483','10682']:
                # Diagnostic upper service: can drain an entire physical port
                # in0.001s. This is not a calibrated operational capacity.
                step['off_drain_vph'][off]=model.offramps[off]['storage_capacity_veh']*3600/.001
    w['meta']['diagnostic_future_external_channels']=list(channels)


@contextmanager
def speeds(seed,arm,selected,observation_dir=None):
    data=(moments(seed,arm) if observation_dir is None else
          {(r['time_s'],r['cell'],r['lane']):r for r in e.load(observation_dir/f's{seed}_{arm}.json')['rows']})
    old_advance=PhysicalLaneGroups.advance;old_update=mn.metanet_speed_update_kmh
    context={};audit=[]
    def observed(plant,t,c,g):
        if len(plant.widths[c])==1:ls=range(1,int(sum(plant.widths[c]))+1)
        elif g<2:ls=[g+1]
        else:ls=range(3,int(sum(plant.widths[c]))+1)
        # An empty group has no mean speed. Keep its existing model velocity;
        # never fill it using a later observation.
        rows=[data[t,c,str(l)] for l in ls if (t,c,str(l)) in data]
        return sum(r['n']*r['speed_mean'] for r in rows)/sum(r['n'] for r in rows) if rows else None
    def advance(plant,state,*args,**kwargs):
        context.update(plant=plant,t=int(state.time_sec),index=0,
            order=[(c,g) for c,ws in enumerate(plant.widths) for g in range(len(ws))])
        try:
            for c,g in context['order']:
                v=observed(plant,context['t'],c,g)
                if c in selected and v is not None:plant.v[c][g]=v
            result=old_advance(plant,state,*args,**kwargs)
            assert context['index']==len(context['order'])
            # The speed equation is followed by merge/FIFO projections inside
            # advance. Override those too, otherwise the following ramp-supply
            # query sees a partly modelled speed despite the oracle label.
            for c,g in context['order']:
                v=observed(plant,context['t']+10,c,g)
                if c not in selected or v is None:continue
                plant.v[c][g]=v
                record=next(r for r in reversed(plant.rows) if r['time_s']==context['t']+10 and r['cell']==c and r['group']==g)
                record['v_kmh']=v
            state.freeway_speed[plant.road]=[sum(n*v for n,v in zip(ns,plant.v[c]))/sum(ns)
                if sum(ns) else sum(plant.v[c])/len(ns) for c,ns in enumerate(plant.n)]
            state.freeway_flow[plant.road]=[sum(n*v for n,v in zip(ns,plant.v[c]))/plant.lengths[c]
                for c,ns in enumerate(plant.n)]
            return result
        finally:context.clear()
    def update(*args,**kwargs):
        value=old_update(*args,**kwargs)
        if not context:return value
        c,g=context['order'][context['index']];context['index']+=1
        v=observed(context['plant'],context['t']+10,c,g)
        if c not in selected or v is None:return value
        audit.append({'t':context['t']+10,'cell':c,'group':g,'observed_v':v,'model_v':value,'v_min':args[-1]})
        return v
    PhysicalLaneGroups.advance=advance;mn.metanet_speed_update_kmh=update
    try:yield audit
    finally:PhysicalLaneGroups.advance=old_advance;mn.metanet_speed_update_kmh=old_update


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=HERE/'destination_clear_ending_lane_v1/config.json')
    parser.add_argument('--parameters',type=Path,default=LANE/'qualification_v6/parameters.json')
    parser.add_argument('--output',type=Path,default=HERE/'speed_oracle_v1')
    parser.add_argument('--ramp-origin',type=Path)
    parser.add_argument('--regions',nargs='+',choices=['all','diverge','merge','downstream'],default=['all','diverge','merge','downstream'])
    parser.add_argument('--external-oracle',action='store_true')
    parser.add_argument('--future-exchange',type=Path)
    parser.add_argument('--rm',action='store_true')
    parser.add_argument('--open-outlet',action='store_true',
        help='Diagnostic combination: existing zero-gradient FW_E terminal and observed speed')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(exist_ok=False)
    params=e.load(args.parameters)['parameters'];profile=e.load(MODEL/'port_profile.json')
    results={}
    cases=[(23,['none','vsl'])] if args.external_oracle else [(23,['none','vsl']),(33,['none','spread_only'])]
    if args.rm:
        if args.external_oracle or args.future_exchange:raise ValueError('RM probe isolates observed speeds only')
        cases=[(s,['none','rm_ramp']) for s in [23,33]]
    for seed,arms in cases:
        _,folder,bank,start=next(r for r in CASES if r[0]==seed)
        data=e.ObservationData(folder);lane=e.load(LANE/f'observations_v1/s{seed}.json')
        model=e.load_base_model(data.geometry,args.config.resolve())
        if args.open_outlet:
            original_config=model._config
            def open_config(road, overrides):
                cfg=original_config(road,overrides)
                if road=='FW_E':cfg.network.terminal_zero_gradient=True
                return cfg
            model._config=open_config
        origins=e.load(args.ramp_origin/f's{seed}.json') if args.ramp_origin else None
        results[seed]={}
        regions=([(name,range(21)) for name in ['unchanged','source','arrival','drain','direct_upper','all_external']]
                 if args.external_oracle else [('all',range(21)),('diverge',range(5,10)),('merge',range(12,15)),('downstream',range(15,21))])
        for label,selected in regions:
            if not args.external_oracle and label not in args.regions:continue
            byarm={}
            for arm in arms:
                command=(lambda _: ({},{d:100 for d in range(51,59)})) if arm=='vsl' else (lambda _: ({},{}))
                if arm=='rm_ramp':command=lambda t: ({'RM_C10490':[8,6,4][int((t-start)//150)]},{})
                w=e.window(data,model,start,'history_forecast',profile,command,
                    port_origin_counts=origins['counts'] if origins else None)
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)]}}
                if args.ramp_origin:
                    w['lane_group_dynamics']['FW_E']['initial_ramp_origin']=origins['counts'][str(start)]
                if model.port_initial_positions:
                    w['lane_group_dynamics']['FW_E']['initial_off_eligible']=origins['eligible_before_off'][str(start)]
                if args.future_exchange:
                    rates=e.load(args.future_exchange/f's{seed}_{arm}.json')['exchange_rates_per_sec']
                    w['lane_group_dynamics']['FW_E']['exchange_rates_per_sec']=rates
                if args.external_oracle and label!='unchanged':
                    actual=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
                    channels=['source','arrival','drain'] if label=='all_external' else [label]
                    observed_external(w,actual,model,channels)
                with speeds(seed,arm,set(selected),HERE/'rm_moments_v1' if args.rm else None) as audit:pred=e.simulate(model,w,params)
                pred['diagnostics']['future_speed_oracle_samples']=len(audit)
                byarm[arm]=parts(pred)
                e.save(out/f'prediction_s{seed}_{label}_{arm}.json',pred)
                e.save(out/f'audit_s{seed}_{label}_{arm}.json',audit)
            delta={a:{k:v-byarm['none'][k] for k,v in byarm[a].items()} for a in arms[1:]}
            for r in delta.values():r['total']=sum(r.values())
            results[seed][label]={'parts':byarm,'delta':delta}
            print(seed,label,delta,flush=True)
    e.save(out/'results.json',{'status':'DIAGNOSTIC_ONLY_FUTURE_SPEED_STATES',
        'future_inventory_resets':0,'future_external_oracle':args.external_oracle,
        'open_outlet':args.open_outlet,
        'future_exchange_hazards':args.future_exchange is not None,'results':results})


if __name__=='__main__':main()
