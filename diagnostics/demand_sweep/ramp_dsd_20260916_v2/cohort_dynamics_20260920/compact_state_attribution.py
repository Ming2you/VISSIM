"""Separate compact-state propagation from boundary uncertainty.

Future-state/boundary rows are explicit diagnostic oracles, never controller
inputs. The causal case exactly replays the saved local30s pilot.
"""
from pathlib import Path
from collections import Counter
import sys,copy,math,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import compact_lane_state as m
d=m.d


def advance(states,entries,start,geo,model,rho_max,mode):
    state=copy.deepcopy(states[start]);source=sum(entries[t] for t in range(start-29,start+1))/30
    initial=sum(state[c]['n'] for c in m.CELLS);cumulative_in=0.;cumulative_out=0.
    trace=[];projections=Counter()
    for dt in range(1,31):
        current=start+dt-1
        if mode in ('aux_oracle','both_oracle'):
            for c in m.CELLS:
                for field in m.FIELDS[1:]:state[c][field]=states[current][c][field]
        rate=source
        if mode in ('boundary_oracle','both_oracle'):
            state[14]=copy.deepcopy(states[current][14]);rate=entries[start+dt]
        result,ps=m.rollout(state,rate,geo,model,rho_max,1)
        row=result[0];assert row['inlet_queue']==0, 'Need persistent queued-boundary state before testing this case'
        cumulative_in+=rate;cumulative_out+=row['cumulative_terminal'];projections.update(ps)
        state=row['cells']
        residual=sum(state[c]['n'] for c in m.CELLS)+cumulative_out-initial-cumulative_in
        assert abs(residual)<1e-7
        trace.append(dict(time_s=start+dt,cells=copy.deepcopy(state),mass_residual=residual))
    return trace,dict(projections)


def main():
    out=d.HERE/'compact_state_attribution_v1';out.mkdir(exist_ok=False)
    source=d.HERE/'compact_lane_state_v1/result.json';doc=d.e.load(source)
    bp=d.HERE/'compact_lane_state_v1/states.json';raw=d.e.load(bp)
    banks={a:({int(t):{int(c):r for c,r in row.items()} for t,row in x['states'].items()},
              {int(t):v for t,v in x['entry'].items()}) for a,x in raw.items()}
    gp=d.H/'controller_response_s23_v1/none/geometry.json'
    geo={r['cell']:r for r in d.e.load(gp)['cells'] if r['road']=='FW_E'}
    results=[];exact=0
    for saved in doc['autonomous_runs']:
        assert saved['status']=='completed'
        arm,start,name=saved['arm'],saved['start_s'],saved['model'];states,entries=banks[arm]
        model=doc['models'][name]
        modes=('causal','boundary_oracle') if name=='coarse' else ('causal','aux_oracle','boundary_oracle','both_oracle')
        for mode in modes:
            trace,projections=advance(states,entries,start,geo,model,doc['rho_max'],mode)
            if mode=='causal':
                assert {str(k):v for k,v in trace[-1]['cells'].items()}==saved['final_cells']
                assert projections==saved['projections'];exact+=1
            ev=[];en=[];extras={f:[] for f in m.FIELDS[1:]}
            for row in trace:
                actual=states[row['time_s']]
                for c in m.CELLS:
                    ev.append(row['cells'][c]['v']-actual[c]['v']);en.append(row['cells'][c]['n']-actual[c]['n'])
                    for f in extras:extras[f].append(row['cells'][c][f]-actual[c][f])
            rmse=lambda xs:math.sqrt(sum(x*x for x in xs)/len(xs))
            results.append(dict(arm=arm,start_s=start,model=name,mode=mode,speed_rmse=rmse(ev),
                n_mae=sum(abs(v) for v in en)/len(en),aux_rmse={f:rmse(xs) for f,xs in extras.items()},
                projections=projections,max_mass_residual=max(abs(x['mass_residual']) for x in trace),
                oracle=mode!='causal',operational_candidate=False))
    # Causal forecasts must be unchanged if future observed scoring states and
    # future boundary entries are replaced. Only labels/oracles may change.
    states,entries=banks['none'];changed=copy.deepcopy(states);e2=dict(entries)
    for t in range(2401,2431):
        e2[t]=999.
        for c in changed[t]:
            for f in m.FIELDS:changed[t][c][f]=999.
            changed[t][c]['n']=999.
    for name,model in doc['models'].items():
        a=advance(states,entries,2400,geo,model,doc['rho_max'],'causal')
        b=advance(changed,e2,2400,geo,model,doc['rho_max'],'causal')
        assert a==b
    files=[Path(__file__),Path(m.__file__),source,bp,gp]
    d.e.save(out/'result.json',dict(status='COMPACT_PILOT_ATTRIBUTION_NOT_QUALIFIED',results=results,
        exact_causal_replays=exact,future_state_boundary_canary_models=2,
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        limitations=['Oracle modes diagnose omissions; they are not permissible online inputs or gain qualification.',
            'Auxiliary fractions taken from actual stock need not equal the predicted stock distribution; oracle is not a conserved microscopic state.',
            'The entire experiment is a local6-cell30s gate; full component interactions/cost and450s gain remain outstanding.'],
        production_changes=0,new_native_runs=0,qualified=False))
    print('EXACT_CAUSAL',exact,flush=True)
    for arm in banks:
        print(arm,[(r['start_s'],r['mode'],round(r['speed_rmse'],3)) for r in results if r['arm']==arm and r['model']=='compact'],flush=True)


if __name__=='__main__':main()
