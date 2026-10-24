"""A feasible improvement on one freeway must not mask the other freeway."""
import numpy as np
import pytest
from evaluation.controllers import sdmpc


class Coordinates:
    axes = [dict(kind='meter', owner='FW_W'), dict(kind='meter', owner='FW_E'),
            dict(kind='green', owner='SC1')]

    def encode(self, action):
        return np.array(action, dtype=float)

    def decode(self, z, template):
        assert z[2] == template[2]
        return tuple(z)

    def valid(self, z):
        return len(z) == 3 and np.all(np.isfinite(z))

    def validate(self, action):
        assert self.valid(action)


def audit(monkeypatch, costs, feasible=lambda a, v: True):
    monkeypatch.setattr(sdmpc, 'meter_neighbors', lambda c, a: [
        ('west:tighten', (1., 0., 7.)), ('east:tighten', (0., 1., 7.))])
    calls = []
    def evaluate(actions):
        calls.extend(actions)
        return [dict(objective_veh_h=costs[tuple(a[:2])]) for a in actions]
    best, proof = sdmpc.audit_meter_neighbors(Coordinates(),
        ((0., 0., 7.), dict(objective_veh_h=100.), None), 1e-7, evaluate, feasible)
    return best, proof, calls


def test_joint_gain_is_evaluated_and_selected(monkeypatch):
    best, proof, calls = audit(monkeypatch, {(1., 0.):99., (0., 1.):99.5, (1., 1.):98.5})
    assert best[0] == (1., 1., 7.)
    assert proof['additional_predictions'] == len(calls) == 3
    assert proof['selected'] == 'combined_meter_owners'


@pytest.mark.parametrize('cost,allowed', [(100.1, True), (98.5, False)])
def test_nonlinear_harm_or_constraint_failure_preserves_single_winner(monkeypatch, cost, allowed):
    best, proof, calls = audit(monkeypatch, {(1., 0.):99., (0., 1.):99.5, (1., 1.):cost},
        lambda a,v: allowed or tuple(a[:2]) != (1., 1.))
    assert best[0] == (1., 0., 7.)
    assert len(calls) == 3


def test_one_improving_owner_needs_no_extra_prediction(monkeypatch):
    best, proof, calls = audit(monkeypatch, {(1., 0.):99., (0., 1.):101.})
    assert best[0] == (1., 0., 7.)
    assert len(calls) == proof['additional_predictions'] == 2


def test_infeasible_single_is_not_used_in_combination(monkeypatch):
    best, proof, calls = audit(monkeypatch, {(1., 0.):99., (0., 1.):98.},
        lambda a,v: a[1] == 0.)
    assert best[0] == (1., 0., 7.)
    assert len(calls) == 2


def test_saved_1800_costs_choose_the_verified_lower_cost_combination(monkeypatch):
    # Selection-only replay of measured model scores, not a new traffic model.
    offset=526.8347525714414-100.
    costs={(1.,0.):526.7880709018351-offset,
           (0.,1.):526.8252300737954-offset,
           (1.,1.):526.7785416876978-offset}
    best,proof,calls=audit(monkeypatch,costs)
    assert best[0]==(1.,1.,7.)
    assert proof['selected']=='combined_meter_owners'


def test_disjoint_ramps_on_same_freeway_are_combined(monkeypatch):
    monkeypatch.setattr(Coordinates, 'axes', [dict(kind='meter',owner='FW_E'),
        dict(kind='meter',owner='FW_E'),dict(kind='green',owner='SC1')])
    best,proof,calls=audit(monkeypatch,{(1.,0.):99.,(0.,1.):99.5,(1.,1.):98.5})
    assert best[0]==(1.,1.,7.)
    assert len(calls)==proof['additional_predictions']==3


def test_same_owner_joint_rejected_by_unchanged_cap(monkeypatch):
    monkeypatch.setattr(Coordinates, 'axes', [dict(kind='meter',owner='FW_E'),
        dict(kind='meter',owner='FW_E'),dict(kind='green',owner='SC1')])
    best,proof,calls=audit(monkeypatch,{(1.,0.):99.,(0.,1.):99.5,(1.,1.):98.5},
        lambda a,v: a[0]+a[1]<=1)
    assert best[0]==(1.,0.,7.) and len(calls)==3


def test_overlapping_bundle_is_not_combined_with_an_individual_move(monkeypatch):
    monkeypatch.setattr(sdmpc,'meter_neighbors',lambda c,a:[
        ('all:tighten',(1.,1.,7.)),('west:release',(-1.,0.,7.)),('east:release',(0.,-1.,7.))])
    seen=[]
    def evaluate(actions):
        seen.extend(actions)
        return [dict(objective_veh_h={(1.,1.):98.,(-1.,0.):99.,(0.,-1.):99.5}[tuple(a[:2])]) for a in actions]
    best,proof=sdmpc.audit_meter_neighbors(Coordinates(),((0.,0.,7.),dict(objective_veh_h=100.),None),
        1e-7,evaluate,lambda a,v:True)
    assert best[0]==(1.,1.,7.) and len(seen)==proof['additional_predictions']==3
