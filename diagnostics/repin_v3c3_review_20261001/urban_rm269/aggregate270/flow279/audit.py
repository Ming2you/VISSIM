"""Trace saved3300 supply without new forecasts, FZP scans or future inputs."""
import gzip, hashlib, json, pickle, subprocess, sys
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
F = Path('E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc

MOVEMENT = 'SC1002_W_SC1001_to_S_SC105'
GROUPS = {
    'SC105_to_SC1005': {10661,10669,10671,1220006403,10655,412,10651,10652,410,10654,408,10647,10648,409,10649,403},
    'SC1002_to_SC105': {10683,10686,10693,420,10659,10660,1220007200},
}
PINS = {}

def pin(p):
    data = Path(p).read_bytes()
    PINS[str(p)] = hashlib.sha256(data).hexdigest()
    return data

def read(p): return json.loads(pin(p))

def main():
    assert not (HERE/'diagnosis.json').exists()
    cfg, state, action, forecast = pickle.loads(pin(HERE/'replay3300/initial.pickle'))
    response = json.loads(gzip.decompress(pin(HERE/'replay3300/response.json.gz')))
    stocks = read(HERE/'replay3300/stocks.json')
    netpath = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree = ET.fromstring(pin(netpath))
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    heads = list(tree.findall('./signalHeads/signalHead'))
    inputs = {int(x.get('link')) for x in tree.findall('./vehicleInputs/vehicleInput')}
    assert all(not (group & inputs) for group in GROUPS.values())
    node = links['10686']; start, end = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
    lanes = list(range(int(start.get('lane').split()[1]), int(start.get('lane').split()[1])+len(node.findall('./lanes/lane'))))
    sharing = []
    for number, other in links.items():
        source = other.find('fromLinkEndPt')
        if source is None or number == '10686' or source.get('lane').split()[0] != '30': continue
        lo = int(source.get('lane').split()[1])
        if set(range(lo,lo+len(other.findall('./lanes/lane')))) & set(lanes): sharing.append(number)
    on_lanes = [h.attrib for h in heads if h.get('lane').split()[0]=='30' and int(h.get('lane').split()[1]) in lanes]
    on_connector = [h.attrib for h in heads if h.get('lane').split()[0]=='10686']
    assert start.get('lane')=='30 1' and end.get('lane')=='420 1' and lanes==[1]
    assert not sharing and not on_lanes and not on_connector
    spec = cfg.network.urban_movements[MOVEMENT]
    assert not spec.get('unsignalized') and spec['receiving_link']=='SC1002_to_SC105'
    assert cfg.network.urban_link_storage_veh[spec['receiving_link']]>0
    route = cfg.network.control_area_routes['movement:'+MOVEMENT]
    assert route['status']=='unique' and len(route['physical_turns'])==1
    assert {k:route['physical_turns'][0][k] for k in ('from_link','connector','to_link')} == dict(from_link='30',connector='10686',to_link='420')
    oldpath = 'diagnostics/sdmpc_n31_20260924/urban/unsignalized_turns_v3c3_20261001.json'
    oldbytes = subprocess.check_output(['git','show','bd39205:'+oldpath], cwd=ROOT)
    old = json.loads(oldbytes)
    claude = old['movements'][MOVEMENT]
    assert claude['connectors'][0]['source_pos_m']==float(start.get('pos'))
    assert claude['connectors'][0]['source_lanes']==lanes and claude['connectors'][0]['target_link']=='420'

    native, snapshots = [], {}
    def snapshot(raw):
        p = Path(raw['lane_plant_observation']['directory'])/f"frame_{int(raw['sim_sec']):06}.json"
        frame = read(p)
        assert frame['complete'] and frame['time_s']==raw['sim_sec'] and frame['run_id']==raw['run_provenance']['run_id']
        return frame['vehicles']
    raw0 = read(F/'state_003300.json')
    assert raw0['lane_plant_observation']['cadence']=='decision_150s'
    snapshots[3300] = snapshot(raw0)
    for end_sec in (3450,3600,3750):
        raw = read(F/f'state_{end_sec:06}.json')
        derived = read(F/'obs150'/f'derived_{end_sec:06}.json')
        bundle = oc.load_bundle(raw)
        ds,_ = oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
        pin(bundle.obs['detector_config']['path'])
        oc.validate_raw(bundle.obs,ds,expected_simres=10)
        bounds = oc.evaluate_boundaries(bundle.obs,ds,bundle.frame_end,bundle.frame_start,bundle.err_rows)
        snapshots[end_sec] = snapshot(raw)
        out = {}
        for group,physical in GROUPS.items():
            a,b = snapshots[end_sec-150],snapshots[end_sec]
            link = 403 if group=='SC105_to_SC1005' else 1220007200
            physical_heads = [h for h in heads if int(h.get('lane').split()[0])==link]
            positions = {int(h.get('lane').split()[1]):float(h.get('pos')) for h in physical_heads}
            def tail(rows):return sum(int(v[1])==link and int(v[2]) in positions and float(v[3])>positions[int(v[2])] for v in rows)
            hs = [h for h in derived['head_window']['heads'] if int(h['link'])==link]
            departures = sum(h['crossings'] for h in hs)
            bypass = bounds['headfree:10565'].cross if group=='SC105_to_SC1005' else 0
            removals = oc.window_removals(bundle.err_rows,end_sec-150,end_sec)
            # Preserve API details rather than assume an absent removal record.
            assert not any(int(x['link']) in physical for x in removals), 'Corridor removals require explicit accounting'
            initial,final = (sum(int(v[1]) in physical for v in rows) for rows in (a,b))
            delta_tail = tail(b)-tail(a)
            out[group] = dict(initial=initial,final=final,head_cross=departures,bypass=bypass,
                posthead_tail_change=delta_tail,removals=0,inflow_from_balance=final-initial+departures+bypass-delta_tail)
        native.append(dict(start_sec=end_sec-150,corridors=out))

    model = []
    interest = [m for m in cfg.network.urban_movements if m.startswith(('SC105_N_','SC1002_'))]
    for j,start_sec in enumerate((3300,3450,3600)):
        transfers=[x for x in response['transfers'] if start_sec<=x['start_sec']<start_sec+150]
        incoming={}
        for group in GROUPS:
            counter=Counter()
            for t in transfers:
                if t['target']=='storage:'+group and t['source']!=t['target']:counter[t['source'] or 'external']+=t['vehicles']
            incoming[group]=dict(counter)
        mm={}
        for m in interest:
            allocations=[x for x in response['resource_allocations'] if x['resource']==m and start_sec<=x['start_sec']<start_sec+150]
            intent=[x for x in allocations if x['kind']=='urban_movement_intended_limit']
            q={x['start_sec']:x['available_veh'] for x in allocations if x['kind']=='urban_movement_stock'}
            mm[m]=dict(accepted=sum(x['accepted_total_veh'] for x in intent),
                requested=sum(x['available_veh'] for x in intent),
                queue_positive_zero_request_steps=sum(q[x['start_sec']]>1e-8 and x['available_veh']<=1e-8 for x in intent),
                initial_ready=stocks[j]['stocks'].get('movement:'+m,{}).get('inside',0),
                final_ready=stocks[j+1]['stocks'].get('movement:'+m,{}).get('inside',0))
        model.append(dict(start_sec=start_sec,corridor_incoming=incoming,movements=mm))
    candidate = read(HERE.parent/'urban_clock277/config_fw5_urban10.json')
    assert not candidate['config_overrides']['network']['urban_movements'][MOVEMENT].get('unsignalized')
    candidate['config_overrides']['network']['urban_movements'][MOVEMENT]['unsignalized']=True
    (HERE/'config_10686_free.json').write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report=dict(status='one_physical_authority_mismatch_identified',native=native,model=model,
        physical10686=dict(source='30',lane=1,connector='10686',target='420',exclusive_source_lane=True,
            source_heads=on_lanes,connector_heads=on_connector,shared_connectors=sharing),
        current_model=dict(movement=MOVEMENT,spec=spec,capacity_veh_h=cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT]),
        claude=dict(commit='bd39205',file=oldpath,sha256=hashlib.sha256(oldbytes).hexdigest(),row=claude,
            original_network=old['network'],same_local_connector_geometry=True),
        limitations=['Native future flow is diagnostic only, never forecast input.',
            'SC1002 native inflow is corridor balance; individual10686 flow is not observed by the saved detector table.',
            'Claude validation uses another network hash. Only local geometry was matched; no rates/betas transferred.',
            'The physical52 group includes SC107-origin model stock; the old SC1005-only footprint is not a full future physical52 stock metric.',
            'One-second lane census failed because saved frames have decision150s cadence; no retry or fabricated1s observations.',
            'Candidate removes one incorrect signal gate using existing finite service/receiving rules; no speed/capacity calibration.'],
        new_predictions=0,new_native_runs=0,new_fits=0,fzp_scans=0,source_pins=PINS)
    (HERE/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for row in native:print('NATIVE',row,flush=True)
    for row in model:print('MODEL',row['start_sec'],row['corridor_incoming'],row['movements'][MOVEMENT],flush=True)
    print('DIAGNOSIS_COMPLETE',flush=True)

if __name__=='__main__':main()
