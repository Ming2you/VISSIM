"""Verify bounded evidence from the failed resolution probe; never qualify it."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import compare_body_resolution_prefix as c

B,e=c.B,c.e


def main():
    comparison=e.load(B/'prefix_resolution_comparison/result.json')
    assert not comparison['qualified'] and not comparison['full_resolution10_run_completed']
    pins=0
    for data in (comparison,e.load(B/'analysis_res1/result.json'),e.load(B/'analysis_res10_prefix1500p1/result.json')):
        for name,digest in data['source_pins'].items():
            source=c.a.a.d.ROOT/name
            choices=[source]
            if source.name=='analyze_body_resolution.py':choices.append(B/'source_before_analyze_run_selection.py')
            assert any(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p in choices),name
            pins+=1
    assert e.load(B/'reference_original20_prefix.json')==e.load(B/'analysis_res1/result.json')['prefix']
    for resolution,name in ((1,'analysis_res1'),(10,'analysis_res10_prefix1500p1')):
        data=e.load(B/name/'result.json');rows=e.load(B/name/'series.json');pairs=e.load(B/name/'overlaps.json')
        assert all(abs(b['t']-a['t']-1)<1e-8 for a,b in zip(rows,rows[1:]))
        limit=1500 if resolution==1 else 1500.1
        for saved in comparison['arms'][str(resolution)]['windows']:
            lo,hi=(0,900) if saved['window']=='before900' else (900,limit+1e-7)
            selected=[r for r in rows if lo<=r['t']<hi]
            events=[r for r in pairs if lo<=r['t']<hi]
            hits=[r for r in events if r['rectangle_margin_m']>0]
            assert saved['samples']==len(selected)
            assert all('adjacent_pairs' in r or r['vehicles']<=3 for r in selected)
            assert saved['adjacent_pairs']==sum(r.get('adjacent_pairs',0) for r in selected)
            assert saved['slow_adjacent_pairs']==sum(r.get('slow_adjacent_pairs',0) for r in selected)
            assert saved['projected_overlaps']==len(events) and saved['rectangle_intersections']==len(hits)
            assert saved['slow_pair_rectangle_intersections']==sum(r['back']['v']<40 and r['front']['v']<40 for r in hits)
        observed=comparison['arms'][str(resolution)]['observations']
        assert sum(observed['first_observation_links'].values())==observed['observed_unique_network_vehicles']
        assert sum(observed['link24_arrival_windows'].values())==observed['observed_unique_link24_arrivals']
        if resolution==10:
            assert not data['native_validation_passed'] and data['failed_run_prefix_only'] and data['closed_prefix']
            assert data['terminal_s'] is None and data['sampling']['last_s']==1500.1
    terminal=e.load(B/'none_s23_res10/run_retry1/terminal_failure_confirmed.json')
    assert terminal['owned_processes_terminal'] and terminal['exec_exit_code']==1 and terminal['reason']=='disk_full'
    assert e.load(B/'disk_guard_validation.json')['prelaunch_rejection']
    core=['evaluation/controllers/physical_lane_groups.py','evaluation/controllers/physical_ramp_boundary.py',
          'evaluation/controllers/vissim_stackelberg_adapter.py','diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    for name in core:assert subprocess.check_output(['git','show','1f378f3:'+name],cwd=c.a.a.d.ROOT)==(c.a.a.d.ROOT/name).read_bytes()
    for p in (Path(__file__),Path(c.__file__),Path(c.a.__file__)):ast.parse(p.read_text(encoding='utf-8'))
    report=dict(passed=True,qualified=False,source_pins=pins,windows_recomputed=4,
        original20_prefix_preserved=True,source_resolution10_failed_run=True,late_congestion_unobserved=True,
        phase_offset_s=.1,core_unchanged_from='1f378f3',new_native_runs_started=False,
        full_forecasts_recomputed=False,completion_unproven=True)
    destination=B/'prefix_resolution_comparison/verification.json'
    if destination.exists():assert e.load(destination)==report
    else:e.save(destination,report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
