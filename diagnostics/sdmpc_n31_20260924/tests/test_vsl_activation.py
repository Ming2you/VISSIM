"""Bounded real-command probing of an inactive VSL, without a benefit bonus."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.sdmpc import vsl_activation_axes
from evaluation.controllers.sdmpc_sequence import SequenceCoordinates


def coordinates():
    c=SequenceCoordinates.__new__(SequenceCoordinates)
    c.vsl_activation_secant=True
    c.axes=[dict(kind='vsl',reference_value=110.,scale=110.,fd=10/110,
                 allowed=list(range(50,111,10)),block=i) for i in range(3)]
    c.lower=np.array([-40.,-60.,-60.])/110
    c.upper=np.zeros(3)
    c.G=np.array([[-1.,1.,0.],[0.,-1.,1.]])
    c.glo=np.array([-20.,-20.])/110;c.ghi=-c.glo
    return c


def test_only_dormant_zero_axes_are_probed():
    c=coordinates();z=np.array([0.,-30/110,0.]);g=np.zeros((2,3));a=np.zeros((2,3))
    assert set(vsl_activation_axes(c,z,g,a,110.))=={0,2}
    g[0,0]=1.
    assert set(vsl_activation_axes(c,z,g,a,110.))=={2}
    a[1,2]=1.
    assert not vsl_activation_axes(c,z,g,a,110.)


def test_three_block_secants_respect_next_and_previous_commands():
    c=coordinates()
    for z in (np.zeros(3),np.array([-10.,-30.,-40.])/110):
        for j in range(3):
            for delta in c.stencil(z,j):
                point=z.copy();point[j]+=delta
                assert np.all(point>=c.lower-1e-12) and np.all(point<=c.upper+1e-12)
                assert np.all(c.G@point>=c.glo-1e-12) and np.all(c.G@point<=c.ghi+1e-12)
                assert abs(round((110+110*point[j])/10)*10-(110+110*point[j]))<1e-9
    assert c.stencil(np.zeros(3),0)==(-10/110,0.)


def test_default_three_block_tangent_contract_is_unchanged():
    c=coordinates();c.vsl_activation_secant=False
    with pytest.raises(ValueError):c.stencil(np.zeros(3),0)
    c.vsl_activation_secant=True;c.axes[0]['kind']='meter'
    with pytest.raises(ValueError):c.stencil(np.zeros(3),0)


def test_selected_policy_does_not_silently_ignore_activation_option():
    import json
    from evaluation.controllers import sdmpc
    tuning=json.loads((Path(__file__).resolve().parents[1]/'integration_20260926/selected/config_n31_v2.json').read_bytes())
    cfg=SimpleNamespace(network=SimpleNamespace(physical_ramp_branches=True,control_area_enabled=True,
        control_area_beta_seconds=0,control_area_refresh_nuf_target_each_decision=True),
        mpc=SimpleNamespace(horizon_steps=3),simulation=SimpleNamespace(T_c_sec=150))
    assert sdmpc.configure(tuning,cfg)['vsl_activation_secant'] is True
    tuning['adapter']['sdmpc_vsl_activation_secant']=False
    assert sdmpc.configure(tuning,cfg)['vsl_activation_secant'] is False
    tuning['adapter']['sdmpc_vsl_activation_secant']='yes'
    with pytest.raises(ValueError):sdmpc.configure(tuning,cfg)

