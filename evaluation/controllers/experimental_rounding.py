"""Experimental opt-in upward quantization; feasibility remains mandatory."""
import math

def upward(value, allowed, tolerance=1e-9):
    if not math.isfinite(float(value)) or not allowed:
        raise ValueError('Invalid continuous control or empty admissible grid')
    choices=sorted(set(float(v) for v in allowed if math.isfinite(float(v))))
    if len(choices)!=len(set(allowed)):
        raise ValueError('Nonfinite actuator grid')
    feasible=[v for v in choices if v>=float(value)-tolerance]
    if not feasible:
        raise ValueError('Upward rounding has no admissible grid value')
    return min(feasible)
