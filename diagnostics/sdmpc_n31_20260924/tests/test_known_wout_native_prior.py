"""Future branch priors must match the selected network without rerouting stock."""
from pathlib import Path
from types import SimpleNamespace as NS
import copy
import json
import xml.etree.ElementTree as ET

import pytest
from evaluation.controllers import route_choice_corridor as route

SELECTED=Path(__file__).resolve().parents[1]/'integration_20260926/selected'
NAMES={'R_F_W':'RM_C10646','R_F_E':'RM_C10681'}


def inputs():
    tree=ET.parse(SELECTED/'network/native_seed29.inpx').getroot()
    proof=json.loads((SELECTED/'scenario/known_wout_routes_ver2_proposal_a424b4.json').read_bytes())
    return tree,proof


def test_native_prior_comes_from_current_route_weights():
    tree,proof=inputs()
    weights,evidence=route._known_native_choice_prior(tree,proof,NAMES)
    assert weights=={'RM_C10646':.2,'free':.2,'RM_C10681':.6}
    assert evidence['1135:2']['weight']==1.
    assert evidence['1135:4']['weight']==3.
    # A different saved native share changes only this conditional prior.
    tree.find(".//vehicleRoutingDecisionStatic[@no='1135']/vehRoutSta/vehicleRouteStatic[@no='4']").set('relFlow','2 0:8')
    assert route._known_native_choice_prior(tree,proof,NAMES)[0]['RM_C10681']==.8


@pytest.mark.parametrize('bad', ['time_dependent','zero_total','path','formula'])
def test_unproved_choice_is_rejected(bad):
    tree,proof=inputs()
    choices=tree.find(".//vehicleRoutingDecisionStatic[@no='1135']/vehRoutSta")
    if bad=='time_dependent':
        choices[0].set('relFlow','2 0:1 150:2')
    elif bad=='zero_total':
        for row in choices:row.set('relFlow','2 0:0')
    elif bad=='path':
        choices[0].set('destLink','2')
    else:
        choices[0].set('formula','x')
    with pytest.raises(ValueError):route._known_native_choice_prior(tree,proof,NAMES)


def test_future_choice_does_not_redistribute_known_unknown_or_pending_stock():
    storage='SC1004_W_out'
    spec=dict(storage=storage,future_choice_weights={'free':.2,'RM_C10646':.2,'RM_C10681':.6})
    cfg=NS(network=NS(known_legsplit_routes=spec,urban_link_storage_veh={storage:100.},
        boundary_out_ramp_split={storage:dict(free=.3333,ramps=dict(RM_C10646=.5,RM_C10681=.1667))}))
    cohorts=[dict(target=t,vehicles=n,due=due,source='fixture') for t,n,due in
             [('RM_C10646',2.,0),('free',3.,0),('unknown',1.,0),('prechoice',5.,0),('prechoice',4.,20)]]
    state=NS(urban_link_storage={storage:85.},known_legsplit_route_state=dict(cohorts=cohorts,plan=None,received=0.,departed=0.))
    original=copy.deepcopy(state)
    candidate=copy.deepcopy(state)
    req=route.known_legsplit_requests(candidate,cfg,storage,11.,11.,10)
    assert req=={'RM_C10646':3.,'free':4.,'RM_C10681':3.}
    assert state==original
    assert sum(c['vehicles'] for c in candidate.known_legsplit_route_state['cohorts'])==15.
    assert sum(c['vehicles'] for c in candidate.known_legsplit_route_state['cohorts'] if c['target']=='unknown')==1.
    assert sum(c['vehicles'] for c in candidate.known_legsplit_route_state['cohorts'] if c['target']=='prechoice')==4.
    route.known_legsplit_commit(candidate,cfg,[],10)  # all receivers reject
    # Even if a later prior differs, already sampled choices cannot be redrawn.
    spec['future_choice_weights']={'free':0.,'RM_C10646':1.,'RM_C10681':0.}
    assert route.known_legsplit_requests(candidate,cfg,storage,11.,11.,11)==req


def test_native_prior_requires_explicit_preserved_route_mode():
    for option in ('true',1,None,True):
        with pytest.raises(ValueError):
            route.configure_known_legsplit(NS(network=NS()),{'urban':{'known_wout_native_choice_prior':option}},None,None)
