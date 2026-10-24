"""Offline opt-in: remove false SC101 signal gating, retaining finite service."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib,json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc15_source301 import candidate as prior

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
MOV="SC101_S_SC1_to_E_SC5"
validate_turns,west,east=prior.validate_turns,prior.west,prior.east


def document():
    d=json.loads((HERE/"evidence.json").read_bytes())
    if d["schema"]!="sc101-prehead-peeloff302/v1":raise ValueError("Wrong302 evidence")
    for p,h in d["source_pins"].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError("Peeloff evidence changed")
    return d


def install(cfg,selected_plan,evidence,*,state_json=None):
    from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    d=evidence
    if d["movement"]!=MOV or d["path"]!=["1220011503","10528","336"]:
        raise ValueError("Unreviewed peeloff path")
    if state_json is not None and snapshot_network_sha256(state_json)!=d["network"]["sha256"]:
        raise ValueError("Snapshot and peeloff network differ")
    plan_path=ROOT/d["selected_plan"]["path"]
    raw=plan_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=d["selected_plan"]["sha256"] or selected_plan!=json.loads(raw):
        raise ValueError("Selected signal plan differs")
    old=cfg.network.urban_movements.get(MOV)
    if old!=d["expected_spec"] or old.get("unsignalized"):
        raise ValueError("SC101 movement semantics changed")
    conn=d["connector"];heads=d["source_heads"]
    if (conn["id"]!="10528" or conn["source_lane"]!=1 or conn["lanes"]!=1 or len(heads)!=5
        or {h["lane"] for h in heads}!={1,2,3,4,5}
        or any(h["SC"]!="SC101" or h["pos_m"]<=conn["source_pos"]
               or not h["all_vehicle_types"] or h["compliance"]!=1 for h in heads)):
        raise ValueError("Peeloff is not before every source head")
    if set(d["native_routes"])!={"1014:3"}:
        raise ValueError("Native route scope changed")
    if d["conflicts"]["1393"]!={"link1":"1210014303","link2":"10529","status":"TWOYIELDSONE"}:
        raise ValueError("Downstream yield relation changed")
    # No state or capacity mutation. This happens before service-pool construction.
    updated=dict(cfg.network.urban_movements)
    updated[MOV]={**old,"unsignalized":True}
    cfg.network.urban_movements=updated
    invalidate_topology_cache(cfg.network)
    result=dict(movement=MOV,before_signal_gating=True,after_signal_gating=False,
        preserved_phase=old["phase"],preserved_receiver=old["receiving_link"],
        downstream_yield_explicitly_modelled=False,
        interpretation="Existing finite movement service and receiving retained; no explicit gap-acceptance model added.")
    cfg.network.sc101_peeloff302=deepcopy(result)
    return result


@contextmanager
def hook(option):
    from evaluation.controllers import physical_movement_routes as pmr
    evidence=document()
    selected_original=pmr.configure_phase_authority
    def configure(cfg,tuning,selected_plan,*,state_json=None):
        base=selected_original(cfg,tuning,selected_plan,state_json=state_json)
        return {**base,"diagnostic_sc101_peeloff302":install(cfg,selected_plan,evidence,state_json=state_json)}
    with prior.hook(option) as side:
        pmr.configure_phase_authority=configure
        try:yield side
        finally:pmr.configure_phase_authority=selected_original

