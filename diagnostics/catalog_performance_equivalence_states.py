"""Inventory recorded test inputs from small raw JSON and saved summaries only.

No controller imports, projection, endpoint, optimizer, VISSIM or FZP reads.
"""
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagnostics/performance_equivalence_state_catalog_20260910.json'
HEAD='codex_contract_observed_nc_s13_1050_v2_20260910'
SMOKE='codex_contract_beta300_s13_1050_v3_20260910'
SOURCE='codex_area_sources_beta0_s13_20260910'
NC='codex_contract_nc_headoff_continuous_s13_5400_v3_20260910'
OLD_NC='codex_area_observed_nc_s13_20260910'
CONFIG='diagnostics/contract_candidate_configs_v4/n7_area_beta300.json'
OFF_CONFIG='diagnostics/contract_observer_off_configs_v3/n7_area_beta300.json'

SELECTED=[
    (HEAD,'state',900,'primary_initial_head_observed'),
    (HEAD,'state',1050,'head_observed_short_run_end'),
    (SMOKE,'state',1050,'first_controlled_window_head_observed'),
    (SOURCE,'state',1200,'pre_onset_E8_queue'),
    (SOURCE,'state',1500,'sustained_E8_slow_onset'),
    (SOURCE,'state',3300,'severe_congestion'),
    (SOURCE,'state',3600,'near_stopped_E8'),
    (SOURCE,'state',4950,'local_W0_partial_recovery_only'),
    (SOURCE,'state',5100,'late_persistent_congestion'),
    (SOURCE,'state',5400,'terminal_censored_not_recovered'),
    (NC,'anchor',1500,'native_E8_onset'),
    (NC,'anchor',3600,'native_severe_congestion'),
    (NC,'anchor',4500,'native_late_persistent_congestion'),
    (NC,'anchor',5400,'native_terminal_censored_not_recovered')]
SOURCES={}


def relative(path):
    path=Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def read(path):
    path=Path(path);data=path.read_bytes()
    SOURCES[relative(path)]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    return json.loads(data)


def pin(path):
    data=Path(path).read_bytes();row={'path':relative(path),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    SOURCES[row['path']]={k:row[k] for k in ('sha256','bytes')}
    return row


def folder(run):return ROOT/'evaluation/runs'/run/('decisions_'+run)


def main():
    membership=read(ROOT/'diagnostics/control_area_membership.json');inside=set(membership['inside_links'])
    curves_path=ROOT/'diagnostics/source_run_comparison_complete/cell_curves.csv';pin(curves_path)
    curves=defaultdict(list)
    for row in csv.DictReader(curves_path.open(encoding='utf-8-sig',newline='')):
        curves[row['run'],int(float(row['sim_sec']))].append(row)
    summaries=[ROOT/'diagnostics/source_run_comparison_complete/comparison.json',
        ROOT/'diagnostics/source_run_comparison_complete/assessment.md',
        ROOT/'diagnostics/observed_nc_snapshot_audit_5400.json',
        ROOT/'diagnostics/current_nc_v3_vs_original_full5400_trajectory.json',
        ROOT/'evaluation/controllers/signal_head_observation.py',ROOT/'evaluation/controllers/head_service_resources.py']
    for path in summaries:pin(path)
    configs={}
    for key,path in [('primary_v4',CONFIG),('legacy_head_off',OFF_CONFIG)]:
        raw=read(ROOT/path);capacity=raw['urban']['capacity']
        configs[key]={**pin(ROOT/path),'head_observation':capacity.get('head_observation'),
            'head_resource_contract':capacity.get('head_resource_contract'),
            'physical_signal_contract':raw.get('urban',{}).get('physical_signal_contract')}
    run_catalog={};raw_cache={}
    for run in (HEAD,SMOKE,SOURCE,NC,OLD_NC):
        base=ROOT/'evaluation/runs'/run
        manifest_path=base/('run_provenance_'+run+'.json');manifest=read(manifest_path)
        paths=[p for p in folder(run).glob('*.json') if p.stem.startswith(('state_','anchor_'))]
        tuning=manifest['files']['tuning'];tuning_path=Path(tuning['path'])
        if not tuning_path.is_absolute():tuning_path=ROOT/tuning_path
        actual_tuning_sha=hashlib.sha256(tuning_path.read_bytes()).hexdigest() if tuning_path.exists() else None
        run_catalog[run]={'manifest':pin(manifest_path),'run_id':manifest['run_id'],
            'created_at':manifest['created_at'],'workspace_git_commit':manifest.get('workspace_git_commit'),
            'controller':manifest['controller'],'seed':manifest['seed'],'sim_period_sec':manifest['sim_period_sec'],
            'network':manifest['files']['network'],'recorded_tuning':tuning,
            'current_tuning_matches_recorded':actual_tuning_sha==tuning['sha256'],
            'current_tuning_sha256':actual_tuning_sha,'recorded_adapter':manifest['files']['adapter'],
            'recorded_vbs':manifest['files']['main_vbs_runner'],
            'head_declaration':manifest.get('signal_observation'),
            'recorded_head_env':manifest['env'].get('RW_SIGNAL_OBSERVATION'),
            'snapshot_inventory':sorted(p.name for p in paths)}
    records=[]
    for run,kind,time,label in SELECTED:
        path=folder(run)/f'{kind}_{time:06d}.json';raw=read(path);raw_cache[run,time]=raw
        if raw['sim_sec']!=time or raw['run_provenance']['run_id']!=run_catalog[run]['run_id']:
            raise ValueError('Snapshot identity mismatch')
        previous_candidates=[p for p in folder(run).glob('action_*.json') if int(p.stem.split('_')[-1])<time]
        previous=max(previous_candidates,key=lambda p:int(p.stem.split('_')[-1]))
        prior=read(previous);metadata={**prior.get('diagnostics',{}),**prior.get('metadata',{})}
        windows=raw['local_observation'].get('signal_observation_window')
        vehicles=raw['vehicle_records'];routes=raw.get('vehicle_routes',{})
        omega=sum(n for link,n in vehicles['full_network_link_counts'].items() if link in inside)
        fw=sum(c['count'] for cells in raw['freeway_segments'].values() for c in cells)
        selected_cells={f'{link}:{index}':{'count':cells[index]['count'],
            'speed_kph':cells[index]['speed_sum']/cells[index]['count'] if cells[index]['count'] else None}
            for link,index in [('FW_E',8),('FW_E',9),('FW_W',0)] for cells in [raw['freeway_segments'][link]]}
        series='target' if run==SOURCE else 'reference' if run==NC else None
        rows=curves.get((series,time),[])
        evidence={'series':series,'path':relative(curves_path),'time_sec':time,
            'observed_slow_cells_count':sum(float(r['count'])>=5 and float(r['mean_speed_kph'])<30 for r in rows)} if rows else None
        if rows and sum(float(r['count']) for r in rows)!=fw:raise ValueError('Stored summary and raw FW stock differ')
        record={'id':f'{run}:{time}','role':label,'run':run,'snapshot':pin(path),'sim_sec':time,
            'previous_action':pin(previous),'previous_action_sec':prior.get('metadata',{}).get('sim_sec'),
            'previous_head_metadata':{'candidate_rates':sum(k.startswith('head_candidate_rate_') for k in metadata),
                'legacy_floors':sum(k.startswith('head_discharge_floor_') for k in metadata),
                'observed_resource_floors':{k:v for k,v in metadata.items() if k.startswith('head_resource_observed_floor_')}},
            'raw':{'records_complete':vehicles['complete'],'records':vehicles['record_count'],
                'routes_complete':routes.get('complete'),'route_records':routes.get('record_count'),
                'omega_vehicles':omega,'freeway_vehicles':fw,'inside_nonfreeway_vehicles':omega-fw,
                'total_stopped_vehicles':raw['stopped_vehicles'],'freeway_mean_speed_kph':raw['freeway_mean_speed_kph'],
                'selected_cells':selected_cells,'queue_window_samples':raw['local_observation'].get('queue_window_samples')},
            'head_window':None if windows is None else {k:windows[k] for k in ('schema','config_sha256','start_sec','end_sec','transition_count','cadence_sec','clock_complete')},
            'summary_evidence':evidence,'remaining_recorded_horizon_sec':raw['sim_period_sec']-time,
            'allowed_pair_config':'primary_v4' if windows else 'legacy_head_off',
            'runtime_check_performed_here':False}
        records.append(record)
    # Read original anchors only at selected common times: no FZP rescan.
    native_identity=[]
    for time in (1500,3600,4500,5400):
        old_path=folder(OLD_NC)/f'anchor_{time:06d}.json';old=read(old_path);new=raw_cache[NC,time]
        native_identity.append({'time_sec':time,'old_snapshot':pin(old_path),
            'full_vehicle_record_object_exact':old['vehicle_records']==new['vehicle_records'],
            'route_record_object_exact':old['vehicle_routes']==new['vehicle_routes'],
            'freeway_segments_exact':old['freeway_segments']==new['freeway_segments']})
    profile=ROOT/'diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z/action.json'
    prof=read(profile);meta={**prof.get('diagnostics',{}),**prof.get('metadata',{})}
    initial_evidence={'action':pin(profile),'head_observation_prior_discarded':meta.get('head_observation_prior_discarded'),
        'resource_floors':{k:v for k,v in meta.items() if k.startswith('head_resource_observed_floor_')},
        'scope':'Existing recorded v4 main output, not rerun here. Both new managed resource floors are zero; do not call this an accumulated v4 resource-floor history.'}
    tail=[{'sim_sec':int(float(r['sim_sec'])),'speed_kph':float(r['mean_speed_kph']),'vehicles':float(r['count'])}
        for r in csv.DictReader(curves_path.open(encoding='utf-8-sig',newline='')) if r['run']=='target'
        and r['model_link']=='FW_W' and r['index']=='0' and 4740<=float(r['sim_sec'])<=5100]
    source_changes=[p for p,r in SOURCES.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=r['sha256']]
    report={'schema':'recorded-performance-equivalence-state-catalog/v1','catalog_scope':'Read-only small raw snapshots plus precomputed physical summaries. No model import/run or FZP scan.',
        'configs':configs,'runs':run_catalog,'states':records,'native_anchor_identity':native_identity,
        'primary_v4_existing_output':initial_evidence,'partial_W0_recovery_30s_samples':tail,
        'recovery_verdict':{'network_wide_recovery_recorded':False,'E8_recovery_recorded':False,
            'partial_local_example':'W0 target is below30 at4740/4770/4800, then above30 at4830..5040, below30 again5070. State4950 is partial local recovery only; E8 remains congested.',
            'horizon_limit':'5400 snapshots exist but have no later recorded horizon. They are initialization/terminal cases, not 450-second prediction-validation cases.'},
        'pair_contract':{'primary':'Same v4 cfg, raw900, previous750 and random/worker settings on both code variants; only proposed optimization differs.',
            'later':'Same existing legacy head-OFF v3 cfg and exact same raw+previous pair on both variants. It tests clock/physics computation equivalence on congested states, not v4 observed-resource application.',
            'prohibited':'Do not splice an earlier head window/floor into a later raw. A later OFF manifest cannot satisfy the ON provenance guard. Disabling only the v4 head flag leaves an invalid resource-contract dependency.',
            'cold_scope':'Reprojecting actual raw constructs a fresh model state; dynamic cohorts derive from that instantaneous route/position evidence, not continuous prior model memory. Report configuration migration explicitly.'},
        'sources':SOURCES,'source_changes':source_changes}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if source_changes:raise ValueError(source_changes)
    print(json.dumps({'output':relative(OUT),'states':len(records),'sources':len(SOURCES),'source_changes':source_changes,
                      'native_anchor_exact':all(all(v for k,v in r.items() if k.endswith('_exact')) for r in native_identity)}))


if __name__=='__main__':main()
