"""One fresh full Jacobian and independent continuous scalar anchor.

The two workers use the identical initialized state/action/config. This checks
owner costs, resources and all exported central state values, not native truth
or equality of every intermediate scalar/AD state. No optimization/native run.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import hashlib,importlib.util,json,pickle,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
OUT=HERE/'ad2400'
F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def main():
    import ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not OUT.exists(),'No duplicate diagnostic'
    for path,digest in read(HERE/'plan.json')['source_pins'].items():assert sha(Path(path))==digest,path
    for at in (2400,3300):assert read(HERE/f'forecast{at}/completion.json')['status']=='complete'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
    sys.argv=['verify.py','--at','2400','--out',str(OUT),'--no-prediction','--tuning',str(HERE/'config.json'),'--decisions',str(F)]
    spec=importlib.util.spec_from_file_location('canonical_ad_verifier',H.parent/'urban260/verify.py')
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo
    from evaluation.controllers import sdmpc_sequence as seq,signal_actuation_contract as signals
    from evaluation.controllers.sdmpc_tangent_surrogate import Query
    import numpy as np
    original_main=adapter.main
    def wrapped_main():
        def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
            query=derivative.__self__
            assert isinstance(query,Query) and query.stats()['total_rollouts']==0
            request=pickle.loads(query.template)
            cfg=request['owned'][0].cfg
            assert request['horizon']==3 and cfg.simulation.T_c_sec==150
            assert cfg.network.regular_alias_pool['group']=='1220006903:10025:p1'
            for block in seq.actions(reference,3):
                signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
            coord.validate(reference)
            save('source_pins.json',dict(read(HERE/'plan.json')['source_pins'],**{str(Path(__file__)):sha(Path(__file__))}))
            receipts=[];runner=query.runner
            def record(req):
                assert len(receipts)<2 and req['surrogate_evaluation']==('scalar' if not receipts else 'ad')
                result=runner(req)
                (OUT/(req['surrogate_evaluation']+'.pickle')).write_bytes(pickle.dumps(result,protocol=5))
                receipts.append(result)
                print('worker_done',req['surrogate_evaluation'],result['wall_sec_including_spawn'],flush=True)
                return result
            query.runner=record
            started=time.perf_counter()
            scalar=evaluate([reference],derivatives=False)[0]
            ad=derivative(reference)
            assert len(receipts)==2 and len(ad['ad_axes'])==len(coord.axes) and not ad['fallback_reasons']
            assert receipts[0]['scalar_rollouts']==1 and ad['tangent_rollouts']==1
            predicted=evaluate([reference],derivatives=False)[0]
            assert len(receipts)==2,'Cached AD response must not launch again'
            differences={}
            for key in ('costs','resources'):
                lhs=np.asarray(receipts[0][key]);rhs=np.asarray(ad[key])
                assert lhs.shape==rhs.shape and np.isfinite(lhs).all() and np.isfinite(rhs).all()
                differences[key]=float(np.max(abs(lhs-rhs),initial=0))
                assert differences[key]<=1e-7,(key,differences[key])
            a,b=scalar['central_physical'],ad['central_physical']
            assert a['names']==b['names']
            differences['central_state_values']=float(np.max(abs(np.asarray(a['values'])-np.asarray(b['values'])),initial=0))
            assert differences['central_state_values']<=1e-7
            for key,rows in [('cost_jacobian',len(ad['costs'])),('resource_jacobian',len(ad['resources']))]:
                matrix=np.asarray(ad[key]);assert matrix.shape==(rows,len(coord.axes)) and np.isfinite(matrix).all()
            central=np.asarray(b['jacobian'])
            assert central.shape==(len(b['names']),len(coord.axes)) and np.isfinite(central).all()
            for item in (scalar,predicted):
                assert item['model_constraint_coverage']['complete'] and item['conditional_model_feasibility_witness']
                assert item['resource_summary']['max_exceedance_veh']<1e-7
                assert abs(sum(item['sdmpc_omega_partition']['costs'].values())-item['objective_veh_h'])<1e-7
            verification=dict(status='passed',axes=len(coord.axes),owners=len(ad['costs']),
                central_states=len(b['names']),max_scalar_ad_difference=differences,
                omega_ttt_veh_h=predicted['objective_veh_h'],owner_costs=predicted['sdmpc_omega_partition']['costs'],
                worker_seconds=[r['wall_sec_including_spawn'] for r in receipts],wall_sec=time.perf_counter()-started,
                query_stats=query.stats(),fallback_reasons=ad['fallback_reasons'],writer_three_blocks=True,
                unchanged_horizon_sec=450,full_sdmpc_selection=False,new_native=0,
                scope='One fresh213-or-current-axis continuous AD and separate scalar worker; all exported central states/costs/resources agree. Intermediate trajectories are not compared; native gain and optimal selection remain unqualified.')
            save('verification.json',verification)
            print('AD_VERIFIED',verification['axes'],differences,flush=True)
            raise v.Done()
        sdmpc_pfo.solve=audit
        return original_main()
    adapter.main=wrapped_main
    v.main()

if __name__=='__main__':main()
