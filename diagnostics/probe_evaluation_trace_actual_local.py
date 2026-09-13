"""One original SC1004 local phase cost per mode; no endpoint/MPC/VISSIM.

An explicit diagnostic wrapper is the only extra selected root. It does not
claim that this direct local-cost invocation is a complete follower solve.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import pickle
import time
from unittest.mock import patch

from diagnostics.test_head_service_resources import configured,read,CONFIG,CONTRACT,input_path,ROOT,adapter
from diagnostics.test_shared_service_main_stack import local_result
from diagnostics import evaluation_trace as base
from diagnostics.evaluation_trace_monitor import install
from diagnostics.evaluation_trace_local import collection


def actual_local_probe(self,state,demand,previous):
    return local_result(self,state,previous,demand)


def selector(code):
    if code is actual_local_probe.__code__:return 'follower'
    return base.classify(code)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=ROOT/'diagnostics'/('evaluation_trace_actual_local_'+stamp)
    output.mkdir()
    source_paths=list((ROOT/'evaluation/controllers').glob('*.py'))
    source_paths+=list((ROOT/'vendor/NumSim-mine/src/controllers').glob('*.py'))
    source_paths+=[ROOT/'diagnostics'/name for name in (
        'evaluation_trace.py','evaluation_trace_local.py','evaluation_trace_monitor.py',
        'evaluation_trace_finalize.py','evaluation_trace_state.py','evaluation_trace_storage.py','test_head_service_resources.py',
        'test_shared_service_main_stack.py','probe_evaluation_trace_actual_local.py')]
    source_paths += [CONFIG,ROOT/CONTRACT,input_path('state_000900.json'),
                     input_path('action_000750.json'),input_path('action_000900.json')]
    hashes={str(p):sha(p) for p in source_paths}
    tuning=read(CONFIG);tuning['urban']['capacity']['head_resource_contract']=CONTRACT
    started=time.perf_counter()
    with patch.dict(os.environ,{'RW_OFFSET_WRITER':'experiment'}):
        cfg,state,detectors,tuning,raw,mapping,metadata=configured(
            tuning,input_path('state_000900.json'),input_path('action_000750.json'))
        controller=adapter.build_priced_wu_link_controller(cfg,tuning)
        adapter.install_vissim_terminal_cost_objective(controller,cfg,tuning)
        adapter.install_price_worker_bootstrap(controller,raw,detectors)
        _,Demand,Control,_,_,_=adapter.repo_imports(ROOT/'vendor/NumSim-mine')
        action=adapter.control_from_json(input_path('action_000900.json'),cfg,Control)
        calibration=adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration=adapter.deep_update(dict(calibration),tuning.get('calibration_override',{}))
        demand=adapter.demand_from_state(raw,cfg,Demand,1,calibration,detectors)[0]
        packet=pickle.dumps((controller,state,action,demand))
        results=[];elapsed=[];inputs_unchanged=[];document=None
        for mode in ('off','monitor'):
            current,current_state,current_action,current_demand=pickle.loads(packet)
            before=pickle.dumps((current_state,current_action,current_demand))
            handle=install(output,selector=selector,include_local=True) if mode=='monitor' else None
            start=time.perf_counter()
            try:result=actual_local_probe(current,current_state,current_demand,current_action)
            finally:
                elapsed.append(time.perf_counter()-start)
                if handle:document=handle.finish()
            results.append(result)
            inputs_unchanged.append(before==pickle.dumps((current_state,current_action,current_demand)))
    evidence=collection(output,root_pid=os.getpid())
    from diagnostics.evaluation_trace_storage import load_document
    local=load_document(output/f'local_evaluation_{os.getpid()}.json')
    changes=[p for p,h in hashes.items() if sha(p)!=h]
    summary={'schema':'actual-local-trace-serialization/v1','output_directory':str(output),
             'scope':'Cold actual head-resource configured900 with actual prior750; original SC1004 setup and one local cost in each mode. Diagnostic root wrapper, not a follower search.',
             'raw_sim_sec':raw['sim_sec'],'config_fixture':str(CONFIG),'prior':str(input_path('action_000750.json')),
             'results':results,'cost_float_hex':[float(r['score']).hex() for r in results],
             'results_exact':results[0]==results[1],'input_pickle_unchanged':inputs_unchanged,
             'local_calls_per_mode':1,'global_endpoints':0,'MPC_searches':0,'VISSIM_runs':0,
             'trace_valid':evidence['valid'],'trace_errors':evidence['errors'],
             'parent_errors':document['errors'],'local_errors':local['errors'],
             'local_rows':len(local['rows']),'local_contexts':len(local['contexts']),
             'local_value_snapshots':len(local['values']),'operational_rows':len(local['operational']),
             'sidecar_bytes':{p.name:p.stat().st_size for p in output.iterdir() if p.is_file()},
             'elapsed_sec_instrumented_scope':dict(zip(('off','monitor'),elapsed)),
             'total_probe_elapsed_sec':time.perf_counter()-started,'source_sha256':hashes,
             'source_changes':changes,'v1_comparison_sha256':evidence['v1_comparison_sha256'],
             'local_comparison_sha256':evidence['comparison_sha256']}
    summary['valid']=summary['results_exact'] and all(inputs_unchanged) and evidence['valid'] and not changes
    (output/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('source_sha256','results')},indent=2,ensure_ascii=False))
    return 0 if summary['valid'] else 1


if __name__=='__main__':raise SystemExit(main())
