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


def merge173(*, split175=False):
    """Finite first-merge-region comparison using the same rollout and writer."""
    work=h.R/('merge_split175' if split175 else 'merge_target173');out=work/'forecast'
    modes=('unsplit173','split175') if split175 else ('aggregate','target_lanes')
    baseline_mode,candidate_mode=modes
    assert not out.exists(), 'Do not overwrite a completed/failed experiment'
    out.mkdir()
    protocol=h.read(work/'protocol.json');source=h.read(work/'executed_function_sources.json')
    spec=h.read(work/'spec.json')
    baseline_source=h.read(h.R/'merge_target173/executed_function_sources.json') if split175 else source
    if split175:
        assert h.read(work/'unit_result.json')['status']=='pass'
        assert h.read(work/'unit_result.json')['source_sha256']==h.sha(work/'executed_function_sources.json')
    pins={str(p):h.sha(p) for p in (Path(__file__),work/'protocol.json',work/'spec.json',work/'executed_function_sources.json')}
    pins.update(protocol['pins'])
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    context,replay,Obs=common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr,physical_lane_groups as lanes,offramp_routing as routing,area_freeway_accounting as area
    manifest=h.R/'coupled_recovery153/candidate/manifest.json';pins[str(manifest)]=h.sha(manifest)
    model=lpr.load_sources(manifest)['component']
    contract=h.read(h.F/'route_inventory/contract.json');pins[str(h.F/'route_inventory/contract.json')]=h.sha(h.F/'route_inventory/contract.json')
    catalog=h.read(h.C/'data_catalog.json')['checked_records']
    records=[r for r in catalog if r['case']=='s29_late']+common.records(False)
    cap61=h.read(h.I/'heldout61_freeway_20260930/capture.json')
    records += [dict(r,case='s61_late',cutoff=cap61['cutoff'],truth=str(h.I/'heldout61_freeway_20260930/observations'/r['arm']))
                for r in cap61['records'] if r['arm'] in ('hold','release')]
    assert len(records)==10
    def payload(rec):
        pins[rec['input']]=rec['sha256']
        args,kw=copy.deepcopy(replay.read_primitive_capture(rec['input'],rec['sha256']))
        assert kw['horizon_sec']==450 and len(args[1])==450 and args[2]==context['parameters']
        raw=h.F/'route_inventory'/('initial_raw.json' if rec['case']=='s29_late' else rec['case']+'/initial_raw.json')
        pins[str(raw)]=h.sha(raw)
        kw.update(offramp_inventory=dict(contract=copy.deepcopy(contract),raw=h.read(raw)))
        kw['port_dynamics']['entry_capacity_mode']='storage'
        return args,kw
    hooks=[];instances=[];forecasts=0;rows=[];began=time.perf_counter()
    h.save(out/'status.json',dict(status='running',stage='disabled_parity',forecasts=0))
    try:
        args,kw=payload(records[0])
        original=model.rollout(*copy.deepcopy(args),**copy.deepcopy(kw));forecasts+=1
        if split175:
            reference=h.read(h.R/'merge_target173/forecast/aggregate'/(records[0]['case']+'_'+records[0]['arm']+'.json.gz'))
            parity={k:json.loads(json.dumps(original[k]))==reference[k] for k in ('cells','flows','ports','ramps')}
            h.save(out/'disabled_parity.json',parity);assert all(parity.values())
        assert not hasattr(lanes,'RouteLaneRegion')
        def lane_class(code,spatial=False):
            ns={};exec(compile(code,'175_class' if spatial else '173_class','exec'),lanes.__dict__,ns)
            cls=ns['RouteLaneRegion'];init=cls.__init__;commit=cls.commit
            def observed_init(obj,*a,**k):
                init(obj,*a,**k);instances.append(obj)
                assert obj.cells==[10,11] and obj.groups==4
            cls.__init__=observed_init
            if spatial:
                def guarded_commit(obj,state,cfg):
                    commit(obj,state,cfg)
                    latest=obj.split10_rows[-8:]
                    courant=max([r['courant'] for r in latest]+[r['v_kmh']*cfg.simulation.T_f_h/r['length_km'] for r in latest])
                    if not all(math.isfinite(r['v_kmh']) and r['v_kmh']>=0 for r in latest) or courant>1.05:
                        obj.numerical_gate=dict(time_s=latest[0]['time_s'],max_courant=courant,rows=latest)
                        raise ArithmeticError('175 spatial numerical gate: Courant/nonfinite speed')
                cls.commit=guarded_commit
            return cls
        classes={candidate_mode:lane_class(source['RouteLaneRegion'],split175)}
        if split175:classes[baseline_mode]=lane_class(baseline_source['RouteLaneRegion'])
        lanes.RouteLaneRegion=classes[candidate_mode];hooks.append((lanes,'RouteLaneRegion',None))
        for target,name in ((routing,'initialize_inventory'),(routing,'advance_inventory'),(area,'_freeway_substep_events'),(type(model),'rollout')):
            fn=getattr(target,name);ns={};exec(compile(source[name],'173_'+name,'exec'),fn.__globals__,ns)
            hooks.append((target,name,fn));setattr(target,name,ns[name])
        for index,rec in enumerate(records):
            for mode in modes:
                args,kw=payload(rec)
                before=copy.deepcopy(args)
                if mode==candidate_mode or split175:
                    lanes.RouteLaneRegion=classes[mode]
                    kw['route_lane_regions']={'FW_E':copy.deepcopy(spec)}
                pred=model.rollout(*args,**kw);forecasts+=1
                assert args==before
                if index==0 and mode==baseline_mode and not split175:
                    parity={key:json.loads(json.dumps(pred[key]))==json.loads(json.dumps(original[key])) for key in ('cells','flows','ports','ramps')}
                    h.save(out/'disabled_parity.json',parity);assert all(parity.values())
                    h.save(out/'preflight.json',dict(status='disabled_parity_passed',physical_integration_sec=pred['diagnostics']['component_integration_step_sec'],
                        baseline_no_route_lane_region=True,other_coefficients_unchanged=True))
                if split175 and mode==baseline_mode:
                    ref_path=h.R/'merge_target173/forecast/target_lanes'/(rec['case']+'_'+rec['arm']+'.json.gz')
                    pins[str(ref_path)]=h.sha(ref_path);ref=h.read(ref_path)
                    parity={key:json.loads(json.dumps(pred[key]))==ref[key] for key in ('cells','flows','ports','ramps')}
                    h.save(out/(rec['case']+'_'+rec['arm']+'_baseline_parity.json'),parity);assert all(parity.values())
                road=pred['diagnostics']['roads'][0]
                assert road['continuity_residual_max_veh']<1e-7 and road['negative_density_count']==0
                assert max(abs(x['conservation_residual_veh']) for x in pred['ramps'])<1e-7
                local=None
                if mode==candidate_mode or split175:
                    assert len(instances)==1
                    obj=instances.pop();assert obj.max_residual<1e-7 and len(obj.rows)==3600 and len(obj.receiving_rows)==3600
                    local=dict(initial_inlet=obj.initial_inlet,lanes=len(obj.rows),receiving_rows=len(obj.receiving_rows),route_residual=obj.max_residual)
                    # Observe the accepted shared lane allocation, not merely
                    # the declared receiving cap.
                    supply={(round(x['time_s']+1,6),x['cell'],x['lane']):x['accepted_budget_veh'] for x in obj.receiving_rows}
                    errors=[x['mainline_in_veh']+x['merge_veh']-supply[round(x['time_s'],6),x['cell'],x['lane']] for x in obj.rows
                            if not (split175 and mode==candidate_mode and x['cell']==10)]
                    if split175 and mode==candidate_mode:
                        assert len(obj.split10_rows)==3600 and obj.split10_error<1e-7
                        errors.extend(r['incoming_veh']+r['merge_veh']-r['receiving_budget_veh'] for r in obj.split10_rows)
                        local.update(spatial_checks=len(obj.split10_rows),class_partition_error=obj.split10_error,
                            max_courant=max(max(r['courant'],r['v_kmh']/3600/r['length_km']) for r in obj.split10_rows),
                            max_speed=max(r['v_kmh'] for r in obj.split10_rows))
                        assert local['max_courant']<=1.05
                    local['shared_budget_excess_max_veh']=max(errors)
                    assert max(errors)<1e-7
                obs=Obs(rec['truth']);row=replay._cellwise_measure(model,pred,rec,obs);row.pop('score',None)
                row.update(version=mode,local_verification=local)
                row['cell10_mean_v']=sum(x['v_kmh'] for x in pred['cells'] if x['cell']==10)/15
                rows.append(row)
                key=rec['case']+'_'+rec['arm'];folder=out/mode;folder.mkdir(exist_ok=True)
                with gzip.open(folder/(key+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
                if split175 and mode==candidate_mode:
                    with gzip.open(folder/(key+'_spatial.json.gz'),'wt',encoding='utf-8') as f:
                        json.dump(dict(initial=obj.split10_initial,rows=obj.split10_rows,checks=local),f,allow_nan=False)
                h.save(out/'rows.json',rows)
                for name in ('cells_30s.csv','flows_30s.csv','ports_30s.csv'):
                    p=Path(rec['truth'])/name;pins[str(p)]=h.sha(p)
                h.save(out/'status.json',dict(status='running',case=rec['case'],arm=rec['arm'],mode=mode,forecasts=forecasts))
                print(rec['case'],rec['arm'],mode,row['predicted']['merges'].get('10639'),row['predicted']['ttt'],flush=True)
        assert forecasts==21
        comparison=[]
        for case in ('s29_late','s67_late','s61_late'):
            for left,right in [('hold','release'),('release','release_vsl90')]:
                by={(x['version'],x['arm']):x for x in rows if x['case']==case}
                if (baseline_mode,right) not in by:continue
                z=dict(case=case,left=left,right=right)
                for mode in modes:
                    a,b=by[mode,left],by[mode,right]
                    z[mode]={k:b['predicted'][k]-a['predicted'][k] for k in ('ttt','mainline_ttt','ramp_ttt','end_n','exits')}
                    z['actual']={k:b['actual'][k]-a['actual'][k] for k in ('ttt','mainline_ttt','ramp_ttt','end_n','exits')}
                comparison.append(z)
        h.save(out/'assessment.json',dict(status='complete',forecasts=forecasts,seconds=time.perf_counter()-began,comparisons=comparison,
             production_adopted=False,gain_qualified=False,qualification='First-region isolation only; full171 combination/independent/wholeOmega/SDMPC gates remain.'))
        h.save(out/'status.json',dict(status='complete',forecasts=forecasts))
        print('completed',forecasts,comparison,flush=True)
    except BaseException as e:
        if split175 and instances:
            obj=instances[-1]
            with gzip.open(out/'failed_partial.json.gz','wt',encoding='utf-8') as f:
                json.dump(dict(case=rec['case'],arm=rec['arm'],mode=mode,error=repr(e),
                    rows=getattr(obj,'rows',[]),spatial_rows=getattr(obj,'split10_rows',[]),
                    initial=getattr(obj,'split10_initial',None),numerical_gate=getattr(obj,'numerical_gate',None),
                    spatial_stocks=getattr(obj,'split10',None),spatial_speeds=getattr(obj,'split10_v',None)),f,allow_nan=False)
        h.save(out/'status.json',dict(status='failed',forecasts=forecasts,error=repr(e)));raise
    finally:
        for target,name,fn in reversed(hooks):
            if fn is None:delattr(target,name)
            else:setattr(target,name,fn)
        for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
        h.save(out/'preservation.json',dict(input_sha256=pins,protected_and_STOP=True,hooks_restored=True))


def queue178(*, transport_once179=False, phase_equilibrium181=False, flow_audit182=False, calibration183=None, merge_priority189=False, spatial190=False, calibration191=None, sampling192=False, characteristic195=False, calibration203=None, calibration243=None):
    """One frozen phase-population candidate; existing rollout, no native run."""
    local_probe=merge_priority189 or spatial190 or sampling192 or characteristic195
    reuse_baseline=transport_once179 or phase_equilibrium181 or local_probe
    prior_phase='transport_once179' if phase_equilibrium181 else 'queue_dynamics178'
    prior_label='old179' if phase_equilibrium181 else 'old178'
    work=h.R/('flowbudget182' if flow_audit182 else ('phase_equilibrium181' if phase_equilibrium181 else ('transport_once179' if transport_once179 else 'queue_dynamics178')));out=work/'forecast'
    if local_probe:
        assert not any((transport_once179,phase_equilibrium181,flow_audit182,calibration183))
        assert sum((merge_priority189,spatial190,sampling192,characteristic195))==1
        work=h.R/('characteristic195' if characteristic195 else 'lateral_sampling192' if sampling192 else 'exit_spatial190' if spatial190 else 'merge_priority189');out=work/'forecast'
        if spatial190:work=work/'attempt2';out=work/'forecast'
    candidate_mode='characteristic' if characteristic195 else 'sampling' if sampling192 else 'spatial' if spatial190 else ('priority' if merge_priority189 else 'queue')
    setting183=None
    if calibration183 is not None:
        work=Path(calibration183).resolve();work.relative_to((h.R/'phase_joint183').resolve())
        setting183=h.read(work/'setting.json');out=work/'forecast'
        # Reuse the existing passive audit on explicitly selected saved cases.
        # This changes recording only; every physical table must match reference.
        if setting183.get('flow_audit182',False):flow_audit182=True
    if calibration191 is not None:
        assert not any((calibration183,local_probe,transport_once179,phase_equilibrium181,flow_audit182))
        work=Path(calibration191).resolve();work.relative_to((h.R/'exit_refit191').resolve())
        setting183=h.read(work/'setting.json');out=work/'forecast'
        local_probe=True;spatial190=True;candidate_mode='spatial';reuse_baseline=False
    if calibration203 is not None:
        assert not any((local_probe,transport_once179,phase_equilibrium181,flow_audit182,calibration183,calibration191))
        work=Path(calibration203).resolve();work.relative_to((h.R/'joint_flux203').resolve())
        setting183=h.read(work/'setting.json');out=work/'forecast'
        local_probe=True;merge_priority189=True;candidate_mode='priority';reuse_baseline=False
    if calibration243 is not None:
        assert not any((local_probe,transport_once179,phase_equilibrium181,flow_audit182,calibration183,calibration191,calibration203))
        work=Path(calibration243).resolve();work.relative_to((h.R/'vsl_response243').resolve())
        setting183=h.read(work/'setting.json');out=work/'forecast'
        local_probe=True;candidate_mode='response243';reuse_baseline=False
    assert not out.exists(),'Do not overwrite completed or failed forecasts'
    out.mkdir()
    protocol=h.read(work/'protocol.json');pins=h.read(work/'pins.json')
    for p,d in pins.items():assert h.sha(p)==d,p
    for p in (Path(__file__),work/'coefficients.json',work/'spec.json',work/'executed_function_sources.json'):
        pins[str(p)]=h.sha(p)
    context,replay,Obs=common.setup()
    from evaluation.controllers import lane_plant_runtime as lpr,physical_lane_groups as lanes,offramp_routing as routing,area_freeway_accounting as area
    model=lpr.load_sources(Path(setting183['manifest']) if setting183 else h.R/'lane_state132/eval_01/manifest.json')['component']
    baseline=h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    candidate=h.read(work/'executed_function_sources.json');spec=h.read(work/'spec.json')
    allowed={'RouteLaneRegion','rollout'} if local_probe else {'RouteLaneRegion'}
    assert all(candidate[k]==v for k,v in baseline.items() if k not in allowed)
    catalog=h.read(h.C/'data_catalog.json')['checked_records']
    records=[r for r in catalog if r['case']=='s29_late']+common.records(False)
    records += [r for r in catalog if r['case']=='s43_early' and r['arm'] in ('none','vsl')]
    cap=h.read(h.I/'heldout61_freeway_20260930/capture.json')
    records += [dict(r,case='s61_late',cutoff=cap['cutoff'],truth=str(h.I/'heldout61_freeway_20260930/observations'/r['arm'])) for r in cap['records'] if r['arm'] in ('hold','release')]
    assert len(records)==12
    modes=(setting183['structure'],) if setting183 else ('baseline',candidate_mode)
    if setting183:
        if calibration243 is not None:
            scope=setting183['records']
            if scope=='train':records=[r for r in records if r['case']=='s67_late']
            elif scope=='validation':records=[r for r in records if r['case']!='s67_late']
            elif scope=='parity':records=[r for r in records if r['case']=='s29_late'][:1]
            else:raise ValueError('243 record scope')
        elif setting183['records']=='train':records=[r for r in records if r['case']=='s29_late']
        elif setting183['records']=='validation':records=[r for r in records if r['case']!='s29_late']
        elif setting183['records']=='parity':records=[r for r in records if r['case']=='s29_late'][:1]
        else:raise ValueError('183 record scope')
    if flow_audit182 and not setting183:
        records=[r for r in records if r['case']=='s67_late' and r['arm'] in ('release','release_vsl90')]
        assert len(records)==2
    hooks=[];instances=[];rows=[];forecasts=0;began=time.perf_counter()
    h.save(out/'status.json',dict(status='running',forecasts=0))
    try:
        assert not hasattr(lanes,'RouteLaneRegion')
        classes={}
        for mode,source in [('baseline',baseline),(candidate_mode,candidate)]:
            ns={};exec(compile(source['RouteLaneRegion'],'178_'+mode,'exec'),lanes.__dict__,ns)
            cls=ns['RouteLaneRegion'];init=cls.__init__
            def observed_init(obj,*a,_init=init,**kw):_init(obj,*a,**kw);instances.append(obj)
            cls.__init__=observed_init;classes[mode]=cls
            if flow_audit182:
                plan=cls.plan
                def observed_plan(obj,*a,_plan=plan,**kw):
                    result=_plan(obj,*a,**kw)
                    state,cfg=a[:2]
                    if not hasattr(obj,'audit182'):obj.audit182=[]
                    dt=cfg.simulation.T_f_h
                    budgets={(z['cell'],z['lane']):z for z in obj.receiving_rows if z['time_s']==state.time_sec}
                    for i in (19,20,21):
                        for g,n in enumerate(obj.n0[i]):
                            off=sum(v[g] for k,v in obj.off_sent.items() if cfg.network.offramp_route_inventory['branches'][k]['source_cell']==i)
                            request=sum(v[g] for k,v in obj.off_requests.items() if cfg.network.offramp_route_inventory['branches'][k]['source_cell']==i)
                            end=sum(obj.next[i][g].values())
                            budget=budgets.get((i,g+1),{})
                            obj.audit182.append(dict(time_s=state.time_sec,cell=i,lane=g+1,n=n,end_n=end,v=obj.oldv[i][g],
                                incoming=obj.incoming[i][g],outgoing=obj.outgoing[i][g],merge=obj.merge[i][g],off=off,off_request=request,
                                lateral_net=end-n-obj.incoming[i][g]-obj.merge[i][g]+obj.outgoing[i][g]+off,
                                receiving_before_merge=budget.get('accepted_budget_veh'),receiving_after_merge=obj.free[i][g]))
                    return result
                cls.plan=observed_plan
        if reuse_baseline:
            old178=candidate if local_probe else h.read(h.R/prior_phase/'executed_function_sources.json')
            ns={};exec(compile(old178['RouteLaneRegion'],'179_old178','exec'),lanes.__dict__,ns)
            cls=ns['RouteLaneRegion'];init=cls.__init__
            def observed_old(obj,*a,_init=init,**kw):_init(obj,*a,**kw);instances.append(obj)
            cls.__init__=observed_old;classes[prior_label]=cls
        # A speed-weighted physical transfer cannot silently move a stagnant
        # subset out at the moving population's speed.
        if not local_probe:
            obj=classes['queue'].__new__(classes['queue'])
            obj.phase0={20:[[4.,0.,360.]]};obj.phase_next=copy.deepcopy(obj.phase0)
            obj.phase_start_n={20:[10.]};obj.phase_balance={20:[[0.]*6]}
            obj._phase_flux(20,0,None,1.,'off')
            assert obj.phase_next[20][0]==[4.,0.,300.]
            obj.phase_next={20:[[4.,4.,360.],[1.,2.,180.]]}
            obj.phase_balance={20:[[0.]*6,[0.]*6]}
            before=[sum(p[z] for p in obj.phase_next[20]) for z in range(3)]
            obj._phase_lateral(20,[[0.,2.],[1.,0.]],[10.,5.])
            after=[sum(p[z] for p in obj.phase_next[20]) for z in range(3)]
            assert all(abs(a-b)<1e-12 for a,b in zip(before,after))
            h.save(out/'unit.json',dict(stagnant_phase_not_advected=True,lateral_count_and_both_moments_conserved=True))
        lanes.RouteLaneRegion=classes['baseline'];hooks.append((lanes,'RouteLaneRegion',None))
        for target,name in ((routing,'initialize_inventory'),(routing,'advance_inventory'),(area,'_freeway_substep_events'),(type(model),'rollout')):
            fn=getattr(target,name);ns={};exec(compile((candidate if local_probe else baseline)[name],'178_'+name,'exec'),fn.__globals__,ns)
            hooks.append((target,name,fn));setattr(target,name,ns[name])
        for record in records:
            for mode in modes:
                pins[record['input']]=record['sha256']
                args,kw=copy.deepcopy(replay.read_primitive_capture(record['input'],record['sha256']))
                assert kw['horizon_sec']==450 and args[2]==context['parameters']
                raw=h.F/'route_inventory'/('initial_raw.json' if record['case']=='s29_late' else record['case']+'/initial_raw.json')
                pins[str(raw)]=h.sha(raw)
                kw.update(offramp_inventory=dict(contract=h.read(h.F/'route_inventory/contract.json'),raw=h.read(raw)),
                    route_lane_regions={'FW_E':copy.deepcopy(spec)})
                kw['port_dynamics']['entry_capacity_mode']='storage'
                before=copy.deepcopy(args);lanes.RouteLaneRegion=classes[mode]
                if reuse_baseline and mode=='baseline':
                    if not forecasts:
                        lanes.RouteLaneRegion=classes[prior_label]
                        if merge_priority189:kw['route_lane_regions']['FW_E']['merge_priority189']={'RM_C10490':1.}
                        if spatial190:kw['route_lane_regions']['FW_E']['spatial20_enabled']=False
                        if sampling192:kw['route_lane_regions']['FW_E'].pop('sampling192_rates')
                        if characteristic195:kw['route_lane_regions']['FW_E']['characteristic195']=False
                        oldpred=model.rollout(*args,**kw);forecasts+=1
                        assert len(instances)==1;instances.pop()
                        if local_probe:kw['route_lane_regions']['FW_E']=copy.deepcopy(spec)
                        path=h.R/prior_phase/'forecast'/('baseline' if local_probe else 'queue')/f"{record['case']}_{record['arm']}.json.gz"
                        pins[str(path)]=h.sha(path);ref=h.read(path)
                        parity={k:json.loads(json.dumps(oldpred[k]))==ref[k] for k in ('cells','flows','ports','ramps')}
                        h.save(out/(prior_label+'_parity.json'),parity);assert all(parity.values())
                    path=h.R/'queue_dynamics178/forecast/baseline'/f"{record['case']}_{record['arm']}.json.gz"
                    pins[str(path)]=h.sha(path);pred=h.read(path);obj=None
                else:
                    pred=model.rollout(*args,**kw);forecasts+=1
                    assert len(instances)==1
                    obj=instances.pop()
                assert before==args
                diag=pred['diagnostics']['roads'][0]
                assert diag['negative_density_count']==0 and diag['continuity_residual_max_veh']<1e-7
                if obj is not None:assert obj.max_residual<1e-7 and obj.split19_error<1e-7
                assert max(abs(x['conservation_residual_veh']) for x in pred['ramps'])<1e-7
                if forecasts==1 and not reuse_baseline and not flow_audit182 and not setting183:
                    reference=h.read(h.R/'spatial_context148/forecast/training'/f"{record['case']}_{record['arm']}.json.gz")
                    parity={k:json.loads(json.dumps(pred[k]))==reference[k] for k in ('cells','flows','ports')}
                    h.save(out/'parity.json',dict(**parity,ramp_note='171 prehead admission fix retained; historical ramp storage split is not the current baseline.'))
                    assert all(parity.values())
                if flow_audit182:
                    reference_path=h.R/'phase_equilibrium181/forecast'/mode/f"{record['case']}_{record['arm']}.json.gz"
                    if setting183 and 'audit_reference_dir' in setting183:
                        reference_path=Path(setting183['audit_reference_dir'])/f"{record['case']}_{record['arm']}.json.gz"
                    pins[str(reference_path)]=h.sha(reference_path);reference=h.read(reference_path)
                    parity={k:json.loads(json.dumps(pred[k]))==reference[k] for k in ('cells','flows','ports','ramps')}
                    assert all(parity.values()),parity
                    audit_dir=out/mode;audit_dir.mkdir(exist_ok=True)
                    key=record['case']+'_'+record['arm']
                    with gzip.open(audit_dir/(key+'_audit.json.gz'),'wt',encoding='utf8') as f:
                        json.dump(dict(rows=obj.audit182,junction=obj.junction_rows,receiving=obj.receiving_rows,parity=parity),f,allow_nan=False)
                obs=Obs(record['truth'])
                for horizon in (150,450):
                    # The measure selects occupancy times but totals every
                    # provided flow/merge row. Slice all four native tables.
                    cutoff=record['cutoff']+horizon
                    prefix=dict(pred)
                    for name,key in [('cells','time_s'),('flows','window_end_s'),('ports','time_s'),('ramps','end_sec')]:
                        prefix[name]=[z for z in pred[name] if z[key]<=cutoff+1e-6]
                    measurement=replay._cellwise_measure(model,prefix,record,obs,horizon_sec=horizon)
                    measurement.pop('score',None);measurement.update(mode=mode,horizon=horizon)
                    errors={'n':[],'v':[],'q':[]}
                    for z in pred['cells']:
                        if z['time_s']>cutoff+1e-6 or not 19<=z['cell']<=25:continue
                        a=next(v for v in obs.cells[round(z['time_s'],6)] if v['road']=='FW_E' and v['cell']==z['cell'])
                        errors['n'].append(z['n_veh']-a['n_veh'])
                        if a['v_kmh'] is not None:errors['v'].append(z['v_kmh']-a['v_kmh'])
                    for z in pred['flows']:
                        if z['window_end_s']>cutoff+1e-6 or not 19<=z['cell']<=25:continue
                        a=obs.flows[round(z['window_end_s'],6),'FW_E',z['cell']]
                        errors['q'].append((z['downstream_crossings']-float(a['downstream_crossings']))*120)
                    measurement['local_rmse']={k:math.sqrt(sum(x*x for x in a)/len(a)) for k,a in errors.items()}
                    rows.append(measurement)
                folder=out/mode;folder.mkdir(exist_ok=True);key=record['case']+'_'+record['arm']
                with gzip.open(folder/(key+'.json.gz'),'wt',encoding='utf8') as f:json.dump(pred,f,allow_nan=False)
                if mode=='queue':
                    assert len(obj.phase_rows)==8100 and len(obj.phase_events)==8100
                    with gzip.open(folder/(key+'_phase.json.gz'),'wt',encoding='utf8') as f:
                        json.dump(dict(initial=obj.phase_initial,rows=obj.phase_rows,events=obj.phase_events),f,allow_nan=False)
                if merge_priority189 and obj is not None:
                    with gzip.open(folder/(key+'_allocation.json.gz'),'wt',encoding='utf8') as f:
                        json.dump(dict(allocation=obj.priority_rows,lanes=obj.rows,junction=obj.junction_rows,receiving=obj.receiving_rows),f,allow_nan=False)
                if spatial190 and mode=='spatial' and obj is not None:
                    with gzip.open(folder/(key+'_spatial.json.gz'),'wt',encoding='utf8') as f:
                        json.dump(dict(initial=obj.split20_initial,parts=obj.split20_rows,
                            lanes=obj.rows,junction=obj.junction_rows,receiving=obj.receiving_rows,
                            max_courant=obj.split20_max_courant,max_residual=obj.split20_error),f,allow_nan=False)
                if sampling192 and mode=='sampling' and obj is not None:
                    assert len(obj.lateral192_rows)==2700
                    with gzip.open(folder/(key+'_lateral.json.gz'),'wt',encoding='utf8') as f:
                        json.dump(dict(transfers=obj.lateral192_rows,lanes=obj.rows),f,allow_nan=False)
                if characteristic195 and mode=='characteristic' and obj is not None:
                    assert len(obj.characteristic_rows)==8100
                    with gzip.open(folder/(key+'_transport.json.gz'),'wt',encoding='utf8') as f:
                        json.dump(dict(rows=obj.characteristic_rows,lanes=obj.rows),f,allow_nan=False)
                for name in ('cells_30s.csv','flows_30s.csv','ports_30s.csv'):
                    p=Path(record['truth'])/name;pins[str(p)]=h.sha(p)
                h.save(out/'rows.json',rows)
                h.save(out/'status.json',dict(status='running',case=record['case'],arm=record['arm'],mode=mode,forecasts=forecasts))
                print(record['case'],record['arm'],mode,rows[-1]['predicted']['ttt'],flush=True)
        assert forecasts==(len(records) if setting183 else (4 if flow_audit182 else (13 if reuse_baseline else 24)))
        assessments={}
        for horizon in (150,450):
            assessments[str(horizon)]={mode:h.losses([r for r in rows if r['mode']==mode and r['horizon']==horizon],[]) for mode in modes}
        h.save(out/'assessment.json',dict(status='complete',forecasts=forecasts,seconds=time.perf_counter()-began,
            losses=assessments,production_adopted=False))
        h.save(out/'status.json',dict(status='complete',forecasts=forecasts))
        print('COMPLETED',forecasts,time.perf_counter()-began,flush=True)
    except BaseException as e:
        if instances:
            obj=instances[-1]
            with gzip.open(out/'failed_partial.json.gz','wt',encoding='utf8') as f:
                json.dump(dict(rows=getattr(obj,'phase_rows',[]),events=getattr(obj,'phase_events',[]),
                    phase=getattr(obj,'phase_next',{}),error=repr(e)),f,allow_nan=False)
        h.save(out/'status.json',dict(status='failed',forecasts=forecasts,error=repr(e)));raise
    finally:
        for target,name,fn in reversed(hooks):
            if fn is None:delattr(target,name)
            else:setattr(target,name,fn)
        for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
        h.save(out/'preservation.json',dict(input_sha256=pins,protected_and_STOP=True,hooks_restored=True))


def calibrate183(*, spatial191=False):
    """Equal-budget one-step refit of the baseline and frozen181 phase law."""
    import itertools
    import numpy as np
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response
    root=h.R/('exit_refit191' if spatial191 else 'phase_joint183');assert not (root/'protocol.json').exists()
    dimensions=2 if spatial191 else 4
    structures=('baseline','spatial') if spatial191 else ('baseline','queue')
    max_forecasts=50 if spatial191 else 66
    context,_,_=common.setup()
    frozen=lpr.load_sources(h.R/'lane_state132/eval_01/manifest.json')
    original=h.read(frozen['paths']['reference_config']);document=frozen['document']
    oldcfg=frozen['component']._config('FW_E',frozen['parameters']['by_direction']['FW_E'])
    proto=copy.deepcopy(h.read(h.R/'phase_equilibrium181/protocol.json'))
    proto.update(previous_goal_turn='PROGRESS182: receiving/junction audit separates off request and shared restriction; fixed-parameter phase failure not a joint calibration limit.',
        hypothesis='Can a small joint cell refit restore discharge and control ranking under the new phase law, compared with the same refit budget for the old structure?',
        parameters=['rho_crit cells20/21 shared multiplier','acceleration_tau cells20/21 shared multiplier','merge_delta cell21 multiplier','merge_delta cell23 multiplier'],
        train='Only seed29 late four executed controls; do not fit67,43,61.',
        validation='67 late four controls;43 early none/VSL;61 late hold/release. Previously inspected records, not pristine blind.67 was used in historical132 calibration.',
        fit='One forward Jacobian at fixed132, each axis+5%; one box-constrained ridge least-squares step in [-.2,.2], evaluate full/half only. No restarts or validation-driven proposals.',
        budget=dict(parity450=2,training450_max=48,validation450_max=16,total450_max=66,new_native=0,FZP=0),
        score='Existing125 score: absolute component TTT/wait/endN/exits/4merges +.25 localN/v/q +2 all-pair response +.1 mean squared parameter departure. ControllerOmega objective unchanged.',
        gates='Train objective>=5%better and response not worse. Then frozen validation meaningful abs(DeltaTTT)>=.5 signs, response>=10%better, absolute<=110% relative fixed same structure, regret<=.5. Also compare against original baseline. No adoption from training alone.',
        no_future_observations=True)
    if spatial191:
        proto.update(previous_goal_turn='PROGRESS190: split20 alone passes conservation but fails450gain; fixed-coefficient failure does not answer local refitting.',
            hypothesis='Does limited re-identification of cell20 relaxation/pressure restore autonomous control response with spatial20, compared to the same fit for baseline?',
            parameters=['cell20 acceleration_tau multiplier','cell20 both anticipation branches shared multiplier'],
            source='Exact190attempt2 spatial20 or exact148 baseline,132 other coefficients and171prehead fix. No189priority,178phase or additional spatial divisions.',
            fit='One forward Jacobian at132, two axes+5%; one box-constrained ridge step in[-.2,.2], full andhalf only. Same budget bothstructures; no restarts or validation-led tuning.',
            budget=dict(parity450=2,training450_max=32,validation450_max=16,total450_max=50,new_native=0,FZP=0),
            prior_reviewed='Claude03 and121/122 joint-fit warning;16120nu_ge alone on158 failed;183newphase had different4axes; no repeat of those candidates.',
            limitations='Knownhistorical records;67 used in older132, not pristine blind. Only20 acceleration andsharedanticipation, not comprehensive refit or impossibility proof.')
    h.save(root/'protocol.json',proto)
    pins={str(Path(__file__)):h.sha(__file__),str(frozen['paths']['reference_config']):h.sha(frozen['paths']['reference_config'])}
    sources=h.R/'exit_spatial190/attempt2' if spatial191 else h.R/'phase_equilibrium181'
    fixedrows=h.read(sources/'forecast/rows.json')
    pins[str(sources/'forecast/rows.json')]=h.sha(sources/'forecast/rows.json')
    for name in ('executed_function_sources.json','spec.json','coefficients.json'):
        pins[str(sources/name)]=h.sha(sources/name)
    forecasts=0;started=time.perf_counter();evaluations=[];bindings=[];selected={};frozen_vectors={}

    def same_binding(a,b):
        if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(same_binding(v,b[k]) for k,v in a.items())
        if isinstance(a,(float,int)) and isinstance(b,(float,int)):return abs(a-b)<1e-10
        return a==b

    def residual(rows):
        absolute=[];local=[];response=[]
        for row in rows:
            a,p=row['actual'],row['predicted']
            absolute += [(p[k]-a[k])/s for k,s in [('ttt',5.),('ramp_ttt',1.),('off_ttt',1.),('end_n',40.),('exits',30.)]]
            absolute += [(p['merges'][r]-a['merges'][r])/20 for r in sorted(a['merges'])]
            local += [row['local_rmse'][k]/s for k,s in [('n',8.),('v',20.),('q',800.)]]
        for case in sorted({r['case'] for r in rows}):
            by={r['arm']:r for r in rows if r['case']==case}
            for aa,bb in itertools.combinations(sorted(by),2):
                a,b=by[aa],by[bb]
                for k,s in [('ttt',.5),('ramp_ttt',.5),('end_n',15.),('exits',15.)]:
                    real=b['actual'][k]-a['actual'][k]
                    response.append((b['predicted'][k]-a['predicted'][k]-real)/max(s,abs(real)))
                for r in sorted(a['actual']['merges']):
                    real=b['actual']['merges'][r]-a['actual']['merges'][r]
                    response.append((b['predicted']['merges'][r]-a['predicted']['merges'][r]-real)/max(10.,abs(real)))
        vector=np.array([v*math.sqrt(weight/len(group)) for weight,group in [(1.,absolute),(.25,local),(2.,response)] for v in group])
        assert abs(float(vector@vector)-h.losses(rows,[1.]*dimensions)['objective'])<1e-10
        return vector

    def evaluate(structure,z,tag,scope='train'):
        nonlocal forecasts
        folder=root/(structure+'_'+tag);folder.mkdir()
        config=copy.deepcopy(original)
        if spatial191:
            local=config['freeway']['state_response']['FW_E']['cell_overrides']['20']
            local['relaxation']['acceleration_sec']*=z[0]
            for branch in ('downstream_ge_local','downstream_lt_local'):local['anticipation'][branch]*=z[1]
        else:
            for i in (20,21):
                config['freeway']['physical_cell_fd']['FW_E'][str(i)]['rho_crit']*=z[0]
                config['freeway']['state_response']['FW_E']['cell_overrides'][str(i)]['relaxation']['acceleration_sec']*=z[1]
            for i,m in ((21,z[2]),(23,z[3])):config['freeway']['state_response']['FW_E']['cell_overrides'][str(i)]['delta_merge']*=m
        configpath=folder/'reference_config.json';h.save(configpath,config)
        manifest=copy.deepcopy(document)
        manifest['sources']['reference_config']=dict(path=configpath.relative_to(h.ROOT).as_posix(),sha256=h.sha(configpath))
        manifest['qualification']=('Unqualified191 spatial20 bounded local refit; exact190/148 source required, no production/native use.' if spatial191 else 'Unqualified183 bounded offline joint calibration; requires exact frozen process-local phase/baseline source. No production or native use.')
        h.save(folder/'manifest.json',manifest)
        new=lpr.load_sources(folder/'manifest.json')
        cfg=new['component']._config('FW_E',new['parameters']['by_direction']['FW_E'])
        assert new['parameters']==frozen['parameters']==context['parameters']
        for i in range(31):
            a=cfg.network.freeway_segment_params['FW_E'][i];b=oldcfg.network.freeway_segment_params['FW_E'][i]
            assert abs(a['rho_crit']-b['rho_crit']*(z[0] if not spatial191 and i in (20,21) else 1.))<1e-10
            assert 0<a['rho_crit']<cfg.network.rho_max
            aa=cell_state_response(cfg.network,'FW_E',i);bb=cell_state_response(oldcfg.network,'FW_E',i)
            expected=copy.deepcopy(bb)
            if spatial191:
                if i==20:
                    expected['relaxation']['acceleration_sec']*=z[0]
                    for branch in ('downstream_ge_local','downstream_lt_local'):expected['anticipation'][branch]*=z[1]
            else:
                if i in (20,21):expected['relaxation']['acceleration_sec']*=z[1]
                if i in (21,23):expected['delta_merge']*=z[2 if i==21 else 3]
            assert same_binding(aa,expected),(i,aa,expected)
            assert {k:v for k,v in a.items() if k!='rho_crit'}=={k:v for k,v in b.items() if k!='rho_crit'}
        assert cfg.network.freeway_segment_params['FW_W']==oldcfg.network.freeway_segment_params['FW_W']
        bindings.append(dict(tag=structure+'_'+tag,z=z,scope=scope,verified=True));h.save(root/'bindings.json',bindings)
        for name in ('executed_function_sources.json','spec.json','coefficients.json'):(folder/name).write_bytes((sources/name).read_bytes())
        h.save(folder/'protocol.json',proto);h.save(folder/'pins.json',{str(configpath):h.sha(configpath),str(folder/'manifest.json'):h.sha(folder/'manifest.json')})
        h.save(folder/'setting.json',dict(manifest=str(folder/'manifest.json'),structure=structure,records=scope))
        expected=1 if scope=='parity' else 4 if scope=='train' else 8
        assert forecasts+expected<=max_forecasts
        if spatial191:queue178(calibration191=folder)
        else:queue178(calibration183=folder)
        status=h.read(folder/'forecast/status.json');assert status['forecasts']==expected
        forecasts+=expected
        rows=[r for r in h.read(folder/'forecast/rows.json') if r['horizon']==450]
        if scope=='parity':
            for r in rows:
                filename=r['case']+'_'+r['arm']+'.json.gz'
                pred=h.read(folder/'forecast'/structure/filename);ref=h.read(sources/'forecast'/structure/filename)
                assert all(pred[k]==ref[k] for k in ('cells','flows','ports','ramps'))
        loss=h.losses(rows,z)
        result=dict(structure=structure,z=z,tag=tag,scope=scope,folder=str(folder),loss=loss,rows=rows)
        evaluations.append(result);h.save(root/'evaluations.json',evaluations)
        h.save(root/'status.json',dict(status='running',stage=structure+'_'+tag,forecasts=forecasts,seconds=time.perf_counter()-started))
        print('191' if spatial191 else '183',structure,tag,'score',loss['objective'],'response',loss['response'],'forecasts',forecasts,flush=True)
        return result

    def bounded_step(J,r):
        ridge=.1/dimensions
        A=J.T@J+ridge*np.eye(dimensions);b=-J.T@r;options=[]
        for codes in itertools.product((-1,0,1),repeat=dimensions):
            x=np.array(codes,dtype=float)*.2;free=[i for i,c in enumerate(codes) if c==0];fixed=[i for i,c in enumerate(codes) if c!=0]
            if free:x[free]=np.linalg.solve(A[np.ix_(free,free)],b[free]-A[np.ix_(free,fixed)]@x[fixed])
            if np.max(np.abs(x))<=.2+1e-10:options.append((float(np.linalg.norm(r+J@x)**2+ridge*(x@x)),x))
        _,x=min(options,key=lambda z:z[0]);g=A@x-b
        assert all((abs(x[i])<.2-1e-8 and abs(g[i])<1e-7) or (x[i]<=-.2+1e-8 and g[i]>=-1e-7) or (x[i]>=.2-1e-8 and g[i]<=1e-7) for i in range(dimensions))
        return x,g

    h.save(root/'status.json',dict(status='running',stage='parity',forecasts=0))
    try:
        for structure in structures:
            evaluate(structure,[1.]*dimensions,'parity','parity')
            rows=[r for r in fixedrows if r['horizon']==450 and r['mode']==structure and r['case']=='s29_late']
            assert len(rows)==4
            r0=residual(rows);base=h.losses(rows,[1.]*dimensions)
            probes=[]
            for axis in range(dimensions):
                z=[1.]*dimensions;z[axis]=1.05;probe=evaluate(structure,z,'axis'+str(axis));probes.append(residual(probe['rows']))
            J=np.column_stack([(v-r0)/.05 for v in probes]);step,gradient=bounded_step(J,r0)
            h.save(root/(structure+'_proposal.json'),dict(step=step.tolist(),gradient=gradient.tolist(),jacobian=J.tolist(),residual=r0.tolist(),norm_check=True,box_kkt=True))
            candidates=[]
            for factor,label in ((1.,'full'),(.5,'half')):
                z=(np.ones(dimensions)+factor*step).tolist()
                candidates.append(evaluate(structure,z,label))
            acceptable=[v for v in candidates if v['loss']['objective']<=.95*base['objective'] and v['loss']['response']<=base['response']+1e-12]
            best=min(acceptable,key=lambda v:v['loss']['objective']) if acceptable else None
            frozen_vectors[structure]=best['z'] if best else [1.]*dimensions
            selected[structure]=dict(train_qualified=bool(best),z=frozen_vectors[structure],tag=best['tag'] if best else 'fixed',fixed_loss=base,selected_loss=best['loss'] if best else base)
        # Freeze both selections BEFORE examining either validation result.
        h.save(root/'selection_frozen.json',selected)
        results={}
        for structure in structures:
            if selected[structure]['train_qualified']:
                trial=evaluate(structure,frozen_vectors[structure],'validation','validation');rows=trial['rows']
            else:rows=[r for r in fixedrows if r['mode']==structure and r['horizon']==450 and r['case']!='s29_late']
            fixed=[r for r in fixedrows if r['mode']==structure and r['horizon']==450 and r['case']!='s29_late']
            base=h.losses(fixed,[1.]*dimensions);loss=h.losses(rows,frozen_vectors[structure])
            regrets=[]
            for case in sorted({r['case'] for r in rows}):
                rs=[r for r in rows if r['case']==case];chosen=min(rs,key=lambda r:r['predicted']['ttt'])
                regrets.append(dict(case=case,chosen=chosen['arm'],regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in rs)))
            gates=dict(train=selected[structure]['train_qualified'],meaningful_signs=all(p['sign_correct'] for p in loss['pairs'] if p['meaningful']),
                response=loss['response']<=.9*base['response'],absolute=loss['absolute']<=1.1*base['absolute'],regret=all(z['regret']<=.5 for z in regrets))
            results[structure]=dict(gates=gates,passed=all(gates.values()),fixed_loss=base,loss=loss,regrets=regrets,rows=rows)
        h.save(root/'validation.json',results)
        h.save(root/'completion.json',dict(status='complete',forecasts=forecasts,seconds=time.perf_counter()-started,
            gates={k:v['gates'] for k,v in results.items()},adopted=False,full_goal='ACTIVE_NOT_QUALIFIED',native=0,FZP_reads=0,push=False))
        h.save(root/'status.json',dict(status='complete',forecasts=forecasts))
    except BaseException as e:
        h.save(root/'status.json',dict(status='failed',forecasts=forecasts,error=repr(e)));raise
    finally:
        for p,d in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(p)==d,p
        h.save(root/'preservation.json',dict(input_sha256=pins,protected_and_STOP=True))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--joint169',action='store_true')
    parser.add_argument('--prehead171',action='store_true')
    parser.add_argument('--merge173',action='store_true')
    parser.add_argument('--split175',action='store_true')
    parser.add_argument('--queue178',action='store_true')
    parser.add_argument('--transport-once179',action='store_true')
    parser.add_argument('--phase-equilibrium181',action='store_true')
    parser.add_argument('--flow-audit182',action='store_true')
    parser.add_argument('--calibrate183',action='store_true')
    parser.add_argument('--merge-priority189',action='store_true')
    parser.add_argument('--spatial190',action='store_true')
    parser.add_argument('--calibrate191',action='store_true')
    parser.add_argument('--sampling192',action='store_true')
    parser.add_argument('--characteristic195',action='store_true')
    args=parser.parse_args()
    if args.characteristic195:
        assert sum(bool(v) for v in vars(args).values())==1
        queue178(characteristic195=True)
    elif args.sampling192:
        assert sum(bool(v) for v in vars(args).values())==1
        queue178(sampling192=True)
    elif args.calibrate191:
        assert not any((args.calibrate183,args.queue178,args.transport_once179,args.phase_equilibrium181,args.flow_audit182,args.merge173,args.split175,args.joint169,args.prehead171,args.merge_priority189,args.spatial190))
        calibrate183(spatial191=True)
    elif args.merge_priority189 or args.spatial190:
        assert not any((args.calibrate183,args.queue178,args.transport_once179,args.phase_equilibrium181,args.flow_audit182,args.merge173,args.split175,args.joint169,args.prehead171))
        assert not (args.merge_priority189 and args.spatial190)
        queue178(merge_priority189=args.merge_priority189,spatial190=args.spatial190)
    elif args.calibrate183:
        assert not any((args.queue178,args.transport_once179,args.phase_equilibrium181,args.flow_audit182,args.merge173,args.split175,args.joint169,args.prehead171))
        calibrate183()
    elif args.queue178 or args.transport_once179 or args.phase_equilibrium181 or args.flow_audit182:
        assert not any((args.merge173,args.split175,args.joint169,args.prehead171))
        assert sum((args.queue178,args.transport_once179,args.phase_equilibrium181,args.flow_audit182))==1
        queue178(transport_once179=args.transport_once179,phase_equilibrium181=args.phase_equilibrium181,flow_audit182=args.flow_audit182)
    elif args.merge173 or args.split175:
        assert not (args.joint169 or args.prehead171)
        assert not (args.merge173 and args.split175)
        merge173(split175=args.split175)
    else:
        main(joint169=args.joint169,prehead171=args.prehead171)
