"""Combine retained prefix proofs and small completed-run evidence; no FZP scan."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostics.audit_observer_control_pair import command_rows,native_signal_prefix

RUNS={
    'A':'codex_area_observed_nc_s13_20260910',
    'B':'codex_contract_observed_nc_s13_1050_v2_20260910',
    'C':'codex_contract_nc_headoff_stepwise_s13_1050_v3_20260910',
    'D':'codex_contract_nc_headoff_continuous_s13_1050_v3_20260910'}


def sha(blob):return hashlib.sha256(blob).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve()
    if not out.is_relative_to(ROOT/'diagnostics') or out.exists():raise ValueError('New diagnostic output required')
    source_proofs={};payloads={}
    for name in ('observer_smoke_v2_complete.json','observer_head_off_v3_vs_on_v2_prefix1050.json',
                 'observer_continuous_v3_vs_stepwise_v3_prefix1050.json'):
        path=ROOT/'diagnostics'/name;blob=path.read_bytes();source_proofs[str(path)]=sha(blob)
        document=json.loads(blob)
        for row in document['trajectory']['payloads']:
            path=Path(row['path']);stat=path.stat();run=path.parent.parent.name
            if (stat.st_size,stat.st_mtime_ns)!=(row['file_size_observed'],row['mtime_ns']):
                raise ValueError('Cached native prefix source stat changed: '+run)
            if run in payloads and payloads[run]!=row:raise ValueError('Conflicting cached prefix evidence')
            payloads[run]=row
    if set(payloads)!=set(RUNS.values()):raise ValueError('Four named native prefixes required')
    cases={};commands={};native={};manifests={}
    for label,name in RUNS.items():
        run=ROOT/'evaluation/runs'/name
        log_path=run/f'runlog_{name}.txt';log_blob=log_path.read_bytes();log=log_blob.decode('utf-8',errors='replace')
        if 'STAGE=SIM_DONE' not in log:raise ValueError('Incomplete named run')
        path=run/f'run_provenance_{name}.json';blob=path.read_bytes();manifest=json.loads(blob);manifests[label]=manifest
        command_path=run/f'action_{name}.csv';commands[label]=command_rows(command_path,1050)
        native[label]=native_signal_prefix(next(run.glob('vissim_eval/*.lsa')),1050)
        source_copy=run/'area_candidate_source_manifest.json'
        snapshots=[]
        for path in sorted((run/f'decisions_{name}').glob('state_*.json')):
            raw=json.loads(path.read_bytes())
            if raw['sim_sec']<=1050:
                local=raw['local_observation']
                snapshots.append({'sim_sec':raw['sim_sec'],'head_window_present':'signal_observation_window' in local,
                                  'legacy_queue_window_samples':local['queue_window_samples']})
        cases[label]={'run':name,'run_id':manifest['run_id'],'seed':manifest['seed'],
            'requested_sim_period_sec':manifest['sim_period_sec'],'controller':manifest['controller'],
            'run_mode':re.findall(r'^RUN_MODE=(.*)',log,re.M),
            'head_transport':manifest['env'].get('RW_SIGNAL_OBSERVATION','absent in pre-feature runner'),
            'manifest_sha256':sha(blob),'source_manifest_sha256':sha(source_copy.read_bytes()),
            'run_log_sha256':sha(log_blob),'action_csv_sha256':sha(command_path.read_bytes()),
            'applied_times':list(commands[label]),'command_rows_per_apply':{k:len(v) for k,v in commands[label].items()},
            'native_signal_prefix':{k:v for k,v in native[label].items() if k!='groups'},
            'native_trajectory_prefix':payloads[name],'snapshots':snapshots}
    baseline=commands['A']['900.0']
    action_value_equal={key:all(rows==baseline for rows in groups.values()) for key,groups in commands.items()}
    comparisons={}
    fields=('header','payload_sha256','rows','payload_bytes','first_sec','last_sec')
    for left,right in (('A','B'),('A','C'),('A','D'),('B','C'),('B','D'),('C','D')):
        x,y=payloads[RUNS[left]],payloads[RUNS[right]]
        comparisons[left+'_'+right]={
            'ordered_native_trajectory_prefix_exact':all(x[k]==y[k] for k in fields),
            'native_signal_event_prefix_exact':native[left]['raw_event_sha256']==native[right]['raw_event_sha256'],
            'applied_schedule_equal':set(commands[left])==set(commands[right]),
            'every_applied_vector_equal_reference900':action_value_equal[left] and action_value_equal[right]}
    result={'schema':'observer-four-condition-comparison/v1','cases':cases,'comparisons':comparisons,
        'cached_prefix_proof_sha256':source_proofs,'fzp_bytes_read_by_this_summary':0,
        'proof_policy':'Original streaming prefix digests are retained and current raw file size/mtime checked. Native LSA and applied commands are re-read as small completed evidence.',
        'interpretation':['The three requested1050-second runs B/C/D have identical native trajectories, despite collector ON/OFF and stepwise/continuous differences.',
            'All four runs have identical native signal state-change prefixes and equal applied physical vectors. Continuous runs apply at1/900; stepwise runs also apply every150 seconds.',
            'The existing5400-second reference differs in52 position/speed/delay rows from1031 onward. The observed distinction aligns with short versus long run groups; horizon-only causality remains unproven because the historical reference uses an earlier software build.',
            'Use an observed1050-second NC for the matching1050-second control smoke. Do not use the old5400 prefix as an exact zero-treatment trajectory oracle for that shorter run.',
            'B vs C proves this NoControl trajectory result while the model source and launcher revisions are separately recorded; it does not claim unchanged MPC actions or identical model observation windows.'],
        'remaining_optional_experiment':'If strict horizon-only attribution or a new long-run baseline is necessary, run the current build at5400 with the intended baseline execution/observer settings and compare its first1050 prefix. This was not executed by this summary.',
        'producer_sha256':sha(Path(__file__).read_bytes())}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(out),'comparisons':comparisons}))


if __name__=='__main__':main()
