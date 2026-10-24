import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from evaluation.controllers import sdmpc, lane_plant_runtime


class Coordinates:
    def __init__(self, held=10):
        self.axes = [dict(kind='meter', key=r, owner=o, scale=10.,
                          reference_value=held, block=b,
                          allowed=list(range(max(2, held-2*(b+1)), min(10, held+2*(b+1))+1)))
                     for b in range(3) for r, o in [('A', 'E'), ('B', 'E'), ('C', 'W')]]
        self.move_box = SimpleNamespace(entries=[('diagnostics', 'rw_meter_green_'+r, held, 2, None)
                                                for r in ('A', 'B', 'C')])
        self.held = held

    def encode(self, action):
        return np.array([(action['g'][a['block']][a['key']]-self.held)/10 for a in self.axes])

    def decode(self, z, template):
        out = copy.deepcopy(template)
        for value, axis in zip(z, self.axes):
            out['g'][axis['block']][axis['key']] = self.held+10*value
        self.validate(out)
        return out

    def validate(self, action):
        for r in ('A', 'B', 'C'):
            previous = self.held
            for block in action['g']:
                assert 2 <= block[r] <= 10 and abs(block[r]-previous) <= 2+1e-9
                previous = block[r]


def action(g):
    return dict(g=[dict(A=g, B=g, C=g) for _ in range(3)],
                city={'green': 60, 'offset': 40}, vsl=90, np_cap=500, nuf_cap=4500)


def test_profiles_leave_plateau_and_preserve_other_controls():
    c = Coordinates()
    a = action(10)
    rows = dict(sdmpc.meter_neighbors(c, a))
    assert len(rows) == 4  # Three individual ramps and the two-ramp E group.
    assert [b['A'] for b in rows['A:tighten']['g']] == [8, 6, 4]
    assert [b['B'] for b in rows['A:tighten']['g']] == [10, 10, 10]
    assert [b['B'] for b in rows['E:tighten']['g']] == [8, 6, 4]
    for candidate in rows.values():
        assert {k:v for k,v in candidate.items() if k != 'g'} == {k:v for k,v in a.items() if k != 'g'}
    assert a == action(10)


def test_release_is_checked_and_infeasible_better_candidate_is_rejected():
    c = Coordinates(4)
    a = action(4)
    rows = dict(sdmpc.meter_neighbors(c, a))
    assert [b['C'] for b in rows['C:release']['g']] == [6, 8, 10]
    def evaluate(candidates):
        return [dict(objective_veh_h=80 if x['g'][0]['A'] == 2 else 90,
                     feasible=x['g'][0]['A'] != 2) for x in candidates]
    best, proof = sdmpc.audit_meter_neighbors(c, (a, {'objective_veh_h':100}, 'old_dual'),
                                            1e-7, evaluate, lambda a,i:i['feasible'])
    assert best[1]['objective_veh_h'] == 90 and best[2] is None
    assert proof['additional_predictions'] <= 8
    held, proof = sdmpc.audit_meter_neighbors(c, (a, {'objective_veh_h':100}, 'old_dual'),
        1e-7, lambda xs:[dict(objective_veh_h=101) for _ in xs], lambda a,i:True)
    assert held[0] is a and held[2] == 'old_dual' and proof['selected'] is None


def test_ramp_reference_conflicts_are_explicit(tmp_path):
    p = tmp_path/'reference.json'
    reference = dict(physical_ramp_head_service_veh_per_cycle={'R':{'9':4.2,'10':4.2}},
                     physical_ramp_receiving_nodes={'R':{'critical_gap_sec':3.5}})
    p.write_text(json.dumps({'freeway':reference}))
    ctx = dict(paths={'reference_config':p}, document={'sources':{'reference_config':{'sha256':'pin'}}})
    tuning = {'freeway':dict(reference, ramp_reference_contract=True)}
    assert lane_plant_runtime.check_ramp_reference(tuning,ctx)['ramp_reference_contract']['matched']
    tuning['freeway']['physical_ramp_head_service_veh_per_cycle'] = {'R':{'9':3.69,'10':4.2}}
    with pytest.raises(ValueError, match='disagree'):
        lane_plant_runtime.check_ramp_reference(tuning,ctx)
    tuning['freeway']['ramp_reference_contract'] = False
    assert lane_plant_runtime.check_ramp_reference(tuning,ctx) == {}
