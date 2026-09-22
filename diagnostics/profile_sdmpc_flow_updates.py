"""150s function timings for flow request and movement update; no VISSIM."""
from collections import defaultdict
import functools
import cProfile
import pstats
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
    times=defaultdict(float);calls=defaultdict(int)
    names={
        'evaluation.controllers.urban_flow_accounting':('_corridor_intended','_receive_corridor','emit_transfer'),
        'evaluation.controllers.sdmpc_continuous':('phase_fraction','periodic_fraction'),
        'evaluation.controllers.sdmpc_aggregate':('prehead_limit','prehead_accept','prehead_check','route_accept','route_check'),
        'evaluation.controllers.native_input_prehead':('limit_intended','receive_accepted'),
        'evaluation.controllers.native_input_routes':('receive_accepted',),
        'evaluation.controllers.route_choice_corridor':('intended_departure','receive_accepted','_movement_spec'),
        'src.models.urban_queue_model':('_movement_capacity_flow','_link_delay_steps','_schedule')}
    def timed(function,label):
        @functools.wraps(function)
        def wrapped(*args,**kwargs):
            mode='tangent' if len(ad._TRACES) else 'scalar'
            started=time.perf_counter()
            try:return function(*args,**kwargs)
            finally:
                times[mode,label]+=time.perf_counter()-started
                calls[mode,label]+=1
        return wrapped
    original=runtime.Loader.exec_module
    def load(loader,module):
        original(loader,module)
        for name in names.get(module.__name__,()):
            setattr(module,name,timed(getattr(module,name),module.__name__+'.'+name))
        if module.__name__=='evaluation.controllers.control_area_objective':
            cls=module.ModelAreaLedger
            cls.transfer=timed(cls.transfer,module.__name__+'.ModelAreaLedger.transfer')
    profiling='--cprofile' in sys.argv
    if not profiling:
        runtime.Loader.exec_module=load
    finder=runtime.install(ROOT,'reverse-v1')
    from evaluation.controllers.sdmpc_tangent_worker import run
    from evaluation.controllers import sdmpc_sequence
    source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    request['horizon']=1;request['axes']=[axis for axis in request['axes'] if axis.get('block',0)==0]
    request['action']=sdmpc_sequence.first_action(request['action'])
    request['owned'][0].cfg.network.sdmpc_options.update(control_blocks=1,spatial_receiving=False)
    for name in request['bootstrap']['runtime_sources']:
        request['bootstrap']['runtime_sources'][name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    if profiling:
        profile=cProfile.Profile()
        try:
            result=profile.runcall(run,request,finder,{})
        finally:
            profile.dump_stats(str(out/'profile.pstats'))
            with (out/'profile.txt').open('w',encoding='utf-8') as stream:
                stats=pstats.Stats(profile,stream=stream)
                stats.sort_stats('cumulative').print_stats(65)
                stats.sort_stats('tottime').print_stats(45)
    else:
        result=run(request,finder,{})
    rows=[dict(mode=k[0],function=k[1],seconds=v,calls=calls[k]) for k,v in times.items()]
    rows.sort(key=lambda row:row['seconds'],reverse=True)
    report=dict(scope=__doc__,scalar_sec=result['scalar_sec'],tangent_sec=result['tangent_sec'],rows=rows)
    (out/'timings.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
