import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import json,pickle,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
request=pickle.loads((HERE.parent/'multirate271/macro_hold_ad_v3_request.pickle').read_bytes())
cfg=request['owned'][0].cfg;state=request['owned'][1]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.runtime_setup import install_worker_runtime
install_worker_runtime(adapter,cfg,request['bootstrap']['state_json'],request['bootstrap']['detector_mapping'])
from evaluation.controllers.route_choice_corridor import _movement_spec
rows={}
for connector,m in state.lane_urban_runtime.movements.items():
    rows[str(connector)]={'movement':m,'spec':cfg.network.urban_movements[m],
        'route_choice':bool(_movement_spec(cfg,m)),
        'known':getattr(cfg.network,'known_legsplit_routes',{}).get('storage'),
        'direct':getattr(cfg.network,'direct_exit_legsplit',{}).get('storage')}
print(json.dumps({'local':rows,'request_fields':list(request),'owned_types':[type(x).__name__ for x in request['owned']]},default=str))
