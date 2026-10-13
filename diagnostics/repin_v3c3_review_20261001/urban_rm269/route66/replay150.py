"""One canonical actual-command first150 replay with complete66 footprint."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import argparse,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['baseline','candidate'],required=True)
args=ap.parse_args()
OUT=HERE/f'replay2400_{args.arm}'
assert not OUT.exists(), 'Do not overwrite or automatically retry a replay'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
tuning=HERE/'config.json' if args.arm=='candidate' else HERE.parent/'config_candidate.json'
sys.argv=['verify.py','--at','2400','--out',str(OUT),'--recorded-first-step',
          '--tuning',str(tuning),'--decisions','D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29']
loader=importlib.util.spec_from_file_location('canonical_verifier',HERE.parent.parent/'urban260/verify.py')
v=importlib.util.module_from_spec(loader);loader.loader.exec_module(v)
from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo
from src.controllers import rollout_endpoint as endpoint
original_main=adapter.main
def main():
    audit=sdmpc_pfo.solve
    def captured(*a,**kw):
        evaluate=endpoint.evaluate_price_point
        count=0
        def trace(state,action,forecast,owners,spec,*extra,**kwargs):
            nonlocal count
            count+=1
            assert count==1 and len(forecast)==1 and spec.depth_override==1
            origin='in_SC1004_S'
            moves=[m for m,s in spec.cfg.network.urban_movements.items() if s['origin']==origin]
            keys={'storage:'+origin,'transit:gate:'+origin,*('movement:'+m for m in moves)}
            def inventory(s):
                return dict(storage=spec.cfg.network.urban_link_storage_veh[origin]-s.urban_link_storage[origin],
                            queue={m:s.urban_movement_queue[m] for m in moves},
                            gate_transit=sum(s.urban_inflow_transit_buffer.get('gate:'+origin,{}).values()))
            before=inventory(state)
            p=evaluate(state,action,forecast,owners,spec,*extra,**kwargs)
            assert not p.aborted and len(p.states)==1
            after=inventory(p.states[-1]);response=p.control_area_response
            transfers=[t for t in response['transfers'] if t['source'] in keys or t['target'] in keys]
            total=lambda d:d['storage']+d['gate_transit']+sum(d['queue'].values())
            balance=total(after)-total(before)-sum(t['vehicles']*((t['target'] in keys)-(t['source'] in keys)) for t in transfers)
            assert abs(balance)<1e-7,balance
            flows={m:sum(t['vehicles'] for t in transfers if t['source']=='movement:'+m and t['target'] not in keys) for m in moves}
            result=dict(arm=args.arm,start_sec=2400,end_sec=2550,initial=before,final=after,
                end_approach_veh=total(after),local_balance_error_veh=balance,
                predicted_departures=flows,omega_ttt_veh_h=p.ttt,transfers=transfers,
                native_execution=False,optimizer=False,future_observation_used_as_input=False,
                scope='Same recorded first150 command under discrete physical model. Composition/input check, not causal RM/VSL comparison. Resource checks remain canonical.')
            (OUT/'link66.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            return p
        endpoint.evaluate_price_point=trace
        try:return audit(*a,**kw)
        finally:endpoint.evaluate_price_point=evaluate
    sdmpc_pfo.solve=captured
    return original_main()
adapter.main=main
v.main()
