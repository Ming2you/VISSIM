import gc
import json
import statistics
import time
from pathlib import Path
from evaluation.controllers import sdmpc_tangent_reverse as ad
from native_emit_candidate import install
import native_emit

cell,old=install()
rows=[]
try:
    for run in range(6):
        mode='python' if run%2==0 else 'compiled'
        cell.cell_contents=old if mode=='python' else native_emit.emit
        gc.collect();start=time.perf_counter()
        t=ad.Trace([1.,1.]);x=ad.Dual(2.,{0:1.},t);y=ad.Dual(3.,{1:1.},t)
        for i in range(250000):
            x=x*.999+y*.001
            y=y*.998+x*.002
        rows.append(dict(mode=mode,sec=time.perf_counter()-start,nodes=len(t.p1),x=x.value,y=y.value))
        native_emit.reset();del x,y,t
    medians={k:statistics.median(r['sec'] for r in rows if r['mode']==k) for k in ('python','compiled')}
    result=dict(rows=rows,medians=medians,speedup=medians['python']/medians['compiled'],native_runs=0,forecasts=0,
                note='Arithmetic-only diagnostic; not a full decision timing.')
    Path(__file__).with_name('native_emit_micro.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:cell.cell_contents=old;native_emit.reset()
