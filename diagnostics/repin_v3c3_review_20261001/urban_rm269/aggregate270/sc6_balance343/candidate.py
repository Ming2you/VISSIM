"""One causal diagnostic: repair attribution of a measured through-head rate.

No right-turn service or initial state is changed. This isolates the mapping
error; retaining the old right rate does not qualify that rate as measured.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json,math,pickle
from evaluation.controllers import head_service_resources as resources
HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
THROUGH='SC6_E_SC104_to_W_SC5';RIGHT='SC6_E_SC104_to_N_SC103'
GROUP='1220021201_p3_'

def support(documents,cutoff,run_id):
    """Recover a completed consecutive-window pair, never a seed/future floor."""
    previous=None;best=0.;evidence=[]
    for doc in documents:
        meta={**doc.get('diagnostics',{}),**doc.get('metadata',{})}
        now=float(doc['metadata']['sim_sec'])
        if now>cutoff or doc['run_provenance']['run_id']!=run_id:
            raise ValueError('SC6 observed rate has a future or foreign source')
        keys=[k for k in meta if k.startswith('head_candidate_rate_'+GROUP)]
        provenance=[k for k,v in meta.items() if k.startswith('head_provenance_') and v==1.]
        if len(keys)>1 or len(provenance)!=1 or meta.get('head_observation_prior_discarded')!=0.:
            raise ValueError('SC6 observed rate lacks its original head provenance')
        if previous and now<=previous[0]:raise ValueError('SC6 observation time is not increasing')
        current=None
        if keys:
            key=keys[0];rate=float(meta[key])
            if not math.isfinite(rate) or rate<=0 or meta[key.replace('rate_','end_')]!=now:
                raise ValueError('Invalid SC6 observed head candidate')
            current=(now,key,rate,provenance[0])
            if previous and now-previous[0]==150. and previous[1:2]==current[1:2] and previous[3]==current[3]:
                value=min(previous[2],rate);best=max(best,value)
                evidence.append(dict(start=previous[0],end=now,rate=value))
        previous=current
    if best<=0:raise ValueError('No completed consecutive SC6 head-rate pair')
    return best,evidence

def install(cfg,raw,plan,folder,cutoff):
    before=deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
    # configure() runs before corridor aliases are joined. A finished model
    # cannot be passed back through that earlier lifecycle unchanged.
    probe,tuning,fixture_raw,_=pickle.loads((HERE/'configure_fixture/fixture.pickle').read_bytes())
    if fixture_raw['run_provenance']['run_id']!=raw['run_provenance']['run_id']:
        raise ValueError('Contract fixture comes from another native run')
    for m in (THROUGH,RIGHT):
        if probe.network.urban_movements[m]!=cfg.network.urban_movements[m]:
            raise ValueError('SC6 movement semantics changed after contract installation')
    tuning['urban']['capacity']['head_resource_contract']=(HERE/'head_resources.json').relative_to(ROOT).as_posix()
    resources.configure(probe,tuning,raw,plan)  # all geometry/path/receiver proofs
    pins={};docs=[]
    for at in range(900,int(cutoff)+1,150):
        path=Path(folder)/f'action_{at:06}.json';blob=path.read_bytes()
        pins[str(path)]=hashlib.sha256(blob).hexdigest();docs.append(json.loads(blob))
    rate,pairs=support(docs,cutoff,raw['run_provenance']['run_id'])
    # Check that this is exactly the same support previously beta-split.
    prior_total=before[THROUGH]+before[RIGHT]
    if abs(prior_total-rate)>1e-7:raise ValueError('Saved SC6 split differs from recovered physical support')
    cfg.network.movement_capacity_by_movement_veh_h={**before,THROUGH:rate}
    assert all(v==cfg.network.movement_capacity_by_movement_veh_h[k] for k,v in before.items() if k!=THROUGH)
    return dict(old_through=before[THROUGH],new_through=rate,right_unchanged=before[RIGHT],
        physical_pair_support=pairs,cutoff_sec=cutoff,source_pins=pins,
        full_online_observer_replay=False,production_adopted=False)
