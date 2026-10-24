import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest

from evaluation.controllers import urban_storage_guard as guard


def coord(weights, limit=10., cap=None):
    # Two phases exchange green, fixed cycle. One non-green axis must stay out.
    data = dict(signals={'SC1':weights}, policy={'reserve_green_sec':2.})
    return NS(cfg=NS(network=NS(urban_storage_guard=data)),
        axes=[dict(owner='SC1',kind='green',scale=150.),dict(owner='SC1',kind='offset',scale=150.)],
        green_vectors={0:{'p1':1.,'p2':-1.}},
        lower=np.array([-limit/150.,-10/150.]),upper=np.array([limit/150.,10/150.]),
        G=np.array([[150.,0.],[-150.,0.]]),glo=np.array([-limit,-limit]),
        ghi=np.array([limit if cap is None else cap,limit]))


def test_crowded_lane_requires_legal_progress_without_adding_cycle_time():
    c=coord({'SC1_p1':1.,'SC1_p2':0.});guard.constrain(c)
    assert c.urban_storage_receipt[0]['required_pressure_sec']==2
    assert c.G[-1].tolist()==[150.,0.]
    assert c.glo[-1]==2
    assert c.urban_storage_receipt[0]['attainable_pressure_sec']==10


def test_full_receiver_prevents_increasing_its_green():
    c=coord({'SC1_p1':-1.,'SC1_p2':0.});guard.constrain(c)
    assert c.G[-1,0]<0 and c.glo[-1]>0


def test_equal_competing_full_phases_cannot_both_get_extra_cycle():
    c=coord({'SC1_p1':1.,'SC1_p2':1.});guard.constrain(c)
    assert len(c.G)==2
    assert c.urban_storage_receipt[0]['status']=='no_green_redistribution_direction'


def test_small_remaining_trust_or_max_green_room_is_not_infeasible():
    c=coord({'SC1_p1':1.},cap=.4);guard.constrain(c)
    assert c.glo[-1]==pytest.approx(.2)
    c=coord({'SC1_p1':1.},cap=0);guard.constrain(c)
    assert len(c.G)==2 and c.urban_storage_receipt[0]['status']=='no_attainable_reserve_progress'


def test_disabled_and_untriggered_are_identical():
    for data in (None,dict(signals={'SC1':{'SC1_p1':0.}},policy={'reserve_green_sec':2.})):
        c=coord({});c.cfg.network.urban_storage_guard=data;before=copy.deepcopy(c.G)
        guard.constrain(c);assert np.array_equal(c.G,before)


def test_actual_lane_geometry_excludes_posthead_and_sees_full_receiver(tmp_path):
    xml='''<network><links><link no="1"><lanes><lane/><lane/></lanes><geometry><linkPolyPts>
    <linkPolyPoint x="0" y="0"/><linkPolyPoint x="50" y="0"/></linkPolyPts></geometry></link>
    <link no="2"><lanes><lane/><lane/></lanes><geometry><linkPolyPts>
    <linkPolyPoint x="0" y="0"/><linkPolyPoint x="60" y="0"/></linkPolyPts></geometry></link>
    <link no="10"><lanes><lane/><lane/></lanes><fromLinkEndPt lane="1 1" pos="45"/>
    <toLinkEndPt lane="2 1" pos="0"/></link></links><signalHeads>
    <signalHead no="1" lane="1 1" pos="44" sg="1 1" allVehTypes="true"/>
    <signalHead no="2" lane="1 2" pos="44" sg="1 1" allVehTypes="true"/>
    </signalHeads></network>'''
    path=tmp_path/'net.inpx';path.write_text(xml)
    plan={'controllers':{'1':{'phase_signal_groups':{'p1':[1]}}}}
    cfg=NS(network=NS(signals=['SC1'],urban_avg_vehicle_length_m=6.,signal_live_phases=lambda _:['p1']))
    policy={'urban':{'storage_release_guard':{'enabled':True,'trigger_fraction':.9,'reserve_green_sec':2}}}
    def snapshot(full):
        rows=[dict(veh_no=i,link_no=1,lane_no=1,position_m=p,speed_kph=0.) for i,p in enumerate([*range(0,43,6),49])]
        if full:rows += [dict(veh_no=100+i,link_no=2,lane_no=1,position_m=6*i,speed_kph=0.) for i in range(10)]
        return {'sim_sec':900,'network_path':str(path),'vehicle_records':dict(complete=True,
            records=rows,collection_count_before=len(rows),collection_count_after=len(rows),record_count=len(rows),
            capture_sim_sec_before=900,capture_sim_sec_after=900,full_network_link_counts={'1':len(rows)-(10 if full else 0),'2':10 if full else 0})}
    raw=snapshot(True);before=copy.deepcopy(raw)
    guard.configure(cfg,policy,raw,plan);lanes=cfg.network.urban_storage_guard['lanes']
    assert raw==before and lanes[0]['vehicles']==8 and lanes[1]['vehicles']==0
    assert lanes[0]['all_receivers_full'] and lanes[0]['pressure']==-1
    guard.configure(cfg,policy,snapshot(False),plan)
    assert cfg.network.urban_storage_guard['lanes'][0]['pressure']>0
    raw['vehicle_records']['complete']=False
    with pytest.raises(ValueError,match='complete vehicle snapshot'):guard.configure(cfg,policy,raw,plan)


def test_next_scenario_keeps_old_support_and_adds_verified_40_turns():
    root=Path(__file__).resolve().parents[1]
    before=json.loads((root/'diagnostics/repin_v3c3_review_20261001/urban257/min_green2/config.json').read_bytes())
    after=json.loads((root/'diagnostics/repin_v3c3_review_20261001/urban260/config.json').read_bytes())
    a=json.loads((root/before['urban']['queue']['head_lane_contract']).read_bytes())
    b=json.loads((root/after['urban']['queue']['head_lane_contract']).read_bytes())
    assert all(b['movements'][k]==v for k,v in a['movements'].items())
    extra={k:v for k,v in b['movements'].items() if k not in a['movements']}
    assert len(extra)==3
    assert extra['SC1001_S_SC1003_to_W_RAMP']['lanes']==[4]
    assert extra['SC1001_S_SC1003_to_W_RAMP']['connector']=='10698'
    after['urban'].pop('storage_release_guard')
    after['urban']['queue']['head_lane_contract']=before['urban']['queue']['head_lane_contract']
    assert after==before
