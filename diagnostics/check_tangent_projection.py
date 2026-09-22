"""Dry-run continuous QP -> legal actuator projection. No native application."""
from pathlib import Path
import hashlib,json,pickle,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers import sdmpc,sdmpc_dual as ad
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import area_follower_objective as joint
    from evaluation.controllers.runtime_setup import install_worker_runtime
    source=ROOT/'diagnostics/tangent_900_h1'
    request=pickle.loads((source/'request.pickle').read_bytes())
    saved=pickle.loads((source/'prediction_attempt05.pickle').read_bytes())
    follower,state,reference,forecast=request['owned']
    cfg=follower.cfg; bootstrap=request['bootstrap']
    install_worker_runtime(adapter,cfg,bootstrap['state_json'],bootstrap['detector_mapping'])
    for k,v in request['runtime'].items():setattr(adapter,k,v)
    adapter._PHASE_VECTOR_FOLLOWER['ref']=follower
    tuning=json.loads((source/'config.json').read_text())
    options=adapter.joint_owner_game_settings(tuning,cfg,'wu-link')
    mapping=adapter.load_optional_json(str(ROOT/tuning['mapping_json']))
    with joint.shared_query_runtime_scope():
        callbacks,context,_=joint._joint_runtime_callbacks(follower,state,forecast,reference,reference,
            mapping,bootstrap['runtime_sources'],reference=reference,total_budget=None,directional={},
            tolerance=options['nuf_tolerance_veh_h'],price_probe=False)
        coord=sdmpc.Coordinates(cfg,reference,callbacks['move_box'],dict(cfg.network.sdmpc_options))
        gradient=np.array([sum(ad.derivative(v).get(j,0.) for v in saved['dual_costs'])
                           for j in range(len(coord.axes))])
        started=time.perf_counter()
        step,receipt=sdmpc.solve_qp(np.zeros(len(gradient)),gradient,cfg.network.sdmpc_options['proximal'],
            coord.lower,coord.upper,coord.G,coord.glo,coord.ghi,cfg.network.sdmpc_options)
        qp_sec=time.perf_counter()-started
        if not receipt['success']:raise ValueError(receipt)
        projected=coord.decode(step,reference)
        proof=callbacks['command_evidence'](projected,context)
        changed={kind:int(sum(abs(coord.encode(projected)[j])>1e-9 for j,a in enumerate(coord.axes) if a['kind']==kind))
                 for kind in ('green','offset','meter','vsl')}
        report=dict(native_command_applied=False,qp=receipt,qp_sec=qp_sec,
            changed_coordinates=changed,actuator_move_box_and_native_phase_constraints_passed=True,
            nonlinear_resource_constraints_checked=False,command_evidence=proof,
            continuous_step=step.tolist(),projected_step=coord.encode(projected).tolist())
        from diagnostics.sdmpc_qualification_report_v4 import atomic_json
        atomic_json(source/'projection_check.json',report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('continuous_step','projected_step','command_evidence')},indent=2))


if __name__=='__main__':main()
