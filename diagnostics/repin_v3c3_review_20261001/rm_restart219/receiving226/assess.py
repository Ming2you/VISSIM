"""Current RM response decomposition from saved receipts, no full forecast."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
R=ROOT/'diagnostics/repin_v3c3_review_20261001'
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'

def main():
    old=R/'ramp10681_receiving/assess.py'
    spec=importlib.util.spec_from_file_location('existing_receiving_audit',old)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    protocol=json.loads((HERE.parent/'link52_225/protocol.json').read_bytes())
    for path,digest in protocol['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    assert hashlib.sha256(Path(protocol['STOP']['path']).read_bytes()).hexdigest()==protocol['STOP']['sha256']
    audit=mod.read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    folder=I/'closedloop_recorded2700_select_check_trace10681_rm225_candidate52_response'
    out=dict(status='CONDITIONAL_COMPONENT_DIAGNOSIS_NOT_GAIN_QUALIFICATION',
        previous_goal_turn='PROGRESS',full_forecasts=0,local_component_replays=10,
        new_native=0,FZP=0,fit=0,optimizer=0,
        input_sha256=mod.PINS,source_sha256=protocol['source_sha256'],arms={},
        limitations=['Future native arrivals/head passages are used only in explicitly conditional component diagnostics.',
                    'Mainline receiving budgets are frozen from the prior autonomous forecast; no closed-loop feedback or whole-network TTT is inferred.',
                    'Native ramp entry detector is at1m; events are binned at1s. Lane-specific merge is not identified separately from lateral movement.',
                    'This reuses the existing diagnostic functions on the current225 model; the earlier October2 diagnosis used a different model.',
                    'Existing52/head/10565 supply findings are reused, not claimed as new fixes.'])
    for case,arm in [('held_actual','hold'),('selected','selected')]:
        trace=mod.read(folder/(case+'_RM_C10681_trace.json.gz'))
        observed=mod.native(arm,audit,trace['initial_buffer']['head_position_m'])
        local={mode:mod.replay(trace,observed,mode) for mode in
               ['baseline','native_arrival_timing','native_arrival_timing_and_lane']}
        post={mode:mod.posthead_replay(trace,observed,mode) for mode in ['model_head','native_head']}
        actual=audit['arms'][arm]['RM_C10681']['actual']
        assert abs(local['baseline']['merge']-post['model_head']['merge'])<1e-8
        out['arms'][case]=dict(actual=actual,observed=observed,local=local,posthead=post)
    out['merge_response_selected_minus_held']={
        **{mode:out['arms']['selected']['local'][mode]['merge']-out['arms']['held_actual']['local'][mode]['merge'] for mode in out['arms']['held_actual']['local']},
        'native_head':out['arms']['selected']['posthead']['native_head']['merge']-out['arms']['held_actual']['posthead']['native_head']['merge'],
        'native_actual':out['arms']['selected']['actual']['merge']-out['arms']['held_actual']['actual']['merge']}
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=out['status'],response=out['merge_response_selected_minus_held'],arms={
        a:dict(actual={k:v['actual'][k] for k in ['arrival','head','merge','final_stock']},
            local={m:{k:r[k] for k in ['head','merge','final_stock','upstream_backlog']} for m,r in v['local'].items()},
            native_head=v['posthead']['native_head']) for a,v in out['arms'].items()})))

if __name__=='__main__':main()
