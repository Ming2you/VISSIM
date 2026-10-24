"""Free the head-storage feedback in the prior frozen-receiving screen."""
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
R = ROOT/'diagnostics/repin_v3c3_review_20261001'
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'


def main():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    protocol=json.loads((HERE/'protocol.json').read_bytes())
    prior=json.loads((HERE.parent/'receiving227/protocol.json').read_bytes())
    data=(HERE.parent/'receiving227/assessment.json').read_bytes()
    assert hashlib.sha256(data).hexdigest()==prior['assessment_sha256']
    previous=json.loads(data)
    base=json.loads((HERE.parent/'receiving226/assessment.json').read_bytes())
    helper=R/'ramp10681_receiving/assess.py'
    spec=importlib.util.spec_from_file_location('receiving_existing',helper)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    out=dict(status='COMPLETE_CONDITIONAL_RAMP_FEEDBACK_SCREEN',full_forecasts=0,new_native=0,FZP=0,fit=0,optimizer=0,
        helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),arms={},input_sha256=mod.PINS,
        source_sha256=previous['source_sha256'],receiving227_sha256=prior['assessment_sha256'],
        limitations=['Full local ramp storage/head/merge conservation; mainline receiving and upstream city transfers are frozen.',
                     'Native future arrivals are conditional diagnosis only. Not whole-network gain, calibration, or selected policy validation.',
                     'The native pair changes city green/offset; all8RM/VSL commands match.'])
    for case in ('held_actual','selected'):
        path=I/'closedloop_recorded2700_select_check_trace10681_rm225_candidate52_response'/f'{case}_RM_C10681_trace.json.gz'
        trace=mod.read(path)
        assert mod.PINS[str(path)]==previous['input_sha256'][str(path)]
        observed=base['arms'][case]['observed']
        budgets={r['time_sec']:r['candidate_by_lane'] for r in previous['arms'][case]['frozen_budget_rows']}
        original=mod.replay(trace,observed,'baseline')
        assert original==base['arms'][case]['local']['baseline']
        changed=mod.replay(trace,observed,'baseline',receiving_by_second=budgets)
        conditional=mod.replay(trace,observed,'native_arrival_timing_and_lane',receiving_by_second=budgets)
        out['arms'][case]=dict(actual=previous['arms'][case]['native_actual'], original=original,
            connected_model_arrivals=changed,connected_native_arrivals=conditional)
    for relative,digest in out['source_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
    out['local_ramp_replays']=6
    assert out['local_ramp_replays']<=protocol['max_local_ramp_replays']
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({case:{mode:{k:v[k] for k in ('head','merge','final_stock')} for mode,v in row.items()} for case,row in out['arms'].items()}))


if __name__=='__main__':main()
