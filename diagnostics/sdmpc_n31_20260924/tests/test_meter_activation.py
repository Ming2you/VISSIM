"""Escape an OPEN service plateau with legal endpoints, not a reward."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import sdmpc
from evaluation.controllers.sdmpc_sequence import SequenceCoordinates


def coordinates(enabled=True):
    c = SequenceCoordinates.__new__(SequenceCoordinates)
    c.vsl_activation_secant = False
    c.meter_activation_secant = enabled
    c.axes = [dict(kind='meter', reference_value=10., scale=10., fd=.2,
                   allowed=list(range(2, 11)), block=i) for i in range(3)]
    c.lower = np.array([-.2, -.4, -.6])
    c.upper = np.zeros(3)
    c.G = np.array([[-1., 1., 0.], [0., -1., 1.]])
    c.glo = np.array([-.2, -.2])
    c.ghi = -c.glo
    return c


def test_open_plateau_probe_reaches_g8_in_each_block():
    c = coordinates()
    for j in range(3):
        lo, hi = c.stencil(np.zeros(3), j)
        assert (lo, hi) == pytest.approx((-.2, 0.))
        # The inherited active table has equal g9/g10; g8 leaves that plateau.
        assert min(.5 * (10 + 10 * lo), 4.2) < min(.5 * 10, 4.2)


def test_probe_respects_previous_and_next_block_limits():
    c = coordinates()
    for z in (np.zeros(3), np.array([-.2, -.4, -.6]), np.array([-.1, -.3, -.1])):
        for j in range(3):
            for delta in c.stencil(z, j):
                point = z.copy()
                point[j] += delta
                assert np.all(point >= c.lower - 1e-12)
                assert np.all(point <= c.upper + 1e-12)
                assert np.all(c.G @ point >= c.glo - 1e-12)
                assert np.all(c.G @ point <= c.ghi + 1e-12)
                assert 10 + 10 * point[j] == pytest.approx(round(10 + 10 * point[j]))


def test_only_open_zero_sensitivity_meter_axes_are_added():
    c = coordinates()
    z = np.array([0., -.1, 0.])
    gradient, resources = np.zeros((2, 3)), np.zeros((2, 3))
    assert set(sdmpc.meter_activation_axes(c, z, gradient, resources)) == {0, 2}
    gradient[0, 0] = 1.
    assert set(sdmpc.meter_activation_axes(c, z, gradient, resources)) == {2}
    resources[1, 2] = 1.
    assert not sdmpc.meter_activation_axes(c, z, gradient, resources)
    c.axes[2]['kind'] = 'vsl'
    assert set(sdmpc.meter_activation_axes(c, z, np.zeros((2, 3)), resources)) == {0}


def test_default_stencil_is_unchanged_and_option_is_explicit():
    c = coordinates(False)
    assert sdmpc.Coordinates.stencil(c, np.zeros(3), 0) == pytest.approx((-.2, 0.))
    with pytest.raises(ValueError):
        c.stencil(np.zeros(3), 0)
    tuning = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/config_n31_v2.json').read_bytes())
    cfg = SimpleNamespace(network=SimpleNamespace(physical_ramp_branches=True, control_area_enabled=True,
        control_area_beta_seconds=0, control_area_refresh_nuf_target_each_decision=True),
        mpc=SimpleNamespace(horizon_steps=3), simulation=SimpleNamespace(T_c_sec=150))
    assert not sdmpc.configure(tuning, cfg).get('meter_activation_secant', False)
    tuning['adapter']['sdmpc_meter_activation_secant'] = True
    assert sdmpc.configure(tuning, cfg)['meter_activation_secant'] is True
    tuning['adapter']['sdmpc_meter_activation_secant'] = 'yes'
    with pytest.raises(ValueError):
        sdmpc.configure(tuning, cfg)
