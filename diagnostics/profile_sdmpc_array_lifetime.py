"""Sample reverse-node creation sites; diagnostic only, no predictor mutations."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import pickle
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers import sdmpc_tangent_runtime as runtime,sdmpc_tangent_reverse as ad
    counts=Counter();total=0
    original=ad.Trace.node
    def node(trace,*args,**kwargs):
        nonlocal total
        total+=1
        if total%4093==0:
            frame=sys._getframe(1);sites=[]
            while frame is not None and len(sites)<3:
                path=Path(frame.f_code.co_filename)
                if (path.is_relative_to(ROOT) and path.name not in
                        ('sdmpc_tangent_reverse.py','sdmpc_dual.py')):
                    sites.append(f'{path.relative_to(ROOT).as_posix()}:{frame.f_lineno}:{frame.f_code.co_name}')
                frame=frame.f_back
            counts[tuple(sites)]+=1
        return original(trace,*args,**kwargs)
    ad.Trace.node=node
    finder=runtime.install(ROOT,'reverse-v1')
    from evaluation.controllers.sdmpc_tangent_worker import run
    from evaluation.controllers import sdmpc_sequence
    source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    request['horizon']=1
    request['axes']=[axis for axis in request['axes'] if axis.get('block',0)==0]
    request['action']=sdmpc_sequence.first_action(request['action'])
    request['owned'][0].cfg.network.sdmpc_options.update(control_blocks=1)
    for path in request['bootstrap']['runtime_sources']:
        request['bootstrap']['runtime_sources'][path]=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    started=time.perf_counter()
    result=run(request,finder,{})
    rows=[dict(stack=list(key),samples=n,estimated_node_fraction=n/sum(counts.values()))
          for key,n in counts.most_common()]
    report=dict(scope=__doc__,sample_every_nodes=4093,total_nodes=total,sample_count=sum(counts.values()),
        diagnostic_horizon_sec=150,diagnostic_axes=77,rows=rows,wall_sec=time.perf_counter()-started,
        scalar_sec=result['scalar_sec'],tangent_sec=result['tangent_sec'],
        complete_primal_state_match=result['complete_primal_state_match'],
        max_primal_state_error=result['max_primal_state_error'],
        source_sha256={**result['transformed_source_sha256'],str(Path(__file__).resolve()):
                       hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        limits='Deterministic sampled node counts, not CPU time. Wrapper and stack-sampling overhead included. '
               'One diagnostic 150s block, not production 450s horizon or complete SDMPC decision.')
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','rows')},indent=2))
    print(json.dumps(rows[:12],indent=2))


if __name__=='__main__':main()
