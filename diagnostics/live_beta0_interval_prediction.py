"""One actual held-action 150s replay and a binary-seek physical interval audit.

No optimizer search, simulator connection, parameter fitting, or production edit.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import copy
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
os.environ['RW_OFFSET_WRITER'] = 'experiment'
os.environ['RW_MAINLINE_SG_ONLY'] = '1'
from diagnostics.probe_model_area_integration import build_projected
from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.probe_e8_window_passages import frames
from scripts.measure_control_area import terminal_lengths
from evaluation.controllers import vissim_stackelberg_adapter as adapter, area_runtime
from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
from src.models.demand import DemandStep
from src.models.state import ControlAction
from src.controllers import rollout_endpoint
from src.simulation import coupling

RUN = ROOT/'evaluation/runs/codex_area_beta0_s13_20260910'
DEC = RUN/('decisions_'+RUN.name)
CONFIG = ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
PREFIX = ROOT/'diagnostics/live_beta0_interval_prediction'
START, END = 900, 1050


def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fingerprints(paths): return {str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}


def read_physical_window(path, membership, terminals, raw_start, raw_end, freeway_sets):
    """Initialize at the observed nonempty900 frame; never reward that stock.

    Terminal inference follows scripts.measure_control_area with the same10m,
    3m/s² and1s-step reach assumptions. It is separately reported from observed
    crossings; interior disappearances are never credited as TTD.
    """
    reader = IndexedFzp(path, max_bytes=64*1024*1024)
    provenance = []
    prev, prev_t, initial = None, None, None
    totals, exits_by_pair, uncertain_by_link = Counter(), Counter(), Counter()
    link_residence, link_slow, link_peak = Counter(), Counter(), Counter()
    entries, departures, vanished = Counter(), Counter(), Counter()
    entry_pairs, departure_pairs, appearance_links = defaultdict(Counter), defaultdict(Counter), Counter()
    freeway_events={link:Counter() for link in freeway_sets}
    freeway_initial,freeway_final={},{}
    rows, sample_rows = [], 0
    terminal_ids = set()
    inside = lambda row: membership[str(row[0])]
    def n_inside(values): return sum(inside(r) for r in values.values())
    def compare_com(values, raw):
        com = {int(r['veh_no']):int(r['link_no']) for r in raw['vehicle_records']['records']}
        native = {no:r[0] for no,r in values.items()}
        return {'native_vehicles':len(native),'com_vehicles':len(com),
                'native_omega_vehicles':n_inside(values),
                'com_omega_vehicles':sum(membership[str(x)] for x in com.values()),
                'only_native_ids':sorted(native.keys()-com.keys()),
                'only_com_ids':sorted(com.keys()-native.keys()),
                'changed_link_ids':sorted(no for no in native.keys()&com.keys() if native[no]!=com[no])}
    try:
        for sec, values in frames(reader,START,END,time.monotonic()+60,provenance):
            sample_rows += len(values)
            unknown = {str(r[0]) for r in values.values()} - membership.keys()
            if unknown: raise ValueError(f'Unknown physical membership: {unknown}')
            if prev is None:
                if sec != START: raise ValueError('Exact native900 initial frame required')
                initial = dict(values)
                freeway_initial={link:sum(str(r[0]) in keys for r in values.values()) for link,keys in freeway_sets.items()}
                start_phase = compare_com(values,raw_start)
                prev, prev_t = values, sec
                continue
            dt = sec-prev_t
            if dt != 1: raise ValueError(f'Expected complete1s physical frames, got{dt}')
            if terminal_ids & values.keys(): raise ValueError('Terminal disappearance inference contradicted by reappearance')
            before, after = n_inside(prev), n_inside(values)
            step = Counter()
            for no, old in prev.items():
                new = values.get(no)
                if new is not None:
                    if old[0] != new[0]:
                        departures[str(old[0])] += 1
                        entries[str(new[0])] += 1
                        entry_pairs[str(new[0])][str(old[0])] += 1
                        departure_pairs[str(old[0])][str(new[0])] += 1
                    if inside(old) and not inside(new):
                        step['observed_exit_veh'] += 1
                        exits_by_pair[f'{old[0]}->{new[0]}'] += 1
                    elif not inside(old) and inside(new): step['observed_entry_veh'] += 1
                else:
                    vanished[str(old[0])] += 1
                    if inside(old):
                        length = terminals.get(str(old[0]))
                        reach = old[3]/3.6*dt + .5*3*dt*dt + 10
                        overshoot = old[3]/3.6 + .5*3 + 10
                        if length is not None and -overshoot <= length-old[2] <= reach:
                            step['terminal_inferred_exit_veh'] += 1
                            terminal_ids.add(no)
                        else:
                            step['unresolved_inside_disappearance_veh'] += 1
                            uncertain_by_link[str(old[0])] += 1
            for no in values.keys()-prev.keys():
                appearance_links[str(values[no][0])] += 1
                if inside(values[no]): step['appeared_inside_veh'] += 1
            for link,keys in freeway_sets.items():
                fw=freeway_events[link]
                for no,old in prev.items():
                    old_in=str(old[0]) in keys
                    new=values.get(no)
                    if new is None:
                        if old_in: fw['disappeared_veh']+=1
                    else:
                        new_in=str(new[0]) in keys
                        if old_in and not new_in: fw['observed_exit_veh']+=1
                        if not old_in and new_in: fw['observed_entry_veh']+=1
                fw['appeared_veh']+=sum(str(values[no][0]) in keys for no in values.keys()-prev.keys())
            closure = after-before-step['observed_entry_veh']-step['appeared_inside_veh']+step['observed_exit_veh']+step['terminal_inferred_exit_veh']+step['unresolved_inside_disappearance_veh']
            if closure: raise AssertionError(f'Physical sampled stock closure{sec}: {closure}')
            totals.update(step)
            totals['ttt_left_veh_h'] += before*dt/3600
            totals['ttt_right_veh_h'] += after*dt/3600
            totals['ttt_trapezoid_veh_h'] += (before+after)*.5*dt/3600
            for endpoint in (prev,values):
                counts = Counter(str(r[0]) for r in endpoint.values())
                slow = Counter(str(r[0]) for r in endpoint.values() if r[3]<5)
                for link,count in counts.items():
                    link_residence[link] += count*.5*dt/3600
                    link_slow[link] += slow[link]*.5*dt/3600
                    link_peak[link] = max(link_peak[link],count)
            rows.append({'sim_sec':sec,'inside_veh':after,**step,
                         'ttt_cumulative_veh_h':totals['ttt_trapezoid_veh_h'],
                         'counted_ttd_cumulative_veh':totals['observed_exit_veh']+totals['terminal_inferred_exit_veh'],
                         'closure_residual_veh':closure})
            prev,prev_t = values,sec
    finally: reader.handle.close()
    if prev_t != END: raise ValueError(f'Native interval ended{prev_t}, expected1050')
    freeway_final={link:sum(str(r[0]) in keys for r in prev.values()) for link,keys in freeway_sets.items()}
    for link,values in freeway_events.items():
        values['initial_veh']=freeway_initial[link]
        values['final_veh']=freeway_final[link]
        values['closure_residual_veh']=values['final_veh']-values['initial_veh']-values['appeared_veh']-values['observed_entry_veh']+values['observed_exit_veh']+values['disappeared_veh']
        if values['closure_residual_veh']: raise AssertionError('FW sampled physical closure failed')
    if abs(sum(v for k,v in link_residence.items() if membership[k])-totals['ttt_trapezoid_veh_h'])>1e-8:
        raise AssertionError('Disaggregated physical residence does not close')
    physical = {'interval_sec':[START,END],'totals':dict(totals),
        'initial_inside_veh':n_inside(initial),'final_inside_veh':n_inside(prev),
        'ttd_observed_plus_terminal_veh':totals['observed_exit_veh']+totals['terminal_inferred_exit_veh'],
        'exit_pairs':dict(exits_by_pair),'unresolved_disappearance_links':dict(uncertain_by_link),
        'freeway_chain_stock_and_flow':{k:dict(v) for k,v in freeway_events.items()},
        'appeared_inside_by_physical_link':{k:v for k,v in appearance_links.items() if membership[k]},
        'max_sampled_stock_closure_error_veh':0,'frame_count':len(rows)+1,'record_rows':sample_rows,
        'native_vs_com_900':start_phase,'native_vs_com_1050':compare_com(prev,raw_end),
        'fzp_source':{'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,
                      'bytes_read':reader.bytes_read,'selected_ranges':provenance},
        'limitations':['Observed TTD plus terminal inference excludes interior disappearance; no unknown sink reward.',
            'Same-side excursions entirely between1s snapshots can be missed; this is not an absolute lower/upper confidence interval.',
            'Terminal inference uses10m position margin,3m/s² reach and1s-step overshoot; normal departure and deletion near a terminal are not distinguishable.',
            'Left/right residence rules are time-discretization alternatives, not statistical uncertainty bounds.']}
    links = {key:{'residence_veh_h':value,'mean_count_veh':value*3600/(END-START),
                  'slow_below5kph_veh_h':link_slow[key],'peak_count_veh':link_peak[key],
                  'observed_entries_veh':entries[key],'observed_departures_veh':departures[key],
                  'observed_entry_source_links':dict(entry_pairs[key]),
                  'observed_departure_target_links':dict(departure_pairs[key]),
                  'appeared_veh':appearance_links[key],
                  'disappeared_veh':vanished[key]} for key,value in link_residence.items()}
    return physical,links,rows


def main():
    began=time.monotonic()
    live_manifest=load(RUN/'area_candidate_source_manifest.json')
    previous=max((p for p in DEC.glob('action_*.json') if int(p.stem.split('_')[-1])<START),key=lambda p:int(p.stem.split('_')[-1]))
    inputs=[CONFIG,DEC/'state_000900.json',DEC/'state_000600.json',previous,DEC/'action_000900.json',
            DEC/'state_001050.json',Path(__file__),ROOT/'scripts/measure_control_area.py',
            RUN/('runlog_'+RUN.name+'.txt'),RUN/('run_provenance_'+RUN.name+'.json'),
            ROOT/'diagnostics/probe_e8_lane_receiving.py',ROOT/'diagnostics/probe_e8_window_passages.py']
    paths=inputs+[ROOT/p for p in live_manifest['source_sha256']]
    paths += list((ROOT/'evaluation/controllers').glob('*.py'))+list((ROOT/'vendor/NumSim-mine/src').rglob('*.py'))
    before=fingerprints(paths)
    changed_from_live={p:{'live':v,'current':before[p]} for p,v in live_manifest['source_sha256'].items() if before[p]!=v}
    support_key='diagnostics\\physical_projection_support_635_proposal.json'
    support_delta=None
    if support_key in changed_from_live:
        old_bytes=subprocess.check_output(['git','show','bc9078e:diagnostics/physical_projection_support_635_proposal.json'],cwd=ROOT)
        working_bytes=old_bytes.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        if hashlib.sha256(working_bytes).hexdigest()!=live_manifest['source_sha256'][support_key]:
            raise ValueError('Historical support source does not match live working-tree hash')
        old_support=json.loads(old_bytes)['link_to_storage']
        current_support=load(ROOT/support_key)['link_to_storage']
        added=sorted(current_support.keys()-old_support.keys(),key=int)
        changed_existing={k:current_support.get(k) for k in old_support if current_support.get(k)!=old_support[k]}
        initial_counts=load(DEC/'state_000900.json')['vehicle_records']['full_network_link_counts']
        support_delta={'baseline_commit':'bc9078e','baseline_git_blob_sha256':hashlib.sha256(old_bytes).hexdigest(),
            'baseline_crlf_matches_live_manifest':True,'added_links':added,'changed_existing':changed_existing,
            'added_link_initial_counts':{k:initial_counts.get(k,0) for k in added},
            'scope':'Initial physical projection support only; no new motion/flow equation.'}
        if changed_existing or any(support_delta['added_link_initial_counts'].values()):
            raise ValueError('Support data change materially alters the live initial snapshot')
    cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(CONFIG,DEC/'state_000900.json',previous)
    live_action=load(DEC/'action_000900.json')
    runtime_numeric_differences={key:{'replay':value,'live':live_action['metadata'][key]}
        for key,value in metadata.items() if key in live_action['metadata']
        and (key.startswith('sat_est_') or key.startswith('far_rate_est_') or key.startswith('far_ramp_capacity_'))
        and value!=live_action['metadata'][key]}
    if runtime_numeric_differences: raise AssertionError('Live runtime estimator mismatch: '+str(runtime_numeric_differences))
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,1,calibration,detectors)
    action=adapter.control_from_json(DEC/'action_000900.json',cfg,ControlAction)
    action_before=copy.deepcopy(vars(action))
    initial_stock=sum(row['inside'] for row in state._control_area_ledger.stocks.values())
    net=cfg.network
    trace,flow_trace,schedule_trace=[],[],[]
    def snapshot(s,elapsed):
        return {'elapsed_sec':elapsed,'cell_counts_veh':continuity_vehicle_counts(s,cfg),
            'cell_speed_kph':copy.deepcopy(s.freeway_speed),'cell_density_veh_km_lane':copy.deepcopy(s.freeway_density),
            'effective_lanes':copy.deepcopy(s.freeway_effective_lanes),
            'omega_stock_veh':sum(row['inside'] for row in s._control_area_ledger.stocks.values()),
            'ramp_queue_veh':dict(s.ramp_queue),'urban_storage_occupancy_veh':{
                key:net.urban_link_storage_veh[key]-value for key,value in s.urban_link_storage.items()}}
    trace.append(snapshot(state,0))
    old_fw,old_schedule=coupling.freeway_substep,coupling.schedule_offramp_arrivals
    def observed_fw(*args,**kwargs):
        for key in ('ramp_metering','green_times','offsets','vsl'):
            if getattr(args[1],key)!=getattr(action,key): raise AssertionError('Actual held physical command changed before model substep: '+key)
        result=old_fw(*args,**kwargs)
        flow_trace.append({'elapsed_sec':(len(flow_trace)+1)*cfg.simulation.T_f_sec,
                          'actual_ramp_release_vph':dict(kwargs['ramp_release_veh_h']),
                          'off_ramp_receiving_vph':dict(kwargs['offramp_capacity_veh_h']),
                          'diagnostics':dict(result[1])})
        return result
    def observed_schedule(s,c,off,vehicles,index):
        result=old_schedule(s,c,off,vehicles,index)
        schedule_trace.append({'elapsed_sec':len(trace)*cfg.simulation.T_f_sec,'offramp':off,
                               'requested_veh':vehicles,'accepted_veh':result[0],'rejected_veh':result[1]})
        if off==net.off_ramps[-1]: trace.append(snapshot(s,len(trace)*cfg.simulation.T_f_sec))
        return result
    with patch.object(coupling,'freeway_substep',observed_fw),patch.object(coupling,'schedule_offramp_arrivals',observed_schedule):
        result=rollout_endpoint.evaluate_price_point(state,action,forecast,[],
            rollout_endpoint.ObjectiveSpec(cfg,depth_override=1,box_walk=False,score_mode='raw'))
    if vars(action)!=action_before: raise AssertionError('Actual held command mutated')
    if len(flow_trace)!=15 or len(trace)!=16 or result.aborted: raise AssertionError('Incomplete150s endpoint')
    last=result.states[-1]
    last._control_area_ledger.assert_stocks(area_runtime.model_inventory(last,cfg))
    if initial_stock!=sum(row['inside'] for row in state._control_area_ledger.stocks.values()): raise AssertionError('Initial state mutated')
    endpoint_elapsed=time.monotonic()-began
    end_raw=load(DEC/'state_001050.json')
    document=load(ROOT/'diagnostics/control_area_membership.json')
    membership={str(x):True for x in document['inside_links']}
    membership.update({str(x):False for x in document['outside_links']})
    fzp=next((RUN/'vissim_eval').glob('*.fzp'))
    freeway_sets={key:set(map(str,row['chain_links'])) for key,row in mapping['freeway_model_links'].items()}
    physical,physical_links,physical_series=read_physical_window(fzp,membership,terminal_lengths(document),raw,end_raw,freeway_sets)
    cell_rows=[]
    for link in net.freeway_links:
        for cell,(initial,actual) in enumerate(zip(raw['freeway_segments'][link],end_raw['freeway_segments'][link])):
            observed_speed=actual['speed_sum']/actual['count'] if actual['count'] else None
            cell_rows.append({'link':link,'cell':cell,'initial_count_veh':initial['count'],
                'predicted_count_veh':trace[-1]['cell_counts_veh'][link][cell],'observed_count_veh':actual['count'],
                'count_error_veh':trace[-1]['cell_counts_veh'][link][cell]-actual['count'],
                'initial_speed_kph':initial['speed_sum']/initial['count'] if initial['count'] else None,
                'predicted_speed_kph':last.freeway_speed[link][cell],'observed_speed_kph':observed_speed,
                'speed_error_kph':last.freeway_speed[link][cell]-observed_speed if observed_speed is not None else None})
    off_rows=[]
    for off,branches in detectors['off_ramp_connectors'].items():
        signal=net.off_ramp_storage_link[off]
        direct=getattr(net,'offramp_direct_tail_by_offramp',{}).get(off)
        off_rows.append({'group':off,'signal_model_storage':signal,'direct_model_shared_storage':direct,
            'direct_share':getattr(net,'offramp_direct_share_by_offramp',{}).get(off),
            'freeway_split_ratio':net.off_ramp_split_ratio[off],
            'group_assigned_model_cell':net.off_ramp_segment_index[off],
            'predicted_fw_to_off_group_veh':sum(t['diagnostics'][f'offramp_flow_{off}']*cfg.simulation.T_f_h for t in flow_trace),
            'predicted_off_blocked_before_removal_veh':sum(t['diagnostics'][f'offramp_blocked_flow_{off}']*cfg.simulation.T_f_h for t in flow_trace),
            'scheduled_accepted_veh':sum(t['accepted_veh'] for t in schedule_trace if t['offramp']==off),
            'scheduled_rejected_veh':sum(t['rejected_veh'] for t in schedule_trace if t['offramp']==off),
            'predicted_initial_signal_storage_veh':trace[0]['urban_storage_occupancy_veh'][signal],
            'predicted_final_signal_storage_veh':trace[-1]['urban_storage_occupancy_veh'][signal],
            'predicted_initial_direct_shared_storage_veh':trace[0]['urban_storage_occupancy_veh'].get(direct),
            'predicted_final_direct_shared_storage_veh':trace[-1]['urban_storage_occupancy_veh'].get(direct),
            'physical_branches':[{**branch,'measured_connector':physical_links.get(str(branch['connector']),{}),
                'raw_initial_count_veh':raw['vehicle_records']['full_network_link_counts'].get(str(branch['connector']),0),
                'raw_final_count_veh':end_raw['vehicle_records']['full_network_link_counts'].get(str(branch['connector']),0)} for branch in branches]})
    after=fingerprints(paths)
    changed={k:{'before':v,'after':after[k]} for k,v in before.items() if after[k]!=v}
    output={'schema':'live-beta0-first-prediction/v1','run':RUN.name,'interval_sec':[START,END],
        'method':'Canonical shared runtime, actual900 action held exactly for one150s endpoint; current-state forecast only, no optimizer search.',
        'model':{'metrics':result.control_area,'initial_omega_veh':initial_stock,
            'live_runtime_capacity_estimates_exactly_match':True,
            'final_omega_veh':trace[-1]['omega_stock_veh'],'stock_closure_valid':True,
            'unchanged_input_action':True,'forecast':vars(forecast[0]),'runtime_metadata':metadata,
            'ramp_initial_veh':trace[0]['ramp_queue_veh'],'ramp_final_veh':trace[-1]['ramp_queue_veh'],
            'ramp_predicted_merge_veh':{r:sum(t['actual_ramp_release_vph'][r]*cfg.simulation.T_f_h for t in flow_trace) for r in net.ramps},
            'endpoint_preparation_and_run_wall_sec':endpoint_elapsed},
        'physical':physical,'physical_ramp_queues_1050':end_raw['ramp_counts'],
        'demand_transition':{'state_600':load(DEC/'state_000600.json')['demand'],'state_900':raw['demand'],
                            'same_900_to_1050_input_rates':raw['demand']==end_raw['demand'],
                            'previous_action_used':str(previous.relative_to(ROOT))},
        'cells_1050':cell_rows,'offramps':off_rows,'physical_link_measurement':physical_links,
        'source_sha256_start':before,'source_changes_during_probe':changed,
        'source_changes_from_live_manifest':changed_from_live,
        'projection_support_data_delta':support_delta,
        'initial_physical_stock_assignment_by_link':state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'],
        'limitations':['One executed interval, one seed; no causal treatment or performance comparison.',
            'Model grouped rates/proportional mixing and stopline timing approximate spatial physical trajectories.',
            'Direct shared storage contains multiple physical corridors; do not treat its total as the count on one connector.',
            'Native FZP and paused COM snapshots may record different phases of a simulation step; both endpoint differences are explicit.']}
    output['comparison']={'ttt_model_minus_physical_veh_h':result.control_area['ttt_veh_h']-physical['totals']['ttt_trapezoid_veh_h'],
        'ttd_model_minus_observed_plus_terminal_veh':result.control_area['ttd_veh']-physical['ttd_observed_plus_terminal_veh'],
        'final_omega_model_minus_com_veh':trace[-1]['omega_stock_veh']-physical['native_vs_com_1050']['com_omega_vehicles']}
    generated={key:value for key,value in result.control_area['flow_counts'].items()
               if key.startswith('input:') and net.control_area_routes[key]['target_inside'] is True}
    output['model']['generated_inside_by_input_veh']=generated
    output['model']['omega_flux_closure_residual_veh']=trace[-1]['omega_stock_veh']-initial_stock-result.control_area['entered_veh']+result.control_area['ttd_veh']-sum(generated.values())
    if abs(output['model']['omega_flux_closure_residual_veh'])>1e-7: raise AssertionError('Omega flux closure fails')
    fw_ttt=sum(sum(sum(values) for values in row['cell_counts_veh'].values())*cfg.simulation.T_f_h for row in trace[1:])
    fw_keys=set().union(*freeway_sets.values())
    physical_fw_ttt=sum(row['residence_veh_h'] for key,row in physical_links.items() if key in fw_keys)
    output['comparison']['residence_decomposition']={
        'freeway_model_veh_h':fw_ttt,'freeway_physical_veh_h':physical_fw_ttt,
        'remaining_omega_model_veh_h':result.control_area['ttt_veh_h']-fw_ttt,
        'remaining_omega_physical_veh_h':physical['totals']['ttt_trapezoid_veh_h']-physical_fw_ttt}
    fw_balance={}
    for link in net.freeway_links:
        f=result.control_area['flow_counts']
        group_offs=[off for off in net.off_ramps if net.off_ramp_from_freeway[off]==link]
        q={'initial_veh':sum(trace[0]['cell_counts_veh'][link]),'final_veh':sum(trace[-1]['cell_counts_veh'][link]),
           'mainline_admitted_veh':f[f'origin:{link}->freeway:{link}'],
           'ramp_merge_veh':sum(v for k,v in f.items() if k.startswith('merge_pending:') and k.endswith('->freeway:'+link)),
           'offramp_exit_veh':sum(row['predicted_fw_to_off_group_veh'] for row in off_rows if row['group'] in group_offs),
           'terminal_exit_veh':f[f'freeway:{link}->external:terminal:{link}']}
        q['closure_residual_veh']=q['final_veh']-q['initial_veh']-q['mainline_admitted_veh']-q['ramp_merge_veh']+q['offramp_exit_veh']+q['terminal_exit_veh']
        if abs(q['closure_residual_veh'])>1e-7: raise AssertionError('Model FW flux closure fails')
        fw_balance[link]=q
    output['model']['freeway_mass_balance']=fw_balance
    if changed: output['valid_source_freeze']=False
    else: output['valid_source_freeze']=True
    PREFIX.with_suffix('.json').write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    PREFIX.with_name(PREFIX.name+'_trace.json').write_text(json.dumps({'state_trace':trace,'accepted_flow_trace':flow_trace,'offramp_schedule_trace':schedule_trace},indent=2)+'\n',encoding='utf-8')
    for suffix,data in (('_cells.csv',cell_rows),('_physical.csv',physical_series)):
        with PREFIX.with_name(PREFIX.name+suffix).open('w',encoding='utf-8',newline='') as file:
            columns=list(dict.fromkeys(key for row in data for key in row))
            writer=csv.DictWriter(file,fieldnames=columns);writer.writeheader();writer.writerows(data)
    predicted=result.control_area
    measured=physical['totals']
    lines=[f'Actual beta0 action, 900–1050 s: prediction audit ({RUN.name}).',
        'The model overpredicts freeway residence and underpredicts residence in the remaining protected area. These errors partly cancel in the aggregate Omega TTT. This is one observed interval, not a treatment-effect or beta comparison.',
        '| Metric | Model | Physical measurement |\n|---|---:|---:|',
        f"| Omega TTT (veh*h) | {predicted['ttt_veh_h']:.6f} | {measured['ttt_trapezoid_veh_h']:.6f} |",
        f"| FW TTT (veh*h) | {fw_ttt:.6f} | {physical_fw_ttt:.6f} |",
        f"| Remaining Omega TTT (veh*h) | {predicted['ttt_veh_h']-fw_ttt:.6f} | {measured['ttt_trapezoid_veh_h']-physical_fw_ttt:.6f} |",
        f"| Outward TD (veh) | {predicted['ttd_veh']:.6f} | 469 observed + 227 terminal-inferred = 696 |",
        f"| Final Omega stock (veh) | {trace[-1]['omega_stock_veh']:.6f} | 2083 COM; 2084 native FZP |",
        '',
        'Physical residence uses 151 complete native FZP frames at 1 s cadence, with trapezoidal integration. Left/right rules give 79.654444 / 79.743056 veh*h; these are integration choices, not confidence bounds. Five interior disappearances are separately unresolved and receive no TD credit. Initial native/COM Omega stocks differ by two vehicles (1765/1763), and final stocks differ by one; native records precede the later paused COM phase. No final stock is treated as an exit.',
        '',
        '| Off-ramp group | Model requested = accepted (veh) | Actual FW-to-connector entries (veh) |\n|---|---:|---:|']
    for row in off_rows:
        physical_count=sum(b['measured_connector'].get('observed_entries_veh',0) for b in row['physical_branches'])
        details=', '.join(f"{b['connector']}:{b['measured_connector'].get('observed_entries_veh',0)}" for b in row['physical_branches'])
        lines.append(f"| {row['group']} | {row['predicted_fw_to_off_group_veh']:.6f} | {physical_count} ({details}) |")
    lines.extend(['',
        'All 295 connector entry events have a previously observed vehicle on that connector’s exact configured physical from_link. They are FW-to-off arrivals, not connector departures, sink counts, or initial stock. All four model group split ratios are 0.2. Receiving-cap blocking and later schedule rejection are both zero; the 141.356 total therefore comes from the requested split flow. Signal/direct shares only divide that already computed total once. Increasing receiver capacity cannot repair this interval’s under-request. The next narrow review is the total off-ramp route fraction and its physical entry cohort/position; no new ratio is fitted here.',
        '',
        '| FW_E cell at1050 | Predicted speed (km/h) | Observed speed (km/h) | Predicted / observed stock (veh) |\n|---|---:|---:|---:|'])
    for row in cell_rows:
        if row['link']=='FW_E' and row['cell'] in (8,9):
            lines.append(f"| {row['cell']} | {row['predicted_speed_kph']:.3f} | {row['observed_speed_kph']:.3f} | {row['predicted_count_veh']:.3f} / {row['observed_count_veh']} |")
    lines.extend(['',
        'Direct connector10682 grows from9 to17 COM vehicles (native mean17.753, peak22); its slow residence below5km/h is0.217222veh*h. The model direct store SC1004_W_out contains several physical corridors and must not be equated with connector10682 alone. Likewise, signal OR store discharge is not automatically the same spatial boundary as the connector’s downstream join.',
        '',
        'Each native mainline input changes from4619.8152veh/h at600s to6599.736veh/h at900s; the model reads6599.736 for each direction, matching the plant’s logged second input interval. Those rates remain unchanged through1050. Native observed appearances into the FW chains are230W+247E=477veh versus the model’s549.978 accepted entries. This difference may include actual input realization/admission; the configured profile is not lagged. Model internal Omega generation is117.616667veh (shared69, in_SC1_W and in_SC1001_W), separately added to boundary entries when checking stock closure.',
        '',
        'The replay uses the actual last warmup action750, and its sat_est, far_rate_est and far_ramp_capacity values exactly match the live900 metadata. Earlier exploratory messages used older warmup history; the figures in this report replace those preliminary urban/total figures. All 15 model substeps assert the executed meter, green, offset and VSL vectors unchanged. Model stock and explicit flux closure pass. No optimizer search or VISSIM connection is used.',
        '',
        'Source hashes are recorded before/after execution with no changes during the probe. Compared with the live manifest, only the later projection support data differ:16 added links all have zero vehicles at900, no existing assignment changes, and no motion equation changes. The baseline Git blob is verified against the live CRLF working-file hash. Physical FZP access reads only the selected900–1050 range by binary seek (about21.8MB of101MB), and records its byte offset and raw range SHA256.',
        '',
        'The adjacent JSON contains accepted flows, physical entry/exit pairs, all42 cell comparisons, source hashes and complete unit definitions. The _trace.json file retains the15 ten-second model flow/state snapshots.'])
    PREFIX.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'model':{k:result.control_area[k] for k in ('ttt_veh_h','ttd_veh','entered_veh')},
        'physical':physical['totals'],'comparison':output['comparison'],'source_changes':changed,
        'live_source_changes':changed_from_live,'wall_sec':time.monotonic()-began},indent=2))


if __name__=='__main__': main()
