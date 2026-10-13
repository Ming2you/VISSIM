"""Identify why past SC12 west head discharge did not update service.

This records provenance and ambiguity; it does not install a new rate.
"""
import hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
PINS={}

def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)

def main():
    assert not (HERE/'service_binding.json').exists()
    config=read(H/'sc1_supply/config.json')
    network=read(H/'sc1_supply/forecast2400/network.json')
    history=read(H/'sc12_source/assessment.json')
    table=read(ROOT/'outputs/lane_group_sustained_v0_ver2_20260907_v2.json')
    m='SC12_W_SC11_to_N_SC6';alias='SC12_W_to_N_SC6'
    past=[]
    for end in ('1950','2100','2250','2400'):
        row=next(x for x in history['past_observation'][end]['SC12_W']['rows'] if x['head_id']=='50201')
        past.append(dict(end_sec=int(end),green_sec=row['green_sec'],qualified_crossings=row['qualified_crossings'],
            rejected_by_single_window_threshold=row['green_sec']<config['urban']['capacity']['head_observation']['min_green_sec']))
    assert all(x['rejected_by_single_window_threshold'] for x in past)
    carried={}
    for end in (1800,1950,2100,2250):
        doc=read(H/f'sc1_supply/forecast2400/head_history/head_prior_{end:06}.json')
        carried[str(end)]={k:v for k,v in doc['metadata'].items() if '1220012103_p4' in k}
    assert not any(carried.values())
    pin=network['head_service_resources']['network'];path=ROOT/pin['path']
    data=path.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha==pin['sha256'];PINS[str(path)]=sha
    tree=ET.fromstring(data)
    head=tree.find("./signalHeads/signalHead[@no='50201']")
    assert head.get('lane')=='1220012103 2' and head.get('sg')=='12 5'
    competing=[]
    for node in tree.findall('./links/link'):
        src=node.find('fromLinkEndPt')
        if src is None or src.get('lane').split()[0]!='1220012103':continue
        lo=int(src.get('lane').split()[1]);lanes=range(lo,lo+len(node.findall('./lanes/lane')))
        if 2 in lanes and float(src.get('pos'))>float(head.get('pos')):
            competing.append(dict(connector=node.get('no'),target=node.find('toLinkEndPt').get('lane').split()[0]))
    assert {r['connector'] for r in competing}=={'10241','10242'}
    document=dict(status='complete_short_exposure_and_post_head_ambiguity',movement=m,
        actual_runtime_rate_veh_h=network['movement_capacity_by_movement_veh_h'][m],
        boundary_alias=dict(movement=alias,rate_veh_h=network['movement_capacity_by_movement_veh_h'][alias]),
        prior_table=table['links']['1220012103'],minimum_green_sec=config['urban']['capacity']['head_observation']['min_green_sec'],
        past_windows=past,carried_matching_metadata=carried,competing_post_head_connectors=competing,
        conclusions=[
            'Past20-24s greens never pass the30s per-window head-update threshold; this phase has no carried head support in these saved priors.',
            'Runtime206.5306veh/h is not the measured current left-turn saturation flow. The table reports450veh/h lane-group achieved prior, with subsequent capacity allocation; do not label the runtime number a direct native measurement.',
            'Lane2 can reach either10241 or10242 after the head. Raising the northbound connector to all head crossings would falsely assume unique destination attribution.',
            'Known source-head to SC6-head IDs already establish31/15 realized northbound paths in the450s held/selected validation, versus4.131/3.082 predicted source departures.',
            'Next narrow repair must use past-only typed connector/path support and one shared physical lane budget for aliases; preserve other phases and finite receiving constraints.'],
        new_forecasts=0,production_changes=0,fitted_coefficients=0,source_pins=PINS)
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (HERE/'service_binding.json').write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('COMPLETE',document['actual_runtime_rate_veh_h'],'veh/h; short greens',[(r['end_sec'],r['green_sec']) for r in past])

if __name__=='__main__':main()
