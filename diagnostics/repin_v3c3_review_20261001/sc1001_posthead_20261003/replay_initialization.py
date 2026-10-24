"""Replay one actual adapter initialization, stopping before any optimizer."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

D=Path(__file__).resolve().parent
ROOT=D.parents[2]
REC=Path('D:/VISSIM_runs/20261002_service66_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
class Finished(Exception): pass
def main():
    sec=int(sys.argv[1]);label=sys.argv[2]
    out=D/(label+str(sec)+'.json');assert not out.exists()
    from evaluation.controllers import runtime_setup,obs150_contract as oc
    from evaluation.controllers import lane_offramp_runtime as off
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    original=runtime_setup.configure_runtime
    shared=off.initialize_shared_approach
    receipt={}
    def snapshot(state,cfg):
        return dict(queue=dict(state.urban_movement_queue),
            storage={k:cfg.network.urban_link_storage_veh[k]-v for k,v in state.urban_link_storage.items()},
            arrival=state.urban_arrival_buffer,release=state.urban_storage_release_buffer,
            gate_tags=state.gate_initial_route_tags,
            projection=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'])
    def intercept(*args,**kwargs):
        cfg,state=args[2:4]
        receipt['before']=json.loads(json.dumps(snapshot(state,cfg)))
        receipt['movement_specs']={k:v for k,v in cfg.network.urban_movements.items() if k.startswith('SC1001_W_to_')}
        metadata=shared(*args,**kwargs)
        receipt['after']=snapshot(state,cfg);receipt['shared_metadata']=metadata
        receipt['shared_stock']=state.sc1001_approach.stock()
        return metadata
    off.initialize_shared_approach=intercept
    def capture(*args,**kwargs):
        result=original(*args,**kwargs)
        receipt['initialization_complete']=True
        receipt['runtime_metadata']=result[2]
        raise Finished()
    runtime_setup.configure_runtime=capture
    def existing(raw,derived):
        obs=raw[oc.RAW_STATE_KEY];p=oc.resolve(obs,oc.derived_path(obs['sim_sec']))
        assert p.read_bytes()==oc.derived_bytes(derived)
        return p
    oc.write_derived=existing
    for k,v in dict(RW_DECISION_FAIL_FAST='1',RW_MAINLINE_SG_ONLY='1',RW_OFFSET_WRITER='experiment',RW_RAMP_AMBER_SEC='0').items():os.environ[k]=v
    paths=[REC/f'state_{sec:06d}.json',REC/f'action_{sec-150:06d}.json',D.parent/'rm47_service66_response/candidate_config.json']
    receipt['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    receipt['source_sha256']=hashlib.sha256(Path(off.__file__).read_bytes()).hexdigest()
    sys.argv=[str(Path(adapter.__file__)),'--state-json',str(paths[0]),'--previous-action-json',str(paths[1]),
        '--out-action-json',str(D/(label+str(sec)+'.unused.json')),'--out-action-csv',str(D/(label+str(sec)+'.unused.csv')),
        '--mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
        '--detector-mapping-json',str(ROOT/'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'),
        '--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
        '--tuning-json',str(paths[2]),'--controller','wu-link']
    try:adapter.main()
    except Finished:receipt['status']='initialized_no_optimizer'
    except Exception:
        receipt['status']='failed';receipt['error']=traceback.format_exc()
    finally:
        off.initialize_shared_approach=shared;runtime_setup.configure_runtime=original
        out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],time=sec,error=receipt.get('error','').splitlines()[-1:]),ensure_ascii=False))
    if receipt['status']=='failed':raise SystemExit(1)

if __name__=='__main__':main()
