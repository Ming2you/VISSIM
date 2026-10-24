"""Diagnostic physical through-head pool using the existing shared allocator."""
from copy import deepcopy
from pathlib import Path
import hashlib,json,math
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
MEMBERS=('SC107_W_SC1004_to_E_SC108','SC107_W_SC1005_to_E_SC108')
GROUP='1220000201:10023:p3:through'


def install(cfg):
    option=json.loads((HERE/'config.json').read_bytes())
    if option.get('diagnostic_shared_SC107_through_service') is not True:
        raise ValueError('Explicit diagnostic configuration required')
    if option.get('service_envelope')!='sum_inherited_movement_rates':
        raise ValueError('No new capacity fit allowed')
    net=cfg.network
    if hasattr(net,'sc107_shared316'):raise ValueError('Duplicate shared head install')
    aliases=net.regular_alias_pool;local=net.local_service_pool
    if aliases['schema']!='regular-alias-head-pool/v1' or local['schema']!='shared-local-service-pool/v1':
        raise ValueError('Verified shared allocator missing')
    if GROUP in aliases['groups'] or GROUP in local['groups'] or any(m in local['group_of'] for m in MEMBERS):
        raise ValueError('Physical service already owned')
    path=ROOT/aliases['network']['path'];data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=aliases['network']['sha256']:raise ValueError('Physical network changed')
    tree=ET.fromstring(data)
    node=tree.find("./links/link[@no='10023']")
    if (node.find('fromLinkEndPt').get('lane')!='1220000201 2'
        or len(node.findall('./lanes/lane'))!=4
        or node.find('toLinkEndPt').get('lane').split()[0]!='1220000402'):
        raise ValueError('Shared through connector geometry changed')
    heads=tree.findall('./signalHeads/signalHead')
    for lane in (2,3,4):
        found=[h for h in heads if h.get('lane')=='1220000201 '+str(lane)]
        if len(found)!=1 or found[0].get('sg')!='107 2' or float(found[0].get('pos'))>=float(node.find('fromLinkEndPt').get('pos')):
            raise ValueError('SG2 common-lane binding changed')
    if '2' not in net.signal_actuation_contract['nodes']['SC107']['phase_signal_groups']['p3']:
        raise ValueError('Physical SG2 does not belong to p3')
    for m,origin in zip(MEMBERS,('SC1004_to_SC107','SC1005_to_SC107')):
        spec=net.urban_movements[m]
        expected=dict(kind='internal',signal='SC107',phase='SC107_p3',origin=origin,receiving_link='SC107_to_SC108')
        if any(spec.get(k)!=v for k,v in expected.items()) or spec.get('ramp') or spec.get('unsignalized'):
            raise ValueError('Source, phase or receiving binding changed')
        turns=net.control_area_routes['movement:'+m]['physical_turns']
        if len(turns)!=1 or turns[0]['path']!=['1220000201','10023','1220000402']:
            raise ValueError('Source aliases do not share one through path')
    inherited={m:net.movement_capacity_by_movement_veh_h[m] for m in MEMBERS}
    if any(not math.isfinite(v) or v<=0 for v in inherited.values()):raise ValueError('Invalid inherited rates')
    rate=sum(inherited.values())
    row=dict(members=MEMBERS,signal='SC107',phase='SC107_p3',receiver='SC107_to_SC108',service_veh_h=rate)
    caps=dict(net.movement_capacity_by_movement_veh_h)
    # Each source may use the shared budget; the allocator debits one total.
    for m in MEMBERS:caps[m]=rate
    shared=deepcopy(aliases);shared['groups'][GROUP]=deepcopy(row)
    local=deepcopy(local);local['groups'][GROUP]=deepcopy(row);local['group_of'].update({m:GROUP for m in MEMBERS})
    net.movement_capacity_by_movement_veh_h=caps;net.regular_alias_pool=shared;net.local_service_pool=local
    receipt=dict(group=GROUP,inherited_rates=inherited,service_veh_h=rate,new_rate_fits=0,
        common_head_lanes=[2,3,4],current_routes_and_stock_unchanged=True,
        geometry_source=dict(path=str(path),sha256=hashlib.sha256(data).hexdigest()),
        limits=['This changes source partition of existing p3 service, not physical saturation or SG5 access.',
                'Aggregate ready queues share service; lateral gap/FIFO ordering is not explicitly modeled.'])
    net.sc107_shared316=receipt
    return deepcopy(receipt)


def refresh_local(follower,cfg):
    from src.controllers.local_signal_plant import build_local_model
    from evaluation.controllers.area_leader_objective import _joint_catalog
    from evaluation.controllers.local_signal_service import _model_view
    if follower.cfg is not cfg:raise ValueError('Shared configuration required')
    old=follower._local_models['SC107']
    follower._local_models['SC107']=build_local_model(cfg,'SC107',follower._specs,follower._phase_movements)
    new=follower._local_models['SC107']
    if set(new.movements)!=set(old.movements):raise ValueError('New control/movement axis not permitted')
    view=_model_view(new)
    if view['groups'][GROUP]['service_veh_h']!=cfg.network.sc107_shared316['service_veh_h']:
        raise ValueError('Stale local shared budget')
    _,_,catalog,_=_joint_catalog(follower)
    if any(catalog[m]!=('SC107','internal') for m in MEMBERS):raise ValueError('Lost unique local owner')
    return dict(owner='SC107',movement_axes_unchanged=True,local_global_budget_equal=True)
