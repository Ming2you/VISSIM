"""Frozen-parameter actuator response checks after all four native runs pass."""
from pathlib import Path
import argparse,copy,csv,hashlib,json,sys
import zipfile
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
CAL=HERE.parent/'metanet_calibration_v1'
sys.path[:0]=[str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps'),str(CAL)]
from canonical_harness import load_base_model,DEFAULT_CONFIG
from boundary_factory import ObservationData,build_window
from scoring import score_rollout

def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def table(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def validated_vsl_schedule(commands):
    expected=set(commands['physical_scope']['vsl_dsd_ids'])
    if expected!={59,60,61,62}:
        raise ValueError('This diagnostic projection is specific to physical DSD59--62')
    grouped={}
    for row in commands['vsl_commands']:
        grouped.setdefault(row['time_s'],[]).append(row)
    result=[]
    for t,rows in sorted(grouped.items()):
        if (len(rows)!=len(expected) or {r['dsd_no'] for r in rows}!=expected
                or len({r['speed_id'] for r in rows})!=1):
            raise ValueError('Every VSL event must cover the four target DSDs at one identical speed ID')
        result.append({'time_s':t,'speed_id':rows[0]['speed_id']})
    return result


def native_baseline_vsl(path):
    # This fixed experiment's downstream boundary is the verified next group
    # DSD63--66. Neither it nor the target group is silently treated as100km/h.
    rows=[r for r in table(path) if r['phase']=='initial' and r['kind']=='vsl'
          and 59<=int(r['no'])<=66]
    if (len(rows)!=32 or len({(r['no'],r['veh_class']) for r in rows})!=32
            or {int(r['no']) for r in rows}!=set(range(59,67))
            or any(r['ok']!='1' or r['actual']!=r['expected'] for r in rows)
            or len({float(r['actual']) for r in rows})!=1):
        raise ValueError('Missing, nonuniform or unverified initial target/downstream VSL readback')
    return float(rows[0]['actual'])


def actuated_window(data,model,cutoff,mode,port_profile,commands,meter,baseline_vsl_id,ramp_local_step_sec=10):
    w=build_window(data,cutoff,mode,port_profile)
    r='RM_C10490';c='10490';spec=model.ramps[r]
    physical=commands['physical_scope']
    schedule=validated_vsl_schedule(commands)
    if baseline_vsl_id!=max(model.base.freeway_follower.vsl_set):
        raise ValueError('Native baseline distribution ID differs from model no-VSL convention')
    if abs(spec['length_m']-physical['connector_length_m'])>1e-7:
        raise ValueError('Physical ramp length differs from approved actuator')
    w['ramp_dynamics']={'schema':'physical-ramp-boundary/v1','ramps':{r:{
        'connector_id':c,'length_m':spec['length_m'],
        'head_position_m':physical['signal_head_pos_m'],'lanes':spec['lanes'],
        'spacing_m':float(model.base.network.urban_avg_vehicle_length_m),
        'travel_speed_kmh':float(port_profile['travel_speed_kmh'][c]),
        'time_sec':cutoff,'initial_cohorts':data.port_cohorts[str(cutoff)][c],
        'initial_backlog_veh':0.}}}
    if ramp_local_step_sec not in (1,10):
        raise ValueError('Ramp local diagnostic step must be1s or unchanged10s')
    if ramp_local_step_sec!=10:
        w['ramp_dynamics']['local_step_sec']=ramp_local_step_sec
        w['ramp_dynamics']['meter_cycle_sec']=float(meter['cycle_sec'])
    history=list(range(cutoff-120,cutoff+1,30))
    geometry=[x for x in data.geometry['cells'] if x['road']=='FW_E']
    selected=[x for x in geometry if max(0,min(x['end_m'],physical['next_native_dsd_chain_m'])-
        max(x['start_m'],physical['chain_from_m']))/(x['end_m']-x['start_m'])>=.5]
    if [x['cell'] for x in selected]!=[10,11,12]:
        raise ValueError('Unexpected physical VSL projection')
    # Split the previous10--14 zone at the downstream native DSD projection.
    # Install this on the copied per-road config only; the canonical default
    # topology and every no-option rollout retain their original zoning.
    heads=list(model.base.network.freeway_vsl_zone_heads['FW_E'])
    w['vsl_zone_heads']={'FW_E':sorted(set(heads+[selected[0]['cell'],selected[-1]['cell']+1]))}
    for step in w['boundary_steps']:
        t=step['window_start_s']
        ends=[(t//30+1)*30] if mode=='conditioned_diagnostic' else history
        records=[data.ports[e,c] for e in ends]
        if any(float(x['unresolved_absences_veh']) for x in records):
            raise ValueError('Unresolved ramp loss')
        step['ramp_arrival_vph']={r:sum(float(x['arrivals_veh']) for x in records)*3600/(30*len(records))}
        active=[x for x in commands['meter_commands'] if x['time_s']<=t]
        g=float(active[-1]['green_sec']) if active else None
        service_g=10 if g is None else int(g)
        dt=float(step['window_end_s'])-float(t)
        service=float(meter['per_lane_veh_per_cycle'][str(service_g)])*spec['lanes']*dt/float(meter['cycle_sec'])
        step['ramp_head_service']={r:{'service_veh':service,'mode':'OFF' if g is None else 'GREEN','green_sec':g}}
        active_vsl=[x for x in schedule if x['time_s']<=t]
        # Keep the existing writer's scalar command convention. Distribution
        # IDs are NOT observations of deterministic native desired speed.
        value=float(active_vsl[-1]['speed_id']) if active_vsl else baseline_vsl_id
        step['vsl_commands']={'FW_E':baseline_vsl_id,'FW_E__seg13':baseline_vsl_id,
            **{f"FW_E__seg{x['cell']}":value for x in selected}}
    w['response_assumptions']={
        'target_ramp':r,'other_seven_merges':'External observed/recent interface flows',
        'ramp_arrivals':'Connector admission-interface forecast; not all desired urban ramp demand',
        'native_OFF_service_proxy':'Existing g10 measured-table budget; OFF equivalence remains a hypothesis',
        'head_service_table_source':str(DEFAULT_CONFIG),'no_added_startup_loss':True,
        'VSL_command_convention':'Existing scalar command ID; native desired-speed distribution remains stochastic',
        'VSL_baseline_distribution_id':baseline_vsl_id,
        'VSL_initial_readback_scope':'All four vehicle classes on DSD59--66; downstream head restored each model step',
        'VSL_physical_interval_m':[physical['chain_from_m'],physical['next_native_dsd_chain_m']],
        'VSL_model_interval_m':[selected[0]['start_m'],selected[-1]['end_m']],
        'VSL_projection_overhang_m':{
            'upstream':physical['chain_from_m']-selected[0]['start_m'],
            'downstream':selected[-1]['end_m']-physical['next_native_dsd_chain_m']},
        'VSL_cell_indices':[x['cell'] for x in selected],
        'VSL_zone_heads':w['vsl_zone_heads'],
        'initial_outside_backlog':'Zero/unobserved; any later denied connector entry remains explicit backlog',
        'ramp_local_step_sec':ramp_local_step_sec,
        'head_timing_approximation':('10s cycle-mean head service occurs at interval end; post-head transit is eligible next interval, adding up to one step of discretization delay, not a calibrated startup-loss coefficient'
            if ramp_local_step_sec==10 else 'Ten1s local ramp steps within each unchanged10s METANET step; the same measured cycle budget is allocated during green, with causal transit and finite downstream receiving'),
        'future_state_resets':0}
    return w

def model_component(prediction,window):
    # Same 30-second trapezoid for freeway, off ports and target ramp. This is
    # separate from native 1-second and core end-step objective quadrature.
    a=window['initial_cells'][0]['time_s'];dt=30/7200
    old_fw=sum(x['n_veh'] for x in window['initial_cells'])
    old_off=sum(len(v) for v in window['port_dynamics']['initial_cohorts'].values())
    old_rm=len(window['ramp_dynamics']['ramps']['RM_C10490']['initial_cohorts'])
    totals={'freeway_ttt_veh_h':0.,'off_ttt_veh_h':0.,'target_ramp_ttt_veh_h':0.}
    receipts=prediction['ramps']
    for t in range(int(a)+30,int(a)+451,30):
        fw=sum(x['n_veh'] for x in prediction['cells'] if x['time_s']==t)
        off=sum(x['n_veh'] for x in prediction['ports'] if x['time_s']==t)
        rr=next(x for x in receipts if x['end_sec']==t and x['ramp']=='RM_C10490')
        rm=rr['end']['connector_veh']
        for key,old,new in [('freeway_ttt_veh_h',old_fw,fw),('off_ttt_veh_h',old_off,off),
                            ('target_ramp_ttt_veh_h',old_rm,rm)]:
            totals[key]+=(old+new)*dt
        old_fw,old_off,old_rm=fw,off,rm
    last=next(x for x in reversed(receipts) if x['ramp']=='RM_C10490')['end']
    return {**totals,'component_ttt_veh_h':sum(totals.values()),
        'ramp_merges_veh':last['cumulative_merge_veh'],
        'ramp_head_service_veh':last['cumulative_head_service_veh'],
        'ramp_final_n_veh':last['connector_veh'],
        'ramp_outside_backlog_veh':last['outside_component_backlog_veh']}


def observed_sampled_component(data,cutoff,off_ids):
    """Match predicted cell/port scope and30s trapezoid, not all native links."""
    totals={'freeway_ttt_veh_h':0.,'off_ttt_veh_h':0.,'target_ramp_ttt_veh_h':0.}
    previous=None
    for t in range(cutoff,cutoff+451,30):
        cohorts=data.port_cohorts[str(t)]
        current={
            'freeway_ttt_veh_h':sum(r['n_veh'] for r in data.cells[t]),
            'off_ttt_veh_h':sum(len(cohorts[c]) for c in off_ids),
            'target_ramp_ttt_veh_h':len(cohorts['10490'])}
        if previous is not None:
            for key in totals:
                totals[key]+=(previous[key]+current[key])*30/7200
        previous=current
    return {**totals,'component_ttt_veh_h':sum(totals.values())}


def posthead_audit(prediction,window,native_rows):
    spec=window['ramp_dynamics']['ramps']['RM_C10490']
    capacity=(spec['length_m']-spec['head_position_m'])*spec['lanes']/spec['spacing_m']
    receipts=[r for r in prediction['ramps'] if r['ramp']=='RM_C10490']
    local_receipts=[part for r in receipts for part in r.get('local_receipts',[r])]
    def stock(snapshot):
        return snapshot['downstream_travelling_veh']+snapshot['merge_ready_veh']
    stocks=[stock(local_receipts[0]['start'])]+[stock(r['end']) for r in local_receipts]
    start,end=receipts[0]['start_sec'],receipts[-1]['end_sec']
    native=[r for r in native_rows if start<=float(r['time_s'])<=end]
    if len(native)!=int(end-start)+1:
        raise ValueError('Missing native1s post-head stock audit')
    excess_times=[r['end_sec'] for r in local_receipts if stock(r['end'])>capacity+1e-8]
    introduced_excess=[r['end_sec'] for r in local_receipts
        if stock(r['end'])>max(capacity,stock(r['start']))+1e-8]
    valid=not introduced_excess
    return {'nominal_posthead_storage_veh':capacity,'model_max_posthead_veh':max(stocks),
        'model_max_excess_veh':max(0.,max(stocks)-capacity),
        'model_end_snapshot_exceedance_times_s':excess_times,
        'initial_observed_posthead_excess_veh':max(0.,stocks[0]-capacity),
        'new_or_increased_posthead_excess_times_s':introduced_excess,
        'model_audit_step_sec':min(r['duration_sec'] for r in local_receipts),
        'model_interval_start_exceedance_seconds':sum(r['duration_sec'] for r in local_receipts if stock(r['start'])>capacity+1e-8),
        'native_max_posthead_veh':max(float(r['downstream_n']) for r in native),
        'native_snapshot_exceedance_count':sum(float(r['downstream_n'])>capacity+1e-8 for r in native),
        'actuator_geometry_valid':valid,
        'verdict':('PASS_WITH_OBSERVED_INITIAL_EXCESS' if stocks[0]>capacity+1e-8 else 'PASS') if valid else 'FAIL_POSTHEAD_POINT_QUEUE_GEOMETRY',
        'limits':'This validity gate checks a nominal fluid-storage assumption, not exact front-position packing. Native two-vehicle samples do not prove physical impossibility. Whole-connector conservation alone does not validate post-head dynamics.'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--experiment',type=Path,required=True)
    ap.add_argument('--analysis',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--ramp-local-step-sec',type=int,choices=(1,10),default=10)
    args=ap.parse_args()
    if args.out.exists():raise FileExistsError('Preserve existing response evaluation')
    proof=load(args.analysis/'comparison.json')
    if not proof['paired_prefix_passed'] or not proof['paired_native_signals_passed']:
        raise ValueError('Native baseline or signal comparability failed')
    args.out.mkdir()
    files=[Path(__file__),CAL/'canonical_harness.py',CAL/'boundary_factory.py',CAL/'scoring.py',
           ROOT/'evaluation/controllers/physical_ramp_boundary.py',HERE/'port_profile.json',
           HERE/'fit_dynamic_v1/parameters.json',DEFAULT_CONFIG,args.analysis/'comparison.json']
    for arm in ('none','vsl','rm','both'):
        files.append(args.experiment/(arm+'.json'))
        files.append(args.analysis/arm/'component_windows.csv')
        files.append(args.analysis/arm/'meter_windows.json')
        files.append(args.analysis/arm/'meter_states_1s.csv')
        files.append(args.experiment/('run_'+arm)/'fixed_readback.csv')
        files.extend(args.analysis/arm/'observations'/name for name in (
            'geometry.json','cells_30s.csv','flows_30s.csv','boundaries_30s.csv',
            'ports_30s.csv','port_cohorts_30s.json'))
    hashes={str(p):sha(p) for p in files}
    profile=load(HERE/'port_profile.json');params=load(HERE/'fit_dynamic_v1/parameters.json')['parameters']
    meter=load(DEFAULT_CONFIG)['actuation']['real_world_ramp_metering']
    records=[];predictions={};windows={};baseline_initial={};model_source_paths=set()
    for arm in ('none','vsl','rm','both'):
        data=ObservationData(args.analysis/arm/'observations');model=load_base_model(data.geometry)
        for p,h in model.provenance['model_files'].items():
            name=str(ROOT/p)
            if name in hashes and hashes[name]!=h:
                raise RuntimeError('Model source changed between response arms')
            hashes[name]=h
            model_source_paths.add(name)
        commands=load(args.experiment/(arm+'.json'))
        baseline_vsl_id=native_baseline_vsl(args.experiment/('run_'+arm)/'fixed_readback.csv')
        observed=table(args.analysis/arm/'component_windows.csv')
        observed_meter=load(args.analysis/arm/'meter_windows.json')
        observed_meter_states=table(args.analysis/arm/'meter_states_1s.csv')
        for cutoff in (1350,1800):
            for mode in ('conditioned_diagnostic','history_forecast'):
                w=actuated_window(data,model,cutoff,mode,profile,commands,meter,baseline_vsl_id,args.ramp_local_step_sec)
                if cutoff==1350:
                    frame=(w['initial_cells'],w['port_dynamics'],w['ramp_dynamics'])
                    if mode in baseline_initial and baseline_initial[mode]!=frame:
                        raise ValueError('Treatment initial state differs before intervention')
                    baseline_initial[mode]=frame
                pred=model.rollout(w['initial_cells'],w['boundary_steps'],params,
                    w['initial_origin_queue'],port_dynamics=w['port_dynamics'],ramp_dynamics=w['ramp_dynamics'],
                    vsl_zone_heads=w['vsl_zone_heads'])
                values=model_component(pred,w)
                obs={x['scope']:x for x in observed if float(x['window_start_s'])==cutoff
                     and float(x['window_end_s'])==cutoff+450}
                actual_fw=sum(float(obs[r]['ttt_veh_h']) for r in ('FW_E','FW_W'))
                actual_off=sum(float(obs[c]['ttt_veh_h']) for c in model.offramps)
                actual_rm=float(obs['10490']['ttt_veh_h'])
                actual_head=next(r for r in observed_meter if r['window_start_s']==cutoff
                                 and r['window_end_s']==cutoff+450)
                native_actual={'freeway_ttt_veh_h':actual_fw,'off_ttt_veh_h':actual_off,
                    'target_ramp_ttt_veh_h':actual_rm,'component_ttt_veh_h':actual_fw+actual_off+actual_rm,
                    'ramp_merges_veh':float(obs['10490']['departures_veh']),
                    'ramp_head_service_veh':float(actual_head['head_crossings']),
                    'ramp_final_n_veh':float(obs['10490']['end_n_veh'])}
                sampled=observed_sampled_component(data,cutoff,model.offramps)
                actual={**native_actual,**sampled}
                score={r:score_rollout(data,cutoff,pred,r) for r in ('FW_E','FW_W')}
                if any(s['invalid'] for s in score.values()):raise ArithmeticError('Invalid physical prediction')
                actuator_audit=posthead_audit(pred,w,observed_meter_states)
                records.append({'arm':arm,'cutoff_s':cutoff,'mode':mode,'model':values,'actual':actual,
                    'actuator_geometry_audit':actuator_audit,
                    'vsl_binding_audit':{r['road']:r['vsl_binding_audit'] for r in pred['diagnostics']['roads']},
                    'response_claim_eligible':actuator_audit['actuator_geometry_valid'],
                    'actual_native_1s':native_actual,
                    'native_1s_minus_grid_30s_ttt':{k:native_actual[k]-sampled[k] for k in sampled},
                    'absolute_errors':{k:values[k]-v for k,v in actual.items()},'scores':score,
                    'comparison_scope':'Same initial-state candidate response' if cutoff==1350 else 'Per-arm realized recovery state; not a common-state candidate test'})
                key=f'{arm}_{cutoff}_{mode}';predictions[key]=pred;windows[key]=w
                print(json.dumps({'completed':key,'predicted_merges':values['ramp_merges_veh'],
                    'actual_merges':actual['ramp_merges_veh']}),flush=True)
    for row in records:
        reference=next(r for r in records if r['arm']=='none' and r['cutoff_s']==row['cutoff_s'] and r['mode']==row['mode'])
        row['paired_response_claim_eligible']=row['response_claim_eligible'] and reference['response_claim_eligible']
        row['response_difference']={k:{'model':row['model'][k]-reference['model'][k],
            'actual':row['actual'][k]-reference['actual'][k],
            'actual_native_1s':row['actual_native_1s'][k]-reference['actual_native_1s'][k],
            'difference_error':(row['model'][k]-reference['model'][k])-(row['actual'][k]-reference['actual'][k])}
            for k in row['actual']}
    for p,h in hashes.items():
        if sha(p)!=h:raise RuntimeError('Source changed during response evaluation')
    source_paths={p for p in hashes if Path(p).suffix in ('.py','.yaml')}
    source_paths.update(model_source_paths)
    source_paths.update(str(p) for p in (DEFAULT_CONFIG,HERE/'port_profile.json',
        HERE/'physical_geometry21_v1.json',HERE/'fit_dynamic_v1/parameters.json',ROOT/'evaluation/parameters.json'))
    archive_path=args.out/'frozen_source_snapshot.zip'
    snapshot_manifest={}
    with zipfile.ZipFile(archive_path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(source_paths):
            path=Path(p);body=path.read_bytes();digest=hashlib.sha256(body).hexdigest()
            if str(path) in hashes and hashes[str(path)]!=digest:
                raise RuntimeError('Source changed before archive capture')
            relative=str(path.relative_to(ROOT)).replace('\\','/')
            snapshot_manifest[relative]=digest
            archive.writestr(relative,body)
        archive.writestr('SNAPSHOT_MANIFEST.json',json.dumps(snapshot_manifest,indent=2))
    result={'schema':'canonical-actuator-response/v1','records':records,
        'assumptions':windows['none_1350_history_forecast']['response_assumptions'],
        'source_sha256':hashes,'fitted_against_native_treatments':False,
        'ramp_local_step_sec':args.ramp_local_step_sec,
        'frozen_source_archive':{'path':str(archive_path),'sha256':sha(archive_path),'files':snapshot_manifest},
        'metric_scope':{'model_and_actual':'Freeway geometry cells (positions >=0), eight off connectors and10490;30s stock trapezoid',
            'actual_native_1s':'Full physical freeway link stock including finite negative positions, eight off connectors and10490;1s trapezoid',
            'native_1s_minus_grid_30s_ttt':'Combined quadrature and negative-position scope difference; not a pure model error',
            'ramp_merge_metric':'Live10490-to-mainline departures; head crossing is a distinct event'},
        'warnings':['Component TTT excludes other7 onramps and all urban links; not Omega MPC cost.',
        'Response cost differences compare matched30s geometry-cell/port TTT; native1s physical-link TTT is separately retained. Core10s objective differs.',
        'Conditional mode consumes future interface flows; history mode does not.',
        'Rows failing the post-head storage audit are frozen diagnostics of model error, not certified actuator-response or benefit predictions.',
        'No response claim is made for the GNE/N_UF feasibility or policy-selection path.']}
    for name,obj in [('response.json',result),('predictions.json',predictions),('windows.json',windows)]:
        (args.out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':main()
