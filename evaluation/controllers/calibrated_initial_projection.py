"""Initial observation consistency and already-served stock assignment.

No rollout coefficient changes. Empty sources require independent proof; passed
heads retain physical-area membership and downstream storage limits.
"""
import math
from evaluation.controllers.area_runtime import model_inventory
from evaluation.controllers.control_area_objective import get_ledger
from src.models import urban_queue_model as uqm

def verify_lane_speed(encoded, factor, observed, nominal, delay_ratio, moving_stock_proof=None):
    numbers=(encoded,factor,nominal,delay_ratio)
    if any(not math.isfinite(float(x)) for x in numbers) or factor<=1 or nominal<=0 or delay_ratio<=0:
        raise ValueError("Invalid lane-delay encoding inputs")
    if observed is not None:
        if not math.isfinite(float(observed)) or observed<0:
            raise ValueError("Invalid observed speed")
        expected=factor*max(observed,nominal/delay_ratio)
        mode="observed_with_existing_delay_floor"
    else:
        expected_keys={"inventory","ledger","provenance","arrival","release"}
        if not isinstance(moving_stock_proof,dict) or set(moving_stock_proof)!=expected_keys:
            raise ValueError("Missing independent empty-moving-stock evidence")
        if any(not math.isfinite(float(v)) or abs(v)>1e-9 for v in moving_stock_proof.values()):
            raise ValueError("Missing observed speed with nonempty moving source")
        expected=factor*nominal
        mode="existing_nominal_for_empty_moving_stock"
    if abs(encoded-expected)>1e-8:
        raise ValueError("Incorrect lane-delay encoded speed")
    return {"mode":mode,"encoded_speed":encoded,"observed_speed":observed,
            "transport_speed_kph":encoded/factor,"state_modified":False}


def empty_proof(state,cfg,target):
    key="storage:"+target
    prov=state.local_observation_summary["projection_diagnostics"]["physical_stock_assignment_by_link"]
    return dict(inventory=model_inventory(state,cfg)[key],
        ledger=sum(get_ledger(state).stocks[key].values()),
        provenance=sum(v.get(key,0.) for v in prov.values()),
        arrival=sum(state.urban_arrival_buffer.get(target,{}).values()),
        release=sum(state.urban_storage_release_buffer.get(target,{}).values()))


def verify_speed(state,cfg,target,factor):
    observed=state.local_observation_summary["urban_link_speed_kph"].get(target)
    return verify_lane_speed(state.urban_link_speed_kph[target],factor,observed,
        cfg.network.urban_avg_speed_km_h,uqm.OBSERVED_SPEED_DELAY_CAP_RATIO,
        empty_proof(state,cfg,target) if observed is None else None)


def own_head(root,vehicle):
    lane=f'{vehicle["link_no"]} {vehicle["lane_no"]}'
    heads=[h for h in root.findall("./signalHeads/signalHead") if h.get("lane")==lane]
    if len(heads)!=1:raise ValueError("Current lane needs exactly one physical head")
    return float(heads[0].get("pos"))


def move_passed(state,cfg,vehicle,movement,root,source):
    # Match the existing shared-head initializer: assign the already served
    # current car once to downstream travelling stock and paired reservations.
    # The actual current physical side is retained; no simulated event is added.
    if movement is None:raise ValueError("Passed-head current vehicle needs a known destination")
    spec=cfg.network.urban_movements[movement]
    target=spec.get("receiving_link")
    if target not in state.urban_link_storage or target==source or spec.get("ramp"):
        raise ValueError("Passed-head receiver needs reviewed ordinary storage")
    turn=cfg.network.control_area_routes["movement:"+movement]["physical_turns"]
    if len(turn)!=1 or turn[0]["from_link"]!=str(vehicle["link_no"]):
        raise ValueError("Passed-head movement physical owner differs")
    connector=root.find("./links/link[@no='"+str(turn[0]["connector"])+"']")
    end=connector.find("fromLinkEndPt")
    if end.get("lane").split()[0]!=str(vehicle["link_no"]) or vehicle["position_m"]>float(end.get("pos"))+1e-6:
        raise ValueError("Passed-head current position beyond known connector")
    n=1.;origin="storage:"+source;receiver="storage:"+target
    ledger=get_ledger(state)
    if ledger.event_count!=0 or ledger.ttt_veh_h!=0 or ledger.captures_response:
        raise ValueError("Initial reassignment only")
    provenance=state.local_observation_summary["projection_diagnostics"]["physical_stock_assignment_by_link"]
    row=provenance[str(vehicle["link_no"])]
    if row.get(origin,0)<n or state.urban_link_storage[target]<n:
        raise ValueError("Passed-head migration exceeds observed source or downstream storage")
    before=sum(model_inventory(state,cfg).values())
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321.candidate import membership
    sides,_=membership();side="inside" if sides[str(vehicle["link_no"])] else "outside"
    if ledger.stocks[origin][side]<n:raise ValueError("Passed-head source side missing")
    # Special corridor owners need their own initialized-cohort migration.
    choice=getattr(cfg.network,"route_choice_corridor",{}) or {}
    for corridor in choice.get("corridors",[]):
        if target in corridor.get("capacity_veh",{}):
            raise ValueError("Passed-head destination has a dedicated corridor owner")
    state.urban_link_storage[source]+=n
    state.urban_link_storage[target]-=n
    row[origin]-=n;row[receiver]=row.get(receiver,0.)+n
    ledger.stocks[origin][side]-=n
    ledger.stocks.setdefault(receiver,{"inside":0.,"outside":0.})[side]+=n
    step=int(state.time_sec/cfg.simulation.T_u_sec)
    due=step+uqm._link_delay_steps(state,cfg,target)
    if target in uqm.approach_routing(cfg):uqm._schedule(state.urban_arrival_buffer,target,due,n)
    uqm._schedule(state.urban_storage_release_buffer,target,due,n)
    ledger.assert_stocks(model_inventory(state,cfg))
    assert abs(before-sum(model_inventory(state,cfg).values()))<1e-7
    return dict(vehicle=vehicle["veh_no"],movement=movement,source=source,target=target,
        current_physical_link=vehicle["link_no"],lane=vehicle["lane_no"],
        head_position_m=own_head(root,vehicle),position_m=vehicle["position_m"],
        arrival_sec=due*cfg.simulation.T_u_sec,vehicles=n,initial_side=side,
        future_head_service_charged=False,downstream_delay="existing_link_delay_steps",
        capacity_unchanged=True)


def initial_calendar(state,cfg,target):
    arrival=state.urban_arrival_buffer.get(target)
    release=state.urban_storage_release_buffer.get(target)
    if arrival is None or release is None:
        proof=empty_proof(state,cfg,target)
        if any(not math.isfinite(v) or abs(v)>1e-9 for v in proof.values()):
            raise ValueError("Missing initial calendar with nonempty source")
    return dict(arrival or {})
