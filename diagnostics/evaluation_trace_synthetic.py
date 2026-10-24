"""Tiny synthetic operations for trace QA, never an alternative traffic model.

Compilation filenames select the real tracer boundaries but live under a
nonexistent synthetic directory. No production function body is copied/executed.
"""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS

_PRICE_WORKER_CTX = {}


def toy_control(value=80.):
    return NS(N_P_star=1., N_UF_star=2., green_times={'SC1_p1': 20.},
              ramp_metering={'R': 5.}, vsl={'FW': value}, offsets={'SC1': 10.},
              inflow_outflow_allocation={}, infeasibility={},
              diagnostics={'wu_faithful_solve_time_sec': 999.,
                           'rw_meter_R_green_sec': 5.})


def source(filename, text):
    path = Path(__file__).parent / '_synthetic_boundaries' / filename
    exec(compile(text, str(path), 'exec'), globals())


source('coupling.py', '''
def run_coupled_interval(state, control, demand, cfg):
    return NS(freeway_ttt=control.vsl['FW']/10, urban_ttt=1.)
''')
source('rollout_endpoint.py', '''
def vendor_evaluate_price_point(state, previous, forecast, action_schedule, objective_spec):
    control=deepcopy(previous)
    run_coupled_interval(state,control,forecast[0],objective_spec.cfg)
    control.vsl['FW']+=1.
    run_coupled_interval(state,control,forecast[0],objective_spec.cfg)
    return NS(control=control,states=[state,state],objective=control.vsl['FW'],ttt=2.,metadata={})
''')
# Keep actual co_name for the inner endpoint without replacing its module name.
vendor_evaluate_price_point.__code__ = vendor_evaluate_price_point.__code__.replace(co_name='evaluate_price_point')
source('area_runtime.py', '''
def evaluate_price_point(state, previous, forecast, action_schedule, objective_spec):
    control=deepcopy(previous)
    return vendor_evaluate_price_point(state,control,forecast,action_schedule,objective_spec)
''')
source('area_follower_objective.py', '''
def inner_solve(self,state,leader,demand,previous):
    return NS(control=deepcopy(previous),objective_value=3.,iterations=1,converged=True,
              residual_objective=0.,residual_control=0.,diagnostics={'wall_time_sec':987.})
''')
inner_solve.__code__ = inner_solve.__code__.replace(co_name='solve')
source('local_signal_service.py', '''
def outer_solve(self,*args,**kwargs):
    return inner_solve(self,*args,**kwargs)
''')
outer_solve.__code__ = outer_solve.__code__.replace(co_name='solve')
source('stackelberg_wu_metered.py', '''
class ToyController:
    def __init__(self):
        self.cfg=NS(network=NS(control_area_beta_seconds=300.),simulation=NS(control_interval=150.))
        self.signal_phase_price={'SC1':{'p1':.25}}
        self._nuf_solve_cache={}
        self._dedupe_hits=0
    def _global_rollout_ttt_with_vsl(self,state,previous,forecast,link,seg_key,value,vsl_upper):
        control=deepcopy(previous)
        control.vsl[seg_key]=value
        return evaluate_price_point(state,control,forecast,(),NS(cfg=self.cfg,score_mode='price')).objective
    def _evaluate_fallback_candidates(self,state,forecast,previous,start_index):
        nash=outer_solve(self,state,None,forecast,previous)
        return [NS(index=start_index,stage='fallback_pfo',action=previous,nash=nash,
                   objective=-3.,objective_terms={'leader_total_objective':-3.},
                   metadata={'wall_time_sec':456.},rollout_used=True)]
def _price_worker_vsl(task):
    key,which,link,value,upper=task
    ctx=_PRICE_WORKER_CTX
    score=ctx['ctrl']._global_rollout_ttt_with_vsl(ctx['state'],ctx['previous'],ctx['forecast'],link,key,value,upper)
    return (key,which),score
''')
source('stackelberg_wu_metered.py', '''
def _price_batch(self,tasks,worker,serial_fn,state,previous,forecast):
    with ProcessPoolExecutor(max_workers=2,initializer=init,initargs=()) as pool:
        return dict(pool.map(worker,tasks))
''')
ToyController._price_batch = _price_batch
source('priced_wu_link_controller.py', '''
def _evaluate_full_candidate(self,index,action,state,forecast,previous,stage='coarse',
                             incumbent_obj=float('inf'),rollout_abort_obj=float('inf')):
    nash=outer_solve(self,state,action,forecast,previous)
    point=evaluate_price_point(state,nash.control,forecast,(),NS(cfg=self.cfg,score_mode='leader'))
    return NS(index=index,stage=stage,action=action,nash=nash,objective=point.objective,
              objective_terms={'leader_total_objective':point.objective},
              metadata={'leader_candidate_wall_sec_coarse_0':123.,'leader_candidate_nuf_reuse_coarse_0':0.},rollout_used=True)
''')
ToyController._evaluate_full_candidate = _evaluate_full_candidate
source('area_leader_objective.py', '''
def _proxy_score_candidate(self,index,action,state,forecast,previous):
    control=deepcopy(previous)
    control.N_P_star=action.N_P_star
    point=evaluate_price_point(state,control,forecast,(),NS(cfg=self.cfg,score_mode='raw'))
    return {'index':index,'objective':point.objective,'N_P_star':control.N_P_star}
''')
ToyController._proxy_score_candidate = _proxy_score_candidate


def init():
    _PRICE_WORKER_CTX.update(ctrl=ToyController(),state=NS(time_sec=900.,stock={'X':2.}),
                             previous=toy_control(),forecast=[NS(rate=1.)])


def run():
    init()
    ctx=_PRICE_WORKER_CTX; ctrl=ctx['ctrl']; state=ctx['state']; previous=ctx['previous']; forecast=ctx['forecast']
    before=deepcopy(vars(previous))
    pfo=ctrl._evaluate_fallback_candidates(state,forecast,previous,0)
    proxies=[ctrl._proxy_score_candidate(i,toy_control(v),state,forecast,previous) for i,v in enumerate((80.,100.))]
    full=ctrl._evaluate_full_candidate(0,previous,state,forecast,previous)
    tasks=[('FW',str(i),'FW',float(80+i),120.) for i in range(4)]
    prices=ctrl._price_batch(tasks,_price_worker_vsl,None,state,previous,forecast)
    assert vars(previous)==before
    return {'pfo':pfo[0].objective,'proxies':proxies,'full':full.objective,
            'prices':[[list(k),v] for k,v in prices.items()]}


if __name__ == '__main__':
    print(json.dumps(run(),sort_keys=True))
