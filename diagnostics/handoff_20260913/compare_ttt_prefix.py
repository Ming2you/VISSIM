"""Measure the interrupted seed13 native prefix; never certify a complete run."""
from pathlib import Path
import csv
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnostics.analyze_no_control_corridors import native_frames
from scripts.measure_control_area import Frame, Vehicle, measure_frames, physical_membership_from_ledger, terminal_lengths, state_frame

D = ROOT / 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
OUT = Path(__file__).parent / 'ttt_prefix8850'
CL = ROOT / 'evaluation/runs/codex_fid_cl9000_s13_v3'
NC = ROOT / 'evaluation/runs/codex_phys8_fidelity_fw080_u050_nc9000_s13_v1'

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def pin(p):
    return {'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}

def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    started = time.perf_counter()
    cp, np = CL / ('run_provenance_' + CL.name + '.json'), NC / ('run_provenance_' + NC.name + '.json')
    c, n = read(cp), read(np)
    assert c['seed'] == n['seed'] == 13
    assert all(c['files'][k]['sha256'] == n['files'][k]['sha256'] for k in ('network', 'demand_profile'))
    receipt = read(NC / 'completion_receipt.json')
    assert receipt['completed'] and receipt['native_execution_passed'] and not receipt['errors']
    membership_path = ROOT / 'diagnostics/control_area_membership.json'
    document = read(membership_path)
    membership = physical_membership_from_ledger(document)
    assert len(membership) == 1236 and sum(membership.values()) == 635
    fzp = CL / 'vissim_eval/baseline_001.fzp'
    stat = (fzp.stat().st_size, fzp.stat().st_mtime_ns)
    evidence, final = {}, None
    def frames():
        nonlocal final
        for sec, rows in native_frames(fzp, evidence, deadline=time.monotonic() + 1800):
            assert 1 <= sec <= 8850
            final = Frame(float(sec), {str(k): Vehicle(str(v[0]), v[2], v[3]) for k, v in rows.items()})
            yield final
    metrics, series = measure_frames(frames(), membership, terminal_lengths(document), end_sec=8850, max_tail_extrap_sec=0, simulation_step_sec=1)
    assert stat == (fzp.stat().st_size, fzp.stat().st_mtime_ns)
    assert metrics['boundaries']['last_fzp_sec'] == 8850 and metrics['boundaries']['unobserved_tail_sec'] == 0
    assert metrics['sampling']['missing_snapshot_gaps'] == 0
    sp = CL / ('decisions_' + CL.name) / 'state_008850.json'
    snapshot = state_frame(sp, 8850, expected_run_id=c['run_id'], expected_manifest_path=cp)
    final_check = {'fzp_vehicles':len(final.vehicles), 'com_vehicles':len(snapshot.vehicles),
        'missing_from_fzp':sorted(set(snapshot.vehicles)-set(final.vehicles)),
        'fzp_only_ids':sorted(set(final.vehicles)-set(snapshot.vehicles))}
    baseline_csv = D / 'fidelity_nc9000_s13_full_v1/area_timeseries.csv'
    baseline_metrics = read(D / 'fidelity_nc9000_s13_full_v1/area_metrics.json')
    assert baseline_metrics['boundaries']['unobserved_tail_sec'] == 0 and baseline_metrics['sampling']['missing_snapshot_gaps'] == 0
    with baseline_csv.open(encoding='utf-8-sig', newline='') as f:
        baseline = {float(row['sim_sec']):row for row in csv.DictReader(f)}
    controlled = {float(row['sim_sec']):row for row in series}
    comparisons = {}
    for start in (0,900):
        nc_ttt = float(baseline[8850]['ttt_veh_h_cumulative']) - (float(baseline[start]['ttt_veh_h_cumulative']) if start else 0.0)
        cl_ttt = float(controlled[8850]['ttt_veh_h_cumulative']) - (float(controlled[start]['ttt_veh_h_cumulative']) if start else 0.0)
        comparisons[str(start)+'_8850'] = {'no_control_ttt_veh_h':nc_ttt,'control_ttt_veh_h':cl_ttt,
            'control_minus_no_control_veh_h':cl_ttt-nc_ttt,'ttt_reduction_percent':100*(nc_ttt-cl_ttt)/nc_ttt}
    result = {'schema':'interrupted-native-prefix-comparison/v1','full_run_completed':False,
        'native_execution_certified':False,'scope':'Observed native 0–8850s prefix; no completion receipt, final LDP/ERR verification remains unavailable. Final vehicles remain censored; no tail extrapolation.',
        'comparisons':comparisons,'last_frame_vs_com':final_check,'boundaries':metrics['boundaries'],
        'sampling':metrics['sampling'],'fzp':{'path':fzp.relative_to(ROOT).as_posix(), **evidence},
        'sources':[pin(p) for p in (cp,np,sp,membership_path,baseline_csv,Path(__file__))],
        'elapsed_sec_not_benchmark':time.perf_counter()-started}
    OUT.mkdir()
    (OUT/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'area_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'area_timeseries.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(series[0])); w.writeheader(); w.writerows(series)
    print(json.dumps({'comparisons':comparisons,'last_frame_vs_com':final_check,'sampling':metrics['sampling']},ensure_ascii=False))

if __name__ == '__main__':
    main()
