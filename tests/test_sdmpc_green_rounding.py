"""Regression for SC6's saved-state 0.001 s pivot undershoot."""
from types import SimpleNamespace as NS
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'vendor/NumSim-mine'))
from evaluation.controllers import sdmpc, physical_ramp_branches, signal_actuation_contract as signals
from src.models.state import ControlAction


def coordinate(monkeypatch, values):
    phases = ('p1', 'p2', 'p3', 'p4')
    native = dict(zip(phases, (43., 21., 52., 22.)))
    basis = dict(schema_version='native-clock-v1', kind='serial', cycle_sec=150.,
        amber_sec=3., all_red_sec=0., phase_order=['p3','p4','p1','p2'],
        idle_after_phase_sec=dict.fromkeys(phases,0.), native_green_sec=native)
    net = NS(signals=['SC6'], ramps=[], freeway_links=[], green_min=20.,
        signal_live_phases=lambda _: phases, signal_effective_green_total=lambda _:138.,
        signal_cycle_length=lambda _:150., signal_actuation_contract={'nodes':{
            'SC6':dict(native_cycle_sec=150.,axis_green_sec=native,native_clock_basis=basis)}})
    ref = ControlAction(green_times={'SC6_'+p:v for p,v in zip(phases,values)})
    c = sdmpc.Coordinates.__new__(sdmpc.Coordinates)
    c.cfg=NS(network=net);c.reference=ref;c.axes=[];c.valid=lambda _:True
    c.move_box=NS(validate=lambda _:None)
    monkeypatch.setattr(physical_ramp_branches,'candidate_from_greens',lambda out,*a:out)
    return c, ref


def test_native_minimum_survives_pivot_rounding(monkeypatch):
    c,ref=coordinate(monkeypatch,(64.2376,20.4086,33.3538,20.))
    result=c.decode([],ref)
    values=[result.green_times['SC6_'+p] for p in ('p1','p2','p3','p4')]
    assert min(values)>=20. and sum(values)==pytest.approx(138.)
    assert max(abs(a-b) for a,b in zip(values,(64.2376,20.4086,33.3538,20.)))<.002
    signals.validate_control(result,c.cfg)


def test_large_physical_violation_is_not_repaired(monkeypatch):
    c,ref=coordinate(monkeypatch,(66.,21.,32.,19.))
    with pytest.raises(ValueError,match='green bounds'):
        c.decode([],ref)


def test_already_executable_command_is_identical(monkeypatch):
    c,ref=coordinate(monkeypatch,(64.238,20.409,33.353,20.))
    assert c.decode([],ref).green_times==ref.green_times
