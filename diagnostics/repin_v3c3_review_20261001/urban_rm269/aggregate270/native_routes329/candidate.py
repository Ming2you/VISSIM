"""Diagnostic aggregate future RD33 choices for two proven incoming sources.

No change to current known routes, demand, service rates, finite parent storage
or objective. Incoming1032:1 ends downstream of RD33 and is NOT reinterpreted.
"""
from pathlib import Path
from contextlib import contextmanager
import copy,hashlib,math,xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as gate

ATTR='_sc12_future_routes329'
EXPECTED={'1':('SC12_N_SC6_to_E_SC106','10224','10237',47.),
          '2':('SC12_N_SC6_to_S_SC16','10223','10235',477.),
          '3':('SC12_N_SC6_to_W_SC11','10223','10236',75.)}
DOCS='https://cgi.ptvgroup.com/vision-help/VISSIM_2026_EN-DE/en-us/Content/5_Netzbearbeiten/Fzgverkehr_Routen_RoutenEntsch_mod.htm'
require=gate.require


def compile_spec(cfg,network):
    from evaluation.controllers.offramp_routing import _weight
    from src.models.urban_queue_model import approach_routing
    require(not hasattr(cfg.network,ATTR),'Duplicate future choice')
    require(hashlib.sha256(network).hexdigest()==gate.NETWORK_SHA,'Unreviewed network')
    previous=getattr(cfg.network,gate.ATTR,None)
    require(previous is not None,'Existing finite SC10 gate required')
    root=ET.fromstring(network);links={x.get('no'):x for x in root.findall('./links/link')}
    choice=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='33']")
    require(choice.get('link')==gate.SHARED[0] and choice.get('allVehTypes')=='true'
        and choice.get('routeChoiceMeth')=='STATIC','Future decision contract changed')
    starts=[float(x.get('start')) for x in root.findall(".//timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")]
    require(starts==[0.],'Time-varying choices require another provider')
    require(len([d for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')
        if d.get('link') in gate.PRE|gate.POST])==1,'Additional decision inside corridor')
    pos=float(choice.get('pos'));heads=root.findall('./signalHeads/signalHead')
    gp=min(float(h.get('pos')) for h in heads if h.get('sg')=='10 4')
    stop=min(float(h.get('pos')) for h in heads if h.get('lane').split()[0]==gate.TERMINAL)
    routes={};weights={}
    for r in choice.findall('./vehRoutSta/vehicleRouteStatic'):
        key=r.get('no');require(key in EXPECTED and not r.get('formula'),'Unsupported future route')
        movement,prehead,turn,expected_weight=EXPECTED[key]
        path=[choice.get('link'),*[x.get('key') for x in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
        require(path[:5]==gate.SHARED[:5] and path[5:8]==[prehead,gate.TERMINAL,turn],'Unexpected route path')
        require(_weight(r)==expected_weight,'Relative flow changed')
        route=cfg.network.control_area_routes['movement:'+movement]['physical_turns']
        require(len(route)==1 and route[0]['connector']==turn and route[0]['to_link']==path[-1],'Turn destination changed')
        routes[movement]=dict(route='33:'+key,path=path,post_m=gate.measure(path[2:7],links,gp,stop),weight=expected_weight)
        weights[movement]=expected_weight
    require(len(routes)==3,'Incomplete future routes')
    total=math.fsum(weights.values());weights={k:v/total for k,v in weights.items()}
    incoming={};eligible={}
    for movement,old in previous['sources'].items():
        turns=cfg.network.control_area_routes['movement:'+movement]['physical_turns']
        require(len(turns)==1,'Ambiguous incoming route')
        tr=turns[0];entry=links[tr['connector']].find('toLinkEndPt')
        require(entry.get('lane').split()[0]==choice.get('link') and float(entry.get('pos'))<pos,'Entry misses decision')
        upstream=[]
        for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
            for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
                path=[d.get('link'),*[x.get('key') for x in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
                if tr['connector'] in path:
                    upstream.append(dict(route=d.get('no')+':'+r.get('no'),path=path,
                        destination=r.get('destLink'),position_m=float(r.get('destPos'))))
        require(len(upstream)==1 and upstream[0]['destination']==choice.get('link'),'Incoming committed path unclear')
        proof=upstream[0];accept=proof['position_m']<pos
        incoming[movement]=dict(entry_m=float(entry.get('pos')),upstream=proof,eligible=accept,
            reason='Previous route ends before RD33' if accept else 'Previous route ends after RD33: leave original treatment; native continuation unresolved')
        if accept:eligible[movement]=copy.deepcopy(old)
    require(len(eligible)==2 and len(incoming)==3,'Eligibility changed')
    spec=dict(source=gate.TARGET,decision='33',position_m=pos,weights=weights,routes=routes,
        incoming=incoming,eligible_sources=eligible,network_sha=gate.NETWORK_SHA,
        network_path=str(gate.ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'),
        former_beta=dict(approach_routing(cfg)[gate.TARGET]),source_pins=copy.deepcopy(previous['source_pins']),
        native_route_rule_reference=DOCS,current_state_modified=False,future_observations_used=False,
        rate_changes=False,production_adopted=False)
    return spec


def install(cfg,network):
    spec=compile_spec(cfg,network)
    setattr(cfg.network,ATTR,spec)
    return copy.deepcopy(spec)


def register(state,cfg,movement,vehicles,step,entry_step=None):
    spec=getattr(cfg.network,ATTR);geom=getattr(cfg.network,gate.ATTR)
    require(movement in spec['eligible_sources'],'Not a proven future source')
    require(float(vehicles)>=0 and math.isfinite(float(vehicles)),'Invalid accepted volume')
    dt=cfg.simulation.T_u_sec;entry=step if entry_step is None else entry_step
    speed=state.urban_link_speed_kph[gate.TARGET]/geom['lane_factor'];nominal=cfg.network.urban_avg_speed_km_h
    pre=gate.steps(spec['eligible_sources'][movement]['pre_m'],speed,nominal,dt)
    parts={};used=0.;keys=list(spec['weights'])
    for i,m in enumerate(keys):
        amount=vehicles-used if i==len(keys)-1 else vehicles*spec['weights'][m]
        post=gate.steps(spec['routes'][m]['post_m'],speed,nominal,dt)
        gate.register(getattr(state,gate.ATTR),entry+pre,post,amount,m)
        parts[m]=dict(vehicles=float(amount),post_sec=post*dt);used+=amount
    require(abs(float(used-vehicles))<1e-9,'Route split lost vehicles')
    return dict(source=movement,entry_sec=entry*dt,gate_due_sec=(entry+pre)*dt,
        accepted_veh=float(vehicles),routes=parts,decision='33')


@contextmanager
def enabled():
    from evaluation.controllers import urban_flow_accounting as ufa
    original=ufa._receive_corridor;records=[]
    def receive(state,cfg,movement,vehicles,step,*,entry_step=None):
        spec=getattr(cfg.network,ATTR,None)
        if spec is None or movement not in spec['eligible_sources']:
            return original(state,cfg,movement,vehicles,step,entry_step=entry_step)
        # Upstream canonical allocation has already charged the one physical
        # receiver. Only its aggregate route/due tags are installed here.
        records.append(register(state,cfg,movement,vehicles,step,entry_step))
        return True
    ufa._receive_corridor=receive
    try:yield records
    finally:ufa._receive_corridor=original

