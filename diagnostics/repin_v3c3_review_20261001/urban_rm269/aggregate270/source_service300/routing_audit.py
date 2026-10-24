"""Check the scope of SC101 routing evidence for the SC15 side-entry sources.

No future path is installed in the predictor. Connector sightings are lower
bounds, and unobserved exits stay unresolved rather than being called straight.
"""
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
PINS={}
from evaluation.controllers import obs150_contract as oc


def pin(p):
    p=Path(p);data=p.read_bytes();PINS[str(p.resolve())]=hashlib.sha256(data).hexdigest();return data
def read(p):return json.loads(pin(p))


def main():
    assert not (HERE/'routing_audit.json').exists()
    source=read(HERE/'source_audit.json')
    geo=read(A/'sc101_clock299/source_geometry.json')
    xml=ET.fromstring(pin(geo['network_path']))
    links={n.get('no'):n for n in xml.findall('./links/link')}
    decisions={n.get('no'):n for n in xml.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')}
    assert decisions['1014'].get('link')=='1220008501'
    cfg,_,_=pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle'))
    movements={k:dict(beta=v['beta'],destination=v['destination']) for k,v in cfg.network.urban_movements.items()
        if v.get('origin')=='SC1_to_SC101'}
    native_weights={r.get('no'):float(r.get('relFlow').split(':')[-1])
        for r in decisions['1014'].findall('./vehRoutSta/vehicleRouteStatic')}
    direct_beta_difference=movements['SC101_S_SC1_to_N_SC2005']['beta']-native_weights['2']/sum(native_weights.values())
    geometry={}
    for dec in ('1099','1100'):
        g=geo['sources'][dec]
        paths=g['paths']
        assert all('1220008501' not in p for p in paths)
        assert all('1220008502' in p and p[-1]=='1220011503' for p in paths)
        end=links[g['connector']].find('toLinkEndPt')
        assert end.get('lane').split()[0]=='1220008502'
        geometry[dec]=dict(source=g['source_link'],native_route_end=[r.attrib for r in decisions[dec].findall('./vehRoutSta/vehicleRouteStatic')],
            join_lane=end.get('lane'),bypasses_routing_decision_1014=True,paths=paths)
    right=links['10528']
    departure=right.find('fromLinkEndPt')
    lane1head=[h for h in xml.findall('./signalHeads/signalHead') if h.get('lane')=='1220011503 1'][0]
    assert departure.get('lane')=='1220011503 1' and float(departure.get('pos'))<float(lane1head.get('pos'))
    results={}
    for arm in ('hold','city'):
        completion=read('E:/VISSIM_analysis/20261010_sc15_source300/completion.json')
        content=pin(completion['arms'][arm]['cache'])
        assert hashlib.sha256(content).hexdigest()==completion['arms'][arm]['cache_sha256']
        cached=json.loads(gzip.decompress(content));tracks=defaultdict(list)
        for frame in cached['frames']:
            for row in frame['rows']:tracks[row[0]].append((frame['sec'],row))
        rows={}
        for dec in ('1099','1100'):
            s=source['arms'][arm][dec]
            north=[e for e in s['events'] if e['direction']=='north' and e['lower_sec']>=2400]
            head_ids={e['veh'] for e in s['matched_source_to_sc101']}
            straight=[];bypass=[];left=[];remaining=[];unresolved=[];tag1014=[];overlaps=[]
            for e in north:
                vid=e['veh'];track=[(t,r) for t,r in tracks[vid] if t>=e['upper_sec']]
                seen={r[1] for t,r in track}
                if any(r[5]=='1014' for t,r in track):tag1014.append(vid)
                if vid in head_ids and (10528 in seen or 10539 in seen):
                    overlaps.append(dict(veh=vid,head_then_connector=[x for x in (10528,10539) if x in seen]))
                assert not (10528 in seen and 10539 in seen), 'Repeated corridor traversal needs separate treatment'
                if 10528 in seen:bypass.append(vid)
                elif 10539 in seen:left.append(vid)
                elif vid in head_ids:straight.append(vid)
                elif any(t==cached['frames'][-1]['sec'] for t,r in track):remaining.append(vid)
                else:unresolved.append(vid)
            assert len(north)==sum(map(len,(straight,bypass,left,remaining,unresolved)))
            rows[dec]=dict(north_source_witnesses=len(north),through_lane_head_only_witnesses=straight,
                unsignalized_right_connector_witnesses=bypass,left_connector_witnesses=left,
                still_in_corridor_last_frame=remaining,unresolved_exit_or_head=unresolved,
                observed_route_1014_tags=tag1014,head_to_other_connector_witnesses=overlaps)
        results[arm]=rows
    for p in (ROOT/'evaluation/controllers/aggregate_route_corridors.py',ROOT/'vendor/NumSim-mine/src/models/urban_queue_model.py',
        A.parent.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md',A.parent.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md'):
        pin(p)
    # Runtime adds dedicated head detectors. Do not confuse them with older
    # base-network DCPs situated upstream of these heads.
    raw=read('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29/state_002550.json')
    bundle=oc.load_bundle(raw)
    detector_path=bundle.obs['detector_config']['path']
    assert hashlib.sha256(pin(detector_path)).hexdigest()==bundle.obs['detector_config']['sha256']
    detectors,_=oc.read_detector_csv(detector_path,bundle.obs['detector_config']['sha256'])
    actual_heads=[dict(dcp=d.dcp_no,lane=d.lane,pos_m=d.pos,ref=d.ref) for d in detectors if d.role=='head' and d.link==1220011503]
    assert len(actual_heads)==5
    pin(__file__)
    report=dict(status='complete_source_specific_turn_scope_mismatch',physical_geometry=geometry,
        routing_decision_1014=dict(link=decisions['1014'].get('link'),position=decisions['1014'].get('pos'),weights=native_weights),
        current_common_downstream_model_splits=movements,direct_beta_difference=direct_beta_difference,
        right_bypass=dict(connector='10528',from_lane=departure.get('lane'),position_m=float(departure.get('pos')),
            next_lane=right.find('toLinkEndPt').get('lane'),lane1_signal_position_m=float(lane1head.get('pos'))),
        native_witnesses=results,actual_runtime_head_detectors=actual_heads,source_pins=PINS,goal_complete=False,
        conclusion='Native1014 weights are close to the generic model, but SC15 side entries join downstream of1014. They enter different lanes and can leave via10528 beforeSC101 straight heads. Common downstream beta is not validated for these sources.',
        limitations=['An absent route tag alone is not proof of a native decision; the physical join location supplies that evidence.',
            'Observed connector counts are lower bounds. Unresolved/censored vehicles are not converted into turn shares.',
            'Two observed city vehicles cross through-lane head detectors and then use the left connector. Head crossings are not exact final-turn counts.',
            'This identifies a missing source/lane routing distinction; it does not identify exact future turning probabilities.',
            'Do not feed native2400–2850 route identities, future arrivals or fitted shares into autonomous predictions.',
            'No parameter change, native run, new rollout, optimizer or production deployment.'])
    (HERE/'routing_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for arm,rows in results.items():
        for dec,r in rows.items():print(arm,dec,{k:len(v) if isinstance(v,list) else v for k,v in r.items()})


if __name__=='__main__':main()
