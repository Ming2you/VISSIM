
"""One canonical saved900 regional selection, gated by input qualification."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
os.environ.update(RW_OFFSET_WRITER='experiment',RW_MAINLINE_SG_ONLY='1',RW_RAMP_AMBER_SEC='0')
import argparse,json,time,hashlib,subprocess,pickle
from pathlib import Path
from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc
from diagnostics.solo355_local_20261013.regional_context_probe import load
from src.models.state import ControlAction,segment_vsl

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False)
    gate=Path('D:/VISSIM_analysis/20261013_solo355_local/task5/input_gate.json')
    assert json.loads(gate.read_text())['passed'] is True
    capture=Path('D:/VISSIM_analysis/20261013_solo355_local/projected.pkl')
    x=load(a.mode,capture);c,s,f,h,m=x['args'];raw=x['obs']['merged'];cfg=c.cfg
    tuning_path=Path('diagnostics/solo355_local_20261013/'+a.mode+'_config.json')
    tuning=json.loads(tuning_path.read_text(encoding='utf-8'))
    adapter.install_config_switches(tuning)
    previous_path=Path(x['kwargs']['previous_path'])
    previous=adapter.control_from_json(previous_path,cfg,ControlAction)
    s._regional_boundary_observation=raw['obs150_derived']
    root=Path.cwd()
    provenance=adapter.build_run_provenance(root/'vendor/NumSim-mine',raw,
        previous_path.with_name('state_000900.json'),root/tuning['mapping_json'],root/tuning['detector_mapping_json'],
        root/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json',
        root/tuning_path,network_path=Path(raw['network_path']))
    options=adapter.joint_owner_game_settings(tuning,cfg,'wu-link')
    protocol=dict(mode=a.mode,stage='canonical_saved900_full_selection',native_runs=0,
        capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(),
        gate_sha256=hashlib.sha256(gate.read_bytes()).hexdigest(),
        source_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        started_epoch=time.time(),pid=os.getpid(),policy=cfg.network.sdmpc_options,options=options)
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    print(json.dumps({'stage':'start','pid':os.getpid(),'mode':a.mode,'output':str(out)}),flush=True)
    start=time.perf_counter()
    result,response,report=adapter.run_joint_owner_decision(c,s,f,previous,cfg,m,tuning,provenance,
        previous_path,options,out/'joint.json',segment_vsl_func=segment_vsl,
        worker_state_json=raw,worker_detector_mapping=x['kwargs']['worker_bootstrap']['detector_mapping'])
    assert report['completed'] and response['feasible']
    metadata=dict(controller_variant='wu-link',controller_status='ok',sdmpc_active=True,
        sdmpc_state=report['selection']['price_state'],sim_sec=900.,run_provenance=provenance)
    action=out/'action.json'
    action.write_text(json.dumps(adapter.control_to_json_dict(result.control,metadata),default=str),encoding='utf-8')
    written=adapter.write_action_csv(out/'action.csv',result.control,cfg,m,segment_vsl,metadata,
        cfg.network.control_area_meter_context['actuation'],
        signal_group_plan_table=adapter.load_signal_group_actuation_plan(),offset_writer='experiment',
        joint_response=response,joint_json_path=action)
    blocks=response['command_evidence']['regional_prediction_blocks']
    assert len(blocks)==3 and all(b['ordered_row_count']>0 for b in blocks)
    record=dict(completed=True,feasible=True,mode=a.mode,native_runs=0,elapsed_sec=time.perf_counter()-start,
        canonical_adapter=True,canonical_writer=written,all_three_blocks=blocks,
        response=response,selection=report['selection'],source_sha256=report['source_sha256'])
    (out/'selection.json').write_text(json.dumps(adapter._json_evidence(record),indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('completed','feasible','mode','elapsed_sec')}),flush=True)

if __name__=='__main__':main()
