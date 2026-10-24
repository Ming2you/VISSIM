"""Small arithmetic fixture for recorder transport QA, not a traffic model."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
from types import SimpleNamespace as NS

from diagnostics.evaluation_trace_synthetic import toy_control

_PRICE_WORKER_CTX={}


def component(model,q0,greens):
    return q0['M']+greens['p1']/10.


class ToyLocal:
    def __init__(self):
        self.cfg=NS(network=NS(control_area_enabled=True),simulation=NS(T_u_h=5/3600.))
        self.signal_marginal_price={'S':.25}
        self.signal_marginal_price_ref={'S':20.}
        self.signal_marginal_price_weight=1.
        self.model=NS(cfg=self.cfg,signal='S',cap_flow_of={'M':600.})

    def green(self,state,demand,previous):
        signal='S';evals=0;best=float('inf');chosen=None
        for p1 in (20.,30.,40.):
            if p1==30.:continue
            greens={'p1':p1}
            cost=component(self.model,{'M':state.stock},greens)
            cost+=.25*(p1-20.)
            evals+=1
            if cost<best:best,chosen=cost,p1
        return chosen,best,evals

    def metered(self,state,demand,previous):
        def _solve_with(meter):
            return {'FW':80.},10.+meter['R'],2
        evals_total=0
        best_meter={'R':2.}
        best_vsl,best_cost,e0=_solve_with(best_meter)
        best_cost+=3.
        evals_total+=e0
        for value in (3.,4.):
            trial={'R':value}
            vsl_dict,cost,e=_solve_with(trial)
            cost+=3.
            evals_total+=e
        return best_vsl,best_meter,evals_total

    def phases(self,state,demand,previous):
        signal='S';price={'p1':.5};ref={'p1':20.};weight=1.
        def scored(vec):
            local=component(self.model,{'M':state.stock},vec)
            ext=price['p1']*(vec['p1']-ref['p1'])
            return local+weight*ext
        scores=[scored({'p1':g}) for g in (20.,25.)]
        return scores

    def fail(self,state,demand,previous):
        raise ValueError('synthetic selected failure')

    def run(self,state,demand,previous):
        return [self.green(state,demand,previous),self.metered(state,demand,previous),
                self.phases(state,demand,previous)]


def specs():
    path='diagnostics/evaluation_trace_local_synthetic.py'
    def make(suffix,kind,mode='return',**kw):
        return dict(path=path,suffix=suffix,kind=kind,mode=mode,**kw)
    return [
        make('ToyLocal.green','urban_candidate','counter',counter='evals',count=1,
             fields=['signal','p1','greens'],score='cost'),
        make('ToyLocal.metered','meter_candidate','counter',counter='evals_total',count=2,
             fields=[],score='meter_branch'),
        make('ToyLocal.phases','phase_search_context','context'),
        make('ToyLocal.phases.<locals>.scored','phase_candidate',fields=['signal','vec','price','ref','weight']),
        make('component','local_physical_component','component'),
        make('ToyLocal.fail','failure','context'),
    ]


def selector(code):
    if code.co_filename==__file__:
        if code.co_qualname=='ToyLocal.run':return 'follower'
        if code.co_name=='_price_worker_toy':return 'price_task'
    return None


def enable(directory,backend):
    from diagnostics import evaluation_trace as base
    from diagnostics.evaluation_trace_local import Targets,attach
    if backend=='off':return None
    if backend=='profile':
        parent=base.install(directory,selector=selector)
        local=attach(parent,Targets(specs()))
        return local,parent
    from diagnostics.evaluation_trace_monitor import install
    return install(directory,selector=selector,local_targets=Targets(specs()))


def disable(handle):
    if isinstance(handle,tuple):
        local,parent=handle
        local.finish();return parent.finish()
    if handle:return handle.finish()


def init(directory,backend):
    ctrl=ToyLocal()
    _PRICE_WORKER_CTX.update(ctrl=ctrl,state=NS(stock=2.),forecast=NS(rate=1.),previous=toy_control())
    enable(directory,backend)


def _price_worker_toy(task):
    ctx=_PRICE_WORKER_CTX
    return [task,ctx['ctrl'].run(ctx['state'],ctx['forecast'],ctx['previous'])]


def execute(directory,backend,spawn=False):
    ctrl=ToyLocal();state=NS(stock=2.);demand=NS(rate=1.);previous=toy_control()
    handle=enable(directory,backend)
    try:
        out=ctrl.run(state,demand,previous)
        if spawn:
            with ProcessPoolExecutor(max_workers=2,initializer=init,initargs=(directory,backend)) as pool:
                tasks=list(pool.map(_price_worker_toy,[0,1,2,3]))
            out.append(tasks)
        return out
    finally:disable(handle)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('directory');parser.add_argument('--backend',choices=['off','profile','monitor'],required=True)
    parser.add_argument('--spawn',action='store_true')
    args=parser.parse_args()
    print(json.dumps(execute(Path(args.directory),args.backend,args.spawn),sort_keys=True))
