"""Native66 lane4/SG3 joins one existing boundary-in turn, with no pool duplication."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from evaluation.controllers import head_service_resources as service

ROOT=Path(__file__).resolve().parents[3]
CONTRACT=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/head_service_resource_10633.json'


def fixture():
    doc=json.loads(CONTRACT.read_bytes());row=doc['resources']['10633']
    movement=copy.deepcopy(row['members']['SC1004_S_to_W']);movement['beta']=.27
    cfg=NS(network=NS(urban_movements={'SC1004_S_to_W':movement},
        urban_link_storage_veh={'SC1004_W_out':100.},
        movement_capacity_by_movement_veh_h={'SC1004_S_to_W':206.,'unrelated':999.}))
    tuning={'urban':{'shared_local_service_pool':True,'capacity':{
        'head_observation':{'enabled':True},'head_resource_contract':str(CONTRACT)}}}
    raw={'network_path':str(ROOT/doc['network']['path'])}
    plan={'controllers':{'1004':{'phase_signal_groups':{'p2':['3'],'p3':['6']}},
                         '107':{'phase_signal_groups':{'p3':['6']}}}}
    return cfg,tuning,raw,plan


def test_native_contract_accepts_boundary_turn_and_one_service_only():
    cfg,tuning,raw,plan=fixture()
    service.configure(cfg,tuning,raw,plan)
    doc=cfg.network.head_service_resources
    doc['resources']={'10633':doc['resources']['10633']}
    doc['observations']={'10633':{'observed_only_floor_veh_h':1330.}}
    result=service.finalize(cfg)
    assert result['head_resource_final_rate_10633']==1330.
    assert cfg.network.movement_capacity_by_movement_veh_h=={'SC1004_S_to_W':1330.,'unrelated':999.}
    assert doc['extra_pool_groups']=={}  # no parallel second service


def test_new_competing_model_turn_is_rejected():
    cfg,tuning,raw,plan=fixture()
    cfg.network.urban_movements['phantom']=dict(cfg.network.urban_movements['SC1004_S_to_W'])
    with pytest.raises(ValueError,match='another model consumer'):service.configure(cfg,tuning,raw,plan)


@pytest.mark.parametrize('bad',['head_lane','target','member','group'])
def test_mismatched_native_resource_cannot_raise_service(tmp_path,bad):
    cfg,tuning,raw,plan=fixture();doc=json.loads(CONTRACT.read_bytes());row=doc['resources']['10633']
    if bad=='head_lane':row['heads'][0]['lane']=3
    if bad=='target':row['target_link']='67'
    if bad=='member':row['members']['SC1004_S_to_W']['phase']='SC1004_p1'
    if bad=='group':row['group']='66|p1'
    p=tmp_path/'changed_contract.json';p.write_text(json.dumps(doc))
    tuning['urban']['capacity']['head_resource_contract']=str(p)
    with pytest.raises(ValueError):service.configure(cfg,tuning,raw,plan)
