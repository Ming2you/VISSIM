from unittest.mock import patch
import copy
import pytest
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as gate


def fixture():
    rows=[dict(veh_no=15380,link_no=10201,lane_no=1,position_m=32.44,speed_kph=39.78,stopped=False),
          dict(veh_no=15912,link_no=10201,lane_no=1,position_m=14.36,speed_kph=38.14,stopped=False)]
    return dict(vehicle_records=dict(records=rows)),{'10201':{'storage:SC104_to_SC6':1.,'storage:'+gate.TARGET:1.}}


def test_existing_shared_stock_and_other_owner_preserved():
    raw,prov=fixture();before=copy.deepcopy((raw,prov))
    with patch('evaluation.controllers.native_internal_input.record_partition',return_value=({},{})):
        rows,w,e=gate.current_owned_stock(None,raw,{'10201'},prov)
    assert set(w)=={15380,15912} and sum(w.values())==1. and set(w.values())=={.5}
    assert e['10201']['other_owners']=={'storage:SC104_to_SC6':1.}
    assert (raw,prov)==before


def test_native_head_partition_beats_fractional_attribution():
    raw,prov=fixture()
    authority=dict(pre_head_storage='SC104_to_SC6',post_head_storage=gate.TARGET,head_position_by_lane_m={'1':20.})
    with patch('evaluation.controllers.native_internal_input.record_partition',return_value=({'10201':{}},{'10201':{'input_no':'x'}})),patch('evaluation.controllers.native_internal_input._signal_authority',return_value=(None,authority)):
        rows,w,e=gate.current_owned_stock(None,raw,{'10201'},prov)
    assert w=={15380:1.} and e['10201']['rule']=='exact_current_native_head_partition'


@pytest.mark.parametrize('defect',['missing_vehicle','negative_stock','ambiguous_ready'])
def test_bad_shared_attribution_is_not_silently_accepted(defect):
    raw,prov=fixture()
    if defect=='missing_vehicle':raw['vehicle_records']['records'].pop()
    if defect=='negative_stock':prov['10201']={'storage:'+gate.TARGET:3.,'storage:other':-1.}
    if defect=='ambiguous_ready':prov['10201']={'storage:'+gate.TARGET:1.,'movement:other':1.}
    with patch('evaluation.controllers.native_internal_input.record_partition',return_value=({},{})):
        with pytest.raises(ValueError):gate.current_owned_stock(None,raw,{'10201'},prov)


def test_whole_source_ready_owner_is_unchanged():
    raw,prov=fixture();m=next(iter(gate.MOVS));prov['10201']={'storage:'+gate.TARGET:1.,'movement:'+m:1.}
    with patch('evaluation.controllers.native_internal_input.record_partition',return_value=({},{})):
        rows,w,e=gate.current_owned_stock(None,raw,{'10201'},prov)
    assert w=={15380:1.,15912:1.} and e['10201']['rule']=='whole_source'
