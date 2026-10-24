"""Opt-in shared service for two source labels at the same physical SC1 head.

Only ready movement queues share the inherited aggregate service envelope.
No demand, stock, arrival time, destination or downstream storage is changed.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
MEMBERS=('SC1_S_SC107_to_N_SC101','SC1_S_to_N_SC101')
GROUP='1220006903:10025:p1'
SCHEMA='regular-alias-head-pool/v1'

def view(cfg):
    return getattr(cfg.network,'regular_alias_pool',None)

def configure(cfg,tuning,raw):
    path=(tuning or {}).get('urban',{}).get('capacity',{}).get('regular_alias_pool')
    net=cfg.network;prior=view(cfg)
    if prior and prior.get('schema')!=SCHEMA:raise ValueError('Unowned regular alias pool')
    if path is None:
        if prior:
            caps=dict(net.movement_capacity_by_movement_veh_h)
            if all(caps[m]==prior['service_veh_h'] for m in MEMBERS):caps.update(prior['inherited_rates'])
            net.movement_capacity_by_movement_veh_h=caps
            delattr(net,'regular_alias_pool')
        return {}
    if not isinstance(path,str) or not path or tuning.get('urban',{}).get('shared_local_service_pool') is not True:
        raise ValueError('Alias head pool needs the shared local service option')
    data=(ROOT/path).read_bytes();doc=json.loads(data);digest=hashlib.sha256(data).hexdigest()
    expected={
        MEMBERS[0]:dict(kind='internal',signal='SC1',phase='SC1_p1',origin='SC107_to_SC1',receiving_link='SC1_to_SC101'),
        MEMBERS[1]:dict(kind='boundary_in',signal='SC1',phase='SC1_p1',origin='in_SC1_S',receiving_link='SC1_to_SC101')}
    if (doc.get('schema')!=SCHEMA or doc.get('group')!=GROUP
        or doc.get('source_link')!='1220006903' or doc.get('connector')!='10025'
        or doc.get('target_link')!='1220008501' or doc.get('signal')!='SC1' or doc.get('phase')!='SC1_p1'
        or doc.get('heads')!=['10801','10802','10803'] or doc.get('head_lanes')!=[2,3,4]
        or doc.get('members')!=expected or doc.get('service_envelope')!='sum_inherited_movement_rates'):
        raise ValueError('Unreviewed physical alias pool')
    network=(ROOT/doc['network']['path']).read_bytes()
    if hashlib.sha256(network).hexdigest()!=doc['network']['sha256']:raise ValueError('Pinned alias network changed')
    if tuning.get('execution',{}).get('native_signal_record') is True:
        from evaluation.controllers.network_provenance import snapshot_physical_file_sha256
        observed=snapshot_physical_file_sha256(raw)
    else:observed=hashlib.sha256(Path(raw['network_path']).read_bytes()).hexdigest()
    if observed!=doc['network']['sha256']:raise ValueError('Alias pool and observed networks differ')
    tree=ET.fromstring(network);links={n.get('no'):n for n in tree.findall('./links/link')}
    heads={n.get('no'):n for n in tree.findall('./signalHeads/signalHead')}
    node=links['10025'];start=node.find('fromLinkEndPt');end=node.find('toLinkEndPt')
    if start.get('lane')!='1220006903 2' or len(node.findall('./lanes/lane'))!=4 or end.get('lane').split()[0]!='1220008501':
        raise ValueError('Alias connector geometry changed')
    actual_lanes=[]
    for key in doc['heads']:
        h=heads[key];link,lane=h.get('lane').split();lane=int(lane);actual_lanes.append(lane)
        if link!='1220006903' or h.get('sg')!='1 8' or float(h.get('pos'))>=float(start.get('pos')):
            raise ValueError('Alias physical head binding changed')
        post=[]
        for connector,other in links.items():
            src=other.find('fromLinkEndPt')
            if src is None or src.get('lane').split()[0]!=link:continue
            low=int(src.get('lane').split()[1])
            if lane in range(low,low+len(other.findall('./lanes/lane'))) and float(src.get('pos'))>=float(h.get('pos')):post.append(connector)
        if post!=['10025']:raise ValueError('Unresolved consumer after shared head')
    if sorted(actual_lanes)!=doc['head_lanes']:raise ValueError('Alias head lanes changed')
    clock=net.signal_actuation_contract['nodes']['SC1']
    if '8' not in clock['phase_signal_groups']['p1']:raise ValueError('Alias phase does not serve physical SG8')
    competing={m for m,s in net.urban_movements.items() if s.get('origin') in {'SC107_to_SC1','in_SC1_S'}
        and s.get('receiving_link')=='SC1_to_SC101' and s.get('beta',0)>0}
    if competing!=set(MEMBERS):raise ValueError('Unknown same-connector model consumer')
    for m,e in expected.items():
        s=net.urban_movements[m]
        if any(s.get(k)!=v for k,v in e.items()) or s.get('ramp') or s.get('unsignalized'):
            raise ValueError('Alias source, phase or receiver changed')
    if 'SC1_to_SC101' not in net.urban_link_storage_veh:raise ValueError('Alias pool has no finite receiver')
    caps=dict(net.movement_capacity_by_movement_veh_h)
    if prior and digest==prior['contract_sha256'] and all(caps[m]==prior['service_veh_h'] for m in MEMBERS):
        return {'regular_alias_pool_groups':1.,'regular_alias_pool_service_veh_h':prior['service_veh_h']}
    inherited={m:float(caps[m]) for m in MEMBERS}
    if any(not math.isfinite(v) or v<=0 for v in inherited.values()):raise ValueError('Invalid inherited alias capacity')
    rate=sum(inherited.values())
    for m in MEMBERS:caps[m]=rate
    net.movement_capacity_by_movement_veh_h=caps
    net.regular_alias_pool={**doc,'contract_sha256':digest,'inherited_rates':inherited,'service_veh_h':rate,
        'groups':{GROUP:dict(members=MEMBERS,signal='SC1',phase='SC1_p1',receiver='SC1_to_SC101',service_veh_h=rate)}}
    return {'regular_alias_pool_groups':1.,'regular_alias_pool_service_veh_h':rate}

def groups(cfg):
    return (view(cfg) or {}).get('groups',{})

def extend_local_pool(cfg):
    pool=getattr(cfg.network,'local_service_pool',None)
    if not groups(cfg):return
    if not pool:raise ValueError('Regular alias pool missing local binding')
    for key,row in groups(cfg).items():
        if key in pool['groups'] or any(m in pool['group_of'] for m in row['members']):
            raise ValueError('Alias physical service is already owned')
        pool['groups'][key]=deepcopy(row)
        pool['group_of'].update({m:key for m in row['members']})

