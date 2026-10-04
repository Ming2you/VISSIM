"""Prepare only the four previously evaluated native command sequences."""
import copy
import csv
import ctypes
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

O=Path(__file__).resolve().parent
I=O.parent
U=I.parents[2]
D=Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
P=I/'expanded036_9000_20260930/loss_onset2250/onset_factorial'
pred_path=Path(json.loads((P/'output.json').read_bytes())['output'])/'summary.json'
pred=json.loads(pred_path.read_bytes())
verified=json.loads((P/'verification.json').read_bytes())
assert verified['all_tested_caps_pass'] and verified['baseline_matches_saved_corrected_baseline_exact']
assert set(pred['results'])=={'held_actual','rm_only','vsl_release','both'}
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
from evaluation.controllers import obs150_contract as oc


def readonly(raw,derived):
    obs=raw[oc.RAW_STATE_KEY]
    p=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
    assert p.read_bytes()==oc.derived_bytes(derived)
    return p


oc.write_derived=readonly
helper=I/'probe_selected_arrival_path.py'
spec=importlib.util.spec_from_file_location('native_onset_prepare',helper)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
pins={str(p):sha(p) for p in (Path(__file__),helper,pred_path,P/'verification.json')}


def physical_rows(p):
    return [{k:v for k,v in r.items() if k!='metadata'} for r in csv.DictReader(
        p.read_text(encoding='utf-8-sig').splitlines())]


def prepare(captured,reference,output,**kwargs):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import physical_ramp_branches as branches,sdmpc_sequence as sequence
    cfg=captured['cfg'];assert captured['state'].time_sec==2250
    reference=sequence.first_action(reference)
    metadata=read(D/'action_002250.json')['metadata']
    actuation=adapter.adapter_actuation_settings(captured['calibration'],captured['tuning'])
    segment=adapter.repo_imports(U/'vendor/NumSim-mine')[-1]
    plan=adapter.load_signal_group_actuation_plan()
    written={}
    for arm,result in pred['results'].items():
        dest=O/arm/'commands';dest.mkdir(parents=True,exist_ok=False)
        for sec in (1,*range(150,2250,150)):
            for suffix in ('.json','.csv'):
                src=D/f'action_{sec:06d}{suffix}'
                pins[str(src)]=sha(src);shutil.copy2(src,dest/src.name)
                assert sha(dest/src.name)==sha(src)
            if sec>=900:assert (D/f'action_{sec:06d}.json.applied').is_file()
        previous=reference
        written[arm]=[]
        for block,sec in enumerate((2250,2400,2550,2700)):
            wanted=result['commands'][min(block,2)]
            current=branches.candidate_from_greens(previous,previous,cfg,wanted['meters'])
            current.vsl=copy.deepcopy(wanted['vsl'])
            current.green_times=copy.deepcopy(wanted['green_times'])
            current.offsets=copy.deepcopy(wanted['offsets'])
            assert current.green_times==reference.green_times and current.offsets==reference.offsets
            assert all(current.diagnostics['rw_meter_green_'+r]==v for r,v in wanted['meters'].items())
            meta=copy.deepcopy(metadata);meta['sim_sec']=sec
            stem=dest/f'action_{sec:06d}'
            adapter.write_action_csv(stem.with_suffix('.csv'),current,cfg,captured['mapping'],segment,
                meta,actuation,signal_group_plan_table=plan,offset_writer='experiment')
            stem.with_suffix('.json').write_text(json.dumps(adapter.control_to_json_dict(current,meta),ensure_ascii=False),encoding='utf8')
            actual=physical_rows(stem.with_suffix('.csv'))
            assert {r['kind'] for r in actual}=={'vsl','ramp_meter','signal','signal_sg'}
            if arm=='held_actual':assert actual==physical_rows(D/'action_002250.csv')
            else:
                base=physical_rows(O/'held_actual/commands'/f'action_{sec:06d}.csv')
                assert len(base)==len(actual)
                changed=[]
                for a,b in zip(actual,base):
                    if a!=b:
                        assert a['kind']==b['kind'] and a['id']==b['id']
                        assert (a['kind']=='ramp_meter' and a['id']=='RM_C10484') or (a['kind']=='vsl' and a['id']=='RW_FW_E_S13')
                        changed.append(a['id'])
                assert set(changed)==({'RM_C10484'} if arm=='rm_only' else {'RW_FW_E_S13'} if arm=='vsl_release' else {'RM_C10484','RW_FW_E_S13'})
            written[arm].append(dict(sec=sec,rows=len(actual),sha256=sha(stem.with_suffix('.csv'))))
            previous=current
        pins.update({str(p):sha(p) for p in dest.iterdir()})
    network=I/'selected/network/native_seed29.inpx'
    assert sha(network)=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    protocol=dict(start_sec=2250,end_sec=2700,seed=29,arms=list(pred['results']),
        control_start_sec=900,controller='wu-link',native_factorial=True,
        network=str(network),network_sha256=sha(network),command_pins=pins,
        original_run=str(D.parent),prediction_source=str(pred_path),prediction_sha256=sha(pred_path),
        predicted_delta_by_arm={k:dict(omega=v.get('delta_ttt_omega_veh_h',0.),
            with_tracked_outside=v.get('delta_with_tracked_outside_veh_h',0.)) for k,v in pred['results'].items()},
        native_authorization_pending=False,native_authorization='User2026-09-29: necessary VISSIM may proceed without repeated permission',
        prior_stop=str(stop),prior_stop_sha256=sha(stop),scope='Four fixed-city2250-2700 counterfactuals after exact original SDMPC prefix; RM10484 g8/6/4 and VSL13 90->110 only; not closed-loop9000.',
        sim_resolution=10,vehicle_record_interval_sec=5,observation_interval_sec=150,
        physical_command_check=written,optimizer_calls=0,forecast_rollouts=0,
        prefix_required_before_qualification=True,future_observation_inputs=False,
        max_native_runs=4,automatic_retries=0)
    (O/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,arms=protocol['arms'],end_sec=2700,new_rollouts=0)))


module.probe_levers=prepare
sys.argv=[str(helper),'--closedloop-recorded','--at=2250','--lever-probe450','--meter-ramp=RM_C10484',
    '--warm-head-history','--replay-vsl-history','--recording-dir='+str(D),
    '--tuning-json='+str(I/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'),
    '--probe-label=onsetnativeprep']
module.main()
