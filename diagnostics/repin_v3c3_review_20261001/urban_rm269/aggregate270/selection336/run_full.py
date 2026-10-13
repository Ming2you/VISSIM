"""One canonical SDMPC3300 choice with fixed331 model and qualified workers."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,os,pickle,sys,time,traceback

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent;ROOT=HERE.parents[4]
BASE=A/'transfer331/build3300_v2';OUT=HERE/'full3300'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,data):
    (HERE/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')


def main():
    assert not OUT.exists() and not (HERE/'execution.json').exists(),'Keep prior attempt'
    assert not any((p/'STOP').exists() for p in (ROOT,H,A,HERE))
    assert read(HERE/'binding_check.json')['status']=='passed'
    proof=read(BASE/'summary.json');pins=dict(proof['source_pins'])
    for p in (*HERE.glob('*.py'),BASE/'initial.pickle',BASE/'canonical.pickle',BASE/'summary.json',
              H.parent/'urban260/verify.py',A/'worker334/capture_v2/summary.json'):
        pins[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in pins.items())
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    sys.argv=['verify.py','--at','3300','--out',str(OUT),'--full-selection',
              '--tuning',str(A/'flow279/config_10686_free.json'),'--decisions',proof['source']]
    spec=importlib.util.spec_from_file_location('selection336_verifier',H.parent/'urban260/verify.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    from evaluation import parameters
    policy=parameters.load()
    assert policy['sdmpc']['max_iterations']==policy['sdmpc_pfo_cap']['max_iterations']==2
    from evaluation.controllers import sdmpc,sdmpc_sequence as seq,physical_ramp_branches as ramps
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers.sdmpc_tangent_surrogate import Query
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.selection336.binding import refresh
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.selection336.worker_runner import evaluate
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled as branch
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import enabled as transport
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325.candidate import enabled as north
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329.candidate import enabled as routes
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook
    original_solve=sdmpc.solve;query_init=Query.__init__;original_audit=sdmpc.audit_meter_neighbors
    restored={};audits=[]
    def solve(controller,state,forecast,historical,*args,**kw):
        assert not restored,'One entire decision only'
        cfg=controller.cfg;follower=controller.nash_solver
        assert follower.cfg is cfg and controller.leader.cfg is cfg and follower._wu.cfg is cfg
        canonical,canonical_state,canonical_forecast=pickle.loads((BASE/'canonical.pickle').read_bytes())
        trial=copy.deepcopy(cfg)
        previous=seq.first_action(historical) if seq.KEY in historical.diagnostics else historical
        reference=meters.prepare_held_actual_reference(previous,trial)
        ramps.configure_operating_bounds(state,trial,reference)
        parity=dict(cfg=equal(trial,canonical),state=equal(state,canonical_state),forecast=equal(forecast,canonical_forecast))
        save('bootstrap_parity.json',parity);assert all(parity.values()),parity
        latest,new_state,new_forecast=pickle.loads((BASE/'initial.pickle').read_bytes())
        assert all(equal(v,getattr(latest,k)) for k,v in vars(cfg).items() if k!='network')
        changed=[k for k in vars(latest.network) if not equal(getattr(cfg.network,k,None),getattr(latest.network,k))]
        assert set(vars(cfg.network))<=set(vars(latest.network))
        for k in changed:setattr(cfg.network,k,copy.deepcopy(getattr(latest.network,k)))
        assert equal(cfg,latest)
        state.__dict__.clear();state.__dict__.update(copy.deepcopy(vars(new_state)))
        assert equal(state,new_state) and equal(forecast,new_forecast)
        binding=refresh(follower,cfg)
        restored.update(cfg=cfg,state=copy.deepcopy(state),changed_fields=changed)
        save('model_binding.json',dict(network_fields=changed,binding=binding,
            same_controller_leader_follower_cfg=True,initial_state_exact=True,
            phase='Before deepcopy, coupling, move boxes, PFO and all objective requests'))
        return original_solve(controller,state,forecast,historical,*args,**kw)
    sdmpc.solve=solve
    def init(self,template,check_budget,emit,runner=None):
        assert restored and runner is None
        f,s,ref,fc=template['owned']
        assert equal(s,restored['state'])
        assert equal(f.cfg,restored['cfg'])
        assert equal(f._specs,f.cfg.network.urban_movements)
        assert len(template['axes'])==213 and template['horizon']==3
        assert f.cfg.simulation.T_f_sec==5 and f.cfg.simulation.T_u_sec==10
        assert f.cfg.network.sdmpc_options['meter_neighbor_audit']
        save('query_binding.json',dict(latest_state=True,latest_cfg=True,latest_static_specs=True,
            axes=213,horizon=450,FW_sec=5,urban_sec=10,meter_neighbor_audit=True,
            previous_path='Actual3150 price history; no cold-price override'))
        return query_init(self,template,check_budget,emit,runner=evaluate)
    Query.__init__=init
    def audit(coord,best,tolerance,evaluate,feasible):
        seen=[]
        def observe(actions,**kw):
            items=evaluate(actions,**kw)
            for a,item in zip(actions,items):
                seen.append(dict(action_token=sdmpc.token(a),np_cap=a.N_P_star,nuf_cap=a.N_UF_star,
                    rm10681=[ramps.physical_commands(b,coord.cfg).get('RM_C10681') for b in seq.actions(a,3)],
                    objective=item['objective_veh_h'],quantities=item['quantities'],
                    owner_costs=item['sdmpc_omega_partition']['costs'],feasible=feasible(a,item)))
            return items
        result,receipt=original_audit(coord,best,tolerance,observe,feasible)
        audits.append(dict(receipt=receipt,evaluations=seen))
        save('finite_rm_audits.json',audits)
        return result,receipt
    sdmpc.audit_meter_neighbors=audit
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        full_decisions=1,automatic_retries=0,native_runs=0,source_pins=pins,
        max_outer_iterations=2,max_restoration_iterations=2,worker_limit=8)
    save('execution.json',record);started=time.perf_counter()
    try:
        with branch(),transport(),north(),routes(),hook('source_path_current_physical_speed'):
            verifier.main()
        assert read(OUT/'completion.json')['full_selection']
        assert restored and audits,'Actual finite RM audit must execute'
        assert all(sha(p)==h for p,h in pins.items())
        record['status']='complete_pending_review'
    except BaseException:
        record.update(status='failed_preserved',error=traceback.format_exc());raise
    finally:
        record.update(wall_sec=time.perf_counter()-started,ended_utc=datetime.now(timezone.utc).isoformat())
        save('execution.json',record)
    print('FULL336_DONE',record['wall_sec'],flush=True)


if __name__=='__main__':main()
