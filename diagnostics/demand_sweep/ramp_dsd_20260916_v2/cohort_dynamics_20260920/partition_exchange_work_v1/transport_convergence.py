"""Isolated numerical diagnostic, not a calibrated traffic forecast.

Compare the existing conserved transport against its constant-speed linear
two-compartment solution. Remove relaxation, anticipation and all lane changes
only in this manufactured case, to avoid confusing FD fit with time integration.
"""
from pathlib import Path
import sys,math,json,hashlib
HERE=Path(__file__).resolve().parent.parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.test_branch_partition import BranchPartitionTests
BranchPartitionTests.setUpClass();test=BranchPartitionTests();results=[]
for step in (10.,1.,.5):
    p,state,cfg=test.setup_partition(pre=0.,post=1.,pre_speed=100.,post_speed=100.)
    cfg.simulation.T_f=step;cfg.simulation.T_u=min(cfg.simulation.T_u,step)
    cfg.simulation.validate();p.sec=step;p.dt=step/3600
    assert abs(cfg.simulation.T_f_h-p.dt)<1e-12
    cfg.network.metanet_tau_h=1e12;cfg.network.metanet_nu_km2_h=0.;cfg.network.v_free=100.
    for row in p.v:
        for g in range(len(row)):row[g]=100.
    p.n[7][2]=10.
    tau7=p.lengths[7]*3600/100.;taupre=p.partitions[8]['pre_length']*3600/100.
    expected=10*taupre/(tau7-taupre)*(math.exp(-10/tau7)-math.exp(-10/taupre))
    # The installed anticipation selector can override the scalar nu=0.
    # Freeze the ODE explicitly in this manufactured transport-only case.
    speed_update=p.a._mn.metanet_speed_update_kmh
    p.a._mn.metanet_speed_update_kmh=lambda velocity,*args,**kwargs:velocity
    try:
        for _ in range(round(10/step)):
            test.advance(p,state,cfg,cap=0.)
            assert all(abs(v-100.)<1e-7 for v in (p.v[7][2],p.partitions[8]['pre_v'][2],p.partitions[8]['post_v'][2]))
    finally:p.a._mn.metanet_speed_update_kmh=speed_update
    total=sum(map(sum,p.n));assert abs(total-11.)<1e-7
    actual=p.partitions[8]['pre_n'][2]
    results.append(dict(step_s=step,pre_n=actual,analytic_pre_n=expected,error=abs(actual-expected),
        post_n=p.partitions[8]['post_n'][2],tau_pre_s=taupre,tau_upstream_s=tau7,
        residual=p.max_partition_residual,total_stock=total))
assert results[2]['error']<results[1]['error']<results[0]['error']
assert results[0]['post_n']==0 and results[1]['post_n']>0
out=Path(__file__).with_name('transport_convergence_v2.json');assert not out.exists()
result=dict(status='COMPLETE',manufactured_constant_speed_case=True,results=results,
    source_sha256=hashlib.sha256((ROOT/'evaluation/controllers/physical_lane_groups.py').read_bytes()).hexdigest(),
    traffic_gain_qualification=False,production_step_changed=False,
    supersedes='transport_convergence.json: invalid constant-speed assumption; actual speeds rose to107.54km/h because scalar nu=0 did not disable the configured anticipation selector.',
    every_step_speed_asserted_100kmh=True,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    conclusion='A10s step cannot resolve the6.34s residence scale of the176m partition;1s/.5s converge toward the same transport equation. This isolates numerical truncation, not nonlinear traffic or controller performance.')
with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
print(json.dumps(result,indent=2))
