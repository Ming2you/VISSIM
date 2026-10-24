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


def ramp10484_native_audit():
    """Cache two closed native windows once; no forecast, simulator or fitting."""
    import statistics
    import time
    h=STUDY/'heldout53_response_v2';runs=Path('D:/VISSIM_runs/20260928_release2670_s53_v2')
    out=HERE/'recovery_flow_audit/native10484';out.mkdir(exist_ok=True)
    assert not (out/'summary.json').exists(), 'Keep the completed diagnosis'
    start,end=2670.1,3120.1;manifest=load(STUDY/'selected/plant_n31_v2.json')
    netpath=ROOT/manifest['sources']['network']['path'];geo_path=ROOT/manifest['sources']['geometry']['path']
    assert hashlib.sha256(netpath.read_bytes()).hexdigest()==manifest['sources']['network']['sha256']
    assert hashlib.sha256(geo_path.read_bytes()).hexdigest()==manifest['sources']['geometry']['sha256']
    network=ET.fromstring(netpath.read_bytes());geometry=load(geo_path)
    ramp=network.find("./links/link[@no='10484']");target=ramp.find('toLinkEndPt')
    target_link,target_lane=map(int,target.get('lane').split());merge_pos=float(target.get('pos'))
    heads={float(z.get('pos')) for z in network.findall('./signalHeads/signalHead') if z.get('lane').split()[0]=='10484'}
    assert len(heads)==1;head=heads.pop()
    chain={z['link']:z for z in geometry['chains']['FW_E']}
    cells={z['cell']:z for z in geometry['cells'] if z['road']=='FW_E' and 21<=z['cell']<=25}
    relevant={31,10484,119,10702,24};assert target_link==24 and target_lane==1
    def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save(out/'protocol.json',dict(arms=['hold','release'],seed=53,window=[start,end],
        new_native=0,new_forecasts=0,calibration=False,raw_scans_max=2,
        network_sha256=manifest['sources']['network']['sha256'],geometry_sha256=manifest['sources']['geometry']['sha256'],
        ramp=10484,head_position_m=head,target_link=target_link,target_lane=target_lane,merge_position_m=merge_pos,
        constraints='Existing STOP kept. User confirmed other VISSIM is an open idle window; never attach/close it.',
        limitations='5s event brackets and current lane labels, not exact gaps, lateral occupancy, acceleration or capacity. Future snapshots are diagnostic only.'))
    summaries=[];common_initial=None;wall=time.perf_counter();all_lane_rows=[]
    for arm in ('hold','release'):
        run=runs/arm/'run';receipt=load(run/'run.json')
        assert receipt['completed'] and receipt['finished'] and not receipt['owned_native_alive']
        fzp,=(run/'vissim_eval').glob('*.fzp');cache=out/(arm+'_frames.json.gz');source=fzp.stat()
        if cache.exists():
            with gzip.open(cache,'rt',encoding='utf-8') as f:recorded=json.load(f)
            assert recorded['source']['size']==source.st_size and recorded['source']['mtime_ns']==source.st_mtime_ns
        else:
            frames={};names=None;digest=hashlib.sha256();count=0
            required=('NO','LANE\\LINK\\NO','LANE\\INDEX','POS','SPEED','LENGTH','POSLAT','DESTLANE','LNCHG')
            with fzp.open('rb') as f:
                for raw in f:
                    digest.update(raw)
                    if raw.startswith(b'$VEHICLE:'):
                        names=[x.strip() for x in raw.decode('ascii').split(':',1)[1].split(';')]
                        ix={k:names.index(k) for k in ('SIMSEC',*required)}
                        assert ix['SIMSEC']==0
                        continue
                    if names is None or not raw.strip() or raw.startswith((b'*',b'$')):continue
                    t=float(raw.split(b';',1)[0]);count+=1
                    if not start-1e-6<=t<=end+1e-6:continue
                    frame=frames.setdefault(str(t),[]);x=raw.strip().split(b';');assert len(x)==len(names)
                    link=int(x[ix['LANE\\LINK\\NO']])
                    if link not in relevant:continue
                    frame.append([int(x[ix['NO']]),link,int(x[ix['LANE\\INDEX']]),
                        *[float(x[ix[k]]) for k in ('POS','SPEED','LENGTH','POSLAT')],
                        *[x[ix[k]].decode('ascii').strip() for k in ('DESTLANE','LNCHG')]])
            old=load(h/(arm+'_native.json'))['raw_evidence']
            assert digest.hexdigest()==old['sha256'] and count==old['rows'], 'FZP differs from completed extraction'
            assert (source.st_size,source.st_mtime_ns)==(fzp.stat().st_size,fzp.stat().st_mtime_ns)
            recorded=dict(source=dict(path=str(fzp),size=source.st_size,mtime_ns=source.st_mtime_ns,sha256=digest.hexdigest()),
                columns=['vehicle','link','lane','position_m','speed_kmh','length_m','poslat','destlane','lnchg'],frames=frames)
            with gzip.open(cache,'wt',encoding='utf-8') as f:json.dump(recorded,f,allow_nan=False)
        frames=[(float(k),{z[0]:z for z in rows}) for k,rows in recorded['frames'].items()];frames.sort()
        assert len(frames)==91 and frames[0][0]==start and frames[-1][0]==end
        assert all(abs(b[0]-a[0]-5)<1e-6 for a,b in zip(frames,frames[1:]))
        if common_initial is None:common_initial=frames[0][1]
        else:assert common_initial==frames[0][1]
        cohorts=load(h/f'observations/{arm}/port_cohorts_30s.json')
        with (h/f'observations/{arm}/cells_30s.csv').open(encoding='utf-8-sig',newline='') as f:
            native_cells={(float(z['time_s']),int(z['cell'])):z for z in csv.DictReader(f) if z['road']=='FW_E'}
        entries=[];merges=[];head_events=[];unknown=[];lane_rows=[];max_stock_error=0;max_speed_error=0.
        for t,frame in frames:
            if str(t) in cohorts:
                now=sorted([z[3],z[4],z[2]] for z in frame.values() if z[1]==10484)
                assert now==sorted(cohorts[str(t)]['10484'])
            for cell,c in cells.items():
                vs=[z for z in frame.values() if z[1] in chain and c['start_m']<=chain[z[1]]['offset_m']+z[3]<c['end_m']]
                if (t,cell) in native_cells:
                    truth=native_cells[t,cell];max_stock_error=max(max_stock_error,abs(len(vs)-float(truth['n_veh'])))
                    if vs:max_speed_error=max(max_speed_error,abs(statistics.mean(z[4] for z in vs)-float(truth['v_kmh'])))
                for lane in (1,2,3):
                    group=[z for z in vs if z[2]==lane]
                    lane_rows.append(dict(arm=arm,time_s=t,cell=cell,lane=lane,n=len(group),
                        speed_sum=sum(z[4] for z in group),mean_speed=statistics.mean(z[4] for z in group) if group else None,
                        stopped=sum(z[4]<5 for z in group),slow=sum(z[4]<15 for z in group)))
        assert max_stock_error==0 and max_speed_error<1e-7,(max_stock_error,max_speed_error)
        for (ta,a),(tb,b) in zip(frames,frames[1:]):
            for vid,z in b.items():
                if z[1]!=10484:continue
                prev=a.get(vid)
                if prev is None or prev[1]!=10484:entries.append(dict(vehicle=vid,lo=ta,hi=tb))
            for vid,z in a.items():
                if z[1]!=10484:continue
                nxt=b.get(vid)
                is_merge=nxt is not None and nxt[1]==target_link
                passed_head=z[3]<head and (is_merge or nxt is not None and nxt[1]==10484 and nxt[3]>=head)
                if passed_head:head_events.append(dict(vehicle=vid,lo=ta,hi=tb))
                if is_merge:
                    merges.append(dict(vehicle=vid,lo=ta,hi=tb,last_ramp_position=z[3],last_ramp_speed=z[4],
                        first_mainline_lane=nxt[2],first_mainline_speed=nxt[4]))
                elif nxt is None or nxt[1]!=10484:unknown.append(dict(vehicle=vid,lo=ta,hi=tb,to_link=None if nxt is None else nxt[1]))
        with (h/f'observations/{arm}/ports_30s.csv').open(encoding='utf-8-sig',newline='') as f:
            ports=[z for z in csv.DictReader(f) if z['connector']=='10484' and start<float(z['window_end_s'])<=end]
        assert len(ports)==15 and not unknown
        assert len(entries)==sum(float(z['arrivals_veh']) for z in ports)
        assert len(merges)==sum(float(z['departures_veh']) for z in ports)
        post=lambda frame:sum(z[1]==10484 and z[3]>=head for z in frame.values())
        assert len(head_events)==len(merges)+post(frames[-1][1])-post(frames[0][1])
        head_by_id={z['vehicle']:z for z in head_events};merge_by_id={z['vehicle']:z for z in merges};trips=[]
        assert len(head_by_id)==len(head_events) and len(merge_by_id)==len(merges)
        for vid,event in head_by_id.items():
            m=merge_by_id.get(vid)
            trips.append(dict(vehicle=vid,head_lo=event['lo'],head_hi=event['hi'],completed=m is not None,
                duration_lower=max(0.,(m['lo'] if m else end)-event['hi']),
                duration_upper=m['hi']-event['lo'] if m else None))
        complete=[z for z in trips if z['completed']];censored=[z for z in trips if not z['completed']]
        bins=[]
        for lo,hi in ((start,start+150),(start+150,start+300),(start+300,end)):
            group=[z for z in complete if lo<=z['head_lo']<hi]
            bins.append(dict(head_window=[lo,hi],completed_count=len(group),
                mean_duration_lower=statistics.mean(z['duration_lower'] for z in group) if group else None,
                mean_duration_upper=statistics.mean(z['duration_upper'] for z in group) if group else None,
                right_censored=sum(lo<=z['head_lo']<hi for z in censored)))
        lane_summary=[]
        for cell in cells:
            for lane in (1,2,3):
                group=[z for z in lane_rows if z['cell']==cell and z['lane']==lane and z['time_s']>=start+150]
                weight=sum(z['n'] for z in group)
                lane_summary.append(dict(cell=cell,lane=lane,mean_speed=sum(z['speed_sum'] for z in group)/weight if weight else None,
                    mean_stock=weight/len(group),slow_fraction=sum(z['slow'] for z in group)/weight if weight else None))
        save(out/(arm+'_events.json'),dict(entries=entries,merges=merges,head_events=head_events,unknown=unknown,trips=trips))
        all_lane_rows.extend(lane_rows)
        summaries.append(dict(arm=arm,frames=len(frames),cache_sha256=hashlib.sha256(cache.read_bytes()).hexdigest(),source=recorded['source'],
            same_initial=True,cohort_match=True,cell_stock_error=max_stock_error,cell_speed_error=max_speed_error,
            arrivals=len(entries),merges=len(merges),head_crossings=len(head_events),posthead_final=post(frames[-1][1]),
            completed_posthead_trips=len(complete),censored_posthead_trips=len(censored),
            travel_time_bins=bins,lane_summary_after2820=lane_summary,
            merge_first_observed_lanes=dict(Counter(z['first_mainline_lane'] for z in merges))))
        print(json.dumps(dict(arm=arm,entries=len(entries),merges=len(merges),head=len(head_events),trip_bins=bins)),flush=True)
    with (out/'lane_snapshots.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(all_lane_rows[0]));w.writeheader();w.writerows(all_lane_rows)
    save(out/'summary.json',dict(rows=summaries,new_native=0,new_forecasts=0,calibration=False,wall_sec=time.perf_counter()-wall,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations=['5s bracketed head/merge events, not interpolated exact times. Unfinished trips are retained as right-censored.',
            'Lane of first downstream sample may differ from lane at merge; lane changes and lateral occupancy inside5s remain unresolved.',
            'Lane speed summaries are vehicle-weighted snapshots2820.1..3120.1, not Lagrangian acceleration or capacity.',
            'All native data are retrospective diagnostics, not future inputs to an autonomous forecast.']))


def ramp10484_cached_sections():
    """Locate the retained bottleneck using cached IDs, not a fresh FZP scan."""
    out=HERE/'recovery_flow_audit/native10484';target=out/'sections.json'
    assert not target.exists()
    prior=load(out/'summary.json');protocol=load(out/'protocol.json')
    manifest=load(STUDY/'selected/plant_n31_v2.json');geometry=load(ROOT/manifest['sources']['geometry']['path'])
    chains={z['link']:z for z in geometry['chains']['FW_E']}
    cells={z['cell']:z for z in geometry['cells'] if z['road']=='FW_E'}
    merge=chains[24]['offset_m']+protocol['merge_position_m'];start,end=protocol['window']
    sections={'cell22_exit':cells[22]['end_m'],'before_merge':merge-1e-6,
              'cell23_exit':cells[23]['end_m'],'cell24_exit':cells[24]['end_m']}
    rows=[];max_error=0;spatial=[]
    for arm in ('hold','release'):
        p=out/(arm+'_frames.json.gz')
        assert hashlib.sha256(p.read_bytes()).hexdigest()==next(z['cache_sha256'] for z in prior['rows'] if z['arm']==arm)
        with gzip.open(p,'rt',encoding='utf-8') as f:d=json.load(f)
        frames=sorted((float(t),{z[0]:z for z in vs}) for t,vs in d['frames'].items())
        with (STUDY/f'heldout53_response_v2/observations/{arm}/flows_30s.csv').open(encoding='utf-8-sig',newline='') as f:
            truth={(float(z['window_end_s']),int(z['cell'])):z for z in csv.DictReader(f) if z['road']=='FW_E'}
        events={s:[] for s in sections}
        for (ta,a),(tb,b) in zip(frames,frames[1:]):
            for vid,z in a.items():
                nxt=b.get(vid)
                if nxt is None or nxt[1] not in chains:continue
                if z[1] in chains:sa=chains[z[1]]['offset_m']+z[3];lane=z[2]
                elif z[1]==10484:sa=merge;lane=1
                else:continue
                sb=chains[nxt[1]]['offset_m']+nxt[3]
                assert sb>=sa-1e-6
                for name,pos in sections.items():
                    if sa<pos<=sb:events[name].append(dict(vid=vid,lo=ta,hi=tb,from_lane=lane,to_lane=nxt[2],from_ramp=z[1]==10484))
        for name,cell in [('cell22_exit',22),('cell23_exit',23),('cell24_exit',24)]:
            for j in range(1,16):
                t=round(start+30*j,6);count=sum(t-30+1e-6<x['hi']<=t+1e-6 for x in events[name])
                expected=float(truth[t,cell]['downstream_crossings'])
                max_error=max(max_error,abs(count-expected))
        for lo,hi in ((start,start+150),(start+150,start+300),(start+300,end)):
            for name,values in events.items():
                chosen=[x for x in values if lo+1e-6<x['hi']<=hi+1e-6]
                known=Counter(x['from_lane'] for x in chosen if x['from_lane']==x['to_lane'])
                ambiguous=[x for x in chosen if x['from_lane']!=x['to_lane']]
                rows.append(dict(arm=arm,start=lo,end=hi,section=name,crossings=len(chosen),
                    same_lane_counts=dict(known),changed_lane_brackets=len(ambiguous),
                    target_lane_observed_endpoint_range=[known[1],known[1]+sum(1 in (x['from_lane'],x['to_lane']) for x in ambiguous)]))
        # Fixed diagnostic spatial bands around the actual merge point. No fit.
        for t,vs in frames:
            if t<start+150:continue
            for lane in (1,2,3):
                for name,low,high in [('upstream100m',merge-100,merge),('downstream100m',merge,merge+100)]:
                    group=[z for z in vs.values() if z[1] in chains and z[2]==lane and low<=chains[z[1]]['offset_m']+z[3]<high]
                    spatial.append(dict(arm=arm,time_s=t,lane=lane,band=name,n=len(group),
                        speed_sum=sum(z[4] for z in group),slow=sum(z[4]<15 for z in group)))
    assert max_error==0, 'Incomplete crossing capture; preserve failure, do not infer capacity'
    bands=[]
    for arm in ('hold','release'):
        for lane in (1,2,3):
            for name in ('upstream100m','downstream100m'):
                group=[z for z in spatial if z['arm']==arm and z['lane']==lane and z['band']==name];n=sum(z['n'] for z in group)
                bands.append(dict(arm=arm,lane=lane,band=name,mean_stock=n/len(group),
                    weighted_speed=sum(z['speed_sum'] for z in group)/n if n else None,
                    slow_fraction=sum(z['slow'] for z in group)/n if n else None))
    target.write_text(json.dumps(dict(rows=rows,spatial=bands,known_aggregate_crossing_error=max_error,
        new_native=0,new_rollouts=0,fzp_rescans=0,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limitations=['All mainline predecessor links and ramp10484-to-mainline crossings are included; counts match validated cell22/23/24 boundary totals per30s.',
            'Lane endpoint ranges are not strict bounds on hidden lane excursions inside5s.',
            'Throughput is realized flow, not independently identified capacity. Do not use it as a future prediction input.']),
        ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(max_crossing_error=max_error,rows=rows,spatial=bands)),flush=True)


def ramp10484_receiving_screen():
    """Reject simple receiving substitutions before adding a new dynamic state.

    Current native snapshots are conditional operands, never future inputs to a
    forecast. Integrated opportunities are not predicted or measured merges.
    No coefficient fitting, state propagation or production configuration edit.
    """
    sys.path.insert(0, str(ROOT))
    from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph

    source = HERE/'recovery_flow_audit/native10484'
    out = source/'receiving_screen'
    assert not out.exists(), 'Keep the completed or failed screen'
    out.mkdir()
    pins = {}

    def read(path):
        pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return load(path)

    def save(name, value):
        (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                        allow_nan=False)+'\n', encoding='utf-8')

    prior = read(source/'summary.json')
    geometry_manifest = read(STUDY/'selected/plant_n31_v2.json')
    geo_path = ROOT/geometry_manifest['sources']['geometry']['path']
    geometry = read(geo_path)
    assert pins[str(geo_path)] == geometry_manifest['sources']['geometry']['sha256']
    physical = {z['cell']: z for z in geometry['cells'] if z['road'] == 'FW_E'}
    parameters = read(HERE/'recovery_flow_audit/receiving_closure/protocol.json')
    # These are existing closure parameters, not locally identified capacities.
    rho_j, rho_c = parameters['rho_max'], parameters['rho_crit']
    road_capacity, ramp_capacity = parameters['mainline_capacity'], parameters['ramp_capacity']
    tc, tf = parameters['critical_gap_sec'], parameters['followup_sec']
    assert parameters['upstream_cell'] == 22 and parameters['merge_cell'] == 23
    assert rho_j > rho_c > 0
    assert all(physical[c]['canonical_segment_lanes'] == 3
               and all(piece['lanes'] == 3 for piece in physical[c]['physical_pieces'])
               for c in (22, 23))
    lengths = {c: (physical[c]['end_m']-physical[c]['start_m'])/1000 for c in (22, 23)}
    lane_path = source/'lane_snapshots.csv'
    pins[str(lane_path)] = hashlib.sha256(lane_path.read_bytes()).hexdigest()
    with lane_path.open(encoding='utf-8-sig', newline='') as f:
        lanes = {(z['arm'], float(z['time_s']), int(z['cell']), int(z['lane'])): z
                 for z in csv.DictReader(f)}
    variants = ['aggregate_current', 'target_lane_current',
                'target_lane_per_lane_capacity', 'target_lane_residual_priority']
    save('protocol.json', dict(variants=variants, seed=53, cells=[22, 23],
        control_cases=['hold', 'release'], window=[2670.1, 3120.1],
        calibration_candidates=0, autonomous_forecasts=0, new_native=0, fzp_rescans=0,
        formulas={
            'aggregate_current': 'min(R, C*f(rho23_avg), gap(rho22_avg*v22_avg))',
            'target_lane_current': 'min(R, C*f(rho23_lane1), gap(q22_lane1))',
            'target_lane_per_lane_capacity': 'min(R, C/3*f(rho23_lane1), gap(q22_lane1))',
            'target_lane_residual_priority': 'min(R, max(0,C/3*f(rho23_lane1)-q22_lane1), gap(q22_lane1))',
            'f': 'clip((rho_j-rho)/(rho_j-rho_c),0,1)',
            'q22_lane1': 'sum of snapshot lane1 vehicle speeds / cell22 length_km'},
        limitations=[
            'Each native state is a conditional input. No autonomous rollout or control-gain validation.',
            'C/3 is an explicit diagnostic assumption; existing road cap is not an identified local lane capacity.',
            'Residual variant assumes mainline priority and ignores cooperative yielding and lateral transfers.',
            'Snapshot rho*v is not a measured boundary flow; five-second sampling does not resolve gap timing.',
            'Observed merges are realized demand/eligibility/service, not a capacity label.',
            'Left/right/trapezoid sums are discretization checks, not strict physical confidence bounds.']))

    rows, summaries = [], []
    initial = None
    for arm in ('hold', 'release'):
        cache = source/(arm+'_frames.json.gz')
        pins[str(cache)] = hashlib.sha256(cache.read_bytes()).hexdigest()
        assert pins[str(cache)] == next(z['cache_sha256'] for z in prior['rows'] if z['arm'] == arm)
        with gzip.open(cache, 'rt', encoding='utf-8') as f:
            frames = json.load(f)['frames']
        stamps = sorted(map(float, frames))
        assert len(stamps) == 91 and stamps[0] == 2670.1 and stamps[-1] == 3120.1
        assert all(abs(b-a-5) < 1e-7 for a, b in zip(stamps, stamps[1:]))
        if initial is None:
            initial = frames[str(stamps[0])]
        else:
            assert initial == frames[str(stamps[0])]
        events = read(source/(arm+'_events.json'))
        assert not events['unknown']
        assert len(events['merges']) == next(z['merges'] for z in prior['rows'] if z['arm'] == arm)
        rates = {}
        for t in stamps:
            g22 = [lanes[arm, t, 22, j] for j in (1, 2, 3)]
            g23 = [lanes[arm, t, 23, j] for j in (1, 2, 3)]
            qa = sum(float(z['speed_sum']) for z in g22)/(3*lengths[22])
            q1 = float(g22[0]['speed_sum'])/lengths[22]
            ra = sum(float(z['n']) for z in g23)/(3*lengths[23])
            r1 = float(g23[0]['n'])/lengths[23]
            factor = lambda rho: min(1., max(0., (rho_j-rho)/(rho_j-rho_c)))
            ga = gap_acceptance_supply_vph(qa, tc, tf)
            g1 = gap_acceptance_supply_vph(q1, tc, tf)
            per_lane = road_capacity/3*factor(r1)
            values = [min(ramp_capacity, road_capacity*factor(ra), ga),
                      min(ramp_capacity, road_capacity*factor(r1), g1),
                      min(ramp_capacity, per_lane, g1),
                      min(ramp_capacity, max(0., per_lane-q1), g1)]
            assert all(math.isfinite(x) and 0 <= x <= ramp_capacity for x in values)
            rates[t] = dict(zip(variants, values))
            rows.append(dict(arm=arm, time_s=t, rho23_avg=ra, rho23_lane1=r1,
                             q22_avg_vphpl=qa, q22_lane1_vph=q1, **rates[t]))
        for start, end in ((2670.1, 2820.1), (2820.1, 2970.1), (2970.1, 3120.1)):
            ts = [t for t in stamps if start <= t <= end]
            assert len(ts) == 31
            observed = sum(start+1e-6 < z['hi'] <= end+1e-6 for z in events['merges'])
            heads = sum(start+1e-6 < z['hi'] <= end+1e-6 for z in events['head_events'])
            for variant in variants:
                left = math.fsum(rates[t][variant]*5/3600 for t in ts[:-1])
                right = math.fsum(rates[t][variant]*5/3600 for t in ts[1:])
                summaries.append(dict(arm=arm, start=start, end=end, variant=variant,
                    observed_merges=observed, observed_head_passages=heads,
                    opportunity_left_veh=left, opportunity_right_veh=right,
                    opportunity_trapezoid_veh=(left+right)/2))
    with (out/'snapshots.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    pins[str(Path(__file__))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    import evaluation.controllers.physical_ramp_boundary as ramp_source
    pins[ramp_source.__file__] = hashlib.sha256(Path(ramp_source.__file__).read_bytes()).hexdigest()
    save('summary.json', dict(rows=summaries, snapshot_rows=len(rows),
        parameter_changes=0, production_changes=0, autonomous_forecasts=0,
        new_native=0, fzp_rescans=0, adopted=False, gain_qualified=False, pins=pins,
        conclusion='Lane-only substitution does not repair the closure. Mainline-priority residual is an unqualified allocation assumption, not a calibrated receiving law.'))
    print(json.dumps(dict(output=str(out), rows=summaries)), flush=True)


def ramp10484_local_state_audit():
    """Exact endpoint mass/moment ledgers and a causal exchange-rate screen.

    This supplies and checks local state for a prospective conserved model; it
    does not advance a plant or claim that endpoint rates identify lane changes.
    """
    source = HERE/'recovery_flow_audit/native10484'
    out = source/'local_state'
    assert not out.exists(), 'Preserve completed/failed evidence'
    out.mkdir()
    pins = {}
    def pin(path):
        pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path
    def save(name, value):
        (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                       allow_nan=False)+'\n', encoding='utf-8')
    native = load(pin(source/'summary.json'))
    protocol = load(pin(source/'protocol.json'))
    manifest = load(pin(STUDY/'selected/plant_n31_v2.json'))
    geo_path = pin(ROOT/manifest['sources']['geometry']['path'])
    assert pins[str(geo_path)] == manifest['sources']['geometry']['sha256']
    geometry = load(geo_path)
    offsets = {z['link']: z['offset_m'] for z in geometry['chains']['FW_E']}
    bounds = geometry['bounds']['FW_E']
    cells = {z['cell']: z for z in geometry['cells'] if z['road'] == 'FW_E'}
    head = protocol['head_position_m']
    cutoff, end = protocol['window']
    history_start = cutoff-150
    relevant = {31, 10484, 119, 10702, 24}
    save('protocol.json', dict(cutoff=cutoff, history_start=history_start,
        evaluation_end=end, seed=53, local_cells=[22, 23], context_cells=[21, 24, 25],
        group_widths=[1, 2], exchange_parameters=2, coefficient_grid=0,
        rate_estimation='Only pre-cutoff150s, pooled22/23 endpoint group changes divided by donor vehicle-seconds.',
        validation='Future native stocks are conditional diagnostic operands, never autonomous prediction inputs.',
        raw_scans_max=1, new_native=0, new_forecasts=0,
        ambiguity='Same observed lane at5s endpoints does not rule out hidden excursions; crossing+lane-change location is unresolved. Endpoint transfer is not boundary flux.'))
    arm_frames = {}
    for arm in ('hold', 'release'):
        path = pin(source/(arm+'_frames.json.gz'))
        assert pins[str(path)] == next(z['cache_sha256'] for z in native['rows'] if z['arm'] == arm)
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            arm_frames[arm] = json.load(f)['frames']
    original = next(z['source'] for z in native['rows'] if z['arm'] == 'hold')
    path = Path(original['path'])
    stat = path.stat()
    assert (stat.st_size, stat.st_mtime_ns) == (original['size'], original['mtime_ns'])
    receipt = load(pin(path.parent.parent/'run.json'))
    assert receipt['completed'] and receipt['finished'] and not receipt['owned_native_alive']
    # One complete read verifies unchanged bytes; only the past150s is retained.
    past = {}; digest = hashlib.sha256(); ix = None
    columns = ('NO', 'LANE\\LINK\\NO', 'LANE\\INDEX', 'POS', 'SPEED', 'LENGTH', 'POSLAT', 'DESTLANE', 'LNCHG')
    with path.open('rb') as stream:
        for raw in stream:
            digest.update(raw)
            if raw.startswith(b'$VEHICLE:'):
                names = [x.strip() for x in raw.decode('ascii').split(':', 1)[1].split(';')]
                ix = {k: names.index(k) for k in ('SIMSEC', *columns)}
                assert ix['SIMSEC'] == 0
                continue
            if ix is None or not raw.strip() or raw.startswith((b'*', b'$')):
                continue
            t = float(raw.split(b';', 1)[0])
            if not history_start-1e-6 <= t <= cutoff+1e-6:
                continue
            frame = past.setdefault(str(t), [])
            x = raw.strip().split(b';')
            assert len(x) == len(names)
            link = int(x[ix['LANE\\LINK\\NO']])
            if link in relevant:
                frame.append([int(x[ix['NO']]), link, int(x[ix['LANE\\INDEX']]),
                    *[float(x[ix[k]]) for k in ('POS', 'SPEED', 'LENGTH', 'POSLAT')],
                    *[x[ix[k]].decode('ascii').strip() for k in ('DESTLANE', 'LNCHG')]])
    assert digest.hexdigest() == original['sha256']
    assert (path.stat().st_size, path.stat().st_mtime_ns) == (stat.st_size, stat.st_mtime_ns)
    assert len(past) == 31 and min(map(float, past)) == history_start and max(map(float, past)) == cutoff
    assert past[str(cutoff)] == arm_frames['hold'][str(cutoff)] == arm_frames['release'][str(cutoff)]
    with gzip.open(out/'past_frames.json.gz', 'wt', encoding='utf-8') as stream:
        json.dump(dict(source=original, frames=past), stream, allow_nan=False)
    pin(out/'past_frames.json.gz')

    def address(z):
        if z is None:
            return ('missing', None)
        if z[1] == 10484:
            return ('post' if z[3] >= head else 'pre', None)
        if z[1] not in offsets:
            return ('outside', None)
        c = bisect.bisect_right(bounds, offsets[z[1]]+z[3])-1
        return (c, 0 if z[2] == 1 else 1)
    def local(a):
        return a[0] in (22, 23)
    targets = [(c, g) for c in (21, 22, 23, 24, 25) for g in (0, 1)]+[('post', None)]
    ledger_rows, exchange_rows = [], []
    for arm, raw_frames in [('past', past), *arm_frames.items()]:
        frames = sorted((float(t), {z[0]: z for z in vs}) for t, vs in raw_frames.items())
        for (ta, a), (tb, b) in zip(frames, frames[1:]):
            assert abs(tb-ta-5) < 1e-7
            addresses_a = {vid: address(z) for vid, z in a.items()}
            addresses_b = {vid: address(z) for vid, z in b.items()}
            transition = Counter(); crossing_change = Counter(); boundary_change = Counter()
            for vid in a.keys() | b.keys():
                aa = addresses_a.get(vid, ('missing', None))
                bb = addresses_b.get(vid, ('missing', None))
                if (local(aa) and bb[0] == 'missing') or (local(bb) and aa[0] == 'missing'):
                    raise AssertionError(('Unexplained local appearance/disappearance', arm, ta, vid))
                if local(aa) and local(bb) and aa[1] != bb[1]:
                    transition[aa[1], bb[1]] += 1
                    crossing_change[aa[1], bb[1]] += aa[0] != bb[0]
                elif local(aa) != local(bb) and isinstance(aa[0], int) and isinstance(bb[0], int) and aa[1] != bb[1]:
                    boundary_change[aa[1], bb[1]] += 1
            for g, k in ((0, 1), (1, 0)):
                n0 = sum(local(x) and x[1] == g for x in addresses_a.values())
                exchange_rows.append(dict(arm=arm, start=ta, end=tb, donor=g, recipient=k,
                    donor_vehicle_seconds=n0*(tb-ta), inside_region_endpoint_changes=transition[g, k],
                    cross_cell_changes= crossing_change[g, k],
                    boundary_and_lane_changes=boundary_change[g, k]))
            for target in targets:
                ids0 = {vid for vid, x in addresses_a.items() if x == target}
                ids1 = {vid for vid, x in addresses_b.items() if x == target}
                incoming, outgoing, retained = ids1-ids0, ids0-ids1, ids0 & ids1
                m0 = math.fsum(a[vid][4] for vid in ids0)
                m1 = math.fsum(b[vid][4] for vid in ids1)
                reaction = math.fsum(b[vid][4]-a[vid][4] for vid in retained)
                entered = math.fsum(b[vid][4] for vid in incoming)
                left = math.fsum(a[vid][4] for vid in outgoing)
                mass_error = len(ids1)-len(ids0)-len(incoming)+len(outgoing)
                moment_error = m1-m0-reaction-entered+left
                assert mass_error == 0 and abs(moment_error) < 1e-8
                same_cell_in = sum(addresses_a.get(vid, (None, None))[0] == target[0] for vid in incoming)
                same_cell_out = sum(addresses_b.get(vid, (None, None))[0] == target[0] for vid in outgoing)
                ledger_rows.append(dict(arm=arm, start=ta, end=tb, cell=target[0], group=target[1],
                    initial_n=len(ids0), final_n=len(ids1), arrivals=len(incoming), departures=len(outgoing),
                    same_cell_lane_in=same_cell_in, same_cell_lane_out=same_cell_out,
                    initial_velocity_moment=m0, final_velocity_moment=m1,
                    retained_velocity_change=reaction, arrival_velocity_moment=entered,
                    departure_velocity_moment=left, mass_error=mass_error, velocity_moment_error=moment_error))
    rates = {}
    for g, k in ((0, 1), (1, 0)):
        rr = [r for r in exchange_rows if r['arm'] == 'past' and r['donor'] == g]
        count = sum(r['inside_region_endpoint_changes'] for r in rr)
        exposure = math.fsum(r['donor_vehicle_seconds'] for r in rr)
        assert exposure > 0
        rates[g] = count/exposure
    initial = []
    for c in (22, 23):
        groups = []
        for g in (0, 1):
            vs = [z for z in past[str(cutoff)] if address(z) == (c, g)]
            assert vs, 'Explicit empty-group speed policy required'
            groups.append(dict(width=1 if g == 0 else 2, n=len(vs),
                               speed=math.fsum(z[4] for z in vs)/len(vs)))
        initial.append(dict(cell=c, length_km=cells[c]['length_km'], groups=groups))
    save('initial_state.json', dict(cutoff=cutoff, source=original, cells=initial,
        pooled_endpoint_exchange_rates_per_sec={str(k): v for k, v in rates.items()},
        production_ready=False, limitations='Two causal pooled rates, uncorrected for unresolved lane-change location and hidden excursions.'))
    summaries = []
    for arm in ('past', 'hold', 'release'):
        windows = [(history_start, cutoff)] if arm == 'past' else [(cutoff+i*150, cutoff+(i+1)*150) for i in range(3)]
        for start, finish in windows:
            for g in (0, 1):
                rr = [r for r in exchange_rows if r['arm'] == arm and r['donor'] == g and start <= r['start'] < finish]
                assert len(rr) == 30
                summaries.append(dict(arm=arm, start=start, end=finish, donor=g,
                    observed_inside_endpoint_changes=sum(r['inside_region_endpoint_changes'] for r in rr),
                    crossing_cell_and_lane=sum(r['cross_cell_changes'] for r in rr),
                    boundary_and_lane_changes=sum(r['boundary_and_lane_changes'] for r in rr),
                    fixed_past_rate_on_native_stocks=math.fsum(r['donor_vehicle_seconds']*rates[g] for r in rr)))
    for name, rows in [('mass_moment_5s.csv', ledger_rows), ('exchange_5s.csv', exchange_rows)]:
        with (out/name).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    pin(Path(__file__))
    save('summary.json', dict(rows=summaries, initial_local_cells=initial,
        rates_per_sec={str(k): v for k, v in rates.items()},
        mass_ledger_rows=len(ledger_rows), max_mass_error=max(abs(r['mass_error']) for r in ledger_rows),
        max_velocity_moment_error=max(abs(r['velocity_moment_error']) for r in ledger_rows),
        common_initial_exact=True, future_training_inputs=False, new_forecasts=0, new_native=0,
        fzp_scans=1, production_adopted=False, gain_qualified=False, pins=pins))
    print(json.dumps(dict(output=str(out), rates=rates, rows=summaries)), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['--ramp10484-local-state']:
        ramp10484_local_state_audit()
    elif sys.argv[1:] == ['--ramp10484-receiving-screen']:
        ramp10484_receiving_screen()
    elif sys.argv[1:] == ['--ramp10484-sections']:
        ramp10484_cached_sections()
    elif sys.argv[1:] == ['--ramp10484']:
        ramp10484_native_audit()
    elif sys.argv[1:] == ['--conflict']:
        conflict_audit()
    elif sys.argv[1:] == ['--native-lanes']:
        native_lane_audit()
    elif sys.argv[1:] == ['--mechanisms']:
        mechanism_audit()
    else:
        assert not sys.argv[1:]
        main()
