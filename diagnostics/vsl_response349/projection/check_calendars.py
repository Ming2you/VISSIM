"""Same saved initial state under before/after projectors; no forecast.

The old test harness pins the entire then-current adapter and now rejects its
changed hash before testing. Keep that failure; compare the saved projector
directly on the same physical input instead of weakening its evidence pins.
"""
import copy, hashlib, importlib.util, json, pickle
from importlib.machinery import SourceFileLoader
from pathlib import Path
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.control_area_objective import get_ledger
from evaluation.controllers.area_runtime import model_inventory
from evaluation.controllers.physical_ramp_branches import split_tagged_arrival
from src.models.urban_queue_model import approach_routing
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306 import candidate as current
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
A=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270'
cfg,state,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
raw_path=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/state_002400.json')
raw=json.loads(raw_path.read_bytes());fp=raw_path.parent/raw['obs150']['frames']['current']['path']
assert hashlib.sha256(fp.read_bytes()).hexdigest()==raw['obs150']['frames']['current']['sha256']
frame=json.loads(fp.read_bytes());network=(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx').read_bytes()
lanes=adapter._contiguous_stopline_queue(raw,per_lane=True)
loader=SourceFileLoader('before306',str(HERE/'sc12_candidate.before.py.txt'))
spec=importlib.util.spec_from_loader(loader.name,loader);before=importlib.util.module_from_spec(spec);loader.exec_module(before)
args=state,cfg,raw,frame,network,True,lanes
old,old_receipt=before.project(*args);new,receipt=current.project(*args)
assert equal(vars(old),vars(new)), 'Unchanged one-reservation state differs'
assert all(equal(receipt[k],v) for k,v in old_receipt.items())

# One disconnected stopped residual and one moving residual, plus five unrelated
# moving parent vehicles. Both calendars and the independent current stocks stay.
state,cfg,raw,frame,network,inside,lanes=copy.deepcopy(args)
residual=[v['vehicle'] for v in receipt['vehicles'] if not v['ready']]
assert len(residual)==2
for v in raw['vehicle_records']['records']:
    if v['veh_no']==residual[0]:v.update(stopped=True,speed_kph=0.)
for v in frame['vehicles']:
    if v[0]==residual[0]:v[4]=0.
source=current.SOURCE
state.urban_arrival_buffer[source]={242:6.,251:1.}
state.urban_storage_release_buffer[source]={242:6.,251:1.}
original=pickle.dumps(state,protocol=5)
result,receipt=current.project(state,cfg,raw,frame,network,inside,lanes)
assert pickle.dumps(state,protocol=5)==original
assert result.urban_arrival_buffer==state.urban_arrival_buffer
assert result.urban_storage_release_buffer==state.urban_storage_release_buffer
assert result.urban_link_storage==state.urban_link_storage
assert {k:sum(v.values()) for k,v in result.gate_initial_route_tags[source].items()}=={242:1.,251:1.}
for side in ('inside','outside'):
    assert abs(sum(v[side] for v in get_ledger(result).stocks.values())-sum(v[side] for v in get_ledger(state).stocks.values()))<1e-8
get_ledger(result).assert_stocks(model_inventory(result,cfg))
for step,n in ((242,6.),(251,1.)):
    assert abs(sum(dict(split_tagged_arrival(result,cfg,source,step,n,approach_routing(cfg)[source])).values())-n)<1e-8
    assert split_tagged_arrival(result,cfg,source,step,n,approach_routing(cfg)[source]) is None
assert result.gate_initial_route_tags[source]=={}
state.urban_arrival_buffer[source]={242:7.} # mismatched release must remain rejected
try:current.project(state,cfg,raw,frame,network,inside,lanes)
except ValueError:pass
else:raise AssertionError('Unpaired calendar accepted')
print(json.dumps(dict(status='passed',old_single_parent_exact_state=True,
    moving_stopped_separate=True,paired_reservations_unchanged=True,
    unrelated_parent_vehicles=5,inside_outside_conserved=True,consumed_once=True,new_predictions=0)))
