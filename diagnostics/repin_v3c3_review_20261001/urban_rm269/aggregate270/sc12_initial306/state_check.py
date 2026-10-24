"""Exact value comparison; pickle memo/alias layout is not physical state."""
import numpy as np

def equal(a,b,seen=None):
    if seen is None:seen=set()
    pair=id(a),id(b)
    if pair in seen:return True
    seen.add(pair)
    if type(a) is not type(b):return False
    if isinstance(a,np.ndarray):
        if a.dtype!=b.dtype or a.shape!=b.shape:return False
        if a.dtype.hasobject:return equal(a.tolist(),b.tolist(),seen)
        return np.array_equal(a,b,equal_nan=a.dtype.kind in 'fc')
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k],seen) for k in a)
    if isinstance(a,(tuple,list)):return len(a)==len(b) and all(equal(v,w,seen) for v,w in zip(a,b))
    if hasattr(a,'__dict__'):return equal(vars(a),vars(b),seen)
    return a==b
