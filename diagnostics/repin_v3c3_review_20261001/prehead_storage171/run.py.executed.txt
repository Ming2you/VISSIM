"""Frozen regional/state lateral closures on existing148, no future lane data."""
import copy
import gzip
import json
import math
import time
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
from diagnostics.repin_v3c3_review_20261001.state_lateral168.fit import rates

HERE=Path(__file__).resolve().parent


def main(*, joint169=False, prehead171=False):
    joint169 = joint169 or prehead171
    work=(h.R/'prehead_storage171' if prehead171 else
          h.R/'recovery_lateral169' if joint169 else HERE)
    out=work/'forecast';out.mkdir(exist_ok=True)
    source_folder='coupled_recovery158' if joint169 else 'spatial_context148'
    modes=('state',) if joint169 else ('regional','state')
    budget=9 if joint169 else 17
    assert not (out/'status.json').exists()
    assert h.read(HERE/'status.json')['status']=='coefficients_frozen'
    protocol=h.read(HERE/'protocol.json');pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    coeff=read(HERE/'coefficients.json')
    assert coeff['max_projected_gradient']<1e-5
    assert len(coeff['state'])==10 and len(coeff['regional'])==8
    pins[str(HERE/'fit.py')]=h.sha(HERE/'fit.py');read(HERE/'protocol.json')
    source=read(h.R/source_folder/'forecast/executed_function_sources.json')
    if prehead171:
        read(work/'source_archive.json');read(work/'protocol.json')
        read(h.R/'ramp10639_170/prehead_storage.json')
        pins[str(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py')]=h.sha(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py')
    elif joint169:
        read(work/'source_archive.json')
        read(HERE/'completion.json');read(HERE/'state_comparison.json');read(HERE/'state_recurrence.json')
        read(h.R/'coupled_recovery158/proposal.json')
        h.save(work/'protocol.json',dict(previous_goal_turn='PROGRESS168 independent execution and matched-state closure checks',
            hypothesis='168 observed-state20 lateral response is close but autonomous early20/21 state remains wrong.158 improves early20 state but used constant lateral exchange. Test their one frozen interaction; not a coefficient or feature grid.',
            source='Exact158: finite target-speed exit feedback plus153 three frozen coefficients. Only168 current-state lateral matrix20--25 is added.',
            coefficients='Frozen168 state trained29;158 coefficients previously fitted/inspected67. These are reused diagnostic states, not blind validation.',
            limitation='158 delta21=0 is an unadopted identification proposal, not absence of real merge friction.25 lane3 observed-state closure remains weak. No automatic adoption even if combined gain sign improves.',
            gate='Unchanged148 meaningful gain signs,response error at least10%better,absolute<=110%,choice regret<=.5; compare148,158,168. No further coefficient combinations on failure.',
            budget=dict(forecasts=budget,new_fits=0,native=0,FZP=0),
            protected_sha256=protocol['protected_sha256'],STOP=protocol['STOP']))
    old='''            matrix = []
            for g,rates in enumerate(self.rates):
                hazard = sum(rates)
                matrix.append([ns[g]*(1.-math.exp(-hazard*dt*3600))*r/hazard if hazard else 0. for r in rates])
'''
    assert source['RouteLaneRegion'].count(old)==1
    changed=dict(source,RouteLaneRegion=source['RouteLaneRegion'].replace(old,
        '            matrix = _lateral168_matrix(self, i, ns, state.time_sec, dt*3600)\n'))
    assert all(changed[k]==v for k,v in source.items() if k!='RouteLaneRegion')
    h.save(out/'executed_function_sources.json',changed)
    context,replay,Obs=common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr,physical_lane_groups as lanes,offramp_routing as routing,area_freeway_accounting as area
    manifest=h.R/('coupled_recovery153/candidate/manifest.json' if joint169 else 'lane_state132/eval_01/manifest.json');read(manifest)
    model=lpr.load_sources(manifest)['component']
    spec=read(h.F/'joint_lane_25/protocol.json')['candidate']
    spec.update(congested_receiving_cells=[21],reciprocal_off='10483')
    contract=read(h.F/'route_inventory/contract.json')
    catalog=read(h.C/'data_catalog.json')['checked_records']
    records=[r for r in catalog if r['case']=='s29_late']+common.records(False)
    assert len(records)==8
    control=dict(mode='original',trace=[])
    def matrix(obj,i,ns,t,dt):
        assert i in range(20,26) and abs(dt-1)<1e-8
        rate=obj.rates if control['mode']=='original' else rates(coeff,i,obj.n0[i],obj.oldv[i],obj.lengths[i],control['mode'])
        result=[]
        for g,row in enumerate(rate):
            hazard=sum(row)
            result.append([ns[g]*(1-math.exp(-hazard*dt))*r/hazard if hazard else 0. for r in row])
        assert all(sum(row)<=ns[g]+1e-9 for g,row in enumerate(result))
        if control['mode']!='original':
            control['trace'].append(dict(time_s=t,cell=i,state_n=list(obj.n0[i]),state_v=list(obj.oldv[i]),length_km=obj.lengths[i],
                donor_stock=list(ns),rates=rate,requested=copy.deepcopy(result)))
        return result
    # Constant/zero-state-slope algebra and donor limits before any rollout.
    fixture=dict(coeff);fixture['state']=coeff['regional']+[0.,0.]
    for i in range(20,26):
        assert rates(fixture,i,[2,4,6],[20,40,60],.1,'state')==rates(fixture,i,[2,4,6],[20,40,60],.1,'regional')
    h.save(out/'preflight.json',dict(status='pass',only_lateral_matrix_changed=True,other_sources_exact_base=True,base=source_folder,
        frozen_coeff_sha256=h.sha(HERE/'coefficients.json'),source_sha256=h.sha(out/'executed_function_sources.json'),
        no_future_covariates=True,physical_integration_sec=1,other_coefficients='exact153 baseline158' if joint169 else 'exact132 baseline148'))
    h.save(out/'protocol.json',dict(parent_protocol=str(work/'protocol.json'),budget_forecasts=budget,
        modes=list(modes),manifest=str(manifest),source=source_folder+' except current-state lateral-rate callback20--25',
        future_observations_in_model=False,gate='Same148 meaningful signs, pair-response>=10% improvement, absolute<=110%, selection regret<=.5. No tuning on evaluated outcomes.',
        protected_sha256=protocol['protected_sha256'],STOP=protocol['STOP']))
    hooks=[];instances=[];forecasts=0;started=time.perf_counter();all_rows={}
    h.save(out/'status.json',dict(status='running',forecasts=0))
    def run(rec,mode):
        nonlocal forecasts
        pins[rec['input']]=rec['sha256']
        args,kw=copy.deepcopy(replay.read_primitive_capture(rec['input'],rec['sha256']))
        args_before=copy.deepcopy(args)
        assert kw['horizon_sec']==450 and args[2]==context['parameters']
        raw=h.F/'route_inventory'/('initial_raw.json' if rec['case']=='s29_late' else rec['case']+'/initial_raw.json')
        kw.update(offramp_inventory=dict(contract=copy.deepcopy(contract),raw=read(raw)),route_lane_regions={'FW_E':copy.deepcopy(spec)})
        kw['port_dynamics']['entry_capacity_mode']='storage'
        control.update(mode='state' if mode=='parity171' else mode,trace=[])
        pred=model.rollout(*args,**kw);forecasts+=1
        assert args==args_before
        assert len(instances)==1
        obj=instances.pop();assert len(obj.split19_rows)==2700 and obj.split19_error<1e-8
        diag=pred['diagnostics']['roads'][0]
        assert diag['negative_density_count']==0 and diag['continuity_residual_max_veh']<1e-7
        assert diag['joint_lane_region']['route_marginal_max_error']<1e-7
        assert max(abs(r['conservation_residual_veh']) for r in pred['ramps'])<1e-7
        key=rec['case']+'_'+rec['arm']
        if mode in ('original','parity171'):
            ref=read(h.R/(f'recovery_lateral169/forecast/state/{key}.json.gz' if mode=='parity171'
                          else f'{source_folder}/forecast/training/{key}.json.gz'))
            parity={k:json.loads(json.dumps(pred[k]))==ref[k] for k in ('cells','flows','ports','ramps')}
            h.save(out/'parity.json',parity);assert all(parity.values());return
        assert len(control['trace'])==2700
        obs=Obs(rec['truth']);row=replay._cellwise_measure(model,pred,rec,obs);row.pop('score',None)
        errors={'n':[],'v':[],'q':[]}
        for z in pred['cells']:
            if 19<=z['cell']<=25:
                a=next(v for v in obs.cells[round(z['time_s'],6)] if v['road']=='FW_E' and v['cell']==z['cell'])
                errors['n'].append(z['n_veh']-a['n_veh'])
                if a['v_kmh'] is not None:errors['v'].append(z['v_kmh']-a['v_kmh'])
        for z in pred['flows']:
            if 19<=z['cell']<=25:
                a=obs.flows[round(z['window_end_s'],6),'FW_E',z['cell']]
                errors['q'].append((z['downstream_crossings']-float(a['downstream_crossings']))*120)
        row['local_rmse']={k:math.sqrt(sum(x*x for x in v)/len(v)) for k,v in errors.items()}
        row['route_error']=diag['joint_lane_region']['route_marginal_max_error']
        row['spatial_checks']=len(obj.split19_rows)
        for name in ('cells_30s.csv','flows_30s.csv','ports_30s.csv'):
            p=Path(rec['truth'])/name;pins[str(p)]=h.sha(p)
        for suffix,payload in [('',pred),('_transfers',control['trace'])]:
            with gzip.open(out/mode/(key+suffix+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(payload,f,allow_nan=False)
        all_rows[mode].append(row);h.save(out/mode/'rows.json',all_rows[mode])
        h.save(out/'status.json',dict(status='running',mode=mode,case=rec['case'],arm=rec['arm'],forecasts=forecasts))
    try:
        assert not hasattr(lanes,'RouteLaneRegion') and not hasattr(lanes,'_lateral168_matrix')
        lanes._lateral168_matrix=matrix;hooks.append((lanes,'_lateral168_matrix',None))
        ns={};exec(compile(changed['RouteLaneRegion'],'168class','exec'),lanes.__dict__,ns)
        lanes.RouteLaneRegion=ns['RouteLaneRegion'];hooks.append((lanes,'RouteLaneRegion',None))
        original_init=lanes.RouteLaneRegion.__init__
        def record_instance(obj,*a,**kw):original_init(obj,*a,**kw);instances.append(obj)
        lanes.RouteLaneRegion.__init__=record_instance
        for target,name in ((routing,'initialize_inventory'),(routing,'advance_inventory'),(area,'_freeway_substep_events'),(type(model),'rollout')):
            old_fn=getattr(target,name);ns={};exec(compile(changed[name],'168_'+name,'exec'),old_fn.__globals__,ns)
            hooks.append((target,name,old_fn));setattr(target,name,ns[name])
        if prehead171:
            from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
            fixed_admission=PhysicalRampBoundary._admission_space_veh
            hooks.append((PhysicalRampBoundary,'_admission_space_veh',fixed_admission))
            PhysicalRampBoundary._admission_space_veh=lambda obj:max(0.,obj.capacity_veh-obj._stocks()['connector_veh'])
            run(records[0],'parity171')
            PhysicalRampBoundary._admission_space_veh=fixed_admission
        else:
            run(records[0],'original')
        for mode in modes:
            (out/mode).mkdir();all_rows[mode]=[]
            for rec in records:run(rec,mode)
        old=read(h.R/'spatial_context148/forecast/training/rows.json')
        baseline=h.losses(old,[1.]*4);assess={}
        for mode,rows in all_rows.items():
            result=h.losses(rows,[1.]*4);regrets={}
            for case in sorted({r['case'] for r in rows}):
                group=[r for r in rows if r['case']==case]
                regrets[case]=min(group,key=lambda r:r['predicted']['ttt'])['actual']['ttt']-min(r['actual']['ttt'] for r in group)
            checks=dict(meaningful_signs=all(p['sign_correct'] for p in result['pairs'] if p['meaningful']),
                response_improvement=result['response']<=.9*baseline['response'],absolute=result['absolute']<=1.1*baseline['absolute'],choice=max(regrets.values())<=.5)
            assess[mode]=dict(result=result,checks=checks,regrets=regrets)
        assert forecasts==budget
        references={}
        if prehead171:
            references['joint169']=h.losses(read(h.R/'recovery_lateral169/forecast/state/rows.json'),[1.]*4)
        if joint169:
            references['recovery158']=h.losses(read(h.R/'coupled_recovery158/forecast/training/rows.json'),[1.]*4)
            references['lateral168']=h.losses(read(HERE/'forecast/state/rows.json'),[1.]*4)
        h.save(out/'assessment.json',dict(status='complete',baseline=baseline,references=references,candidates=assess,forecasts=forecasts,
            elapsed_sec=time.perf_counter()-started,production_adopted=False,goal_complete=False))
        h.save(out/'status.json',dict(status='complete',forecasts=forecasts))
        for mode,a in assess.items():
            print(mode,a['checks'])
            for p in a['result']['pairs']:
                if p['case']=='s67_late' and p['right'] in ('release','release_vsl90'):print(p)
    except BaseException as exc:
        h.save(out/'status.json',dict(status='failed',forecasts=forecasts,error=repr(exc)));raise
    finally:
        for target,name,old_fn in reversed(hooks):
            if old_fn is None:delattr(target,name)
            else:setattr(target,name,old_fn)
        for path,digest in {**pins,**protocol['protected_sha256']}.items():assert h.sha(path)==digest,path
        assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
        h.save(out/'preservation.json',dict(core=True,STOP=True,input_sha256=pins,hooks_restored=True))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--joint169',action='store_true')
    parser.add_argument('--prehead171',action='store_true')
    args=parser.parse_args()
    main(joint169=args.joint169,prehead171=args.prehead171)
