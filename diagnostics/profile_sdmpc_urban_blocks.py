"""One 150s diagnostic interval: time urban stages without per-call profiling.

Instrumentation lives only in this child. This is not a whole-decision timing
or a replacement qualification trajectory; the source files are never edited.
"""
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import pickle
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers import sdmpc_tangent_runtime as runtime
    from evaluation.controllers import sdmpc_tangent_reverse as ad
    times=defaultdict(float);calls=defaultdict(int)
    def record(line, elapsed):
        key=('tangent' if len(ad._TRACES) else 'scalar',line)
        times[key]+=elapsed;calls[key]+=1
    original=runtime.Loader.exec_module
    def load(loader,module):
        original(loader,module)
        if module.__name__!='evaluation.controllers.urban_flow_accounting':return
        tree=ast.parse(Path(loader.filename).read_bytes(),filename=loader.filename)
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='urban_substep_accounted')
        function=runtime.Transform().visit(function)
        body=[]
        for statement in function.body:
            if isinstance(statement,(ast.Return,ast.Expr)):
                body.append(statement);continue
            before=ast.parse('_urban_profile_started=_urban_profile_clock()').body[0]
            after=ast.parse(f'_urban_profile_record({statement.lineno},_urban_profile_clock()-_urban_profile_started)').body[0]
            body.extend((before,statement,after))
        function.body=body
        module.__dict__.update(_urban_profile_clock=time.perf_counter,_urban_profile_record=record)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),
            loader.filename,'exec',flags=__import__('__future__').annotations.compiler_flag),module.__dict__)
    runtime.Loader.exec_module=load
    finder=runtime.install(ROOT,'reverse-v1')
    from evaluation.controllers.sdmpc_tangent_worker import run
    source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    request['horizon']=1
    request['axes']=[axis for axis in request['axes'] if axis.get('block',0)==0]
    from evaluation.controllers import sdmpc_sequence
    request['action']=sdmpc_sequence.first_action(request['action'])
    request['owned'][0].cfg.network.sdmpc_options.update(control_blocks=1,spatial_receiving=False)
    for name in request['bootstrap']['runtime_sources']:
        request['bootstrap']['runtime_sources'][name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    started=time.perf_counter()
    result=run(request,finder,{})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    rows=[dict(mode=k[0],line=k[1],seconds=v,calls=calls[k]) for k,v in times.items()]
    rows.sort(key=lambda row:row['seconds'],reverse=True)
    report=dict(scope=__doc__,wall_sec=time.perf_counter()-started,rows=rows,
        scalar_sec=result['scalar_sec'],tangent_sec=result['tangent_sec'],native_applied=False)
    (out/'stages.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(wall_sec=report['wall_sec'],top=rows[:16])),flush=True)


if __name__=='__main__':main()
