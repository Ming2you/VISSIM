"""Bridge completed response inputs into the selected checkout's sole plant.

Capture runs in a separate process against the historical input builder and
stops BEFORE its rollout/scoring. Prediction imports only the selected checkout.
Prediction commands do not start native runs or fit coefficients. The explicit
prepare-seed53 command freezes a finite new response test for the existing runner.
"""
import copy
import csv
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import pickletools
import io
import math
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT.parent/'control-full-review'
OUT=HERE/'congested_replay'


def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def read_primitive_capture(path, expected_sha):
    raw=Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected_sha
    allowed={'PROTO','FRAME','STOP','MARK','MEMOIZE','BINGET','LONG_BINGET',
        'NONE','NEWTRUE','NEWFALSE','BININT','BININT1','BININT2','LONG1','LONG4','BINFLOAT',
        'SHORT_BINUNICODE','BINUNICODE','BINUNICODE8','EMPTY_DICT','EMPTY_LIST','EMPTY_TUPLE',
        'APPEND','APPENDS','SETITEM','SETITEMS','TUPLE','TUPLE1','TUPLE2','TUPLE3'}
    assert all(op.name in allowed for op,arg,pos in pickletools.genops(raw)), 'Non-data capture opcode'
    class DataOnly(pickle.Unpickler):
        def find_class(self,*args):raise ValueError('Class/function resolution forbidden')
        def persistent_load(self,*args):raise ValueError('External reference forbidden')
    return DataOnly(io.BytesIO(raw)).load()


def capture():
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c
    data,ctx,_,_=c.inputs()
    prior=e.HERE/'legal_release2670'
    assert load(prior/'status.json')['stage']=='complete_response_validation'
    protocol=load(prior/'protocol.json')
    assert protocol['source_sha']==load(HERE/'selected/plant_n31_v2.json')['sources']['network']['sha256']
    ctx=list(copy.deepcopy(ctx));ctx[3]=protocol['port_profile']
    model=c.prior.one.base.load_base_model(data['rm'].geometry,e.HERE/'local_fd/candidate.json')
    OUT.mkdir(exist_ok=False)
    class Captured(BaseException): pass
    records=[]
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        commands={int(k):v for k,v in load(prior/f'{arm}_commands.json').items()}
        def intercept(*args,**kwargs):
            # Native future truth is scored only after model.rollout, which
            # this capture deliberately never enters.
            json.dumps([args,kwargs],allow_nan=False)
            payload=pickle.dumps((args,kwargs),protocol=5)
            path=OUT/(arm+'_input.pickle');path.write_bytes(payload)
            records.append(dict(arm=arm,input=path.name,sha256=sha(path),
                truth=str(prior/'observations'/arm),previous_native_result=str(prior/f'{arm}_result.json'),
                previous_prediction=str(prior/f'{arm}_prediction.json.gz'),
                command_sha256=sha(prior/f'{arm}_commands.json')))
            raise Captured()
        model.rollout=intercept
        try:
            c.prior.forecast(model,protocol['parameters'],data['rm'],data['rm'],2670.1,450,
                             *ctx[:-1],commands,True)
            raise AssertionError('Rollout input not captured')
        except Captured: pass
    save(OUT/'capture.json',dict(source_network=protocol['source_sha'],cutoff=2670.1,horizon=450,
        geometry_sha256=sha(data['rm'].folder/'geometry.json'),records=records,
        parameter_source=str(prior/'protocol.json'),parameter_sha256=sha(prior/'protocol.json'),
        builder_sources={str(p):sha(p) for p in (Path(c.prior.__file__),Path(c.prior.one.__file__),Path(__file__))},
        cutoff_truncation_assertion_passed=True,native_started=False,future_truth_read_for_prediction=False))
    print(json.dumps(dict(captured=len(records),folder=str(OUT))),flush=True)


def capture_response2220():
    """Reuse two completed common-state interventions; no native or fitting."""
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c
    data,ctx,_,_=c.inputs()
    ctx=list(copy.deepcopy(ctx))
    ctx[3]=load(HERE/'selected/port_gain/port_profile.json')
    parameters=load(HERE/'selected/port_gain/parameters.json')['parameters']
    network=load(HERE/'selected/plant_n31_v2.json')['sources']['network']['sha256']
    assert sha(c.prior.REF/'source/mtfc_s29_none.inpx')==network
    for seed in (29,43):
        destination=HERE/'baseline_reproduction_20260929'/f'component2220_s{seed}_inputs_v2'
        destination.mkdir(parents=True,exist_ok=False)
        initial=data['none'] if seed==29 else c.prior.ObservationData(e.r.HERE/'gain_response/seed43/none')
        native_path=e.HERE/f'source_cost_native{seed}/summary.json'
        native=load(native_path)
        assert all(r['trajectory_exact'] and r['native_signals_exact'] for r in native['rows'])
        observations=e.r.HERE/'observations' if seed==29 else e.HERE/'heldout43/observations'
        model=c.prior.one.base.load_base_model(initial.geometry,e.HERE/'local_fd/candidate.json')
        records=[]
        class Captured(BaseException):pass
        for arm in ('none','vsl','rm','both'):
            commands=c.exp.commands(arm,ctx[0],ctx[-1])
            command_path=destination/(arm+'_commands.json');save(command_path,commands)
            truth=initial.folder if arm=='none' else observations/arm
            measurement=next(r for r in native['rows'] if r['arm']==arm)
            def intercept(*args,**kwargs):
                json.dumps([args,kwargs],allow_nan=False)
                path=destination/(arm+'_input.pickle')
                path.write_bytes(pickle.dumps((args,kwargs),protocol=5))
                records.append(dict(arm=arm,input=path.name,sha256=sha(path),truth=str(truth),
                    command_sha256=sha(command_path),native_total_cost=dict(
                        internal_veh_h=measurement['native_network_ttt_veh_h'],
                        external_wait_veh_h=measurement['external_wait_veh_h'],
                        total_veh_h=measurement['network_tts_including_external_veh_h'])))
                raise Captured()
            model.rollout=intercept
            try:
                c.prior.forecast(model,parameters,initial,initial,2220.1,450,*ctx[:-1],commands,True)
                raise AssertionError('Rollout input not captured')
            except Captured:pass
        initials=[read_primitive_capture(destination/r['input'],r['sha256']) for r in records]
        assert all(a[0][0]==initials[0][0][0] and a[0][3]==initials[0][0][3]
                   and a[1]==initials[0][1] for a in initials)
        save(destination/'capture.json',dict(source_network=network,seed=seed,cutoff=2220.1,horizon=450,
            geometry_sha256=sha(initial.folder/'geometry.json'),records=records,
            native_cost_receipt=str(native_path),native_cost_receipt_sha256=sha(native_path),
            builder_sources={str(p):sha(p) for p in (Path(c.prior.__file__),Path(c.prior.one.__file__),Path(c.exp.__file__),Path(__file__))},
            common_initial_inputs_exact=True,cutoff_truncation_assertion_passed=True,
            native_started=False,future_truth_read_for_prediction=False,
            qualification='Previously inspected common-state response; different seeds, not blind holdout. Fixed g8/6/4 and bottleneck90 from2250, not full9000 ALINEA policy.'))
        print(json.dumps(dict(captured=len(records),seed=seed,folder=str(destination))),flush=True)


def capture_extended_nc_windows():
    """Capture seven clean, broader NC states with the existing causal builder."""
    import xml.etree.ElementTree as ET
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c;data,ctx,_,_=c.inputs();ctx=list(copy.deepcopy(ctx))
    ctx[3]=load(HERE/'selected/port_gain/port_profile.json')
    params=load(HERE/'selected/port_gain/parameters.json')['parameters']
    parent=HERE/'baseline_reproduction_20260929';cw=parent/'cellwise_calibration'
    out=cw/'expanded_nc_windows';out.mkdir(exist_ok=True)
    assert not (out/'capture.json').exists(), 'Reuse captured inputs'
    (out/'inputs').mkdir(exist_ok=True)
    assert not any((out/'inputs').iterdir()), 'Do not overwrite a partial capture'
    coverage=load(cw/'full_run_coverage_review.json');records=[];evidence=[];pins={}
    network=load(HERE/'selected/plant_n31_v2.json')['sources']['network']['sha256']
    canonical=Path(c.prior.REF/'source/mtfc_s29_none.inpx');assert sha(canonical)==network
    root=ET.parse(canonical).getroot()
    def tree(z):return (z.tag,tuple(sorted(z.attrib.items())),(z.text or '').strip(),tuple(tree(x) for x in z))
    class Captured(BaseException):pass
    for dataset in coverage['datasets']:
        seed=dataset['seed'];initial=c.prior.ObservationData(dataset['folder'])
        for name,digest in dataset['cache_sha256'].items():
            path=initial.folder/name;assert sha(path)==digest;pins[str(path)]=digest
        source=Path(f'D:/VISSIM_runs/20260924_bottleneck90_full_s{seed}/source/mtfc_s{seed}_none.inpx')
        receipt_path=source.parent.parent/'none/run/run.json';receipt=load(receipt_path)
        assert receipt['completed'] and receipt['finished'] and not receipt['owned_native_alive']
        assert receipt['terminal_sec']==9000 and receipt['exit_code']==receipt['fixed_profile_validation_exit_code']==0
        proof=receipt['fixed_profile_proof'];assert proof['event_rows']==0 and proof['native_resolution_probe']==10
        assert proof['network_sha256']==sha(source) and proof['seed']==seed
        prepared=Path(receipt['network']);prepared_receipt=Path(receipt['prepared'])/'prepared.json'
        assert sha(prepared_receipt)==receipt['prepared_sha256']
        assert sha(prepared)==proof['network_sha256']
        native=ET.parse(source).getroot();assert tree(native)==tree(ET.parse(prepared).getroot())
        seed_only=copy.deepcopy(native);seed_only.find('simulation').set('randSeed','29')
        assert tree(seed_only)==tree(root), 'NC differs beyond seed'
        legacy=Path(initial.geometry['source_network']['path']);oldroot=ET.parse(legacy).getroot()
        changed=sorted(k for k in {z.tag for z in root}|{z.tag for z in oldroot}
            if tree(root.find(k))!=tree(oldroot.find(k)))
        assert changed==['dataCollectionMeasurements','dataCollectionPoints','desSpeedDecisions']
        for p in (canonical,source,prepared,prepared_receipt,receipt_path,legacy):pins[str(p)]=sha(p)
        evidence.append(dict(seed=seed,network_sha256=sha(source),seed_only_difference=True,
            prepared_tree_exact=True,completed_native_sec=9000,no_control_events=True,
            legacy_geometry_source_differences=changed,legacy_geometry_physical_links_exact=True))
        model=c.prior.one.base.load_base_model(initial.geometry,e.HERE/'local_fd/candidate.json')
        commands=c.exp.commands('none',ctx[0],ctx[-1])
        assert all(set(h['greens'].values())=={10} and set(h['vsl'].values())=={110} for h in commands.values())
        for window in dataset['candidate_windows']:
            if not window['complete_with_no_recorded_accounting_issue']:continue
            t0=window['cutoff'];name=f's{seed}_t{int(t0)}';path=out/'inputs'/(name+'.pickle')
            def intercept(*args,**kwargs):
                assert kwargs['horizon_sec']==450 and kwargs['roads']==['FW_E']
                assert len(args[1])==450 and args[2]==params
                assert all(set(s['vsl_commands'].values())=={110} and
                    all(h['mode']=='OFF' for h in s['ramp_head_service'].values()) for s in args[1])
                json.dumps([args,kwargs],allow_nan=False)
                path.write_bytes(pickle.dumps((args,kwargs),protocol=5))
                raise Captured()
            model.rollout=intercept
            try:
                c.prior.forecast(model,params,initial,initial,t0,450,*ctx[:-1],commands,True)
                raise AssertionError('Capture must precede rollout/scoring')
            except Captured:pass
            records.append(dict(case=name,seed=seed,arm='none',cutoff=t0,horizon=450,input=str(path),
                sha256=sha(path),truth=str(initial.folder),source_network=network,
                actual_seed_network_sha256=sha(source),role='train_coverage' if seed==29 else 'inspected_check',
                future_truncation_exact=True,recorded_accounting_issue_veh=0))
    assert len(records)==7
    for p,digest in pins.items():assert sha(p)==digest
    pins[str(Path(__file__))]=sha(__file__)
    save(out/'capture.json',dict(records=records,network_evidence=evidence,pins=pins,
        builder_sources={str(p):sha(p) for p in (Path(c.prior.__file__),Path(c.prior.one.__file__))},
        excluded_windows=[dict(seed=d['seed'],**w) for d in coverage['datasets'] for w in d['candidate_windows']
            if not w['complete_with_no_recorded_accounting_issue']],
        scope='Seven NC states only, not paired intervention evidence. No future realized boundary input.',
        native_started=False,new_forecasts=0))
    print(json.dumps(dict(captured=len(records),future_truncation_exact=True)),flush=True)


def predict_extended_nc_windows():
    """Check frozen prior/159-cellwise candidates on wider NC state coverage."""
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    parent=HERE/'baseline_reproduction_20260929';cw=parent/'cellwise_calibration';out=cw/'expanded_nc_windows'
    assert not (out/'protocol.json').exists(), 'Do not repeat a prepared comparison'
    cap=load(out/'capture.json');selected=load(cw/'jacobian_step/selection.json')
    manifests={'prior':HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json',
        'cellwise':cw/'jacobian_step'/selected['selected']/'manifest.json'}
    core={str(ROOT/p):sha(ROOT/p) for p in load(cw/'protocol.json')['core_pins']}
    for p,digest in cap['pins'].items():assert sha(p)==digest
    protocol=dict(manifests={k:dict(path=str(p),sha256=sha(p)) for k,p in manifests.items()},
        core_pins=core,capture_sha256=sha(out/'capture.json'),maximum_new_rollouts=14,
        models_frozen_before_new_states=True,calibration=False,production_adopted=False,
        purpose='Determine whether the previous cellwise coefficients generalize across time before expanded calibration.',
        qualification='NC wider-state check only; no new control-pair ranking/fullOmega/SDMPC qualification.')
    save(out/'protocol.json',protocol);contexts={k:lpr.load_sources(p) for k,p in manifests.items()}
    records=cap['records'];payload={r['case']:read_primitive_capture(r['input'],r['sha256']) for r in records}
    observations={r['seed']:ObservationData(r['truth']) for r in records};results={};completed=0
    start=time.perf_counter()
    for version,context in contexts.items():
        folder=out/version;folder.mkdir(exist_ok=False);rows=[]
        for r in records:
            args,kwargs=copy.deepcopy(payload[r['case']]);assert args[2]==context['parameters']
            pred=context['component'].rollout(*args,**kwargs);completed+=1
            with gzip.open(folder/(r['case']+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            row=_cellwise_measure(context['component'],pred,r,observations[r['seed']]);rows.append(row)
            save(folder/(r['case']+'_result.json'),row)
            save(out/'status.json',dict(stage='running',completed=completed,last_case=r['case'],last_version=version))
            print(json.dumps(dict(version=version,case=r['case'],n_rmse=row['score']['cell_n']['rmse'],
                q_rmse=row['score']['flow_vph']['rmse'],v_rmse=row['score']['speed']['rmse'])),flush=True)
        results[version]=rows
    for p,digest in {**core,**cap['pins']}.items():assert sha(p)==digest
    comparisons=[]
    for base,new in zip(results['prior'],results['cellwise']):
        assert base['case']==new['case'] and base['actual']==new['actual']
        comparisons.append(dict(case=base['case'],metrics={k:{v:r['score'][k]['rmse'] for v,r in
            [('prior',base),('cellwise',new)]} for k in ('speed','cell_n','flow_vph','source_flow_vph')},
            ttt_actual=base['actual']['ttt'],ttt_prior=base['predicted']['ttt'],ttt_cellwise=new['predicted']['ttt']))
    save(out/'summary.json',dict(comparisons=comparisons,rows=results,completed=completed,
        wall_sec=time.perf_counter()-start,core_and_inputs_unchanged=True,fit=False,new_native=0,
        scope='East31+8connector,30s trapezoid; not fullOmega. NC does not establish intervention response.',
        production_adopted=False,gain_qualified=False))
    save(out/'status.json',dict(stage='complete',completed=completed,new_native=0,calibration=False))


def predict(*, manifest_path=None, output=None, input_dir=None, inflow_diagnostic=False):
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    manifest_path=Path(manifest_path) if manifest_path is not None else HERE/'selected/plant_n31_v2.json'
    destination=Path(output) if output is not None else OUT
    if output is not None:destination.mkdir(parents=True,exist_ok=False)
    context=lpr.load_sources(manifest_path)
    source=Path(input_dir) if input_dir is not None else OUT
    model=context['component'];manifest=load(source/'capture.json')
    assert context['document']['sources']['network']['sha256']==manifest['source_network']
    results=[];conditional_pins={}
    for row in manifest['records']:
        p=source/row['input'];assert sha(p)==row['sha256']
        args,kwargs=read_primitive_capture(p,row['sha256'])
        assert args[2]==context['parameters'], 'Selected coefficients differ; do not silently replace them'
        assert kwargs['roads']==['FW_E'] and kwargs['horizon_sec']==450
        if inflow_diagnostic:
            # Cause isolation only, following the existing response_balance
            # diagnostic. Future inflows are NOT deployable prediction inputs.
            truth=ObservationData(row['truth']);t0=manifest['cutoff'];counts={}
            event_path=truth.folder/'port_events.csv'
            with event_path.open(encoding='utf-8-sig',newline='') as f:
                for event in csv.DictReader(f):
                    if event['kind']=='arrival' and t0<float(event['time_s'])<=t0+450+1e-7:
                        key=(round(float(event['time_s']),6),event['connector'],int(event['lane']))
                        counts[key]=counts.get(key,0)+1
            for step in args[1]:
                delta=step['window_start_s']-t0
                end=round(t0+(int(math.floor((delta+1e-7)/30))+1)*30,6)
                step['source_demand_vph']['FW_E']=float(truth.flows[end,'FW_E',0]['source_admissions'])*120
                arrival_end=round(t0+(int(math.floor((delta+1e-7)/5))+1)*5,6)
                step['ramp_arrival_lane_profile']={}
                for mid,port in model.ramps.items():
                    if port['road']!='FW_E':continue
                    lanes=[[counts.get((arrival_end,str(port['connector']),lane),0)/5.]
                           for lane in range(1,port['lanes']+1)]
                    step['ramp_arrival_lane_profile'][mid]=lanes
                    step['ramp_arrival_vph'][mid]=sum(x[0] for x in lanes)*3600
            for path in (event_path,truth.folder/'flows_30s.csv'):
                conditional_pins[str(path)]=sha(path)
            assert abs(sum(s['source_demand_vph']['FW_E']/3600 for s in args[1])-
                sum(float(truth.flows[round(t0+d,6),'FW_E',0]['source_admissions']) for d in range(30,451,30)))<1e-7
        started=time.perf_counter();pred=model.rollout(*args,**kwargs)
        wall=time.perf_counter()-started
        with gzip.open(destination/(row['arm']+'_prediction.json.gz'),'wt',encoding='utf-8') as f:
            json.dump(pred,f,allow_nan=False)
        # Autonomous mode opens future observations only after its prediction.
        # Conditional diagnostic mode is explicitly excluded from qualification.
        truth=ObservationData(row['truth']);t0=manifest['cutoff']
        initial_n=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
        times=[round(t0+d,6) for d in range(0,451,30)]
        port_ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
        port_ids|={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
        observed_main={t:sum(x['n_veh'] for x in truth.cells[t] if x['road']=='FW_E') for t in times}
        observed_port={t:sum(float(truth.ports[t,c]['end_n_veh']) for c in port_ids) for t in times}
        predicted_main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
        predicted_port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
            sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
        assert observed_main[t0]==initial_n
        predicted_main[t0]=initial_n;predicted_port[t0]=observed_port[t0]
        integral=lambda values:sum((values[a]+values[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
        flows={}
        for label,records in [('predicted',pred['flows']),('actual',[dict(v,window_end_s=t)
                for (t,r,c),v in truth.flows.items() if r=='FW_E' and t0<t<=times[-1]])]:
            flows[label]={key:sum(float(x[key]) for x in records) for key in
                          ('source_admissions','off_departures','terminal_exits' if label=='predicted' else 'terminal_exits_inferred')}
        merges={r:sum(x['accepted_merge_veh'] for x in pred['ramps'] if x['ramp']==r) for r,v in model.ramps.items() if v['road']=='FW_E'}
        actual_merges={r:sum(float(truth.ports[t,str(model.ramps[r]['connector'])]['departures_veh']) for t in times[1:]) for r in merges}
        score=score_rollout(truth,t0,pred,'FW_E',include_source_boundary=True)
        assert not score['invalid']
        residual=max([abs(x['conservation_residual_veh']) for x in pred['ports']]+[abs(x['conservation_residual_veh']) for x in pred['ramps']])
        assert residual<1e-7
        native_cost=load(row['previous_native_result'])['native'] if 'previous_native_result' in row else row['native_total_cost']
        item=dict(arm=row['arm'],wall_sec=wall,score=score,conservation_max=residual,
            predicted_mainline_ttt=integral(predicted_main),actual_mainline_ttt=integral(observed_main),
            predicted_port_ttt=integral(predicted_port),actual_port_ttt=integral(observed_port),
            predicted_merge=merges,actual_merge=actual_merges,flows=flows,
            native_total_cost=native_cost)
        item['predicted_component_ttt']=item['predicted_mainline_ttt']+item['predicted_port_ttt']
        item['actual_component_ttt']=item['actual_mainline_ttt']+item['actual_port_ttt']
        results.append(item);save(destination/(row['arm']+'_result.json'),item)
        print(json.dumps(dict(arm=row['arm'],wall_sec=wall,predicted=item['predicted_component_ttt'],actual=item['actual_component_ttt'])),flush=True)
    base=results[0]
    for row in results:
        row['deltas']={k:row[k]-base[k] for k in ('predicted_component_ttt','actual_component_ttt','predicted_mainline_ttt','actual_mainline_ttt','predicted_port_ttt','actual_port_ttt')}
        row['deltas']['predicted_merge']=sum(row['predicted_merge'].values())-sum(base['predicted_merge'].values())
        row['deltas']['actual_merge']=sum(row['actual_merge'].values())-sum(base['actual_merge'].values())
    save(destination/'summary.json',dict(results=results,gain_qualified=False,calibration=False,
        source_capture=str(source/'capture.json'),source_capture_sha256=sha(source/'capture.json'),
        manifest=str(manifest_path),manifest_sha256=sha(manifest_path),
        scope='East31 cells plus8 ramp connectors; not full urban/Omega prediction',
        total_native_cost_scope='All network plus latent waiting; independent scope, not compared numerically to component prediction',
        independent_holdout=False,future_observed_inflow_inputs=inflow_diagnostic,
        conditional_only=inflow_diagnostic,conditional_source_pins=conditional_pins,
        source_file_pins={str(p):sha(p) for p in
            (Path(lpr.__file__),Path(sys.modules[model.__class__.__module__].__file__),manifest_path,Path(__file__))}))


def audit_saved_vsl_discharge():
    """Locate current VSL response errors using saved states/flows only."""
    parent=HERE/'baseline_reproduction_20260929'
    out=parent/'spatial_vsl_response';out.mkdir(exist_ok=True)
    assert not (out/'summary.json').exists(), 'Reuse completed spatial audit'
    results={};pins={};verification=[]
    for seed in (29,43):
        capture_path=parent/f'component2220_s{seed}_inputs_v2/capture.json'
        manifest=load(capture_path);pins[str(capture_path)]=sha(capture_path)
        t0=manifest['cutoff'];times=[round(t0+30*j,6) for j in range(16)]
        data={};cost_checks={};geometry=None
        for arm in ('none','vsl'):
            record=next(r for r in manifest['records'] if r['arm']==arm)
            truth=Path(record['truth']);proof=load(truth/'manifest.json')
            native={}
            for name,time_key in [('cells_30s.csv','time_s'),('flows_30s.csv','window_end_s')]:
                path=truth/name;pins[str(path)]=sha(path)
                if 'files' in proof:
                    assert pins[str(path)]==proof['files'][name]
                    verification.append(dict(path=str(path),proof='native extraction manifest SHA'))
                else:
                    assert seed==43 and arm=='none' and proof['seed']==43
                    prior=load(parent/'component2220_s43_conditional_inflow/summary.json')['conditional_source_pins']
                    if name=='flows_30s.csv':
                        assert pins[str(path)]==prior[str(path)]
                        basis='previous conditional audit SHA'
                    else:
                        basis='No prior per-file SHA in native manifest; current hash and exact prior mainline TTT checked only'
                    verification.append(dict(path=str(path),proof=basis))
                with path.open(encoding='utf-8-sig',newline='') as f:
                    native[name]={(round(float(r[time_key]),6),int(r['cell'])):r
                        for r in csv.DictReader(f) if r['road']=='FW_E' and t0<=float(r[time_key])<=times[-1]}
            initial={c:native['cells_30s.csv'][t0,c] for c in range(31)}
            if geometry is None:
                geometry=load(truth/'geometry.json');pins[str(truth/'geometry.json')]=sha(truth/'geometry.json')
            data['actual',arm]=(native['cells_30s.csv'],native['flows_30s.csv'])
            folders={'current':parent/f'component2220_s{seed}_current_v2',
                     'observed_inflow_diagnostic':parent/f'component2220_s{seed}_conditional_inflow',
                     'rejected_E4':parent/'vsl_E4_countercheck'/f's{seed}_early'}
            for version,folder in folders.items():
                p=folder/(arm+'_prediction.json.gz');pins[str(p)]=sha(p)
                with gzip.open(p,'rt',encoding='utf-8') as f:pred=json.load(f)
                cells={(round(r['time_s'],6),int(r['cell'])):r for r in pred['cells']}
                cells.update({(t0,c):r for c,r in initial.items()})
                flows={(round(r['window_end_s'],6),int(r['cell'])):r for r in pred['flows']}
                data[version,arm]=(cells,flows)
                cost_checks[version,arm]=load(folder/(arm+'_result.json'))
        assert all(data['actual','none'][0][t0,c]==data['actual','vsl'][0][t0,c] for c in range(31))
        rows=[];blocks=[]
        for cell in range(31):
            row=dict(cell=cell,initial=data['actual','none'][0][t0,cell],
                     geometry=next(z for z in geometry['cells'] if z['road']=='FW_E' and z['cell']==cell))
            for version in ('actual',*folders):
                values={}
                for arm in ('none','vsl'):
                    cells,flows=data[version,arm]
                    values[arm]=dict(ttt=sum((float(cells[a,cell]['n_veh'])+float(cells[b,cell]['n_veh']))*(b-a)/7200 for a,b in zip(times,times[1:])),
                        final_stock=float(cells[times[-1],cell]['n_veh']))
                    for key in ('downstream_crossings','source_admissions','ramp_merges','off_departures','terminal_exits'):
                        field='terminal_exits_inferred' if version=='actual' and key=='terminal_exits' else key
                        values[arm][key]=sum(float(flows[t,cell][field]) for t in times[1:])
                    for block in range(3):
                        stamps=times[1+block*5:6+block*5]
                        blocks.append(dict(cell=cell,version=version,arm=arm,start=times[block*5],end=stamps[-1],
                            downstream_crossings=sum(float(flows[t,cell]['downstream_crossings']) for t in stamps),
                            end_stock=float(cells[stamps[-1],cell]['n_veh']),
                            mean_speed=sum(float(cells[t,cell]['v_kmh']) for t in stamps)/5))
                row[version]=dict(arms=values,delta={k:values['vsl'][k]-values['none'][k] for k in values['none']})
            rows.append(row)
        summary={}
        for version in ('actual',*folders):
            total={k:sum(r[version]['delta'][k] for r in rows) for k in rows[0][version]['delta']}
            ref=cost_checks['current' if version=='actual' else version,'vsl']
            base=cost_checks['current' if version=='actual' else version,'none']
            key='actual_mainline_ttt' if version=='actual' else 'predicted_mainline_ttt'
            assert abs(total['ttt']-(ref[key]-base[key]))<1e-7
            summary[version]=dict(total=total,
                upstream0_14_delta_ttt=sum(r[version]['delta']['ttt'] for r in rows if r['cell']<15),
                control_region15_30_delta_ttt=sum(r[version]['delta']['ttt'] for r in rows if r['cell']>=15))
        results[str(seed)]=dict(summary=summary,cells=rows,blocks=blocks)
    save(out/'summary.json',dict(seeds=results,source_pins=pins,source_verification=verification,new_rollouts=0,new_native=0,
        future_inputs_for_prediction=False,coefficient_changes=0,ttt_reconstruction_exact=True,
        scope='East31 mainline cells, same initial state per seed,30s trapezoids. Ports/urban/outside are excluded here.',
        limits=['Observed-inflow series is a previously labeled future-conditioned diagnostic, not autonomous validation.',
                'Spatial cost/flow localization is accounting, not proof of an independent causal mechanism.',
                'Previously examined seeds29/43; not pristine holdouts.']))
    print(json.dumps({s:r['summary'] for s,r in results.items()},ensure_ascii=False),flush=True)


def audit_early_control_flow_ledger():
    """Exact 30s conservation accounting, not counterfactual forcing or causal attribution."""
    parent=HERE/'baseline_reproduction_20260929';out=parent/'early_control_flow_ledger'
    out.mkdir(exist_ok=False);pins={};seeds={};checks=[]
    joint=parent/'cellwise_calibration/jacobian_step'
    selection=load(joint/'selection.json');assert load(joint/'status.json')['stage']=='complete_jacobian_step'
    fields={'source':('source_admissions',1),'merge':('ramp_merges',1),
        'off_entry':('off_departures',-1),'terminal':('terminal_exits',-1)}
    frozen=load(parent/'cellwise_calibration/protocol.json')['truth_file_pins']
    for seed in (29,43):
        receipt=parent/f'component2220_s{seed}_inputs_v2/capture.json';capture=load(receipt);pins[str(receipt)]=sha(receipt)
        t0=capture['cutoff'];times=[round(t0+30*i,6) for i in range(16)];data={};geometry=None
        for arm in ('none','vsl','rm','both'):
            record=next(x for x in capture['records'] if x['arm']==arm);truth=Path(record['truth']);native={}
            for name,time_key in [('cells_30s.csv','time_s'),('flows_30s.csv','window_end_s')]:
                path=truth/name;digest=sha(path);assert digest==frozen[str(path)];pins[str(path)]=digest
                with path.open(encoding='utf-8-sig',newline='') as f:
                    native[name]={(round(float(r[time_key]),6),int(r['cell'])):r for r in csv.DictReader(f)
                        if r['road']=='FW_E' and t0<=float(r[time_key])<=times[-1]}
            cells={key:float(r['n_veh']) for key,r in native['cells_30s.csv'].items()}
            flows={key:{**r,'terminal_exits':float(r['terminal_exits_inferred'])} for key,r in native['flows_30s.csv'].items()}
            for (t,c),row in flows.items():
                if t<=t0:continue
                assert all(float(row[k])==0 for k in ('unexplained_entries','unexplained_losses','native_removals')),(seed,arm,t,c)
            data['actual',arm]=(cells,flows)
            if geometry is None:geometry=load(truth/'geometry.json')
            folders={'prior':parent/f'component2220_s{seed}_current_v2','joint':joint/selection['selected'] if seed==29 else joint/'check43'}
            for version,folder in folders.items():
                filename=f's29_early_{arm}_prediction.json.gz' if version=='joint' and seed==29 else arm+'_prediction.json.gz'
                path=folder/filename;pins[str(path)]=sha(path)
                with gzip.open(path,'rt',encoding='utf-8') as f:prediction=json.load(f)
                pc={(round(r['time_s'],6),int(r['cell'])):float(r['n_veh']) for r in prediction['cells']}
                pc.update({(t0,c):cells[t0,c] for c in range(31)})
                pf={(round(r['window_end_s'],6),int(r['cell'])):r for r in prediction['flows']}
                data[version,arm]=(pc,pf)
        for arm in ('vsl','rm','both'):
            assert all(data['actual',arm][0][t0,c]==data['actual','none'][0][t0,c] for c in range(31))
        # Every cell/interval, not only global cancellation, must close.
        maximum=0.
        for (version,arm),(cells,flows) in data.items():
            for a,b in zip(times,times[1:]):
                for c in range(31):
                    f=flows[b,c];up=0. if c==0 else float(flows[b,c-1]['downstream_crossings'])
                    change=up-float(f['downstream_crossings'])+sum(sign*float(f[field]) for field,sign in fields.values())
                    residual=abs(cells[b,c]-cells[a,c]-change);maximum=max(maximum,residual)
                    assert residual<1e-7,(seed,version,arm,b,c,residual)
        checks.append(dict(seed=seed,cell_interval_checks=12*15*31,max_conservation_residual=maximum,unexplained_events_zero=True,common_initial_counts_exact=True))
        rows=[]
        for arm in ('vsl','rm','both'):
            for version in ('actual','prior','joint'):
                c0,f0=data[version,'none'];c1,f1=data[version,arm]
                weights={t:(times[-1]-t+15)/3600 for t in times[1:]}
                totals={};terms={};cells=[];exits={}
                for name,(field,sign) in fields.items():
                    totals[name]=sum(float(f1[t,c][field])-float(f0[t,c][field]) for t in times[1:] for c in range(31))
                    terms[name]=sign*sum((float(f1[t,c][field])-float(f0[t,c][field]))*weights[t] for t in times[1:] for c in range(31))
                for c in range(31):
                    delta_ttt=sum((c1[a,c]-c0[a,c]+c1[b,c]-c0[b,c])*(b-a)/7200 for a,b in zip(times,times[1:]))
                    counts={name:sum(float(f1[t,c][field])-float(f0[t,c][field]) for t in times[1:]) for name,(field,_) in fields.items()}
                    cell_geometry=next(r for r in geometry['cells'] if r['road']=='FW_E' and r['cell']==c)
                    cells.append(dict(cell=c,delta_ttt=delta_ttt,end_n_delta=c1[times[-1],c]-c0[times[-1],c],
                        counts=counts,downstream_delta=sum(float(f1[t,c]['downstream_crossings'])-float(f0[t,c]['downstream_crossings']) for t in times[1:]),
                        physical_pieces=cell_geometry['physical_pieces']))
                    if c in (9,11,18,20,30):exits[str(c)]={k:counts[k] for k in ('off_entry','terminal')}
                total=sum(r['delta_ttt'] for r in cells)
                assert abs(total-sum(terms.values()))<1e-7,(seed,arm,version,total,terms)
                series=[]
                for t in times[1:]:
                    series.append(dict(time_s=t,delta_total_n=sum(c1[t,c]-c0[t,c] for c in range(31)),
                        interval_deltas={name:sum(float(f1[t,c][field])-float(f0[t,c][field]) for c in range(31)) for name,(field,_) in fields.items()}))
                rows.append(dict(arm=arm,version=version,mainline_delta_ttt=total,signed_ttt_terms=terms,flow_deltas=totals,
                    exits_by_cell=exits,cells=cells,series=series))
        cost_path=OLD/f'diagnostics/metanet_net_gain_goal_20260924/source_cost_native{seed}/summary.json';native_cost=load(cost_path);pins[str(cost_path)]=sha(cost_path)
        assert all(r['trajectory_exact'] and r['native_signals_exact'] for r in native_cost['rows'])
        seeds[str(seed)]=dict(rows=rows,native_whole_network_cost_deltas={r['arm']:r['delta'] for r in native_cost['rows']},
            native_cost_scope='All network + latent waiting, separately measured cumulative counters; not the East31 ledger or Omega definition.')
    result=dict(seeds=seeds,checks=checks,source_pins=pins,new_rollouts=0,new_native=0,coefficient_changes=0,
        definition='DeltaTTT_main=sum over30s windows and cells of signed delta boundary volume * (horizon_end-window_end+15)/3600. Exact for the same30s trapezoidal stock metric, assuming equal initial stocks and closed cell ledgers.',
        scope='East31 mainline cells only. Off_entry is a mainline exit into the connector, NOT Omega TTD. Ramp/urban/outside waits are excluded from this ledger.',
        causal_limit='Terms are a conservation identity, not isolated causal effects. Controls can change source admission timing, arrivals and subsequent exits jointly. Do not subtract a term and call the remainder a counterfactual control benefit.',
        no_future_truth_prediction_inputs=True)
    save(out/'summary.json',result)
    print(json.dumps({seed:[dict(arm=r['arm'],version=r['version'],ttt=r['mainline_delta_ttt'],terms=r['signed_ttt_terms']) for r in item['rows']] for seed,item in seeds.items()}),flush=True)


def audit_early_rm_timing():
    """Timing and spatial response from cached tables; no causal coefficient fit."""
    from collections import Counter
    parent=HERE/'baseline_reproduction_20260929';out=parent/'early_control_flow_ledger/rm_timing.json'
    assert not out.exists(), 'Reuse completed timing audit'
    pins={};results=[];t0=2220.1;start=2250.1;end=2670.1;con_cells={'10639':10,'10681':12,'10490':21,'10484':23}
    for seed in (29,43):
        capture=load(parent/f'component2220_s{seed}_inputs_v2/capture.json');data={}
        for arm in ('none','rm'):
            record=next(r for r in capture['records'] if r['arm']==arm);folder=Path(record['truth']);tables={}
            for name in ('port_events.csv','cells_30s.csv','flows_30s.csv','ports_30s.csv'):
                path=folder/name;pins[str(path)]=sha(path)
                with path.open(encoding='utf-8-sig',newline='') as f:tables[name]=list(csv.DictReader(f))
            data[arm]=tables
        ramps=[]
        for con,cell in con_cells.items():
            event={a:[r for r in d['port_events.csv'] if r['connector']==con and float(r['time_s'])<=end] for a,d in data.items()}
            # Membership before the intervention is shared; new IDs after it are never matched.
            key=lambda r:tuple(r.get(k,'') for k in ('time_s','vehicle','kind','lane','position_m','speed_kmh'))
            assert sorted(key(r) for r in event['none'] if float(r['time_s'])<=start)==sorted(key(r) for r in event['rm'] if float(r['time_s'])<=start)
            initial={};departures={};counts={}
            for arm,rows in event.items():
                pending=set()
                for r in rows:
                    if float(r['time_s'])>start:continue
                    if r['kind']=='arrival':pending.add(r['vehicle'])
                    else:pending.remove(r['vehicle'])
                observed=next(r for r in data[arm]['ports_30s.csv'] if r['connector']==con and abs(float(r['window_end_s'])-start)<1e-6)
                assert len(pending)==float(observed['end_n_veh'])
                initial[arm]=pending;dd={}
                for r in rows:
                    if r['kind']=='departure' and start<float(r['time_s'])<=end and r['vehicle'] in pending:
                        assert r['vehicle'] not in dd;dd[r['vehicle']]=r
                departures[arm]=dd
                counts[arm]=Counter(round(float(r['time_s']),6) for r in rows if r['kind']=='departure' and t0<float(r['time_s'])<=end)
            assert initial['none']==initial['rm']
            paired=[]
            for vehicle in sorted(departures['none'].keys()&departures['rm'].keys(),key=int):
                a=departures['none'][vehicle];b=departures['rm'][vehicle]
                paired.append(dict(vehicle=vehicle,none_upper_s=float(a['time_s']),rm_upper_s=float(b['time_s']),
                    delta_upper_s=float(b['time_s'])-float(a['time_s']),
                    delta_last_connector_sample_speed_kmh=float(b['speed_kmh'])-float(a['speed_kmh'])))
            bins=[];cumulative=0
            for j in range(1,91):
                t=round(t0+5*j,6);delta=counts['rm'][t]-counts['none'][t];cumulative+=delta
                bins.append(dict(end_s=t,none=counts['none'][t],rm=counts['rm'][t],delta=delta,cumulative_delta=cumulative))
            ramps.append(dict(connector=con,merge_cell=cell,common_precontrol_port_stock=len(initial['none']),
                paired_completed=paired,remaining={a:len(initial[a]-departures[a].keys()) for a in initial},
                count_bins_5s=bins,first_count_difference=next((r for r in bins if r['delta']),None)))
        cellmap={a:{(round(float(r['time_s']),6),int(r['cell'])):r for r in d['cells_30s.csv'] if r['road']=='FW_E'} for a,d in data.items()}
        flowmap={a:{(round(float(r['window_end_s']),6),int(r['cell'])):r for r in d['flows_30s.csv'] if r['road']=='FW_E'} for a,d in data.items()}
        spatial=[]
        for cell in range(31):
            series=[];cumulative=0.
            for j in range(1,16):
                t=round(t0+30*j,6);a=cellmap['none'][t,cell];b=cellmap['rm'][t,cell];fa=flowmap['none'][t,cell];fb=flowmap['rm'][t,cell]
                dq=float(fb['downstream_crossings'])-float(fa['downstream_crossings']);cumulative+=dq
                series.append(dict(time_s=t,delta_n=float(b['n_veh'])-float(a['n_veh']),
                    delta_v=float(b['v_kmh'])-float(a['v_kmh']) if a['v_kmh'] and b['v_kmh'] else None,
                    delta_downstream_crossings=dq,cumulative_downstream_delta=cumulative,
                    delta_merge=float(fb['ramp_merges'])-float(fa['ramp_merges'])))
            spatial.append(dict(cell=cell,series=series))
        results.append(dict(seed=seed,ramps=ramps,spatial=spatial,precontrol_events_exact=True))
    save(out,dict(rows=results,source_pins=pins,new_rollouts=0,new_native=0,coefficients_changed=False,
        caveat='Departure time lies in(lower,upper], width5s. Stored departure speed is the LAST CONNECTOR sample, not exact crossing speed or downstream speed. Only vehicles present in the same connector at2250.1 are paired. Completed-pair conditioning and coarse timing prevent causal speed/variance attribution. Spatial and temporal differences are descriptive outcomes, never future model inputs.'))
    print(json.dumps([dict(seed=r['seed'],ramps=[dict(connector=x['connector'],common_stock=x['common_precontrol_port_stock'],paired=len(x['paired_completed']),first_count=x['first_count_difference']) for x in r['ramps']]) for r in results]),flush=True)


def audit_cellwise_receiving_contract():
    """Inspect saved min operands; no rollout, coefficient change, or future forcing."""
    import inspect
    from evaluation.controllers import lane_plant_runtime as lpr
    from src.models import metanet as mn
    from src.models.state import ControlAction
    parent=HERE/'baseline_reproduction_20260929';joint=parent/'cellwise_calibration/jacobian_step'
    out=parent/'early_control_flow_ledger/receiving_contract.json'
    assert not out.exists(), 'Reuse completed receiving audit'
    protocol=load(joint/'protocol.json')
    for path,digest in protocol['core_pins'].items():assert sha(ROOT/path)==digest
    flow_ledger=load(out.parent/'summary.json');selection=load(joint/'selection.json')
    manifests={'prior':HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json',
               'joint':joint/selection['selected']/'manifest.json'}
    result=dict(versions={},source_pins={},new_rollouts=0,new_native=0,production_changed=False,
        scope='Same saved autonomous450s runs. Receiving bounds compare only replacing global critical density by the nominal local value in the existing ramp query, at unchanged states. No VSL-dependent receiving law is assumed.',
        bound='Old canonical query is min(ramp cap, qcap*clip((jam-rho)/(jam-global_critical),0,1)). Local candidate rescales the unclipped factor by (jam-global_critical)/(jam-local_critical). If old query equals ramp cap, only an interval is known. Apply the same saved gap cap to both bounds.',
        causal_limit='Equal budget bounds exclude this nominal-density wiring as an instantaneous budget cause on these saved states. Nonzero bounds do not establish a control benefit or an autonomous result.')
    for version,manifest in manifests.items():
        ctx=lpr.load_sources(manifest);model=ctx['component'];cfg=model._config('FW_E',ctx['parameters']['by_direction']['FW_E']);net=cfg.network
        assert not model.lane_groups_enabled and not getattr(net,'vsl_fd_two_branch',False)
        control=ControlAction.uncontrolled(cfg);critical=[]
        for i,p in enumerate(net.freeway_segment_params['FW_E']):
            value=mn.effective_rho_crit(net,mn.segment_vsl(control,'FW_E',i,cfg))
            critical.append(dict(cell=i,local=p['rho_crit'],receiving=value))
        assert all(r['receiving']==net.rho_crit for r in critical)
        rows=[]
        for seed in (29,43):
            folder=(parent/f'component2220_s{seed}_current_v2') if version=='prior' else (joint/selection['selected'] if seed==29 else joint/'check43')
            for arm in ('none','vsl','rm','both'):
                filename=f's29_early_{arm}_prediction.json.gz' if version=='joint' and seed==29 else arm+'_prediction.json.gz'
                path=folder/filename;digest=sha(path);assert digest==flow_ledger['source_pins'][str(path)];result['source_pins'][str(path)]=digest
                with gzip.open(path,'rt',encoding='utf-8') as f:prediction=json.load(f)
                for ramp in net.ramps:
                    samples=[r for r in prediction['ramps'] if r['ramp']==ramp];assert len(samples)==450
                    cap=net.ramp_capacity_veh_h[ramp];i=net.ramp_merge_segment_index[ramp]
                    local=net.freeway_segment_params['FW_E'][i]['rho_crit'];ratio=(net.rho_max-net.rho_crit)/(net.rho_max-local)
                    assert net.freeway_capacity_veh_h>cap and 0<local<net.rho_max
                    uncertain=[];density_limited=0;gap_limited=0;accepted=0.;eligible=0.;budget=0.
                    for r in samples:
                        node=r['receiving_node'];old=node['unlimited_node_canonical_budget_vph'];gap=node['gap_supply_vph_per_lane']*model.ramps[ramp]['lanes'];current=min(old,gap)
                        assert abs(current-r['canonical_receiving_budget_vph'])<1e-7
                        if old<cap-1e-7:
                            density_limited+=1;lo=hi=min(cap,old*ratio)
                        else:
                            assert abs(old-cap)<1e-7
                            lo=min(cap,cap*ratio);hi=cap
                        lo=min(lo,gap);hi=min(hi,gap)
                        if max(abs(lo-current),abs(hi-current))>1e-7:
                            uncertain.append(dict(start_sec=r['start_sec'],old_vph=current,local_lower_vph=lo,local_upper_vph=hi))
                        gap_limited+=gap<old-1e-7;accepted+=r['accepted_merge_veh'];eligible+=r['eligible_merge_veh'];budget+=r['receiving_budget_veh']
                    rows.append(dict(seed=seed,arm=arm,ramp=ramp,cell=i,local_critical=local,global_critical=net.rho_crit,
                        samples=len(samples),old_density_limited_samples=density_limited,gap_limited_samples=gap_limited,
                        guaranteed_same_budget_samples=len(samples)-len(uncertain),possibly_different_budget_samples=len(uncertain),
                        possible_budget_change_upper_veh=sum(max(abs(x['local_lower_vph']-x['old_vph']),abs(x['local_upper_vph']-x['old_vph']))/3600 for x in uncertain),
                        accepted_merge_veh=accepted,sum_eligible_query_veh=eligible,offered_budget_veh=budget,examples=uncertain[:3]))
        result['versions'][version]=dict(manifest=str(manifest),manifest_sha256=sha(manifest),critical_by_cell=critical,
            receiving_function_source=inspect.getsource(mn.effective_rho_crit),rows=rows)
    save(out,result)
    print(json.dumps({v:dict(samples=sum(r['samples'] for r in data['rows']),possibly_changed=sum(r['possibly_different_budget_samples'] for r in data['rows']),
        density_limited=sum(r['old_density_limited_samples'] for r in data['rows']),gap_limited=sum(r['gap_limited_samples'] for r in data['rows'])) for v,data in result['versions'].items()}),flush=True)


def audit_saved_vsl_speed_terms():
    """Record four canonical150s prefixes, asserting saved450s parity."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.sdmpc_n31_20260924.integration_20260926.probe_selected_arrival_path import observe_first_interval_speed_terms
    parent=HERE/'baseline_reproduction_20260929'
    out=parent/'spatial_vsl_response/speed_terms'
    out.mkdir(exist_ok=True)
    assert not (out/'summary.json').exists(), 'Reuse completed term audit'
    manifest=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    context=lpr.load_sources(manifest);model=context['component']
    rows=[];checks=[]
    pins={str(manifest):sha(manifest),str(Path(__file__)):sha(Path(__file__)),
          str(Path(sys.modules[observe_first_interval_speed_terms.__module__].__file__)):sha(Path(sys.modules[observe_first_interval_speed_terms.__module__].__file__))}
    save(out/'protocol.json',dict(max_new_prefix_replays=4,horizon_sec=150,
        coefficient_changes=0,future_prediction_inputs=False,new_native=0,
        cases=['s29_none','s29_vsl','s43_none','s43_vsl'],
        purpose='Observe executed equation terms with existing VSL exposure and dynamic off-ramp storage, then require exact saved prefix parity.',pins=pins))
    for seed in (29,43):
        source=parent/f'component2220_s{seed}_inputs_v2'
        capture=load(source/'capture.json');pins[str(source/'capture.json')]=sha(source/'capture.json')
        for arm in ('none','vsl'):
            rec=next(r for r in capture['records'] if r['arm']==arm)
            args,kwargs=read_primitive_capture(source/rec['input'],rec['sha256'])
            assert args[2]==context['parameters'] and kwargs['horizon_sec']==450
            args=list(args);args[1]=args[1][:150];kwargs['horizon_sec']=150
            terms=[];started=time.perf_counter()
            prefix_path=out/f's{seed}_{arm}_prefix.json.gz'
            reused=prefix_path.exists()
            if reused:
                with gzip.open(prefix_path,'rt',encoding='utf-8') as f:cached=json.load(f)
                prediction,terms=cached['prediction'],cached['terms']
            else:
                with observe_first_interval_speed_terms(capture['cutoff'],terms):
                    prediction=model.rollout(*args,**kwargs)
                # Saved reference JSON has stringified integer lane-dict keys.
                # Compare both in that same serialization; no numeric rounding.
                prediction=json.loads(json.dumps(prediction,allow_nan=False))
                with gzip.open(prefix_path,'wt',encoding='utf-8') as f:
                    json.dump(dict(prediction=prediction,terms=terms),f,allow_nan=False)
            pins[str(prefix_path)]=sha(prefix_path)
            reference_path=parent/f'component2220_s{seed}_current_v2/{arm}_prediction.json.gz'
            pins[str(reference_path)]=sha(reference_path)
            with gzip.open(reference_path,'rt',encoding='utf-8') as f:reference=json.load(f)
            end=capture['cutoff']+150
            for key,time_key in [('cells','time_s'),('flows','window_end_s'),('ports','time_s'),('ramps','end_sec')]:
                expected=[r for r in reference[key] if r[time_key]<=end+1e-7]
                if prediction[key]!=expected:
                    difference=next(((a,b) for a,b in zip(prediction[key],expected) if a!=b),None)
                    save(out/f's{seed}_{arm}_prefix_failure.json',dict(key=key,
                        observed_length=len(prediction[key]),expected_length=len(expected),first_difference=difference))
                assert prediction[key]==expected,(seed,arm,key,'observer/prefix drift')
            assert len(terms)==150*19,(seed,arm,len(terms))
            path=out/f's{seed}_{arm}_terms.json.gz'
            with gzip.open(path,'wt',encoding='utf-8') as f:json.dump(terms,f,allow_nan=False)
            pins[str(path)]=sha(path)
            rows.extend(dict(seed=seed,arm=arm,**r) for r in terms)
            checks.append(dict(seed=seed,arm=arm,wall_sec=time.perf_counter()-started,reused_prefix=reused,terms=len(terms),
                exact_arrays=['cells','flows','ports','ramps']))
            save(out/'partial_checks.json',checks)
            print(json.dumps(checks[-1]),flush=True)
    groups=[]
    for seed in (29,43):
        for arm in ('none','vsl'):
            for cell in range(15,22):
                for start,end in [(0,30),(30,90),(90,150)]:
                    selected=[r for r in rows if r['seed']==seed and r['arm']==arm and r['cell']==cell
                              and 2220.1+start-1e-7<=r['time_sec']<2220.1+end-1e-7]
                    metrics=['speed_before','rho','downstream_rho','desired','relaxation','convection','anticipation',
                             'lane_drop_raw','after_speed_equation','speed_final','post_equation_change','delta_lanes']
                    groups.append(dict(seed=seed,arm=arm,cell=cell,start_sec=start,end_sec=end,samples=len(selected),
                        means={k:sum(r[k] for r in selected)/len(selected) for k in metrics}))
    save(out/'summary.json',dict(checks=checks,groups=groups,pins=pins,unique_prefix_cases=4,
        total_prefix_replays_including_failed_check=5,new_native=0,
        coefficient_changes=0,observer_reconstruction_exact=True,all_saved_physical_prefixes_exact=True,
        interpretation='Executed canonical equations, including transported command target and dynamic lane profile. Not coefficient fitting, new forecast validation, or proof of an individual causal term.'))


def calibrate_local_anticipation():
    """Two local pressure-response candidates; freeze before action checks."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    parent=HERE/'baseline_reproduction_20260929'
    out=parent/'local_anticipation_17_20';out.mkdir(exist_ok=True)
    assert not (out/'training.json').exists(), 'Reuse completed training'
    manifest_path=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    manifest=load(manifest_path);context=lpr.load_sources(manifest_path)
    config_path=ROOT/manifest['sources']['reference_config']['path']
    assert sha(config_path)==manifest['sources']['reference_config']['sha256']
    original=load(config_path)
    cfg=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    source=parent/'component2220_s29_inputs_v2';capture=load(source/'capture.json')
    record=next(r for r in capture['records'] if r['arm']=='none')
    args,kwargs=read_primitive_capture(source/record['input'],record['sha256'])
    assert args[2]==context['parameters'] and kwargs['horizon_sec']==450
    args=list(args);args[1]=args[1][:150];kwargs['horizon_sec']=150
    truth=ObservationData(record['truth']);t0=capture['cutoff'];t1=t0+150
    save(out/'protocol.json',dict(hypothesis='Excess pressure response in cells17--20 contributes to pre-control false congestion and weak VSL discharge response.',
        train='seed29 NC first150s from2220.1; observed states score forecasts only',
        candidate_multipliers=[.5,.25],changed='Only downstream_ge_local anticipation in cells17--20, one common multiplier of existing values',
        unchanged=['downstream_lt_local response','FD/E','lane-drop phi','merge delta','cell23 correction','port dynamics','controls/demand/geometry'],
        score='mean(speed_error^2)/20^2 + mean(stock_error^2)/10^2 + mean(boundary_crossing_error^2)/10^2, cells17--20',
        selection='Lowest finite local score; require >=20% reduction before frozen action checks. No further candidates after failure.',
        max_training_rollouts=2,max_frozen450_rollouts=12,
        frozen_cases=['s29_early four arms','s43_early four arms','s29_late hold/release +/-VSL'],
        gain_acceptance='Do not adopt on speed improvement: retain correct meaningful loss/gain directions, improve discharge and stock, preserve costs and conservation. Previously inspected states, not pristine holdout.',
        manifest=str(manifest_path),manifest_sha256=sha(manifest_path),config_sha256=sha(config_path),
        new_native=0,production_adoption=False))
    def assess(pred):
        local=[];speeds=[];stocks=[];flows=[]
        for cell in range(17,21):
            vr=[];nr=[];qr=[]
            for stamp in [round(t0+30*j,6) for j in range(1,6)]:
                actual=next(r for r in truth.cells[stamp] if r['road']=='FW_E' and r['cell']==cell)
                model=next(r for r in pred['cells'] if r['road']=='FW_E' and r['cell']==cell and abs(r['time_s']-stamp)<1e-6)
                flow=next(r for r in pred['flows'] if r['road']=='FW_E' and r['cell']==cell and abs(r['window_end_s']-stamp)<1e-6)
                vr.append(model['v_kmh']-float(actual['v_kmh']))
                nr.append(model['n_veh']-float(actual['n_veh']))
                qr.append(flow['downstream_crossings']-float(truth.flows[stamp,'FW_E',cell]['downstream_crossings']))
            speeds+=vr;stocks+=nr;flows+=qr
            local.append(dict(cell=cell,speed_rmse=math.sqrt(sum(x*x for x in vr)/5),stock_rmse=math.sqrt(sum(x*x for x in nr)/5),flow_rmse=math.sqrt(sum(x*x for x in qr)/5)))
        mse=lambda values:sum(x*x for x in values)/len(values)
        assert len(pred['cells'])==len(pred['flows'])==31*5
        detail=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
        residual=max([abs(detail['continuity_residual_max_veh'])]+
            [abs(r['conservation_residual_veh']) for r in pred['ports']+pred['ramps']])
        invalid=(any(detail[k]>0 for k in ('density_projection_count','jam_density_exceedance_count','negative_density_count'))
            or residual>1e-7 or not all(math.isfinite(x) for x in speeds+stocks+flows)
            or any(not math.isfinite(r['v_kmh']) or r['v_kmh']<0 or r['v_kmh']>200 for r in pred['cells']))
        score=dict(invalid=invalid,diagnostics=detail,maximum_mass_residual=residual)
        return dict(local_score=mse(speeds)/400+mse(stocks)/100+mse(flows)/100,
            speed_rmse=math.sqrt(mse(speeds)),stock_rmse=math.sqrt(mse(stocks)),flow_rmse=math.sqrt(mse(flows)),
            cells=local,global_score=score)
    # Use a previously verified exact150 prefix including interval diagnostics.
    with gzip.open(parent/'spatial_vsl_response/speed_terms/s29_none_prefix.json.gz','rt',encoding='utf-8') as f:base=json.load(f)['prediction']
    rows=[dict(name='current',**assess(base))];manifests={}
    for scale in (.5,.25):
        name=f'ge{scale:g}';folder=out/name;folder.mkdir()
        config=copy.deepcopy(original);overrides=config['freeway']['state_response']['FW_E']['cell_overrides'];changes={}
        for cell in range(17,21):
            prior=cell_state_response(cfg.network,'FW_E',cell).get('anticipation')
            if prior is None:
                nu=cfg.network.freeway_segment_params['FW_E'][cell]['metanet_nu_km2_h']
                prior=dict(downstream_ge_local=nu,downstream_lt_local=nu)
            new={**prior,'downstream_ge_local':prior['downstream_ge_local']*scale}
            overrides.setdefault(str(cell),{})['anticipation']=new
            changes[str(cell)]=dict(before=prior,after=new)
        path=folder/'reference_config.json';save(path,config)
        document=copy.deepcopy(manifest);document['sources']['reference_config']=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
        document['qualification']='Local anticipation training candidate; no production adoption or gain qualification.'
        path=folder/'manifest.json';save(path,document);manifests[name]=path
        candidate=lpr.load_sources(path);cc=candidate['component']._config('FW_E',candidate['parameters']['by_direction']['FW_E'])
        for cell in range(31):
            now={k:v for k,v in cell_state_response(cc.network,'FW_E',cell).items() if k!='cell_overrides'}
            before={k:v for k,v in cell_state_response(cfg.network,'FW_E',cell).items() if k!='cell_overrides'}
            if 17<=cell<=20:assert now['anticipation']==changes[str(cell)]['after']
            else:assert now==before,(name,cell,'changed unrelated response')
        pred=candidate['component'].rollout(*copy.deepcopy(args),**copy.deepcopy(kwargs))
        with gzip.open(folder/'training150.json.gz','wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
        row=dict(name=name,changes=changes,**assess(pred));rows.append(row)
        save(out/'training.json',rows)
        print(json.dumps(dict(training=name,local_score=row['local_score'],speed_rmse=row['speed_rmse'],invalid=row['global_score']['invalid'])),flush=True)
    valid=[r for r in rows[1:] if not r['global_score']['invalid']]
    best=min(valid,key=lambda r:r['local_score']) if valid else rows[0]
    improvement=1-best['local_score']/rows[0]['local_score']
    selected=best['name'] if best['name']!='current' and improvement>=.2 else None
    save(out/'selection.json',dict(selected=selected,training_improvement=improvement,training=rows,
        selected_manifest=str(manifests[selected]) if selected else None,
        selected_manifest_sha256=sha(manifests[selected]) if selected else None,
        frozen_before_action_checks=True,production_adopted=False))
    if selected is not None:
        for name,inputs in [('s29_early',parent/'component2220_s29_inputs_v2'),
                            ('s43_early',parent/'component2220_s43_inputs_v2'),('s29_late',OUT)]:
            predict(manifest_path=manifests[selected],input_dir=inputs,output=out/'validation'/name)
    save(out/'status.json',dict(stage='complete_bounded_candidate',selected=selected,
        training_rollouts=2,validation_rollouts=12 if selected else 0,gain_qualified=False,production_adopted=False,new_native=0))


def calibrate_local_fd_18_20():
    """Bounded local FD calibration using existing physical_cell_fd support."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    parent=HERE/'baseline_reproduction_20260929';out=parent/'local_fd_18_20'
    assert not (out/'training.json').exists(), 'Reuse completed training'
    protocol=load(out/'protocol.json')
    for name,digest in protocol['core_pins'].items():assert sha(ROOT/name)==digest
    manifest_path=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    manifest=load(manifest_path);context=lpr.load_sources(manifest_path)
    config_path=ROOT/manifest['sources']['reference_config']['path'];original=load(config_path)
    assert sha(config_path)==manifest['sources']['reference_config']['sha256']
    model=context['component'];parameters=context['parameters']['by_direction']['FW_E']
    original_cfg=model._config('FW_E',parameters)
    original_rows=original_cfg.network.freeway_segment_params['FW_E']
    def assess(folder):
        rows=load(folder/'summary.json')['results'];reference=rows[0];loss=0.;comparisons=[]
        def exits(row,actual):
            f=row['flows']['actual' if actual else 'predicted']
            return f['off_departures']+f['terminal_exits_inferred' if actual else 'terminal_exits']
        for row in rows[1:]:
            p=row['deltas']['predicted_component_ttt'];a=row['deltas']['actual_component_ttt']
            qe=exits(row,False)-exits(reference,False);qa=exits(row,True)-exits(reference,True)
            me=row['deltas']['predicted_merge'];ma=row['deltas']['actual_merge']
            loss+=((p-a)/.5)**2+((qe-qa)/50)**2+((me-ma)/50)**2
            comparisons.append(dict(arm=row['arm'],predicted_delta=p,actual_delta=a,
                predicted_exit_delta=qe,actual_exit_delta=qa,predicted_merge_delta=me,actual_merge_delta=ma))
        return dict(loss=loss/3,rows=comparisons,
            mean_n_rmse=sum(r['score']['cell_n']['rmse'] for r in rows)/4,
            mean_q_rmse=sum(r['score']['flow_vph']['rmse'] for r in rows)/4,
            meaningful_signs_pass=all(r['predicted_delta']*r['actual_delta']>0 for r in comparisons if abs(r['actual_delta'])>.2))
    baseline=assess(parent/'component2220_s29_current_v2');candidates=[];manifests={};coefficient_checks=[]
    for rho_scale in protocol['rho_multipliers']:
        for shape_scale in protocol['shape_multipliers']:
            name=f'rho{rho_scale:g}_a{shape_scale:g}';folder=out/name;folder.mkdir()
            config=copy.deepcopy(original);overrides=config['freeway'].setdefault('physical_cell_fd',{}).setdefault('FW_E',{})
            for cell in protocol['cells']:
                raw=model.base.network.freeway_segment_params['FW_E'][cell]
                overrides.setdefault(str(cell),{}).update(rho_crit=raw['rho_crit']*rho_scale,metanet_a_m=raw['metanet_a_m']*shape_scale)
            path=folder/'reference_config.json';save(path,config)
            document=copy.deepcopy(manifest);document['sources']['reference_config']=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
            document['qualification']='Unqualified local18-20 FD trial; physical equations and control domain unchanged.'
            path=folder/'manifest.json';save(path,document);manifests[name]=path
            candidate=lpr.load_sources(path);cfg=candidate['component']._config('FW_E',parameters)
            assert cfg.network.freeway_state_response==original_cfg.network.freeway_state_response
            for cell in range(31):
                old=original_rows[cell];now=cfg.network.freeway_segment_params['FW_E'][cell]
                expected=copy.deepcopy(old)
                if cell in protocol['cells']:
                    expected['rho_crit']*=rho_scale;expected['metanet_a_m']*=shape_scale
                    assert now['metanet_a_m']>1 and now['rho_crit']<cfg.network.rho_max
                assert set(now)==set(expected)
                assert all(abs(now[k]-expected[k])<=1e-12 if isinstance(now[k],(int,float)) else now[k]==expected[k] for k in now),(name,cell)
                if cell not in protocol['cells']:assert now==old
            coefficient_checks.append(dict(candidate=name,all31_cell_scope_pass=True,
                runtime_coefficients={str(c):cfg.network.freeway_segment_params['FW_E'][c] for c in protocol['cells']}))
            predict(manifest_path=path,input_dir=parent/'component2220_s29_inputs_v2',output=folder/'training')
            score=assess(folder/'training');row=dict(name=name,rho_multiplier=rho_scale,shape_multiplier=shape_scale,**score)
            row['improvement']=1-score['loss']/baseline['loss']
            row['gate_pass']=(row['improvement']>=.2 and score['mean_n_rmse']<=1.1*baseline['mean_n_rmse']
                and score['mean_q_rmse']<=1.1*baseline['mean_q_rmse'] and score['meaningful_signs_pass'])
            candidates.append(row);save(out/'training.json',dict(baseline=baseline,candidates=candidates))
            print(json.dumps(dict(candidate=name,improvement=row['improvement'],gate=row['gate_pass'])),flush=True)
    valid=[r for r in candidates if r['gate_pass']];selected=min(valid,key=lambda r:r['loss'])['name'] if valid else None
    save(out/'selection.json',dict(selected=selected,frozen_before_validation=True,production_adopted=False))
    validation=[]
    if selected:
        for name,inputs,existing in [('s43',parent/'component2220_s43_inputs_v2',parent/'component2220_s43_current_v2'),
                                    ('late29',OUT,parent/'component2670_current')]:
            folder=out/'validation'/name
            predict(manifest_path=manifests[selected],input_dir=inputs,output=folder)
            before,after=assess(existing),assess(folder)
            validation.append(dict(case=name,existing=before,candidate=after,
                passed=(after['meaningful_signs_pass'] and after['loss']<before['loss']
                        and after['mean_n_rmse']<=1.1*before['mean_n_rmse'] and after['mean_q_rmse']<=1.1*before['mean_q_rmse'])))
    for name,digest in protocol['core_pins'].items():assert sha(ROOT/name)==digest
    save(out/'verification.json',dict(core_sources_unchanged=True,core_pins=protocol['core_pins'],coefficient_checks=coefficient_checks,
        reused_default_exact_proof=str(parent/'local_transport_response_24_25/default_regression.json'),
        selected_network_and_capture_pins_checked_by_predict=True,new_native=0))
    save(out/'summary.json',dict(stage='complete_bounded_local_fd',baseline=baseline,training=candidates,selected=selected,
        validation=validation,known_state_gate_passed=bool(validation) and all(r['passed'] for r in validation),
        new_training_rollouts=24,new_validation_rollouts=4*len(validation),new_default_rollouts=0,
        gain_qualified=False,production_adopted=False,new_native=0))


def _cellwise_config(spec, values, original, rho_multiplier):
    """Serialize independently indexed values through existing plant fields."""
    config=copy.deepcopy(original)
    fd=config['freeway'].setdefault('physical_cell_fd',{}).setdefault('FW_E',{})
    response=config['freeway'].setdefault('state_response',{}).setdefault('FW_E',{})
    local=response.setdefault('cell_overrides',{})
    assert len(values)==len(spec['variables'])
    for row,value in zip(spec['variables'],values):
        value=float(value);cell=str(row['cell']);name=row['parameter']
        assert math.isfinite(value) and row['lower']-1e-10<=value<=row['upper']+1e-10
        if name in ('rho_crit','metanet_a_m'):
            fd.setdefault(cell,{})[name]=value/rho_multiplier if name=='rho_crit' else value
        elif name=='tau_sec':
            local.setdefault(cell,{})['relaxation']={'acceleration_sec':value,'deceleration_sec':value}
        elif name in ('nu_ge','nu_lt'):
            local.setdefault(cell,{}).setdefault('anticipation',{})[
                'downstream_ge_local' if name=='nu_ge' else 'downstream_lt_local']=value
        elif name=='delta_merge':local.setdefault(cell,{})['delta_merge']=value
        else:raise ValueError(name)
    return config


def _cellwise_measure(model, pred, record, truth):
    """Same component/trapezoid definition as predict(), including on-ramp waits."""
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    t0=record['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
    on={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
    off={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
    obs_main={t:sum(x['n_veh'] for x in truth.cells[t] if x['road']=='FW_E') for t in times}
    obs_on={t:sum(float(truth.ports[t,c]['end_n_veh']) for c in on) for t in times}
    obs_off={t:sum(float(truth.ports[t,c]['end_n_veh']) for c in off) for t in times}
    p_main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
    p_on={t:sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
    p_off={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
    for p,o in ((p_main,obs_main),(p_on,obs_on),(p_off,obs_off)):p[t0]=o[t0]
    integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
    def totals(main,on_n,off_n):
        m,r,o=map(integral,(main,on_n,off_n))
        return dict(ttt=m+r+o,mainline_ttt=m,ramp_ttt=r,off_ttt=o,end_n=main[times[-1]]+on_n[times[-1]]+off_n[times[-1]])
    actual=totals(obs_main,obs_on,obs_off);forecast=totals(p_main,p_on,p_off)
    flows=[v for (t,r,c),v in truth.flows.items() if r=='FW_E' and t0<t<=times[-1]]
    actual['exits']=sum(float(f['off_departures'])+float(f['terminal_exits_inferred']) for f in flows)
    forecast['exits']=sum(f['off_departures']+f['terminal_exits'] for f in pred['flows'])
    ramps=sorted(r for r,v in model.ramps.items() if v['road']=='FW_E')
    actual['merges']={r:sum(float(truth.ports[t,str(model.ramps[r]['connector'])]['departures_veh']) for t in times[1:]) for r in ramps}
    forecast['merges']={r:sum(x['accepted_merge_veh'] for x in pred['ramps'] if x['ramp']==r) for r in ramps}
    score=score_rollout(truth,t0,pred,'FW_E',include_source_boundary=True)
    residual=max([abs(x['conservation_residual_veh']) for x in pred['ports']]+[abs(x['conservation_residual_veh']) for x in pred['ramps']])
    assert not score['invalid'] and residual<1e-7, 'Invalid conservative rollout'
    return dict(case=record['case'],arm=record['arm'],actual=actual,predicted=forecast,score=score,conservation_max=residual)


def _cellwise_losses(rows, relative_values, protocol):
    """Calibration loss only; never changes the controller's Omega objective."""
    import numpy as np
    state=[];paired=[];pairs=[]
    scales=protocol['state_scales']
    for row in rows:
        s=row['score'];p=row['predicted'];a=row['actual']
        terms=[(s[k]['rmse']/scales[k])**2 for k in ('speed','cell_n','flow_vph','source_flow_vph')]
        terms += [np.mean([((p['merges'][r]-a['merges'][r])/scales['ramp_merge_veh'])**2 for r in a['merges']]),
                  ((p['ramp_ttt']-a['ramp_ttt'])/scales['ramp_wait_veh_h'])**2]
        state.append(float(np.mean(terms)))
    for case in sorted({r['case'] for r in rows}):
        group=[r for r in rows if r['case']==case]
        base=next(r for r in group if r['arm'] in ('none','hold'))
        for row in group:
            if row is base:continue
            pd={k:row['predicted'][k]-base['predicted'][k] for k in ('ttt','ramp_ttt','exits')}
            ad={k:row['actual'][k]-base['actual'][k] for k in pd}
            terms=[((pd[k]-ad[k])/max(protocol['pair_scale_floors'][k],abs(ad[k])))**2 for k in pd]
            pm={r:row['predicted']['merges'][r]-base['predicted']['merges'][r] for r in row['actual']['merges']}
            am={r:row['actual']['merges'][r]-base['actual']['merges'][r] for r in pm}
            terms.append(float(np.mean([((pm[r]-am[r])/max(protocol['pair_scale_floors']['merge'],abs(am[r])))**2 for r in pm])))
            paired.append(float(np.mean(terms)))
            pairs.append(dict(case=case,arm=row['arm'],predicted=pd,actual=ad,predicted_merges=pm,actual_merges=am))
    prior=float(np.mean(np.square(relative_values)))
    result=dict(state=float(np.mean(state)),response=float(np.mean(paired)),prior=prior,pairs=pairs)
    result['state_objective']=result['state']+protocol['prior_weight']*prior
    result['response_objective']=result['state_objective']+protocol['response_weight']*result['response']
    result['meaningful_signs_pass']=all(x['predicted']['ttt']*x['actual']['ttt']>0 for x in pairs if abs(x['actual']['ttt'])>=protocol['meaningful_delta_veh_h'])
    result['mean_n_rmse']=float(np.mean([r['score']['cell_n']['rmse'] for r in rows]))
    result['mean_q_rmse']=float(np.mean([r['score']['flow_vph']['rmse'] for r in rows]))
    return result


def calibrate_cellwise(mode='state'):
    """Bounded simultaneous-perturbation calibration of the CONNECTED 31-cell model."""
    import numpy as np
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    root=HERE/'baseline_reproduction_20260929/cellwise_calibration'
    protocol=load(root/'protocol.json');spec=load(root/'parameter_spec.json');catalog=load(root/'data_catalog.json')
    assert mode in ('state','response')
    out=root/mode;out.mkdir(exist_ok=False)
    for name,digest in protocol['core_pins'].items():assert sha(ROOT/name)==digest
    assert sha(root/'parameter_spec.json')==protocol['spec_sha256'] and sha(root/'data_catalog.json')==protocol['catalog_sha256']
    assert sha(__file__)==protocol['helper_sha256']
    source=Path(spec['initial_manifest']);assert sha(source)==spec['initial_manifest_sha256']
    document=load(source);context=lpr.load_sources(source);original=load(ROOT/document['sources']['reference_config']['path'])
    params=context['parameters'];mult=params['by_direction']['FW_E']['rho_crit_multiplier']
    initial=np.array([r['initial'] for r in spec['variables']],dtype=float)
    lower=np.array([r['lower'] for r in spec['variables']])/initial-1
    upper=np.array([r['upper'] for r in spec['variables']])/initial-1
    records=[r for r in catalog['checked_records'] if r['role']=='train']
    assert len(records)==8 and all(r['source_network']==document['sources']['network']['sha256'] for r in records)
    data={};payloads={}
    for r in records:
        key=(r['case'],r['arm']);payloads[key]=read_primitive_capture(r['input'],r['sha256'])
        assert payloads[key][0][2]==params and payloads[key][1]['horizon_sec']==450
        data[key]=ObservationData(r['truth'])
    # Explicit values must round-trip through the SAME loader and runtime writer.
    evaluations=[];best=None;best_pred=None;rollouts=0;started=time.perf_counter()
    def evaluate(z,tag):
        nonlocal best,best_pred,rollouts
        values=initial*(1+z);folder=out/f'eval_{len(evaluations):03d}';folder.mkdir()
        config=_cellwise_config(spec,values,original,mult)
        config_path=folder/'reference_config.json';save(config_path,config)
        manifest=copy.deepcopy(document);manifest['sources']['reference_config']=dict(path=config_path.relative_to(ROOT).as_posix(),sha256=sha(config_path))
        manifest['qualification']='Unqualified joint cellwise calibration; no native or SDMPC promotion.'
        manifest_path=folder/'manifest.json';save(manifest_path,manifest)
        ctx=lpr.load_sources(manifest_path);model=ctx['component'];cfg=model._config('FW_E',params['by_direction']['FW_E'])
        for row,value in zip(spec['variables'],values):
            i=row['cell'];name=row['parameter'];local=cell_state_response(cfg.network,'FW_E',i)
            if name in ('rho_crit','metanet_a_m'):actual=cfg.network.freeway_segment_params['FW_E'][i][name]
            elif name=='tau_sec':actual=local['relaxation']['acceleration_sec'];assert actual==local['relaxation']['deceleration_sec']
            elif name=='delta_merge':actual=local['delta_merge']
            else:actual=local['anticipation']['downstream_ge_local' if name=='nu_ge' else 'downstream_lt_local']
            assert abs(actual-value)<1e-10,(i,name,actual,value)
        # West coefficients, commands, geometry and arrival payloads are untouched.
        assert cfg.network.freeway_segment_params['FW_W']==context['component']._config('FW_E',params['by_direction']['FW_E']).network.freeway_segment_params['FW_W']
        rows=[];predictions={};error=None
        for r in records:
            key=(r['case'],r['arm']);args,kwargs=copy.deepcopy(payloads[key])
            try:
                pred=model.rollout(*args,**kwargs);rollouts+=1
                rows.append(_cellwise_measure(model,pred,r,data[key]));predictions[key]=pred
            except (ArithmeticError,AssertionError,ValueError) as exc:
                error=f'{type(exc).__name__}: {exc}';break
        if error:
            item=dict(index=len(evaluations),tag=tag,relative_values=z.tolist(),values=values.tolist(),invalid=error,objective=1e12,rows=rows)
        else:
            loss=_cellwise_losses(rows,z,protocol)
            item=dict(index=len(evaluations),tag=tag,relative_values=z.tolist(),values=values.tolist(),invalid=None,objective=loss[mode+'_objective'],loss=loss,rows=rows)
        evaluations.append(item);save(folder/'result.json',item)
        if not error and (best is None or item['objective']<best['objective']):best=item;best_pred=predictions
        save(out/'status.json',dict(stage='fitting',mode=mode,evaluations=len(evaluations),rollouts=rollouts,best_index=None if best is None else best['index'],best_objective=None if best is None else best['objective'],elapsed_sec=time.perf_counter()-started))
        return item
    baseline=evaluate(np.zeros(len(initial)),'identity')
    assert baseline['invalid'] is None
    # Check state arrays against previously saved predictions, not just scalar TTT.
    refs=protocol['baseline_prediction_folders'];max_difference=0.;compared=0
    for r in records:
        path=Path(refs[r['case']])/(r['arm']+'_prediction.json.gz')
        with gzip.open(path,'rt',encoding='utf-8') as f:previous=json.load(f)
        current=json.loads(json.dumps(best_pred[(r['case'],r['arm'])]))
        def compare(a,b):
            nonlocal max_difference,compared
            if isinstance(a,dict):
                assert set(a)==set(b)
                for k in a:compare(a[k],b[k])
            elif isinstance(a,list):
                assert len(a)==len(b)
                for x,y in zip(a,b):compare(x,y)
            elif isinstance(a,(int,float)) and not isinstance(a,bool):
                d=abs(a-b);max_difference=max(max_difference,d);compared+=1
                assert d<=1e-8*max(1.,abs(a)),(a,b)
            else:assert a==b,(a,b)
        for key in ('cells','flows','ports','ramps'):compare(previous[key],current[key])
    save(out/'identity_verification.json',dict(physical_arrays_checked=True,numeric_values=compared,max_abs_difference=max_difference,tolerance='1e-8 * max(1,abs(reference)); explicit coefficients may round at machine precision'))
    rng=np.random.default_rng(protocol['optimizer_seed']);z=np.zeros(len(initial));m=np.zeros_like(z);v=np.zeros_like(z);history=[]
    for k in range(1,protocol['iterations']+1):
        delta=rng.choice([-1.,1.],size=len(z));c=protocol['perturbation_relative']/k**.101
        plus=evaluate(np.clip(z+c*delta,lower,upper),f'{k}:plus')
        minus=evaluate(np.clip(z-c*delta,lower,upper),f'{k}:minus')
        if plus['invalid'] or minus['invalid']:gradient=np.zeros_like(z)
        else:gradient=np.clip((plus['objective']-minus['objective'])/(2*c)*delta,-100,100)
        m=.9*m+.1*gradient;v=.999*v+.001*gradient**2
        direction=(m/(1-.9**k))/(np.sqrt(v/(1-.999**k))+1e-8)
        proposal=np.clip(z-protocol['step_relative']*direction/(1+k/24)**.5,lower,upper)
        evaluate(proposal,f'{k}:proposal')
        z=np.array(best['relative_values']);history.append(best['objective'])
        print(json.dumps(dict(mode=mode,iteration=k,evaluations=len(evaluations),best=best['objective'],state=best['loss']['state'],response=best['loss']['response'])),flush=True)
        if k>=protocol['minimum_iterations'] and len(history)>=protocol['stagnation_window']:
            old=history[-protocol['stagnation_window']]
            if old-history[-1]<protocol['minimum_relative_improvement']*max(abs(old),1e-9):break
    # Freeze BEFORE reading seed43 labels; no validation-dependent coefficient selection.
    save(out/'selection.json',dict(mode=mode,best_index=best['index'],values=best['values'],loss=best['loss'],frozen_before_check=True,iterations=len(history),evaluations=len(evaluations),production_adopted=False))
    for (case,arm),pred in best_pred.items():
        with gzip.open(out/f'{case}_{arm}_prediction.json.gz','wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
    chosen=out/f"eval_{best['index']:03d}"/'manifest.json'
    predict(manifest_path=chosen,input_dir=HERE/'baseline_reproduction_20260929/component2220_s43_inputs_v2',output=out/'check43')
    for name,digest in protocol['core_pins'].items():assert sha(ROOT/name)==digest
    save(out/'status.json',dict(stage='complete_frozen_check',mode=mode,evaluations=len(evaluations),training_rollouts=rollouts,check_rollouts=4,iterations=len(history),best_index=best['index'],elapsed_sec=time.perf_counter()-started,core_unchanged=True,production_adopted=False,gain_qualified=False,new_native=0))


def _cellwise_residuals(records, predictions, observations, measured, relative_values, protocol):
    """Vector form EXACTLY preserving the frozen scalar calibration objective."""
    import numpy as np
    result=[];count=len(records);scales=protocol['state_scales']
    def add(values,scale,weight):
        assert len(values)>0
        result.extend(np.asarray(values,dtype=float)*math.sqrt(weight/len(values))/scale)
    for record,row in zip(records,measured):
        key=(record['case'],record['arm']);truth=observations[key];pred=predictions[key]
        observed={(t,x['cell']):x for t,rows in truth.cells.items() for x in rows if x['road']=='FW_E'}
        speeds=[];counts=[];flows=[];source=[]
        for x in pred['cells']:
            o=observed[round(x['time_s'],6),x['cell']];counts.append(x['n_veh']-o['n_veh'])
            if o['n_veh']>=5 and o['v_kmh'] is not None:speeds.append(x['v_kmh']-o['v_kmh'])
        for x in pred['flows']:
            o=truth.flows[round(x['window_end_s'],6),'FW_E',x['cell']]
            flows.append(120*(x['downstream_crossings']+x['off_departures']+x['terminal_exits']-
                float(o['downstream_crossings'])-float(o['off_departures'])-float(o['terminal_exits_inferred'])))
            if x['cell']==0:source.append(120*(x['source_admissions']-float(o['source_admissions'])))
        for key,values in [('speed',speeds),('cell_n',counts),('flow_vph',flows),('source_flow_vph',source)]:
            add(values,scales[key],1/(count*6))
        a,p=row['actual'],row['predicted']
        add([p['merges'][r]-a['merges'][r] for r in sorted(a['merges'])],scales['ramp_merge_veh'],1/(count*6))
        add([p['ramp_ttt']-a['ramp_ttt']],scales['ramp_wait_veh_h'],1/(count*6))
    loss=_cellwise_losses(measured,relative_values,protocol);pairs=loss['pairs']
    weight=protocol['response_weight']/(len(pairs)*4)
    for row in pairs:
        for key in ('ttt','ramp_ttt','exits'):
            actual=row['actual'][key]
            add([row['predicted'][key]-actual],max(protocol['pair_scale_floors'][key],abs(actual)),weight)
        errors=[(row['predicted_merges'][r]-row['actual_merges'][r])/
            max(protocol['pair_scale_floors']['merge'],abs(row['actual_merges'][r])) for r in sorted(row['actual_merges'])]
        add(errors,1.,weight)
    add(relative_values,1.,protocol['prior_weight'])
    residual=np.asarray(result,dtype=float)
    assert np.isfinite(residual).all()
    assert abs(float(residual@residual)-loss['response_objective'])<1e-10
    return residual


def _cellwise_jacobian_initialize(folder):
    """Each numerical worker loads immutable saved inputs once; no COM/native."""
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    global _CELLWISE_JACOBIAN
    out=Path(folder);parent=out.parent;protocol=load(out/'protocol.json')
    for path,digest in protocol['core_pins'].items():assert sha(ROOT/path)==digest
    assert sha(__file__)==protocol['helper_sha256']
    spec=load(parent/'parameter_spec.json');document=load(spec['initial_manifest']);context=lpr.load_sources(spec['initial_manifest'])
    records=[r for r in load(parent/'data_catalog.json')['checked_records'] if r['role']=='train']
    payloads={};observations={}
    for r in records:
        key=(r['case'],r['arm']);payloads[key]=read_primitive_capture(r['input'],r['sha256'])
        assert payloads[key][0][2]==context['parameters']
        observations[key]=ObservationData(r['truth'])
    _CELLWISE_JACOBIAN=dict(out=out,protocol=protocol,spec=spec,document=document,context=context,
        original=load(ROOT/document['sources']['reference_config']['path']),records=records,
        payloads=payloads,observations=observations,loss_protocol=load(parent/'protocol.json'))


def calibrate_local_ramp_gap10484():
    """Two existing physical-gap coefficients; select on late29 before checks."""
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    parent=HERE/'baseline_reproduction_20260929';cw=parent/'cellwise_calibration';out=parent/'local_ramp_gap10484'
    out.mkdir(exist_ok=True);assert not (out/'protocol.json').exists(), 'Do not restart a prepared or completed calibration'
    protocol=load(cw/'protocol.json');catalog=load(cw/'data_catalog.json')['checked_records']
    baseline_manifest=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    document=load(baseline_manifest);ctx=lpr.load_sources(baseline_manifest);params=ctx['parameters']
    original=load(ROOT/document['sources']['reference_config']['path'])
    assert original['freeway']['physical_ramp_receiving_nodes']['RM_C10484']['critical_gap_sec']==2.0
    train=[r for r in catalog if r['case']=='s29_late'];assert len(train)==4
    checks=[r for r in catalog if r['case'] in ('s29_early','s43_early')]+load(cw/'additional_admission_s53.json')['records']
    assert len(checks)==12
    for p,digest in protocol['core_pins'].items():assert sha(ROOT/p)==digest
    for p,digest in protocol['truth_file_pins'].items():assert sha(p)==digest
    for p,digest in load(cw/'additional_admission_s53.json')['pins'].items():assert sha(p)==digest
    old_rows=load(cw/'state/eval_000/result.json')['rows'];baseline_train=[r for r in old_rows if r['case']=='s29_late']
    assert len(baseline_train)==4
    baseline_loss=_cellwise_losses(baseline_train,[0.]*159,protocol)
    save(out/'protocol.json',dict(candidates_critical_gap_sec=[2.5,3.0],original_critical_gap_sec=2.0,
        changed='Existing RM_C10484 critical_gap_sec only. Follow-up1.5s/head curve/density supply/all cell coefficients unchanged.',
        training_cases=[dict(case=r['case'],arm=r['arm']) for r in train],checks=[dict(case=r['case'],arm=r['arm']) for r in checks],
        training_only_selection='Lowest original paired response loss; require20% reduction, no meaningful sign reversal, and at most10% worse mean stock/flow RMSE. No further gap candidates after failure.',
        forecast_limit=20,new_native=0,future_input=False,previously_inspected_states_not_blind=True,
        rationale='Observed-inflow diagnostic over-releases10484 after meter relaxation; existing mean-flow gap service is the active budget. Test this parameter before any new receiving law.',
        manifest=str(baseline_manifest),manifest_sha256=sha(baseline_manifest),core_pins=protocol['core_pins'],baseline_train_loss=baseline_loss))
    def evaluate(model,records,folder):
        folder.mkdir();rows=[]
        for record in records:
            args,kwargs=read_primitive_capture(record['input'],record['sha256']);assert args[2]==params and kwargs['horizon_sec']==450
            pred=model.rollout(*args,**kwargs)
            filename=record['case']+'_'+record['arm']
            with gzip.open(folder/(filename+'_prediction.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            rows.append(_cellwise_measure(model,pred,record,ObservationData(record['truth'])))
        loss=_cellwise_losses(rows,[0.]*159,protocol);save(folder/'result.json',dict(rows=rows,loss=loss));return rows,loss
    trials=[]
    for gap in (2.5,3.0):
        folder=out/('gap_'+str(gap));folder.mkdir();config=copy.deepcopy(original)
        config['freeway']['physical_ramp_receiving_nodes']['RM_C10484']['critical_gap_sec']=gap
        path=folder/'reference_config.json';save(path,config);manifest=copy.deepcopy(document)
        manifest['sources']['reference_config']=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path));manifest['qualification']='Unqualified local gap calibration, no deployment.'
        path=folder/'manifest.json';save(path,manifest);model=lpr.load_sources(path)['component']
        assert model.ramp_receiving_nodes['RM_C10484']['critical_gap_sec']==gap
        rows,loss=evaluate(model,train,folder/'train');trials.append(dict(gap=gap,folder=str(folder),manifest=str(path),loss=loss))
        save(out/'status.json',dict(stage='training',completed_rollouts=len(trials)*4));print(json.dumps(dict(gap=gap,response=loss['response'],pairs=loss['pairs'])),flush=True)
    best=min(trials,key=lambda r:r['loss']['response']);loss=best['loss'];improvement=1-loss['response']/baseline_loss['response']
    eligible=improvement>=.2 and loss['meaningful_signs_pass'] and loss['mean_n_rmse']<=1.1*baseline_loss['mean_n_rmse'] and loss['mean_q_rmse']<=1.1*baseline_loss['mean_q_rmse']
    save(out/'selection.json',dict(best=best,training_improvement=improvement,eligible_for_checks=eligible,selected_before_checks=True))
    check=None
    if eligible:
        model=lpr.load_sources(best['manifest'])['component'];rows,loss=evaluate(model,checks,out/'checks');check=dict(rows=rows,loss=loss)
    for p,digest in protocol['core_pins'].items():assert sha(ROOT/p)==digest
    save(out/'summary.json',dict(trials=trials,best=best,training_improvement=improvement,eligible_for_checks=eligible,check=check,
        new_rollouts=8+(12 if check else 0),core_unchanged=True,new_native=0,production_adopted=False,gain_qualified=False))
    save(out/'status.json',dict(stage='complete_bounded_check',new_rollouts=8+(12 if check else 0),eligible_for_checks=eligible,production_adopted=False))
    print(json.dumps(dict(best_gap=best['gap'],training_improvement=improvement,eligible=eligible,new_rollouts=8+(12 if check else 0))),flush=True)


def check_cellwise_seed53():
    """Frozen additional-state check of the existing two models, without fitting."""
    import itertools
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    root=HERE/'baseline_reproduction_20260929/cellwise_calibration';joint=root/'jacobian_step'
    out=root/'check53';out.mkdir(exist_ok=False)
    admission=load(root/'additional_admission_s53.json');records=admission['records'];protocol=load(root/'protocol.json')
    for path,digest in admission['pins'].items():assert sha(path)==digest
    for path,digest in protocol['core_pins'].items():assert sha(ROOT/path)==digest
    selected=load(joint/'selection.json')
    manifests={'prior':HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json',
               'joint':joint/selected['selected']/'manifest.json'}
    save(out/'protocol.json',dict(admission_sha256=sha(root/'additional_admission_s53.json'),core_pins=protocol['core_pins'],
        manifests={k:dict(path=str(v),sha256=sha(v)) for k,v in manifests.items()},new_rollout_limit=8,
        fit=False,blind_holdout=False,previously_inspected_state=True,check_not_used_in_fitting=True,
        scope='East31+8connectors. Native component removals0; urban removals25/25/24/25 exclude whole-network qualification.',
        adoption=False,selection='Compare both already frozen models; no coefficient selection or retuning from this check.'))
    contexts={k:lpr.load_sources(v) for k,v in manifests.items()};params=contexts['prior']['parameters']
    assert contexts['joint']['parameters']==params
    payloads={r['arm']:read_primitive_capture(r['input'],r['sha256']) for r in records}
    first=payloads['hold']
    for args,kwargs in payloads.values():
        assert args[2]==params and args[0]==first[0][0] and kwargs['horizon_sec']==450
        assert kwargs['ramp_dynamics']==first[1]['ramp_dynamics'] and kwargs['port_dynamics']==first[1]['port_dynamics']
    observations={r['arm']:ObservationData(r['truth']) for r in records};versions={};completed=0
    for version,ctx in contexts.items():
        model=ctx['component'];folder=out/version;folder.mkdir();rows=[]
        for record in records:
            started=time.perf_counter();args,kwargs=copy.deepcopy(payloads[record['arm']])
            pred=model.rollout(*args,**kwargs);completed+=1
            with gzip.open(folder/(record['arm']+'_prediction.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            row=_cellwise_measure(model,pred,record,observations[record['arm']]);rows.append(row)
            save(folder/(record['arm']+'_result.json'),row)
            save(out/'status.json',dict(stage='running',completed=completed,last_version=version,last_arm=record['arm']))
            print(json.dumps(dict(version=version,arm=record['arm'],wall_sec=time.perf_counter()-started)),flush=True)
        relative=[0.]*159 if version=='prior' else selected['relative_values']
        comparisons=[]
        for a,b in itertools.combinations(rows,2):
            actual=b['actual']['ttt']-a['actual']['ttt'];predicted=b['predicted']['ttt']-a['predicted']['ttt']
            comparisons.append(dict(base=a['arm'],arm=b['arm'],actual_delta=actual,predicted_delta=predicted,
                meaningful=abs(actual)>=protocol['meaningful_delta_veh_h'],same_sign=actual*predicted>0))
        versions[version]=dict(rows=rows,loss=_cellwise_losses(rows,relative,protocol),all_pairs=comparisons)
    for path,digest in protocol['core_pins'].items():assert sha(ROOT/path)==digest
    for path,digest in admission['pins'].items():assert sha(path)==digest
    save(out/'summary.json',dict(versions=versions,scope='East31+8connectors, same30s trapezoid, not whole Omega.',
        source_pins_unchanged=True,common_initial_states_exact=True,new_rollouts=completed,new_native=0,fit=False,production_adopted=False,gain_qualified=False))
    save(out/'status.json',dict(stage='complete_frozen_check',completed=completed,production_adopted=False))
    print(json.dumps({v:dict(response=x['loss']['response'],pairs=x['all_pairs']) for v,x in versions.items()}),flush=True)


def _cellwise_jacobian_evaluate(task):
    import numpy as np
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import cell_state_response
    d=_CELLWISE_JACOBIAN;name,relative,keep_predictions=task;folder=d['out']/name;folder.mkdir(exist_ok=False)
    started=time.perf_counter();variables=d['spec']['variables'];initial=np.array([r['initial'] for r in variables])
    values=initial*(1+np.asarray(relative));params=d['context']['parameters'];road_params=params['by_direction']['FW_E']
    config=_cellwise_config(d['spec'],values,d['original'],road_params['rho_crit_multiplier'])
    path=folder/'reference_config.json';save(path,config)
    manifest=copy.deepcopy(d['document']);manifest['sources']['reference_config']=dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
    manifest['qualification']='Unqualified bounded Jacobian-based joint calibration; no production adoption.'
    path=folder/'manifest.json';save(path,manifest)
    model=lpr.load_sources(path)['component'];cfg=model._config('FW_E',road_params)
    for row,value in zip(variables,values):
        local=cell_state_response(cfg.network,'FW_E',row['cell']);key=row['parameter']
        if key in ('rho_crit','metanet_a_m'):actual=cfg.network.freeway_segment_params['FW_E'][row['cell']][key]
        elif key=='tau_sec':actual=local['relaxation']['acceleration_sec'];assert actual==local['relaxation']['deceleration_sec']
        elif key=='delta_merge':actual=local[key]
        else:actual=local['anticipation']['downstream_ge_local' if key=='nu_ge' else 'downstream_lt_local']
        assert abs(actual-value)<1e-10
    predictions={};rows=[];completed=0
    try:
        for record in d['records']:
            key=(record['case'],record['arm']);args,kwargs=copy.deepcopy(d['payloads'][key])
            prediction=model.rollout(*args,**kwargs);completed+=1
            rows.append(_cellwise_measure(model,prediction,record,d['observations'][key]));predictions[key]=prediction
        residual=_cellwise_residuals(d['records'],predictions,d['observations'],rows,relative,d['loss_protocol'])
        np.save(folder/'residual.npy',residual,allow_pickle=False)
        loss=_cellwise_losses(rows,relative,d['loss_protocol'])
        result=dict(name=name,relative_values=list(relative),values=values.tolist(),rows=rows,loss=loss,invalid=None,
            scalar_vector_objective_difference=abs(float(residual@residual)-loss['response_objective']),rollouts=completed,wall_sec=time.perf_counter()-started)
        if keep_predictions:
            for (case,arm),prediction in predictions.items():
                with gzip.open(folder/f'{case}_{arm}_prediction.json.gz','wt',encoding='utf-8') as f:json.dump(prediction,f,allow_nan=False)
    except (AssertionError,ArithmeticError,ValueError) as exc:
        result=dict(name=name,relative_values=list(relative),values=values.tolist(),rows=rows,invalid=f'{type(exc).__name__}: {exc}',rollouts=completed,wall_sec=time.perf_counter()-started)
    save(folder/'result.json',result)
    return dict(name=name,invalid=result['invalid'],rollouts=completed,wall_sec=result['wall_sec'])


def calibrate_cellwise_jacobian():
    """One finite-difference Jacobian and three bounded linearized steps, no refits on checks."""
    import numpy as np
    from concurrent.futures import ProcessPoolExecutor,as_completed
    from scipy.optimize import lsq_linear
    out=HERE/'baseline_reproduction_20260929/cellwise_calibration/jacobian_step'
    assert not (out/'status.json').exists(), 'Never restart a live/finished derivative job'
    protocol=load(out/'protocol.json');parent=out.parent;spec=load(parent/'parameter_spec.json')
    for p,h in load(parent/'protocol.json')['truth_file_pins'].items():assert sha(p)==h
    for p,h in protocol['input_pins'].items():assert sha(p)==h
    _cellwise_jacobian_initialize(out)
    z=np.array(protocol['start_relative_values']);initial=np.array([r['initial'] for r in spec['variables']])
    lower=np.array([r['lower'] for r in spec['variables']])/initial-1;upper=np.array([r['upper'] for r in spec['variables']])/initial-1
    started=time.perf_counter();completed=[]
    baseline=_cellwise_jacobian_evaluate(('baseline',z.tolist(),True));assert baseline['invalid'] is None
    original=load(parent/'response'/f"eval_{protocol['start_index']:03d}"/'result.json')
    current=load(out/'baseline/result.json')
    assert abs(current['loss']['response_objective']-original['loss']['response_objective'])<1e-12
    r0=np.load(out/'baseline/residual.npy',allow_pickle=False)
    steps=[];tasks=[]
    for i in range(len(z)):
        h=protocol['relative_difference_step'];h=h if z[i]+h<=upper[i] else -h
        assert lower[i]<=z[i]+h<=upper[i]
        trial=z.copy();trial[i]+=h;steps.append(h);tasks.append((f'column_{i:03d}',trial.tolist(),False))
    save(out/'status.json',dict(stage='jacobian_running',completed_columns=0,total_columns=len(tasks)))
    with ProcessPoolExecutor(max_workers=protocol['workers'],initializer=_cellwise_jacobian_initialize,initargs=(str(out),)) as pool:
        pending={pool.submit(_cellwise_jacobian_evaluate,t):t[0] for t in tasks}
        for future in as_completed(pending):
            row=future.result();completed.append(row)
            save(out/'status.json',dict(stage='jacobian_running',completed_columns=len(completed),total_columns=len(tasks),elapsed_sec=time.perf_counter()-started))
            if len(completed)%20==0:print(json.dumps(dict(completed_columns=len(completed),total_columns=len(tasks))),flush=True)
    assert not any(x['invalid'] for x in completed), 'Invalid probe preserved; no derivative/fit from incomplete physics'
    jac=np.column_stack([(np.load(out/f'column_{i:03d}/residual.npy',allow_pickle=False)-r0)/h for i,h in enumerate(steps)])
    np.savez_compressed(out/'jacobian.npz',jacobian=jac,residual=r0,steps=steps,relative_values=z)
    # Repeat six largest objective-gradient columns at half-step to disclose kinks.
    gradient=jac.T@r0;indices=np.argsort(np.abs(gradient))[-protocol['half_step_columns']:].tolist();stability=[]
    for i in indices:
        trial=z.copy();trial[i]+=steps[i]/2;label=f'half_{i:03d}'
        result=_cellwise_jacobian_evaluate((label,trial.tolist(),False));assert result['invalid'] is None
        small=(np.load(out/label/'residual.npy',allow_pickle=False)-r0)/(steps[i]/2)
        stability.append(dict(index=i,**spec['variables'][i],relative_column_difference=float(np.linalg.norm(small-jac[:,i])/max(np.linalg.norm(small),np.linalg.norm(jac[:,i]),1e-12))))
    # Prior rows are last159. Their positive diagonal must not be mistaken for data identification.
    singular=np.linalg.svd(jac[:-len(z)],compute_uv=False)
    response_start=len(r0)-len(z)-sum(3+len(x['actual_merges']) for x in current['loss']['pairs'])
    audit=dict(half_step_checks=stability,data_singular_values=singular.tolist(),
        singular_above_one_percent_max=int(sum(singular>.01*singular[0])),
        response_column_norm=np.linalg.norm(jac[response_start:-len(z)],axis=0).tolist(),
        data_column_norm=np.linalg.norm(jac[:-len(z)],axis=0).tolist(),
        interpretation='Local finite-difference sensitivity, not statistical identifiability; actuator/min/max kinks may invalidate the local linear approximation.')
    save(out/'sensitivity.json',audit)
    candidates=[]
    for radius in protocol['trust_radii']:
        lo=np.maximum(lower-z,-radius);hi=np.minimum(upper-z,radius)
        solution=lsq_linear(jac,-r0,bounds=(lo,hi),method='bvls',tol=1e-8,max_iter=100)
        assert np.isfinite(solution.x).all()
        step=solution.x;trial=z+step;name=f'trust_{radius:g}'
        result=_cellwise_jacobian_evaluate((name,trial.tolist(),True))
        row=load(out/name/'result.json')
        candidates.append(dict(name=name,radius=radius,solver_success=bool(solution.success),solver_message=str(solution.message),
            predicted_objective=float(np.linalg.norm(r0+jac@step)**2),actual_objective=None if row['invalid'] else row['loss']['response_objective'],
            invalid=row['invalid'],relative_step_rms=float(np.sqrt(np.mean(step**2))),relative_step_max=float(max(abs(step)))))
        save(out/'trials.json',candidates);print(json.dumps(candidates[-1]),flush=True)
    valid=[r for r in candidates if r['invalid'] is None and r['actual_objective']<current['loss']['response_objective']]
    chosen=min(valid,key=lambda r:r['actual_objective'])['name'] if valid else 'baseline'
    chosen_result=load(out/chosen/'result.json')
    save(out/'selection.json',dict(selected=chosen,loss=chosen_result['loss'],values=chosen_result['values'],relative_values=chosen_result['relative_values'],
        frozen_before_check=True,production_adopted=False,one_jacobian_only=True))
    predict(manifest_path=out/chosen/'manifest.json',input_dir=parent.parent/'component2220_s43_inputs_v2',output=out/'check43')
    for path,digest in protocol['core_pins'].items():assert sha(ROOT/path)==digest
    all_results=[load(p) for p in out.glob('*/result.json')]
    save(out/'status.json',dict(stage='complete_jacobian_step',selected=chosen,new_training_rollouts=sum(r['rollouts'] for r in all_results),new_check_rollouts=4,
        elapsed_sec=time.perf_counter()-started,core_unchanged=True,production_adopted=False,gain_qualified=False,new_native=0))


def audit_observed_state_pressure(integrate_five=False, variant=None):
    """Conditional one-step equation check, not autonomous prediction or fitting."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr, area_freeway_accounting as accounting
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.sdmpc_n31_20260924.integration_20260926.probe_selected_arrival_path import observe_first_interval_speed_terms
    from src.models.state import TrafficState,ControlAction
    from src.models.demand import DemandStep
    parent=HERE/'baseline_reproduction_20260929';out=parent/'observed_state_pressure'
    previous=load(out/'summary.json') if integrate_five else None
    if integrate_five:out=out/('five_second' + ('_'+variant if variant else ''))
    out.mkdir(parents=True,exist_ok=True)
    assert not (out/'summary.json').exists()
    manifest=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    context=lpr.load_sources(manifest);model=context['component']
    moment_dir=OLD/'diagnostics/metanet_net_gain_goal_20260924/mainline_moments'
    moment_manifest=load(moment_dir/'manifest.json')
    save(out/'protocol.json',dict(cases=['seed29 NC','seed43 NC'],timestamps='cutoff+30..420 every30s',
        bases=['native current N/v','saved autonomous current N/v'],
        common_inputs='Same observed current off stocks and preceding30s source/merge rates in both bases; same configured split and110 command.',
        purpose='Does substituting measured mainline state remove large local speed-equation imbalance?',
        horizon=('Five consecutive canonical1s steps' if integrate_five else 'One canonical1s step')+' per conditional snapshot, not a continuous450s prediction',
        comparison='Following5s native cell-mean speed trend. Population changes/transport are included; NOT individual acceleration or exact instantaneous derivative.',
        limits=['Future snapshots are labels only, but later initial states are observed: cause-isolation, never gain qualification.',
                'Preceding30s mean flows are not exact future fluxes. Current off occupancy/free-space support is held during this conditional probe; off-drain/queue feedback is not forecast here.',
                'Saved prediction state is re-evaluated under common observed ports/lagged rates, not exact archived autonomous continuation.',
                'NC only avoids guessing future VSL cohort composition. No new coefficient selection from this audit.'],
        variant=variant,new_native=0,new_full_rollouts=0,new_parameters=0,expected_conditional_steps=280 if integrate_five else 56))
    pins={str(manifest):sha(manifest),str(moment_dir/'manifest.json'):sha(moment_dir/'manifest.json')}
    rows=[];mass=[];reconstructed=0;first_step_checks=0
    oldrows={(r['seed'],r['basis'],r['time_sec'],r['cell']):r for r in previous['rows']} if previous else {}
    native_transport={}
    if integrate_five:
        transport_path=parent/'observed_state_pressure/velocity_transport/rows.csv'
        pins[str(transport_path)]=sha(transport_path)
        with transport_path.open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                if r['arm']=='none':native_transport[int(r['seed']),round(float(r['time_s']),6),int(r['cell'])]=r
    for seed in (29,43):
        inputs=parent/f'component2220_s{seed}_inputs_v2';cap=load(inputs/'capture.json');t0=cap['cutoff']
        rec=next(r for r in cap['records'] if r['arm']=='none');args,kwargs=read_primitive_capture(inputs/rec['input'],rec['sha256'])
        assert args[2]==context['parameters']
        assert all(all(v==110 for v in step.get('vsl_commands',{}).values()) for step in args[1])
        truth=ObservationData(rec['truth'])
        for name in ('cells_30s.csv','ports_30s.csv','flows_30s.csv'):
            p=truth.folder/name;pins[str(p)]=sha(p)
        pred_path=parent/f'component2220_s{seed}_current_v2/none_prediction.json.gz';pins[str(pred_path)]=sha(pred_path)
        with gzip.open(pred_path,'rt',encoding='utf-8') as f:prediction=json.load(f)
        pc={(round(r['time_s'],6),r['cell']):r for r in prediction['cells']}
        mm=next(r for r in moment_manifest['rows'] if r['seed']==seed and r['arm']=='none')
        mp=moment_dir/mm['output'];assert sha(mp)==mm['sha256'];pins[str(mp)]=sha(mp)
        moments={}
        with gzip.open(mp,'rt',encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                if r['scope']!='cell':continue
                key=(round(float(r['time_s']),6),int(r['bin']));z=moments.setdefault(key,[0.,0.])
                z[0]+=float(r['n']);z[1]+=float(r['speed_sum'])
        for offset in range(30,421,30):
            stamp=round(t0+offset,6);native={r['cell']:r for r in truth.cells[stamp] if r['road']=='FW_E'}
            for cell in range(31):
                n,nv=moments[stamp,cell]
                assert abs(n-native[cell]['n_veh'])<1e-8
                if n:assert abs(nv/n-native[cell]['v_kmh'])<1e-8
                reconstructed+=1
            for basis in ('native','predicted'):
                cfg=model._config('FW_E',context['parameters']['by_direction']['FW_E']);net=cfg.network
                local=native if basis=='native' else {i:pc[stamp,i] for i in range(31)}
                state=TrafficState.initial(cfg);state.time_sec=stamp
                lengths=[p['segment_length_km'] for p in net.freeway_segment_params['FW_E']]
                lanes=list(net.freeway_segment_lanes['FW_E'])
                state.freeway_effective_lanes['FW_E']=lanes
                state.freeway_density['FW_E']=[local[i]['n_veh']/(lengths[i]*lanes[i]) for i in range(31)]
                state.freeway_speed['FW_E']=[local[i]['v_kmh'] if local[i]['v_kmh'] is not None else net.v_free for i in range(31)]
                state.urban_link_storage=dict(net.urban_link_storage_veh)
                for o in net.off_ramps:
                    k=net.off_ramp_storage_link[o];state.urban_link_storage[k]=max(0.,net.urban_link_storage_veh[k]-float(truth.ports[stamp,o]['end_n_veh']))
                net.off_ramp_split_ratio=dict(args[1][offset]['off_split_ratio'])
                control=ControlAction.uncontrolled(cfg)
                release={r:float(truth.ports[stamp,str(model.ramps[r]['connector'])]['departures_veh'])*120 for r in net.ramps}
                source=float(truth.flows[stamp,'FW_E',0]['source_admissions'])*120
                demand=DemandStep({'FW_E':source},{},{})
                terms=[];before=sum(local[i]['n_veh'] for i in range(31))
                with observe_first_interval_speed_terms(stamp,terms):
                    assert cfg.simulation.T_f_sec==1
                    for second in range(5 if integrate_five else 1):
                        origin_before=state.mainline_origin_queue.get('FW_E',0.)
                        _,diag=accounting._freeway_substep_events(state,control,demand,cfg,
                            offramp_capacity_veh_h={o:state.urban_link_storage[net.off_ramp_storage_link[o]]*3600 for o in net.off_ramps},
                            ramp_release_veh_h=release,ramp_release_diagnostics={'total_no_meter_flow':sum(release.values()),'mean_ramp_receiving_factor':1.},
                            update_ramp_queues=False,include_ramp_queue_ttt=False,complete_allocator_scope=False)
                        after=sum(accounting.continuity_vehicle_counts(state,cfg)['FW_E'])
                        residual=after-before-((source+sum(release.values())-diag['offramp_flow_total']-diag['mainline_exit_flow_total'])/3600-(state.mainline_origin_queue['FW_E']-origin_before))
                        assert abs(residual)<1e-7 and diag['density_projection_count']==0
                        mass.append(abs(residual));before=after;state.time_sec=round(stamp+second+1,6)
                if integrate_five:
                    for i in range(17,26):
                        parts=[r for r in terms if r['cell']==i]
                        assert len(parts)==5
                        prior=oldrows[seed,basis,stamp,i]
                        if variant is None:
                            for key in ('speed_before','speed_final','relaxation','convection','anticipation','lane_drop_raw','post_equation_change'):
                                assert abs(parts[0][key]-prior[key])<1e-8,(seed,basis,stamp,i,key)
                            first_step_checks+=1
                        n,nv=moments[round(stamp+5,6),i]
                        if native[i]['n_veh']<5 or n<5:continue
                        native_row=native_transport[seed,stamp,i]
                        native_change=nv/n-native[i]['v_kmh']
                        assert abs(native_change-float(native_row['mean_change_kmh']))<1e-8
                        sums={key:sum(p[key] for p in parts) for key in ('relaxation','convection','anticipation','lane_drop_raw','post_equation_change')}
                        projection=sum(p['after_speed_equation']-p['speed_before']-p['relaxation']-p['convection']-p['anticipation']+p['lane_drop_raw'] for p in parts)
                        change=parts[-1]['speed_final']-parts[0]['speed_before']
                        assert abs(change-(sums['relaxation']+sums['convection']+sums['anticipation']-sums['lane_drop_raw']+sums['post_equation_change']+projection))<1e-8
                        rows.append(dict(seed=seed,basis=basis,time_sec=stamp,cell=i,speed_start=parts[0]['speed_before'],speed_end=parts[-1]['speed_final'],
                            model_change_kmh=change,first_step_extrapolated_kmh=5*(parts[0]['speed_final']-parts[0]['speed_before']),native_change_kmh=native_change,
                            native_stayer_kmh=float(native_row['stayer_change_kmh']),native_entry_kmh=float(native_row['entry_composition_kmh']),native_exit_kmh=float(native_row['exit_composition_kmh']),
                            terms_sum_kmh=sums,projection_sum_kmh=projection,steps=parts))
                    continue
                for term in terms:
                    i=term['cell']
                    if not 17<=i<=25:continue
                    n,nv=moments[round(stamp+5,6),i]
                    if native[i]['n_veh']<5 or n<5:continue
                    trend=(nv/n-native[i]['v_kmh'])/5
                    rows.append(dict(seed=seed,basis=basis,**term,
                        native_start_kmh=native[i]['v_kmh'],next5_native_mean_trend_kmh_per_s=trend,
                        equation_increment_kmh=term['speed_final']-term['speed_before']))
    groups=[]
    for seed in (29,43):
        for basis in ('native','predicted'):
            for cell in range(17,26):
                selected=[r for r in rows if (r['seed'],r['basis'],r['cell'])==(seed,basis,cell)]
                if integrate_five:
                    def rmse(key):return math.sqrt(sum((r[key]-r['native_change_kmh'])**2 for r in selected)/len(selected))
                    keys=['model_change_kmh','first_step_extrapolated_kmh','native_change_kmh','native_stayer_kmh','native_entry_kmh','native_exit_kmh']
                    groups.append(dict(seed=seed,basis=basis,cell=cell,count=len(selected),means={k:sum(r[k] for r in selected)/len(selected) for k in keys},
                        rmse_five_step=rmse('model_change_kmh'),rmse_first_step_extrapolated=rmse('first_step_extrapolated_kmh'),
                        terms_sum_mean={k:sum(r['terms_sum_kmh'][k] for r in selected)/len(selected) for k in selected[0]['terms_sum_kmh']}))
                    continue
                keys=['relaxation','convection','anticipation','lane_drop_raw','post_equation_change','equation_increment_kmh','next5_native_mean_trend_kmh_per_s']
                groups.append(dict(seed=seed,basis=basis,cell=cell,count=len(selected),
                    means={k:sum(r[k] for r in selected)/len(selected) for k in keys},
                    sign_agreement=sum(r['equation_increment_kmh']*r['next5_native_mean_trend_kmh_per_s']>0 for r in selected),
                    equation_below_minus1=sum(r['equation_increment_kmh']<-1 for r in selected)))
    save(out/'summary.json',dict(groups=groups,rows=rows,conditional_steps=len(mass),max_mass_residual=max(mass),
        native_moment_reconstruction_checks=reconstructed,first_step_exact_checks=first_step_checks,source_pins=pins,helper_sha256=sha(Path(__file__)),
        new_full_rollouts=0,new_native=0,coefficient_fit=False,autonomous_validation=False))
    print(json.dumps(dict(conditional_steps=len(mass),maxmass=max(mass),groups=[g for g in groups if g['basis']=='native']),ensure_ascii=False),flush=True)


def audit_native_velocity_transport():
    """Exact sampled-population mean-speed decomposition; no prediction law."""
    from bisect import bisect_right
    parent=HERE/'baseline_reproduction_20260929';out=parent/'observed_state_pressure/velocity_transport'
    out.mkdir(exist_ok=False)
    directory=OLD/'diagnostics/metanet_net_gain_goal_20260924/mainline_moments'
    provenance=load(directory/'manifest.json');geometry=load(HERE/'selected/port_gain/geometry.json')
    addresses={int(k):float(v[1]) for k,v in geometry['addresses'].items() if v[0]=='FW_E'}
    bounds=geometry['bounds']['FW_E'];start,end=provenance['window_sec']
    save(out/'protocol.json',dict(cases=['s29 none','s29 vsl','s43 none','s43 vsl'],start=start,end=end,
        sampling_sec=5,target_cells=list(range(17,26)),fit=False,new_native=0,
        identity='mean(v1)-mean(v0) = sum_stayers(v1-v0)/N1 + sum_entries(v1-mean(v0))/N1 - sum_exits(v0-mean(v0))/N1',
        limitations=['Sampled entries/exits are set differences, not exact crossing times.',
            'Entry speed at interval end includes acceleration after crossing; before/after speeds are both retained.',
            'Terms are a population accounting identity, not separately identified METANET force terms or a new dynamics closure.',
            'Do not substitute actual future crossing speeds or variances into autonomous MPC.'],
        purpose='Check whether the upstream cell mean represents the vehicles that actually advance to a recovery cell.'))
    rows=[];checks=[]
    for seed in (29,43):
        for arm in ('none','vsl'):
            meta=next(r for r in provenance['rows'] if r['seed']==seed and r['arm']==arm)
            source=Path(meta['source']);stat=source.stat()
            assert stat.st_size==meta['source_bytes'] and stat.st_mtime_ns==meta['source_mtime_ns']
            mp=directory/meta['output'];assert sha(mp)==meta['sha256']
            moments={}
            with gzip.open(mp,'rt',encoding='utf-8-sig',newline='') as f:
                for row in csv.DictReader(f):
                    if row['scope']!='cell':continue
                    key=(round(float(row['time_s']),6),int(row['bin']));z=moments.setdefault(key,[0.,0.])
                    z[0]+=float(row['n']);z[1]+=float(row['speed_sum'])
            frames={};digest=hashlib.sha256();columns=None;window_rows=0
            with source.open('rb') as f:
                for line in f:
                    if columns is None:
                        if line.startswith(b'$VEHICLE:'):
                            columns=line.rstrip().split(b':',1)[1].split(b';')
                            ci={x:i for i,x in enumerate(columns)}
                        continue
                    if not line.strip():continue
                    t=float(line.split(b';',1)[0])
                    if t>end+1e-7:break
                    digest.update(line)
                    if t<start-1e-7:continue
                    window_rows+=1;values=line.rstrip().split(b';');link=int(values[ci[b'LANE\\LINK\\NO']])
                    if link not in addresses:continue
                    x=addresses[link]+float(values[ci[b'POS']]);cell=max(0,min(len(bounds)-2,bisect_right(bounds,x)-1))
                    vehicle=int(values[ci[b'NO']]);frame=frames.setdefault(round(t,6),{})
                    assert vehicle not in frame
                    frame[vehicle]=(cell,float(values[ci[b'SPEED']]))
            actual_digest=digest.hexdigest()
            save(out/f's{seed}_{arm}_source.json',dict(source=str(source),bytes=stat.st_size,window_rows=window_rows,
                prefix_sha256=actual_digest,expected_prefix_sha256=meta['data_prefix_sha256']))
            assert actual_digest==meta['data_prefix_sha256'], 'Existing native prefix changed'
            assert window_rows==meta['window_raw_rows'] and len(frames)==91
            grouping={}
            for t,frame in frames.items():
                for i in range(17,26):
                    group={v:s for v,(c,s) in frame.items() if c==i};n,nv=moments.get((t,i),(0,0))
                    assert len(group)==n and abs(sum(group.values())-nv)<1e-7,(seed,arm,t,i)
                    grouping[t,i]=group
            for t in sorted(frames)[:-1]:
                later=round(t+5,6)
                for i in range(17,26):
                    before=grouping[t,i];after=grouping[later,i]
                    if not before or not after:continue
                    n1=len(after);v0=sum(before.values())/len(before);v1=sum(after.values())/n1
                    stay=before.keys()&after.keys();enter=after.keys()-before.keys();leave=before.keys()-after.keys()
                    a=sum(after[v]-before[v] for v in stay)/n1
                    b=sum(after[v]-v0 for v in enter)/n1;c=-sum(before[v]-v0 for v in leave)/n1
                    assert abs(v1-v0-a-b-c)<1e-8
                    from_previous=[v for v in enter if v in frames[t] and frames[t][v][0]==i-1]
                    upn,upnv=moments.get((t,i-1),(0,0));upmean=upnv/upn if upn else None
                    moving=[frames[t][v][1] for v in from_previous]
                    crossing_end=[after[v] for v in from_previous]
                    rows.append(dict(seed=seed,arm=arm,time_s=t,cell=i,n0=len(before),n1=n1,
                        mean_change_kmh=v1-v0,stayer_change_kmh=a,entry_composition_kmh=b,exit_composition_kmh=c,
                        entering=len(enter),leaving=len(leave),from_previous_cell=len(moving),upstream_cell_mean_kmh=upmean,
                        advancing_before_speed_sum=sum(moving),advancing_end_speed_sum=sum(crossing_end),
                        advancing_excess_before_sum=sum(v-upmean for v in moving) if moving else 0.))
            checks.append(dict(seed=seed,arm=arm,frames=91,window_rows=window_rows,prefix_sha256=actual_digest,
                matched_cell_moments=91*9,exact_mean_identity=True))
            print(json.dumps(checks[-1]),flush=True)
    groups=[]
    for seed in (29,43):
        for arm in ('none','vsl'):
            for cell in range(17,26):
                selected=[r for r in rows if (r['seed'],r['arm'],r['cell'])==(seed,arm,cell)]
                advance=sum(r['from_previous_cell'] for r in selected)
                groups.append(dict(seed=seed,arm=arm,cell=cell,intervals=len(selected),advancing_samples=advance,
                    mean_advancing_minus_upstream_mean_kmh=sum(r['advancing_excess_before_sum'] for r in selected)/advance if advance else None,
                    advancing_before_mean_kmh=sum(r['advancing_before_speed_sum'] for r in selected)/advance if advance else None,
                    advancing_end_mean_kmh=sum(r['advancing_end_speed_sum'] for r in selected)/advance if advance else None,
                    mean_terms_kmh_per_s={k:sum(r[k] for r in selected)/len(selected)/5 for k in
                        ('mean_change_kmh','stayer_change_kmh','entry_composition_kmh','exit_composition_kmh')}))
    with (out/'rows.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    save(out/'summary.json',dict(groups=groups,checks=checks,new_native=0,fit=False,new_full_rollouts=0,
        helper_sha256=sha(Path(__file__)),source_manifest_sha256=sha(directory/'manifest.json')))


def audit_native_lane_sufficiency():
    """Cached lane-state/flow evidence, never a new predictive closure."""
    parent=HERE/'baseline_reproduction_20260929';out=parent/'native_lane_sufficiency';out.mkdir(exist_ok=False)
    original=OLD/'diagnostics/metanet_net_gain_goal_20260924/mainline_moments'
    provenance=load(original/'manifest.json');geometry_path=HERE/'selected/port_gain/geometry.json'
    geometry=load(geometry_path);cells={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    spatial=load(parent/'spatial_vsl_response/summary.json')
    pins={str(original/'manifest.json'):sha(original/'manifest.json'),str(geometry_path):sha(geometry_path)}
    save(out/'protocol.json',dict(cases=['seed29 none/vsl','seed43 none/vsl'],cells=list(range(16,26)),
        new_rollouts=0,new_native=0,coefficient_fit=False,
        matching='Same cell, same control arm, same150s signal phase; distinct seeds or >=150s separation in one seed. Local absN<=3veh,absv<=5km/h. Stronger screen also requires upstream/downstream absN<=3 and absv<=10, plus all8east connector absstock<=3.',
        interpretation='Matched descriptive states, not independent causal samples. Future30s outflow is an outcome only. Missing future arrivals, command exposure distributions and within-cell positions can also explain differences; do not assign all residuals to lanes.',
        flow_proxy='Trapezoidal5s integral of Nv/L is space-average cell production, not boundary discharge/capacity. Its difference is not a capacity bonus.'))
    samples=[];groups=[];checks=[]
    for seed in (29,43):
        capture=load(parent/f'component2220_s{seed}_inputs_v2/capture.json');t0=capture['cutoff'];times=[round(t0+5*j,6) for j in range(91)]
        for arm in ('none','vsl'):
            source=next(r for r in provenance['rows'] if r['seed']==seed and r['arm']==arm)
            path=original/source['output'];assert sha(path)==source['sha256'];pins[str(path)]=sha(path)
            lane={}
            with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:
                for r in csv.DictReader(f):
                    if r['scope']!='cell':continue
                    key=(round(float(r['time_s']),6),int(r['bin']),int(r['lane']))
                    z=lane.setdefault(key,dict(n=0.,nv=0.,nv2=0.,acc=0.,stopped=0.))
                    for dst,src in [('n','n'),('nv','speed_sum'),('nv2','speed_sq_sum'),('acc','acceleration_sum'),('stopped','stopped_n')]:z[dst]+=float(r[src])
            aggregate={}
            for t in times:
                for cell in range(31):
                    ls=[lane.get((t,cell,g),dict(n=0.,nv=0.,nv2=0.,acc=0.,stopped=0.)) for g in range(1,int(round(cells[cell]['effective_lanes']))+1)]
                    n=sum(z['n'] for z in ls);nv=sum(z['nv'] for z in ls);v=nv/n if n else 0.
                    var=max(0.,sum(z['nv2'] for z in ls)/n-v*v) if n else 0.
                    between=sum(z['n']*(z['nv']/z['n']-v)**2 for z in ls if z['n'])/n if n else 0.
                    assert between<=var+1e-7
                    aggregate[t,cell]=dict(n=n,v=v,nv=nv,variance=var,between_variance=between,
                        acceleration=sum(z['acc'] for z in ls)/n if n else 0.,
                        right_lane_n=ls[0]['n'],stopped_n=sum(z['stopped'] for z in ls),lanes=ls)
            record=next(r for r in capture['records'] if r['arm']==arm);truth=Path(record['truth'])
            tables={}
            for name in ('cells_30s.csv','flows_30s.csv','ports_30s.csv'):
                path=truth/name;pins[str(path)]=sha(path)
                if str(path) in spatial['source_pins']:assert pins[str(path)]==spatial['source_pins'][str(path)]
                with path.open(encoding='utf-8-sig',newline='') as f:tables[name]=list(csv.DictReader(f))
            counts=0;max_v_error=0.
            for r in tables['cells_30s.csv']:
                t=round(float(r['time_s']),6);cell=int(r['cell'])
                if r['road']!='FW_E' or (t,cell) not in aggregate:continue
                z=aggregate[t,cell];assert z['n']==float(r['n_veh'])
                if z['n']:
                    error=abs(z['v']-float(r['v_kmh']));assert error<1e-7;max_v_error=max(max_v_error,error)
                counts+=1
            assert counts==16*31
            checks.append(dict(seed=seed,arm=arm,exact_cell_count_snapshots=counts,speed_max_error=max_v_error))
            flow={(round(float(r['window_end_s']),6),int(r['cell'])):r for r in tables['flows_30s.csv'] if r['road']=='FW_E'}
            port={(round(float(r['window_end_s']),6),r['connector']):float(r['end_n_veh']) for r in tables['ports_30s.csv'] if r['road']=='FW_E'}
            for cell in range(16,26):
                for j in range(15):
                    start=round(t0+30*j,6);end=round(start+30,6);z=aggregate[start,cell]
                    stamps=[round(start+5*k,6) for k in range(7)];length=(cells[cell]['end_m']-cells[cell]['start_m'])/1000
                    production=sum((aggregate[a,cell]['nv']+aggregate[b,cell]['nv'])*5/(7200*length) for a,b in zip(stamps,stamps[1:]))
                    f=flow[end,cell]
                    samples.append(dict(seed=seed,arm=arm,cell=cell,time_s=start,phase=round((start-.1)%150,6),
                        **{k:v for k,v in z.items() if k not in ('lanes','nv')},up=aggregate[start,cell-1],down=aggregate[start,cell+1],
                        port_stock={k:n for (t,k),n in port.items() if t==start},
                        next30_through=float(f['downstream_crossings']),next30_off=float(f['off_departures']),
                        next30_merge=float(f['ramp_merges']),production_proxy_veh=production,
                        end_n=aggregate[end,cell]['n']))
                rows=[aggregate[t,cell] for t in times]
                total_n=sum(z['n'] for z in rows);total_var=sum(z['n']*z['variance'] for z in rows)
                groups.append(dict(seed=seed,arm=arm,cell=cell,mean_n=total_n/len(rows),
                    vehicle_weighted_speed=sum(z['nv'] for z in rows)/total_n,
                    mean_right_lane_n=sum(z['right_lane_n'] for z in rows)/len(rows),
                    between_lane_variance_fraction=sum(z['n']*z['between_variance'] for z in rows)/total_var if total_var else 0.,
                    stopped_fraction=sum(z['stopped_n'] for z in rows)/total_n))
    matches=[]
    for i,a in enumerate(samples):
        if a['n']<5:continue
        for b in samples[i+1:]:
            if a['cell']!=b['cell'] or a['arm']!=b['arm'] or a['phase']!=b['phase'] or b['n']<5:continue
            if a['seed']==b['seed'] and abs(a['time_s']-b['time_s'])<150-1e-7:continue
            if abs(a['n']-b['n'])>3 or abs(a['v']-b['v'])>5:continue
            nearby=all(abs(a[k]['n']-b[k]['n'])<=3 and abs(a[k]['v']-b[k]['v'])<=10 for k in ('up','down'))
            port=all(abs(a['port_stock'][k]-b['port_stock'][k])<=3 for k in a['port_stock'])
            matches.append(dict(cell=a['cell'],arm=a['arm'],a=dict(seed=a['seed'],time_s=a['time_s']),b=dict(seed=b['seed'],time_s=b['time_s']),
                delta_n=b['n']-a['n'],delta_v=b['v']-a['v'],delta_next30_through=b['next30_through']-a['next30_through'],
                delta_right_lane_n=b['right_lane_n']-a['right_lane_n'],delta_between_variance=b['between_variance']-a['between_variance'],
                neighbor_screen_pass=nearby,port_screen_pass=port,stronger_screen_pass=nearby and port))
    pins[str(Path(__file__))]=sha(Path(__file__))
    save(out/'summary.json',dict(groups=groups,matches=matches,samples=samples,checks=checks,pins=pins,
        local_matches=len(matches),stronger_matches=sum(r['stronger_screen_pass'] for r in matches),
        model_state_insufficiency_proven=False,causal_lane_effect_proven=False,new_native=0,new_rollouts=0,
        limits=['30s future counts are noisy outcomes, not model capacities.',
                'Same signal phase and local neighborhood do not match every urban/source/command-cohort state.',
                'Prior per-file SHA of seed43NC cells CSV is unavailable; moment archive SHA plus exact count/speed reconstruction add an independent cache consistency check.']))
    print(json.dumps(dict(checks=checks,local_matches=len(matches),stronger_matches=sum(r['stronger_screen_pass'] for r in matches))),flush=True)


def prepare_native_distribution_split():
    """Two native mechanism tests using the existing fixed-command runner."""
    import xml.etree.ElementTree as ET
    from diagnostics.fast_fixed_profile import prepare
    parent=HERE/'baseline_reproduction_20260929';out=parent/'native_distribution_split';out.mkdir(exist_ok=False)
    source=HERE/'selected/network/native_seed29.inpx';raw=source.read_bytes()
    assert sha(source)=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    tree=ET.fromstring(raw);nodes={int(n.get('no')):n for n in tree.findall('./desSpeedDistributions/desSpeedDistribution')}
    assert 91 not in nodes and 109 not in nodes
    def moments(node):
        points=[(float(p.get('fx')),float(p.get('x'))) for p in node.findall('./speedDistrDatPts/speedDistributionDataPoint')]
        assert points[0][0]==0 and points[-1][0]==1
        mean=sum((q-p)*(a+b)/2 for (p,a),(q,b) in zip(points,points[1:]))
        second=sum((q-p)*(a*a+a*b+b*b)/3 for (p,a),(q,b) in zip(points,points[1:]))
        return dict(mean_kmh=mean,std_kmh=math.sqrt(second-mean*mean),points=points)
    nominal,controlled=moments(nodes[110]),moments(nodes[90]);shift=nominal['mean_kmh']-controlled['mean_kmh']
    new={};definitions={}
    for no,origin,offset,name in [(91,110,-shift,'diagnostic_mean_only'),(109,90,shift,'diagnostic_shape_only')]:
        node=copy.deepcopy(nodes[origin]);node.set('no',str(no));node.set('name',name)
        for point in node.findall('./speedDistrDatPts/speedDistributionDataPoint'):
            point.set('x',format(float(point.get('x'))+offset,'.12g'))
        new[no]=node;definitions[str(no)]=moments(node)
    assert abs(definitions['91']['mean_kmh']-controlled['mean_kmh'])<1e-9
    assert abs(definitions['91']['std_kmh']-nominal['std_kmh'])<1e-9
    assert abs(definitions['109']['mean_kmh']-nominal['mean_kmh'])<1e-9
    assert abs(definitions['109']['std_kmh']-controlled['std_kmh'])<1e-9
    assert raw.count(b'</desSpeedDistributions>')==1
    addition=b''.join(ET.tostring(new[k],encoding='utf-8') for k in (91,109))
    revised=raw.replace(b'</desSpeedDistributions>',addition+b'</desSpeedDistributions>')
    assert revised.replace(addition,b'',1)==raw
    network_dir=out/'source';network_dir.mkdir()
    assets=set()
    for node in tree.iter():
        for value in node.attrib.values():
            if value.startswith('#data#'):assets.add(value[len('#data#'):])
    for name in assets:
        assert Path(name).name==name
        (network_dir/name).write_bytes((source.parent/name).read_bytes())
    old_profile=Path('D:/VISSIM_runs/20260924_response2250_s29/vsl.json')
    original=load(old_profile);assert original['network_sha256']==sha(source)
    assert original['seed']==29 and original['terminal_sec']==3000 and original['control_start_sec']==2250
    assert {r['dsd_no'] for r in original['vsl_commands']}=={63,64,65,66}
    assert not original['meter_commands']
    plans=[];pins={str(source):sha(source),str(old_profile):sha(old_profile)}
    for arm,no in [('mean_only',91),('shape_only',109)]:
        network=network_dir/f'dsd_split_s29_{arm}.inpx';network.write_bytes(revised)
        profile=copy.deepcopy(original);profile['network_sha256']=sha(network)
        for row in profile['vsl_commands']:row['speed_id']=no
        path=out/(arm+'.json');save(path,profile)
        prepared=out/('prepared_'+arm);metadata=prepare(network,path,prepared)
        pins.update(metadata['snapshot_sha256']);pins[str(prepared/'prepared.json')]=sha(prepared/'prepared.json')
        plans.append(dict(arm=arm,prepared=str(prepared),output=f'D:/VISSIM_runs/20260929_dsd_mean_shape_s29/{arm}/run'))
    for name in ('fast_nc_run.ps1','fast_nc_runner.vbs','fast_fixed_profile_verify.py','validate_native_signal_record.py'):
        p=ROOT/'diagnostics'/name;pins[str(p)]=sha(p)
    save(out/'protocol.json',dict(stage='prepared_not_started',finite_run_count=2,automatic_retries=0,
        plans=plans,seed=29,sim_res=10,fzp_interval_sec=5,terminal_sec=3000,
        scoring_window=[2220.1,2670.1],intervention_sec=2250,
        hypothesis='Native110->90 changes both desired-speed mean and distribution shape. Separate mean translation from zero-mean shape change before inventing a plant capacity effect.',
        original_distributions={'110':nominal,'90':controlled},diagnostic_distributions=definitions,
        shape_definition='Shape-only preserves mean, changes width and higher distribution shape; not a pure variance-only intervention.',
        unchanged='Original64cf bytes preserved except two unreferenced distribution definitions appended. Same seed/demand/routes/geometry/city signals/meters/entry110; at2250 onlyDSD63--66 assignments change.',
        native_validation='Require exact pre2250 FZP data parity with existing baseline, all commanded distribution/class readbacks and LDP pass. Failed parity invalidates causal comparison; do not silently change the baseline.',
        interpretation='Mechanism diagnosis only; IDs91/109 are distributions, not deployable91/109kmh VSL actions or SDMPC candidates. No fitting or adoption based on a single seed.',
        pins=pins,helper_sha256=sha(Path(__file__))))
    print(json.dumps(dict(prepared=plans,distributions=definitions,native_started=False)),flush=True)


def countercheck_vsl_shape():
    """One existing FD coefficient, frozen before 12 recorded-case checks.

    This countercheck tests a regression hypothesis. It is not a parameter
    sweep or a production adoption; the opposite-sign late case is mandatory.
    """
    folder=HERE/'baseline_reproduction_20260929/vsl_E4_countercheck'
    folder.mkdir(exist_ok=False)
    manifest_path=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'
    manifest=load(manifest_path)
    original=ROOT/manifest['sources']['reference_config']['path']
    assert sha(original)==manifest['sources']['reference_config']['sha256']
    config=load(original)
    assert config['freeway']['vsl_fd_response']['FW_E']['E']==2.
    config['freeway']['vsl_fd_response']['FW_E']['E']=4.
    candidate=folder/'reference_config.json';save(candidate,config)
    manifest['sources']['reference_config']=dict(path=candidate.relative_to(ROOT).as_posix(),sha256=sha(candidate))
    manifest['qualification']='Diagnostic restoration of historical Carlson E4 with current cell23 coefficients. NOT adopted; no gain qualification.'
    path=folder/'manifest.json';save(path,manifest)
    cases=[('s29_early',HERE/'baseline_reproduction_20260929/component2220_s29_inputs_v2'),
           ('s43_early',HERE/'baseline_reproduction_20260929/component2220_s43_inputs_v2'),
           ('s29_late',OUT)]
    save(folder/'protocol.json',dict(hypothesis='Earlier E4 to E2 changed the sign of beneficial early VSL in cached factorial comparisons. Test E4 once with the latest local cell23 correction, retaining a harmful late VSL case.',
        changed={'freeway.vsl_fd_response.FW_E.E':[2.,4.]},max_rollouts=12,
        cases=[name for name,source in cases],source_manifest=str(manifest_path),source_manifest_sha256=sha(manifest_path),
        candidate_manifest_sha256=sha(path),new_native=0,new_fit=False,future_observation_inputs=False,
        acceptance='Diagnostic only. Preserve RM-only physical arrays, check both signs and stock/flow errors; no automatic adoption or new search if the finite candidate fails.'))
    for name,source in cases:
        predict(manifest_path=path,input_dir=source,output=folder/name)


def compare_saved():
    manifest=load(OUT/'capture.json');checks=[]
    for item in manifest['records']:
        now=OUT/(item['arm']+'_prediction.json.gz')
        before=Path(item['previous_prediction'])
        with gzip.open(now,'rt',encoding='utf-8') as f: actual=json.load(f)
        with gzip.open(before,'rt',encoding='utf-8') as f: old=json.load(f)['rollout']
        for key in ('cells','flows','ports','ramps'):
            assert actual[key]==old[key], (item['arm'],key,'physical replay changed')
        checks.append(dict(arm=item['arm'],arrays_exact=['cells','flows','ports','ramps'],
                           current_sha256=sha(now),previous_sha256=sha(before)))
    save(OUT/'historical_parity.json',dict(passed=True,checks=checks,
        interpretation='Selected current component reproduces the prior wrong response; no new gain calibration',
        no_new_rollouts=True))
    print(json.dumps(dict(parity_cases=len(checks),physical_arrays_exact=True)))


def decompose_saved():
    """Accounting audit of cached outcomes, never forecast inputs or capacity fits."""
    manifest=load(OUT/'capture.json');t0=manifest['cutoff'];end=t0+manifest['horizon']
    steps=[round(t0+x,6) for x in range(0,451,30)]
    all_rows={};pins={};events={};ports={}
    for item in manifest['records']:
        arm=item['arm'];truth=Path(item['truth']);native_manifest=load(truth/'manifest.json')
        def read_csv(name):
            path=truth/name
            assert sha(path)==native_manifest['files'][name],str(path)
            pins[str(path)]=sha(path)
            with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
        cells={(round(float(r['time_s']),6),int(r['cell'])):float(r['n_veh'])
               for r in read_csv('cells_30s.csv') if r['road']=='FW_E'}
        flows={(round(float(r['window_end_s']),6),int(r['cell'])):r
               for r in read_csv('flows_30s.csv') if r['road']=='FW_E'}
        ports[arm]=[r for r in read_csv('ports_30s.csv') if r['road']=='FW_E']
        events[arm]=read_csv('port_events.csv')
        path=OUT/(arm+'_prediction.json.gz');pins[str(path)]=sha(path)
        with gzip.open(path,'rt') as f:p=json.load(f)
        predicted={(round(r['time_s'],6),r['cell']):r['n_veh'] for r in p['cells']}
        pf={(round(r['window_end_s'],6),r['cell']):r for r in p['flows']}
        for c in range(31):predicted[t0,c]=cells[t0,c]
        all_rows[arm]={}
        for c in range(31):
            row={}
            for label,stocks,ff in [('actual',cells,flows),('predicted',predicted,pf)]:
                row[label+'_ttt']=sum((stocks[a,c]+stocks[b,c])*(b-a)/7200 for a,b in zip(steps,steps[1:]))
                for key in ('source_admissions','ramp_merges','off_departures','terminal_exits','downstream_crossings'):
                    source='terminal_exits_inferred' if label=='actual' and key=='terminal_exits' else key
                    row[label+'_'+key]=sum(float(ff[t,c][source]) for t in steps[1:])
                row[label+'_n_final']=stocks[end,c]
            all_rows[arm][c]=row
    base=all_rows['hold'];summary={};series=[];matches={}
    off_ids={r['connector'] for r in ports['hold'] if r['kind']!='ramp'}
    assert off_ids=={'10643','10682','10481','10483'},off_ids
    for arm,rows in all_rows.items():
        if arm=='hold':continue
        differences=[]
        for c,row in rows.items():
            delta={key:row[key]-base[c][key] for key in row}
            delta.update(cell=c,arm=arm,ttt_response_error=delta['predicted_ttt']-delta['actual_ttt'])
            series.append(delta);differences.append(delta)
        ports_delta={}
        for connector in sorted(off_ids):
            def total(name,key):return sum(float(r[key]) for r in ports[name]
                if r['connector']==connector and t0<float(r['window_end_s'])<=end)
            ports_delta[connector]={key:total(arm,key)-total('hold',key) for key in ('arrivals_veh','departures_veh')}
        # Same IDs reaching the same exit; missing IDs are NOT assumed deleted,
        # rerouted, or queued because this event cache cannot distinguish them.
        def exits(name):
            out={}
            for r in events[name]:
                if r['connector'] in off_ids and r['kind']=='arrival' and float(r['time_s'])>t0:
                    out.setdefault(int(r['vehicle']),[]).append((r['connector'],float(r['time_s'])))
            return out
        hold,changed=exits('hold'),exits(arm)
        by_port={}
        for connector in sorted(off_ids):
            ids={v for v,ee in hold.items() if any(c==connector and t<=end for c,t in ee)}
            categories=dict(same_exit_within_horizon=0,same_exit_after_horizon=0,
                            different_exit_only_observed=0,no_east_exit_observed=0)
            later=[]
            for v in ids:
                same=[t for c,t in changed.get(v,[]) if c==connector]
                if same:
                    key='same_exit_within_horizon' if min(same)<=end else 'same_exit_after_horizon'
                    categories[key]+=1
                    h=min(t for c,t in hold[v] if c==connector)
                    later.append(min(same)-h)
                elif changed.get(v):categories['different_exit_only_observed']+=1
                else:categories['no_east_exit_observed']+=1
            assert sum(categories.values())==len(ids)
            by_port[connector]=dict(hold_exit_ids=len(ids),categories=categories,
                                   matched_same_exit_mean_delay_s=sum(later)/len(later) if later else None)
        matches[arm]=by_port
        summary[arm]=dict(component_mainline_deltas={key:sum(r[key] for r in differences)
            for key in ('actual_ttt','predicted_ttt','actual_off_departures','predicted_off_departures',
                        'actual_terminal_exits','predicted_terminal_exits')},
            largest_underestimated_cost_cells=sorted(differences,key=lambda r:r['ttt_response_error'])[:6],
            actual_port_delta=ports_delta)
    checked=load(OUT/'summary.json')
    for r in checked['results']:
        if r['arm']=='hold':continue
        for label in ('actual','predicted'):
            assert abs(summary[r['arm']]['component_mainline_deltas'][label+'_ttt']-
                       r['deltas'][label+'_mainline_ttt'])<1e-7
    with (OUT/'cell_response.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(series[0]));writer.writeheader();writer.writerows(series)
    save(OUT/'spatial_audit.json',dict(summary=summary,matched_exit_events=matches,pins=pins,
        no_new_rollouts=True,no_future_prediction_inputs=True,
        limits='Port events alone do not identify initial destination, final location, removals, or causal rerouting'))
    print(json.dumps({arm:dict(total=x['component_mainline_deltas'],ports=x['actual_port_delta'],
        cells=[(r['cell'],round(r['actual_ttt'],3),round(r['predicted_ttt'],3))
               for r in x['largest_underestimated_cost_cells']]) for arm,x in summary.items()}))


def initial_cohort_exits():
    """Separate known common vehicles from arrivals after the initial snapshot.

    Only the missing whole-network initial frame is read from native FZP.
    All post-initial outcomes come from previously validated event caches.
    """
    source=OLD/'diagnostics/metanet_net_gain_goal_20260924/legal_release2670'
    meta=load(source/'current_route_snapshot/manifest.json');t0=meta['cutoff'];end=t0+450
    path=Path(meta['source']);stat=path.stat()
    assert (stat.st_size,stat.st_mtime_ns)==(meta['size'],meta['mtime_ns'])
    assert meta['network_sha256']==load(OUT/'capture.json')['source_network']
    cache=OUT/'initial_network_cohort.json'
    assert not cache.exists(),'Reuse the completed initial cohort audit, do not rescan'
    digest=hashlib.sha256();initial={};count=0
    with path.open('rb') as f:
        header=None
        for raw in f:
            if raw.startswith(b'$VEHICLE:'):
                header=raw.decode('ascii').strip().split(':',1)[1].split(';')
                fields={k:header.index(k) for k in ('NO','LANE\\LINK\\NO','LANE\\INDEX','POS','ROUTDECNO','ROUTENO')}
                digest.update(raw);continue
            if header is None or raw.startswith((b'*',b'$')) or not raw.strip():
                digest.update(raw);continue
            sec=float(raw.split(b';',1)[0])
            if sec>t0+1e-7:break
            digest.update(raw);count+=1
            if abs(sec-t0)>1e-7:continue
            z=raw.decode('ascii').strip().split(';');row={k:z[i].strip() for k,i in fields.items()}
            no=int(row['NO']);assert no not in initial;initial[no]=row
    assert digest.hexdigest()==meta['prefix_sha256'] and count==meta['scanned_data_rows']
    assert (path.stat().st_size,path.stat().st_mtime_ns)==(stat.st_size,stat.st_mtime_ns)
    prior_snapshot=load(source/'current_route_snapshot/snapshot.json')
    assert len(prior_snapshot)==1035
    for row in prior_snapshot:
        assert all(initial[int(row['NO'])][k]==row[k] for k in fields)
    pins={str(source/'current_route_snapshot/manifest.json'):sha(source/'current_route_snapshot/manifest.json'),
          str(source/'current_route_snapshot/snapshot.json'):sha(source/'current_route_snapshot/snapshot.json')}
    east={int(r['NO']) for r in prior_snapshot};offs={'10643','10682','10481','10483'}
    events={};prefix=None
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        result=load(source/(arm+'_result.json'))
        if prefix is None:prefix=result['prefix_exact']
        assert result['prefix_exact']==prefix
        p=source/'observations'/arm/'port_events.csv';m=load(p.parent/'manifest.json')
        assert sha(p)==m['files'][p.name];pins[str(p)]=sha(p)
        with p.open(encoding='utf-8-sig',newline='') as f:
            events[arm]=[r for r in csv.DictReader(f) if r['kind']=='arrival'
                         and r['connector'] in offs and float(r['time_s'])>t0]
    totals={};paired={}
    for arm,rows in events.items():
        totals[arm]={}
        for off in sorted(offs):
            totals[arm][off]={label:sum(r['connector']==off and float(r['time_s'])<=end and test(int(r['vehicle'])) for r in rows)
                for label,test in [('initial_east',lambda v:v in east),
                                   ('initial_elsewhere',lambda v:v in initial and v not in east),
                                   ('not_present_at_initial',lambda v:v not in initial)]}
        if arm=='hold':continue
        paired[arm]={}
        for off in sorted(offs):
            hold={int(r['vehicle']):float(r['time_s']) for r in events['hold']
                  if r['connector']==off and float(r['time_s'])<=end and int(r['vehicle']) in initial}
            same={int(r['vehicle']):float(r['time_s']) for r in rows if r['connector']==off}
            other={int(r['vehicle']) for r in rows if r['connector']!=off}
            matched=[v for v in hold if v in same]
            differences=[dict(vehicle=v,initial_link=initial[v]['LANE\\LINK\\NO'],
                initial_route=initial[v]['ROUTDECNO']+':'+initial[v]['ROUTENO'],
                changed_exit=[(r['connector'],float(r['time_s'])) for r in rows if int(r['vehicle'])==v])
                for v in hold if v not in same and v in other]
            paired[arm][off]=dict(initial_hold_exit_count=len(hold),
                same_exit_within_horizon=sum(same[v]<=end for v in matched),
                same_exit_after_horizon=sum(same[v]>end for v in matched),
                different_exit_only_observed=differences,
                unresolved_by_end_of_cache=[v for v in hold if v not in same and v not in other],
                matched_delay_sum_s=sum(same[v]-hold[v] for v in matched),
                matched_delay_mean_s=sum(same[v]-hold[v] for v in matched)/len(matched) if matched else None)
    save(cache,dict(cutoff=t0,vehicles=initial,source_meta=meta))
    pins[str(cache)]=sha(cache)
    summary=dict(initial_network_count=len(initial),initial_east_count=len(east),totals=totals,paired=paired,
        pins=pins,precontrol_prefix=prefix,future_model_inputs=False,new_rollouts=0,
        limits='Known initial IDs are comparable; later creation identities are not certified. Missing cached exit is not proof of deletion or rerouting. Exit timing includes full network interaction and is not an identified local capacity.')
    save(OUT/'initial_cohort_exit_audit.json',summary)
    print(json.dumps(dict(initial_network=len(initial),initial_east=len(east),totals=totals,paired=paired)))


def cohort_delay_bounds():
    audit=load(OUT/'initial_cohort_exit_audit.json')
    cache=OUT/'initial_network_cohort.json'
    assert sha(cache)==audit['pins'][str(cache)]
    initial=load(cache);ids=set(map(int,initial['vehicles']));t0=initial['cutoff'];end=t0+450
    source=OLD/'diagnostics/metanet_net_gain_goal_20260924/legal_release2670/observations'
    rows={}
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        p=source/arm/'port_events.csv';assert sha(p)==audit['pins'][str(p)]
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows[arm]={(int(r['vehicle']),r['connector']):r for r in csv.DictReader(f)
                       if r['kind']=='arrival' and int(r['vehicle']) in ids and float(r['time_s'])>t0}
    result={}
    for arm in ('release','hold_vsl90','release_vsl90'):
        result[arm]={}
        for off,expected in audit['paired'][arm].items():
            matched=[(r,rows[arm][key]) for key,r in rows['hold'].items() if key[1]==off
                     and float(r['time_s'])<=end and key in rows[arm]]
            assert len(matched)==expected['same_exit_within_horizon']+expected['same_exit_after_horizon']
            lower=sum(float(b['lower_time_s'])-float(a['upper_time_s']) for a,b in matched)
            upper=sum(float(b['upper_time_s'])-float(a['lower_time_s']) for a,b in matched)
            measured=sum(float(b['time_s'])-float(a['time_s']) for a,b in matched)
            assert lower<=measured<=upper
            result[arm][off]=dict(matched=len(matched),delay_mean_s=measured/len(matched),
                mean_lower_s=lower/len(matched),mean_upper_s=upper/len(matched))
    save(OUT/'initial_cohort_delay_bounds.json',dict(results=result,source_audit_sha256=sha(OUT/'initial_cohort_exit_audit.json'),
        interpretation='Deterministic crossing-time brackets from FZP5; not a confidence interval or local capacity estimate. Same-exit matching conditions on the eventual outcome.',
        new_scans=0,new_rollouts=0))
    print(json.dumps(result))


DECISIONS=HERE/'decision_response'


def capture_decisions():
    """Reuse past-only builders for two training and two checking contexts."""
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c;data,ctx,_,_=c.inputs()
    DECISIONS.mkdir(exist_ok=False)
    records=[]
    # Already captured, same current selected component; no repeated forecast.
    previous=load(OUT/'capture.json')
    for row in previous['records']:
        p=OUT/row['input'];assert sha(p)==row['sha256']
        records.append(dict(row,case='s29_late',role='train',reference='hold',
                            cutoff=2670.1,input=str(p)))
    frozen=load(e.HERE/'heldout43/freeze.json')
    model=c.prior.one.base.load_base_model(data['none'].geometry,e.HERE/'local_fd/candidate.json')
    parameters=load(HERE/'selected/port_gain/parameters.json')['parameters']
    class Captured(BaseException):pass
    for seed in (29,43,47):
        late=seed==47
        case=f's{seed}_'+('late' if late else 'early')
        cutoff=2670.1 if late else 2220.1
        if late:
            folder=e.HERE/'release2670_seed47'
            state=c.prior.ObservationData(folder/'observations/hold')
            port_profile=load(folder/'protocol.json')['port_profile']
            arms=('hold','release_10490','release_10484','hold_vsl90')
        else:
            state=data['none'] if seed==29 else c.prior.ObservationData(e.r.HERE/'gain_response/seed43/none')
            port_profile=frozen['port_profile'];arms=('none','vsl','rm','both')
        local_ctx=list(copy.deepcopy(ctx));local_ctx[3]=port_profile
        for arm in arms:
            commands=({int(t):v for t,v in load(folder/f'{arm}_commands.json').items()}
                      if late else c.exp.commands(arm,ctx[0],ctx[-1]))
            if late:truth=folder/'observations'/arm
            elif arm=='none':truth=state.folder
            elif seed==43:truth=e.HERE/'heldout43/observations'/arm
            else:truth=c.exp.HERE/'observations'/arm
            assert (truth/'cells_30s.csv').is_file(),str(truth)
            def intercept(*args,**kwargs):
                json.dumps([args,kwargs],allow_nan=False)
                p=DECISIONS/f'{case}_{arm}.pickle'
                p.write_bytes(pickle.dumps((args,kwargs),protocol=5))
                records.append(dict(case=case,role='train' if seed==29 else 'check',
                    reference=arms[0],arm=arm,cutoff=cutoff,input=str(p),sha256=sha(p),
                    truth=str(truth),commands_sha256=hashlib.sha256(json.dumps(commands,sort_keys=True).encode()).hexdigest()))
                raise Captured()
            model.rollout=intercept
            try:
                c.prior.forecast(model,parameters,state,state,cutoff,450,*local_ctx[:-1],commands,True)
                raise AssertionError('Input capture failed')
            except Captured:pass
    save(DECISIONS/'capture.json',dict(records=records,source_network=previous['source_network'],
        new_rollouts=0,future_truth_used_as_input=False,
        role_note='29 early+late training;43 early and47 late checking only, previously inspected development data, NOT pristine holdout',
        builder_sha256={str(p):sha(p) for p in (Path(c.prior.__file__),Path(__file__))}))
    print(json.dumps(dict(captured=len(records),path=str(DECISIONS))),flush=True)


def decision_screen():
    """Finite direct-response calibration of existing physical coefficients.

    Costs retain physical stocks. No fitted objective correction, command bonus,
    future input or per-vehicle timing calibration is introduced.
    """
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    assert not (DECISIONS/'screen.json').exists(),'Preserve completed screening'
    manifest=load(DECISIONS/'capture.json');context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    model=context['component'];records=manifest['records'];payloads={};truths={};actual={}
    port_ids={str(r['connector']) for r in model.ramps.values() if r['road']=='FW_E'}
    port_ids|={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
    def integral(values,times):
        return sum((values[a]+values[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
    def key(r):return r['case']+'/'+r['arm']
    for r in records:
        p=Path(r['input']);assert sha(p)==r['sha256']
        payloads[key(r)]=pickle.loads(p.read_bytes())
        assert payloads[key(r)][0][2]==context['parameters']
        truth=ObservationData(r['truth']);truths[key(r)]=truth
        times=[round(r['cutoff']+d,6) for d in range(0,451,30)]
        main={t:sum(x['n_veh'] for x in truth.cells[t] if x['road']=='FW_E') for t in times}
        port={t:sum(float(truth.ports[t,c]['end_n_veh']) for c in port_ids) for t in times}
        actual[key(r)]=dict(main=integral(main,times),port=integral(port,times))
        actual[key(r)]['total']=sum(actual[key(r)].values())
    train=[r for r in records if r['role']=='train'];check=[r for r in records if r['role']=='check']
    baseline_response=copy.deepcopy(model.base.network.freeway_state_response)
    baseline_fd=copy.deepcopy(model.base.network.freeway_vsl_fd_response)
    # Two bounded, existing coefficients only. Freeze this finite design before
    # scoring candidates; no adaptive enlargement if the result is unfavourable.
    grid=[(d,e) for d in (0.,1.,2.,4.,6.) for e in (1.,2.,4.)]
    protocol=dict(delta_merge=sorted({d for d,e in grid}),carlson_E=sorted({e for d,e in grid}),
        fixed_carlson_A=baseline_fd['FW_E']['A'],fit_scope='All four east physical merge cells share delta; original FD and all other terms retained',
        objective='Mean per-state squared error of signed component DeltaTTT, normalized by max(1,max absolute measured contrast) within state',
        counts=dict(train_cases=2,train_arms=8,check_cases=2,check_arms=8,max_training_rollouts=120,max_check_rollouts=16),
        physical_cost_scope='East31 cells plus4 on/4 off connectors; no full urban/external cost claim',
        production_changed=False,source_pins={str(p):sha(p) for p in (Path(__file__),Path(lpr.__file__),Path(sys.modules[model.__class__.__module__].__file__),HERE/'selected/plant_n31_v2.json')})
    protocol_path=DECISIONS/'protocol.json'
    if protocol_path.exists():
        previous=load(protocol_path)
        assert {k:v for k,v in previous.items() if k!='source_pins'}=={k:v for k,v in protocol.items() if k!='source_pins'}
        save(DECISIONS/'resume.json',dict(reason='Runtime tuple versus JSON list comparison only; physical arrays exact',
            previous_protocol_sha256=sha(protocol_path),current_helper_sha256=sha(Path(__file__)),
            reused_candidates=sorted(p.name for p in DECISIONS.glob('train_d*_e*.json'))))
    else:save(protocol_path,protocol)
    def evaluate(delta,e,rows):
        model.base.network.freeway_state_response=copy.deepcopy(baseline_response)
        for ramp in model.ramps.values():
            if ramp['road']=='FW_E':
                cell=str(ramp['to_cell'])
                model.base.network.freeway_state_response['FW_E']['cell_overrides'].setdefault(cell,{})['delta_merge']=delta
        model.base.network.freeway_vsl_fd_response=copy.deepcopy(baseline_fd)
        model.base.network.freeway_vsl_fd_response['FW_E']['E']=e
        out=[]
        for r in rows:
            args,kwargs=copy.deepcopy(payloads[key(r)])
            t0=r['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
            pred=model.rollout(*args,**kwargs)
            score=score_rollout(truths[key(r)],t0,pred,'FW_E',include_source_boundary=True)
            assert not score['invalid'],score['diagnostics']
            residual=max([abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps']])
            assert residual<1e-7
            main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
            port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
            truth=truths[key(r)]
            main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
            port[t0]=sum(float(truth.ports[t0,c]['end_n_veh']) for c in port_ids)
            pp=dict(main=integral(main,times),port=integral(port,times));pp['total']=sum(pp.values())
            if delta==1. and e==4. and r['case']=='s29_late':
                with gzip.open(OUT/(r['arm']+'_prediction.json.gz'),'rt') as f:old=json.load(f)
                assert all(json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps')),'Baseline physical arrays changed'
            out.append(dict(case=r['case'],arm=r['arm'],reference=r['reference'],predicted=pp,actual=actual[key(r)],
                merge=sum(x['accepted_merge_veh'] for x in pred['ramps']),conservation_max=residual,
                speed_rmse=score['speed']['rmse'],mainline_n_rmse=score['cell_n']['rmse']))
        choices=[];losses=[]
        for case in sorted({r['case'] for r in out}):
            group=[r for r in out if r['case']==case];base=next(r for r in group if r['arm']==r['reference'])
            for r in group:
                r['actual_delta']=r['actual']['total']-base['actual']['total']
                r['predicted_delta']=r['predicted']['total']-base['predicted']['total']
            scale=max(1.,max(abs(r['actual_delta']) for r in group))
            losses.append(sum(((r['predicted_delta']-r['actual_delta'])/scale)**2 for r in group if r!=base)/(len(group)-1))
            picked=min(group,key=lambda r:r['predicted']['total']);best=min(group,key=lambda r:r['actual']['total'])
            choices.append(dict(case=case,selected=picked['arm'],observed_best=best['arm'],
                component_regret=picked['actual']['total']-best['actual']['total']))
        return dict(delta_merge=delta,carlson_E=e,loss=sum(losses)/len(losses),rows=out,choices=choices)
    candidates=[];started=time.perf_counter()
    for d,e in grid:
        path=DECISIONS/f'train_d{d:g}_e{e:g}.json'
        if path.exists():
            result=load(path)
            assert result['delta_merge']==d and result['carlson_E']==e and len(result['rows'])==len(train)
        else:
            result=evaluate(d,e,train)
            save(path,result)
        candidates.append(result)
        print(json.dumps(dict(delta=d,E=e,loss=result['loss'],choices=result['choices'])),flush=True)
    selected=min(candidates,key=lambda r:r['loss'])
    # Freeze training selection before loading held-back outcome values into
    # any calibration objective. These are developmental checks, not untouched data.
    save(DECISIONS/'selection.json',dict(delta_merge=selected['delta_merge'],carlson_E=selected['carlson_E'],training_loss=selected['loss']))
    checks=[evaluate(1.,4.,check)]
    if (selected['delta_merge'],selected['carlson_E'])!=(1.,4.):
        checks.append(evaluate(selected['delta_merge'],selected['carlson_E'],check))
    save(DECISIONS/'screen.json',dict(candidates=candidates,checks=checks,elapsed_sec=time.perf_counter()-started,
        training_rollouts=len(grid)*len(train),check_rollouts=len(checks)*len(check),selected=load(DECISIONS/'selection.json'),
        gain_qualified=False,production_adopted=False,new_native_runs=0,independent_holdout=False))
    print(json.dumps(dict(selected=load(DECISIONS/'selection.json'),checks=[x['choices'] for x in checks],elapsed_sec=time.perf_counter()-started)),flush=True)


def anticipation_response(*, merge_speed=False, lane_drop=False):
    """Two bounded shock-response alternatives; signed cost and choice, no speed fit."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    model=context['component'];records=load(DECISIONS/'capture.json')['records']
    assert not (merge_speed and lane_drop)
    out=HERE/('lane_drop_response' if lane_drop else 'merge_speed_response' if merge_speed else 'anticipation_response')
    out.mkdir(exist_ok=False)
    cached=load(DECISIONS/'screen.json')
    baseline_rows=next(r for r in cached['candidates'] if r['delta_merge']==1. and r['carlson_E']==4.)['rows']
    baseline_rows+=next(r for r in cached['checks'] if r['delta_merge']==1. and r['carlson_E']==4.)['rows']
    baseline={(r['case'],r['arm']):r for r in baseline_rows}
    response=copy.deepcopy(model.base.network.freeway_state_response)
    affected=sorted(response['FW_E']['cell_overrides'],key=int)
    nu=context['parameters']['by_direction']['FW_E']['nu_km2_h']
    assert nu==36.75
    assert all(response['FW_E']['cell_overrides'][c]['anticipation']==
               {'downstream_ge_local':18.375,'downstream_lt_local':18.375} for c in affected)
    variants={'formation_nominal':dict(downstream_ge_local=nu,downstream_lt_local=nu/2),
              'both_nominal':dict(downstream_ge_local=nu,downstream_lt_local=nu)}
    if merge_speed:
        variants={'flow_weighted_merge': None}
    if lane_drop:
        assert model.base.network.freeway_lane_drop_phi==3.
        assert not any('freeway_lane_drop_phi' in p for p in
                       (getattr(model.base.network,'metanet_parameters_by_direction',{}) or {}).values())
        variants={'no_extra_lane_drop_deceleration':None}
    rollout_count=2+len(variants)*len(records)
    save(out/'protocol.json',dict(variants=variants,affected_cells=affected,
        reason=('Only phi3 to0 ablation: retain physical4-to3 lanes, off storage/lane loss, merge and FD. Existing model underfeeds downstream merges while falsely slowing cell18. No capacity bonus.' if lane_drop else
                'METANET virtual inlet uses actual accepted mainline/ramp flows and causal calibrated ramp travel speed; no new capacity or reward.' if merge_speed else
                'Current ramp-neighbour anticipation is half the directional nominal. Test stronger upstream braking and separately symmetric nominal recovery.'),
        unchanged='All other coefficients, physical controls, arrivals, geometry, waiting costs and initial states.',
        cutoff_and_seed='29early2220.1+late2670.1 development;43early+47late checking, previously inspected, not pristine holdout',
        evaluation='Signed component DeltaTTT and candidate regret; no speed RMSE objective',
        cost_scope='East31 plus4 on/4 off connectors, NOT whole Omega or external input waiting',
        max_rollouts=rollout_count,production_adopted=False,native_runs=0,
        sources={str(p):sha(p) for p in (Path(__file__),Path(lpr.__file__),
            HERE/'selected/plant_n31_v2.json',DECISIONS/'capture.json',DECISIONS/'screen.json')}))
    payloads={}
    for r in records:
        p=Path(r['input']);assert sha(p)==r['sha256']
        args,kwargs=read_primitive_capture(p,r['sha256'])
        assert args[2]==context['parameters']
        payloads[r['case'],r['arm']]=(args,kwargs)
    parity=[]
    for arm in ('hold','release'):
        args,kwargs=copy.deepcopy(payloads['s29_late',arm]);pred=model.rollout(*args,**kwargs)
        with gzip.open(OUT/(arm+'_prediction.json.gz'),'rt') as f: previous=json.load(f)
        assert all(json.loads(json.dumps(pred[k]))==previous[k] for k in ('cells','flows','ports','ramps'))
        parity.append(dict(arm=arm,all_physical_arrays_exact=True))
    save(out/'baseline_parity.json',parity)
    variants_results=[]
    for name,coefficients in variants.items():
        model.base.network.freeway_state_response=copy.deepcopy(response)
        if lane_drop:
            model.base.network.freeway_lane_drop_phi=0.
        elif merge_speed:
            model.aggregate_merge_speed=True
        else:
            for c in affected:
                model.base.network.freeway_state_response['FW_E']['cell_overrides'][c]['anticipation']=copy.deepcopy(coefficients)
        rows=[]
        for r in records:
            key=r['case'],r['arm'];args,kwargs=copy.deepcopy(payloads[key])
            started=time.perf_counter();pred=model.rollout(*args,**kwargs)
            t0=r['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
            main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
            port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
                  sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
            main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
            # Read the common initial port stock only after the forecast. Future
            # observations are scoring evidence, never rollout inputs.
            from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
            truth=ObservationData(r['truth'])
            ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
            ids|={str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
            port[t0]=sum(float(truth.ports[t0,c]['end_n_veh']) for c in ids)
            integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            costs=dict(main=integral(main),port=integral(port));costs['total']=sum(costs.values())
            residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
            assert residual<1e-7
            flows={k:sum(float(x[k]) for x in pred['flows']) for k in
                   ('source_admissions','off_departures','terminal_exits')}
            row=dict(case=r['case'],arm=r['arm'],reference=r['reference'],predicted=costs,
                actual=baseline[key]['actual'],merge=sum(x['accepted_merge_veh'] for x in pred['ramps']),
                flows=flows,conservation_max=residual,wall_sec=time.perf_counter()-started)
            rows.append(row)
            print(json.dumps(dict(variant=name,case=r['case'],arm=r['arm'],ttt=costs['total'])),flush=True)
        choices=[]
        for case in sorted({r['case'] for r in rows}):
            group=[r for r in rows if r['case']==case];held=next(r for r in group if r['arm']==r['reference'])
            for r in group:
                r['predicted_delta']=r['predicted']['total']-held['predicted']['total']
                r['actual_delta']=r['actual']['total']-held['actual']['total']
            chosen=min(group,key=lambda r:r['predicted']['total']);best=min(group,key=lambda r:r['actual']['total'])
            choices.append(dict(case=case,selected=chosen['arm'],observed_best=best['arm'],
                                component_regret=chosen['actual']['total']-best['actual']['total']))
        result=dict(name=name,coefficients=coefficients,rows=rows,choices=choices)
        save(out/(name+'.json'),result);variants_results.append(result)
    save(out/'summary.json',dict(variants=variants_results,baseline_rows=baseline_rows,
        new_rollouts=rollout_count,production_adopted=False,gain_qualified=False,native_runs=0))
    print(json.dumps(dict(choices={r['name']:r['choices'] for r in variants_results})),flush=True)


def receiving_audit():
    """Observe shared storage allocation without substituting a capacity law."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json');model=context['component']
    from evaluation.controllers import area_freeway_accounting as accounting
    out=HERE/'receiving_audit';out.mkdir(exist_ok=False)
    manifest=load(OUT/'capture.json');original=accounting._freeway_substep_events
    save(out/'protocol.json',dict(max_rollouts=2,coefficient_changes=False,production_changed=False,
        hypothesis='Determine whether the joint mainline+ramp allocation binds storage, and whether an existing equilibrium FD peak is a defensible hard inflow cap.',
        scope='Same2670.1 state hold/release; observation only. An equilibrium peak is NOT assumed to be a transient upper bound.',
        sources={str(p):sha(p) for p in (Path(__file__),Path(accounting.__file__),OUT/'capture.json',HERE/'selected/plant_n31_v2.json')}))
    all_rows=[];summaries=[]
    for arm in ('hold','release'):
        record=next(r for r in manifest['records'] if r['arm']==arm)
        args,kwargs=read_primitive_capture(OUT/record['input'],record['sha256'])
        assert args[2]==context['parameters'];observations=[];tick=0
        def observe(state,control,demand,cfg,**options):
            nonlocal tick
            net=cfg.network;road='FW_E';dt=cfg.simulation.T_f_h
            assert net.capacity_drop_discharge_phi==1 and not getattr(net,'freeway_hadiuzzaman',None)
            assert not accounting._routing.inventory_enabled(cfg)
            lanes,_=accounting._mn.effective_lane_profile(state,cfg,demand)
            stocks=accounting.continuity_vehicle_counts(state,cfg)[road]
            lengths=accounting.cell_lengths_km(cfg,road,len(stocks))
            q=[n/length*v for n,length,v in zip(stocks,lengths,state.freeway_speed[road])]
            assert len(set(net.ramp_merge_segment_index.values()))==len(net.ramps)
            for ramp in net.ramps:
                i=net.ramp_merge_segment_index[ramp];assert i>0
                split=sum(net.off_ramp_split_ratio[o] for o in net.off_ramps if net.off_ramp_segment_index[o]==i-1)
                requested=q[i-1]*(1-split)
                merge=options['ramp_release_veh_h'][ramp]
                storage=max(0.,net.rho_max*lanes[road][i]*lengths[i]-stocks[i])/dt
                accepted=min(requested,max(0.,storage-merge))
                fd=net.freeway_segment_params[road][i]
                peak=lanes[road][i]*fd['v_free']*fd['rho_crit']*math.exp(-1/fd['metanet_a_m'])
                observations.append(dict(arm=arm,time_s=manifest['cutoff']+tick,ramp=ramp,cell=i,
                    main_requested_vph=requested,main_accepted_vph=accepted,merge_vph=merge,
                    combined_vph=accepted+merge,storage_supply_vph=storage,nominal_fd_peak_vph=peak,
                    storage_binding=accepted<requested-1e-7,above_fd_peak=accepted+merge>peak+1e-7))
            tick+=1
            return original(state,control,demand,cfg,**options)
        accounting._freeway_substep_events=observe
        try:pred=model.rollout(*args,**kwargs)
        finally:accounting._freeway_substep_events=original
        with gzip.open(OUT/(arm+'_prediction.json.gz'),'rt') as f:old=json.load(f)
        assert all(json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps'))
        truth=ObservationData(record['truth'])
        for ramp,spec in model.ramps.items():
            if spec['road']!='FW_E':continue
            i=spec['to_cell'];group=[r for r in observations if r['ramp']==ramp]
            rate_mean=lambda key:sum(r[key] for r in group)/len(group)
            main_count=sum(r['downstream_crossings'] for r in pred['flows'] if r['cell']==i-1)
            merge_count=sum(r['ramp_merges'] for r in pred['flows'] if r['cell']==i)
            assert abs(main_count-rate_mean('main_accepted_vph')*450/3600)<1e-7
            assert abs(merge_count-rate_mean('merge_vph')*450/3600)<1e-7
            actual_main=sum(float(v['downstream_crossings']) for (t,road,cell),v in truth.flows.items()
                            if road=='FW_E' and cell==i-1 and manifest['cutoff']<t<=manifest['cutoff']+450)
            actual_merge=sum(float(v['ramp_merges']) for (t,road,cell),v in truth.flows.items()
                             if road=='FW_E' and cell==i and manifest['cutoff']<t<=manifest['cutoff']+450)
            summaries.append(dict(arm=arm,ramp=ramp,cell=i,steps=len(group),
                storage_binding_steps=sum(r['storage_binding'] for r in group),
                above_fd_peak_steps=sum(r['above_fd_peak'] for r in group),
                storage_supply_min_vph=min(r['storage_supply_vph'] for r in group),
                nominal_fd_peak_mean_vph=rate_mean('nominal_fd_peak_vph'),
                model_combined_mean_vph=rate_mean('combined_vph'),
                actual_combined_mean_vph=(actual_main+actual_merge)*3600/450,
                model_main_veh=main_count,actual_main_veh=actual_main,
                model_merge_veh=merge_count,actual_merge_veh=actual_merge))
        all_rows+=observations
        print(json.dumps(dict(arm=arm,baseline_arrays_exact=True,recorded_steps=tick)),flush=True)
    with (out/'allocation_steps.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
    save(out/'summary.json',dict(rows=summaries,new_rollouts=2,baseline_arrays_exact=True,
        predicted_allocation_reconstruction_passed=True,new_native_runs=0,production_changed=False))
    print(json.dumps(summaries),flush=True)


def decision_regret_check():
    """Reuse the finite grid; freeze by training choice loss, check eight arms."""
    cached=load(DECISIONS/'screen.json');out=HERE/'decision_regret_check'
    out.mkdir(exist_ok=False)
    ranking=[]
    for candidate in cached['candidates']:
        ranking.append(dict(delta_merge=candidate['delta_merge'],carlson_E=candidate['carlson_E'],
            train_choice_loss=sum(c['component_regret'] for c in candidate['choices']),
            train_choices=candidate['choices'],previous_delta_cost_loss=candidate['loss']))
    # Among identical training choices, prefer the smaller merge change and
    # the VSL coefficient closest to the existing E=4. No checking outcomes.
    ranking.sort(key=lambda r:(r['train_choice_loss'],r['delta_merge'],-r['carlson_E']))
    selected=ranking[0]
    save(out/'selection.json',dict(selected=selected,ranking=ranking,
        policy='Minimize sum of observed candidate regret on the two existing training states; exact ties: smaller delta, then larger E. No new grid or fitted reward.',
        evidence_sha256=sha(DECISIONS/'screen.json'),independent_holdout=False,
        selection_frozen_before_check_predictions=True,max_new_rollouts=8))
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json');model=context['component']
    for ramp in model.ramps.values():
        if ramp['road']=='FW_E':
            cell=str(ramp['to_cell'])
            model.base.network.freeway_state_response['FW_E']['cell_overrides'].setdefault(cell,{})['delta_merge']=selected['delta_merge']
    model.base.network.freeway_vsl_fd_response['FW_E']['E']=selected['carlson_E']
    baseline=next(r for r in cached['checks'] if r['delta_merge']==1 and r['carlson_E']==4)
    actual={(r['case'],r['arm']):r['actual'] for r in baseline['rows']}
    records=[r for r in load(DECISIONS/'capture.json')['records'] if r['role']=='check']
    assert len(records)==8
    ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}
    ids|={off for off,v in model.offramps.items() if v['road']=='FW_E'}
    rows=[]
    for record in records:
        args,kwargs=read_primitive_capture(record['input'],record['sha256'])
        assert args[2]==context['parameters']
        pred=model.rollout(*args,**kwargs)
        with gzip.open(out/(record['case']+'_'+record['arm']+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
        truth=ObservationData(record['truth'])
        score=score_rollout(truth,record['cutoff'],pred,'FW_E',include_source_boundary=True)
        assert not score['invalid']
        t0=record['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
        main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
        port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
            sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
        main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
        port[t0]=sum(float(truth.ports[t0,off]['end_n_veh']) for off in ids)
        integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
        residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
        assert residual<1e-7
        costs=dict(main=integral(main),port=integral(port));costs['total']=sum(costs.values())
        rows.append(dict(case=record['case'],arm=record['arm'],reference=record['reference'],
            predicted=costs,actual=actual[record['case'],record['arm']],conservation_max=residual))
        print(json.dumps(dict(case=record['case'],arm=record['arm'],ttt=costs['total'])),flush=True)
    choices=[]
    for case in sorted({r['case'] for r in rows}):
        group=[r for r in rows if r['case']==case];reference=next(r for r in group if r['arm']==r['reference'])
        for r in group:
            r['predicted_delta']=r['predicted']['total']-reference['predicted']['total']
            r['actual_delta']=r['actual']['total']-reference['actual']['total']
        ordered=sorted(group,key=lambda r:r['predicted']['total']);pick=ordered[0]
        best=min(group,key=lambda r:r['actual']['total'])
        choices.append(dict(case=case,selected=pick['arm'],observed_best=best['arm'],
            component_regret=pick['actual']['total']-best['actual']['total'],
            predicted_margin_to_second=ordered[1]['predicted']['total']-pick['predicted']['total']))
    save(out/'summary.json',dict(selected=selected,rows=rows,choices=choices,
        previous_choices=baseline['choices'],new_rollouts=8,new_training_rollouts=0,
        production_adopted=False,gain_qualified=False,native_runs=0,
        scope='East31 plus8 connectors only; seed43/47 previously inspected development checks, not pristine validation.',
        pins={str(p):sha(p) for p in (Path(__file__),HERE/'selected/plant_n31_v2.json',DECISIONS/'capture.json')}))
    print(json.dumps(dict(choices=choices)),flush=True)


def off_entry_response():
    """Identify a binding observed-entry proxy; eight fixed diagnostic forecasts."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json');model=context['component']
    from evaluation.controllers import area_freeway_accounting as accounting
    manifest=load(OUT/'capture.json');out=HERE/'off_entry_response'
    out.mkdir(exist_ok=False)
    assert context['document']['sources']['network']['sha256']==manifest['source_network']
    save(out/'protocol.json',dict(
        hypothesis='A held observed off-entry rate is used as receiving capacity even with spare physical storage; identify binding before changing any production setting.',
        variants=['storage_and_proxy','storage'],max_rollouts=8,
        unchanged='Initial state, all parameters, splits, arrival/drain forecasts, controls, storage, travel time and cost.',
        source='Existing common2670.1 state seed29; development evidence, not an independent holdout.',
        scope='East31 and4on/4off connector residence; not whole Omega or all outside waiting.',
        production_adopted=False,native_runs=0,
        pins={str(p):sha(p) for p in (Path(__file__),OUT/'capture.json',HERE/'selected/plant_n31_v2.json',
            Path(accounting.__file__),Path(sys.modules[model.__class__.__module__].__file__))}))
    original=accounting._freeway_substep_events;rows=[]
    for mode in ('storage_and_proxy','storage'):
        for record in manifest['records']:
            args,kwargs=read_primitive_capture(OUT/record['input'],record['sha256'])
            assert args[2]==context['parameters']
            assert kwargs['port_dynamics']['entry_capacity_mode']=='storage_and_proxy'
            kwargs['port_dynamics']['entry_capacity_mode']=mode
            counters={off:dict(steps=0,binding_steps=0,proxy_below_storage_steps=0,
                blocked_request_veh=0.,accepted_veh=0.,min_storage_room_veh=float('inf'))
                for off,spec in model.offramps.items() if spec['road']=='FW_E'}
            def observe(state,control,demand,cfg,**options):
                dt=cfg.simulation.T_f_h
                caps=options['offramp_capacity_veh_h']
                available={off:float(state.urban_link_storage[cfg.network.off_ramp_storage_link[off]])
                           for off in counters}
                value=original(state,control,demand,cfg,**options);diag=value[1]
                for off,counter in counters.items():
                    blocked=diag['offramp_blocked_flow_'+off]
                    counter['steps']+=1
                    counter['binding_steps']+=int(blocked>1e-7)
                    counter['proxy_below_storage_steps']+=int(caps[off]*dt<available[off]-1e-7)
                    counter['blocked_request_veh']+=blocked*dt
                    counter['accepted_veh']+=diag['offramp_flow_'+off]*dt
                    counter['min_storage_room_veh']=min(counter['min_storage_room_veh'],available[off])
                return value
            accounting._freeway_substep_events=observe
            try:pred=model.rollout(*args,**kwargs)
            finally:accounting._freeway_substep_events=original
            arm=record['arm']
            if mode=='storage_and_proxy':
                with gzip.open(OUT/(arm+'_prediction.json.gz'),'rt') as f:old=json.load(f)
                assert all(json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps'))
            with gzip.open(out/(mode+'_'+arm+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            truth=ObservationData(record['truth']) # Future evidence opened after prediction only.
            score=score_rollout(truth,manifest['cutoff'],pred,'FW_E',include_source_boundary=True)
            assert not score['invalid']
            t0=manifest['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
            ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|set(counters)
            main={t:sum(x['n_veh'] for x in pred['cells'] if abs(x['time_s']-t)<1e-6) for t in times[1:]}
            port={t:sum(x['n_veh'] for x in pred['ports'] if abs(x['time_s']-t)<1e-6)+
                sum(x['end']['connector_veh'] for x in pred['ramps'] if abs(x['end_sec']-t)<1e-6) for t in times[1:]}
            main[t0]=sum(x['n_veh'] for x in args[0] if x['road']=='FW_E')
            port[t0]=sum(float(truth.ports[t0,off]['end_n_veh']) for off in ids)
            integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            residual=max(abs(x['conservation_residual_veh']) for x in pred['ports']+pred['ramps'])
            assert residual<1e-7
            previous=load(OUT/(arm+'_result.json'))
            row=dict(mode=mode,arm=arm,main_ttt=integral(main),port_ttt=integral(port),
                actual_component_ttt=previous['actual_component_ttt'],off_entry=counters,
                flows={k:sum(float(x[k]) for x in pred['flows']) for k in
                    ('source_admissions','off_departures','terminal_exits')},
                conservation_max=residual,invalid=score['invalid'])
            row['component_ttt']=row['main_ttt']+row['port_ttt'];rows.append(row)
            save(out/(mode+'_'+arm+'_summary.json'),row)
            print(json.dumps(dict(mode=mode,arm=arm,ttt=row['component_ttt'])),flush=True)
    for row in rows:
        held=next(r for r in rows if r['mode']==row['mode'] and r['arm']=='hold')
        row['predicted_delta']=row['component_ttt']-held['component_ttt']
        row['actual_delta']=row['actual_component_ttt']-held['actual_component_ttt']
    save(out/'summary.json',dict(rows=rows,new_rollouts=8,baseline_arrays_exact=True,
        production_adopted=False,gain_qualified=False,native_runs=0))


def prepare_seed53_response():
    """Freeze the previously selected partial improvement before new traffic."""
    import os,re,shutil,subprocess
    from evaluation.controllers import lane_plant_runtime as lpr
    out=HERE/'heldout53_response_v2';runs=Path('D:/VISSIM_runs/20260928_release2670_s53_v2')
    assert not out.exists() and not runs.exists(), 'Preserve previous attempts; no automatic retry'
    context=lpr.load_sources(HERE/'selected/plant_n31_v2.json')
    chosen=load(HERE/'decision_regret_check/selection.json')['selected']
    assert chosen['delta_merge']==4. and chosen['carlson_E']==2.
    out.mkdir();runs.mkdir();(runs/'source').mkdir();(runs/'runtime').mkdir()
    baseline=load(HERE/'selected/plant_n31_v2.json')
    original_config=ROOT/baseline['sources']['reference_config']['path']
    config=load(original_config)
    cells=sorted({int(r['to_cell']) for r in context['component'].ramps.values() if r['road']=='FW_E'})
    assert cells==[10,12,21,23]
    for cell in cells:
        config['freeway']['state_response']['FW_E']['cell_overrides'].setdefault(str(cell),{})['delta_merge']=4.
    assert config['freeway']['vsl_fd_response']['FW_E']['E']==4.
    config['freeway']['vsl_fd_response']['FW_E']['E']=2.
    save(out/'candidate_config.json',config)
    candidate=copy.deepcopy(baseline)
    candidate['sources']['reference_config']=dict(path=(out/'candidate_config.json').relative_to(ROOT).as_posix(),sha256=sha(out/'candidate_config.json'))
    candidate['qualification']='FROZEN EXPERIMENTAL delta4/E2: partial choice-loss improvement, not gain qualified or production adopted.'
    save(out/'candidate_manifest.json',candidate)
    check=lpr.load_sources(out/'candidate_manifest.json')['component']
    assert check.base.network.freeway_vsl_fd_response['FW_E']['E']==2.
    assert all(check.base.network.freeway_state_response['FW_E']['cell_overrides'][str(c)]['delta_merge']==4. for c in cells)
    source=ROOT/baseline['sources']['network']['path'];raw=source.read_bytes()
    assert sha(source)=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    revised,count=re.subn(rb'(<simulation\b[^>]*\brandSeed=")29(")',rb'\g<1>53\2',raw)
    assert count==1 and re.sub(rb'(<simulation\b[^>]*\brandSeed=")53(")',rb'\g<1>29\2',revised)==raw
    prior=Path('D:/VISSIM_runs/20260924_release2670_s29')
    for p in (prior/'source').iterdir():
        if p.is_file() and p.suffix.lower()!='.inpx':shutil.copy2(p,runs/'source'/p.name)
    arms=['hold','release','hold_vsl90','release_vsl90'];profiles={};plans=[];pins={}
    for arm in arms:
        profile=load(prior/(arm+'.json'));assert profile['network_sha256']==sha(source) and profile['seed']==29
        network=runs/'source'/f'release2670_s53_{arm}.inpx';network.write_bytes(revised)
        profile.update(network_sha256=sha(network),seed=53)
        path=runs/(arm+'.json');save(path,profile);profiles[arm]=profile
        prepared=runs/('prepared_'+arm)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(OLD))
        command=[sys.executable,'-B',str(OLD/'diagnostics/fast_fixed_profile.py'),
            '--network',str(network),'--profile',str(path),'--output',str(prepared)]
        result=subprocess.run(command,cwd=OLD,env=env,text=True,encoding='utf-8',capture_output=True)
        (out/(arm+'_prepare.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        assert result.returncode==0, result.stderr[-2000:]
        metadata=load(prepared/'prepared.json');metadata['concurrent_identity_network_stem']=network.stem
        save(prepared/'prepared.json',metadata)
        pins.update(metadata['snapshot_sha256']);pins[str(prepared/'prepared.json')]=sha(prepared/'prepared.json')
        plans.append(dict(arm=arm,prepared=str(prepared),output=str(runs/arm/'run')))
    prefix=lambda p:{k:[r for r in p[k] if r['time_s']<2700] for k in ('meter_commands','vsl_commands')}
    assert all(prefix(p)==prefix(profiles['hold']) for p in profiles.values())
    for name in ('fast_nc_run.ps1','fast_nc_runner.vbs','fast_fixed_profile_verify.py','validate_native_signal_record.py'):
        original=OLD/'diagnostics'/name;dest=runs/'runtime'/name;shutil.copy2(original,dest)
        assert sha(dest)==sha(original);pins[str(dest)]=sha(dest)
    sources=[HERE/'selected/plant_n31_v2.json',HERE/'decision_regret_check/selection.json',Path(__file__)]
    sources.extend(ROOT/p for p in context['component'].provenance['model_files'])
    sources.extend(ROOT/v['path'] for v in baseline['sources'].values())
    sources.extend([out/'candidate_config.json',out/'candidate_manifest.json'])
    model_pins={str(p):sha(p) for p in sources}
    save(out/'protocol.json',dict(seed=53,cutoff_sec=2670.1,horizon_sec=450,intervention_sec=2700,terminal_sec=3300,
        arms=arms,plans=plans,results_root=str(runs),source_network_sha256=sha(source),seed53_network_sha256=hashlib.sha256(revised).hexdigest(),
        candidate=dict(delta_merge=4.,carlson_E=2.,cells=cells,production_adopted=False),
        model_pins=model_pins,execution_pins=pins,parameters_frozen_before_new_traffic=True,
        controls='Replay the previously verified seed29 ALINEA command history on fresh seed53 traffic; same history through2550. Then hold or legal+2s/150s east-meter release, with/without90kph atDSD63..66. Not liveALINEA or unconditionalNC.',
        unchanged='All demand/routes/geometry/urban signals/entryDSD110, SimRes10,FZP5s,RED/GREEN meter timing; only traffic seed changes.',
        evaluation='Compare frozen baseline and delta4/E2 on identical fresh-state inputs. Predict before reading future targets. Costs: east31+8connector and separately wholeOmega/outside/native latent costs. No coefficient refit using this seed.',
        finite_run_count=4,max_concurrent=4,automatic_retries=0,native_started=False))
    save(runs/'preflight.json',dict(passed=True,plans=plans,pins=pins,seed=53,terminal_sec=3300,
        common_command_prefix_exact=True,model_protocol=str(out/'protocol.json'),model_protocol_sha256=sha(out/'protocol.json')))
    print(json.dumps(dict(prepared=str(out),runs=str(runs),native_started=False,profiles=4)),flush=True)


def recovery_flow_audit():
    """Observe four unchanged rollouts: state product versus realized discharge."""
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    parent=HERE/'closedloop9000_d4e2_analysis'
    out=parent/'recovery_flow_audit';out.mkdir(exist_ok=False)
    manifest=parent/'local_merge_cell23/candidate_manifest.json'
    context=lpr.load_sources(manifest);model=context['component']
    from evaluation.controllers import area_freeway_accounting as accounting
    records=load(DECISIONS/'capture.json')['records']
    records += [dict(r,case='s53_late',cutoff=2670.1,reference='hold',truth=str(HERE/'heldout53_response_v2/observations'/r['arm']))
                for r in load(HERE/'heldout53_response_v2/capture.json')['records']]
    records=[r for r in records if (r['case'],r['arm']) in (
        ('s47_late','hold'),('s47_late','release_10484'),('s53_late','hold'),('s53_late','release'))]
    cells=list(range(18,31));original=accounting._freeway_substep_events
    save(out/'protocol.json',dict(max_rollouts=4,calibration=False,production_changed=False,new_native=0,
        cells=cells,model='Frozen cell23-only candidate; recovery candidate remains rejected',
        hypothesis='Determine whether release-minus-hold discharge errors arise before or after sending/receiving allocation.',
        measured_Nv='30s snapshot trapezoids are approximate spatial-mean flow, not an exact downstream crossing count or calibration target.',
        invariants='Every replay cells/flows/ports/ramps must exactly match its completed saved prediction.',
        pins={str(p):sha(p) for p in (manifest,Path(__file__),Path(accounting.__file__))}))
    traces={};results=[];pins={};started=time.perf_counter()
    for r in records:
        trace=[];tick=0;args,kwargs=read_primitive_capture(r['input'],r['sha256'])
        assert args[2]==context['parameters']
        def observe(state,control,demand,cfg,**options):
            nonlocal tick
            net=cfg.network;road='FW_E';dt=cfg.simulation.T_f_h
            assert abs(dt*3600-1)<1e-9
            assert net.capacity_drop_discharge_phi==1 and not getattr(net,'freeway_hadiuzzaman',None)
            assert not accounting._routing.inventory_enabled(cfg) and not getattr(net,'freeway_buffer_segments',0)
            lanes,_=accounting._mn.effective_lane_profile(state,cfg,demand)
            stocks=accounting.continuity_vehicle_counts(state,cfg)[road]
            lengths=accounting.cell_lengths_km(cfg,road,len(stocks));speeds=state.freeway_speed[road]
            q=[n/L*v for n,L,v in zip(stocks,lengths,speeds)]
            merges=[0.]*31
            for ramp in net.ramps:merges[net.ramp_merge_segment_index[ramp]]+=options['ramp_release_veh_h'][ramp]
            for c in cells:
                branches=[o for o in net.off_ramps if net.off_ramp_segment_index[o]==c]
                split=min(1.,max(0.,sum(net.off_ramp_split_ratio[o] for o in branches)))
                sending=q[c]*(1-split);off_request=off_actual=0.
                caps=options.get('offramp_capacity_veh_h')
                for o in branches:
                    request=q[c]*net.off_ramp_split_ratio[o]
                    cap=None if caps is None else caps.get(o,caps.get(road))
                    off_request+=request;off_actual+=request if cap is None else min(request,max(0.,cap))
                if c<30:
                    receiving=max(0.,net.rho_max*lanes[road][c+1]*lengths[c+1]-stocks[c+1])/dt
                    limit=max(0.,receiving-merges[c+1])
                else:
                    cap=(getattr(net,'freeway_terminal_capacity_veh_h',{}) or {}).get(road,
                        net.freeway_capacity_veh_h*lanes[road][c]/net.freeway_lanes)
                    limit=sending if cap is None or getattr(net,'terminal_zero_gradient',False) else cap
                accepted=min(sending,limit)
                trace.append(dict(case=r['case'],arm=r['arm'],time_s=r['cutoff']+tick,cell=c,
                    n_veh=stocks[c],v_kmh=speeds[c],length_km=lengths[c],
                    potential_veh=q[c]*dt,through_veh=accepted*dt,off_entry_veh=off_actual*dt,
                    receiving_loss_veh=(sending-accepted)*dt,off_cap_loss_veh=(off_request-off_actual)*dt,
                    merge_veh=merges[c]*dt,split=split,
                    junction_mix_active=options.get('junction_ramp_speeds') is not None))
            tick+=1
            return original(state,control,demand,cfg,**options)
        accounting._freeway_substep_events=observe
        try:pred=model.rollout(*args,**kwargs)
        finally:accounting._freeway_substep_events=original
        oldpath=parent/'local_merge_cell23/nu0.25_delta2'/(r['case']+'_'+r['arm']+'.json.gz')
        pins[str(oldpath)]=sha(oldpath)
        with gzip.open(oldpath,'rt',encoding='utf-8') as f:old=json.load(f)
        assert all(json.loads(json.dumps(pred[k]))==old[k] for k in ('cells','flows','ports','ramps'))
        assert tick==450
        truth=ObservationData(r['truth']);times=[round(r['cutoff']+30*j,6) for j in range(16)]
        native={(t,int(z['cell'])):z for t in times for z in truth.cells[t] if z['road']=='FW_E'}
        for c in cells:
            t=[z for z in trace if z['cell']==c]
            through=sum(z['through_veh'] for z in t);off=sum(z['off_entry_veh'] for z in t)
            exact=sum(z['terminal_exits' if c==30 else 'downstream_crossings'] for z in pred['flows'] if z['cell']==c)
            assert abs(through-exact)<1e-7,(r['case'],r['arm'],c,through,exact)
            assert abs(off-sum(z['off_departures'] for z in pred['flows'] if z['cell']==c))<1e-7
            L=t[0]['length_km'];nv=[float(native[tm,c]['n_veh'])*float(native[tm,c]['v_kmh'])/L for tm in times]
            trapezoid=sum((a+b)*30/7200 for a,b in zip(nv,nv[1:]))
            actual_through=sum(float(truth.flows[tm,'FW_E',c]['terminal_exits_inferred' if c==30 else 'downstream_crossings']) for tm in times[1:])
            actual_off=sum(float(truth.flows[tm,'FW_E',c]['off_departures']) for tm in times[1:])
            results.append(dict(case=r['case'],arm=r['arm'],cell=c,length_km=L,
                model_potential_veh=sum(z['potential_veh'] for z in t),model_through_veh=through,model_off_entry_veh=off,
                model_receiving_loss_veh=sum(z['receiving_loss_veh'] for z in t),
                model_off_cap_loss_veh=sum(z['off_cap_loss_veh'] for z in t),
                measured_Nv_trapezoid_veh=trapezoid,measured_Nv_left_veh=sum(nv[:-1])*30/3600,
                measured_Nv_right_veh=sum(nv[1:])*30/3600,
                actual_through_veh=actual_through,actual_off_entry_veh=actual_off))
        traces[r['case'],r['arm']]=trace
        print(json.dumps(dict(case=r['case'],arm=r['arm'],arrays_exact=True,steps=tick)),flush=True)
    contrasts=[]
    for case,release in [('s47_late','release_10484'),('s53_late','release')]:
        for c in cells:
            held=[z for z in traces[case,'hold'] if z['cell']==c]
            changed=[z for z in traces[case,release] if z['cell']==c]
            density_term=sum((a['v_kmh']+b['v_kmh'])/2*(b['n_veh']-a['n_veh'])/a['length_km']/3600 for a,b in zip(held,changed))
            speed_term=sum((a['n_veh']+b['n_veh'])/2*(b['v_kmh']-a['v_kmh'])/a['length_km']/3600 for a,b in zip(held,changed))
            h=next(z for z in results if z['case']==case and z['arm']=='hold' and z['cell']==c)
            m=next(z for z in results if z['case']==case and z['arm']==release and z['cell']==c)
            delta={k:m[k]-h[k] for k in h if k not in ('case','arm','cell','length_km')}
            assert abs(density_term+speed_term-delta['model_potential_veh'])<1e-7
            contrasts.append(dict(case=case,cell=c,delta=delta,model_stock_product_term=density_term,
                model_speed_product_term=speed_term,
                scope='Exact symmetric algebra of paired autonomous model Nv; not independent causal effects.'))
    with (out/'model_steps.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(next(iter(traces.values()))[0]));writer.writeheader()
        for trace in traces.values():writer.writerows(trace)
    save(out/'summary.json',dict(rows=results,contrasts=contrasts,new_rollouts=4,arrays_exact=True,
        flow_reconstruction_exact=True,model_product_decomposition_exact=True,new_native=0,
        coefficient_changes=0,junction_mix_active=any(z['junction_mix_active'] for t in traces.values() for z in t),
        wall_sec=time.perf_counter()-started,pins=pins))
    print(json.dumps(dict(completed=str(out),new_rollouts=4,wall_sec=time.perf_counter()-started)),flush=True)


def conditional_ramp_arrival_audit():
    """Four diagnostic-only runs using FUTURE observed10484 arrivals, no fitting."""
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    parent=HERE/'closedloop9000_d4e2_analysis';out=parent/'recovery_flow_audit/conditional_arrivals'
    out.mkdir(exist_ok=False)
    model=lpr.load_sources(parent/'local_merge_cell23/candidate_manifest.json')['component']
    records=load(DECISIONS/'capture.json')['records']
    records += [dict(r,case='s53_late',cutoff=2670.1,reference='hold',truth=str(HERE/'heldout53_response_v2/observations'/r['arm']))
                for r in load(HERE/'heldout53_response_v2/capture.json')['records']]
    records=[r for r in records if (r['case'],r['arm']) in (
        ('s47_late','hold'),('s47_late','release_10484'),('s53_late','hold'),('s53_late','release'))]
    save(out/'protocol.json',dict(max_rollouts=4,future_observations=True,autonomous_validation=False,
        intervention='Only10484 ramp_arrival_vph replaced by realized30s bin counts /30s. Initial states, controls and all other forecast inputs remain exact.',
        purpose='Separate forecast-arrival contribution from accepted-merge/recovery response; NOT an operational forecast or gain qualification.',
        coefficient_changes=0,new_native=0,source_sha256=sha(Path(__file__))))
    baseline=load(parent/'local_merge_cell23/summary.json');results=[]
    for r in records:
        a,k=read_primitive_capture(r['input'],r['sha256']);before=copy.deepcopy(a[1]);t0=r['cutoff']
        path=Path(r['truth'])/'ports_30s.csv'
        with path.open(encoding='utf-8-sig',newline='') as f:
            native=[z for z in csv.DictReader(f) if z['connector']=='10484' and t0<float(z['window_end_s'])<=t0+450+1e-6]
        assert len(native)==15
        native_total=sum(float(z['arrivals_veh']) for z in native)
        for boundary,old in zip(a[1],before):
            index=int(math.floor((boundary['window_start_s']-t0)/30+1e-7));assert 0<=index<15
            boundary['ramp_arrival_vph']['RM_C10484']=float(native[index]['arrivals_veh'])*120
            stripped=copy.deepcopy(boundary);stripped['ramp_arrival_vph']['RM_C10484']=old['ramp_arrival_vph']['RM_C10484']
            assert stripped==old
        begin=time.perf_counter();pred=model.rollout(*a,**k);elapsed=time.perf_counter()-begin
        p=out/(r['case']+'_'+r['arm']+'.json.gz')
        with gzip.open(p,'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
        ramp=[z for z in pred['ramps'] if z['ramp']=='RM_C10484']
        requested=sum(z['requested_arrivals_veh'] for z in ramp)
        admitted=sum(z['admitted_arrivals_veh'] for z in ramp)
        assert abs(requested-native_total)<1e-7
        assert max(abs(z['conservation_residual_veh']) for z in pred['ramps']+pred['ports'])<1e-7
        truth=ObservationData(r['truth']);times=[round(t0+30*j,6) for j in range(16)]
        ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|{str(o) for o,v in model.offramps.items() if v['road']=='FW_E'}
        main={t:sum(z['n_veh'] for z in pred['cells'] if abs(z['time_s']-t)<1e-6) for t in times}
        ports={t:sum(z['n_veh'] for z in pred['ports'] if abs(z['time_s']-t)<1e-6)+sum(z['end']['connector_veh'] for z in pred['ramps'] if abs(z['end_sec']-t)<1e-6) for t in times}
        main[t0]=sum(z['n_veh'] for z in a[0] if z['road']=='FW_E')
        ports[t0]=sum(float(truth.ports[t0,no]['end_n_veh']) for no in ids)
        integral=lambda x:sum((x[a]+x[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
        costs=dict(main=integral(main),ports=integral(ports));costs['total']=sum(costs.values())
        old=next(z for z in baseline['rows'] if z['variant']=='nu0.25_delta2' and z['case']==r['case'] and z['arm']==r['arm'])
        results.append(dict(case=r['case'],arm=r['arm'],wall_sec=elapsed,costs=costs,autonomous_costs=old['costs']['predicted'],actual_costs=old['costs']['actual'],
            ramp10484=dict(native_arrivals=native_total,requested=requested,admitted=admitted,
                predicted_merge=sum(z['accepted_merge_veh'] for z in ramp),actual_merge=sum(float(z['departures_veh']) for z in native),
                predicted_end=ramp[-1]['end']['connector_veh'],actual_end=float(native[-1]['end_n_veh'])),
            terminal_exits=sum(z['terminal_exits'] for z in pred['flows']),
            inputs_sha256=r['sha256'],observed_future_arrivals_sha256=sha(path),prediction_sha256=sha(p)))
        print(json.dumps(dict(case=r['case'],arm=r['arm'],merge=results[-1]['ramp10484'],costs=costs)),flush=True)
    for r in results:
        base=next(z for z in results if z['case']==r['case'] and z['arm']=='hold')
        r['deltas']={name:{key:r[name][key]-base[name][key] for key in ('main','ports','total')}
            for name in ('costs','autonomous_costs','actual_costs')}
    save(out/'summary.json',dict(rows=results,new_rollouts=4,new_native=0,coefficient_changes=0,
        future_observations=True,autonomous_validation=False,gain_qualified=False,adopted=False))


def cached_posthead_receiving_audit():
    """No rollouts/fitting: compare existing budgets with observed posthead stocks.

    Native snapshot q=rho*v is only a conditional input to the existing formula,
    not a measured lane boundary flow or an identified receiving capacity.
    """
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph
    parent=HERE/'closedloop9000_d4e2_analysis'
    flow=parent/'recovery_flow_audit';out=flow/'receiving_closure';out.mkdir(exist_ok=False)
    manifest=parent/'local_merge_cell23/candidate_manifest.json'
    context=lpr.load_sources(manifest);model=context['component']
    cfg=model._config('FW_E',context['parameters']['by_direction']['FW_E']);net=cfg.network
    assert not getattr(net,'vsl_fd_two_branch',False) and not getattr(net,'freeway_hadiuzzaman',None)
    assert not context['document']['lane_groups']
    ramp='RM_C10484';spec=model.ramp_receiving_nodes[ramp]
    head=377.1107628548054  # Geometry already verified in the pinned head-balance audit.
    cap=net.ramp_capacity_veh_h[ramp];tc=spec['critical_gap_sec'];tf=spec['followup_sec']
    records=load(DECISIONS/'capture.json')['records']
    records += [dict(r,case='s53_late',truth=str(HERE/'heldout53_response_v2/observations'/r['arm']))
                for r in load(HERE/'heldout53_response_v2/capture.json')['records']]
    previous=load(flow/'ramp10484_head_balance.json')['rows'];rows=[];summaries=[]
    pins={str(p):sha(p) for p in (manifest,Path(__file__),flow/'ramp10484_head_balance.json')}
    save(out/'protocol.json',dict(new_rollouts=0,optimizer_iterations=0,new_native=0,fzp_rescans=0,
        purpose='Separate receiving closure and demand/eligibility limits using completed receipts only.',
        future_observed_states='Conditional formula evaluations only; never autonomous predictions.',
        interpretation='Snapshot mean q, unknown target-lane gaps and within-bin head timing prevent identification of a unique receiving law.',
        adopting_coefficients=False,ramp=ramp,upstream_cell=22,merge_cell=23,
        cells_zero_based=True,rho_max=net.rho_max,rho_crit=net.rho_crit,
        mainline_capacity=net.freeway_capacity_veh_h,ramp_capacity=cap,critical_gap_sec=tc,followup_sec=tf))
    for old in previous:
        case,arm=old['case'],old['arm'];assert old['head_position_m']==head
        rec=next(r for r in records if r['case']==case and r['arm']==arm)
        truth=Path(rec['truth']);cohort_path=truth/'port_cohorts_30s.json';cell_path=truth/'cells_30s.csv'
        pins[str(cohort_path)]=sha(cohort_path);pins[str(cell_path)]=sha(cell_path)
        cohorts=load(cohort_path)
        with cell_path.open(encoding='utf-8-sig',newline='') as f:
            cells={(round(float(z['time_s']),6),int(z['cell'])):z for z in csv.DictReader(f) if z['road']=='FW_E'}
        actual=old['series'];mode_rows={}
        for mode,folder in [('autonomous',parent/'local_merge_cell23/nu0.25_delta2'),
                            ('conditional_arrivals',flow/'conditional_arrivals')]:
            path=folder/(case+'_'+arm+'.json.gz');pins[str(path)]=sha(path)
            with gzip.open(path,'rt',encoding='utf-8') as f:pred=json.load(f)
            ramp_rows=[z for z in pred['ramps'] if z['ramp']==ramp];assert len(ramp_rows)==450
            mode_rows[mode]=ramp_rows
            for a in actual:
                end=a['end_sec'];start=end-30
                interval=[z for z in ramp_rows if start+1e-6<z['end_sec']<=end+1e-6];assert len(interval)==30
                c22=cells[round(end,6),22];c23=cells[round(end,6),23]
                rho22=float(c22['rho_veh_per_km_lane']);v22=float(c22['v_kmh'])
                rho23=float(c23['rho_veh_per_km_lane']);v23=float(c23['v_kmh'])
                q=rho22*v22
                native_gap=gap_acceptance_supply_vph(q,tc,tf)
                native_canonical=min(cap,net.freeway_capacity_veh_h*min(1.,max(0.,
                    (net.rho_max-rho23)/(net.rho_max-net.rho_crit))))
                post=[z for z in cohorts[str(end)]['10484'] if float(z[0])>head]
                assert len(post)==a['native_posthead']
                post_speed=sum(float(z[1]) for z in post)/len(post) if post else None
                first,last=interval[0]['start'],interval[-1]['end']
                post_n=lambda z:z['downstream_travelling_veh']+z['merge_ready_veh']
                merges=sum(z['accepted_merge_veh'] for z in interval)
                served=sum(z['head_service_veh'] for z in interval)
                assert abs(post_n(last)-post_n(first)-served+merges)<1e-7
                assert all(abs(z['accepted_merge_veh']-min(z['eligible_merge_veh'],z['receiving_budget_veh']))<1e-7 for z in interval)
                row=dict(case=case,arm=arm,mode=mode,start_sec=start,end_sec=end,
                    actual_merge=a['native_merges'],actual_head=a['inferred_net_head_passages'],
                    actual_posthead_n=len(post),actual_posthead_below15=sum(float(z[1])<15 for z in post),
                    actual_posthead_mean_speed=post_speed,
                    actual_rho22=rho22,actual_v22=v22,actual_rho23=rho23,actual_v23=v23,
                    native_snapshot_q22_vphpl=q,native_snapshot_gap_vph=native_gap,
                    native_snapshot_density_supply_vph=native_canonical,
                    native_snapshot_combined_supply_vph=min(native_gap,native_canonical),
                    model_merge=merges,model_head=served,model_posthead_n=post_n(last),
                    model_merge_ready_n=last['merge_ready_veh'],
                    model_receiving_budget=sum(z['receiving_budget_veh'] for z in interval),
                    model_receiving_limited_seconds=sum(z['eligible_merge_veh']>z['receiving_budget_veh']+1e-8 for z in interval),
                    model_eligibility_limited_seconds=sum(z['eligible_merge_veh']<z['receiving_budget_veh']-1e-8 for z in interval),
                    model_density_supply_min_vph=min(z['receiving_node']['unlimited_node_canonical_budget_vph'] for z in interval),
                    model_receiving_min_vph=min(z['canonical_receiving_budget_vph'] for z in interval),
                    model_receiving_max_vph=max(z['canonical_receiving_budget_vph'] for z in interval))
                rows.append(row)
            rr=[z for z in rows if z['case']==case and z['arm']==arm and z['mode']==mode]
            # Slow vehicles present at both endpoints: retrospective localization,
            # not proof of a continuously saturated merge queue throughout a bin.
            slow=[]
            for z in rr:
                prev=cohorts[str(round(z['start_sec'],6))]['10484']
                if z['actual_posthead_below15']>=3 and sum(float(x[0])>head and float(x[1])<15 for x in prev)>=3:slow.append(z)
            summaries.append(dict(case=case,arm=arm,mode=mode,
                actual_merge=sum(z['actual_merge'] for z in rr),model_merge=sum(z['model_merge'] for z in rr),
                actual_posthead_final=rr[-1]['actual_posthead_n'],model_posthead_final=rr[-1]['model_posthead_n'],
                minimum_density_supply_vph=min(z['model_density_supply_min_vph'] for z in rr),
                receiving_limited_seconds=sum(z['model_receiving_limited_seconds'] for z in rr),
                eligibility_limited_seconds=sum(z['model_eligibility_limited_seconds'] for z in rr),
                slow_endpoint_bins=len(slow),slow_endpoint_actual_merges=sum(z['actual_merge'] for z in slow),
                slow_endpoint_model_merges=sum(z['model_merge'] for z in slow),
                slow_endpoint_model_budget=sum(z['model_receiving_budget'] for z in slow),
                slow_endpoint_native_formula_budget=sum(z['native_snapshot_combined_supply_vph']/120 for z in slow)))
    with (out/'intervals.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # Show an equation-level ambiguity, not a new or calibrated traffic case.
    same_q=[]
    for rho,v in ((15.,100.),(75.,20.)):
        q=rho*v;canonical=min(cap,net.freeway_capacity_veh_h*min(1.,(net.rho_max-rho)/(net.rho_max-net.rho_crit)))
        same_q.append(dict(rho=rho,v=v,q=q,supply=min(canonical,gap_acceptance_supply_vph(q,tc,tf))))
    assert same_q[0]['supply']==same_q[1]['supply']
    save(out/'summary.json',dict(rows=summaries,interval_rows=len(rows),new_rollouts=0,
        coefficient_changes=0,new_native=0,adopted=False,gain_qualified=False,
        cached_merge_identity_passed=True,posthead_balance_passed=True,
        synthetic_equal_flow_counterexample=same_q,pins=pins,
        conclusion='Existing scalar gap/density budget does not distinguish some free and congested states. Current evidence does not identify a replacement target-lane receiving law. No new coefficient grid.'))
    print(json.dumps(dict(completed=str(out),new_rollouts=0,rows=summaries)),flush=True)


def recovery_response(*, local_merge=False, recovery_pair=False):
    """Bounded one-parameter recovery test, selected on seed29 reference flows.

    Existing causal recovery relaxation only; no new model equation. Independent
    seed/control responses are evaluated AFTER freezing the selection.
    """
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import configure_state_response
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    out=HERE/'closedloop9000_d4e2_analysis'/('recovery_cells24_25' if recovery_pair else 'local_merge_cell23' if local_merge else 'recovery_response')
    out.mkdir(exist_ok=recovery_pair)
    assert not (out/'protocol.json').exists(), 'Preserve completed calibration'
    source=HERE/'heldout53_response_v2/candidate_manifest.json'
    ctx=lpr.load_sources(source);model=ctx['component']
    response=copy.deepcopy(model.base.network.freeway_state_response)
    records=load(DECISIONS/'capture.json')['records']
    for r in load(HERE/'heldout53_response_v2/capture.json')['records']:
        records.append(dict(r,case='s53_late',cutoff=2670.1,reference='hold',
            truth=str(HERE/'heldout53_response_v2/observations'/r['arm'])))
    # Contiguous two ramp-group influence interval, same coefficient in all
    # cells. Existing rho-gradient and desired>current predicates stay intact.
    affected=list(range(21,26)) if local_merge else list(range(9,26))
    variants={'baseline':None,'tau8':8.,'tau6':6.,'tau4':4.}
    if local_merge:
        variants={'baseline':None}
        nominal=response['FW_E']['cell_overrides']['23']['anticipation']['downstream_lt_local']
        for fraction in (0.,0.25,0.5,1.):
            for delta in (1.,2.,4.):
                if fraction==1. and delta==4.:continue
                variants[f'nu{fraction:g}_delta{delta:g}']=dict(nu_lower_downstream=nominal*fraction,delta_merge=delta)
    reused={}; new_count=0
    if recovery_pair:
        affected=[24,25]
        prior=out.parent/'local_merge_cell23'
        variants={'baseline':None,'cell23':None}
        candidates={
            'acc6':{'recovery_relaxation':{'acceleration_sec':6.}},
            'dec24':{'relaxation':{'acceleration_sec':12.,'deceleration_sec':24.}},
            'acc6_dec24':{'relaxation':{'acceleration_sec':12.,'deceleration_sec':24.},
                          'recovery_relaxation':{'acceleration_sec':6.}},
        }
        for name,setting in candidates.items():
            variants['recovery_'+name]=setting
            variants['combined_'+name]=setting
    protocol=dict(variants=variants,affected_cells=affected,model_reference=str(source),
        train='Only seed29 early/late reference commands; no DeltaTTT fitting',
        selection='Mean normalized stock RMSE plus downstream-count RMSE; each training metric must not worsen >5% versus baseline.',
        check='Frozen selection on all saved commands, seed43/47/53; these seeds were inspected earlier, not pristine blind holdouts.',
        unchanged='FD, critical densities, sending/receiving, merge, lane loss, VSL response, route fractions, objective and horizon.',
        coefficient='Existing recovery_relaxation acceleration_sec; nu/tau pressure ratio preserved.',
        max_rollouts=44,new_native=0,optimizer_iterations=0,production_adopted=False,
        pins={str(p):sha(p) for p in (source,HERE/'decision_response/capture.json',HERE/'heldout53_response_v2/capture.json',Path(__file__))})
    if local_merge:
        protocol.update(train='Seed29 late2670.1 hold and gradual release; physical state/flow errors, no cost/rank fitting',
            affected_cells=[23],score_cells=affected,variants=variants,max_rollouts=62,
            coefficient='Existing cell23 downstream-lower-density anticipation and delta_merge only. No new equations.',
            unchanged='All other cells, formation anticipation, FD, recovery time, conservation, demand, command, objective and horizon.',
            selection='Minimize local normalized stock+flow+speed RMSE; whole east31 stock and flow RMSE in each training arm must stay within5% of baseline.')
    if recovery_pair:
        protocol.update(train='Seed29 late2670.1 hold/release only; coefficients frozen before scoring other cases',
            variants=variants,affected_cells=[24,25],diagnostic_cells=[21,22,23,24,25],
            selection='One shared24/25 parameter set: mean normalized N/v/q+terminal RMSE across both cell23 contexts. Each whole31 N/q training RMSE <=1.05 its matching context. No DeltaTTT fitting.',
            max_rollouts=48,max_coefficient_candidates=3,max_wall_sec=1800,
            coefficient='Existing recovery acceleration6s; asymmetric deceleration24s; their combination.24/25 always share coefficients. Deceleration tau also reduces nu/tau; recovery override preserves pressure ratio.',
            unchanged='Cell21/22 and all other cells except existing cell23 variant; FD, critical density, convection coefficient, conservation, actual merges, dynamic off storage/drain/spillback, demand, objective, control and forecast horizon.',
            comparison='baseline/cell23/recovery-only/combined;40 completed baseline/cell23 predictions reused with hashes',
            state_condition='Canonical current predicted desired>speed/downstream<=rho/downstream<critical for recovery; desired>=speed for general relaxation. No seed/time/control bonus.',
            event_definition='30s snapshots. Congestion<60kmh, recovery>=80kmh for3 consecutive snapshots after congestion; censored within450s. Diagnostic thresholds, not coefficient selection targets.',
            stop_rule='Single grid only. If no admitted improvement, preserve least-error candidate as rejected diagnostic; no repeated parameter search. Reject premature clearing of sustained release congestion.',
            known_data_limit='seed47 VSL90 has4 unexplained losses and is excluded from clean ranking. Other seeds were historically inspected, not pristine blind holdouts.')
    save(out/'protocol.json',protocol)
    overall_begin=time.perf_counter()
    inputs={};results={};truth_cache={}
    for r in records:
        inputs[r['case'],r['arm']]=read_primitive_capture(r['input'],r['sha256'])
    def run(name,r):
        nonlocal new_count
        key=(name,r['case'],r['arm'])
        if key in results:return results[key]
        spec=copy.deepcopy(response)
        if recovery_pair and (name=='cell23' or name.startswith('combined_')):
            spec['FW_E']['cell_overrides']['23']['anticipation']['downstream_lt_local']=4.59375
            spec['FW_E']['cell_overrides']['23']['delta_merge']=2.
        if variants[name] is not None:
            if recovery_pair:
                for cell in affected:
                    spec['FW_E']['cell_overrides'][str(cell)].update(copy.deepcopy(variants[name]))
            elif local_merge:
                local=spec['FW_E']['cell_overrides']['23']
                local['anticipation']['downstream_lt_local']=variants[name]['nu_lower_downstream']
                local['delta_merge']=variants[name]['delta_merge']
            else:
                for cell in affected:
                    spec['FW_E']['cell_overrides'].setdefault(str(cell),{})['recovery_relaxation']={'acceleration_sec':variants[name]}
        configure_state_response(model.base,{'freeway':{'state_response':spec}})
        a,k=copy.deepcopy(inputs[r['case'],r['arm']]);assert a[2]==ctx['parameters']
        folder=out/name;folder.mkdir(exist_ok=True)
        pred_path=folder/(r['case']+'_'+r['arm']+'.json.gz')
        if recovery_pair and name in ('baseline','cell23'):
            pred_path=prior/('baseline' if name=='baseline' else 'nu0.25_delta2')/pred_path.name
            reused[str(pred_path)]=sha(pred_path)
            with gzip.open(pred_path,'rt',encoding='utf-8') as f:pred=json.load(f)
            wall=0.
        else:
            if recovery_pair:
                assert new_count<48 and time.perf_counter()-overall_begin<1800, 'Predeclared budget exhausted'
            begin=time.perf_counter();pred=model.rollout(*a,**k);wall=time.perf_counter()-begin
            new_count+=1
            with gzip.open(pred_path,'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
        if recovery_pair:save(folder/'state_response.json',spec)
        # Targets enter only scoring, after autonomous prediction has finished.
        if r['truth'] not in truth_cache:truth_cache[r['truth']]=ObservationData(r['truth'])
        truth=truth_cache[r['truth']];t0=r['cutoff'];times=[round(t0+d,6) for d in range(0,451,30)]
        observed={(t,int(z['cell'])):z for t in times for z in truth.cells[t] if z['road']=='FW_E'}
        predicted={(round(z['time_s'],6),z['cell']):z for z in pred['cells']}
        n_pairs=[(predicted[t,c]['n_veh'],float(observed[t,c]['n_veh'])) for t in times[1:] for c in affected]
        # Includes terminal because its timing changes the residence objective.
        selected_cells=affected+[30]
        pflows={(round(z['window_end_s'],6),z['cell']):z for z in pred['flows']}
        q_pairs=[]
        for t in times[1:]:
            for c in selected_cells:
                pn='terminal_exits' if c==30 else 'downstream_crossings'
                an='terminal_exits_inferred' if c==30 else 'downstream_crossings'
                q_pairs.append((pflows[t,c][pn],float(truth.flows[t,'FW_E',c][an])))
        def error(pairs):
            rmse=math.sqrt(sum((a-b)**2 for a,b in pairs)/len(pairs))
            return dict(rmse=rmse,normalized=rmse/max(1.,sum(b for _,b in pairs)/len(pairs)))
        errors=dict(stock=error(n_pairs),flow=error(q_pairs))
        whole_errors=None
        if local_merge or recovery_pair:
            v_pairs=[(predicted[t,c]['v_kmh'],float(observed[t,c]['v_kmh'])) for t in times[1:] for c in affected if observed[t,c]['v_kmh'] not in ('',None)]
            errors['speed']=error(v_pairs)
            whole_errors=dict(stock=error([(predicted[t,c]['n_veh'],float(observed[t,c]['n_veh'])) for t in times[1:] for c in range(31)]),
                flow=error([(pflows[t,c]['terminal_exits' if c==30 else 'downstream_crossings'],
                    float(truth.flows[t,'FW_E',c]['terminal_exits_inferred' if c==30 else 'downstream_crossings'])) for t in times[1:] for c in range(31)]))
        ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|{str(o) for o,v in model.offramps.items() if v['road']=='FW_E'}
        costs={}
        for kind in ('predicted','actual'):
            main={t:sum(float(z['n_veh']) for (stamp,c),z in (predicted if kind=='predicted' else observed).items() if stamp==t) for t in times}
            ports={t:(sum(z['n_veh'] for z in pred['ports'] if abs(z['time_s']-t)<1e-6)+sum(z['end']['connector_veh'] for z in pred['ramps'] if abs(z['end_sec']-t)<1e-6)
                if kind=='predicted' else sum(float(truth.ports[t,no]['end_n_veh']) for no in ids)) for t in times}
            main[t0]=sum(float(z['n_veh']) for (stamp,c),z in observed.items() if stamp==t0)
            ports[t0]=sum(float(truth.ports[t0,no]['end_n_veh']) for no in ids)
            integ=lambda d:sum((d[a]+d[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            costs[kind]=dict(main=integ(main),ports=integ(ports),total=integ(main)+integ(ports))
        residual=max(abs(z['conservation_residual_veh']) for z in pred['ports']+pred['ramps']);assert residual<1e-7
        result=dict(variant=name,case=r['case'],arm=r['arm'],reference=r['reference'],wall_sec=wall,
            errors=errors,whole_errors=whole_errors,score=sum(v['normalized'] for v in errors.values()),costs=costs,conservation_max=residual,
            source_admissions=sum(z['source_admissions'] for z in pred['flows']),
            off_departures=sum(z['off_departures'] for z in pred['flows']),terminal_exits=sum(z['terminal_exits'] for z in pred['flows']),
            merge=sum(z['accepted_merge_veh'] for z in pred['ramps']))
        if recovery_pair:
            def events(series):
                low=[t for t,v in series if v<60.]
                onset=low[0] if low else None
                recovered=next((series[i][0] for i in range(len(series)-2)
                    if onset is not None and series[i][0]>onset and all(v>=80. for t,v in series[i:i+3])),None)
                return dict(onset_sec=onset,recovered_sec=recovered,low_speed_sample_sec=30*len(low),
                    recovery_censored=onset is not None and recovered is None)
            metrics=[]
            for c in range(21,26):
                z=dict(cell=c)
                for kind,table in [('predicted',predicted),('actual',observed)]:
                    cells=[table[t,c] for t in times[1:]]
                    velocities=[(t,float(table[t,c]['v_kmh'])) for t in times[1:] if table[t,c]['v_kmh'] not in ('',None)]
                    z[kind]=dict(mean_speed_kmh=sum(v for _,v in velocities)/len(velocities),
                        end_n_veh=float(cells[-1]['n_veh']),
                        downstream_veh=sum(float((pflows[t,c] if kind=='predicted' else truth.flows[t,'FW_E',c])['downstream_crossings']) for t in times[1:]),
                        events=events(velocities))
                metrics.append(z)
            result.update(prediction=str(pred_path),prediction_sha256=sha(pred_path),cell_metrics=metrics,
                end_stock=sum(float(predicted[times[-1],c]['n_veh']) for c in range(31)),
                scope='East31+8connector residence; urban waiting and full Omega require coupled check')
        save(folder/(r['case']+'_'+r['arm']+'_result.json'),result);results[key]=result
        print(json.dumps(dict(variant=name,case=r['case'],arm=r['arm'],score=result['score'],cost=costs['predicted']['total'])),flush=True)
        return result
    train=[r for r in records if r['case'].startswith('s29_') and r['arm']==r['reference']]
    if local_merge or recovery_pair:train=[r for r in records if r['case']=='s29_late' and r['arm'] in ('hold','release')]
    assert len(train)==2
    scores=[]
    for name in variants:
        rows=[run(name,r) for r in train]
        admitted=all(row['errors'][m]['rmse']<=1.05*results['baseline',row['case'],row['arm']]['errors'][m]['rmse'] for row in rows for m in ('stock','flow'))
        if local_merge or recovery_pair:
            context='cell23' if recovery_pair and name.startswith('combined_') else 'baseline'
            admitted=all(row['whole_errors'][m]['rmse']<=1.05*results[context,row['case'],row['arm']]['whole_errors'][m]['rmse'] for row in rows for m in ('stock','flow'))
        scores.append(dict(name=name,score=sum(z['score'] for z in rows)/len(rows),admitted=admitted))
    selected=min((s for s in scores if s['admitted']),key=lambda s:s['score'])['name']
    selection=dict(selected=selected,training_scores=scores,heldout_read_for_selection=False)
    comparison=list(dict.fromkeys(['baseline',selected]))
    if recovery_pair:
        score_map={s['name']:s for s in scores}
        paired=[dict(name=n,score=sum(score_map[p+n]['score'] for p in ('recovery_','combined_'))/2,
            admitted=all(score_map[p+n]['admitted'] for p in ('recovery_','combined_'))) for n in candidates]
        baseline_score=(score_map['baseline']['score']+score_map['cell23']['score'])/2
        feasible=[s for s in paired if s['admitted']]
        selected=min(feasible or paired,key=lambda s:s['score'])['name']
        improves=bool(feasible) and next(s['score'] for s in paired if s['name']==selected)<baseline_score
        selection.update(selected=selected,paired_scores=paired,baseline_score=baseline_score,training_improved=improves,
            adopted=False,status='frozen_for_validation' if improves else 'rejected_training_diagnostic_only')
        comparison=['baseline','cell23','recovery_'+selected,'combined_'+selected]
    save(out/'frozen_selection.json',selection)
    choices=[]
    for name in comparison:
        for r in records:run(name,r)
        for case in sorted({r['case'] for r in records}):
            rows=[z for (v,c,a),z in results.items() if v==name and c==case and not (recovery_pair and c=='s47_late' and a=='hold_vsl90')]
            held=next(z for z in rows if z['arm']==z['reference'])
            for z in rows:
                z['predicted_delta']=z['costs']['predicted']['total']-held['costs']['predicted']['total']
                z['actual_delta']=z['costs']['actual']['total']-held['costs']['actual']['total']
            best=min(rows,key=lambda z:z['costs']['predicted']['total']);actual=min(rows,key=lambda z:z['costs']['actual']['total'])
            choices.append(dict(variant=name,case=case,selected=best['arm'],actual_best=actual['arm'],
                regret=best['costs']['actual']['total']-actual['costs']['actual']['total']))
    save(out/'summary.json',dict(selected=selected,training_scores=scores,rows=list(results.values()),choices=choices,
        rollouts=len(results),new_native=0,production_adopted=False,gain_qualified=False,optimizer_iterations=0,
        new_rollouts=new_count,reused_predictions=reused,wall_sec=time.perf_counter()-overall_begin,
        comparison=comparison,selection=selection,
        scope='East31+8connector costs only; not full Omega or outside waiting.'))
    print(json.dumps(dict(selected=selected,choices=choices)),flush=True)


def local_speed_balance(*, recovery_pair=False):
    """Conditional speed-term audit, no fitting or autonomous rollout.

    Existing 30s snapshots and only the preceding30s merge count are supplied
    to the canonical1s speed update. The observed next30s trend is a descriptive
    comparator, NOT a same-vehicle acceleration measurement or forecast input.
    """
    sys.path.insert(0,str(ROOT/'vendor/NumSim-mine'))
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers.freeway_fd import cell_state_response, state_response_coefficients, literature_desired_speed
    from src.models.state import ControlAction
    out=HERE/'closedloop9000_d4e2_analysis'/('recovery_cells24_25/conditional_terms' if recovery_pair else 'recovery_response/seed47_audit/speed_balance')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.mkdir(exist_ok=True)
    assert not (out/'summary.json').exists(), 'Preserve the completed speed audit'
    records={r['arm']:r for r in load(DECISIONS/'capture.json')['records'] if r['case']=='s47_late'}
    pins={};native={};rows=[]
    for arm in ('hold','release_10484'):
        folder=Path(records[arm]['truth']);manifest=load(folder/'manifest.json')
        data={}
        for name,time_key in [('cells_30s.csv','time_s'),('flows_30s.csv','window_end_s')]:
            path=folder/name;assert sha(path)==manifest['files'][name];pins[str(path)]=sha(path)
            with path.open(encoding='utf-8-sig',newline='') as f:
                data[name]={(round(float(z[time_key]),6),int(z['cell'])):z for z in csv.DictReader(f) if z['road']=='FW_E'}
        native[arm]=data
    manifests={'baseline':HERE/'heldout53_response_v2/candidate_manifest.json',
               'tau4':out.parents[1]/'candidate_manifest.json'}
    if recovery_pair:
        manifests={'baseline':HERE/'heldout53_response_v2/candidate_manifest.json',
                   'cell23':HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json'}
    bases=('native','autonomous_prediction')
    if recovery_pair:
        bases=tuple(f'local{a}_up{b}_down{c}' for a in (0,1) for b in (0,1) for c in (0,1))
    for variant,manifest in manifests.items():
        pins[str(manifest)]=sha(manifest)
        ctx=lpr.load_sources(manifest);model=ctx['component']
        cfg=model._config('FW_E',ctx['parameters']['by_direction']['FW_E']);net=cfg.network
        maximum=max(cfg.freeway_follower.vsl_set);assert maximum==110
        control=ControlAction(vsl={'FW_E':maximum})
        for arm in native:
            path=(HERE/'closedloop9000_d4e2_analysis/local_merge_cell23'/('nu0.25_delta2' if variant=='cell23' else 'baseline')/f's47_late_{arm}.json.gz'
                  if recovery_pair else out.parents[1]/variant/f's47_late_{arm}.json.gz');pins[str(path)]=sha(path)
            with gzip.open(path,'rt',encoding='utf-8') as f:pred=json.load(f)
            pc={(round(z['time_s'],6),int(z['cell'])):z for z in pred['cells']}
            pf={(round(z['window_end_s'],6),int(z['cell'])):z for z in pred['flows']}
            for basis in bases:
                states=native[arm]['cells_30s.csv'] if basis=='native' else pc
                flows=native[arm]['flows_30s.csv'] if basis=='native' else pf
                if recovery_pair:
                    observed_local,observed_up,observed_down=(int(x[-1]) for x in basis.split('_'))
                    states=native[arm]['cells_30s.csv'] if observed_local else pc
                    flows=native[arm]['flows_30s.csv'] if observed_local else pf
                for j in range(1,15):
                    stamp=round(2670.1+30*j,6)
                    for cell in (21,22,23,24,25):
                        local=states[stamp,cell];up=states[stamp,cell-1];down=states[stamp,cell+1]
                        if recovery_pair:
                            up=(native[arm]['cells_30s.csv'] if observed_up else pc)[stamp,cell-1]
                            down=(native[arm]['cells_30s.csv'] if observed_down else pc)[stamp,cell+1]
                        v=float(local['v_kmh']);vu=float(up['v_kmh'])
                        rho=float(local['rho_veh_per_km_lane']);rd=float(down['rho_veh_per_km_lane'])
                        p=net.freeway_segment_params['FW_E'][cell]
                        length=p['segment_length_km'];lanes=net.freeway_segment_lanes['FW_E'][cell]
                        assert abs(lanes-3)<1e-10 and abs(net.freeway_segment_lanes['FW_E'][cell+1]-3)<1e-10
                        vsl=accounting._mn.segment_vsl(control,'FW_E',cell,cfg)
                        desired=accounting._mn.effective_desired_speed_kmh(rho,net.v_free,net.rho_crit,vsl,
                            net.alpha_vsl,False,net.metanet_a_m,False,net.rho_max,0.)
                        desired=literature_desired_speed((getattr(net,'freeway_vsl_fd_response',{}) or {}).get('FW_E'),
                            cfg,'FW_E',cell,rho,desired,vsl,False)
                        nu0=accounting._mn.select_anticipation_nu(rho,net,vsl)
                        spec=cell_state_response(net,'FW_E',cell)
                        tau,nu=state_response_coefficients(spec,v,desired,rho,rd,p['rho_crit'],p['metanet_tau_h'],nu0)
                        kappa=p['metanet_kappa_veh_km_lane'];dt=1/3600
                        relaxation=dt/tau*(desired-v)
                        convection=dt/length*v*(vu-v)
                        anticipation=-nu*dt/(tau*length)*(rd-rho)/(rho+kappa)
                        canonical=accounting._mn.metanet_speed_update_kmh(v,vu,rho,rd,desired,dt,length,
                            net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
                        reconstructed=max(net.v_min,v+relaxation+convection+anticipation)
                        assert abs(canonical-reconstructed)<1e-10,(variant,arm,basis,stamp,cell,canonical,reconstructed)
                        rate=float(flows[stamp,cell]['ramp_merges'])*120
                        delta=spec.get('delta_merge',net.metanet_delta_merge)
                        merge=delta*dt*rate*v/(length*lanes*(rho+kappa))
                        final=max(net.v_min,canonical-merge)
                        following=float(states[round(stamp+30,6),cell]['v_kmh'])
                        rows.append(dict(variant=variant,arm=arm,basis=basis,time_s=stamp,cell=cell,
                            speed_kmh=v,upstream_speed_kmh=vu,rho=rho,downstream_rho=rd,desired_speed_kmh=desired,
                            preceding30_merge_vph=rate,tau_sec=tau*3600,nu=nu,delta_merge=delta,
                            relaxation_kmh_per_s=relaxation,convection_kmh_per_s=convection,
                            anticipation_kmh_per_s=anticipation,merge_loss_kmh_per_s=merge,
                            total_kmh_per_s=final-v,next30_snapshot_trend_kmh_per_s=(following-v)/30,
                            canonical_reconstruction_error=abs(canonical-reconstructed)))
    groups=[]
    for variant in manifests:
        for arm in native:
            for basis in bases:
                for cell in (21,22,23,24,25):
                    selected=[r for r in rows if (r['variant'],r['arm'],r['basis'],r['cell'])==(variant,arm,basis,cell)]
                    metrics=('relaxation_kmh_per_s','convection_kmh_per_s','anticipation_kmh_per_s',
                        'merge_loss_kmh_per_s','total_kmh_per_s','next30_snapshot_trend_kmh_per_s')
                    groups.append(dict(variant=variant,arm=arm,basis=basis,cell=cell,samples=len(selected),
                        means={k:sum(r[k] for r in selected)/len(selected) for k in metrics},
                        positive_acceleration_samples=sum(r['total_kmh_per_s']>0 for r in selected),
                        recovery_active_samples=sum(r['tau_sec']<12 for r in selected)))
    save(out/'summary.json',dict(groups=groups,rows=rows,pins=pins,source_sha256=sha(Path(__file__)),
        new_rollouts=0,new_native=0,new_coefficients=0,canonical_evaluations=len(rows),
        exact_reconstruction=True,scope='Conditional local derivative audit. Next30 snapshot changes include vehicle mixing and sampling; not observed individual acceleration.'))
    with (out/'terms.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(dict(evaluations=len(rows),cell23=[g for g in groups if g['cell']==23])),flush=True)


def cached_wave_audit():
    """Locate discharge-response errors in existing 30s caches; no forecasting."""
    manifest=load(OUT/'capture.json'); t0=manifest['cutoff']; end=t0+manifest['horizon']
    assert manifest['horizon']==450
    target=OUT/'wave_response_20260928.json'
    if target.exists():raise ValueError('Preserve the previous cached wave audit')
    pins={str(OUT/'capture.json'):sha(OUT/'capture.json')}; data={}
    for arm in ('hold','release'):
        record=next(r for r in manifest['records'] if r['arm']==arm)
        truth=Path(record['truth']); native_manifest=load(truth/'manifest.json')
        cells={}; flows={}
        for name,dest,time_key in (('cells_30s.csv',cells,'time_s'),
                                    ('flows_30s.csv',flows,'window_end_s')):
            path=truth/name; digest=sha(path); assert digest==native_manifest['files'][name]
            pins[str(path)]=digest
            with path.open(encoding='utf-8-sig',newline='') as f:
                for row in csv.DictReader(f):
                    time=round(float(row[time_key]),6)
                    if row['road']=='FW_E' and t0<time<=end:
                        dest[time,int(row['cell'])]=row
        path=OUT/(arm+'_prediction.json.gz');pins[str(path)]=sha(path)
        with gzip.open(path,'rt',encoding='utf-8') as f:pred=json.load(f)
        data['actual',arm]=(cells,flows)
        data['predicted',arm]=({(round(r['time_s'],6),int(r['cell'])):r for r in pred['cells']},
            {(round(r['window_end_s'],6),int(r['cell'])):r for r in pred['flows']})
    rows=[]
    for cell in range(31):
        for block in range(3):
            a=t0+150*block;b=a+150;times=[round(a+30*j,6) for j in range(1,6)]
            row=dict(cell=cell,start_sec=a,end_sec=b)
            for kind in ('actual','predicted'):
                arms={}
                for arm in ('hold','release'):
                    cells,flows=data[kind,arm]; c=[cells[t,cell] for t in times]; f=[flows[t,cell] for t in times]
                    eligible=[r for r in c if r['v_kmh'] not in ('',None) and float(r['n_veh'])>0]
                    weight=sum(float(r['n_veh']) for r in eligible)
                    arms[arm]=dict(downstream_veh=sum(float(r['downstream_crossings']) for r in f),
                        merge_veh=sum(float(r['ramp_merges']) for r in f),
                        off_veh=sum(float(r['off_departures']) for r in f),
                        end_stock_veh=float(c[-1]['n_veh']),
                        mean_density=sum(float(r['rho_veh_per_km_lane']) for r in c)/5,
                        vehicle_weighted_snapshot_speed_kmh=(sum(float(r['n_veh'])*float(r['v_kmh']) for r in eligible)/weight if weight else None))
                row[kind]=dict(arms=arms,delta={k:(arms['release'][k]-arms['hold'][k]
                    if arms['release'][k] is not None and arms['hold'][k] is not None else None) for k in arms['hold']})
            rows.append(row)
    with (OUT/'cell_response.csv').open(encoding='utf-8-sig',newline='') as f:
        reference={int(r['cell']):r for r in csv.DictReader(f) if r['arm']=='release'}
    for cell in range(31):
        for kind in ('actual','predicted'):
            value=sum(r[kind]['delta']['downstream_veh'] for r in rows if r['cell']==cell)
            assert abs(value-float(reference[cell][kind+'_downstream_crossings']))<1e-7
    save(target,dict(rows=rows,pins=pins,new_rollouts=0,new_native_runs=0,fzp_rescans=0,
        full_horizon_flow_parity=True,control='release minus hold at the same2670.1s microscopic state',
        speed_basis='Vehicle-weighted mean of five30s endpoint speed snapshots per150s; not a continuous trajectory mean.',
        limitations=['Retrospective localization only; not future prediction inputs or a capacity estimate.',
                     'Cell-specific speed, density and discharge differences do not alone identify their causal mechanism.']))
    print(json.dumps({'output':str(target),'cells22_23_24':[
        dict(cell=r['cell'],start_sec=r['start_sec'],actual=r['actual']['delta'],predicted=r['predicted']['delta'])
        for r in rows if r['cell'] in (22,23,24)]}),flush=True)


def local_lane_response():
    """One causal sparse-lane candidate and its constant-rate ablation, no grid."""
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    parent=HERE/'closedloop9000_d4e2_analysis';base=parent/'recovery_flow_audit'
    out=base/'local_lane_candidate';out.mkdir(exist_ok=True)
    retry = (out/'protocol.json').exists()
    if retry:
        assert not (out/'summary.json').exists() and not (out/'attempt2_source_pins.json').exists()
        assert load(out/'failure.json')['error'] == "ValueError('Missing or extra component desired-speed observations')"
        (out/'failure_attempt1.json').write_bytes((out/'failure.json').read_bytes())
    local=base/'native10484/local_state';initial=load(local/'initial_state.json')
    with gzip.open(local/'past_frames.json.gz','rt',encoding='utf-8') as f:past=json.load(f)['frames']
    import bisect
    geometry_manifest=load(HERE/'selected/plant_n31_v2.json')
    geometry_path=ROOT/geometry_manifest['sources']['geometry']['path'];geometry=load(geometry_path)
    assert sha(geometry_path)==geometry_manifest['sources']['geometry']['sha256']
    offsets={z['link']:z['offset_m'] for z in geometry['chains']['FW_E']}
    with (local/'exchange_5s.csv').open(encoding='utf-8-sig',newline='') as f:
        observations={(float(z['start']),int(z['donor'])):int(z['inside_region_endpoint_changes'])
                      for z in csv.DictReader(f) if z['arm']=='past'}
    # Three shared exchange parameters: two baseline hazards and one speed-gap
    # sensitivity. Likelihood uses only past endpoint changes and donor stock.
    training=[];speed_scale=110.
    for t in sorted(map(float,past))[:-1]:
        grouped={(c,g):[] for c in (22,23) for g in (0,1)}
        for z in past[str(t)]:
            if z[1] not in offsets:continue
            c=bisect.bisect_right(geometry['bounds']['FW_E'],offsets[z[1]]+z[3])-1
            if c in (22,23):grouped[c,0 if z[2]==1 else 1].append(z)
        for g in (0,1):
            terms=[]
            for c in (22,23):
                donor,recipient=grouped[c,g],grouped[c,1-g]
                assert donor and recipient, 'Empty-group speed is not identified by this fit'
                dv=sum(z[4] for z in recipient)/len(recipient)-sum(z[4] for z in donor)/len(donor)
                terms.append((len(donor)*5,dv/speed_scale))
            training.append(dict(time=t,g=g,y=observations[t,g],terms=terms))
    def profile(beta):
        exposures=[sum(n*math.exp(beta*x) for n,x in z['terms']) for z in training]
        counts=[sum(z['y'] for z in training if z['g']==g) for g in (0,1)]
        totals=[sum(e for e,z in zip(exposures,training) if z['g']==g) for g in (0,1)]
        hazards=[c/e for c,e in zip(counts,totals)]
        loss=sum(e*hazards[z['g']]-z['y']*math.log(e*hazards[z['g']]) for e,z in zip(exposures,training))
        return loss,hazards
    # One scalar bounded likelihood solve; no physical-error/TTT objective.
    lo,hi=0.,20.;phi=(math.sqrt(5)-1)/2
    c=hi-phi*(hi-lo);d=lo+phi*(hi-lo)
    for _ in range(60):
        if profile(c)[0]<profile(d)[0]:hi,d=d,c;c=hi-phi*(hi-lo)
        else:lo,c=c,d;d=lo+phi*(hi-lo)
    beta=min((0.,20.,(lo+hi)/2),key=lambda x:profile(x)[0])
    ctx=lpr.load_sources(parent/'local_merge_cell23/candidate_manifest.json');model=ctx['component']
    spec=dict(schema='local-merge-lanes/v1',road='FW_E',cutoff=initial['cutoff'],
              cells=initial['cells'],ramps={'RM_C10484':0})
    variants={name:dict(spec,exchange=dict(rates_per_sec=profile(b)[1],speed_sensitivity=b,speed_scale_kmh=speed_scale))
              for name,b in [('constant',0.),('speed_response',beta)]}
    sources=[Path(__file__),local/'initial_state.json',local/'past_frames.json.gz',local/'exchange_5s.csv',
             ROOT/'evaluation/controllers/physical_lane_groups.py',ROOT/'evaluation/controllers/area_freeway_accounting.py',
             ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    protocol=dict(train_window=[2520.1,2670.1],calibration='Past endpoint-change Poisson likelihood; three shared exchange parameters only',
        beta_domain=[0.,20.],coefficient_grid=0,max_new_rollouts=10,max_wall_sec=180,
        active_cells=[22,23],unchanged='Canonical31 cells elsewhere, FD/merge/recovery coefficients, physical jam storage, off dynamics, commands, demand, objective; VSL cohort fractions preserved and shared by local groups.',
        assumptions='Uniform lane shares at aggregate neighbours; lane1/lanes2-3 share within-cell VSL command fractions. Same-cell and cross-cell endpoint changes pooled; unresolved5s paths are not exact hazards.',
        qualification='Candidate only. Full v2/SDMPC and independent seed not qualified. No new native or push.',
        physical_gate='All mass and source/receiving constraints; no speed above200km/h; no negative/projected inventory. No grid if it fails.',
        comparison='Existing cell23 model vs sparse constant/speed-responsive exchange, four executed-command arms.',pins={str(p):sha(p) for p in sources})
    frozen=dict(beta=beta,at_bound=beta in (0.,20.),loss0=profile(0.)[0],loss_selected=profile(beta)[0],variants=variants)
    if retry:
        assert load(out/'frozen_exchange.json')==frozen, 'Do not refit after validation'
        save(out/'attempt2_source_pins.json',dict(reason='Repair pure desired-speed audit for two actual local groups plus unused aggregate call; physical equations and fitted coefficients unchanged.',pins=protocol['pins']))
    else:
        save(out/'protocol.json',protocol)
        save(out/'frozen_exchange.json',frozen)
    begin=time.perf_counter();results=[];disabled={};new_count=0
    records=load(HERE/'heldout53_response_v2/capture.json')['records']
    for rec in records:
        arm=rec['arm'];args,kwargs=read_primitive_capture(rec['input'],rec['sha256'])
        truth=ObservationData(HERE/'heldout53_response_v2/observations'/arm)
        times=[round(2670.1+j*30,6) for j in range(16)]
        observed={(t,int(z['cell'])):z for t in times for z in truth.cells[t] if z['road']=='FW_E'}
        oldpath=parent/'local_merge_cell23/nu0.25_delta2'/('s53_late_'+arm+'.json.gz')
        with gzip.open(oldpath,'rt',encoding='utf-8') as f:old=json.load(f)
        if arm in ('hold','release'):
            current=model.rollout(*copy.deepcopy(args),**copy.deepcopy(kwargs));new_count+=1
            normalized=json.loads(json.dumps(current,allow_nan=False))
            disabled[arm]={k:normalized[k]==old[k] for k in ('cells','flows','ports','ramps')}
            assert all(disabled[arm].values()), 'Disabled path changed recorded physical trajectory'
            save(out/'disabled_check_normalized.json',dict(exact=disabled,note='Serialize numeric map keys exactly as historical JSON before comparing. First raw in-memory equality failed only on key types.'))
        for name in ('existing','constant','speed_response'):
            if name=='existing':pred=old
            else:
                assert new_count<10 and time.perf_counter()-begin<180
                kw=copy.deepcopy(kwargs);kw['local_merge_group_dynamics']={'FW_E':variants[name]}
                try:pred=model.rollout(*copy.deepcopy(args),**kw)
                except Exception as exc:
                    save(out/'failure.json',dict(variant=name,arm=arm,error=repr(exc),new_count=new_count,results=results))
                    raise
                new_count+=1
                with gzip.open(out/(name+'_'+arm+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            tab={(round(z['time_s'],6),z['cell']):z for z in pred['cells']}
            pflows={(round(z['window_end_s'],6),z['cell']):z for z in pred['flows']}
            rmse=lambda pairs:math.sqrt(sum((x-y)**2 for x,y in pairs)/len(pairs))
            cells={}
            for c in range(21,26):
                cells[c]=dict(speed_rmse=rmse([(tab[t,c]['v_kmh'],float(observed[t,c]['v_kmh'])) for t in times[1:]]),
                    mean_speed=sum(tab[t,c]['v_kmh'] for t in times[1:])/15,
                    observed_mean_speed=sum(float(observed[t,c]['v_kmh']) for t in times[1:])/15,
                    end_n=tab[times[-1],c]['n_veh'],observed_end_n=float(observed[times[-1],c]['n_veh']),
                    discharge=sum(pflows[t,c]['downstream_crossings'] for t in times[1:]),
                    observed_discharge=sum(float(truth.flows[t,'FW_E',c]['downstream_crossings']) for t in times[1:]))
            port_ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|{str(o) for o,v in model.offramps.items() if v['road']=='FW_E'}
            costs={}
            for kind,table in [('actual',observed),('predicted',tab)]:
                ns={t:sum(float(table[t,c]['n_veh']) for c in range(31)) for t in times[1:]}
                ns[times[0]]=sum(float(observed[times[0],c]['n_veh']) for c in range(31))
                ports={t:(sum(z['n_veh'] for z in pred['ports'] if abs(z['time_s']-t)<1e-6)+sum(z['end']['connector_veh'] for z in pred['ramps'] if abs(z['end_sec']-t)<1e-6)
                    if kind=='predicted' else sum(float(truth.ports[t,o]['end_n_veh']) for o in port_ids)) for t in times[1:]}
                ports[times[0]]=sum(float(truth.ports[times[0],o]['end_n_veh']) for o in port_ids)
                integral=lambda n:sum((n[x]+n[y])*(y-x)/7200 for x,y in zip(times,times[1:]))
                costs[kind]=dict(main=integral(ns),ports=integral(ports),total=integral(ns)+integral(ports))
            local_detail=pred.get('local_merge_groups',{}).get('FW_E',{})
            ramp=[z for z in pred['ramps'] if z['ramp']=='RM_C10484']
            whole_n=rmse([(tab[t,c]['n_veh'],float(observed[t,c]['n_veh'])) for t in times[1:] for c in range(31)])
            whole_q=rmse([(pflows[t,c]['terminal_exits' if c==30 else 'downstream_crossings'],float(truth.flows[t,'FW_E',c]['terminal_exits_inferred' if c==30 else 'downstream_crossings'])) for t in times[1:] for c in range(31)])
            result=dict(variant=name,arm=arm,cells=cells,costs=costs,whole_stock_rmse=whole_n,whole_flow_rmse=whole_q,
                merge10484=sum(z['accepted_merge_veh'] for z in ramp),posthead_final=ramp[-1]['end']['downstream_travelling_veh']+ramp[-1]['end']['merge_ready_veh'],
                local_mass_residual=local_detail.get('maximum_mass_residual'),maximum_local_speed=local_detail.get('maximum_speed'),
                global_mass_residual=max(z['continuity_residual_max_veh'] for z in pred['diagnostics']['roads']),
                port_mass_residual=max(abs(z['conservation_residual_veh']) for z in pred['ports']+pred['ramps']))
            if name!='existing':assert result['local_mass_residual']<1e-7 and result['maximum_local_speed']<200
            assert result['global_mass_residual']<1e-7 and result['port_mass_residual']<1e-7
            results.append(result)
            save(out/'partial_results.json',results)
            print(json.dumps(dict(variant=name,arm=arm,stock_rmse=whole_n,flow_rmse=whole_q,merge10484=result['merge10484'])),flush=True)
    for z in results:
        held=next(r for r in results if r['variant']==z['variant'] and r['arm']=='hold')
        z['predicted_delta']=z['costs']['predicted']['total']-held['costs']['predicted']['total']
        z['actual_delta']=z['costs']['actual']['total']-held['costs']['actual']['total']
    save(out/'summary.json',dict(rows=results,disabled=disabled,new_rollouts=new_count,wall_sec=time.perf_counter()-begin,
        objective_scope='East31 plus8connectors using matching30s trapezoids; not full Omega or outside waits.',
        new_native=0,gain_qualified=False,production_adopted=False,future_observation_inputs=False))


if __name__=='__main__':
    {'capture':capture,'predict':predict,'compare':compare_saved,'decompose':decompose_saved,
     'capture-response2220':capture_response2220,
     'capture-extended-nc':capture_extended_nc_windows,
     'predict-extended-nc':predict_extended_nc_windows,
     'audit-saved-vsl-discharge':audit_saved_vsl_discharge,
     'audit-early-control-flow-ledger':audit_early_control_flow_ledger,
     'audit-cellwise-receiving-contract':audit_cellwise_receiving_contract,
     'audit-early-rm-timing':audit_early_rm_timing,
     'check-cellwise-seed53':check_cellwise_seed53,
     'calibrate-local-ramp-gap10484':calibrate_local_ramp_gap10484,
     'audit-saved-vsl-speed-terms':audit_saved_vsl_speed_terms,
     'calibrate-local-anticipation':calibrate_local_anticipation,
     'calibrate-local-fd-18-20':calibrate_local_fd_18_20,
     'calibrate-cellwise-state':lambda:calibrate_cellwise('state'),
     'calibrate-cellwise-response':lambda:calibrate_cellwise('response'),
     'calibrate-cellwise-jacobian':calibrate_cellwise_jacobian,
     'audit-observed-state-pressure':audit_observed_state_pressure,
     'audit-five-second-state-pressure':lambda:audit_observed_state_pressure(integrate_five=True),
     'audit-native-velocity-transport':audit_native_velocity_transport,
     'audit-native-lane-sufficiency':audit_native_lane_sufficiency,
     'prepare-native-distribution-split':prepare_native_distribution_split,
     'countercheck-vsl-shape':countercheck_vsl_shape,
     'predict-response2220':lambda:[predict(
         manifest_path=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json',
         input_dir=HERE/'baseline_reproduction_20260929'/f'component2220_s{seed}_inputs_v2',
         output=HERE/'baseline_reproduction_20260929'/f'component2220_s{seed}_current_v2') for seed in (29,43)],
     'diagnose-response2220-inflow':lambda:[predict(
         manifest_path=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json',
         input_dir=HERE/'baseline_reproduction_20260929'/f'component2220_s{seed}_inputs_v2',
         output=HERE/'baseline_reproduction_20260929'/f'component2220_s{seed}_conditional_inflow',
         inflow_diagnostic=True) for seed in (29,43)],
     'predict-current-benchmark':lambda:predict(
         manifest_path=HERE/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_manifest.json',
         output=HERE/'baseline_reproduction_20260929/component2670_current'),
     'initial-cohort':initial_cohort_exits,'delay-bounds':cohort_delay_bounds,
     'capture-decisions':capture_decisions,'decision-screen':decision_screen,
     'anticipation-response':anticipation_response,
     'merge-speed-response':lambda:anticipation_response(merge_speed=True),
     'lane-drop-response':lambda:anticipation_response(lane_drop=True),
     'decision-regret-check':decision_regret_check,
     'receiving-audit':receiving_audit,'cached-wave-audit':cached_wave_audit,
     'recovery-response':recovery_response,'local-speed-balance':local_speed_balance,
     'local-merge-calibration':lambda:recovery_response(local_merge=True),
     'recovery-pair-terms':lambda:local_speed_balance(recovery_pair=True),
     'recovery-pair-calibration':lambda:recovery_response(recovery_pair=True),
     'recovery-flow-audit':recovery_flow_audit,
     'conditional-ramp-arrival-audit':conditional_ramp_arrival_audit,
     'cached-posthead-receiving-audit':cached_posthead_receiving_audit,
     'local-lane-response':local_lane_response,
     'prepare-seed53':prepare_seed53_response,
     'off-entry-response':off_entry_response}[sys.argv[1]]()
