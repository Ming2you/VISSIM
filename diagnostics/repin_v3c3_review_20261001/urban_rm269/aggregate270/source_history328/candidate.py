"""One causal four-window admitted-rate smoother, diagnostic only.

Retains A1's schedule/backlog recursion. A smoothed achieved rate is not a
physical saturation estimate or an endogenous source receiving law.
"""
import math
from evaluation.controllers.source_boundary import forecast

WINDOWS=4

def historical_cap(records,cutoff):
    # A caller may hold later verification records, but they cannot affect this
    # forecast. Duplicate/invalid history and gaps fail rather than pool runs.
    past=[r for r in records if r['end_sec']<=cutoff]
    if not past or past[-1]['end_sec']!=cutoff:raise ValueError('No observed cutoff')
    if len({r['end_sec'] for r in past})!=len(past) or past!=sorted(past,key=lambda r:r['end_sec']):
        raise ValueError('History is not uniquely ordered')
    selected=past[-WINDOWS:]
    if len({r['run_id'] for r in selected})!=1:raise ValueError('Mixed runs')
    for i,r in enumerate(selected):
        n=r['admitted_window'];dt=r['interval_s']
        if isinstance(n,bool) or not math.isfinite(n) or n<0 or dt!=150:
            raise ValueError('Invalid admitted count or interval')
        if i and r['end_sec']-selected[i-1]['end_sec']!=150:raise ValueError('History gap')
    if len(selected)<WINDOWS:
        return dict(cap_vph=selected[-1]['admitted_window']*24.,windows=1,fallback='insufficient_history',end_sec=cutoff)
    return dict(cap_vph=math.fsum(r['admitted_window'] for r in selected)*3600/600,
                windows=4,start_sec=selected[0]['end_sec']-150,end_sec=cutoff,fallback=None)

def predict(records,cutoff,backlog,schedule):
    receipt=historical_cap(records,cutoff)
    rates=forecast(receipt['cap_vph'],backlog,schedule,float(cutoff),150,3,step_s=10)
    return rates,receipt
