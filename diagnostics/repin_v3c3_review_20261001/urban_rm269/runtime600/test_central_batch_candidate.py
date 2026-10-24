import numpy as np
import pytest
from evaluation.controllers.sdmpc_tangent_constraints import _forward_columns,_forward_column
from central_batch_candidate import columns

def fixture(n=1200,axes=13):
    rng=np.random.default_rng(8081)
    p1=np.zeros(n,dtype=np.int64);p2=p1.copy()
    for i in range(2,n):p1[i]=rng.integers(i);p2[i]=rng.integers(i)
    w1=rng.uniform(-.8,.8,n);w2=rng.uniform(-.8,.8,n)
    sn=np.array([0,1,2,11,42,42,900,950],dtype=np.int64)
    sa=np.array([0,1,3,5,8,8,2,4],dtype=np.int64)
    sw=np.array([1.,1.,-1.,1e-200,2.,-.25,1.,1.])
    return (p1,p2,w1,w2,sn,sa,sw),np.array([0,1,2,11,42,87,950,970,999,1100,n-1],dtype=np.int64)

@pytest.mark.parametrize('workers',[1,2,3,4,8])
@pytest.mark.parametrize('poison',[None,np.inf,np.nan])
def test_same_columns_and_nonfinite_pattern(workers,poison):
    arrays,outputs=fixture()
    if poison is not None:arrays[2][11]=poison
    old,_=_forward_columns(arrays,outputs,13,workers)
    for width in (2,4):
        new=columns(arrays,outputs,13,workers,width)
        np.testing.assert_array_equal(old,new,strict=True)
        np.testing.assert_array_equal(np.signbit(old),np.signbit(new))

def test_no_live_axes_and_late_seeds():
    arrays,outputs=fixture()
    a=(*arrays[:4],np.zeros(0,dtype=np.int64),np.zeros(0,dtype=np.int64),np.zeros(0))
    assert not columns(a,outputs,13,8).any()
    old,_=_forward_columns(arrays,outputs,13,8)
    np.testing.assert_array_equal(old,columns(arrays,outputs,13,8))
