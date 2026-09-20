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


if __name__=='__main__':main()
