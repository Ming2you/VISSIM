"""Bounded diagnostic: shared SC12 north heads with a one-lane right cap.

The nominal 1400 veh/h/head is a provisional prior, not observed saturation.
Keep the existing conservative aggregate multi-receiver allocator unchanged.
"""
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
import hashlib, math
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
T='SC12_N_SC6_to_S_SC16';R='SC12_N_SC6_to_W_SC11'
MEMBERS=(T,R);GROUP='sc12_north326:1220015000:heads123'
CAPS={T:4200.,R:1400.}


def install(cfg):
    net=cfg.network
    if hasattr(net,'sc12_head326'):raise ValueError('Duplicate SC12 north install')
    aliases=net.regular_alias_pool;local=net.local_service_pool
    if any(m in local['group_of'] for m in MEMBERS):raise ValueError('Already owned service')
    path=ROOT/aliases['network']['path'];data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=aliases['network']['sha256']:raise ValueError('Network changed')
    tree=ET.fromstring(data)
    for m,conn,lanes,to in ((T,'10235',3,'1220012600'),(R,'10236',1,'1220012003')):
        spec=net.urban_movements[m];turn=tree.find("./links/link[@no='"+conn+"']")
        expected=dict(signal='SC12',phase='SC12_p1',origin='SC6_to_SC12',kind='internal')
        if any(spec.get(k)!=v for k,v in expected.items()) or spec.get('ramp') or spec.get('unsignalized'):
            raise ValueError('Movement binding changed')
        if (turn.find('fromLinkEndPt').get('lane')!='1220015000 1'
            or len(turn.findall('./lanes/lane'))!=lanes
            or turn.find('toLinkEndPt').get('lane').split()[0]!=to):
            raise ValueError('Connector lanes changed')
        routes=net.control_area_routes['movement:'+m]['physical_turns']
        if len(routes)!=1 or [routes[0].get(k) for k in ('from_link','connector','to_link')]!=['1220015000',conn,to]:
            raise ValueError('Route changed')
        if spec['receiving_link'] not in net.urban_link_storage_veh:raise ValueError('Finite receiver missing')
    for lane in (1,2,3):
        heads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('lane')=='1220015000 '+str(lane)]
        if len(heads)!=1 or heads[0].get('sg')!='12 4' or float(heads[0].get('pos'))>=28.651408719053997:
            raise ValueError('Physical head binding changed')
    if '4' not in net.signal_actuation_contract['nodes']['SC12']['phase_signal_groups']['p1']:
        raise ValueError('Phase mapping changed')
    consumers={m for m,s in net.urban_movements.items() if s.get('signal')=='SC12' and s.get('phase')=='SC12_p1'
               and s.get('origin')=='SC6_to_SC12' and not s.get('unsignalized')}
    if consumers!=set(MEMBERS):raise ValueError('Unaccounted head consumer')
    inherited={m:net.movement_capacity_by_movement_veh_h[m] for m in MEMBERS}
    row=dict(members=MEMBERS,signal='SC12',phase='SC12_p1',service_veh_h=4200.,
             member_service_veh_h=dict(CAPS),receivers={m:net.urban_movements[m]['receiving_link'] for m in MEMBERS})
    caps=dict(net.movement_capacity_by_movement_veh_h);caps.update(CAPS)
    shared=deepcopy(aliases);shared['groups'][GROUP]=deepcopy(row)
    pool=deepcopy(local);pool['groups'][GROUP]=deepcopy(row);pool['group_of'].update({m:GROUP for m in MEMBERS})
    net.movement_capacity_by_movement_veh_h=caps;net.regular_alias_pool=shared;net.local_service_pool=pool
    receipt=dict(inherited_rates=inherited,member_caps=dict(CAPS),shared_cap=4200.,nominal_per_head=1400.,
                 observed_saturation=False,future_observation_inputs=False,coefficient_fits=0,
                 source_pins={str(path):hashlib.sha256(data).hexdigest()},
                 limitation='Existing proportional ready-stock sharing is conservative partial FIFO across the group; exclusive through lanes are not explicitly resolved.')
    net.sc12_head326=receipt
    return deepcopy(receipt)


@contextmanager
def enabled():
    from evaluation.controllers import local_signal_service as pool
    original=pool._model_view
    def model_view(model):
        spec=pool.view(model.cfg)
        if not spec or GROUP not in spec['groups'] or model.signal!='SC12':return original(model)
        groups={k:g for k,g in spec['groups'].items() if any(m in model.movements for m in g['members'])}
        for key,g in groups.items():
            if not set(g['members']).issubset(model.movements) or model.signal!=g['signal']:
                raise ValueError('Incomplete local physical pool')
            if 'receivers' in g and set(g['receivers'])!=set(g['members']):raise ValueError('Incomplete receiver contract')
            if key==GROUP and (g['member_service_veh_h']!=CAPS or g['service_veh_h']!=4200.):
                raise ValueError('Diagnostic member caps changed')
            for m in g['members']:
                cap=g['member_service_veh_h'][m] if key==GROUP else g['service_veh_h']
                if (model.receiving_of[m]!=pool.receiver_of(g,m) or model.cap_flow_of[m]!=cap
                    or model.phase_of[m]!=g['phase'].rsplit('_',1)[-1]):raise ValueError('Stale local physical service cache')
        return {**spec,'groups':groups,'group_of':{m:k for m,k in spec['group_of'].items() if k in groups}}
    pool._model_view=model_view
    try:yield
    finally:pool._model_view=original


def refresh_local(follower,cfg):
    from src.controllers.local_signal_plant import build_local_model
    from evaluation.controllers.local_signal_service import _model_view
    if follower.cfg is not cfg:raise ValueError('Shared config required')
    old=follower._local_models['SC12']
    new=build_local_model(cfg,'SC12',follower._specs,follower._phase_movements)
    if set(old.movements)!=set(new.movements):raise ValueError('Movement axes changed')
    follower._local_models['SC12']=new
    assert _model_view(new)['groups'][GROUP]['member_service_veh_h']==CAPS
    return dict(owner='SC12',axes_unchanged=True,local_global_caps_equal=True)
