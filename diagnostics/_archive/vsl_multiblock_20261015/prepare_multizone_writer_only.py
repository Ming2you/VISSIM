"""One-arm VSL replay preparation and three matched exact355 forecasts.

Reuses the completed OFF2250 hold/90 experiment. No COM or native dispatch.
"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import copy,csv,gzip,hashlib,importlib.util,json,shutil,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
REL='diagnostics/sdmpc_n31_20260924/integration_20260926'
PACK=HERE/'command_metadata_repair'
OLD=Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold')
ANALYSIS=Path('E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2/native_analysis')
PROV=OLD/'run_provenance_sdmpc31_g_2250_hold_s29.json'
EXEC=ANALYSIS/'hold/execution.json'
CONFIG=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
MEM=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'
OUT=HERE/'writer_metadata_check2250'
OBS=Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(Path(p).read_bytes())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return [{k:v for k,v in row.items() if k!='metadata'} for row in csv.DictReader(f)]

def main():
    assert PACK.exists() and not OUT.exists() and not (PACK/'protocol.json').exists(),'Preserve existing completed attempts'
    assert read(HERE/'native_package_receipt.json')['status']=='exported_pending_preflight'
    assert all(read(HERE/'baseline_reuse_qualification.json')['checks'].values())
    prov=read(PROV);exe=read(EXEC);summary=read(ANALYSIS/'summary.json')
    assert prov['seed']==29 and prov['sim_period_sec']==2700
    assert exe['native_execution_passed'] and summary['counterfactual_valid'] and summary['paired_prefix_exact']
    F=OLD/('decisions_'+prov['name'])
    network=ROOT/REL/'selected/network/native_seed29.inpx'
    assert sha(network)==prov['files']['network']['sha256']
    physical_pins={}
    for key in ('demand_profile','control_mapping','vehicle_input_roles','urban_input_gate_map'):
        old=prov['files'][key]
        path=ROOT/Path(old['path']).relative_to(Path(prov['workspace_root']))
        assert sha(path)==old['sha256'],('Physical input differs',key)
        physical_pins[str(path)]=sha(path)
    sg=ROOT/REL/'selected/scenario/lane_native_b110_sgplan.vbs'
    assert sha(sg)==prov['files']['signal_group_plan']['sha256']
    physical_pins[str(sg)]=sha(sg)
    dest=PACK/'selected/commands'
    assert summary['original_initial_history_exact'] and summary['source_observed_model_inputs_exact']
    assert len(summary['observed_input_checks'])==15 and all(r['source_observations_exact'] for r in summary['observed_input_checks'])
    assert (OBS/'obs150/derived_002250.json').exists()
    assert {p.name for p in dest.iterdir()}=={f'action_{s:06d}.{ext}' for s in [1,*range(150,2250,150)] for ext in ('json','csv')}
    pins={str(p):sha(p) for p in (Path(__file__),PROV,EXEC,ANALYSIS/'summary.json',
        ANALYSIS/'runtime_closure.json',CONFIG,MEM,ROOT/REL/'native_pair1200/run_pair.ps1',
        ROOT/REL/'native_pair1200/analyze_pair.py',ROOT/'tools/sdmpc31/freeze_worktree.ps1')}
    pins.update(physical_pins)
    prefix=[]
    witness={int(r['sim_sec']):r for r in exe['checks']['actual_commands']['decisions']}
    for sec in [1,*range(150,2250,150)]:
        record=dict(sim_sec=sec)
        for suffix in ('json','csv'):
            src=F/f'action_{sec:06d}.{suffix}';dst=dest/src.name;digest=sha(src)
            assert sha(dst)==digest,('Preserve prefix mismatch',dst)
            record[suffix]=dict(source=str(src),destination=str(dst),sha256=digest)
            pins[str(dst)]=digest
            if suffix=='csv':assert witness[sec]['sha256']==digest
        prefix.append(record)
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    verify=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv=[str(verify),'--at','2250','--out',str(OUT),'--tuning',str(CONFIG),
        '--decisions',str(OBS),'--full-selection']
    spec=importlib.util.spec_from_file_location('matched_off2250_bootstrap',verify)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo,sdmpc_sequence as seq,runtime_setup,sdmpc
    import numpy as np
    sdmpc.load_prices=lambda *a,**kw:(np.zeros(2),{'source':'offline_conditional_replay_cold_prices','committed':False})
    from evaluation.controllers import physical_ramp_branches as ramps,signal_actuation_contract as signals
    from evaluation.controllers.control_hold import fixed_vsl_values
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    captured={};configure=runtime_setup.configure_runtime;bound=ramps.configure_operating_bounds;forecast=adapter.demand_from_state
    def runtime(*a,**kw):
        result=configure(*a,**kw);captured.update(mapping=a[3],calibration=a[7],tuning=a[2]);return result
    def bounds(state,cfg,reference):
        result=bound(state,cfg,reference);captured.update(state=state,cfg=cfg);return result
    def demand(*a,**kw):
        result=forecast(*a,**kw);captured['forecast']=result;return result
    runtime_setup.configure_runtime=runtime;ramps.configure_operating_bounds=bounds;adapter.demand_from_state=demand
    checks=[];results=[]
    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        state,cfg=captured['state'],captured['cfg']
        assert state.time_sec==2250 and (cfg.simulation.T_f_sec,cfg.simulation.T_u_sec,cfg.mpc.horizon_steps)==(5,10,3)
        recorded=seq.actions(seq.pack([seq.first_action(adapter.control_from_json(F/f'action_{sec:06d}.json',cfg,ControlAction)) for sec in (2250,2400,2550)]),3)
        segment=adapter.repo_imports(ROOT/'vendor/NumSim-mine')[-1]
        actions={}
        for name,zones in [('hold',{}),('single90',{'FW_E__seg13':90}),('selected',{'FW_E__seg10':90,'FW_E__seg13':90})]:
            blocks=[]
            for i,base in enumerate(recorded):
                sec=2250+150*i;action=copy.deepcopy(base)
                action.vsl=fixed_vsl_values(action.vsl,dict(start_sec=2250,base_kmh=110,zone_kmh=zones),cfg.network.freeway_vsl_zone_heads,sec)
                for field in ('green_times','offsets','ramp_metering','N_P_star','N_UF_star','inflow_outflow_allocation'):
                    assert getattr(action,field)==getattr(base,field),(name,sec,field)
                signals.validate_writer(action,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
                blocks.append(action)
                if name!='selected':continue
                source=F/f'action_{sec:06d}.json';target=dest/source.name
                from evaluation.controllers import offset_promotion
                assert signals.enabled(cfg.network)
                writer_metadata=dict(read(source)['metadata'])
                writer_metadata.update(offset_promotion.action_metadata(action, 'experiment'))
                writer_metadata['physical_signal_contract_enabled']=1.0
                adapter.write_action_csv(target.with_suffix('.csv'),action,cfg,captured['mapping'],segment,
                    writer_metadata,adapter.adapter_actuation_settings(captured['calibration'],captured['tuning']),
                    signal_group_plan_table=adapter.load_signal_group_actuation_plan(),offset_writer='experiment')
                oldrows,newrows=rows(source.with_suffix('.csv')),rows(target.with_suffix('.csv'))
                assert len(oldrows)==len(newrows)
                changed=[]
                for before,after in zip(oldrows,newrows):
                    if before==after:continue
                    assert {k:v for k,v in before.items() if k!='speed_kph'}=={k:v for k,v in after.items() if k!='speed_kph'}
                    assert before['kind']=='vsl' and float(before['speed_kph'])==110 and float(after['speed_kph'])==90
                    changed.append(int(before['dsd_no']))
                assert set(changed).issuperset({63,64,65,66}) and len(changed)==8,changed
                if checks:assert sorted(changed)==checks[0]['changed_dsd']
                metadata=dict(controller_status='ok',controller_variant='wu-link',sim_sec=sec,
                    experiment='Two adjacent East VSL zones90; recorded city/RM and all other VSL fixed',
                    source_action=str(source),source_sha256=sha(source),optimization_performed=False,
                    prediction_status='see matched_off2250 receipts',inherited_diagnostics_are_source_command_evidence=True)
                metadata.update({k:writer_metadata[k] for k in ('offset_writer','offset_experiment','physical_signal_contract_enabled')})
                save(target,adapter.control_to_json_dict(action,metadata))
                with source.with_suffix('.csv').open(encoding='utf-8-sig',newline='') as f: baseline_rows=list(csv.DictReader(f))
                with target.with_suffix('.csv').open(encoding='utf-8-sig',newline='') as f: fixed_rows=list(csv.DictReader(f))
                assert len(baseline_rows)==len(fixed_rows)==213
                assert all(a['metadata']==b['metadata'] for a,b in zip(baseline_rows,fixed_rows)), 'Every metadata token must match the validated native hold'
                for p in (target,target.with_suffix('.csv')):pins[str(p)]=sha(p)
                checks.append(dict(sim_sec=sec,changed_dsd=sorted(changed),canonical_writer=True,city_rm_unchanged=True))
            actions[name]=seq.pack(blocks)
        save(OUT/'writer_metadata_verification.json',dict(status='writer_contract_verified',checks=checks,new_forecasts=0,new_native=0,full_optimizations=0))
        raise verifier.Done()
    # verifier.main wraps the existing solve callback; this replaces only PFO entry.
    sdmpc_pfo.solve=audit
    verifier.main()
    assert len(results)==0 and len(checks)==3
    print('WRITER_REPAIR_READY; native_runs=0; forecasts=0',flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        import traceback
        save(HERE/'native_preparation_failure_v3.json',dict(error=repr(exc),traceback=traceback.format_exc(),native_runs=0))
        raise
