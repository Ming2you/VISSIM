"""Whole accepted destinations must not leave artificial positive packets."""
from types import SimpleNamespace as NS
import pytest
from evaluation.controllers.route_choice_corridor import known_legsplit_commit


def commit(amounts,accepted):
    rows=[dict(target='free',vehicles=x,due=0,source='same') for x in amounts]
    total=sum(amounts)
    state=NS(known_legsplit_route_state=dict(cohorts=rows,plan=dict(step=0,rows=[(c,c['vehicles']) for c in rows],
                 requests={'free':total}),departed=0.),urban_storage_release_buffer={},urban_link_storage={'W':100.-total+accepted})
    cfg=NS(network=NS(known_legsplit_routes={'storage':'W'},urban_link_storage_veh={'W':100.}))
    known_legsplit_commit(state,cfg,[('W',None,accepted)],0)
    return state


@pytest.mark.parametrize('amounts',[(.1,.6),(.3,.4),(.01,.06),(.0001,.0006)])
def test_whole_acceptance_retires_every_source_packet(amounts):
    s=commit(amounts,sum(amounts))
    assert s.known_legsplit_route_state['cohorts']==[]
    assert s.known_legsplit_route_state['departed']==sum(amounts)


@pytest.mark.parametrize('scale',[1.,1e-180])
def test_real_partial_stock_survives_even_when_tiny(scale):
    amounts=[.1*scale,.6*scale];s=commit(amounts,sum(amounts)/2.)
    remaining=[c['vehicles'] for c in s.known_legsplit_route_state['cohorts']]
    assert len(remaining)==2
    assert sum(remaining)==pytest.approx(sum(amounts)/2.,rel=1e-14,abs=0.)


def test_partial_acceptance_keeps_sensitivity(monkeypatch):
    from evaluation.controllers import route_choice_corridor as routes
    from evaluation.controllers.sdmpc_dual import Dual,Trace,derivative,MathProxy
    monkeypatch.setattr(routes,'math',MathProxy())
    accepted=Dual(.35,{0:1.},Trace([.01]))
    s=commit([.1,.6],accepted)
    remaining=sum(c['vehicles'] for c in s.known_legsplit_route_state['cohorts'])
    assert derivative(remaining)[0]==pytest.approx(-1.)
    assert derivative(s.known_legsplit_route_state['departed'])[0]==1.
