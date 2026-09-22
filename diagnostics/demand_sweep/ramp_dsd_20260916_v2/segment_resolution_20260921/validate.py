"""Qualify geometry and numerical records separately from control benefit."""
from pathlib import Path
import copy, hashlib, json, math, sys
from collections import Counter,defaultdict
B=Path(__file__).resolve().parent;H=B.parent;K=H/'cohort_dynamics_20260920';ROOT=H.parents[2]
sys.path.insert(0,str(B));from prepare import mesh,save,table,native

def main():
    source=native.G;geo=json.loads((B/'geometry_200_branch_guard.json').read_text());parents=json.loads((B/'parent_map.json').read_text())
    assert mesh(source,200,100)[0]==geo
    from evaluation.controllers.freeway_geometry import geometry_fingerprint
    assert geometry_fingerprint(source)==geometry_fingerprint(geo)
    for road,ps in parents.items():
        assert len(ps)==31 and set(source['bounds'][road])<=set(geo['bounds'][road])
        cells=[r for r in geo['cells'] if r['road']==road]
        assert all(abs(c['length_km']*1000-(c['end_m']-c['start_m']))<1e-7 for c in cells)
        assert all(a['end_m']==b['start_m'] for a,b in zip(cells,cells[1:]))
    counts=Counter((p['road'],p['to_cell'] if p['kind']=='ramp' else p['from_cell']) for p in geo['boundaries'] if p['kind'] in ('ramp','offramp'))
    assert len(counts)==16 and max(counts.values())==1
    for arm in ('none','rm_ramp','vsl','both'):
        assert json.loads((B/f'reference5_{arm}.json').read_text())==json.loads((K/f'runtime5s_20260921_step5/prediction_{arm}.json').read_text())
    harness=ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py'
    # Retain the exact line-ending-only intermediate executed by the first
    # three batches; it has the identical Python AST to the final source.
    lf=harness.read_bytes().replace(b'\r\n',b'\n')
    (B/'canonical_harness_executed_lf.py.txt').write_bytes(lf)
    pin_checks=0
    for mode in ('reference5','reference1','refined1','refined_guard1'):
        protocol=json.loads((K/f'segment_resolution_20260921_{mode}/protocol.json').read_text())
        for path,expected in protocol['source_pins'].items():
            actual=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
            if actual!=expected:
                assert Path(path).name=='canonical_harness.py' and hashlib.sha256(lf).hexdigest()==expected
            pin_checks+=1
    records=[];results={};first_invalid=None
    for mode in ('reference5','reference1','refined1','refined_guard1'):
        mg=source if mode.startswith('reference') else json.loads((B/('geometry_200_branch_guard.json' if mode=='refined_guard1' else 'geometry_200.json')).read_text())
        L={(c['road'],c['cell']):c['length_km'] for c in mg['cells']}
        dt=5 if mode=='reference5' else 1
        for arm in ('none','rm_ramp','vsl','both'):
            p=json.loads((B/f'{mode}_{arm}.json').read_text());nchecks=0;vmax=0.;cfl=0.;maxres=0.
            for d in p['diagnostics']['roads']:
                assert d['negative_density_count']==d['jam_density_exceedance_count']==0
                assert d['continuity_residual_max_veh']<1e-7;maxres=max(maxres,d['continuity_residual_max_veh'])
                assert len(d['vsl_binding_audit']['cells'])==(21 if mode.startswith('reference') else 31)
                for r in d.get('branch_partition_trace',[]):
                    c=next(c for c in mg['cells'] if c['road']=='FW_E' and c['cell']==r['cell'])
                    off=next(o for o in mg['boundaries'] if o['connector']==10643)
                    for side,length in [('pre',off['chain_pos_m']-c['start_m']),('post',c['end_m']-off['chain_pos_m'])]:
                        v=r[side+'_v'];vmax=max(vmax,v);cfl=max(cfl,v*dt/(3.6*length))
                        if mode=='refined1' and arm=='none' and v>180 and first_invalid is None:first_invalid=dict(time_s=r['time_s'],cell=r['cell'],group=r['group'],side=side,length_m=length,speed_kmh=v)
            for r in p['lane_groups']['FW_E']:
                vmax=max(vmax,r['v_kmh']);cfl=max(cfl,r['v_kmh']*dt/(3600*L['FW_E',r['cell']]));nchecks+=1
                assert r['n_veh']>=-1e-8 and math.isfinite(r['v_kmh'])
            for r in p['ports']+p['ramps']:assert abs(r['conservation_residual_veh'])<1e-7
            valid=vmax<=180 and cfl<=1+1e-8
            if mode!='refined1':assert valid,(mode,arm,vmax,cfl)
            records.append(dict(mode=mode,arm=arm,group_state_checks=nchecks,max_speed_kmh=vmax,max_advective_courant=cfl,
                max_conservation_residual_veh=maxres,numerical_screen_pass=valid))
        result=json.loads((K/f'segment_resolution_20260921_{mode}/result.json').read_text())
        q=result['summaries']['none']
        results[mode]=dict(deltas=result['deltas'],east_speed_rmse=q['score']['speed']['rmse'],east_state_score=q['score']['objective'],west_state_score=q['west_state_score']['objective'],
            simulation_seconds=json.loads((B/f'{mode}_receipt.json').read_text())['seconds'])
    table(B/'numerical_checks.csv',records)
    save(B/'validation.json',dict(status='GEOMETRY_VERIFIED_GAIN_NOT_QUALIFIED',old_reference_predictions_exact=4,source_pins_verified=pin_checks,
        all_ports=16,max_ports_per_cell=1,cells_per_direction=31,native_runs=0,offline_forecasts=16,
        initial_N_and_Nv_verified_in_install=True,future_state_resets=0,coefficient_fit_evaluations=0,
        first_candidate_status='INVALID_NUMERICAL_RESPONSE',first_invalid_internal_state=first_invalid,
        guarded_mesh_status='CONSERVATION_AND_NUMERICAL_SCREEN_PASS_GAIN_FAIL',
        numerical_screen_note='Courant<=1 and loose180km/h sanity screen; not a fitted speed cap or proof of all stability properties.',
        production_adopted=False,results=results,records=records,
        source_pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [harness,K/'urban_route_transport.py',B/'prepare.py',B/'run.py',B/'analyze_space.py',B/'geometry_200_branch_guard.json']}))
    print('Validation PASS:16 exclusive ports,4 exact defaults; guarded mesh physically checked, gain gate failed.',flush=True)

if __name__=='__main__':main()
