"""Offline source route tags: metadata within existing aggregate arrival stock."""
from contextlib import contextmanager
import hashlib,json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc101_peeloff302 import candidate as prior

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
TARGET="SC1_to_SC101"
ATTR="_sc101_route_tags303"
CATEGORIES=("straight","right","left","unresolved")
validate_turns,west,east=prior.validate_turns,prior.west,prior.east
MOV=prior.MOV


def document():
    d=json.loads((HERE/"support.json").read_bytes())
    if d["schema"]!="aggregate-source-route-support303/v1":raise ValueError("Wrong route tag support")
    for p,h in d["source_pins"].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError("Route support source changed")
    return d


def validate(cfg,cutoff,d):
    if d["route_followup_end"]>=cutoff or d["fit_window"][1]>=cutoff:
        raise ValueError("Route support must precede prediction")
    if set(d["sources"])!={"1099","1100"} or d["receiver"]!=TARGET:
        raise ValueError("Unsupported source or receiver")
    specs={m:s for m,s in cfg.network.urban_movements.items() if s.get("origin")==TARGET}
    if set(specs)!=set(d["movements"].values()):raise ValueError("Movement catalog differs")
    for kind,m in d["movements"].items():
        if specs[m]["beta"]!=d["base_beta"][kind]:raise ValueError("Base turning prior differs")
    for r in d["sources"].values():
        w=r["category_shares"]
        if set(w)!=set(CATEGORIES) or min(w.values())<0 or abs(sum(w.values())-1)>1e-12:
            raise ValueError("Invalid route category shares")


def add_tag(state,decision,due,amount,d):
    if type(due) is not int or due<0 or amount<0:raise ValueError("Invalid tagged receipt")
    weights=d["sources"][decision]["category_shares"]
    values={};allocated=0
    for kind in CATEGORIES[:-1]:
        values[kind]=amount*weights[kind];allocated+=values[kind]
    values["unresolved"]=amount-allocated
    if values["unresolved"] < -1e-8:raise ValueError("Negative unresolved tagged mass")
    # Categories are a label on this SAME parent amount, not another stock.
    tags=getattr(state,ATTR,None)
    if tags is None:
        tags=dict(pending={},scheduled={k:0. for k in CATEGORIES},matured={k:0. for k in CATEGORIES},receipts=0)
        setattr(state,ATTR,tags)
    entry=tags["pending"].setdefault(due,{}).setdefault(decision,{k:0. for k in CATEGORIES})
    for kind,n in values.items():entry[kind]+=n;tags["scheduled"][kind]+=n
    tags["receipts"]+=1


def verify_pending(state):
    tags=getattr(state,ATTR,None)
    if tags is None:return
    pending={k:0. for k in CATEGORIES}
    parent=state.urban_arrival_buffer.get(TARGET,{})
    for due,sources in tags["pending"].items():
        amount=sum(n for row in sources.values() for n in row.values())
        if amount>parent.get(due,0)+1e-8:raise ValueError("Route tags exceed parent arrival buffer")
        for row in sources.values():
            for kind,n in row.items():
                if n < -1e-8:raise ValueError("Negative route tag")
                pending[kind]+=n
    for kind in CATEGORIES:
        if abs(tags["scheduled"][kind]-tags["matured"][kind]-pending[kind])>1e-7:
            raise ValueError("Route tag scheduled/matured conservation failed")


def split(state,cfg,source,step,arrived,routing,d,original):
    tags=getattr(state,ATTR,None)
    if source!=TARGET or tags is None or step not in tags["pending"]:
        return original(state,cfg,source,step,arrived,routing)
    category={k:sum(row[k] for row in tags["pending"][step].values()) for k in CATEGORIES}
    tagged=sum(category.values())
    if tagged>arrived+1e-8 or tagged<0:raise ValueError("Tags exceed arriving parent amount")
    weights=dict(routing)
    if set(weights)!=set(d["movements"].values()) or abs(sum(weights.values())-1)>1e-10:
        raise ValueError("Runtime route catalog differs")
    remaining=max(0.,arrived-tagged)
    # Let existing initial route labels keep ownership of the unmodified remainder.
    base=original(state,cfg,source,step,remaining,routing)
    values=dict(base) if base is not None else {m:beta*remaining for m,beta in routing}
    for kind,m in d["movements"].items():values[m]+=category[kind]
    allocated=0
    for i,(m,beta) in enumerate(routing):
        n=category["unresolved"]-allocated if i==len(routing)-1 else category["unresolved"]*beta
        values[m]+=n;allocated+=n
    if min(values.values()) < -1e-8 or abs(sum(values.values())-arrived)>1e-7:
        raise ValueError("Source-specific arrival split lost vehicles")
    tags["pending"].pop(step)
    for k,n in category.items():tags["matured"][k]+=n
    return list(values.items())


@contextmanager
def hook(option):
    from evaluation.controllers.aggregate_route_corridors import Routes
    from evaluation.controllers import physical_ramp_branches as prb
    from src.models import urban_queue_model as uqm
    support=document()
    with prior.hook(option) as side:
        original_advance=Routes.advance_one
        original_schedule=uqm._schedule
        original_split=prb.split_tagged_arrival
        active=None
        def advance(self,state,control,cfg,step,spec):
            nonlocal active
            if active is not None:raise RuntimeError("Nested source tag context")
            if spec["decision"] in support["sources"]:
                validate(cfg,state.time_sec,support)
                active=(state,spec["decision"])
            try:
                result=original_advance(self,state,control,cfg,step,spec)
                verify_pending(state)
                return result
            finally:active=None
        def schedule(buffer,key,due,n):
            original_schedule(buffer,key,due,n)
            if active is not None and key==TARGET and buffer is active[0].urban_arrival_buffer and n>0:
                add_tag(active[0],active[1],due,n,support)
        def tagged(state,cfg,source,step,arrived,routing):
            return split(state,cfg,source,step,arrived,routing,support,original_split)
        Routes.advance_one=advance
        uqm._schedule=schedule
        prb.split_tagged_arrival=tagged
        try:yield side
        finally:
            Routes.advance_one=original_advance
            uqm._schedule=original_schedule
            prb.split_tagged_arrival=original_split

