"""One causal Erlang headway-shape candidate; existing ramp component only."""
import ctypes
import hashlib
import importlib.util
import json
import math
import statistics
from pathlib import Path

from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
R=ROOT/'diagnostics/repin_v3c3_review_20261001'
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)


def erlang_opportunities_vph(q, tc, tf, shape):
    """q * sum[n>=0] P(H >= tc+n*tf), H~Erlang(k, rate=k*q/3600).

    The finite-sum closed forms implement the same isolated opportunity rule as
    the old Poisson bound. No mainline priority/density or merging capacity is
    identified by this function. The caller keeps the canonical supply cap.
    """
    assert q>=0 and tc>=tf>0 and shape in (1,2,3)
    if shape==1:
        return gap_acceptance_supply_vph(q,tc,tf)
    if q==0:
        return 3600/tf
    rate=shape*q/3600
    a,b=rate*tc,rate*tf
    r=math.exp(-b);d=-math.expm1(-b)
    s0=1/d;s1=r/(d*d)
    if shape==2:
        expectation=math.exp(-a)*((1+a)*s0+b*s1)
    else:
        s2=r*(1+r)/(d*d*d)
        expectation=math.exp(-a)*((1+a+a*a/2)*s0+b*(1+a)*s1+b*b*s2/2)
    value=q*expectation
    assert math.isfinite(value) and 0<=value<=3600/tf+1e-8
    return value


def verify_formula():
    from scipy.special import gammaincc
    largest=0.
    for k in (1,2,3):
        for q in (100.,300.,500.,1000.,2000.,4000.):
            terms=[]
            for n in range(5000):
                term=float(gammaincc(k,k*q/3600*(3.5+n*1.5)))
                terms.append(term)
                if term<1e-15:break
            else:raise AssertionError('Numerical reference did not converge')
            exact=erlang_opportunities_vph(q,3.5,1.5,k)
            delta=abs(exact-q*math.fsum(terms));largest=max(largest,delta)
            assert delta<1e-8,(k,q,delta)
        assert erlang_opportunities_vph(0.,3.5,1.5,k)==2400.
    return dict(reference='Independent incomplete-gamma survival sum',max_absolute_difference_vph=largest,cases=18)


def main():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    protocol=read(HERE/'protocol.json')
    pinned=read(HERE.parent/'receiving228/protocol.json')
    for name,digest in pinned['outputs_sha256'].items():
        assert hashlib.sha256((HERE.parent/'receiving228'/name).read_bytes()).hexdigest()==digest,name
    earlier=read(HERE.parent/'receiving227/assessment.json')
    feedback=read(HERE.parent/'receiving228/assessment.json')
    evidence=read(HERE.parent/'receiving228/native_evidence.json')
    original=read(HERE.parent/'receiving226/assessment.json')
    causal=[row for row in evidence['through_headways'] if row['arm']=='hold' and row['end_sec']==2700]
    causal.sort(key=lambda r:r['lane'])
    assert [r['lane'] for r in causal]==[1,2]
    shapes=[]
    for row in causal:
        assert not row['source_is_future_diagnostic']
        raw_shape=statistics.mean(row['intervals_sec'])**2/statistics.pvariance(row['intervals_sec'])
        k=round(raw_shape)
        assert 1<=k<=3, 'This finite screening protocol does not cover that shape'
        shapes.append(dict(lane=row['lane'],sample_count=row['interval_count'],raw_moment_shape=raw_shape,
            shape=k,poisson_at_observed_q_vph=row['poisson_expected_slots_vph'],empirical_at_observed_q_vph=row['empirical_slots_vph'],
            erlang_at_observed_q_vph=erlang_opportunities_vph(row['interior_gap_flow_vph'],3.5,1.5,k)))
    helper=R/'ramp10681_receiving/assess.py'
    spec=importlib.util.spec_from_file_location('existing_ramp_replay',helper)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert hashlib.sha256(helper.read_bytes()).hexdigest()==feedback['helper_sha256']
    out=dict(status='COMPLETE_CAUSAL_SHAPE_CONDITIONAL_SCREEN',input_sha256=PINS,
        source_sha256=earlier['source_sha256'],formula_verification=verify_formula(),shape_estimation=shapes,arms={},
        control_outcome_fits=0,full_forecasts=0,new_native=0,FZP=0,optimizer=0,
        formula='q * sum(n>=0, survival_Erlang(tc+n*tf)); E[H]=3600/q; current critical/followup retained',
        limitations=['Shape/flow shares only use pre2700 history, but finite-sample estimation and constancy throughout450s remain assumptions.',
                     'Frozen mainline/city feedback; not autonomous whole-network gain validation.',
                     'Native future arrivals are separate conditional diagnostics, not prediction inputs.',
                     'The actual detector is147.51m before merge; no native capacity, forced merging, priority or spatial receiving identified.',
                     'Current pair changes city green/offset only, not RM/VSL.'])
    for case in ('held_actual','selected'):
        path=I/'closedloop_recorded2700_select_check_trace10681_rm225_candidate52_response'/f'{case}_RM_C10681_trace.json.gz'
        trace=mod.read(path);assert mod.PINS[str(path)]==earlier['input_sha256'][str(path)]
        out['input_sha256'].update(mod.PINS)
        shares=earlier['arms'][case]['pre2700_shares']
        budgets={}
        for row in earlier['arms'][case]['frozen_budget_rows']:
            q=row['inferred_frozen_conflict_all_lane_mean_vph']*4
            budgets[row['time_sec']]=[min(row['canonical_total']/2,
                erlang_opportunities_vph(q*shares[j],3.5,1.5,shapes[j]['shape'])/3600) for j in (0,1)]
        observed=original['arms'][case]['observed']
        out['arms'][case]=dict(actual=feedback['arms'][case]['actual'],
            old=feedback['arms'][case]['original'],poisson_connected=feedback['arms'][case]['connected_model_arrivals'],
            erlang_model_arrivals=mod.replay(trace,observed,'baseline',receiving_by_second=budgets),
            erlang_native_arrivals=mod.replay(trace,observed,'native_arrival_timing_and_lane',receiving_by_second=budgets))
    for path,digest in out['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    out['local_ramp_replays']=4
    assert out['local_ramp_replays']<=protocol['max_local_ramp_replays']
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(shapes=shapes,arms={arm:{m:{k:(v[k]['connector_veh'] if isinstance(v[k],dict) else v[k]) for k in ('head','merge','final_stock')} for m,v in data.items()} for arm,data in out['arms'].items()})))


if __name__=='__main__':main()
