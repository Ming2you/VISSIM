"""Small synthetic tape timing, not a traffic rollout or full-decision claim."""
import ctypes
import json
from pathlib import Path
import time
import numpy as np
from evaluation.controllers.sdmpc_tangent_constraints import _forward_columns
from central_batch_candidate import columns

HERE=Path(__file__).resolve().parent
out=HERE/'central_batch_micro.json'
assert not out.exists()
k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p
k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
n=300000;axes=96
rng=np.random.default_rng(1009)
p1=np.maximum(0,np.arange(n,dtype=np.int64)-1)
p2=np.maximum(0,np.arange(n,dtype=np.int64)-rng.integers(1,1000,n))
w1=np.full(n,.9);w2=np.full(n,.1)
sn=np.linspace(1,n//2,axes,dtype=np.int64)
sa=np.arange(axes,dtype=np.int64);sw=np.ones(axes)
outputs=np.unique(np.linspace(1,n-1,200,dtype=np.int64))
arrays=(p1,p2,w1,w2,sn,sa,sw)
# Warm both JITs on the small existing numerical fixture; no large warm run.
from test_central_batch_candidate import fixture
a,o=fixture();_forward_columns(a,o,13,8);columns(a,o,13,8)
measure=[];baseline=None
for label,width in [('existing',None),('batch2',2),('batch4',4),('existing',None),('batch4',4),('batch2',2)]:
    t=time.perf_counter()
    result=_forward_columns(arrays,outputs,axes,8)[0] if width is None else columns(arrays,outputs,axes,8,width)
    elapsed=time.perf_counter()-t
    if baseline is None:baseline=result
    np.testing.assert_array_equal(baseline,result,strict=True)
    measure.append(dict(mode=label,seconds=elapsed,identical=True))
report=dict(status='synthetic_only',nodes=n,axes=axes,threads_budget=8,
    measurements=measure,additional_traffic_rollouts=0,production_installed=False,
    caveat='Small synthetic tape under competing native/full-benchmark workload; no end-to-end speed claim.')
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report))
