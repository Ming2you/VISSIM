"""One scalar diagnostic, counting live cohort size without changing model state."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes
import json
import math
from collections import Counter
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_worker as worker
original_run=worker.run


def run(request,finder,progress):
    assert request.get('surrogate_evaluation')=='scalar'
    from evaluation.controllers import route_choice_corridor as rc,known_wout_causal_response as causal
    from evaluation.controllers.lane_offramp_runtime import SharedSignalApproach
    original_commit=rc.known_legsplit_commit
    original_stock=SharedSignalApproach.stock
    evidence=dict(samples=[],commit_calls=0,peak_cohorts=0,stock_calls=0,stock_items=0,timings={})
    for module,name in [(rc,'known_legsplit_requests'),(rc,'_known_local_queue_advance'),(causal,'advance')]:
        original=getattr(module,name)
        def timed(*args,_original=original,_name=name,**kwargs):
            start=time.perf_counter()
            try:return _original(*args,**kwargs)
            finally:evidence['timings'][_name]=evidence['timings'].get(_name,0.)+time.perf_counter()-start
        setattr(module,name,timed)
    def stock(self,lane=None):
        evidence['stock_calls']+=1
        evidence['stock_items']+=sum(len(q) for key,q in self.queues.items() if lane is None or key==lane)
        return original_stock(self,lane)
    def commit(state,cfg,receipts,step):
        start=time.perf_counter()
        result=original_commit(state,cfg,receipts,step)
        evidence['timings']['commit_including_local_queue']=evidence['timings'].get('commit_including_local_queue',0.)+time.perf_counter()-start
        cohorts=state.known_legsplit_route_state['cohorts']
        evidence['commit_calls']+=1
        evidence['peak_cohorts']=max(evidence['peak_cohorts'],len(cohorts))
        if evidence['commit_calls'] in (1,150,300,450):
            small=[]
            for limit in (1e-15,1e-12,1e-9,1e-6,.001,.01):
                amounts=[c['vehicles'] for c in cohorts if 0<c['vehicles']<limit]
                small.append(dict(below_veh=limit,count=len(amounts),mass_veh=math.fsum(amounts)))
            signatures=Counter(json.dumps({k:v for k,v in c.items() if k!='vehicles'},sort_keys=True) for c in cohorts)
            evidence['samples'].append(dict(step=step,cohorts=len(cohorts),mass_veh=math.fsum(c['vehicles'] for c in cohorts),
                target_counts=dict(Counter(c['target'] for c in cohorts)),small=small,
                exactly_identical_metadata_groups=len(signatures),ready=sum(c['due']<=step for c in cohorts)))
        return result
    rc.known_legsplit_commit=commit;SharedSignalApproach.stock=stock
    result=original_run(request,finder,progress)
    result['cohort_size_diagnostic']=evidence
    return result

if __name__=='__main__':
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    worker.run=run
    raise SystemExit(worker.main())
