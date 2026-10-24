"""Read paused route/position snapshots; never advance the freeway model."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.vehicle_routes import complete_vehicle_routes
from evaluation.controllers.network_provenance import snapshot_network_sha256

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',default='codex_area_observed_nc_s13_20260910')
    ap.add_argument('--times',type=int,nargs='+',default=[900,2700])
    ap.add_argument('--out',type=Path,default=Path('diagnostics/freeway_route_observability.json'))
    ap.add_argument('--reference-audit',type=Path)
    ap.add_argument('--interval-evidence',type=Path)
    args=ap.parse_args(argv)
    out=(ROOT/args.out).resolve()
    if (ROOT/'diagnostics').resolve() not in out.parents:ap.error('Output must stay under diagnostics')
    network=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
    prior_path=ROOT/'diagnostics/total_offramp_ratio_audit.json'
    mapping_path=ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    prior,mapping=load(prior_path),load(mapping_path)
    pinned_network=[row['sha256'] for row in prior['sources'] if str(row['path']).endswith('modi_eval_userfix Ver2.inpx')]
    if pinned_network!=[sha(network)]:raise ValueError('Physical branch audit network differs')
    run=(ROOT/'evaluation/runs'/args.run).resolve()
    if run.parent!=(ROOT/'evaluation/runs').resolve():ap.error('Run must be a direct child of evaluation/runs')
    directory=run/('decisions_'+run.name)
    snapshots=[]
    for sec in args.times:
        candidates=[directory/f'{kind}_{sec:06d}.json' for kind in ('state','anchor')]
        path=next((path for path in candidates if path.is_file()),None)
        if path is None:raise FileNotFoundError(f'No complete state/anchor at {sec}')
        snapshots.append(path)
    sources=[Path(__file__),network,prior_path,mapping_path,*snapshots,
        ROOT/'evaluation/controllers/vehicle_routes.py',ROOT/'evaluation/controllers/projection_support.py',ROOT/'evaluation/controllers/network_provenance.py']
    sources += [ROOT/path for path in (
        'evaluation/controllers/vissim_stackelberg_adapter.py','evaluation/controllers/area_freeway_accounting.py',
        'evaluation/controllers/urban_flow_accounting.py','evaluation/controllers/observation_projection.py',
        'evaluation/controllers/link_predictor.py','evaluation/controllers/offramp_routing.py',
        'vendor/NumSim-mine/src/controllers/local_freeway_plant.py','vendor/NumSim-mine/src/models/state.py',
        'vendor/NumSim-mine/src/simulation/coupling.py','diagnostics/e8_minimal_repair_handoff.md',
        'diagnostics/total_offramp_ratio_review.md','diagnostics/static_route_matched_cohorts.md')]
    for extra in (args.reference_audit,args.interval_evidence):
        if extra:sources.append((ROOT/extra).resolve())
    before={str(path.relative_to(ROOT)):sha(path) for path in sources}
    lookup={str(link):(model,float(offset)) for model,row in mapping['freeway_model_links'].items()
            for link,offset in zip(row['chain_links'],row['chain_offsets_m'])}
    result={'schema':'freeway-route-observability/v1','run':run.name,'source_sha256':before,'snapshots':[],
        'scope':'Recorded physical stock and current route only. A null or other-decision identity is not a newly sampled route, and current route does not recover a historical merge cohort.',
        'group_regions':'Each decision plane through its second diverge; stock is a snapshot, not a gate passage denominator. Regions are not added across groups.'}
    for path in snapshots:
        raw=load(path);routes=complete_vehicle_routes(raw,required=True)
        if snapshot_network_sha256(raw)!=pinned_network[0]:raise ValueError('Snapshot network differs from branch geometry')
        if raw['sim_sec'] not in args.times:raise ValueError('Wrong snapshot time')
        fw=[row for row in raw['vehicle_records']['records'] if str(row['link_no']) in lookup]
        by_model=Counter(lookup[str(row['link_no'])][0] for row in fw)
        observed={model:sum(row['count'] for row in values) for model,values in raw['freeway_segments'].items()}
        if dict(by_model)!=observed:raise ValueError('Physical FW records do not match canonical segment count')
        snapshot={'sim_sec':raw['sim_sec'],'physical_fw_veh':dict(by_model),'groups':{}}
        for group,spec in prior['native_routes_and_order'].items():
            branches=sorted(spec['physical_branches'],key=lambda row:row['chain_pos_m'])
            model=branches[0]['direction'];first,last=[row['chain_pos_m'] for row in branches]
            decision=int(spec['decision_attributes']['no']);native={int(row['route']):row['kind'] for row in spec['routes']}
            lo=spec['decision_chain_pos_m'];counts=Counter();current=Counter();lanes=Counter();selected=[]
            for row in fw:
                link_model,offset=lookup[str(row['link_no'])];position=offset+row['position_m']
                if link_model!=model or not lo<=position<last:continue
                identity=routes[row['veh_no']]
                stage='before_first_diverge' if position<first else 'between_diverges'
                if identity['route_decision_no'] is None:kind='null_current_route'
                elif identity['route_decision_no']==decision and identity['route_decision_type']=='STATIC':
                    kind='current_native_'+native.get(identity['route_no'],'UNKNOWN_ROUTE')
                else:kind='other_current_decision'
                counts[(stage,kind)]+=1
                current[str(identity['route_decision_no'])+':'+str(identity['route_no'])]+=1
                lanes[(stage,row['lane_no'])]+=1
                selected.append({'veh_no':row['veh_no'],'link':row['link_no'],'position_m':row['position_m'],
                    'chain_position_m':position,'lane':row['lane_no'],'speed_kph':row['speed_kph'],
                    'stage':stage,'route_class':kind,**{k:identity[k] for k in ('route_decision_no','route_no','route_decision_type')}})
            snapshot['groups'][group]={'region_chain_m':[lo,last],'physical_order':branches,
                'intermediate_merges':spec['merges_after_decision_before_last_branch'],
                'counts_by_stage_and_route':{f'{stage}/{kind}':n for (stage,kind),n in sorted(counts.items())},
                'current_identity_counts':dict(current),'lane_counts':{f'{stage}/lane{lane}':n for (stage,lane),n in sorted(lanes.items())},
                'total_veh':len(selected),'records':selected}
        result['snapshots'].append(snapshot)
    if args.reference_audit:
        reference=load((ROOT/args.reference_audit).resolve())
        comparisons=[]
        for current in result['snapshots']:
            matched=[row for row in reference['snapshots'] if row['sim_sec']==current['sim_sec']]
            if len(matched)!=1:raise ValueError('Exactly one same-time reference snapshot required')
            comparisons.append({'sim_sec':current['sim_sec'],
                'physical_fw_count_equal':matched[0]['physical_fw_veh']==current['physical_fw_veh'],
                'all_group_records_equal':matched[0]['groups']==current['groups']})
        result['reference_comparison']=comparisons
    if args.interval_evidence:
        interval=load((ROOT/args.interval_evidence).resolve());traces=interval['model']['freeway_substep_trace']
        if interval['run']!=run.name or interval['interval_sec'][0] not in args.times:raise ValueError('Interval belongs to a different run or initial snapshot')
        if not interval['replay_matches_executed_model'] or not interval['executed_command_audit_valid']:raise ValueError('Interval replay is not aligned with the executed model/action')
        previous=0.;flows=Counter()
        for row in traces:
            dt=row['elapsed_sec']-previous
            if dt<=0:raise ValueError('Invalid model step interval')
            for group in prior['native_routes_and_order']:flows[group]+=row['diagnostics']['offramp_flow_'+group]*dt/3600
            previous=row['elapsed_sec']
        if previous!=interval['interval_sec'][1]-interval['interval_sec'][0]:raise ValueError('Incomplete model flow interval')
        groups=[]
        for group,spec in prior['native_routes_and_order'].items():
            branches=[]
            for branch in spec['physical_branches']:
                physical=interval['physical_link_measurement'][branch['connector']]
                if physical['observed_entry_source_links']!={branch['from_link']:physical['observed_entries_veh']}:raise ValueError('Physical branch entry has an unexpected source')
                branches.append({'connector':branch['connector'],'source_link':branch['from_link'],'observed_entry_veh':physical['observed_entries_veh']})
            groups.append({'group':group,'predicted_accepted_group_veh':flows[group],
                'observed_branch_entries_veh':sum(row['observed_entry_veh'] for row in branches),'physical_branches':branches})
        result['executed_interval']={'run':interval['run'],'interval_sec':interval['interval_sec'],
            'boundary_definition':'Accepted model FW->off group flux versus explicit physical source-road->offconnector entry. Neither is an Omega exit or connector discharge.',
            'groups':groups,'end_stock_error_vs_com':interval['comparison']['final_stock_error_vs_com'],
            'residence':interval['comparison']['residence'],'ttd_model_veh':interval['model']['metrics']['ttd_veh'],
            'ttd_observed_plus_terminal_veh':interval['physical']['ttd_observed_plus_terminal_veh']}
    result['source_changes']=[key for key,value in before.items() if sha(ROOT/key)!=value]
    if result['source_changes']:raise ValueError('Read-only source changed during audit')
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(out),'source_changes':result['source_changes'],
        'snapshots':[{**{k:v for k,v in row.items() if k!='groups'},'groups':{group:{'total_veh':data['total_veh'],'counts':data['counts_by_stage_and_route']} for group,data in row['groups'].items()}} for row in result['snapshots']]},ensure_ascii=False))
    return 0

if __name__=='__main__':raise SystemExit(main())
