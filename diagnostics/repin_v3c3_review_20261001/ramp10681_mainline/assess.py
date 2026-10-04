"""Read unchanged model traces and eight existing native snapshots only."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
ROOT = R.parents[1]
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def main():
    target = HERE/'assessment.json'
    if target.exists():
        raise FileExistsError(target)
    source = I/'closedloop_recorded2700_select_check_trace10681_gap_inputs47'
    folder = I/'closedloop_recorded2700_select_check_trace10681_mainline_terms47'
    geometry = read(I/'selected/port_gain/geometry.json')
    cells = {c['cell']: c for c in geometry['cells'] if c['road'] == 'FW_E'}
    audit = read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    supply = read(R/'ramp10681_receiving/supply/assessment.json')
    observation_position = supply['measurement']['position_m']+geometry['addresses']['2'][1]
    assert abs(observation_position-cells[11]['end_m']) < 1e-5
    outcomes = {}
    for name, arm in (('held_actual','hold'),('selected','selected')):
        a = read(source/(name+'.json'))
        b = read(folder/(name+'.json'))
        a.pop('wall_sec'); seconds = b.pop('wall_sec')
        assert a == b
        old = read(source/(name+'_RM_C10681_trace.json.gz'))
        trace = read(folder/(name+'_RM_C10681_trace.json.gz'))
        stripped = copy.deepcopy(trace)
        mainline = stripped.pop('mainline_diagnostics')
        assert stripped == old
        assert len(mainline['speed_terms']) == 3600
        terms = {(r['time_sec'],r['cell']):r for r in mainline['speed_terms']}
        assert len(terms)==3600
        resources = {(r['start_sec'],r['kind'],r['resource']):r for r in mainline['resources']}
        assert len(resources)==len(mainline['resources'])
        snapshots = {}
        for text, pin in audit['input_sha256'].items():
            path = Path(text)
            if arm not in path.parts:
                continue
            raw = read(path)
            assert PINS[str(path)] == pin and raw['vehicle_records']['complete']
            rows = raw['vehicle_records']['records']
            states = {}
            for i in range(8,16):
                selected=[]
                for v in rows:
                    address = geometry['addresses'].get(str(v['link_no']))
                    if address is not None and address[0]=='FW_E':
                        x=address[1]+v['position_m']
                        if cells[i]['start_m'] <= x < cells[i]['end_m']:
                            selected.append(v)
                states[i]=dict(n=len(selected),speed=sum(v['speed_kph'] for v in selected)/len(selected) if selected else None)
            snapshots[raw['sim_sec']]=states
        assert sorted(snapshots)==[2700,2850,3000,3150]
        state_comparison={}
        for state in mainline['initial_and_block_states']:
            t=state['time_sec']
            state_comparison[t]={}
            for i in range(8,16):
                model_n=state['density'][i]*state['lanes'][i]*cells[i]['length_km']
                state_comparison[t][i]=dict(native=snapshots[t][i],model=dict(n=model_n,speed=state['speed'][i]))
                if t==2700:
                    assert abs(model_n-snapshots[t][i]['n'])<1e-7
                    if snapshots[t][i]['speed'] is not None:
                        assert abs(state['speed'][i]-snapshots[t][i]['speed'])<1e-7
        windows={}
        for t0 in (2700,2850,3000):
            summaries={}
            for i in range(8,16):
                sample=[terms[t,i] for t in range(t0,t0+150)]
                values={k:sum(r[k] for r in sample)/150 for k in
                    ('speed_before','rho','downstream_rho','desired','relaxation','convection','anticipation',
                     'lane_drop_raw','post_equation_change','tau_sec','nu')}
                send=[resources[t,'freeway_mainline_sending',f'FW_E:cell:{i}'] for t in range(t0,t0+150)]
                recv=[resources[t,'freeway_mainline_receiving_after_ramps',f'FW_E:cell:{i}'] for t in range(t0,t0+150)]
                values.update(outflow_veh=sum(r['accepted_total_veh'] for r in send),
                    inflow_mainline_veh=sum(r['accepted_total_veh'] for r in recv),
                    sending_limit_veh=sum(r['available_veh'] for r in send),
                    receiving_limited_seconds=sum(r['accepted_total_veh'] < r['available_veh']-1e-8 for r in send),
                    net_speed_change=sum(r['speed_final']-r['speed_before'] for r in sample),
                    min_speed=min(r['speed_before'] for r in sample),
                    max_abs_post_equation_change=max(abs(r['post_equation_change']) for r in sample))
                summaries[i]=values
            actual=supply['arms'][name]['native_windows']
            matched=next(w for w in actual if w['start_sec']==t0)
            measured=sum(matched['flow_veh_h_by_lane'])/24
            sent=summaries[11]
            expected=supply['arms'][name]['mean_model_conflict_by150'][str(t0)]
            assert abs(sent['sending_limit_veh']*24/4-expected)<1e-7
            windows[t0]=dict(cells=summaries,through11to12=dict(native_count=measured,
                model_sending_count=sent['sending_limit_veh'],model_accepted_count=sent['outflow_veh'],
                receiving_limited_seconds=sent['receiving_limited_seconds']))
        outcomes[name]=dict(full_output_and_previous_trace_exact=True,forecast_wall_sec=seconds,
            snapshots=state_comparison,windows=windows)
    out=dict(status='completed_mainline_input_diagnosis_not_gain_qualified',arms=outcomes,
             actual_detector_matches_cell11_end=True,new_native=0,new_fzp_scan=0,new_fit=0,
             forecasts=2,optimizer_iterations=0,future_observations_in_prediction=False,
             source_sha256=PINS,limitations=['Native snapshots are150s apart; model speed-term decomposition is not causal native term identification.',
               'Post-equation changes combine accepted-merge braking and boundary caps until separated.',
               'Same two earlier states, not new independent gain validation.'])
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for name,row in outcomes.items():
        print(name)
        for t,w in row['windows'].items():
            print(t,w['through11to12'])
            for i in (9,10,11,12,13):
                c=w['cells'][i]
                print(i,{k:round(c[k],3) for k in ('speed_before','rho','relaxation','convection','anticipation',
                    'lane_drop_raw','post_equation_change','receiving_limited_seconds')})


def boundary_cap():
    """Reconstruct the already-accepted off flow from cell11 conservation."""
    target=HERE/'boundary_cap.json'
    if target.exists():
        raise FileExistsError(target)
    report=read(HERE/'assessment.json')
    audit=read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    geometry=read(I/'selected/port_gain/geometry.json')
    cell=next(c for c in geometry['cells'] if c['road']=='FW_E' and c['cell']==11)
    assert not any(b.get('to_cell')==11 and b['road']=='FW_E' and b['kind']=='onramp'
                   for b in geometry['boundaries'])
    outcome={}
    for name,arm in (('held_actual','hold'),('selected','selected')):
        folder=I/'closedloop_recorded2700_select_check_trace10681_mainline_terms47'
        trace=read(folder/(name+'_RM_C10681_trace.json.gz'))
        result=read(folder/(name+'.json'))
        resources={(r['start_sec'],r['kind'],r['resource']):r for r in trace['mainline_diagnostics']['resources']}
        terms={r['time_sec']:r for r in trace['mainline_diagnostics']['speed_terms'] if r['cell']==11}
        states={r['arguments']['start_sec']:r['freeway_before'] for r in trace['lane_interval_receipts']}
        final=trace['mainline_diagnostics']['initial_and_block_states'][-1]
        stocks={}
        for t,s in states.items():
            split=sum(x['ratio'] for x in s['offramp_splits'].values() if x['cell']==11)
            assert split==.25
            send=resources[t,'freeway_mainline_sending','FW_E:cell:11']['available_veh']*3600
            lanes=send/(1-split)/s['density'][11]/s['speed'][11]
            assert abs(lanes-4)<1e-7
            stocks[t]=s['density'][11]*lanes*cell['length_km']
        stocks[3150]=final['density'][11]*final['lanes'][11]*cell['length_km']
        rows=[]
        for t,r in terms.items():
            sending=resources[t,'freeway_mainline_sending','FW_E:cell:11']
            incoming=resources[t,'freeway_mainline_receiving_after_ramps','FW_E:cell:11']
            through=sending['accepted_total_veh']
            off=incoming['accepted_total_veh']-through-(stocks[t+1]-stocks[t])
            desired=sending['available_veh']/3
            assert -1e-9<=off<=desired+1e-9
            capped=r['post_equation_change'] < -1e-8
            cap=(through+off)*3600/(r['rho']*4)
            if capped:
                assert desired>off+1e-10
                assert abs(cap-r['speed_final'])<1e-7
            rows.append(dict(t=t,off_accepted=off,off_desired=desired,cap_active=capped,
                             computed_cap_kmh=cap,post_change=r['post_equation_change']))
        ledger_off=result['control_area']['flow_counts']['freeway:FW_E->storage:lane_off_10682']
        assert abs(sum(r['off_accepted'] for r in rows)-ledger_off)<1e-7
        native={}
        for text,pin in audit['input_sha256'].items():
            path=Path(text)
            if arm not in path.parts:
                continue
            raw=read(path);assert PINS[str(path)]==pin
            values=raw['vehicle_records']['records']
            native[raw['sim_sec']]=dict(off_entry=raw['obs150']['detectors']['960231'],
                connector_stock=sum(v['link_no']==10682 for v in values),
                connector_stopped=sum(v['link_no']==10682 and v['stopped'] for v in values))
        windows={}
        for start in (2700,2850,3000):
            w=[r for r in rows if start<=r['t']<start+150]
            windows[start]=dict(native_off_entry=native[start+150]['off_entry'],
                model_off_desired=sum(r['off_desired'] for r in w),model_off_accepted=sum(r['off_accepted'] for r in w),
                cap_active_seconds=sum(r['cap_active'] for r in w),
                mean_speed_correction_kmh_per_step=sum(r['post_change'] for r in w)/150)
        outcome[name]=dict(windows=windows,native=native,
                           first_cap_sec=next(r['t'] for r in rows if r['cap_active']),
                           model_off_total=ledger_off,all_active_cap_reconstructions_passed=True)
    target.write_text(json.dumps(dict(status='offramp_boundary_speed_cap_identified',arms=outcome,
        source_sha256=PINS,extra_forecasts=0,new_native=0,
        limitation='Model off entry reconstructed from conserved mainline cell, checked against saved total. Native connector stock is not the entire downstream branch storage.'),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(outcome,ensure_ascii=False))


def drain_audit():
    """Conditional port replay, not an autonomous full-network forecast."""
    import math
    from evaluation.controllers import obs150_contract as oc
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
    target=HERE/'drain_audit.json'
    if target.exists():raise FileExistsError(target)
    audit=read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    geometry=read(I/'selected/port_gain/geometry.json')
    profile=read(I/'selected/port_gain/port_profile.json')
    off=next(b for b in geometry['boundaries'] if b.get('connector')==10682)
    # The current raw frames put no car in the 0--1m offset. Use the actual
    # detector plane, subtracting that metre from travel, not from inventory.
    length=off['length_m']-1.
    params=read(ROOT/'evaluation/parameters.json')
    def find(tree,key):
        found=[]
        if isinstance(tree,dict):
            for k,v in tree.items():
                if k==key:found.append(v)
                found.extend(find(v,key))
        return found
    service_values=find(params,'movement_capacity_veh_h')
    spacing_values=find(params,'urban_avg_vehicle_length_m')
    assert len(service_values)==len(spacing_values)==1
    ordinary=float(service_values[0])*off['lanes']
    declared=float(profile['drain_service_vph']['10682'])
    capacity=off['length_m']*off['lanes']/spacing_values[0]
    arms={}
    for arm in ('hold','selected'):
        raws={}
        for text,pin in audit['input_sha256'].items():
            path=Path(text)
            if arm not in path.parts:continue
            raw=read(path);assert PINS[str(path)]==pin
            raws[int(raw['sim_sec'])]=raw
        assert sorted(raws)==[2700,2850,3000,3150]
        samples={}
        for t,raw in raws.items():
            assert raw['vehicle_records']['complete']
            vehicles=[v for v in raw['vehicle_records']['records'] if v['link_no']==10682]
            assert all(v['position_m']>=1 for v in vehicles)
            samples[t]=dict(stock=len(vehicles),stopped=sum(v['stopped'] for v in vehicles),
                mean_speed_kmh=sum(v['speed_kph'] for v in vehicles)/len(vehicles) if vehicles else None)
        events=[];windows={}
        for end in (2850,3000,3150):
            raw=raws[end];bundle=oc.load_bundle(raw)
            assigned=oc.assign_window(bundle.obs,bundle.mer_rows)
            assert assigned.tails[960231]==0
            arrivals=assigned.entries[960231]
            assert len(arrivals)==raw['obs150']['detectors']['960231']
            for row in arrivals:
                assert end-150 <= row.t_entry <= end
                events.append((row.t_entry,row.veh))
            removals=[r for r in oc.window_removals(bundle.err_rows,end-150,end) if r['link']==10682]
            assert not removals
            windows[end]=dict(entries=len(arrivals),
                balance_inferred_drain=samples[end-150]['stock']+len(arrivals)-samples[end]['stock'],
                removals=0,initial_stock=samples[end-150]['stock'],final_stock=samples[end]['stock'])
            for spec in (raw['obs150']['mer'],raw['obs150']['err']):
                path=oc.resolve(raw['obs150'],spec['chunk'])
                PINS[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
                assert PINS[str(path)]==spec['chunk_sha256']
        initial=[[v['position_m']-1.,v['speed_kph'],v['lane_no']]
                 for v in raws[2700]['vehicle_records']['records'] if v['link_no']==10682]
        cases={}
        for service in (ordinary,declared):
            port=DelayedPort(capacity,length,profile['travel_speed_kmh']['10682'],initial,2700.,interval_service=True)
            clock=2700.;states={};peak=port.stock
            events_by_time={}
            for t,veh in events:events_by_time.setdefault(t,[]).append(veh)
            for t in sorted({*events_by_time,2850.,3000.,3150.}):
                if t>clock:port.release(clock,t-clock,service)
                if t in events_by_time:port.accept(t,float(len(events_by_time[t])))
                peak=max(peak,port.stock);clock=t
                assert abs(port.stock-port.initial-port.admitted+port.departed)<1e-7
                if t in samples:
                    states[t]=dict(stock=port.stock,ready=port.ready,drained=port.departed,
                        residual_veh=port.stock-port.initial-port.admitted+port.departed,
                        native_stock=samples[t]['stock'],error_veh=port.stock-samples[t]['stock'])
            cases[str(service)]=dict(states=states,peak_stock=peak,
                stock_mae_veh=sum(abs(r['error_veh']) for r in states.values())/3,
                conditional_residence_veh_h=port.residence_veh_h,drain_total_veh=port.departed)
        arms[arm]=dict(native_samples=samples,native_windows=windows,conditional_cases=cases)
    result=dict(status='conditional_drain_audit_complete_not_gain_qualified',arms=arms,
        geometry=off,capacity_veh=capacity,ordinary_service_vph=ordinary,
        declared_profile_service_vph=declared,port_travel_speed_kmh=profile['travel_speed_kmh']['10682'],
        future_truth_used_only_in_component_diagnosis=True,new_native=0,new_full_forecasts=0,
        limitations=['Native drain is balance-inferred, not a dedicated exit detector count.',
            'Replay uses measured future entry times, and unlimited downstream receiving; not autonomous validation.',
            'No removal on connector and no car before the detector at the four endpoints; transient position uncertainty remains.',
            'Neither service value is identified as saturated capacity from this unsaturated sample.',
            'No production change and no gain qualification.'],source_sha256=PINS)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))


def eight_offramps():
    """Native entry/drain/stock audit before any cell-parameter fitting."""
    from evaluation.controllers import obs150_contract as oc
    target=HERE.parent/'offramp_drain_profile/eight_offramps.json'
    if target.exists():raise FileExistsError(target)
    audit=read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    geometry=read(I/'selected/port_gain/geometry.json')
    offramps=[b for b in geometry['boundaries'] if b['kind']=='offramp']
    table=I/'selected/obs150/obs150_detectors_v2.csv'
    detectors,digest=oc.read_detector_csv(table);PINS[str(table)]=digest
    groups=oc.group_boundaries(detectors)
    results={}
    for arm,name in (('hold','held_actual'),('selected','selected')):
        raw_by_time={}
        for text,pin in audit['input_sha256'].items():
            path=Path(text)
            if arm not in path.parts:continue
            raw=read(path);assert PINS[str(path)]==pin and raw['vehicle_records']['complete']
            raw_by_time[int(raw['sim_sec'])]=raw
        bundles={t:oc.load_bundle(raw_by_time[t]) for t in (2850,3000,3150)}
        model=read(I/'closedloop_recorded2700_select_check_trace10681_declared_drain47'/(name+'.json'))
        flows=model['control_area']['flow_counts']
        arms={}
        for off in offramps:
            number=off['connector'];ref='off_entry:'+str(number)
            key='storage:'+('lane_off_'+str(number) if off['branch']=='direct' else off['group']+'_storage')
            windows=[]
            for end,b in bundles.items():
                start=end-150
                stock=lambda t:sum(v['link_no']==number for v in raw_by_time[t]['vehicle_records']['records'])
                actual=oc.evaluate_boundary(groups[ref],b.obs['detectors'],b.frame_end,b.frame_start,b.err_rows,start,end)
                removed=[r for r in oc.window_removals(b.err_rows,start,end) if r['link']==number]
                final_rows=[v for v in raw_by_time[end]['vehicle_records']['records'] if v['link_no']==number]
                drain=stock(start)+actual.cross-stock(end)-len(removed)
                assert drain>=0
                windows.append(dict(start_sec=start,end_sec=end,entry=actual.cross,
                    detector_count=actual.vehs,entry_offset_correction=actual.cross-actual.vehs,
                    initial_stock=stock(start),final_stock=stock(end),removals=len(removed),
                    balance_inferred_drain=drain,stopped=sum(v['stopped'] for v in final_rows)))
            entry=flows['freeway:'+off['road']+'->'+key]
            outgoing={k:v for k,v in flows.items() if k.startswith(key+'->')}
            observed_entry=sum(w['entry'] for w in windows)
            arms[number]=dict(road=off['road'],cell=off['from_cell'],branch=off['branch'],windows=windows,
                native_entry=observed_entry,native_drain=sum(w['balance_inferred_drain'] for w in windows),
                model_entry=entry,entry_error=entry-observed_entry,
                model_drain_from_unambiguous_flow_key=sum(outgoing.values()) if outgoing else None,
                model_drain_coverage='physical_source_key' if outgoing else 'route_key_aggregation_requires_port_state',
                model_flow_keys=outgoing)
        results[arm]=arms
    doc=dict(status='EIGHT_OFFRAMP_ENTRY_AUDIT_BEFORE_CELL_FIT',arms=results,new_forecasts=0,new_native=0,
        new_fzp_scan=0,future_native_used_as_targets_only=True,source_pins=PINS,
        limitations=['Native exit to city is conservation-inferred with connector removals excluded, not directly measured.',
            'Model physical-source totals are missing for three route-key-aggregated signal branches; no invented drainage result.',
            'Single existing seed47 pair; independent states/seeds remain required before cell calibration.'])
    target.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for arm,ports in results.items():
        print(arm,[(o,round(r['native_entry'],2),round(r['model_entry'],2),r['native_drain']) for o,r in ports.items()])


if __name__=='__main__':
    import sys
    if '--offramp-eight' in sys.argv:eight_offramps()
    elif '--drain-audit' in sys.argv:drain_audit()
    elif '--boundary-cap' in sys.argv:boundary_cap()
    else:main()
