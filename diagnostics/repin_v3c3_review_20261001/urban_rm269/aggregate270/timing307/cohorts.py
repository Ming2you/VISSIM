"""Locate SC6 P1 crossers relative to the common current stock, without replay."""
import json,pickle
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
from audit import A,ROOT,HERE,RUNS,MODEL,oc,read,pin,PINS
TARGET='SC12_to_SC6';STOPLINE='1210018302'
def main():
    assert not (HERE/'cohorts.json').exists()
    cfg,state,_=pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle'))
    raw=read(RUNS['hold']/'state_002400.json');other=read(RUNS['city']/'state_002400.json')
    assert raw['vehicle_records']==other['vehicle_records']
    meta=raw['vehicle_records'];physical={r['veh_no']:r for r in meta['records']}
    assert meta['complete'] and meta['record_count']==meta['collection_count_before']==meta['collection_count_after']==len(physical)
    assert meta['unobservable_count']==meta['external_source_count']==0
    frame=read(RUNS['hold']/raw['obs150']['frames']['current']['path'])
    assert frame['complete'] and frame['time_s']==2400 and len(frame['vehicles'])==len(physical)
    provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    support={k:v for k,v in provenance.items() if any(x=='storage:'+TARGET or x.startswith('movement:SC6_S_SC12_') for x in v)}
    ids={i for i,v in physical.items() if str(v['link_no']) in support}
    assert len(ids)==round(sum(sum(v.values()) for v in support.values()))
    network=ET.fromstring(pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    paths={}
    for d in network.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
            paths[(int(d.get('no')),int(r.get('no')))]=[d.get('link'),*[x.get('key') for x in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
    turns={'10205':'p1_N','10207':'p1_E','10206':'p2_W'}
    routes=[]
    for row in frame['vehicles']:
        if row[0] not in ids:continue
        destination='unresolved'
        if all(x is not None for x in row[6:9]) and row[8]=='STATIC':
            path=paths[(int(row[6]),int(row[7]))]
            if path.count(str(row[1]))==1 and path.count(STOPLINE)==1:
                at=path.index(STOPLINE)
                if path.index(str(row[1]))<=at<len(path)-1:destination=turns.get(path[at+1],'other')
        routes.append(dict(vehicle=row[0],link=row[1],lane=row[2],position=row[3],speed=row[4],
                           known_sc6_destination=destination,current_route=[row[6],row[7],row[8]]))
    grouped={};event_rows={}
    for arm,folder in RUNS.items():
        rows=[];windows=[]
        for end in (2550,2700,2850):
            current=read(folder/f'state_{end:06}.json');b=oc.load_bundle(current);w=oc.assign_window(b.obs,b.mer_rows)
            dets,_=oc.read_detector_csv(b.obs['detector_config']['path'],b.obs['detector_config']['sha256'])
            pin(b.obs['detector_config']['path']);pin(folder/b.obs['mer']['chunk'])
            sg=set(cfg.network.signal_actuation_contract['nodes']['SC6']['phase_signal_groups']['p1'])
            wanted=[d for d in dets if d.role=='head' and d.link==int(STOPLINE) and oc.parse_head_ref(d.ref)[2] in sg]
            these=[]
            for d in wanted:
                for r in w.entries[d.dcp_no]:
                    before=physical.get(r.veh)
                    category=('initial_target_origin' if r.veh in ids else 'initial_elsewhere') if before else 'absent_complete_initial_stock'
                    these.append(dict(vehicle=r.veh,time=r.t_entry,category=category,
                                      initial_link=before['link_no'] if before else None))
            windows.append(dict(end=end,counts=dict(Counter(x['category'] for x in these)),
                                initial_links=dict(Counter(str(x['initial_link']) for x in these if x['initial_link'] is not None)),
                                unresolved_tail=sum(w.tails[d.dcp_no] for d in wanted)))
            rows.extend(these)
        grouped[arm]=windows;event_rows[arm]=rows
    result=dict(status='complete_common_initial_cohort_classification',initial_target_count=len(ids),
        initial_physical_provenance=support,initial_route_counts=dict(Counter(r['known_sc6_destination'] for r in routes)),
        initial_routes=routes,head_events=event_rows,windows=grouped,source_pins=PINS,
        budget=dict(new_forecasts=0,new_native=0,fzp_scans=0,fits=0),
        limits=['Future head observations label diagnostic outcomes only; not predictor inputs.',
          'Initial destination is resolved only when the current static route actually spans the stopline.',
          'Absence in the complete initial stock indicates a later appearance, not a proven input source.',
          'Head P1 crossings include right turns and may precede connector crossing by a short distance.'])
    pin(Path(__file__))
    (HERE/'cohorts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('INITIAL',len(ids),result['initial_route_counts']);print('WINDOWS',grouped)
if __name__=='__main__':main()
