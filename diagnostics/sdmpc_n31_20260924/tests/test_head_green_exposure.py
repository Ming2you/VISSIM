"""Short signal greens retain measured exposure; empty demand is not saturation."""
import copy
import json
from pathlib import Path

import pytest
from evaluation.controllers import signal_head_observation as observed
from diagnostics.test_signal_observation_window_patch import InstalledConsumerTests, OPTIONS, save_previous


def window(start,green,count):
    return dict(start=start,end=start+150,green=[green],qualified=[count])


def test_two_disjoint_exposure_blocks_use_all_seconds_and_no_future():
    history=[]
    for i,n in enumerate((5,12,11,12)):
        history,support=observed.pooled_green_support(history,window(300+150*i,23,n),4,OPTIONS)
        if i<3:assert support==0.
    assert support==pytest.approx(3600*17/46)
    # Low/zero demand observations remain in denominators and numerators.
    empty=[]
    for i,n in enumerate((0,12,0,12)):
        empty,support=observed.pooled_green_support(empty,window(300+150*i,23,n),4,OPTIONS)
    assert support==pytest.approx(3600*12/46)
    h,support=observed.pooled_green_support(history,window(1200,23,12),4,OPTIONS)
    assert h==[window(1200,23,12)] and support==0.
    with pytest.raises(ValueError,match='overlaps'):
        observed.pooled_green_support(history,window(800,23,12),4,OPTIONS)


@pytest.mark.parametrize('bad', [dict(green=[-1]),dict(green=[151]),dict(green=[0],qualified=[1]),
                               dict(qualified=[True]),dict(qualified=[1.5]),dict(qualified=[1,2])])
def test_impossible_evidence_fails(bad):
    row=window(0,23,5);row.update(bad)
    with pytest.raises(ValueError):observed.pooled_green_support([],row,4,OPTIONS)


def test_installed_observer_carries_only_provenanced_causal_history(tmp_path):
    cfg,raw,plan,distribute=InstalledConsumerTests().fixture(tmp_path,green=23,count=5,start=300,end=450)
    observed.configure_green_exposure_pool(cfg,dict(head_observation=OPTIONS,head_green_exposure_windows=4))
    prior=tmp_path/'observation_prior.json'
    untouched=copy.deepcopy(raw)
    for i,count in enumerate((5,12,11,12)):
        raw['sim_sec']=450+i*150
        w=raw['local_observation']['signal_observation_window']
        w.update(start_sec=raw['sim_sec']-150,end_sec=raw['sim_sec'])
        w['heads'][0].update(crossings=count,qualified_crossings=count)
        meta=observed.install(cfg,raw,prior if prior.exists() else None,{'through':200.},plan,distribute,OPTIONS)
        save_previous(prior,meta)
        if i<3:assert cfg.network.movement_capacity_by_movement_veh_h['through']==200.
    assert cfg.network.movement_capacity_by_movement_veh_h['through']==pytest.approx(3600*17/46)
    assert untouched['local_observation']['signal_observation_window']['heads'][0]['green_sec']==23
    assert not any(k.startswith('head_discharge_floor_') for k in meta)
    raw['sim_sec']=1050;raw['local_observation']={}
    cfg.network.movement_capacity_by_movement_veh_h={'through':200.}
    off=copy.deepcopy(cfg);observed.configure_green_exposure_pool(off,dict(head_observation=OPTIONS))
    observed.install(off,raw,prior,{'through':200.},plan,distribute,OPTIONS)
    assert off.network.movement_capacity_by_movement_veh_h['through']==200.
    doc=json.loads(prior.read_text());doc['run_provenance']['run_id']='foreign';prior.write_text(json.dumps(doc))
    invalid=observed.install(cfg,raw,prior,{'through':200.},plan,distribute,OPTIONS)
    assert invalid['head_observation_prior_discarded']==1.
    assert cfg.network.movement_capacity_by_movement_veh_h['through']==200.


@pytest.mark.parametrize('bad',[True,1,2,3,5,10,'4'])
def test_invalid_pool_configuration_rejected(tmp_path,bad):
    cfg,*_=InstalledConsumerTests().fixture(tmp_path)
    with pytest.raises(ValueError):
        observed.configure_green_exposure_pool(cfg,dict(head_observation=OPTIONS,head_green_exposure_windows=bad))
