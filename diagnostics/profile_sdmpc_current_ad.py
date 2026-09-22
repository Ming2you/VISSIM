"""Profile one AD trajectory, not an optimization iteration; no VISSIM."""
from pathlib import Path
import cProfile
import hashlib
import json
import pickle
import pstats
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    from evaluation.controllers import sdmpc_tangent_runtime as runtime
    finder=runtime.install(ROOT,'reverse-v1')
    from evaluation.controllers.sdmpc_tangent_worker import run
    from evaluation.controllers import sdmpc_sequence
    source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
    request=pickle.loads((source/'request.pickle').read_bytes())
    request['horizon']=1
    request['axes']=[axis for axis in request['axes'] if axis.get('block',0)==0]
    request['action']=sdmpc_sequence.first_action(request['action'])
    request['owned'][0].cfg.network.sdmpc_options.update(control_blocks=1)
    request['surrogate_evaluation']='ad'
    for name in request['bootstrap']['runtime_sources']:
        request['bootstrap']['runtime_sources'][name]=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    profile=cProfile.Profile()
    try:
        result=profile.runcall(run,request,finder,{})
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        profile.dump_stats(str(out/'profile.pstats'))
        with (out/'profile.txt').open('w',encoding='utf-8') as stream:
            stats=pstats.Stats(profile,stream=stream)
            stats.sort_stats('cumulative').print_stats(70)
            stats.sort_stats('tottime').print_stats(55)


if __name__=='__main__':main()
