"""Offline SC12 north service bound from a queued, shared-head prefix."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import hashlib,json,math
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc101_route_tags303 import candidate as prior
HERE=Path(__file__).resolve().parent
hook_prior=prior.hook
validate_turns,west,east,MOV,verify_pending,ATTR=prior.validate_turns,prior.west,prior.east,prior.MOV,prior.verify_pending,prior.ATTR
def evidence():
    d=json.loads((HERE/"past_shared_prefix_support.json").read_bytes())
    for p,h in d["source_pins"].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError("Past support source changed")
    return d
def rate_from_support(d,at):
    if d["window"]!=[1800,2400] or not d["cutoff_exclusive"] or at<2400:
        raise ValueError("Future or wrong support window")
    rates=[]
    for r in d["rows"]:
        if not r["eligible"]:continue
        p=r["prefix"]
        if len(p)<4 or len({x["vehicle"] for x in p})!=len(p):raise ValueError("Incomplete head prefix")
        if not all(x["vehicle"] in r["stable_prefix_queue"] and r["start"]<x["time"]<r["end"]<=2400 and x["turn"] in ("10241","10242") for x in p):
            raise ValueError("Unqualified route or timing")
        n=sum(x["turn"]=="10242" for x in p)
        if n<3 or n!=r["north_count"]:raise ValueError("Bad north count")
        value=3600*n/(p[-1]["time"]-r["start"])
        if abs(value-r["startup_inclusive_rate_veh_h"])>1e-9:raise ValueError("Wrong rate")
        rates.append(value)
    if not rates or not math.isclose(min(rates),d["selected_support"]["rate"]):raise ValueError("No qualified rate")
    return min(rates)
def install(cfg,at,d):
    rate=rate_from_support(d,at);n=cfg.network
    group=n.regular_alias_pool["groups"][west.GROUP]
    if set(group["members"])!=set(west.MEMBERS) or group["signal"]!="SC12" or group["phase"]!="SC12_p4" or group["receiver"]!="SC12_to_SC6":
        raise ValueError("Physical service binding changed")
    if group["service_veh_h"]!=960 or any(n.movement_capacity_by_movement_veh_h[k]!=960 for k in west.MEMBERS):
        raise ValueError("Expected previous typed lower-bound support")
    pool=deepcopy(n.regular_alias_pool);pool["groups"][west.GROUP]["service_veh_h"]=rate
    caps=dict(n.movement_capacity_by_movement_veh_h)
    for k in west.MEMBERS:caps[k]=rate
    n.regular_alias_pool=pool;n.movement_capacity_by_movement_veh_h=caps
    n.sc12_phase305=dict(previous_rate=960.,rate=rate,shared_members=list(west.MEMBERS),
        support_starts=d["selected_support"]["starts"],cutoff=2400,
        scope="North effective service includes startup and observed shared-through use; one historical queue, not a general lane scheduler.")
    return n.sc12_phase305
@contextmanager
def hook(option):
    from evaluation.controllers import regular_alias_service
    d=evidence()
    with hook_prior(option) as side:
        original=regular_alias_service.configure
        def configure(cfg,tuning,raw):
            base=original(cfg,tuning,raw)
            metadata=install(cfg,int(raw["sim_sec"]),d)
            return {**base,"diagnostic_sc12_phase305":metadata}
        regular_alias_service.configure=configure
        try:yield side
        finally:regular_alias_service.configure=original

