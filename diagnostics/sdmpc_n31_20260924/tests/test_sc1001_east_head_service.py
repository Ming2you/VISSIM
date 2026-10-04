"""Two29/p3 heads belong once to10119, not to every SC1001 movement."""
import ast
import copy
import json
from pathlib import Path
import pytest
from evaluation.controllers import head_service_resources as service
from test_sc109_head_service import fixture as prior_fixture

HERE=Path(__file__).resolve().parents[1]/'integration_20260926/sc1001_sources_20260929'
NAME='SC1001_E_SC1002_to_W_RAMP'


def fixture():
    cfg,tuning,raw,plan=prior_fixture()
    contract=json.loads((HERE/'head_resources.json').read_bytes())
    cfg.network.urban_movements[NAME]=dict(contract['resources']['10119']['members'][NAME],beta=.5636)
    cfg.network.movement_capacity_by_movement_veh_h[NAME]=413.0612244897959
    for name,detail in contract['resources']['10119'].get('disjoint_consumers',{}).items():
        cfg.network.urban_movements[name]=dict(detail['expected_spec'],beta=.36)
        cfg.network.movement_capacity_by_movement_veh_h[name]=206.53
    plan['controllers']['1001']['phase_signal_groups']['p3']=['6']
    tuning['urban']['capacity']['head_resource_contract']=str(HERE/'head_resources.json')
    return cfg,tuning,raw,plan


def test_verified_two_lane_service_is_consumed_only_once():
    cfg,tuning,raw,plan=fixture()
    before=copy.deepcopy(cfg.network.movement_capacity_by_movement_veh_h)
    service.configure(cfg,tuning,raw,plan)
    spec=service.view(cfg);spec['resources']={'10119':spec['resources']['10119']}
    assert [h['lane'] for h in spec['resources']['10119']['heads']]==[2,3]
    spec['observations']={'10119':{'observed_only_floor_veh_h':960.}}
    service.finalize(cfg)
    before[NAME]=960.
    assert cfg.network.movement_capacity_by_movement_veh_h==before
    assert spec['extra_pool_groups']=={}


@pytest.mark.parametrize('bad',['competitor','phase','receiver','lane','source','prior_route'])
def test_wrong_or_shared_physical_evidence_is_rejected(tmp_path,bad):
    cfg,tuning,raw,plan=fixture()
    doc=json.loads((HERE/'head_resources.json').read_bytes());row=doc['resources']['10119']
    if bad=='competitor':cfg.network.urban_movements['alias']=dict(cfg.network.urban_movements[NAME])
    elif bad=='phase':row['members'][NAME]['phase']='SC1001_p2'
    elif bad=='receiver':row['receiver']='SC1004_W_out'
    elif bad=='lane':row['heads'][0]['lane']=1
    elif bad=='source':row['group']='40|p3'
    else:row['proof']['sha256']='0'*64
    path=tmp_path/'invalid.json';path.write_text(json.dumps(doc));tuning['urban']['capacity']['head_resource_contract']=str(path)
    with pytest.raises(ValueError):service.configure(cfg,tuning,raw,plan)


def test_existing_v5_configuration_is_exact_to_archived_function():
    cfg,tuning,raw,plan=prior_fixture();other=copy.deepcopy(cfg)
    module=ast.parse((HERE/'head_service_resources.before.py').read_text(encoding='utf-8'))
    node=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='configure')
    namespace=dict(vars(service));exec(compile(ast.Module(body=[node],type_ignores=[]),'<archived-v5>','exec'),namespace)
    before=namespace['configure'](other,tuning,raw,plan)
    after=service.configure(cfg,tuning,raw,plan)
    assert before==after
    assert vars(cfg.network)==vars(other.network)


def test_opt_out_removes_our_v6_view():
    cfg,tuning,raw,plan=fixture();service.configure(cfg,tuning,raw,plan)
    tuning['urban']['capacity'].pop('head_resource_contract')
    assert service.configure(cfg,tuning,raw,plan)=={}
    assert service.view(cfg) is None


@pytest.mark.parametrize('bad',['missing','route','receiver','overlapping_path'])
def test_same_phase_other_lane_requires_complete_physical_proof(tmp_path,bad):
    cfg,tuning,raw,plan=fixture()
    doc=json.loads((HERE/'head_resources.json').read_bytes());row=doc['resources']['10119']
    detail=next(iter(row['disjoint_consumers'].values()))
    if bad=='missing':row.pop('disjoint_consumers')
    elif bad=='route':detail['native_route']='1118:2'
    elif bad=='receiver':detail['expected_spec']['receiving_link']='SC1001_W_out'
    else:detail['path']=['29','10119','31']
    path=tmp_path/'bad_exclusion.json';path.write_text(json.dumps(doc));tuning['urban']['capacity']['head_resource_contract']=str(path)
    with pytest.raises(ValueError):service.configure(cfg,tuning,raw,plan)
