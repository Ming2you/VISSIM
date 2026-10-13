import builtins
import importlib.util
from pathlib import Path
import numpy as np
import pytest
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import sdmpc_tangent_summary as summary

spec=importlib.util.spec_from_file_location('stock_sum_candidate',Path(__file__).with_name('stock_sum_candidate.py'))
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)

@pytest.fixture(autouse=True,params=['prototype','production'])
def implementation(request,monkeypatch):
    if request.param=='production':
        from evaluation.controllers import sdmpc_stock_geometry
        monkeypatch.setitem(globals(),'candidate',sdmpc_stock_geometry)

def witness(function, values, guard=False):
    trace=ad.Trace([1.,1.])
    a=ad.Dual(1.,{0:1.},trace);b=ad.Dual(-1.,{1:1.},trace)
    zero=ad.Dual._result(0.,0,0,trace)
    items=[{'a':a,'b':b,'zero':zero}.get(v,v) if isinstance(v,str) else v for v in values]
    old=ad.PRIMAL_GUARD;ad.PRIMAL_GUARD=guard
    try: result=function(items)
    finally: ad.PRIMAL_GUARD=old
    return (ad.primal(result),type(result),getattr(result,'node',0),getattr(result,'support',0),
            tuple(v.tobytes() for v in (trace.p1,trace.p2,trace.w1,trace.w2)),dict(trace.counts))

@pytest.mark.parametrize('guard',[False,True])
@pytest.mark.parametrize('values',[
    ['a']*100, ['a','b',0.]*100, [1e12,-1e12,1e-8]*20+['a','b'],
    ['zero',1e-200,'a',-0.]*30, [0.]*40+['a']+[0.]*40,
    ['a']+[1e-200]*100+['b'], ['zero']*40,
    [1,2]*30+['a'], [1e308]*40+['a'], [], ['a','b'], [1.,2.]*50])
def test_same_numeric_type_tape_weights_and_dependency(values,guard):
    assert witness(builtins.sum,values,guard)==witness(candidate.stock_sum,values,guard)

def test_fused_operation_path_same_tape():
    names=('__add__','__radd__','__sub__','__rsub__','__mul__','__rmul__','__truediv__','__lt__','__le__','__gt__','__ge__')
    old={k:getattr(ad.Dual,k) for k in names};operation=ad.Trace.operation
    try:
        ad.Trace.operation=summary.checked_operation;summary.install_fused_operations()
        values=['a','b',0.,1e-200]*80
        assert witness(builtins.sum,values)==witness(candidate.stock_sum,values)
    finally:
        for k,v in old.items():setattr(ad.Dual,k,v)
        ad.Trace.operation=operation

def test_mixed_tapes_and_frozen_tape_fail():
    one,two=ad.Trace([1.]),ad.Trace([1.])
    a=ad.Dual(1.,{0:1.},one);b=ad.Dual(1.,{0:1.},two)
    with pytest.raises(ValueError,match='mixed'):candidate.stock_sum([a,b]*80)
    one.frozen=True
    with pytest.raises(ValueError,match='frozen|after derivative'):candidate.stock_sum([a]*160)

@pytest.mark.parametrize('lane',[None,'1','2','3'])
def test_actual_shared_stock_wrapper_preserves_lane_order(lane):
    from collections import deque
    from types import SimpleNamespace
    from evaluation.controllers.lane_offramp_runtime import SharedSignalApproach
    values=['a','zero',0.,1e-200,'b']*40
    def wrapper(fn):
        def run(items):
            # Source tags and physical lane keys must stay unchanged.
            obj=SimpleNamespace(queues={'2':deque([[i,'off','left',v] for i,v in enumerate(items[:100])]),
                                         '1':deque([[i,'city','straight',v] for i,v in enumerate(items[100:])])})
            before=repr(obj.queues)
            result=fn(obj,lane)
            assert repr(obj.queues)==before
            return result
        return run
    assert witness(wrapper(SharedSignalApproach.stock),values)==witness(wrapper(candidate.shared_stock),values)

def test_actual_known_total_wrapper_preserves_routes_and_order():
    from types import SimpleNamespace
    from evaluation.controllers.route_choice_corridor import _known_total
    values=['a','zero',0.,1e-200,'b']*40
    def wrapper(fn):
        def run(items):
            state=SimpleNamespace(known_legsplit_route_state={'cohorts':[
                {'vehicles':v,'lane':i%2+1,'target':'ramp' if i%2 else 'straight'}
                for i,v in enumerate(items)]})
            before=repr(state.known_legsplit_route_state)
            result=fn(state)
            assert repr(state.known_legsplit_route_state)==before
            return result
        return run
    assert witness(wrapper(_known_total),values)==witness(wrapper(candidate.known_total),values)
