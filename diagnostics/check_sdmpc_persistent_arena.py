"""Persistent numeric state and AD lifetime checks, not a plant performance claim."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.sdmpc_persistent_arena_probe import Arena,reference,QA,QB,TTT,COMPLETED
from evaluation.controllers import sdmpc_tangent_reverse as ad


def main():
    out=ROOT/'diagnostics/sdmpc_persistent_review_20260922/lifetime_v3'
    out.mkdir(parents=True,exist_ok=False)
    rows=[]
    arrivals=[(.13 if i%17 else .72) for i in range(450)]
    for cap,service,initial,controls in ((5.,.2,(1.,2.),(.3,.04,.6)),
            (.8,.05,(3.,.8),(.5,.5,.02)),(4.,.6,(0.,0.),(.0,.25,.0)),
            (4.,.6,(50.,0.),(.1,.12,.2))):
        traces=[];outputs=[]
        for compiled in (False,True):
            trace=ad.Trace([1.]*5)
            seeded=[ad.Dual(v,{j:1.},trace) for j,v in enumerate([*initial,*controls])]
            if compiled:
                arena=Arena(seeded[:2],seeded[2:],cap,service)
                snapshots=[];original_snapshot=None;frozen_prefixes=[]
                for step,arrival in enumerate(arrivals):
                    arena.advance(step,arrival)
                    if (step+1)%150==0:
                        for count,parents,weights in frozen_prefixes:
                            np.testing.assert_array_equal(arena.p[:count],parents)
                            np.testing.assert_array_equal(arena.w[:count],weights)
                        count=int(arena.c[0])
                        frozen_prefixes.append((count,arena.p[:count].copy(),arena.w[:count].copy()))
                        snapshots.append(arena.snapshot())
                        if step==149:original_snapshot=snapshots[0]['values'].copy()
                assert arena.exports==0
                assert arena.register_addresses==tuple(x.ctypes.data for x in (arena.v,arena.r,arena.k))
                assert np.array_equal(snapshots[0]['values'],original_snapshot)
                result=arena.export()
                assert arena.exports==1 and arena.growths>0
                for snap,expected in zip(snapshots,checkpoints):
                    np.testing.assert_array_equal(snap['values'],[ad.primal(v) for v in expected])
                # Adding a constant may legally preserve a derivative node ID
                # while changing its primal value. Test tape immutability above,
                # not a false one-to-one mapping between IDs and primal values.
                for action in (lambda:arena.advance(450,.1),arena.export):
                    try:action()
                    except ValueError:pass
                    else:raise AssertionError('Closed arena accepted reuse')
            else:
                checkpoints=reference(seeded[:2],seeded[2:],cap,service,arrivals)
                result=checkpoints[-1]
            traces.append(trace);outputs.append(result)
        for field in ('p1','p2','w1','w2','counts','exact_support','discrete_support'):
            assert getattr(traces[0],field)==getattr(traces[1],field),field
        matrices=[t.jacobian(v,workers=1) for t,v in zip(traces,outputs)]
        np.testing.assert_array_equal(*matrices)
        if initial==(50.,0.):
            assert np.all(np.abs(matrices[1][TTT,2:])>1.)
            np.testing.assert_allclose(matrices[1][QA,2:],[-150.,-150.,-150.],rtol=0.,atol=0.)
        rows.append(dict(capacity=cap,service=service,steps=450,blocks=3,stage_calls=1350,
            exact_values_all_three_checkpoints=True,exact_tape_and_jacobian=True,
            cross_block_control_gradient=matrices[1][TTT,2:].tolist(),
            stable_state_addresses=True,snapshot_immutable=True,tape_prefix_immutable=True,
            exports=1,tape_growths=arena.growths,
            nodes=len(traces[1].p1)-1,max_mass_residual=arena.conservation_error))
    # Separate candidates own separate state and graph buffers.
    a=Arena([1.,2.],[.2,.3,.4],4.,.2);b=Arena([1.,2.],[.2,.3,.4],4.,.2)
    old=b.snapshot()
    a.advance(0,.3)
    for field in ('v','r','k','p','w'):
        assert not np.shares_memory(getattr(a,field),getattr(b,field))
    np.testing.assert_array_equal(b.v,old['values'])
    try:b.advance(1,.3)
    except ValueError:pass
    else:raise AssertionError('Noncontiguous step accepted')
    paths=[Path(__file__),ROOT/'diagnostics/sdmpc_persistent_arena_probe.py',
        ROOT/'evaluation/controllers/sdmpc_tangent_spatial.py',ROOT/'evaluation/controllers/sdmpc_tangent_transport.py',
        ROOT/'evaluation/controllers/sdmpc_tangent_reverse.py']
    report=dict(scope=__doc__,pass_all=True,scenarios=rows,candidate_isolation=True,
        all_three_controls_reach_final_state_and_cost=True,
        native_applied=False,production_predictor_integrated=False,performance_measured=False,
        source_sha256={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
