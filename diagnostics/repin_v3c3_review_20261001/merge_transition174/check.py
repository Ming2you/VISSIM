"""Replay frozen173 twice and audit actual speed calls plus native population change.

No coefficient fit, state reset, or future-observation input to either rollout.
"""
import copy
import gzip
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve completed or failed work'
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    from evaluation.controllers import lane_plant_runtime as lpr, physical_lane_groups as lanes
    from evaluation.controllers import offramp_routing as routing, area_freeway_accounting as area
    from evaluation.controllers.freeway_fd import state_response_coefficients

    protected = h.read(h.R/'merge_target173/protocol.json')
    pins = {str(Path(__file__)):h.sha(__file__)}
    def read(p):
        pins[str(p)] = h.sha(p)
        return h.read(p)
    source = read(h.R/'merge_target173/executed_function_sources.json')
    spec = read(h.R/'merge_target173/spec.json')
    h.save(HERE/'protocol.json', dict(
        previous_goal_turn='PROGRESS: user-requested172/173 handoff published and remote7c2fea4a verified.',
        question='Which actually executed speed terms create10/11 state drift, and how much native mean-speed change is population turnover?',
        prior=['Claude03_codex_review: nontransferable cell parameters and transition bounds',
               '148 consumed parameter context bug', '160 localODE limitations',
               '48/50/51/52 first-region transport and failed recovery fit', '172 target-lane evidence', '173 rejected candidate'],
        budget=dict(replays=2,seconds_each=450,cells=[10,11],lanes=[1,2,3,4],fits=0,native=0,FZP=0),
        invariants='Frozen173 source/spec/153 coefficients/171 admission. Exact cells/flows/ports/ramps replay required; instrumentation never changes arguments or returns.',
        limits=['Native5s membership decomposition is exact for observed endpoints, not a complete within-step lane-change ledger.',
                'Model term attribution is its executed algebra, not an identified causal share of native error.',
                'Same-vehicle speed change is separated from entrants/leavers; individual acceleration is not a conservation equation for aggregate speed.',
                'No independent-state qualification, coefficient change, production adoption or9000 run.'],
        protected_sha256=protected['protected_sha256'],STOP=protected['STOP']))
    h.save(HERE/'status.json',dict(status='running',completed_replays=0))
    context,replay,_ = common.setup()
    manifest=h.R/'coupled_recovery153/candidate/manifest.json';read(manifest)
    model=lpr.load_sources(manifest)['component']
    contract=read(h.F/'route_inventory/contract.json')
    records=[r for r in common.records(False) if r['arm'] in ('release','release_vsl90')]
    assert len(records)==2
    mn=area._mn;hooks=[];active={};traces=[];native=[];state_rows=[];parities=[]
    max_algebra_error=0.;canonical_calls=0;completed=0
    original_update=mn.metanet_speed_update_kmh
    speedctx=original_update.__globals__['_FW_SEG_CTX']
    try:
        assert not hasattr(lanes,'RouteLaneRegion')
        ns={};exec(compile(source['RouteLaneRegion'],'174_frozen173_class','exec'),lanes.__dict__,ns)
        lanes.RouteLaneRegion=ns['RouteLaneRegion'];hooks.append((lanes,'RouteLaneRegion',None))
        for target,name in ((routing,'initialize_inventory'),(routing,'advance_inventory'),(area,'_freeway_substep_events'),(type(model),'rollout')):
            fn=getattr(target,name);ns={};exec(compile(source[name],'174_'+name,'exec'),fn.__globals__,ns)
            hooks.append((target,name,fn));setattr(target,name,ns[name])
        original_speed=lanes.RouteLaneRegion.speed
        def audit_update(*args):
            nonlocal max_algebra_error,canonical_calls
            if not active:return original_update(*args)
            obj=active['obj'];i=active['cell'];g=active['g'];active['g']+=1
            assert speedctx['armed']
            p=copy.deepcopy(speedctx['p']);sr=copy.deepcopy(speedctx['state_response'])
            v,up,rho,down,target,dt,length,tau,nu,kappa,vmin=args
            length=p.get('segment_length_km',length);tau=p.get('metanet_tau_h',tau);kappa=p.get('metanet_kappa_veh_km_lane',kappa)
            tau,nu=state_response_coefficients(sr,v,target,rho,down,speedctx['response_rho_crit'],tau,nu)
            assert abs(length-obj.lengths[i])<1e-12
            terms=dict(lateral_mixing=v-obj.oldv[i][g],relaxation=dt/tau*(target-v),
                convection=dt/length*v*(up-v),anticipation=-nu*dt*(down-rho)/(tau*length*(rho+kappa)))
            raw=v+terms['relaxation']+terms['convection']+terms['anticipation']
            floored=max(vmin,raw);terms['speed_floor']=floored-raw
            phi=speedctx.get('phi',0.);dl=speedctx.get('dlam',0.)
            after_drop=floored
            if phi>0 and dl>0:
                after_drop=max(vmin,floored-phi*dt*dl*max(rho,0)*v*v/(length*speedctx['lanes']*p['rho_crit']))
            terms['lane_drop']=after_drop-floored
            value=original_update(*args);canonical_calls+=1
            error=abs(value-after_drop);max_algebra_error=max(max_algebra_error,error);assert error<1e-8
            loss=active['delta']*obj.merge[i][g]*obj.oldv[i][g]/(length*(rho+active['kappa'])) if active['delta']>0 and obj.merge[i][g] else 0.
            final=max(vmin,value-loss);terms['merge_loss']=-loss;terms['last_floor']=final-(value-loss)
            assert abs(sum(terms.values())-(final-obj.oldv[i][g]))<1e-8
            requests=sum(row[g] for off,row in obj.off_requests.items() if obj.off_access[off]==g
                and active['cfg'].network.offramp_route_inventory['branches'][off]['source_cell']==i)
            sent=sum(row[g] for off,row in obj.off_sent.items() if obj.off_access[off]==g
                and active['cfg'].network.offramp_route_inventory['branches'][off]['source_cell']==i)
            active['rows'].append(dict(arm=active['arm'],time_s=active['time'],cell=i,lane=g+1,
                n_before=obj.n0[i][g],old_v=obj.oldv[i][g],exchange_v=v,final_v=final,
                rho=rho,up_v=up,down_rho=down,target=target,terms=terms,
                tau_sec=tau*3600,nu=nu,length_km=length,kappa=kappa,
                accepted_merge=obj.merge[i][g],delta_merge=active['delta'],
                off_request=requests,off_sent=sent,context_parameters=p,state_response=sr))
            return value
        def audit_speed(obj,i,state,cfg,control,mn_arg,exposure,delta,kappa):
            assert not active
            active.update(obj=obj,cell=i,g=0,cfg=cfg,delta=delta,kappa=kappa,time=state.time_sec,arm=current_arm,rows=[])
            try:
                value=original_speed(obj,i,state,cfg,control,mn_arg,exposure,delta,kappa)
                assert active['g']==4
                for row in active['rows']:
                    assert abs(row['final_v']-obj.next_v[i][row['lane']-1])<1e-9
                traces.extend(active['rows']);return value
            finally:active.clear()
        lanes.RouteLaneRegion.speed=audit_speed
        mn.metanet_speed_update_kmh=audit_update
        for rec in records:
            current_arm=rec['arm'];pins[rec['input']]=rec['sha256']
            args,kw=copy.deepcopy(replay.read_primitive_capture(rec['input'],rec['sha256']))
            assert kw['horizon_sec']==450 and args[2]==context['parameters']
            kw.update(offramp_inventory=dict(contract=copy.deepcopy(contract),raw=read(h.F/'route_inventory/s67_late/initial_raw.json')))
            kw['port_dynamics']['entry_capacity_mode']='storage'
            kw['route_lane_regions']={'FW_E':copy.deepcopy(spec)}
            pred=model.rollout(*args,**kw);completed+=1
            old=read(h.R/'merge_target173/forecast/target_lanes'/('s67_late_'+current_arm+'.json.gz'))
            parity={k:json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps')}
            assert all(parity.values());parities.append(dict(arm=current_arm,**parity))
            doc=read(h.F/'flow67'/(current_arm+'_frames.json.gz'));fields=doc['fields']
            frames={round(float(t),6):{vid:dict(zip(fields,row)) for vid,row in f.items()} for t,f in doc['frames'].items()}
            model_rows={(round(row['time_s'],6),row['cell'],row['lane']):row for row in pred['diagnostics']['roads'][0]['joint_lane_region']['rows']}
            for t,u in zip(sorted(frames),sorted(frames)[1:]):
                assert abs(u-t-5)<1e-7
                for cell in (10,11):
                    for lane in (1,2,3,4):
                        a={v:r for v,r in frames[t].items() if r['cell']==cell and r['lane']==lane}
                        b={v:r for v,r in frames[u].items() if r['cell']==cell and r['lane']==lane}
                        if not a or not b:continue
                        v0=sum(r['speed_kmh'] for r in a.values())/len(a);v1=sum(r['speed_kmh'] for r in b.values())/len(b)
                        staying=a.keys()&b.keys();entering=b.keys()-a.keys();leaving=a.keys()-b.keys()
                        terms=dict(stayers=sum(b[v]['speed_kmh']-a[v]['speed_kmh'] for v in staying)/len(b),
                            entrants=sum(b[v]['speed_kmh']-v0 for v in entering)/len(b),
                            leavers=-sum(a[v]['speed_kmh']-v0 for v in leaving)/len(b))
                        assert abs(sum(terms.values())-(v1-v0))<1e-8
                        m1=model_rows[u,cell,lane]
                        m0=model_rows.get((t,cell,lane))
                        native.append(dict(arm=current_arm,time_s=t,cell=cell,lane=lane,n0=len(a),n1=len(b),v0=v0,v1=v1,
                            stayers=len(staying),entrants=len(entering),leavers=len(leaving),terms=terms,
                            instantaneous_acceleration_kmh_per_s=3.6*sum(r['acceleration_mps2'] for r in a.values())/len(a)))
                        state_rows.append(dict(arm=current_arm,time_s=u,cell=cell,lane=lane,
                            actual_n=len(b),model_n=m1['n_veh'],actual_v=v1,model_v=m1['v_kmh'],
                            model_delta5=m1['v_kmh']-(m0['v_kmh'] if m0 else v0),native_delta5=v1-v0))
            h.save(HERE/'status.json',dict(status='running',completed_replays=completed))
    finally:
        mn.metanet_speed_update_kmh=original_update
        for target,name,fn in reversed(hooks):
            if fn is None:delattr(target,name)
            else:setattr(target,name,fn)
    assert completed==2 and canonical_calls==7200
    summary=[]
    for arm in ('release','release_vsl90'):
        for cell in (10,11):
            for lane in (1,2):
                for lo,hi in ((2670.1,2675.1),(2670.1,2700.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                    ts=[r for r in traces if r['arm']==arm and r['cell']==cell and r['lane']==lane and lo-1e-6<=r['time_s']<hi-1e-6]
                    ns=[r for r in native if r['arm']==arm and r['cell']==cell and r['lane']==lane and lo-1e-6<=r['time_s']<hi-1e-6]
                    ss=[r for r in state_rows if r['arm']==arm and r['cell']==cell and r['lane']==lane and lo+1e-6<r['time_s']<=hi+1e-6]
                    if not ts or not ns:continue
                    summary.append(dict(arm=arm,cell=cell,lane=lane,lo=lo,hi=hi,
                        model_terms_per_second={k:sum(r['terms'][k] for r in ts)/len(ts) for k in ts[0]['terms']},
                        native_terms_per_second={k:sum(r['terms'][k] for r in ns)/(5*len(ns)) for k in ns[0]['terms']},
                        native_instantaneous_acceleration=sum(r['instantaneous_acceleration_kmh_per_s'] for r in ns)/len(ns),
                        native_mean_delta_per_second=sum(r['v1']-r['v0'] for r in ns)/(5*len(ns)),
                        model_mean_delta_per_second=sum(sum(r['terms'].values()) for r in ts)/len(ts),
                        mean_n_error=sum(r['model_n']-r['actual_n'] for r in ss)/len(ss),
                        mean_v_error=sum(r['model_v']-r['actual_v'] for r in ss)/len(ss),
                        speed_rmse=math.sqrt(sum((r['model_v']-r['actual_v'])**2 for r in ss)/len(ss)),
                        model_parameter_context=ts[0]['context_parameters'],state_response=ts[0]['state_response']))
    for p,d in {**pins,**protected['protected_sha256'],protected['STOP']['path']:protected['STOP']['sha256']}.items():assert h.sha(p)==d,p
    for name,value in [('executed_terms',traces),('native_population',native),('matched_states',state_rows)]:
        with gzip.open(HERE/(name+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(value,f,allow_nan=False)
    h.save(HERE/'summary.json',summary);h.save(HERE/'parity.json',parities)
    h.save(HERE/'verification.json',dict(actual_speed_calls=canonical_calls,manual_max_error=max_algebra_error,
        native_population_identities=len(native),input_sha256=pins,protected_and_STOP_preserved=True,
        completed_replays=completed,production_adopted=False,new_fits=0,new_native=0,new_FZP=0,hooks_restored=True))
    h.save(HERE/'status.json',dict(status='complete_diagnostic_only',completed_replays=completed))
    for row in summary:
        if row['arm']=='release' and row['lane']==1 and row['hi']-row['lo']<=5.1:print(row)


if __name__=='__main__':main()
