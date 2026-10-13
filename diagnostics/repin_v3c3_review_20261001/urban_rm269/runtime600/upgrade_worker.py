"""Canonical one-candidate worker plus route/time transfer evidence only."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import ctypes
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_tangent_worker as worker
original_run=worker.run

def run(request,finder,progress):
    from evaluation.controllers import sdmpc_tangent_surrogate as surrogate
    original_prediction=surrogate.prediction
    def prediction(point,*args,**kwargs):
        result=original_prediction(point,*args,**kwargs)
        rows=point.control_area_response['transfers']
        identities=('stage','start_sec','end_sec','source','target','route_key')
        amounts=('vehicles','ttd_veh','entered_veh')
        groups={}
        for row in rows:
            key=tuple(row[k] for k in identities)
            group=groups.setdefault(key,{k:[] for k in amounts})
            for k in amounts:group[k].append(float(getattr(row[k],'value',row[k])))
        result['diagnostic_transfer_witness']=dict(schema='route-clock-transfer-comparison/v1',
            captured_count=len(rows),uncaptured_count=result['control_area']['event_count']-len(rows),
            groups=[dict(key=list(key),**{k:math.fsum(group[k]) for k in amounts})
                    for key,group in sorted(groups.items(),key=lambda row:repr(row[0]))])
        result.pop('response_token')
        result['response_token']=surrogate.token(result)
        return result
    surrogate.prediction=prediction
    return original_run(request,finder,progress)

if __name__=='__main__':
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    worker.run=run
    raise SystemExit(worker.main())
