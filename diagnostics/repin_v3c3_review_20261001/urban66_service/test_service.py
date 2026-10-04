"""Native unique straight head, excluding the earlier same-lane right branch."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from evaluation.controllers import head_service_resources as service

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
NAME='SC1004_S_to_N_SC1003'
RIGHT='SC1004_S_to_E_SC1005'


def fixture():
    doc=json.loads((HERE/'head_resources.json').read_bytes())
    moves={}; plan={'controllers':{}}
    for row in doc['resources'].values():
        moves.update({m:dict(s,beta=.5) for m,s in row['members'].items()})
        moves.update({m:dict(s['expected_spec'],beta=.5) for m,s in row.get('disjoint_consumers',{}).items()})
        for h in row['heads']:
            plan['controllers'].setdefault(h['sc'],{'phase_signal_groups':{}})['phase_signal_groups'][row['group'].split('|')[1]]=[h['sg']]
    cfg=NS(network=NS(urban_movements=moves,
        urban_link_storage_veh={row['receiver']:100. for row in doc['resources'].values()},
        movement_capacity_by_movement_veh_h={m:620. for m in moves}))
    tuning={'urban':{'shared_local_service_pool':True,'capacity':{'head_observation':{'enabled':True},
        'head_resource_contract':str(HERE/'head_resources.json')}}}
    detail=doc['resources']['10631']['disjoint_consumers'][RIGHT]
    tuning['urban']['route_choice_corridor']={'evidence_paths':[detail['downstream_choice']['path']]}
    moves['SC1004_S_to_E_SC107']=dict(moves[RIGHT],receiving_link='SC1004_to_SC107')
    cfg.network.movement_capacity_by_movement_veh_h['SC1004_S_to_E_SC107']=620.
    return cfg,tuning,{'network_path':str(ROOT/doc['network']['path'])},plan,doc


def test_native_prehead_right_is_excluded_and_straight_has_one_budget():
    cfg,tuning,raw,plan,_=fixture()
    service.configure(cfg,tuning,raw,plan)
    spec=cfg.network.head_service_resources
    spec['resources']={'10631':spec['resources']['10631']}
    spec['observations']={'10631':{'observed_only_floor_veh_h':1700.}}
    before=copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
    service.finalize(cfg)
    before[NAME]=1700.
    assert cfg.network.movement_capacity_by_movement_veh_h==before
    assert cfg.network.movement_capacity_by_movement_veh_h[RIGHT]==620.
    assert spec['extra_pool_groups']=={}


@pytest.mark.parametrize('bad',['unproven_prehead','bad_target','wrong_head','wrong_member','missing_exclusion','wrong_receiver'])
def test_wrong_physical_join_cannot_raise_capacity(tmp_path,bad):
    cfg,tuning,raw,plan,doc=fixture(); row=doc['resources']['10631']
    if bad=='unproven_prehead':row['disjoint_consumers'][RIGHT].pop('upstream_of_head')
    elif bad=='bad_target':row['target_link']='56'
    elif bad=='wrong_head':row['heads'][0]['lane']=4
    elif bad=='wrong_member':row['members'][NAME]['kind']='internal'
    elif bad=='missing_exclusion':row.pop('disjoint_consumers')
    elif bad=='wrong_receiver':row['disjoint_consumers'][RIGHT]['expected_spec']['receiving_link']='SC1004_E_choice'
    path=tmp_path/'bad.json';path.write_text(json.dumps(doc))
    tuning['urban']['capacity']['head_resource_contract']=str(path)
    with pytest.raises(ValueError):service.configure(cfg,tuning,raw,plan)


def test_extra_posthead_model_consumer_is_rejected():
    cfg,tuning,raw,plan,_=fixture()
    cfg.network.urban_movements['phantom']=dict(cfg.network.urban_movements[NAME])
    with pytest.raises(ValueError,match='another model consumer'):
        service.configure(cfg,tuning,raw,plan)


def test_downstream_alias_needs_its_configured_owner():
    cfg,tuning,raw,plan,_=fixture()
    tuning['urban']['route_choice_corridor']['evidence_paths']=[]
    with pytest.raises(ValueError,match='configured corridor proof'):
        service.configure(cfg,tuning,raw,plan)
