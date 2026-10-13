"""Opt-in native bridge for the reviewed aggregate urban calibration.

Historical coefficients are explicit immutable input data. Current physical
queues/routes are projected once, before follower models are constructed.
Workers install the same tested rollout functions from the pickled configuration;
they do not read historical observations or repeat current-state projection.
"""
from contextlib import ExitStack,contextmanager
from copy import deepcopy
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PACKAGE='diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270'
ATTR='calibrated_urban_native348'
_active=None

def module(name):
    from importlib import import_module
    return import_module(PACKAGE+'.'+name)

def load(tuning):
    option=(tuning or {}).get('urban',{}).get('calibrated_aggregate')
    if option is None:return None
    if not isinstance(option,dict) or set(option)!={'path','sha256'}:
        raise ValueError('calibrated_aggregate requires an explicit pinned document')
    path=(ROOT/option['path']).resolve()
    if not path.is_relative_to(ROOT):raise ValueError('Calibration must be frozen with the checkout')
    blob=path.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=option['sha256']:raise ValueError('Urban calibration pin differs')
    data=json.loads(blob)
    if data['schema']!='calibrated-urban-native348/v1':raise ValueError('Unknown calibration recipe')
    net=ROOT/data['network']['path']
    if hashlib.sha256(net.read_bytes()).hexdigest()!=data['network']['sha256']:
        raise ValueError('Calibration network differs')
    data['document_sha256']=option['sha256']
    return data

def phase(cfg,data):
    if data is None:return
    from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
    m=data['peeloff']['movement'];old=cfg.network.urban_movements[m]
    expected=data['peeloff']['spec']
    if any(old.get(k)!=v for k,v in expected.items() if k!='unsignalized'):
        raise ValueError('SC101 pre-head peeloff topology differs')
    cfg.network.urban_movements[m]=dict(old,unsignalized=True)
    invalidate_topology_cache(cfg.network)

def service(cfg,data):
    if data is None:return
    net=cfg.network
    for m,spec in data['movement_contracts'].items():
        if m in data['service_floors']:continue  # Native input authority is installed later.
        if any(net.urban_movements[m].get(k)!=v for k,v in spec.items()):
            raise ValueError('Calibrated movement differs: '+m)
    pool=deepcopy(net.regular_alias_pool)
    if set(pool['groups'])&set(data['shared_groups']):raise ValueError('Duplicate calibrated head pool')
    pool['groups'].update(deepcopy(data['shared_groups']))
    net.regular_alias_pool=pool
    caps=dict(net.movement_capacity_by_movement_veh_h)
    caps.update(data['movement_rates'])
    net.movement_capacity_by_movement_veh_h=caps
    for spec in net.route_choice_corridor['corridors']:
        if spec['decision'] in data['native_fixed_service']:
            spec['native_fixed_service']['calibrated_service_veh_h']=data['native_fixed_service'][spec['decision']]
    setattr(net,ATTR,deepcopy(data))

def configure_queue_projection(cfg,raw,data):
    """Retain observed zero ready queues before stock/arrival initialization.

    The current-link tag projectors use the contiguous queue definition.
    A zero from that complete walk must not fall back to all stopped vehicles.
    Other origins keep their existing observation policy.
    """
    if data is None:return {}
    import math
    targets={module('sc12_initial306.candidate').LINK,module('sc16_aggregate323.candidate').LINK} | set(module('sc109_initial320.candidate').LINKS) | {module('sc105_initial340.candidate').TERMINAL}
    records=raw.get('vehicle_records',{})
    bins=raw.get('local_observation',{}).get('queue_bins')
    if (not records.get('complete') or not isinstance(bins,dict)
            or any(records.get(k)!=raw['sim_sec'] for k in
                ('paused_at_sim_sec','capture_sim_sec_before','capture_sim_sec_after'))):
        raise ValueError('Calibrated queue projection needs complete current records and bins')
    observed,expected={},{}
    for v in records['records']:
        if str(v['link_no']) in targets:
            key=(str(v['link_no']),str(v['lane_no']))
            counts=expected.setdefault(key,[0,0]);counts[0]+=1;counts[1]+=bool(v['stopped'])
    for key,counts in bins.items():
        parts=str(key).split('|')
        if parts[0] not in targets:continue
        if (len(parts)!=3 or not isinstance(counts,(list,tuple)) or len(counts)!=2
                or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in counts)
                or not 0<=counts[1]<=counts[0]):
            raise ValueError('Invalid calibrated queue bins')
        values=observed.setdefault(tuple(parts[:2]),[0,0])
        for i in range(2):values[i]+=counts[i]
    for key in set(observed)|set(expected):
        if observed.get(key,[0,0])!=expected.get(key,[0,0]):
            raise ValueError('Calibrated queue bins do not cover current lane records')
    cfg.network.kinematic_queue_zero_links=frozenset(
        set(getattr(cfg.network,'kinematic_queue_zero_links',()))|targets)
    # SC10 is an intermediate fixed signal on the SC6->SC12 approach.
    # Its stopped stock waits in that approach, not in the downstream SC12
    # ready queue. The existing gate325 runtime supplies its actual gate service.
    gate=module('sc10_north325.candidate')
    upstream=dict(getattr(cfg.network,'head_queue_upstream_storage',{}))
    if gate.GATE in upstream and upstream[gate.GATE]!=gate.TARGET:
        raise ValueError('Calibrated intermediate signal has another storage owner')
    upstream[gate.GATE]=gate.TARGET
    cfg.network.head_queue_upstream_storage=upstream
    return {'calibrated_observed_zero_queue_links':sorted(targets),
            'calibrated_intermediate_queue_storage':{gate.GATE:gate.TARGET}}


def initialize(cfg,state,raw,frame,data):
    if data is None:return state,{}
    if cfg.simulation.T_f_sec!=5 or cfg.simulation.T_u_sec!=10:
        raise ValueError('Calibrated aggregate runtime requires FW5/urban10 clocks')
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.aggregate_route_corridors import configure_branch_service
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    module('transfer331.inputs').validate(raw,frame,state.time_sec)
    netbytes=(ROOT/data['network']['path']).read_bytes()
    sides,_=module('sc109_routes321.candidate').membership()
    lanes=adapter._contiguous_stopline_queue(raw,per_lane=True)
    initial={side:sum(v[side] for v in get_ledger(state).stocks.values()) for side in ('inside','outside')}
    receipts={}
    caps=dict(cfg.network.movement_capacity_by_movement_veh_h)
    for m,rate in data['service_floors'].items():
        expected=data['movement_contracts'][m]
        if any(cfg.network.urban_movements[m].get(k)!=v for k,v in expected.items()):
            raise ValueError('Calibrated movement differs after authority: '+m)
        caps[m]=max(caps[m],rate)
    cfg.network.movement_capacity_by_movement_veh_h=caps
    def check(label):
        ledger=get_ledger(state);ledger.assert_stocks(model_inventory(state,cfg))
        for side,n in initial.items():
            if abs(sum(v[side] for v in ledger.stocks.values())-n)>1e-7:
                raise ValueError('Current projection changed area stock: '+label)
    component=module('sc12_initial306.candidate')
    state,receipts['306']=project_current_link(component,state,cfg,raw,frame,netbytes,sides[component.LINK],lanes)
    check('306')
    receipts['311']=module('sc108_geometry311.candidate').install(cfg,state)
    receipts['316']=module('sc107_shared316.candidate').install(cfg)
    receipts['317']=module('sc109_transport317.candidate').install(cfg,state)
    state,receipts['339']=module('corridor339.project').install(cfg,state,raw,frame,netbytes,lanes)
    check('339')
    sc16=module('sc16_aggregate323.candidate');support=data['sc16']
    old={m:cfg.network.urban_movements[m]['beta'] for m in sc16.MOVEMENTS}
    if old!=support['beta_before']:raise ValueError('SC16 prior composition differs')
    for m,b in support['beta_after'].items():cfg.network.urban_movements[m]['beta']=b
    cfg.network.movement_capacity_by_movement_veh_h[sc16.LEFT]=support['service_after_veh_h']
    from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
    invalidate_topology_cache(cfg.network)
    state,receipts['323']=project_current_link(sc16.projection,state,cfg,raw,frame,netbytes,sides[sc16.LINK],lanes)
    check('323')
    with module('corridor339.gate_coverage').enabled(cfg,netbytes):
        state,receipts['325']=module('sc10_north325.candidate').install(cfg,state,raw,frame,netbytes,lanes)
    check('325')
    receipts['329']=module('native_routes329.candidate').install(cfg,netbytes)
    state,receipts['340']=module('sc105_initial340.candidate').install(cfg,state,raw,frame,netbytes,lanes)
    check('340')
    receipts['347']=configure_branch_service(cfg,data['branch_service'])
    # Current geometry/programs are frozen in cfg for spawned workers too.
    data=deepcopy(data)
    data['south_geometry']=module('gate296.candidate').geometry(ROOT,cfg)
    data['side_geometry']=module('sc101_clock299.source_geometry').geometry(ROOT,cfg)
    data['prehead_geometry']=module('sc108_geometry311.candidate').geometry(cfg)
    setattr(cfg.network,ATTR,data)
    install(cfg)
    return state,dict(calibrated_urban_native348=True,calibration_training=data['training'],
        calibration_current_stock=initial,calibration_components=list(receipts),
        calibration_projection_at_sec=state.time_sec,calibration_future_observations=False)

def project_current_link(component,state,cfg,raw,frame,network,inside,lanes):
    # Complete current rosters omit empty physical links from provenance. There
    # is no cohort to relabel; retain all stock belonging to other source links.
    physical=[v for v in raw['vehicle_records']['records'] if str(v['link_no'])==component.LINK]
    provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    if not physical and component.LINK not in provenance:
        return state,dict(physical_link=component.LINK,empty_current_cohort=True,at_sec=state.time_sec)
    return component.project(state,cfg,raw,frame,network,inside,lanes)

@contextmanager
def side_runtime(cfg,data):
    """299 travel + 303 source tags, using fixed training shares in cfg."""
    from evaluation.controllers.aggregate_route_corridors import Routes
    from evaluation.controllers import physical_ramp_branches as prb
    from src.models import urban_queue_model as uqm
    tag=module('sc101_route_tags303.candidate');clock=module('sc101_clock299.candidate')
    old_advance,old_schedule,old_split,old_delay=Routes.advance_one,uqm._schedule,prb.split_tagged_arrival,uqm._link_delay_steps
    support=data['source_route_support'];geom=data['side_geometry'];active=None
    def enabled(current):
        value=getattr(current.network,ATTR,None)
        return value is not None and value['document_sha256']==data['document_sha256']
    def advance(self,state,control,current,step,spec):
        nonlocal active
        if active is not None:raise RuntimeError('Nested calibrated source')
        if enabled(current) and spec['decision'] in support['sources']:active=(state,spec)
        try:
            result=old_advance(self,state,control,current,step,spec)
            if enabled(current):tag.verify_pending(state)
            return result
        finally:active=None
    def delay(state,current,target):
        if active is None or not enabled(current) or target!=tag.TARGET:return old_delay(state,current,target)
        spec=active[1];proof=geom['sources'][spec['decision']];branch=spec['branches']['1']
        if branch['destination']!=target or branch['connector']!=proof['connector'] or spec['prefix_storage']!=proof['source']:
            raise ValueError('Calibrated side source differs')
        return clock.delay_steps(state,current,geom,spec['decision'])
    def schedule(buffer,key,due,n):
        old_schedule(buffer,key,due,n)
        if active is not None and key==tag.TARGET and buffer is active[0].urban_arrival_buffer and n>0:
            tag.add_tag(active[0],active[1]['decision'],due,n,support)
    def split(state,current,source,step,arrived,routing):
        if not enabled(current):return old_split(state,current,source,step,arrived,routing)
        return tag.split(state,current,source,step,arrived,routing,support,old_split)
    Routes.advance_one=advance;uqm._link_delay_steps=delay;uqm._schedule=schedule;prb.split_tagged_arrival=split
    try:yield
    finally:
        Routes.advance_one=old_advance;uqm._link_delay_steps=old_delay;uqm._schedule=old_schedule;prb.split_tagged_arrival=old_split

@contextmanager
def prehead_runtime(data):
    # Local and direct joint rollouts own deep-copied cfg objects. Bind by the
    # immutable calibration document, not Python identity of the parent cfg.
    from src.models import urban_queue_model as uqm
    clock=module('sc108_geometry311.candidate');old=uqm._link_delay_steps
    def delay(state,cfg,target):
        value=getattr(cfg.network,ATTR,None)
        if value is None or value['document_sha256']!=data['document_sha256'] or target!=clock.TARGET:
            return old(state,cfg,target)
        return clock.delay_steps(state,cfg,data['prehead_geometry'])
    uqm._link_delay_steps=delay
    try:yield
    finally:uqm._link_delay_steps=old

def install(cfg):
    global _active
    data=getattr(cfg.network,ATTR,None)
    if data is None:return {}
    if _active is not None:
        if _active[0] is cfg:return {'calibrated_urban_runtime_restored':True}
        _active[1].close();_active=None
    stack=ExitStack()
    try:
        stack.enter_context(module('sc109_transport317.candidate').enabled())
        stack.enter_context(module('sc10_north325.candidate').enabled())
        stack.enter_context(module('native_routes329.candidate').enabled())
        stack.enter_context(side_runtime(cfg,data))
        stack.enter_context(module('gate296.candidate').installed(cfg,'aggregate_sc10_native_calendar',data['south_geometry']))
        stack.enter_context(prehead_runtime(data))
    except BaseException:
        stack.close();raise
    _active=(cfg,stack)
    return {'calibrated_urban_runtime_restored':True}
