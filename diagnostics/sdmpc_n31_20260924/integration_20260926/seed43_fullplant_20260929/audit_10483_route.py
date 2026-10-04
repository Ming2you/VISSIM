"""Pin the impossible10483-to10484 rebranch using the selected network and closed results."""
from pathlib import Path
import collections
import csv
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OLD=ROOT.parent/'control-full-review/diagnostics'
pins={}
def read(p):
    data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest();return data
def load(p):return json.loads(read(p))
target=HERE/'off10483_route_audit.json';assert not target.exists()
spec=load(HERE.parent/'selected/scenario/topology_routes_v2_8ac6fd.json')
network=ROOT/spec['network']['path'];tree=ET.fromstring(read(network))
assert pins[str(network)]==spec['network']['sha256']=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
paths=[]
for decision in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
    for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
        path=[decision.get('link')]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
        if '10483' in path:paths.append(dict(decision=decision.get('no'),route=route.get('no'),path=path,dest_pos=float(route.get('destPos'))))
assert len(paths)==1 and paths[0]['decision']=='1131' and paths[0]['route']=='3'
assert paths[0]['path'][paths[0]['path'].index('10483'):]==['10483','124','10775','125']
downstream_decisions=[d.attrib for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic') if d.get('link') in ('124','125')]
assert not downstream_decisions
off=tree.find("./links/link[@no='10483']");ramp=tree.find("./links/link[@no='10484']")
assert off.find('toLinkEndPt').get('lane').split()[0]=='124'
assert ramp.find('fromLinkEndPt').get('lane').split()[0]=='31'
native={}
for arm in ('nc','rm','vsl','both'):
    folder=OLD/('dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none' if arm=='nc'
                else f'metanet_net_gain_goal_20260924/heldout43/observations/{arm}')
    events=list(csv.DictReader(read(folder/'port_events.csv').decode('utf-8-sig').splitlines()))
    if arm!='nc':assert pins[str(folder/'port_events.csv')]==load(folder/'manifest.json')['files']['port_events.csv']
    exits=[r for r in events if r['connector']=='10483' and r['kind']=='departure' and 2250.1<float(r['time_s'])<=2700.1]
    ids={r['vehicle'] for r in exits}
    later=[r for r in events if r['connector'] in ('10484','10480') and r['kind']=='arrival'
           and r['vehicle'] in ids and any(float(r['time_s'])>float(e['time_s']) for e in exits if e['vehicle']==r['vehicle'])]
    assert not later
    native[arm]=dict(off10483_departures=len(exits),unique_vehicles=len(ids),later_onramp_entries=len(later),
                    departure_observed_links=dict(collections.Counter(r['other_link'] for r in exits)))
folder=HERE.parent/'closedloop_recorded2250_select_check_trace10484_gate_full_s43'
model={}
for arm in ('held_actual','selected'):
    data=read(folder/(arm+'_RM_C10484_trace.json.gz'));trace=json.loads(gzip.decompress(data))
    totals=collections.defaultdict(float)
    for r in trace['transfers']:totals[(r['source'],r['target'],r['route_key'])]+=r['vehicles']
    off_into_pool=sum(n for (source,destination,key),n in totals.items()
                      if source=='storage:lane_off_10483' and destination=='storage:SC1001_W_out')
    assert off_into_pool>0
    split=trace['upstream_storage']['SC1001_W_out']['split'];assert split['ramps']['RM_C10484']==.5
    model[arm]=dict(off10483_into_shared_pool=off_into_pool,split=split,
        shared_pool_to_10484=sum(n for (source,destination,key),n in totals.items()
                               if source=='storage:SC1001_W_out' and destination=='ramp:RM_C10484'),
        other_direct_10484_arrival=sum(n for (source,destination,key),n in totals.items()
                                      if destination=='ramp:RM_C10484' and source!='storage:SC1001_W_out'))
for name in ('lane_offramp_runtime.py','urban_flow_accounting.py','route_choice_corridor.py','vissim_stackelberg_adapter.py'):
    read(ROOT/'evaluation/controllers'/name)
read(Path(__file__))
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
report=dict(network_sha256=spec['network']['sha256'],fixed_native_paths=paths,downstream_decisions=downstream_decisions,
    native_departures=native,model_transfers=model,source_pins=pins,
    confirmed='Future10483 drainage loses its fixed1131:3 destination in SC1001_W_out; the generic split reoffers10484 even though that path is unreachable.',
    unresolved=['Mixed-pool trace has no source-cohort labels, so the exact fraction of10484 flow originating at10483 cannot be recovered.',
                'Initial124 vehicles have no live route IDs; distinguish committed future off-ramp receipts from ambiguous initial traffic.',
                'Shared downstream storage, receiving, travel time, Omega membership and real free-exit service must remain after any correction.'],
    corrective_scope='Extend existing destination-preserving storage accounting for the proven direct source; do not send all shared storage traffic to the free exit or add a capacity bonus.',
    forecasts_in_this_audit=0,new_native_runs=0,production_fix_applied=False)
target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(dict(native=native,model=model,confirmed=report['confirmed'])))
