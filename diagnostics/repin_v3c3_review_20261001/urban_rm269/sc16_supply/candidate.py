"""One offline SC16 east shared-lane service candidate; never native enabled."""
from copy import deepcopy
from functools import lru_cache
import hashlib,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
GROUP='1220011200:180601:p3'
MEMBERS={'SC16_E_to_W_SC7':('10257','1220009600','SC16_to_SC7'),
         'SC16_E_to_N_SC12':('10258','1220012700','SC16_to_SC12'),
         'SC16_E_to_S_SC109':('10259','1220009403','SC16_to_SC109')}

def supported_rate(doc):
    rows=[]
    for end in (1950,2100,2250,2400):
        group=doc['past'][str(end)]['SC16_E'];heads=group['rows']
        if len(heads)!=1:raise ValueError('Unreviewed physical head count')
        r=heads[0]
        if (r['head_id']!='180601' or r['sc']!='16' or r['sg']!='6' or r['lane']!=1
            or r['link']!='1220011200' or r['controlled_sec']!=150 or r['native_sec'] or r['unverified_sec']
            or r['boundary_ambiguous'] or r['green_sec']<30
            or not 0<=r['qualified_crossings']<=r['crossings']):raise ValueError('Unqualified past head observation')
        rows.append((r['qualified_crossings'],r['green_sec']))
    rates=[3600*sum(x[0] for x in pair)/sum(x[1] for x in pair) for pair in (rows[:2],rows[2:])]
    return min(rates)

@lru_cache(maxsize=1)
def evidence():
    data=(HERE/'assessment.json').read_bytes();doc=json.loads(data)
    for p,d in doc['source_pins'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=d:raise ValueError('Source changed: '+p)
    return supported_rate(doc)

def validate_turns(net):
    for m,(connector,target,receiver) in MEMBERS.items():
        turns=net.control_area_routes['movement:'+m]['physical_turns']
        if len(turns)!=1 or turns[0]['connector']!=connector or turns[0]['to_link']!=target:raise ValueError('Canonical receiver changed')

def install(cfg,at):
    if at not in (2400,3300):raise ValueError('Offline saved-state candidate only')
    net=cfg.network
    if hasattr(net,'sc16_east_service'):return deepcopy(net.sc16_east_service)
    parent=net.regular_alias_pool
    if parent['schema']!='regular-alias-head-pool/v1' or set(parent['groups'])!={'1220006903:10025:p1'}:raise ValueError('Wrong baseline')
    data=(ROOT/parent['network']['path']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=parent['network']['sha256']:raise ValueError('Physical network changed')
    tree=ET.fromstring(data);links={n.get('no'):n for n in tree.findall('./links/link')}
    heads=[n for n in tree.findall('./signalHeads/signalHead') if n.get('lane').split()[0]=='1220011200']
    if len(heads)!=1 or heads[0].get('no')!='180601' or heads[0].get('lane')!='1220011200 1' or heads[0].get('sg')!='16 6':raise ValueError('Physical head changed')
    found={k for k,l in links.items() if l.find('fromLinkEndPt') is not None and l.find('fromLinkEndPt').get('lane').split()[0]=='1220011200'}
    if found!={v[0] for v in MEMBERS.values()} or len(links['1220011200'].findall('./lanes/lane'))!=1:raise ValueError('Unreviewed shared-lane consumer')
    if '6' not in net.signal_actuation_contract['nodes']['SC16']['phase_signal_groups']['p3']:raise ValueError('Wrong physical green phase')
    actual_members={m for m,s in net.urban_movements.items() if s.get('origin')=='in_SC16_E' and s.get('beta',0)>0}
    if actual_members!=set(MEMBERS):raise ValueError('Unknown model head consumer')
    for m,(connector,target,receiver) in MEMBERS.items():
        c=links[connector];start=c.find('fromLinkEndPt');spec=net.urban_movements[m]
        if (start.get('lane')!='1220011200 1' or float(start.get('pos'))<=float(heads[0].get('pos'))
            or len(c.findall('./lanes/lane'))!=1 or c.find('toLinkEndPt').get('lane').split()[0]!=target):raise ValueError('Connector topology changed')
        if (spec.get('kind')!='boundary_in' or spec.get('phase')!='SC16_p3' or spec.get('signal')!='SC16'
            or spec.get('receiving_link')!=receiver or spec.get('ramp') or spec.get('unsignalized')):raise ValueError('Movement binding changed')
        if receiver not in net.urban_link_storage_veh:raise ValueError('Finite receiver missing')
    rate=evidence()
    if not math.isfinite(rate) or rate<=0:raise ValueError('Invalid past head rate')
    caps=dict(net.movement_capacity_by_movement_veh_h);old={m:caps[m] for m in MEMBERS}
    caps.update({m:rate for m in MEMBERS});net.movement_capacity_by_movement_veh_h=caps
    shared=deepcopy(parent);shared['groups'][GROUP]=dict(members=tuple(MEMBERS),signal='SC16',phase='SC16_p3',
        receivers={m:v[2] for m,v in MEMBERS.items()},service_veh_h=rate)
    net.regular_alias_pool=shared
    result=dict(at=at,cutoff_sec=2400,rate_veh_h=rate,inherited_rates=old,group=GROUP,new_rate_estimates=1,
        allocation='Ready-queue proportions of one physical head; receiver rejection retains unused share in this step.',
        production_installed=False)
    net.sc16_east_service=result
    return deepcopy(result)

def enable_hook():
    from evaluation.controllers import regular_alias_service
    original=regular_alias_service.configure
    if getattr(original,'_sc16_candidate',False):raise ValueError('Duplicate hook')
    def configure(cfg,tuning,raw):
        metadata=original(cfg,tuning,raw);r=install(cfg,int(raw['sim_sec']))
        return {**metadata,'diagnostic_sc16_east_head_veh_h':r['rate_veh_h']}
    configure._sc16_candidate=True;regular_alias_service.configure=configure
