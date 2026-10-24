"""Current cohort coverage, without running an optimizer or a simulation."""
import copy
import xml.etree.ElementTree as ET
from types import SimpleNamespace as NS
from unittest.mock import patch
import pytest
from evaluation.controllers import calibrated_urban_runtime as runtime
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339 import project
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc105_initial340 import candidate as terminal


def raw_fixture():
    return dict(sim_sec=2250,vehicle_records=dict(complete=True,paused_at_sim_sec=2250,
        capture_sim_sec_before=2250,capture_sim_sec_after=2250,
        records=[dict(link_no=1210012600,lane_no=4,stopped=True),
                 dict(link_no=1210012600,lane_no=4,stopped=False)]),
        local_observation={'queue_bins':{'1210012600|4|1':[1,1],'1210012600|4|2':[1,0]}})


def test_complete_zero_does_not_become_all_stopped_and_existing_origins_remain():
    raw=raw_fixture();cfg=NS(network=NS(kinematic_queue_zero_links={'existing'}))
    runtime.configure_queue_projection(cfg,raw,{'enabled':True})
    assert cfg.network.kinematic_queue_zero_links=={'existing','1220012103','1210012600','173','174','10280','10281','10285','1220007200'}
    assert cfg.network.head_queue_upstream_storage=={'1210018202':'SC6_to_SC12'}
    with patch.object(adapter,'_link_lengths_m',return_value={}):
        legacy=adapter._contiguous_stopline_queue(raw)
        current=adapter._contiguous_stopline_queue(raw,zero_links=cfg.network.kinematic_queue_zero_links)
    assert '1210012600' not in legacy and current['1210012600']==0


@pytest.mark.parametrize('defect',['incomplete','time','count','lane'])
def test_zero_contract_requires_complete_current_lane_coverage(defect):
    raw=raw_fixture();cfg=NS(network=NS())
    if defect=='incomplete':raw['vehicle_records']['complete']=False
    if defect=='time':raw['vehicle_records']['capture_sim_sec_after']+=1
    if defect=='count':raw['local_observation']['queue_bins']['1210012600|4|2']=[2,0]
    if defect=='lane':raw['vehicle_records']['records'][0]['lane_no']=3
    with pytest.raises(ValueError):runtime.configure_queue_projection(cfg,raw,{})
    assert not hasattr(cfg.network,'kinematic_queue_zero_links')


def test_absent_recipe_keeps_projection_unchanged():
    cfg=NS(network=NS())
    assert runtime.configure_queue_projection(cfg,None,None)=={}
    assert not vars(cfg.network)


def geometry():
    root=ET.fromstring('''<net><signalHeads>
      <signalHead lane="173 1" sg="109 1" pos="25"/>
      <signalHead lane="173 4" sg="109 2" pos="26"/>
      </signalHeads><links>
      <link no="10285"><fromLinkEndPt lane="173 1" pos="29"/><lanes><lane/></lanes></link>
      <link no="10286"><fromLinkEndPt lane="173 4" pos="29"/><lanes><lane/></lanes></link>
      </links></net>''')
    return root,{n.get('no'):n for n in root.findall('./links/link')}


def test_post_head_geometry_covers_both_turns_with_lane_specific_heads():
    root,links=geometry()
    assert project.post_head_geometry(root,links)==({1:25.,4:26.},{'10285','10286'})
    links['10286'].find('fromLinkEndPt').set('pos','24')
    with pytest.raises(ValueError):project.post_head_geometry(root,links)


@pytest.mark.parametrize('connector',['10285','10286'])
def test_occupied_connector_preserves_observed_turn_without_inventing_route(connector):
    root,_=geometry();row=[1,int(connector),1,5,30,0,None,None,None,None]
    prior={k:.5 for k in project.routes.MOVEMENTS}
    weights,known,path=project.route_weights(row,{'link_no':int(connector)},root,prior,{})
    movement=next(m for m,c in project.routes.MOVEMENTS.items() if c==connector)
    assert weights=={movement:1.} and known and path is None


def test_connector_does_not_override_conflicting_known_route():
    root,_=geometry();row=[1,10286,1,5,30,0,1,1,'STATIC',2]
    wrong=next(m for m,c in project.routes.MOVEMENTS.items() if c=='10285')
    with patch.object(project.routes,'current_weights',return_value=({wrong:1.},True,['173','10285'])):
        with pytest.raises(ValueError):project.route_weights(row,{'link_no':10286},root,{}, {})


def test_zero_movement_keys_do_not_make_fractional_storage_a_ready_queue():
    source='storage:'+project.TARGET
    rows=[{'veh_no':i} for i in range(4)]
    support={source:2.,'storage:other':2.,'movement:empty':0.}
    with patch('evaluation.controllers.native_internal_input.record_partition',return_value=({},{})):
        cohort,rule=project.owned_residual(None,None,'10286',rows,support)
        assert sum(w for _,w in cohort)==2. and all(w==.5 for _,w in cohort)
        support['movement:empty']=1.
        with pytest.raises(ValueError):project.owned_residual(None,None,'10286',rows,support)
        support={source:.9999999999999993,'movement:existing':12.}
        cohort,rule=project.owned_residual(None,None,'173',rows[:1],support)
        assert rule=='whole_source' and abs(sum(w for _,w in cohort)-1)<1e-12
        support[source]=.9
        with pytest.raises(ValueError):project.owned_residual(None,None,'173',rows[:1],support)


def terminal_geometry():
    nodes=ET.fromstring('''<links>
      <link no="10659"><fromLinkEndPt lane="420 1"/><toLinkEndPt lane="1220007200 1"/><lanes><lane/><lane/></lanes></link>
      <link no="10660"><fromLinkEndPt lane="420 3"/><toLinkEndPt lane="1220007200 3"/><lanes><lane/></lanes></link>
      </links>''')
    links={n.get('no'):n for n in nodes}
    cfg=NS(network=NS(urban_movements={}))
    return links,terminal.path_catalog(cfg,links)


def test_parallel_connector_current_path_and_unknown_lane():
    links,paths=terminal_geometry()
    assert set(paths)=={'420','10659','10660','1220007200'}
    v={'link_no':420,'lane_no':3}
    assert terminal.choose_path(paths['420'],v,links)==['420','10660','1220007200']
    # Intent overrides lane only if the currently assigned path names the turn.
    assert terminal.choose_path(paths['420'],v,links,['420','10659'])==['420','10659','1220007200']
    assert terminal.choose_path(paths['420'],v,links,['420'])==['420','10660','1220007200']
    with pytest.raises(ValueError):terminal.choose_path(paths['420'],v,links,['420','unrelated'])


def test_intermediate_storage_does_not_overwrite_another_owner():
    cfg=NS(network=NS(head_queue_upstream_storage={'1210018202':'other'}))
    with pytest.raises(ValueError):runtime.configure_queue_projection(cfg,raw_fixture(),{})
    assert cfg.network.head_queue_upstream_storage=={'1210018202':'other'}


def test_cohort_replacement_keeps_other_stock_and_rejects_material_shortfall():
    assert terminal.replace_cohort(2.,.5,1.)==2.5
    assert terminal.replace_cohort(2.-4.44e-16,2.,0.)==0.
    with pytest.raises(ValueError):terminal.replace_cohort(1.9,2.,0.)
