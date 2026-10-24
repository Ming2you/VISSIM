"""One saved-state actual FW5/urban10 control interval, no optimizer/native."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import copy,json,pickle,sys,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
def main():
    output=HERE/('interval_'+sys.argv[1]+'.json');assert not output.exists()
    t0=time.perf_counter();report={'status':'running','full_sdmpc_selections':0,'native_runs':0}
    try:
        req=pickle.loads((HERE.parent/'multirate271/macro_hold_ad_v3_request.pickle').read_bytes())
        cfg=req['owned'][0].cfg;state=req['owned'][1];demand=req['owned'][3][0]
        from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence
        from evaluation.controllers.runtime_setup import install_worker_runtime
        from evaluation.controllers.multirate_coupling import configure,run_interval
        from evaluation.controllers.area_runtime import model_inventory
        install_worker_runtime(adapter,cfg,req['bootstrap']['state_json'],req['bootstrap']['detector_mapping'])
        configure(cfg,{'urban':{'multirate_exchange_sec':10}},state)
        action=sdmpc_sequence.actions(req['action'],3)[0]
        from evaluation.controllers.control_area_objective import ModelAreaLedger
        ledger=ModelAreaLedger(copy.deepcopy(state._control_area_ledger.stocks),capture_response=True,indexed_coverage=True)
        state._control_area_ledger=ledger;before=ledger.ttt_veh_h
        ledger.record_freeway_operands(state,action,initial=True)
        result=run_interval(state,action,demand,cfg)
        ledger.assert_stocks(model_inventory(state,cfg))
        response=ledger.response()
        report.update(status='complete',physical_end_sec=state.lane_freeway_runtime.time_sec,
            omega_ttt=ledger.ttt_veh_h-before,response_keys=list(response),coverage=response['model_constraint_coverage'],
            freeway_frames=len(response['freeway_frames']),residence_samples=len(response['residence']),
            diagnostics=result.diagnostics,pending=dict(state.multirate_exchange_pending))
        (HERE/('interval_'+sys.argv[1]+'.pickle')).write_bytes(pickle.dumps(state,protocol=5))
    except Exception as e:
        report.update(status='failed_preserved',error=repr(e),traceback=traceback.format_exc())
    report['wall_sec']=time.perf_counter()-t0
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('diagnostics','pending')},ensure_ascii=False))
    return 0 if report['status']=='complete' else 1
if __name__=='__main__':raise SystemExit(main())
