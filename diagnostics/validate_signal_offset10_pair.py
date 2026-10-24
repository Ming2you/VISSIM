"""Validate the completed fixed-green/offset10 pair without touching its inputs."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUNS=[ROOT/'evaluation/runs'/name for name in ('codex_signal_zero_s13_20260910','codex_signal_offset10_s13_20260910')]


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    provenance=[read(run/f'run_provenance_{run.name}.json') for run in RUNS]
    shared_file_hashes={key:provenance[0]['files'][key]['sha256']==provenance[1]['files'][key]['sha256']
        for key in ('network','main_vbs_runner','adapter','control_mapping','generated_vbs_config','demand_profile','urban_input_gate_map')}
    assert all(shared_file_hashes.values()),shared_file_hashes
    scalar_equal={key:provenance[0][key]==provenance[1][key] for key in ('seed','sim_period_sec','control_interval_sec','demand_scale','demand_profile','audit_anchors_sec')}
    assert all(scalar_equal.values()),scalar_equal
    warmup={}
    for prefix in ('state','bottleneck_segments','bottleneck_links'):
        pathlist=[run/f'{prefix}_{run.name}.csv' for run in RUNS]
        # Wall duration is not a traffic state or experimental input.
        rr=[[{k:v for k,v in row.items() if k!='decision_wall_sec'} for row in rows(path) if float(row['sim_sec'])<=900] for path in pathlist]
        assert rr[0]==rr[1],prefix
        warmup[prefix]={'equal':True,'rows_each':len(rr[0])}
    command_paths=[run/f'decisions_{run.name}/action_000900.csv' for run in RUNS]
    cmd=[rows(path) for path in command_paths]
    assert len(cmd[0])==len(cmd[1])
    differences=[]
    for a,b in zip(*cmd):
        assert (a['kind'],a['id'],a['dsd_no'])==(b['kind'],b['id'],b['dsd_no'])
        diff={key:[a[key],b[key]] for key in a if key!='metadata' and a[key]!=b[key]}
        if diff:
            assert a['kind'] in ('signal','signal_sg') and a['sc_no'] in ('1001','1004') and set(diff)=={'offset'},(a,diff)
            differences.append({'kind':a['kind'],'id':a['id'],'sc':a['sc_no'],'changes':diff})
    assert len(differences)==18
    green_totals=[]
    for run in RUNS:
        total=Counter()
        for row in rows(run/'analysis/signal_seconds_from_readback.csv'):
            total[(row['sc'],row['sg'])]+=float(row['green'])
        green_totals.append(total)
    assert green_totals[0]==green_totals[1]
    metrics=[read(run/'analysis/area_metrics.json') for run in RUNS]
    for m in metrics:
        assert m['sampling']['nominal_step_sec']==1 and m['sampling']['missing_snapshot_gaps']==0
        assert m['boundaries']['first_fzp_sec']==1 and m['boundaries']['last_fzp_sec']==5400
        assert m['boundaries']['final_state_used'] is False
        assert m['closure']['max_abs_residual_veh']==0
    metric_delta={key:{'zero':metrics[0][key],'offset10':metrics[1][key],'delta':metrics[1][key]-metrics[0][key]} for key in
        ('ttt_veh_h','ttd_observed_exit_events','ttd_terminal_exit_inferred_events','ttd_observed_plus_terminal_events',
         'ttd_counted_unique_vehicle_ids','ttd_repeat_exit_events','unresolved_inside_disappearances')}
    physical=[{r['physical_link']:r for r in rows(run/'analysis/physical_link_residence.csv')} for run in RUNS]
    link_deltas=[]
    for key in set(physical[0])|set(physical[1]):
        a,b=(physical[i].get(key,{}) for i in range(2))
        va,vb=float(a.get('ttt_veh_h',0)),float(b.get('ttt_veh_h',0))
        marker=a.get('inside',b.get('inside'))
        link_deltas.append({'link':key,'inside':str(marker).lower() in ('true','1'),'zero_ttt':va,'offset10_ttt':vb,'delta':vb-va})
    errors=[read(run/'analysis/simulation_errors_summary.json') for run in RUNS]
    out={'scope':'Same seed13 fixed-green vector, t900 intervention; SC1001 +10, SC1004 -10, relative displacement20 seconds.',
         'same_recorded_source_hashes':shared_file_hashes,'same_settings':scalar_equal,'warmup_observation_tables':warmup,
         'same_actual_green_duration':{'equal':True,'signal_groups':len(green_totals[0]),'source':'analysis/signal_seconds_from_readback.csv','window_sec':[900,5400]},
         'command_differences':differences,'metrics':metric_delta,
         'TTT_percent_delta':100*(metrics[1]['ttt_veh_h']/metrics[0]['ttt_veh_h']-1),
         'inside_physical_ttt_delta_sum':sum(r['delta'] for r in link_deltas if r['inside']),
         'largest_inside_reductions':sorted((r for r in link_deltas if r['inside']),key=lambda r:r['delta'])[:10],
         'largest_inside_increases':sorted((r for r in link_deltas if r['inside']),key=lambda r:r['delta'],reverse=True)[:10],
         'simulation_errors':[{'event_counts':e['event_counts'],'inside_removed':e['lane_change_removal_inside'],'outside_removed':e['lane_change_removal_outside']} for e in errors],
         'sources':{str(p.relative_to(ROOT)):sha(p) for run in RUNS for p in
             [run/f'run_provenance_{run.name}.json',run/f'decisions_{run.name}/action_000900.csv',run/'analysis/area_metrics.json',
              run/'analysis/physical_link_residence.csv',run/'analysis/simulation_errors_summary.json']}}
    assert abs(out['inside_physical_ttt_delta_sum']-metric_delta['ttt_veh_h']['delta'])<1e-7
    target=ROOT/'diagnostics/signal_offset10_validation.json'
    target.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k in ('warmup_observation_tables','metrics','TTT_percent_delta','largest_inside_reductions','largest_inside_increases')},indent=2))


if __name__=='__main__':main()
