"""Verify saved speed-error ledgers without native re-extraction or forecasts."""
from pathlib import Path
import ast
import hashlib
import json
import math
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import velocity_ledger_audit as a

K,e,s=a.K,a.e,a.s


def close(x,y):
    assert math.isfinite(x) and math.isfinite(y) and abs(x-y)<1e-8,(x,y)


def main():
    result=e.load(a.OUT/'result.json');bins=e.load(a.OUT/'bin_ledger.json');cells=e.load(a.OUT/'cell_ledger.json')
    mechanism=e.load(K/'velocity_ledger_mechanism_v1/result.json')
    pins=0
    for data in (result,mechanism):
        assert not data['qualified'] and data['new_native_runs']==0
        for name,digest in data['source_pins'].items():
            assert hashlib.sha256((s.d.ROOT/name).read_bytes()).hexdigest()==digest,name
            pins+=1
    assert not result['unavailable'] and result['max_mass_residual']<1e-8
    assert len(bins)==result['bin_rows'] and len(cells)==result['cell_rows']==2160
    assert {(r['arm'],r['start'],r['t'],r['cell']) for r in cells}=={
        (arm,start,t,cell) for arm in ('none','rm_ramp','vsl') for start in a.STARTS
        for t in range(start,start+30) for cell in s.CELLS}
    for row in bins:
        native,model=row['actual'],row['model']
        assert native['missing_current']==0 and sum(native['transitions'].values())==row['n']
        close(native['carrier']+native['reaction'],native['observed_v'])
        close(model['actual_function_value']-native['observed_v'],row['error'])
        close(row['mixing_error']+row['reaction_error'],row['error'])
        close(row['model_reaction'],row['relaxation']+row['pressure']+model['convection']+row['floor_correction'])
    for row in cells:
        close(row['prediction']['v']-row['actual']['v'],row['error'])
        close(row['mixing_error']+row['reaction_error']+row['composition_weight_error'],row['error'])
    for summary in result['summaries']:
        def select(r):return r['arm']==summary['arm'] and r['start']==summary['start'] and (summary['scope']=='all15_20' or r['cell']==16)
        for name,rows,weight in (('bins',bins,'n'),('cells',cells,'weight')):
            actual=a.statistics([r for r in rows if select(r)],summary[name]['terms'],weight)
            assert actual==summary[name]
    # Synthetic mixture: one retained vehicle and one arriving from cell14.
    spatial=[dict(start=0.,length=.1),dict(start=100.,length=.1)]
    now={1:dict(x=20.,cell=15,lane=1,v=40.),2:dict(x=90.,cell=15,lane=1,v=80.),3:dict(x=-1.,cell=14,lane=1,v=50.)}
    nxt={1:dict(x=32.,cell=15,lane=1,v=42.),2:dict(x=111.,cell=15,lane=1,v=79.),3:dict(x=14.,cell=15,lane=1,v=53.)}
    test=a.labels(now,nxt,spatial)
    assert test[0,0]['carrier']==45. and test[0,0]['reaction']==2.5 and test[0,0]['observed_v']==47.5
    assert test[0,0]['transitions']=={'same_bin_lane':1,'upstream_entry':1}
    assert test[1,0]['transitions']=={'longitudinal':1}
    missing=a.labels({},nxt,spatial)
    assert all(v['missing_current']==v['n'] and 'carrier' not in v for v in missing.values())
    first=0
    for arm in ('none','rm_ramp','vsl'):
        for start in a.STARTS:
            old=e.load(K/f'target_acceleration_coupling_v1/{arm}_{start}_base.json')[0]
            for row in cells:
                if row['arm']==arm and row['t']==start and row['start']==start:
                    assert row['prediction']==old['cells'][str(row['cell'])]
                    first+=1
    assert first==72
    cases=e.load(K/'velocity_ledger_mechanism_v1/current_vehicle_cases.json')
    for row in cases:
        assert row['n_current']==len(row['vehicles'])
        assert all(v['v']>=0 and math.isfinite(v['x']) for v in row['vehicles'])
    core=['evaluation/controllers/physical_lane_groups.py','evaluation/controllers/physical_ramp_boundary.py',
        'evaluation/controllers/vissim_stackelberg_adapter.py',
        'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    for name in core:assert subprocess.check_output(['git','show','a5dcbd3:'+name],cwd=s.d.ROOT)==(s.d.ROOT/name).read_bytes()
    for path in (Path(__file__),Path(a.__file__),K/'velocity_ledger_mechanism.py'):
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    report=dict(passed=True,qualified=False,source_pins=pins,bin_identities=len(bins),cell_identities=len(cells),
        complete_one_step_snapshots=360,summary_groups=len(result['summaries']),native_missing_rows=0,
        unchanged_first_cell_states=first,current_vehicle_case_rows=len(cases),synthetic_mixing_and_censoring=True,
        core_unchanged_from='a5dcbd3',native_started=False,forecasts_recomputed=False,
        previous_goal_turn='progress: model code and evidence delivered and remote hash verified',
        current_goal_turn='progress: mixing/response/weight ledger isolates local acceleration error',
        goal_status='active; NOT_QUALIFIED',completed_session='54170 exit0; mechanism execution also terminal exit0',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    destination=a.OUT/'verification.json'
    if destination.exists():assert e.load(destination)==report
    else:e.save(destination,report)
    print(json.dumps(report,indent=2))


def current_regional():
    """Verify current-law diagnosis from saved records; no new forecasts."""
    import numpy as np
    base=K.parent/'segment_resolution_20260921';out=base/'recovery_entry_ledger_v1'
    current=e.load(out/'continuous_result.json');sampled=e.load(out/'result.json')
    rows=e.load(out/'continuous_rows.json');sample=e.load(out/'rows.json')
    compact=e.load(K/'compact_lane_state_v1/states.json')
    pin_checks=0
    for record in (sampled,current):
        assert not record['qualified'] and not record['production_adopted']
        assert record['new_native_runs']==record['new_autonomous_forecasts']==record['fitted_parameters']==0
        assert record['canonical_reconstruction']['rows']==9000
        assert record['canonical_reconstruction']['max_absolute_kmh']<1e-8
        for name,digest in record['source_pins'].items():
            p=s.d.ROOT/name
            if record is sampled and p.resolve()==Path(a.__file__).resolve():p=out/'executed_sampled_source.py.txt'
            assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,(name,p)
            pin_checks+=1
    lookup={(r['arm'],r['t'],r['cell']):r for r in rows}
    expected={(arm,t,i) for arm in ('none','rm_ramp','vsl') for t in range(2280,2850) for i in range(26,30)}
    assert len(rows)==len(lookup)==6840 and set(lookup)==expected
    arrays={}
    for arm in ('none','rm_ramp','vsl'):
        with np.load(base/f'{arm}_s23_0.npz') as z:arrays[arm]={key:z[key] for key in ('n','mom')}
    for r in rows:
        arm,t,i=r['arm'],r['t'],r['cell'];j=t-2249;c=i-10;z=arrays[arm]
        now=compact[arm]['states'][str(t)][str(c)];later=compact[arm]['states'][str(t+1)][str(c)]
        assert later['history_coverage']==1. and later['n']==r['n']==z['n'][j+1,c].sum()
        close(now['v'],r['current_v']);close(later['v'],r['actual'])
        close(z['mom'][j+1,c].sum()/z['n'][j+1,c].sum(),r['actual'])
        close(later['acceleration'],r['actual_reaction'])
        close(r['carrier']+r['actual_reaction'],r['actual'])
        close(r['relaxation']+r['pressure'],r['model_reaction'])
        close(r['current_v']+r['convection']+r['model_reaction'],r['predicted'])
        close(r['predicted']-r['actual'],r['error'])
        close(r['mixing_error']+r['reaction_error'],r['error'])
        assert r['current_features']=={k:now[k] for k in r['current_features']}
    for r in sample:
        actual=lookup[r['arm'],r['t'],r['cell']]
        for key in r:
            if key=='current_features':continue
            if isinstance(r[key],(float,int)):close(r[key],actual[key])
            else:assert r[key]==actual[key]
    assert len(sample)==current['sampled_rows_exact']==1440
    max_summary_difference=0.
    def stats_equal(actual,expected):
        nonlocal max_summary_difference
        assert actual['rows']==expected['rows'] and actual['weight']==expected['weight']
        assert actual['terms'].keys()==expected['terms'].keys()
        for name,terms in actual['terms'].items():
            for key,value in terms.items():
                close(value,expected['terms'][name][key])
                max_summary_difference=max(max_summary_difference,abs(value-expected['terms'][name][key]))
    for entry in current['summaries']:
        selected=[r for r in rows if r['arm']==entry['arm'] and entry['start']<=r['t']<entry['start']+30
                  and (entry['scope']=='all26_29' or r['cell']==26)]
        stats_equal(a.statistics(selected,entry['stats']['terms'],'weight'),entry['stats'])
    for entry in current['phase_summary']:
        selected=[r for r in rows if r['arm']==entry['arm'] and r['cell']==26 and
                  (entry['condition']=='all' or ((r['current_features']['braking']>=.5)==(entry['condition']=='current_braking_ge_half')))]
        stats_equal(a.statistics(selected,entry['stats']['terms'],'weight'),entry['stats'])
        for eps,count in entry['counts_by_sign_threshold'].items():
            assert count==sum(r['actual_reaction'] < -float(eps) and r['model_reaction']>float(eps) for r in selected)
    before=e.load(out/'before_sources.json');core_count=0
    for name,digest in before.items():
        p=s.d.ROOT/name
        if p.resolve()==Path(a.__file__).resolve():p=out/'before_velocity_ledger_audit.py.txt'
        else:core_count+=1
        assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    # Original extraction and verification entry points are preserved verbatim
    # in AST form. Old historical hashes resolve to the retained source copy.
    for source,archive,names in ((Path(a.__file__),out/'before_velocity_ledger_audit.py.txt',('labels','statistics','main')),
                               (Path(__file__),out/'before_verify_velocity_ledger.py.txt',('main','close'))):
        def funcs(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef)}
        old,new=funcs(archive),funcs(source)
        assert all(old[n]==new[n] for n in names)
    receipt=dict(passed=True,qualified=False,source_pin_checks=pin_checks,
        native_stock_speed_reaction_identities=len(rows),continuous_sample_agreement=len(sample),
        summary_checks=len(current['summaries'])+len(current['phase_summary']),max_summary_roundtrip_error=max_summary_difference,
        original_helper_ast_preserved=True,unchanged_core_files=core_count,
        new_native_runs=0,new_autonomous_forecasts=0,production_adopted=False,
        failures_preserved=['scope_mismatch_failure.log','continuous_metadata_failure.log','partial_result_guard.log','continuous_result.failed.json','verification_float_failure.log'],
        metadata_recovery='NumPy integer conversion; saved rows reused exactly, only inexpensive equation checks repeated.',
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    e.save(out/'verification.json',receipt)
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='current-regional':current_regional()
    else:main()
