"""Honor the existing native1032 input's committed1095:1 upstream route.

No demand, current stock, service, receiving or downstream SC6 choice changes.
"""
from pathlib import Path
from copy import deepcopy
import hashlib,math,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
ORIGIN='in_SC104_E';KEEP='SC104_E_to_W_SC6'
MEMBERS={KEEP:.5,'SC104_E_to_S_SC106':.25,'SC104_E_to_N':.25}
PATH=['55','10081','54','10080','53','10082','1220061200','10125','1220021204']
NET_SHA='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'

def require(condition,message):
    if not condition:raise ValueError(message)

def validate_current(frame,route_position):
    rows=[r for r in frame['vehicles'] if str(int(r[1])) in PATH[:-2]]
    for r in rows:
        if r[6] is None:
            require(r[1]==55 and r[3]<route_position,'Unassigned vehicle is already downstream of native route decision')
        else:
            require(r[6:9]==[1095.,1.,'STATIC'] or tuple(r[6:9])==(1095.,1.,'STATIC'),'Different current committed route')
            i=PATH.index(str(int(r[1])))
            require(r[9]==float(PATH[i+1]),'Current next link contradicts native committed path')
    return dict(current_source_vehicles=len(rows),committed=sum(r[6] is not None for r in rows),
                before_decision_uncommitted=sum(r[6] is None for r in rows))

def compile_spec(cfg,network,frame):
    require(hashlib.sha256(network).hexdigest()==NET_SHA,'Unreviewed physical network')
    root=ET.fromstring(network);links={n.get('no'):n for n in root.findall('./links/link')}
    inputs=cfg.network.native_input_schedule['inputs']
    here={k:v for k,v in inputs.items() if v.get('gate')==ORIGIN}
    require(set(here)=={'1032'} and here['1032']['physical_source']=='55','Another input shares the model gate')
    native=root.find("./vehicleInputs/vehicleInput[@no='1032']")
    require(native.get('link')=='55','Native input changed its physical source')
    d=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1095']")
    require(d.get('link')=='55' and d.get('allVehTypes')=='true' and d.get('routeChoiceMeth')=='STATIC','Native route authority changed')
    routes=d.findall('./vehRoutSta/vehicleRouteStatic')
    require(len(routes)==1 and routes[0].get('no')=='1' and not routes[0].get('formula'),'Not a single unconditional native path')
    r=routes[0];path=[d.get('link')]+[x.get('key') for x in r.findall('./linkSeq/intObjectRef')]+[r.get('destLink')]
    require(path==PATH,'Native committed path changed')
    require(len([q for q in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')
        if q.get('link') in PATH[:-1]])==1,'Another route decision precedes the target')
    for no,n in links.items():
        source=n.find('fromLinkEndPt');target=n.find('toLinkEndPt')
        if target is not None and target.get('lane').split()[0] in PATH[:-1]:
            require(source.get('lane').split()[0] in PATH[:-1],'Unreviewed side entry into the physical source')
        if source is not None and source.get('lane').split()[0]=='55':
            require(float(source.get('pos'))>float(d.get('pos')),'Input can leave before its route decision')
    downstream=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1032']")
    require(downstream.get('link')==PATH[-1] and float(r.get('destPos'))<float(downstream.get('pos')),
            'Committed upstream route does not end before downstream SC6 decision')
    movements=cfg.network.urban_movements;group={m:v for m,v in movements.items() if v.get('origin')==ORIGIN}
    require(set(group)==set(MEMBERS),'Model source acquired a different consumer')
    require(all(abs(group[m]['beta']-b)<1e-12 and group[m]['kind']=='boundary_in' and group[m]['phase']=='' for m,b in MEMBERS.items()),
            'Unreviewed source phase or prior split')
    turns=cfg.network.control_area_routes['movement:'+KEEP]['physical_turns']
    require(len(turns)==1 and [turns[0][k] for k in ('from_link','connector','to_link')]==PATH[-3:],
            'Canonical receiving turn differs from native path')
    require(group[KEEP]['receiving_link']=='SC104_to_SC6','Canonical receiver changed')
    current=validate_current(frame,float(d.get('pos')))
    return dict(input='1032',native_route='1095:1',path=path,old_beta=MEMBERS,
        new_beta={m:float(m==KEEP) for m in MEMBERS},current=current,
        demand_unchanged=True,current_state_unchanged=True,service_unchanged=True,
        receiving_unchanged=True,downstream_SC6_routing_unchanged=True,production_adopted=False)

def install(cfg,network,frame):
    spec=compile_spec(cfg,network,frame)
    for m,b in spec['new_beta'].items():cfg.network.urban_movements[m]['beta']=b
    return deepcopy(spec)
