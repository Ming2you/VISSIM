"""One bounded offline typed-service candidate, installed before local models.

Not enabled by a native config. Two labels share one observed phase budget.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib,json,math
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
MEMBERS=('SC12_W_SC11_to_N_SC6','SC12_W_to_N_SC6')
GROUP='1220012103:10242:p4:typed'

def supported_rate(doc):
    if doc.get('cutoff_sec')!=2400:raise ValueError('Past service cutoff changed')
    rows=doc['rows']
    if [(r['start_sec'],r['end_sec']) for r in rows]!=[(1800,1950),(1950,2100),(2100,2250),(2250,2400)]:raise ValueError('Predeclared past windows changed')
    rates=[]
    for r in rows:
        ids=set()
        for w in r['typed_witnesses']:
            t=w['head_time_sec'];p=w['prior']
            if (not r['start_sec']<t<r['end_sec'] or not 0<=t-p['time_sec']<=5.1
                or p['link']!=1220012103 or p['position_m']>=107.36635894390177
                or w['vehicle_id']!=p['vehicle_id'] or w['vehicle_id'] in ids):raise ValueError('Invalid typed past witness')
            ids.add(w['vehicle_id'])
            if w['proof']=='active_static_route_and_next_link':
                if p['route_type']!='Static' or p['next_link']!='10242' or not w['observed_current_route']:raise ValueError('Missing chosen direct route')
            elif w['proof']=='observed_adjacent_source_to_connector_frames':
                z=w['post_connector']
                if (not z or z['vehicle_id']!=p['vehicle_id'] or z['link']!=10242
                    or not t<z['time_sec']<2400 or abs(z['time_sec']-p['time_sec']-5)>1e-7):raise ValueError('Invalid observed connector transition')
            else:raise ValueError('Unqualified route attribution')
        if len(ids)!=r['typed_count'] or not 0<r['green_sec']<=150:raise ValueError('Typed support count or exposure changed')
    for pair in (rows[:2],rows[2:]):
        count=sum(r['typed_count'] for r in pair);green=sum(r['green_sec'] for r in pair)
        if count<5 or green<30:raise ValueError('Insufficient pooled typed support')
        rates.append(3600*count/green)
    rate=min(rates)
    if not math.isfinite(rate) or abs(rate-doc['selected_support_veh_h'])>1e-8:raise ValueError('Support estimator changed')
    return rate

@lru_cache(maxsize=1)
def evidence():
    doc=json.loads((HERE/'typed_support_v3.json').read_bytes())
    for p,h in doc['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError('Typed support source changed: '+p)
    return supported_rate(doc)

def validate_turns(net):
    """Validate canonical turns after runtime_setup has built the area routes."""
    for m in MEMBERS:
        turns=net.control_area_routes['movement:'+m]['physical_turns']
        if len(turns)!=1 or turns[0]['connector']!='10242':raise ValueError('Canonical turn changed')

def install(cfg,at):
    if at not in (2400,3300):raise ValueError('Saved-state candidate only; not native deployment')
    net=cfg.network
    if hasattr(net,'sc12w_typed_service'):return deepcopy(net.sc12w_typed_service)
    rate=evidence()
    parent=net.regular_alias_pool
    if parent['schema']!='regular-alias-head-pool/v1' or set(parent['groups'])!={'1220006903:10025:p1'}:raise ValueError('Baseline shared aliases changed')
    network=(ROOT/parent['network']['path']).read_bytes()
    if hashlib.sha256(network).hexdigest()!=parent['network']['sha256']:raise ValueError('Native geometry changed')
    tree=ET.fromstring(network);head=tree.find("./signalHeads/signalHead[@no='50201']")
    connector=tree.find("./links/link[@no='10242']")
    if (head.get('lane')!='1220012103 2' or head.get('sg')!='12 5'
        or connector.find('fromLinkEndPt').get('lane')!='1220012103 2'
        or len(connector.findall('./lanes/lane'))!=1
        or connector.find('toLinkEndPt').get('lane').split()[0]!='1220015100'
        or '5' not in net.signal_actuation_contract['nodes']['SC12']['phase_signal_groups']['p4']):raise ValueError('Physical phase/head/connector changed')
    expected={MEMBERS[0]:dict(kind='internal',signal='SC12',phase='SC12_p4',origin='SC11_to_SC12',receiving_link='SC12_to_SC6'),
        MEMBERS[1]:dict(kind='boundary_in',signal='SC12',phase='SC12_p4',origin='in_SC12_W',receiving_link='SC12_to_SC6')}
    found={m for m,s in net.urban_movements.items() if s.get('origin') in ('SC11_to_SC12','in_SC12_W')
        and s.get('receiving_link')=='SC12_to_SC6' and s.get('beta',0)>0}
    if found!=set(MEMBERS):raise ValueError('Unreviewed same-turn consumer')
    for m,spec in expected.items():
        actual=net.urban_movements[m]
        if any(actual.get(k)!=v for k,v in spec.items()) or actual.get('ramp') or actual.get('unsignalized'):raise ValueError('Source alias binding changed')
    if 'SC12_to_SC6' not in net.urban_link_storage_veh:raise ValueError('Finite receiver missing')
    caps=dict(net.movement_capacity_by_movement_veh_h);before={m:caps[m] for m in MEMBERS}
    rate=max(rate,sum(before.values()))
    for m in MEMBERS:caps[m]=rate
    net.movement_capacity_by_movement_veh_h=caps
    shared=deepcopy(parent)
    shared['groups'][GROUP]=dict(members=MEMBERS,signal='SC12',phase='SC12_p4',receiver='SC12_to_SC6',service_veh_h=rate)
    net.regular_alias_pool=shared
    result=dict(variant='offline_typed_SC12W_shared_budget',at=at,cutoff_sec=2400,rate_veh_h=rate,
        inherited_rates=before,group=GROUP,new_rate_estimates=1,production_installed=False,
        scope='Shared direct-north phase budget from past typed subset. Other phases, initial stock, demand, routes, arrival delay and receiver capacity unchanged.')
    net.sc12w_typed_service=result
    return deepcopy(result)

def enable_hook():
    from evaluation.controllers import regular_alias_service
    original=regular_alias_service.configure
    if getattr(original,'_sc12w_candidate',False):raise ValueError('Duplicate candidate hook')
    def configure(cfg,tuning,raw):
        metadata=original(cfg,tuning,raw)
        result=install(cfg,int(raw['sim_sec']))
        return {**metadata,'diagnostic_sc12w_shared_service_veh_h':result['rate_veh_h']}
    configure._sc12w_candidate=True
    regular_alias_service.configure=configure
