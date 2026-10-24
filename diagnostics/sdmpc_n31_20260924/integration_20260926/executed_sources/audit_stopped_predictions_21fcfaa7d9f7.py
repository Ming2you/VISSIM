"""Summarize two completed offline forecasts; no simulator, fit or controller call."""
import bisect
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from collections import Counter

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[2]
RECORDS = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')


def load(path):
    return json.loads(path.read_bytes())


def main():
    sources = {}

    def pin(path):
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    manifest = load(pin(STUDY/'selected/plant_n31_v2.json'))
    geometry_path = ROOT/manifest['sources']['geometry']['path']
    geometry = load(pin(geometry_path))
    assert sources[str(geometry_path)] == manifest['sources']['geometry']['sha256']
    chains = {int(x['link']): (road, x['offset_m'])
              for road, chain in geometry['chains'].items() for x in chain}
    cells = {road: sorted((c for c in geometry['cells'] if c['road'] == road),
                          key=lambda c: c['cell']) for road in ('FW_E', 'FW_W')}
    series_path = pin(HERE/'stopped_prefix8100/sdmpc/area_timeseries.csv')
    with series_path.open(encoding='utf-8-sig', newline='') as handle:
        series = list(csv.DictReader(handle))
    stamps = [float(row['sim_sec']) for row in series]

    def cumulative_at(sec):
        index = bisect.bisect_right(stamps, sec)-1
        left, right = series[index], series[index+1]
        start, end = float(left['sim_sec']), float(right['sim_sec'])
        assert start <= sec <= end and end-start < 5.00001
        n0, n1 = float(left['inside_vehicles']), float(right['inside_vehicles'])
        dt = sec-start
        # The original FZP accounting integrates a linear stock interpolant.
        return float(left['ttt_veh_h_cumulative']) + (n0*dt + .5*(n1-n0)*dt*dt/(end-start))/3600

    def counts(state, road):
        assert state['vehicle_records']['complete']
        out = [0]*len(cells[road])
        for vehicle in state['vehicle_records']['records']:
            address = chains.get(int(vehicle['link_no']))
            if address is None or address[0] != road:
                continue
            position = address[1]+vehicle['position_m']
            index = min(len(out)-1, max(0, bisect.bisect_right(geometry['bounds'][road], position)-1))
            out[index] += 1
        return out

    results = {}
    for sec in (4500, 6000):
        forecast_dir = STUDY/f'closedloop_recorded{sec}_trace_stop150'
        forecast = load(pin(forecast_dir/'summary.json'))
        assert forecast['future_target_only'] and forecast['duration_sec'] == 150
        with gzip.open(pin(forecast_dir/'trace.json.gz'), 'rt', encoding='utf-8') as handle:
            response = json.load(handle)['response']
        initial = load(pin(RECORDS/f'state_{sec:06d}.json'))
        actual = load(pin(RECORDS/f'state_{sec+150:06d}.json'))
        derived = load(pin(RECORDS/f'obs150/derived_{sec+150:06d}.json'))
        assert derived['window'] == dict(start_s=sec, end_s=sec+150)
        final = response['freeway_frames'][-1]
        assert final['end_sec'] == sec+150
        pred_cost = forecast['cases']['recorded']['ttt_omega_veh_h']
        cost_from_response = sum(sum(row['inside_veh'].values())*row['dt_h'] for row in response['residence'])
        assert math.isclose(pred_cost, cost_from_response, abs_tol=1e-8)
        roads = {}
        for road in cells:
            n0, observed = counts(initial, road), counts(actual, road)
            predicted = final['model_stock_veh']['freeway:'+road]
            model_initial = response['initial_freeway_operands']['model_stock_veh']['freeway:'+road]
            assert math.isclose(sum(n0), model_initial, abs_tol=1e-7)
            assert len(final['freeway_density'][road]) == len(observed) == 31
            # The frame does not record the effective lane denominator. Use
            # the conserved freeway stock, not density times static lane-km.
            roads[road] = dict(initial_stock_veh=sum(n0), observed_final_stock_veh=sum(observed),
                               predicted_final_stock_veh=predicted,
                               error_veh=predicted-sum(observed),
                               observed_change_veh=sum(observed)-sum(n0),
                               predicted_change_veh=predicted-model_initial)
        for name, row in forecast['ramps'].items():
            released = sum(frame['actual_ramp_release_veh_h'].get(name, 0)*(frame['end_sec']-frame['start_sec'])/3600
                           for frame in response['freeway_frames'])
            assert math.isclose(released, row['predicted']['merge'], abs_tol=1e-7)
            assert abs(row['stock_conservation_residual_veh']) < 1e-7
        for road, ramp_ids, off_ids in (
                ('FW_E', (10639,10681,10490,10484), (10643,10682,10481,10483)),
                ('FW_W', (10644,10646,10482,10480), (10645,10638,10479,10491))):
            transfers = response['transfers']
            native = dict(
                source=derived['source_boundary'][road]['admitted_window'],
                merge=sum(forecast['ramps']['RM_C'+str(ramp)]['actual']['merge'] for ramp in ramp_ids),
                off=sum(derived['boundaries']['off_entry:'+str(off)]['cross'] for off in off_ids),
                terminal=derived['boundaries']['chain_end:'+road]['cross'],
                removed=sum(1 for row in derived['removals']['rows']
                            if chains.get(int(row['link']), (None,None))[0] == road))
            model = dict(
                source=sum(row['vehicles'] for row in transfers
                           if row['source']=='origin:'+road and row['target']=='freeway:'+road),
                merge=sum(forecast['ramps']['RM_C'+str(ramp)]['predicted']['merge'] for ramp in ramp_ids),
                off=sum(row['vehicles'] for row in transfers
                        if row['source']=='freeway:'+road and row['target'].startswith('storage:')),
                terminal=sum(row['vehicles'] for row in transfers
                             if row['source']=='freeway:'+road and row['target']=='external:terminal:'+road),
                removed=0.)
            native_change = native['source']+native['merge']-native['off']-native['terminal']-native['removed']
            model_change = model['source']+model['merge']-model['off']-model['terminal']
            assert abs(native_change-roads[road]['observed_change_veh']) < 1e-7
            assert abs(model_change-roads[road]['predicted_change_veh']) < 1e-7
            contributions = {key:(model[key]-native[key])*(1 if key in ('source','merge') else -1)
                             for key in native}
            assert math.isclose(sum(contributions.values()), roads[road]['error_veh'], abs_tol=1e-7)
            roads[road]['boundary_balance'] = dict(actual=native, predicted=model,
                stock_error_contributions_veh=contributions, closure_pass=True)
        selection = load(pin(STUDY/f'closedloop_recorded{sec}_select_check_stop/summary.json'))
        held, selected = selection['results']['held_actual'], selection['results']['selected']
        selection_delta = {key:selected[key]-held[key] for key in (
            'ttt_omega_veh_h', 'tracked_outside_residence_veh_h', 'ttt_with_tracked_outside_veh_h')}
        actual_cost = cumulative_at(sec+150)-cumulative_at(sec)
        results[str(sec)] = dict(
            command_conditioned_150s=dict(predicted_omega_ttt_veh_h=pred_cost,
                observed_omega_ttt_veh_h=actual_cost, prediction_error_veh_h=pred_cost-actual_cost,
                roads=roads, ramps=forecast['ramps']),
            planned_sequence_450s=dict(canonical_selected_minus_held=selection_delta,
                surrogate=selection['surrogate']))
    result = dict(purpose='Stopped-run diagnosis only; objective, configuration and coefficients unchanged',
        initial_states_s=[4500,6000], source_run=str(RECORDS), results=results,
        future_inputs_used_for_prediction=False, new_native_runs=0, fits=0,
        new_optimizer_iterations=0,
        limitations=[
            'The450s planned selected-minus-held differences are predictions, not observed causal gains.',
            'The150s tests condition on actual applied joint green/offset/VSL/meter commands, not isolated levers.',
            'Absolute response error does not establish candidate ranking error; a common-state native counterfactual is absent.',
            'Native OmegaTTT uses the existing5s FZP linear-stock integral; endpoint cell stock uses complete150s snapshots.',
            'No per-cell predicted stock or speed comparison: saved frames omit effective lane counts and speeds. Road totals use the conserved stock ledger.',
            'Only two current-run intervals tested; not independent-seed gain qualification.',
            'Outside modeled residence is diagnostic and does not include every uninserted/native outside cost.'],
        sources=sources)
    path = HERE/'stopped_response_diagnosis.json'
    assert not path.exists(), 'Preserve previous completed diagnosis'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for sec, row in results.items():
        step = row['command_conditioned_150s']
        print(json.dumps(dict(start_s=sec,
            predicted_ttt=step['predicted_omega_ttt_veh_h'], observed_ttt=step['observed_omega_ttt_veh_h'],
            roads={road:{key:value for key,value in values.items() if key not in ('cells','largest_errors')}
                   for road,values in step['roads'].items()},
            planned_450s=row['planned_sequence_450s']),ensure_ascii=False))


def mechanism_audit():
    """Attribute existing response errors without another model rollout."""
    sources = {}

    def pin(path):
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    manifest = load(pin(STUDY/'heldout53_response_v2/candidate_manifest.json'))
    reference_path = ROOT/manifest['sources']['reference_config']['path']
    reference = load(pin(reference_path))
    assert sources[str(reference_path)] == manifest['sources']['reference_config']['sha256']
    assert manifest['lane_groups'] is False
    assert not reference['freeway'].get('ramp_lane_coupling')
    assert not reference['freeway'].get('ramp_lane_exchange')
    network_path = ROOT/manifest['sources']['network']['path']
    tree = ET.fromstring(pin(network_path).read_bytes())
    assert sources[str(network_path)] == manifest['sources']['network']['sha256']
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    # These physical positions are already after the on-ramp choices.
    assert links['10777'].find('toLinkEndPt').get('lane').split()[0] == '127'
    assert links['10695'].find('fromLinkEndPt').get('lane').split()[0] == '127'
    assert links['10695'].find('toLinkEndPt').get('lane').split()[0] == '38'
    for name in ('lane_ramp_runtime.py','physical_ramp_boundary.py',
                 'vissim_stackelberg_adapter.py','lane_plant_runtime.py'):
        pin(ROOT/'evaluation/controllers'/name)
    with pin(STUDY/'selected/obs150/obs150_detectors_v2.csv').open(encoding='utf-8-sig',newline='') as handle:
        heads = [x for x in csv.DictReader(handle) if x['role']=='meter_head' and x['link']=='10681']
    assert {x['lane'] for x in heads} == {'1','2'}
    position = json.loads(heads[0]['geometry_assert'])['head_position_m']
    results = {}
    for sec in (4500,6000):
        folder = STUDY/f'closedloop_recorded{sec}_trace_stop150'
        with gzip.open(pin(folder/'trace.json.gz'),'rt',encoding='utf-8') as handle:
            trace = json.load(handle)
        response = trace['response']
        forecast = load(pin(folder/'summary.json'))
        initial = load(pin(RECORDS/f'state_{sec:06d}.json'))
        final = load(pin(RECORDS/f'state_{sec+150:06d}.json'))
        derived = load(pin(RECORDS/f'obs150/derived_{sec+150:06d}.json'))
        ownership = trace['initial_model_observation_summary']['projection_diagnostics']['physical_stock_assignment_by_link']
        source = 'storage:in_SC1001_W'
        owned = {link:row[source] for link,row in ownership.items() if row.get(source,0)>0}
        known_city = sum(owned.get(link,0) for link in ('127','10777','10695'))
        stock = response['initial_freeway_operands']['model_stock_veh'][source]
        incoming = sum(x['vehicles'] for x in response['transfers'] if x['target']==source)
        outgoing = {}
        for row in response['transfers']:
            if row['source']==source:
                outgoing[row['target']] = outgoing.get(row['target'],0)+row['vehicles']
        assert incoming == 0 and abs(response['freeway_frames'][-1]['model_stock_veh'][source]) < 1e-7
        assert math.isclose(sum(owned.values()),stock,abs_tol=1e-7)
        assert math.isclose(sum(outgoing.values()),stock,abs_tol=1e-7)
        ramp_targets = {'movement:SC1001_W_to_onE','movement:SC1001_W_to_onW'}
        city_out = sum(value for key,value in outgoing.items() if key not in ramp_targets)
        gate = dict(initial_stock_veh=stock, initial_physical_owners=owned,
            certainly_already_city_veh=known_city, model_initial_stock_allocation=outgoing,
            model_city_veh=city_out, initial_source_receives_new_flow_veh=incoming,
            minimum_wrong_city_to_ramp_family_veh=max(0.,known_city-city_out),
            bound_scope='Existing initial stock only; not an individual-vehicle attribution or an east-ramp-only bound',
            complete_route_envelope_available=('vehicle_routes' in initial))
        ramp = forecast['ramps']['RM_C10681']

        def lane_stocks(raw):
            assert raw['vehicle_records']['complete']
            output = {str(i):dict(pre=0,post=0) for i in (1,2)}
            for vehicle in raw['vehicle_records']['records']:
                if vehicle['link_no']==10681:
                    output[str(vehicle['lane_no'])]['post' if vehicle['position_m']>=position else 'pre'] += 1
            return output

        initial_lanes, final_lanes = lane_stocks(initial),lane_stocks(final)
        observed_head = {h['lane']:derived['boundaries'][h['boundary_ref']]['cross'] for h in heads}
        predicted_head = {str(i+1):sum(x['accepted_total_veh'] for x in response['resource_allocations']
            if x['kind']=='physical_ramp_head_service' and x['resource']=='RM_C10681:'+str(i)) for i in range(2)}
        receiving = sum(x['available_veh'] for x in response['resource_allocations']
                        if x['kind']=='physical_ramp_merge_physical_receiving' and x['resource']=='RM_C10681')
        initial_post = sum(row['post'] for row in initial_lanes.values())
        final_post = sum(row['post'] for row in final_lanes.values())
        assert math.isclose(initial_post+sum(observed_head.values())-ramp['actual']['merge'],final_post,abs_tol=1e-7)
        assert math.isclose(sum(predicted_head.values()),ramp['predicted']['head'],abs_tol=1e-7)
        predicted_post = initial_post+sum(predicted_head.values())-ramp['predicted']['merge']
        upper_by_lane = {i:min(receiving/2.,initial_lanes[i]['post']+predicted_head[i]) for i in ('1','2')}
        upper = sum(upper_by_lane.values())
        assert ramp['predicted']['merge'] <= upper+1e-7
        merger = dict(initial_native_lane_stocks=initial_lanes,final_native_lane_stocks=final_lanes,
            native_head_by_lane=observed_head,predicted_head_by_lane=predicted_head,
            actual_merge_veh=ramp['actual']['merge'], predicted_merge_veh=ramp['predicted']['merge'],
            observed_posthead_change_veh=final_post-initial_post,
            predicted_posthead_change_veh=predicted_post-initial_post,
            predicted_total_receiving_budget_veh=receiving,
            predicted_equal_lane_budget_veh=receiving/2.,
            optimistic_merge_bound_given_predicted_receiving_and_head_veh=upper,
            conditional_bound_by_lane_veh=upper_by_lane,
            observed_minus_conditional_bound_veh=ramp['actual']['merge']-upper,
            bound_scope='Fixed predicted receiving/head histories and initialized post-head stock; removes travel delay optimistically. Not a bound over all controls, receiving laws or lane exchanges.',
            native_within_interval_lane_changes_observed=False)
        results[str(sec)] = dict(initial_destination_ownership=gate,posthead_merge_10681=merger)
    document = dict(purpose='Saved-response mechanism diagnosis; no objective, model or configuration change',
        forecasts=0,native_runs=0,optimizer_iterations=0,calibration=False,results=results,sources=sources)
    output=HERE/'stopped_mechanism_audit.json'
    assert not output.exists(), 'Preserve prior mechanism audit'
    output.write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))


def native_lane_audit():
    """One read-only FZP pass; retain two narrow windows for native lane checks."""
    manifest = load(STUDY/'heldout53_response_v2/candidate_manifest.json')
    network_path = ROOT/manifest['sources']['network']['path']
    network_bytes = network_path.read_bytes()
    assert hashlib.sha256(network_bytes).hexdigest() == manifest['sources']['network']['sha256']
    network = ET.fromstring(network_bytes)
    head_positions = {float(row.get('pos')) for row in network.findall('./signalHeads/signalHead')
                      if row.get('lane').split()[0]=='10681'}
    assert len(head_positions)==1
    head, = head_positions
    fzp, = (RECORDS.parent/'vissim_eval').glob('*.fzp')
    cache = HERE/'stopped_native_windows.json.gz'
    output = HERE/'stopped_native_lane_audit.json'
    assert not output.exists(), 'Preserve completed native lane audit'
    if cache.exists():
        with gzip.open(cache,'rt',encoding='utf-8') as handle:
            recorded = json.load(handle)
        signature=fzp.stat()
        assert recorded['source']['size']==signature.st_size
        assert recorded['source']['mtime_ns']==signature.st_mtime_ns
    else:
        before = fzp.stat()
        times, frames, names = [], {}, None
        digest = hashlib.sha256()
        required = ('SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED',
                    'ROUTDECNO','ROUTENO','ROUTDECTYPE','NEXTLINK\\NO','DESTLANE','LNCHG')
        with fzp.open('rb') as handle:
            for line in handle:
                digest.update(line)
                if line.startswith(b'$VEHICLE:'):
                    names = [x.strip().upper() for x in line.decode('ascii').split(':',1)[1].split(';')]
                    indexes = {name:names.index(name) for name in required}
                    continue
                if names is None or not line.strip() or line.startswith((b'*',b'$')):
                    continue
                stamp = float(line.split(b';',1)[0])
                if stamp > 6155.1+1e-7:
                    break
                if not (4495-1e-7 <= stamp <= 4655.1+1e-7 or 5995-1e-7 <= stamp <= 6155.1+1e-7):
                    continue
                columns = line.strip().split(b';')
                assert len(columns)==len(names)
                values = {name:columns[index].strip() for name,index in indexes.items()}
                key = str(stamp)
                if key not in frames:
                    assert not times or stamp > times[-1]
                    times.append(stamp);frames[key] = []
                row = [int(values['NO']),int(values['LANE\\LINK\\NO']),int(values['LANE\\INDEX']),
                       float(values['POS']),float(values['SPEED'])]
                row.extend(values[name].decode('ascii') for name in required[6:])
                frames[key].append(row)
        after = fzp.stat()
        assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        assert names is not None and times
        recorded = dict(source=dict(path=str(fzp),size=before.st_size,mtime_ns=before.st_mtime_ns,
            read_prefix_sha256=digest.hexdigest(),sha_scope='Bytes actually read through first row after6155.1s; not a whole-file hash'),
            columns=['vehicle','link','lane','position_m','speed_kph',*required[6:]],frames=frames)
        with gzip.open(cache,'wt',encoding='utf-8') as handle:
            json.dump(recorded,handle,ensure_ascii=False,allow_nan=False)
    results = {}
    for start in (4500,6000):
        end = start+150
        expected = load(STUDY/f'closedloop_recorded{start}_trace_stop150/summary.json')['ramps']['RM_C10681']['actual']
        snapshots = []
        for sec in (start,end):
            raw = load(RECORDS/f'state_{sec:06d}.json')
            assert raw['vehicle_records']['complete'] and raw['vehicle_records']['paused_at_sim_sec']==sec
            snapshots.append((float(sec),{v['veh_no']:[v['link_no'],v['lane_no'],v['position_m'],v['speed_kph']]
                for v in raw['vehicle_records']['records']}))
        middle = [(float(time),{r[0]:r[1:5] for r in rows}) for time,rows in recorded['frames'].items()
                  if start < float(time) < end]
        ordered = [snapshots[0],*sorted(middle),snapshots[1]]
        assert max(b[0]-a[0] for a,b in zip(ordered,ordered[1:])) <= 5.00001
        events = dict(entries=[],merges=[],unresolved_disappearances=[],lane_changes=[],head_crossings=[])
        for (ta,a),(tb,b) in zip(ordered,ordered[1:]):
            aa = {vid:v for vid,v in a.items() if v[0]==10681}
            bb = {vid:v for vid,v in b.items() if v[0]==10681}
            for vid,v in bb.items():
                previous = a.get(vid)
                if vid not in aa:
                    events['entries'].append(dict(vehicle=vid,lower_sec=ta,upper_sec=tb,
                        from_link=previous[0] if previous else None,to_lane=v[1]))
                elif aa[vid][1] != v[1]:
                    events['lane_changes'].append(dict(vehicle=vid,lower_sec=ta,upper_sec=tb,
                        from_lane=aa[vid][1],to_lane=v[1],from_position_m=aa[vid][2],to_position_m=v[2]))
                if previous and previous[0]==10681 and previous[2]<head<=v[2]:
                    events['head_crossings'].append(dict(vehicle=vid,lower_sec=ta,upper_sec=tb,
                        from_lane=previous[1],to_lane=v[1]))
            for vid,v in aa.items():
                if vid in bb:
                    continue
                current=b.get(vid)
                event=dict(vehicle=vid,lower_sec=ta,upper_sec=tb,last_ramp_lane=v[1],
                           last_ramp_position_m=v[2],last_ramp_speed_kph=v[3],
                           first_next_link=current[0] if current else None,
                           first_next_lane=current[1] if current else None,
                           first_next_position_m=current[2] if current else None)
                events['merges' if current and current[0]==2 else 'unresolved_disappearances'].append(event)
        counts={key:len(rows) for key,rows in events.items()}
        checks=dict(entry_count_matches_native=counts['entries']==expected['arrival'],
            merge_count_matches_native=counts['merges']==expected['merge'],
            head_count_matches_native=counts['head_crossings']==expected['head'],
            no_unresolved=counts['unresolved_disappearances']==0,
            stock_closure=len({vid for vid,v in ordered[0][1].items() if v[0]==10681})+counts['entries']-
                counts['merges']-counts['unresolved_disappearances']==expected['final_stock'])
        results[str(start)] = dict(window_s=[start,end],sampling='FZP5s at .1 phase plus exact paused COM endpoints',
            checks=checks,counts=counts,
            merges_by_last_observed_ramp_lane=dict(Counter(str(x['last_ramp_lane']) for x in events['merges'])),
            merges_by_first_observed_mainline_lane=dict(Counter(str(x['first_next_lane']) for x in events['merges'])),
            observed_lane_changes_by_direction=dict(Counter(f"{x['from_lane']}->{x['to_lane']}" for x in events['lane_changes'])),
            events=events)
    document=dict(source=recorded['source'],cache=str(cache),results=results,
        checks_pass=all(all(row['checks'].values()) for row in results.values()),
        limitations=['5s observations give event brackets and sampled lane changes, not exact merge times or all lane changes.',
                    'Last ramp lane and first mainline lane need not equal the lane at the unobserved transition instant.',
                    'Future frames are validation data only, never prediction inputs.',
                    'No model parameter or objective modification; no prediction or new simulator run.'])
    output.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:{k:v for k,v in row.items() if k!='events'} for key,row in results.items()},ensure_ascii=False))
    assert document['checks_pass'], 'Preserved mismatch; do not treat partial event capture as complete'


def conflict_audit():
    """Observed lane flows and the existing gap-law operands; no parameter fit."""
    sys.path.insert(0,str(ROOT))
    from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph
    cache=HERE/'stopped_native_windows.json.gz'
    with gzip.open(cache,'rt',encoding='utf-8') as handle:
        recorded=json.load(handle)
    assert load(HERE/'stopped_native_lane_audit.json')['checks_pass']
    manifest=load(STUDY/'heldout53_response_v2/candidate_manifest.json')
    geometry=load(ROOT/manifest['sources']['geometry']['path'])
    reference=load(ROOT/manifest['sources']['reference_config']['path'])
    node=reference['freeway']['physical_ramp_receiving_nodes']['RM_C10681']
    offset=next(x['offset_m'] for x in geometry['chains']['FW_E'] if x['link']==2)
    upstream=next(x for x in geometry['cells'] if x['road']=='FW_E' and x['cell']==11)['end_m']-offset
    network=ET.fromstring((ROOT/manifest['sources']['network']['path']).read_bytes())
    ramp=network.find("./links/link[@no='10681']")
    assert ramp.find('toLinkEndPt').get('lane')=='2 1'
    cuts={'upstream_model_cell_end':upstream,
          'just_upstream_of_merge':float(ramp.find('toLinkEndPt').get('pos'))-.001}
    results={}
    for start in (4500,6000):
        frames=[]
        for sec in (start,start+150):
            raw=load(RECORDS/f'state_{sec:06d}.json')
            assert raw['vehicle_records']['complete']
            frames.append((sec,{v['veh_no']:[v['link_no'],v['lane_no'],v['position_m'],v['speed_kph']]
                for v in raw['vehicle_records']['records']}))
        frames.extend((float(k),{v[0]:v[1:5] for v in rows}) for k,rows in recorded['frames'].items()
                      if start<float(k)<start+150)
        frames.sort()
        section={}
        for name,position in cuts.items():
            exact=Counter();uncertain=Counter();ids=[]
            for (ta,a),(tb,b) in zip(frames,frames[1:]):
                for vid,v in a.items():
                    z=b.get(vid)
                    if v[0]==2 and z and z[0]==2 and v[2]<position<=z[2]:
                        ids.append(vid)
                        if v[1]==z[1]:exact[v[1]]+=1
                        else:uncertain[(v[1],z[1])]+=1
            assert len(ids)==len(set(ids))
            bounds={str(lane):dict(lower_veh=exact[lane],
                upper_veh=exact[lane]+sum(n for pair,n in uncertain.items() if lane in pair)) for lane in range(1,5)}
            section[name]=dict(link=2,position_m=position,crossings_veh=len(ids),
                no_observed_lane_change_counts=dict(exact),
                changed_lane_brackets={f'{a}->{b}':n for (a,b),n in uncertain.items()},
                lane_crossing_bounds=bounds,
                observed_four_lane_mean_vph=len(ids)*24/4,
                lane2_vph_bounds=[bounds['2']['lower_veh']*24,bounds['2']['upper_veh']*24])
        with gzip.open(STUDY/f'closedloop_recorded{start}_trace_stop150/trace.json.gz','rt',encoding='utf-8') as handle:
            response=json.load(handle)['response']
        allocations=[x for x in response['resource_allocations'] if x['resource']=='RM_C10681']
        canonical={x['start_sec']:x['available_veh'] for x in allocations if x['kind']=='physical_ramp_merge_canonical_receiving'}
        physical=[x for x in allocations if x['kind']=='physical_ramp_merge_physical_receiving']
        assert len(physical)==150
        inferred=[]
        for row in physical:
            assert row['available_veh'] < canonical[row['start_sec']]-1e-8
            target=row['available_veh']*3600/2
            lo,hi=0.,20000.
            assert gap_acceptance_supply_vph(lo,node['critical_gap_sec'],node['followup_sec'])>=target
            assert gap_acceptance_supply_vph(hi,node['critical_gap_sec'],node['followup_sec'])<=target
            for _ in range(60):
                mid=(lo+hi)/2
                if gap_acceptance_supply_vph(mid,node['critical_gap_sec'],node['followup_sec'])>target:lo=mid
                else:hi=mid
            inferred.append((lo+hi)/2)
        results[str(start)]=dict(native_sections=section,
            equivalent_model_conflicting_vph=dict(mean=sum(inferred)/len(inferred),minimum=min(inferred),maximum=max(inferred),
                source='Inverse of the unchanged gap law, each recorded1s physical receiving budget; canonical bound strictly slack',
                critical_gap_sec=node['critical_gap_sec'],followup_sec=node['followup_sec']),
            interpretation='The native conflict-lane rate and four-lane mean differ; neither is automatically the correct effective conflicting stream.')
    path=HERE/'stopped_conflict_lane_audit.json'
    assert not path.exists()
    path.write_text(json.dumps(dict(results=results,source=recorded['source'],
        source_cache_sha256=hashlib.sha256(cache.read_bytes()).hexdigest(),
        limitations=['5s cross-section counts use observed ID transitions. Lane-change brackets bound observed start/end lanes, not unseen intermediate lane excursions.',
            'Inverse-gap rates are model-implied operands, not measured flows or independently fitted parameters.',
            'Period averages hide platooning, yielding and instantaneous gaps; this does not qualify a new receiving law.',
            'Future native samples are validation only. New forecasts, fits, simulations and optimizer iterations are all zero.']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1:] == ['--conflict']:
        conflict_audit()
    elif sys.argv[1:] == ['--native-lanes']:
        native_lane_audit()
    elif sys.argv[1:] == ['--mechanisms']:
        mechanism_audit()
    else:
        assert not sys.argv[1:]
        main()
