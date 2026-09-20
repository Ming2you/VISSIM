"""Numerical/causality checks and an explicit physical-state rejection gate."""
from pathlib import Path
import sys,math,copy,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import compact_moment_transport as t
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import compact_state_attribution as a
m=t.m;d=m.d


def main():
    out=d.HERE/'compact_moment_transport_v1';docs={};pins=0
    for name in ('compact_lane_state_v1','compact_state_attribution_v1','compact_moment_transport_v1'):
        p=d.HERE/name/'result.json';doc=d.e.load(p);docs[name]=doc
        for path,h in doc['pins'].items():assert hashlib.sha256((d.ROOT/path).read_bytes()).hexdigest()==h;pins+=1
        assert not doc['qualified'] and doc['production_changes']==doc['new_native_runs']==0
    raw=d.e.load(d.HERE/'compact_lane_state_v1/states.json')
    banks={arm:({int(s):{int(c):v for c,v in row.items()} for s,row in data['states'].items()},
                {int(s):v for s,v in data['entry'].items()}) for arm,data in raw.items()}
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geo={r['cell']:r for r in d.e.load(gp)['cells'] if r['road']=='FW_E'}
    rho_max=docs['compact_lane_state_v1']['rho_max']
    # A uniform stream transports moments without creating a speed variance.
    uniform={c:dict(n=30.,v=72.,sd=4.,closing=2.,braking=.2,acceleration=-.1) for c in range(14,21)}
    rate=30*72/(geo[15]['length_km']*3600)
    adv,q,exits,accepted=t.transport(uniform,rate,0.,geo,rho_max)
    for c in m.CELLS:
        for f in m.FIELDS:assert abs(adv[c][f]-uniform[c][f])<1e-8
        assert abs(adv[c]['n']-30)<1e-8
    assert q==0 and abs(accepted-rate)<1e-8 and abs(exits-rate)<1e-8
    # Mixing two zero-variance streams must create exactly the mixture's
    # second central moment, while retaining vehicle counts.
    mixed=copy.deepcopy(uniform);mixed[14].update(v=36.,sd=0.);mixed[15].update(v=72.,sd=0.)
    adv,_,_,entered=t.transport(mixed,rate,0.,geo,rho_max)
    removed=30*72/(geo[15]['length_km']*3600);remaining=30-removed;n=remaining+entered
    expected_v=(remaining*72+entered*36)/n
    expected_var=(remaining*72**2+entered*36**2)/n-expected_v**2
    assert abs(adv[15]['v']-expected_v)<1e-10 and abs(adv[15]['sd']**2-expected_var)<1e-8
    # Current-boundary changes must not read future observational labels.
    nc,entry=banks['none'];copy_states=copy.deepcopy(nc);copy_entries=dict(entry)
    for s in range(2401,2431):
        copy_entries[s]=999.
        for c in copy_states[s]:copy_states[s][c]['v']=999.
    base=docs['compact_lane_state_v1']['models']['compact']
    assert a.advance(nc,entry,2400,geo,base,rho_max,'causal')==a.advance(copy_states,copy_entries,2400,geo,base,rho_max,'causal')
    # Persist explicit rejection, even though all arithmetic/mass computations
    # completed. For nonnegative vehicle speeds, mean0 implies variance0.
    pilot=docs['compact_moment_transport_v1'];model=pilot['models']['transported']
    physical_failures=[];mass_checks=0;final_replays=0
    for arm,(states,entries) in banks.items():
        for start in (2280,2400,2550,2700):
            state=copy.deepcopy(states[start]);rate=sum(entries[s] for s in range(start-29,start+1))/30
            queue=0.;exits=0.;n0=sum(state[c]['n'] for c in m.CELLS)
            for dt in range(1,31):
                state,queue,q,accepted,projections=t.step(state,rate,queue,geo,rho_max,model);exits+=q
                residual=sum(state[c]['n'] for c in m.CELLS)+queue+exits-n0-dt*rate
                assert abs(residual)<1e-7;mass_checks+=1
                for c in m.CELLS:
                    row=state[c]
                    if row['n']>1e-8 and row['v']<=1e-10 and row['sd']>1e-8:
                        physical_failures.append(dict(arm=arm,start_s=start,time_s=start+dt,cell=c,n=row['n'],
                            mean_speed=row['v'],speed_sd=row['sd'],reason='Nonnegative-speed population cannot have mean0 and positive variance'))
            saved=next(r for r in pilot['autonomous_runs'] if r['arm']==arm and r['start_s']==start and r['model']=='transported')
            assert {str(c):v for c,v in state.items()}==saved['final_cells'];final_replays+=1
    assert physical_failures,'Expected rejection case disappeared; review source/model changes'
    old=d.e.load(d.HERE/'transport_step_work_v1/checkpoint.json');core={}
    for path,h in old['sha256'].items():
        if path.startswith('evaluation') or path.endswith('canonical_harness.py'):
            assert hashlib.sha256((d.ROOT/path).read_bytes()).hexdigest()==h;core[path]=h
    result=dict(status='REJECTED_NONREALIZABLE_AUXILIARY_STATE',qualified=False,source_pin_checks=pins,
        numerical_checks_passed=dict(uniform_moment_transport=True,two_stream_variance=True,mass_steps=mass_checks,
            exact_transported_final_states=final_replays,attribution_exact_causal_cases=32,future_input_canary=True),
        physical_state_failures=physical_failures,failed_cases=sorted({(r['arm'],r['start_s']) for r in physical_failures}),
        interpretation='Numerical completion and mass conservation do not imply a valid speed distribution. Reject the empirical moment-reaction candidate; do not repair its scores by silently projecting variance.',
        core_hashes_unchanged=core,new_native_runs=0,production_changes=0,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    d.e.save(out/'validation.json',result)
    print(dict(status=result['status'],pins=pins,mass_checks=mass_checks,physical_failures=len(physical_failures),failed_cases=result['failed_cases']),flush=True)


if __name__=='__main__':main()
