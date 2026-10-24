"""SC6 ready-stock and source-path audit of already closed observations.

No native run, FZP scan, new plant prediction, or future-input substitution.
Matched head IDs prove a realized path, not all arrivals or saturation capacity.
"""
import ctypes
import gzip
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
loader = importlib.util.spec_from_file_location('closed_heads', H/'sc12_source/audit.py')
a = importlib.util.module_from_spec(loader)
loader.loader.exec_module(a)
a.LINKS = {'SC12_W':1220012103, 'SC12_S':1210012700, 'SC6_S':1210018302}
from evaluation.controllers.route_choice_corridor import _length, _travel_segments, _validate_path
from plant.src.vissim_strict.signal_program import parse_sig

ORIGIN = 'SC12_to_SC6'
P1 = ['SC6_S_SC12_to_N_SC103', 'SC6_S_SC12_to_E_SC104']


def main():
    assert not (HERE/'assessment.json').exists(), 'Preserve completed audit'
    kernel = ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    q = H/'sc1_supply/forecast2400'
    network, state = a.read(q/'network.json'), a.read(q/'state.json')
    clock = a.read(H/'city_response/assessment.json')
    source = a.read(H/'sc12_source/assessment.json')
    tree = ET.fromstring(a.pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    links = {n.get('no'):n for n in tree.findall('./links/link')}
    ctrl = tree.find("./signalControllers/signalController[@no='10']")
    sig = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network'/ctrl.get('supplyFile2').removeprefix('#data#')
    a.pin(sig)
    program = parse_sig(sig, int(ctrl.get('progNo')))
    assert ctrl.get('active') == 'true' and ctrl.get('type') == 'FIXEDTIME'
    heads = [h for h in tree.findall('./signalHeads/signalHead') if h.get('sg') == '10 8']
    assert {h.get('lane') for h in heads} == {f'1220018301 {i}' for i in range(1,5)}
    paths = {
        'SC12_S_connector_to_SC6_head':['10244','1220015100','10212','136','10211','1220018301','10216','1220018302','10209','1210018302'],
        'input1085_source_to_SC6_head':network['native_internal_inputs']['inputs']['1085']['approach_path']}
    geometry = {}
    for label,path in paths.items():
        _validate_path(path,links)
        seg = _travel_segments(path, links, {k:_length(links[k]) for k in path}, 140.108794)
        gate_idx = path.index('1220018301')
        before = sum(x['stop']-x['start'] for x in seg[:gate_idx])+min(float(h.get('pos')) for h in heads)-seg[gate_idx]['start']
        geometry[label] = dict(segments=seg, length_m=sum(x['stop']-x['start'] for x in seg), pre_gate_m=before)
    factor = a.read(ROOT/'outputs/storage_effective_lanes_20260904.json')['storage_effective_lanes'][ORIGIN]
    old_geometry = a.read(ROOT/'outputs/urban_storage_geometry_core17legs4f_20260826.json')
    speed = state['urban_link_speed_kph'][ORIGIN]
    delay = math.ceil(state['urban_link_storage'][ORIGIN]*network['urban_avg_vehicle_length_m']/(speed/3.6))
    initial_delay = dict(sec=delay, available_transit_spaces_veh=state['urban_link_storage'][ORIGIN],
        all_lane_capacity_veh=network['urban_link_storage_veh'][ORIGIN], effective_speed_kph=speed,
        lane_factor=factor, unscaled_speed_kph=speed/factor,
        equivalent_longitudinal_free_m=state['urban_link_storage'][ORIGIN]*network['urban_avg_vehicle_length_m']/factor,
        scope='Initial generic delay operand only; actual future delay changes with model stock. Not a per-vehicle error measurement.')
    result = {}
    for arm in ('hold','selected'):
        response = json.loads(gzip.decompress(a.pin(q/(arm+'.response.json.gz'))))
        residence = {r['end_sec']:r for r in response['residence'] if r['stage']=='urban'}
        transfers = response['transfers']
        rows = []
        for start in (2400,2550,2700):
            prior = {'movement:'+m:state['urban_movement_queue'][m] for m in P1} if start==2400 else residence[start]['model_stock_veh']
            ready0 = sum(prior.get('movement:'+m,0) for m in P1)
            ts = [t for t in transfers if start<=t['start_sec']<start+150]
            arrived = sum(t['vehicles'] for t in ts if t['source']=='storage:'+ORIGIN and t['target'] in {'movement:'+m for m in P1})
            depart = sum(t['vehicles'] for t in ts if t['source'] in {'movement:'+m for m in P1} and t['source']!=t['target'])
            ready1 = sum(residence[start+150]['model_stock_veh'].get('movement:'+m,0) for m in P1)
            assert abs(ready0+arrived-depart-ready1)<1e-7
            old = next(r for r in clock['arms'][arm] if r['start_sec']==start)['phases']['SC6_S_p1']
            assert abs(depart-old['model_head_veh'])<1e-7, 'SC1 repair unexpectedly changed SC6'
            incoming = Counter()
            for t in ts:
                if t['target']=='storage:'+ORIGIN and t['source']!=t['target']:
                    incoming[t['source'] or t['route_key']]+=t['vehicles']
            rows.append(dict(start_sec=start, p1_ready_start=ready0, p1_arrived=arrived, p1_discharged=depart,
                p1_ready_end=ready1, p1_available_even_with_unlimited_service=ready0+arrived,
                native_p1_head=old['native_head_veh'], model_incoming_by_source=dict(incoming),
                receiver_rejection=sum(m['receiver_rejection_veh'] for m in old['movements'].values()),
                clock_mismatch_seconds=old['clock_mismatch_seconds']))
        folder = a.NATIVE/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        events = {key:[] for key in a.LINKS}
        for end in (2550,2700,2850):
            _, current = a.heads_and_entries(folder,end)
            for key,values in current.items(): events[key].extend(values)
        downstream = {}
        for lane,veh,t in events['SC6_S']:
            downstream.setdefault(veh,[]).append(t)
        witnesses = []
        for label in ('SC12_W','SC12_S'):
            for lane,veh,t in events[label]:
                later = [v for v in downstream.get(veh,[]) if t<v]
                if later:
                    witnesses.append(dict(source=label,lane=lane,vehicle_id=veh,source_sec=t,
                        downstream_sec=min(later),travel_sec=min(later)-t))
        totals = Counter(w['source'] for w in witnesses)
        model_sources = {}
        for label in ('SC12_W','SC12_S'):
            model_sources[label] = sum(t['vehicles'] for t in transfers if t['target']=='storage:'+ORIGIN
                and (t['source'] or '').startswith('movement:'+label+'_'))
        # Lower bound uses upstream and downstream passages both inside this450s.
        # Crossers still in transit at2850 and absent MER IDs only increase the actual count.
        result[arm] = dict(blocks=rows, realized_SC12_to_SC6_path_lower_bound=dict(totals),
            model_same450s_source_departures=model_sources, path_witnesses=witnesses,
            native_existing_travel_summary=source['native_path_witnesses'][arm])
        del response
    proof_sources = [Path(__file__),ROOT/'evaluation/controllers/native_internal_input.py',
        ROOT/'evaluation/controllers/urban_flow_accounting.py',ROOT/'vendor/NumSim-mine/src/models/urban_queue_model.py',
        ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
        H.parent/'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md',
        H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md']
    for p in proof_sources:a.pin(p)
    report = dict(status='complete_diagnostic_no_fit', arms=result, representative_geometry=geometry,
        initial_generic_delay=initial_delay, intermediate_fixed_signal=dict(controller='10', signal_group='8',
            sig_file=str(sig), file_controller_id=program.controller_id, cycle_sec=program.cycle_length_sec,
            program_offset_sec=program.program_offset_sec, controller_offset_sec=float(ctrl.get('offset')),
            intervals=[dict(start_sec=i.start_sec,end_sec=i.end_sec,state=i.state) for i in program.sg_timelines['8'].intervals],
            heads=[h.attrib for h in heads],
            explicitly_in_common_approach_dynamics=False, actual_signal_log_collected=False),
        new_forecasts=0,new_native=0,fzp_scans=0,production_changes=0,coefficients_fitted=0,
        limitations=['Representative path distances are not all-lane queue-tail distances or observed free-flow times.',
            'A native fixed signal timing file proves intended timing, not recorded execution; SC10 is absent from stored COM signal logs.',
            'Physical speed must remove the existing lane multiplier before a distance/speed model is used.',
            'Future head witnesses are diagnostic only, never fed into an autonomous prediction or a calibration prior.',
            'Known source-to-downstream head paths are lower bounds, not saturation-flow samples or a complete input census.',
            'No matched SC12 head does not identify a side input or an unknown route.',
            'Generic storage and full geometric path footprints differ; their raw occupancies are not asserted equivalent.'],
        source_pins=a.PINS)
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for arm,v in result.items():
        print(arm,'ready',[(r['start_sec'],round(r['p1_available_even_with_unlimited_service'],3),r['native_p1_head']) for r in v['blocks']])
        print(arm,'source_lower_bounds',v['realized_SC12_to_SC6_path_lower_bound'],'model',v['model_same450s_source_departures'])
    print('COMPLETE',len(a.PINS),'pins')


if __name__=='__main__':main()
