import math
import random
import struct
import pytest
from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers.sdmpc_tangent_summary import install_fused_operations
import native_emit


def original():
    install_fused_operations()
    cells=dict(zip(ad.Dual.__add__.__code__.co_freevars,ad.Dual.__add__.__closure__))
    native_emit.configure(ad,ad.Dual)
    return cells['emit'].cell_contents


def describe(v):
    if isinstance(v,ad.Dual):
        return ('dual',struct.pack('d',v.value),v.node,v.support,v.risks,v.tangent)
    return ('float',struct.pack('d',v))


@pytest.mark.parametrize('guard',[False,True])
@pytest.mark.parametrize('wa,wb',[(1.,1.),(-1.,1.),(0.,0.),(1.,0.),(0.,1.),(2.,3.),(math.inf,math.nan),(1e-250,-1e-250)])
def test_edge_tapes(guard,wa,wb):
    old=original();ad.PRIMAL_GUARD=guard
    try:
        outputs=[]
        for emit in (old,native_emit.emit):
            t=ad.Trace([1.]*240)
            a=ad.Dual(2.,{0:1.,230:1.},t);b=ad.Dual(3.,{1:1.,230:1.},t)
            values=[]
            for other,db in ((a,True),(b,True),(3.,False)):
                for value in (0.,-0.,math.inf,math.nan,1e-250,1.25):
                    values.append(describe(emit(t,value,a,wa,other,wb,db)))
            outputs.append((values,tuple(bytes(x) for x in (t.p1,t.p2,t.w1,t.w2))))
        assert outputs[0]==outputs[1]
    finally:
        ad.PRIMAL_GUARD=False;native_emit.reset()


@pytest.mark.parametrize('frozen',[False,True])
def test_mixed_trace_and_frozen(frozen):
    old=original()
    for emit in (old,native_emit.emit):
        t=ad.Trace([1.]);u=ad.Trace([1.]);a=ad.Dual(2.,{0:1.},t);b=ad.Dual(3.,{0:1.},u)
        with pytest.raises(ValueError,match='mixed'):emit(t,5.,a,1.,b,1.,True)
        t.frozen=frozen
        if frozen:
            with pytest.raises(ValueError,match='frozen|sweep'):emit(t,4.,a,2.,2.,0.,False)
        else:emit(t,4.,a,2.,2.,0.,False)
        # Identity and exact cancellation need no new tape node, even frozen.
        assert describe(emit(t,2.,a,1.,0.,0.,False))[2]==a.node
        assert emit(t,0.,a,1.,a,-1.,True)==0.
    native_emit.reset()


def test_complete_chain_same_tape():
    old=original();cells=dict(zip(ad.Dual.__add__.__code__.co_freevars,ad.Dual.__add__.__closure__))
    cell=cells['emit'];results=[]
    try:
        for emitter in (old,native_emit.emit):
            cell.cell_contents=emitter
            t=ad.Trace([1.,1.]);x=ad.Dual(2.,{0:1.},t);y=ad.Dual(3.,{1:1.},t)
            rng=random.Random(42)
            for i in range(12000):
                # Add, subtract, multiplication, reverse subtraction and division.
                x=(x*.999+rng.random()*y)/(1.+rng.random()*.001)
                y=5.-(y*.998-x*.001)
            results.append((describe(x),describe(y),tuple(bytes(a) for a in (t.p1,t.p2,t.w1,t.w2))))
        assert results[0]==results[1]
    finally:cell.cell_contents=old;native_emit.reset()
