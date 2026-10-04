"""One finite closed-run extraction/capture/prediction; no simulator or fitting.

Historical observation/input utilities and current model imports run in separate
processes. Never run this while any of the four owned native jobs remains alive.
"""
import argparse
import csv
import copy
import gzip
import hashlib
import json
import os
import pickle
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
I=HERE.parent
ROOT=I.parents[2]
OLD=ROOT.parent/'control-full-review'
RUNS=Path('D:/VISSIM_runs/20260928_release2670_s53_v2')
T0=2670.1
END=3120.1
ARMS=('hold','release','hold_vsl90','release_vsl90')

def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def status(stage,**kw):save(HERE/'postprocess_status.json',dict(stage=stage,time=time.time(),**kw))

def configure_case(case_dir):
    """Reuse this processor without changing a completed case or its inputs."""
    global HERE,RUNS
    if case_dir is None:return
    case=Path(case_dir).resolve()
    assert case.parent==I.resolve(), 'Case must belong to this integration workspace'
    protocol=load(case/'protocol.json')
    runs=Path(protocol['results_root'])
    assert runs.is_absolute() and runs.is_dir(), 'Missing explicit native results root'
    assert protocol['arms']==list(ARMS)
    assert (protocol['cutoff_sec'],protocol['horizon_sec'],protocol['terminal_sec'])==(T0,END-T0,3300)
    assert protocol['seed'] not in (31,37,41)
    HERE=case;RUNS=runs

def verify_vsl_commands(commands,profile,network):
    """Reconstruct every sign from saved XML and the actual event profile."""
    initial={}
    for sign in ET.parse(network).findall('./desSpeedDecisions/desSpeedDecision'):
        speeds={int(x.get('desSpeedDistr')) for x in sign.findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')}
        assert len(speeds)==1, 'Per-class VSL requires an explicit input mapping'
        initial[sign.get('no')]=speeds.pop()
    events=sorted(profile['vsl_commands'],key=lambda e:(e['time_s'],e['dsd_no']))
    assert all(e['time_s'] in commands and str(e['dsd_no']) in initial for e in events)
    for t,command in sorted(commands.items()):
        expected=dict(initial)
        for event in events:
            if event['time_s']<=t:expected[str(event['dsd_no'])]=event['speed_id']
        assert command['vsl']==expected, ('VSL capture differs from native profile',t)
    return dict(signs=len(initial),command_times=len(commands),native_events=len(events),passed=True)


def closed():
    assert not (RUNS/'STOP').exists(), 'STOP exists; do not resume'
    queue=load(RUNS/'task_status.json');assert queue['phase']=='native_complete', queue['phase']
    assert len(queue['jobs'])==4 and all(j['completed'] and j['exit_code']==0 for j in queue['jobs'])
    for arm in ARMS:
        r=load(RUNS/arm/'run/run.json')
        assert r['completed'] and r['finished'] and not r['owned_native_alive'], arm
        v=load(RUNS/arm/'run/fixed_validation.json')
        assert v['passed'] and not v['unrecorded_signal_groups'], arm
    protocol=load(HERE/'protocol.json')
    for key in ('model_pins','execution_pins'):
        for path,digest in protocol[key].items():
            resolved=Path(path) if Path(path).is_absolute() else ROOT/path
            assert sha(resolved)==digest, path
    # Authoritative OS check, not just the presence of completion files.
    command=r"$ErrorActionPreference='Stop'; $names=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^Vissim'} | Select-Object ProcessId,CreationDate; ConvertTo-Json -InputObject @($names) -Compress"
    ps='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    result=subprocess.run([ps,'-NoProfile','-Command',command],capture_output=True,text=True,check=True)
    # Another user's simulation is never terminated. Postprocessing waits for
    # a quiet machine, matching the user's no-heavy-analysis-during-native rule.
    assert not json.loads(result.stdout), 'Native VISSIM is still running; defer analysis'
    return protocol

def extract():
    closed();sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    from diagnostics.fast_fixed_profile_verify import prefix_digest,native_record
    c=e.c;data,ctx,_,_=c.inputs();ref=data['rm']
    source=ROOT/load(I/'selected/plant_n31_v2.json')['sources']['network']['path']
    proof,membership,_=c.prior.compare.old.area_proof(source,ref.geometry)
    assert proof['status']=='PASS';save(HERE/'omega_membership_proof.json',proof)
    folder=HERE/'observations';folder.mkdir(exist_ok=False)
    common_prefix=None;common_signals=None;initial=None;results=[]
    east_sg={str(m['sc'])+':1' for m in ctx[0]['meters'].values() if m['connector'] in (10639,10681,10490,10484)}
    for arm in ARMS:
        run=RUNS/arm/'run';valid=load(run/'fixed_validation.json')
        frames=native_record(run,load(RUNS/f'prepared_{arm}/prepared.json'),3300)['frames']
        changed=east_sg if arm.startswith('release') else set()
        if common_signals is None:common_signals=frames
        else:
            unaffected=lambda rows:{t:{k:v for k,v in row.items() if k not in changed} for t,row in rows.items()}
            assert unaffected(frames)==unaffected(common_signals), 'Untargeted signals differ'
        fzp,=(run/'vissim_eval').glob('*.fzp');prefix=prefix_digest(fzp,2700,recording_grid=(5,.1))
        if common_prefix is None:common_prefix=prefix
        assert prefix==common_prefix, 'Microscopic common prefix differs'
        events=[z for p in run.glob('*.err') for z in c.prior.extract.parse_bytes(p.read_bytes())['events']]
        events=[json.loads(z) for z in sorted({json.dumps(z,sort_keys=True) for z in events})]
        removals=[z for z in events if z['kind']=='lane_change_removal']
        obs=c.prior.extract.Observer(ref.geometry,removals,interval_sec=5,phase_sec=.1)
        ports=c.prior.extract.PortObserver(ref.geometry,interval_sec=5,phase_sec=.1)
        c.prior.compare.END=3300;evidence={};stocks=[];before=fzp.stat()
        for t,frame in c.prior.compare.raw_frames(fzp,evidence,(obs,ports)):
            if T0<=t<=END:stocks.append(dict(time_s=t,network_n=len(frame),omega_n=sum(int(membership[z[0]]) for z in frame.values())))
        assert len(stocks)==91 and (before.st_size,before.st_mtime_ns)==(fzp.stat().st_size,fzp.stat().st_mtime_ns)
        dest=folder/arm;dest.mkdir()
        for name,rows in (('cells_30s',obs.cells),('flows_30s',obs.flows),('ports_30s',ports.rows),('boundaries_30s',obs.boundary_rows),('port_events',ports.events),('area_stocks_5s',stocks)):
            c.prior.table(dest/(name+'.csv'),rows)
        save(dest/'geometry.json',ref.geometry);save(dest/'port_cohorts_30s.json',ports.snapshots)
        save(dest/'manifest.json',dict(native_phase_sec=.1,files={p.name:sha(p) for p in dest.iterdir()}))
        truth=c.prior.ObservationData(dest);at0=(truth.cells[T0],truth.port_cohorts[str(T0)])
        if initial is None:initial=at0
        assert initial==at0, 'Initial cell/cohort state differs'
        checkpoints=valid['native_network_performance_checkpoints'];a,b=checkpoints['2670'],checkpoints['3120']
        internal=(b['TravTmTot']-a['TravTmTot'])/3600;latent=(b['DelayLatent']-a['DelayLatent'])/3600
        integral=lambda key:sum((x[key]+y[key])*(y['time_s']-x['time_s'])/7200 for x,y in zip(stocks,stocks[1:]))
        omega=integral('omega_n');network=integral('network_n')
        results.append(dict(arm=arm,prefix=prefix,initial_native=a,final_native=b,
            native_network_residence_veh_h=internal,native_latent_veh_h=latent,native_total_veh_h=internal+latent,
            omega_snapshot_veh_h=omega,network_snapshot_veh_h=network,outside_omega_snapshot_veh_h=network-omega,
            native_error_events=events,raw_evidence=evidence))
        save(HERE/(arm+'_native.json'),results[-1]);status('extracted_arm',arm=arm)
    base=results[0]
    for r in results:
        assert r['initial_native']==base['initial_native']
        r['delta']={k:r[k]-base[k] for k in ('native_network_residence_veh_h','native_latent_veh_h','native_total_veh_h','omega_snapshot_veh_h','outside_omega_snapshot_veh_h')}
    save(HERE/'native_summary.json',dict(rows=results,common_prefix_exact=True,
        intervals={'component_and_stock_snapshots':[T0,END],'native_checkpoints':[2670,3120]},
        ttd_not_computed=True,limitations=['Snapshot costs use5s trapezoids. Native checkpoint costs use their own integer-time cumulative counters.',
        'No TTD total is inferred from disappearances or terminal stock. This response test scores cost and physical flows.']))

def capture():
    closed();sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    c=e.c;_,ctx,_,_=c.inputs();state=c.prior.ObservationData(HERE/'observations/hold')
    prior=load(e.HERE/'legal_release2670/protocol.json');local=list(copy.deepcopy(ctx));local[3]=prior['port_profile']
    model=c.prior.one.base.load_base_model(state.geometry,e.HERE/'local_fd/candidate.json')
    parameters=load(I/'selected/port_gain/parameters.json')['parameters'];rows=[]
    class Captured(BaseException):pass
    for arm in ARMS:
        path=e.HERE/'legal_release2670'/f'{arm}_commands.json';commands={int(t):v for t,v in load(path).items()}
        profile=load(RUNS/(arm+'.json'))
        expected=[dict(time_s=t,sc_no=m['sc'],green_sec=z['greens'][mid]) for t,z in sorted(commands.items()) if 0<t<3300 for mid,m in ctx[0]['meters'].items()]
        assert expected==profile['meter_commands'], 'Capture commands differ from native profile'
        prepared=load(RUNS/f'prepared_{arm}/prepared.json')
        vsl_proof=verify_vsl_commands(commands,profile,prepared['network'])
        save(HERE/(arm+'_commands.json'),commands)
        def intercept(*args,**kwargs):
            json.dumps([args,kwargs],allow_nan=False)
            p=HERE/(arm+'_input.pickle');assert not p.exists();p.write_bytes(pickle.dumps((args,kwargs),protocol=5))
            rows.append(dict(arm=arm,input=str(p),sha256=sha(p),commands_sha256=sha(HERE/(arm+'_commands.json')),vsl_command_proof=vsl_proof))
            raise Captured()
        model.rollout=intercept
        try:
            c.prior.forecast(model,parameters,state,state,T0,450,*local[:-1],commands,True)
            raise AssertionError('Did not intercept input-only builder')
        except Captured:pass
    save(HERE/'capture.json',dict(records=rows,cutoff=T0,horizon=450,future_truth_used_as_input=False,
        builder_pins={str(Path(c.prior.__file__)):sha(c.prior.__file__)},scope='Canonical past-truncation guard executes before rollout capture. No model forecast or score in this process.'))

def assess_mainline(results):
    """Apply the declared decision thresholds to every pair, without refitting."""
    assessments=[]
    for family in ('baseline','candidate'):
        rows=[r for r in results if r['family']==family]
        pairs=[]
        for index,a in enumerate(rows):
            for b in rows[index+1:]:
                actual=b['actual_main']-a['actual_main']
                predicted=b['predicted_main']-a['predicted_main']
                flows=[]
                quantities=[('merge_'+rid,a['actual_merges'][rid],b['actual_merges'][rid],a['predicted_merges'][rid],b['predicted_merges'][rid]) for rid in a['actual_merges']]
                for key,actual_key in (('source_admissions','source_admissions'),('off_departures','off_departures'),('terminal_exits','terminal_exits_inferred')):
                    quantities.append((key,a['actual_flows'][actual_key],b['actual_flows'][actual_key],a['predicted_flows'][key],b['predicted_flows'][key]))
                for cell in a['actual_cell_down']:
                    quantities.append(('cell_'+cell+'_downstream',a['actual_cell_down'][cell],b['actual_cell_down'][cell],a['predicted_cell_down'][cell],b['predicted_cell_down'][cell]))
                for name,aa,ab,pa,pb in quantities:
                    da,dp=ab-aa,pb-pa
                    flows.append(dict(quantity=name,actual_delta_veh=da,predicted_delta_veh=dp,meaningful=abs(da)>=10,sign_matches=da*dp>0 if abs(da)>=10 else None))
                pairs.append(dict(reference=a['arm'],candidate=b['arm'],actual_main_delta_veh_h=actual,predicted_main_delta_veh_h=predicted,
                    meaningful=abs(actual)>=.5,sign_matches=actual*predicted>0 if abs(actual)>=.5 else None,flows=flows))
        selected=min(rows,key=lambda r:r['predicted_main']);best=min(rows,key=lambda r:r['actual_main'])
        regret=selected['actual_main']-best['actual_main']
        assessments.append(dict(family=family,pairs=pairs,selected=selected['arm'],actual_best=best['arm'],actual_selection_regret_veh_h=regret,
            selection_within_half_veh_h=regret<=.5,meaningful_pairs=sum(p['meaningful'] for p in pairs),
            incorrect_meaningful_pairs=sum(p['sign_matches'] is False for p in pairs),
            native_accounting={r['arm']:r['native_accounting'] for r in rows}))
    return dict(assessments=assessments,ttt_threshold_veh_h=.5,flow_threshold_veh=10,
        scope='Mainline only; small effects inconclusive. No full-Omega or SDMPC qualification from this check.')


def predict():
    protocol=closed();sys.path.insert(0,str(ROOT))
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.scoring import score_rollout
    from diagnostics.sdmpc_n31_20260924.integration_20260926.replay_congested_component import read_primitive_capture
    capture=load(HERE/'capture.json');results=[];times=[round(T0+i,6) for i in range(0,451,30)]
    for family,path in (('baseline',I/'selected/plant_n31_v2.json'),('candidate',HERE/'candidate_manifest.json')):
        context=lpr.load_sources(path);model=context['component'];dest=HERE/family;dest.mkdir(exist_ok=False)
        ids={str(v['connector']) for v in model.ramps.values() if v['road']=='FW_E'}|{str(k) for k,v in model.offramps.items() if v['road']=='FW_E'}
        assert len(ids)==8
        for record in capture['records']:
            arm=record['arm'];args,kw=read_primitive_capture(record['input'],record['sha256'])
            assert args[2]==context['parameters'] and kw['horizon_sec']==450 and kw['roads']==['FW_E']
            pred=model.rollout(*args,**kw)
            with gzip.open(dest/(arm+'_prediction.json.gz'),'wt',encoding='utf-8') as f:json.dump(pred,f,allow_nan=False)
            # Future targets are consumed only after this prediction completes.
            truth=ObservationData(HERE/'observations'/arm);score=score_rollout(truth,T0,pred,'FW_E',include_source_boundary=True)
            assert not score['invalid'], (family,arm,score['invalid'])
            main={t:sum(r['n_veh'] for r in pred['cells'] if abs(r['time_s']-t)<1e-6) for t in times[1:]}
            ports={t:sum(r['n_veh'] for r in pred['ports'] if abs(r['time_s']-t)<1e-6)+sum(r['end']['connector_veh'] for r in pred['ramps'] if abs(r['end_sec']-t)<1e-6) for t in times[1:]}
            actual_main={t:sum(float(r['n_veh']) for r in truth.cells[t] if r['road']=='FW_E') for t in times}
            actual_ports={t:sum(float(truth.ports[t,k]['end_n_veh']) for k in ids) for t in times}
            main[T0]=actual_main[T0];ports[T0]=actual_ports[T0]
            integral=lambda v:sum((v[a]+v[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
            residual=max(abs(r['conservation_residual_veh']) for r in pred['ports']+pred['ramps']);assert residual<1e-7
            actual_flows=[v for (t,road,cell),v in truth.flows.items() if road=='FW_E' and T0<t<=END]
            merges={rid:sum(z['accepted_merge_veh'] for z in pred['ramps'] if z['ramp']==rid) for rid,v in model.ramps.items() if v['road']=='FW_E'}
            actual_merges={rid:sum(float(truth.ports[t,str(model.ramps[rid]['connector'])]['departures_veh']) for t in times[1:]) for rid in merges}
            r=dict(family=family,arm=arm,predicted_main=integral(main),predicted_ports=integral(ports),actual_main=integral(actual_main),actual_ports=integral(actual_ports),conservation_max=residual,score=score,
                predicted_flows={k:sum(float(x[k]) for x in pred['flows']) for k in ('ramp_merges','off_departures','terminal_exits','source_admissions')},
                actual_flows={k:sum(float(x[k]) for x in actual_flows) for k in ('off_departures','terminal_exits_inferred','source_admissions')},
                predicted_merges=merges,actual_merges=actual_merges)
            cell_ids=sorted({int(x['cell']) for x in actual_flows})
            r['actual_cell_down']={str(c):sum(float(x['downstream_crossings']) for x in actual_flows if int(x['cell'])==c) for c in cell_ids}
            r['predicted_cell_down']={str(c):sum(float(x['downstream_crossings']) for x in pred['flows'] if int(x['cell'])==c) for c in cell_ids}
            r['native_accounting']={k:sum(float(x[k]) for x in actual_flows) for k in ('unexplained_entries','unexplained_losses','native_removals')}
            r['predicted_component']=r['predicted_main']+r['predicted_ports'];r['actual_component']=r['actual_main']+r['actual_ports'];results.append(r)
            save(dest/(arm+'_result.json'),r);status('predicted_arm',family=family,arm=arm)
    selections=[]
    for family in ('baseline','candidate'):
        rows=[r for r in results if r['family']==family];held=rows[0]
        for r in rows:r.update(predicted_delta=r['predicted_component']-held['predicted_component'],actual_delta=r['actual_component']-held['actual_component'])
        best=min(rows,key=lambda r:r['predicted_component']);actual=min(rows,key=lambda r:r['actual_component'])
        selections.append(dict(family=family,selected=best['arm'],observed_best=actual['arm'],selection_loss_veh_h=best['actual_component']-actual['actual_component']))
    save(HERE/'mainline_validation.json',assess_mainline(results))
    save(HERE/'prediction_summary.json',dict(rows=results,selections=selections,rollouts=8,seed=protocol['seed'],refit=False,production_adopted=False,
        scope='East31cells+4on/4offconnector residence only. Native Omega and outside costs are in native_summary.json, not forecast by this component.',
        source_protocol_sha256=sha(HERE/'protocol.json'),source_script_sha256=sha(__file__)))
    status('complete',new_rollouts=8,refit=False,production_adopted=False)

def distribution_split():
    """Score the two closed native mean/shape experiments, without fitting."""
    out=I/'baseline_reproduction_20260929/native_distribution_split/attempt2'
    protocol=load(out/'protocol.json');t0,end=protocol['scoring_window'];terminal=protocol['terminal_sec']
    runs=Path(protocol['plans'][0]['output']).parents[1]
    assert not (runs/'STOP').exists(), 'STOP exists; do not resume'
    assert (t0,end,terminal)==(2220.1,2670.1,3000)
    for plan in protocol['plans']:
        receipt=load(Path(plan['output'])/'run.json')
        assert receipt['completed'] and receipt['finished'] and not receipt['owned_native_alive'], plan['arm']
        assert receipt['error'] is None and receipt['exit_code']==0
        valid=load(Path(plan['output'])/'fixed_validation.json')
        assert valid['passed'] and not valid['unrecorded_signal_groups']
    command=r"$ErrorActionPreference='Stop'; $names=Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^Vissim'} | Select-Object ProcessId,CreationDate; ConvertTo-Json -InputObject @($names) -Compress"
    ps='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    result=subprocess.run([ps,'-NoProfile','-Command',command],capture_output=True,text=True,check=True)
    assert not json.loads(result.stdout), 'Native VISSIM still running; defer extraction'
    for p,digest in protocol['pins'].items():assert sha(p)==digest,p
    folder=out/'analysis';folder.mkdir(exist_ok=False)
    (folder/'postprocessor_executed.py.txt').write_bytes(Path(__file__).read_bytes())
    save(folder/'status.json',dict(stage='extracting',new_fzp_files=2,model_fit=False))
    # Historical observation utilities only, in this dedicated process.
    sys.path.insert(0,str(OLD))
    from diagnostics.metanet_net_gain_goal_20260924 import extract as e
    from diagnostics.fast_fixed_profile_verify import prefix_digest,native_record
    c=e.c;data,ctx,_,_=c.inputs();geometry=data['none'].geometry
    source=I/'selected/network/native_seed29.inpx'
    proof,membership,_=c.prior.compare.old.area_proof(source,geometry)
    assert proof['status']=='PASS';save(folder/'omega_membership_proof.json',proof)
    reference_run=Path('D:/VISSIM_runs/20260924_response2250_s29/vsl/run')
    reference_prepared=Path(load(reference_run/'run.json')['prepared'])
    reference_signals=native_record(reference_run,load(reference_prepared/'prepared.json'),terminal)['frames']
    records=[r for r in load(I/'decision_response/capture.json')['records'] if r['case']=='s29_early' and r['arm'] in ('none','vsl')]
    assert len(records)==2
    truths={r['arm']:c.prior.ObservationData(r['truth']) for r in records}
    initial=(truths['none'].cells[t0],truths['none'].port_cohorts[str(t0)])
    assert initial==(truths['vsl'].cells[t0],truths['vsl'].port_cohorts[str(t0)])
    reference_fzp,=(reference_run/'vissim_eval').glob('*.fzp')
    prefix=prefix_digest(reference_fzp,2250,recording_grid=(5,.1))
    nc=Path('D:/VISSIM_runs/20260924_bottleneck90_full_s29/none/run/vissim_eval/mtfc_s29_none_001.fzp')
    assert prefix_digest(nc,2250,recording_grid=(5,.1))==prefix
    native=[]
    for plan in protocol['plans']:
        arm=plan['arm'];run=Path(plan['output']);prepared=Path(plan['prepared'])
        assert native_record(run,load(prepared/'prepared.json'),terminal)['frames']==reference_signals, 'Untargeted signals differ'
        fzp,=(run/'vissim_eval').glob('*.fzp');before=fzp.stat()
        assert prefix_digest(fzp,2250,recording_grid=(5,.1))==prefix, 'Pre-intervention FZP data differ'
        events=[]
        for p in run.glob('*.err'):
            parsed=c.prior.extract.parse_bytes(p.read_bytes())
            assert not parsed['unparsed_removal_lines'], str(p)
            events.extend(parsed['events'])
        events=[json.loads(z) for z in sorted({json.dumps(z,sort_keys=True) for z in events})]
        obs=c.prior.extract.Observer(geometry,[z for z in events if z['kind']=='lane_change_removal'],interval_sec=5,phase_sec=.1)
        ports=c.prior.extract.PortObserver(geometry,interval_sec=5,phase_sec=.1)
        c.prior.compare.END=terminal;evidence={};stocks=[]
        for t,frame in c.prior.compare.raw_frames(fzp,evidence,(obs,ports)):
            if t0<=t<=end:stocks.append(dict(time_s=t,network_n=len(frame),omega_n=sum(int(membership[z[0]]) for z in frame.values())))
        assert len(stocks)==91 and (before.st_size,before.st_mtime_ns)==(fzp.stat().st_size,fzp.stat().st_mtime_ns)
        dest=folder/arm;dest.mkdir()
        for name,rows in (('cells_30s',obs.cells),('flows_30s',obs.flows),('ports_30s',ports.rows),('boundaries_30s',obs.boundary_rows),('port_events',ports.events),('area_stocks_5s',stocks)):
            c.prior.table(dest/(name+'.csv'),rows)
        save(dest/'geometry.json',geometry);save(dest/'port_cohorts_30s.json',ports.snapshots)
        save(dest/'manifest.json',dict(native_phase_sec=.1,files={p.name:sha(p) for p in dest.iterdir()}))
        truth=c.prior.ObservationData(dest);assert initial==(truth.cells[t0],truth.port_cohorts[str(t0)])
        truths[arm]=truth
        integral=lambda key:sum((a[key]+b[key])*(b['time_s']-a['time_s'])/7200 for a,b in zip(stocks,stocks[1:]))
        native.append(dict(arm=arm,evidence=evidence,source=str(fzp),source_size=before.st_size,source_mtime_ns=before.st_mtime_ns,
            omega_snapshot_veh_h=integral('omega_n'),network_snapshot_veh_h=integral('network_n'),native_error_events=events,
            common_prefix=prefix,all_signal_frames_exact=True,initial_cells_and_port_cohorts_exact=True))
        save(folder/(arm+'_native.json'),native[-1]);print(json.dumps(dict(extracted=arm)),flush=True)
    times=[round(t0+i,6) for i in range(0,451,30)];rows=[]
    definitions={str(b['connector']):b for b in geometry['boundaries'] if b['road']=='FW_E' and b['kind'] in ('ramp','offramp')}
    assert len(definitions)==8
    for arm,truth in truths.items():
        integral=lambda values:sum((values[a]+values[b])*(b-a)/7200 for a,b in zip(times,times[1:]))
        main={t:sum(float(r['n_veh']) for r in truth.cells[t] if r['road']=='FW_E') for t in times}
        costs={kind:integral({t:sum(float(truth.ports[t,k]['end_n_veh']) for k,d in definitions.items() if d['kind']==kind) for t in times}) for kind in ('ramp','offramp')}
        flows=[r for (t,road,cell),r in truth.flows.items() if road=='FW_E' and t0<t<=end]
        portrows=[r for (t,k),r in truth.ports.items() if k in definitions and t0<t<=end]
        row=dict(arm=arm,mainline_ttt=integral(main),ramp_ttt=costs['ramp'],off_ttt=costs['offramp'],
            component_ttt=integral(main)+sum(costs.values()),end_main_n=main[end],
            flows={key:sum(float(r[key]) for r in flows) for key in ('source_admissions','ramp_merges','off_departures','terminal_exits_inferred','native_removals','unexplained_entries','unexplained_losses')},
            port_unresolved_absences=sum(float(r['unresolved_absences_veh']) for r in portrows),
            max_main_mass_residual=max(abs(float(r['conservation_residual_veh'])) for r in flows),
            max_port_mass_residual=max(abs(float(r['conservation_residual_veh'])) for r in portrows),cells={})
        for cell in range(31):
            snapshots=[r for t in times[1:] for r in truth.cells[t] if r['road']=='FW_E' and int(r['cell'])==cell]
            populated=[r for r in snapshots if float(r['n_veh'])>0]
            row['cells'][str(cell)]=dict(mean_v_kmh=sum(float(r['v_kmh']) for r in populated)/len(populated) if populated else None,
                end_n=next(float(r['n_veh']) for r in truth.cells[end] if r['road']=='FW_E' and int(r['cell'])==cell),
                downstream_veh=sum(float(r['downstream_crossings']) for r in flows if int(r['cell'])==cell))
        assert row['max_main_mass_residual']==0 and row['max_port_mass_residual']==0
        rows.append(row)
    base=next(r for r in rows if r['arm']=='none')
    for row in rows:
        row['delta']={k:row[k]-base[k] for k in ('mainline_ttt','ramp_ttt','off_ttt','component_ttt','end_main_n')}
        row['delta']['flows']={k:row['flows'][k]-base['flows'][k] for k in base['flows']}
    for p,digest in protocol['pins'].items():assert sha(p)==digest,p
    save(folder/'summary.json',dict(rows=rows,native=native,protocol_sha256=sha(out/'protocol.json'),
        reference_signal_source=str(reference_run),common_prefix=prefix,scoring_window=[t0,end],new_native_runs=2,reused_native_runs=2,
        fit=False,adopted=False,ttd_not_computed=True,
        limitations=['One seed and initial state; not independent confirmation or controller qualification.',
        'Mean-only translates CDF110; shape-only translates CDF90 to the original mean. Shape includes higher moments, not only variance.',
        '31-cell mainline and8connector costs use identical30s trapezoids; Omega5s snapshots are diagnostic and do not include latent waiting.',
        'Terminal flows retain the existing geometry/time-qualified inference; disappearances and removals are not TTD.']))
    save(folder/'status.json',dict(stage='complete',new_native_runs=2,new_forecasts=0,fit=False,adopted=False))
    print(json.dumps([dict(arm=r['arm'],delta=r['delta']) for r in rows]),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',nargs='?',default='all',choices=('all','extract','capture','predict','distribution-split'))
    parser.add_argument('--case-dir',type=Path,help='Prepared case with its own protocol and frozen model')
    args=parser.parse_args();configure_case(args.case_dir);stage=args.stage
    if stage!='all':return {'extract':extract,'capture':capture,'predict':predict,'distribution-split':distribution_split}[stage]()
    closed();assert not (HERE/'postprocess_status.json').exists(), 'Preserve previous analysis attempts'
    try:
        for stage in ('extract','capture','predict'):
            status('starting_'+stage)
            root=ROOT if stage=='predict' else OLD
            env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root.parent.parent/'.review-deps/sdmpc')+';'+str(root),
                     NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
            with (HERE/(stage+'.log')).open('x',encoding='utf-8') as log:
                subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),stage,'--case-dir',str(HERE)],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    except BaseException as error:
        status('failed',stage_name=stage,error=str(error));raise

if __name__=='__main__':main()
