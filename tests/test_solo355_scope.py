import copy
from types import SimpleNamespace as NS
import numpy as np
import pytest
from evaluation.controllers import sdmpc, sdmpc_sequence, sdmpc_actuator_scope as scope
from evaluation.controllers import signal_actuation_contract as sig, physical_ramp_branches as rm
from evaluation.controllers.joint_owner_neighbors import FixedMoveBox
from src.models.state import ControlAction

def fixture(monkeypatch, mode):
    spec={'cycle_sec':10.,'ramps':{'RM':{'service_by_green_veh_h':{str(g):g*100 for g in range(2,11)}}}}
    net=NS(signals=['SC1'],ramps=['RM'],freeway_links=['FW_E'],physical_ramp_branches=spec,
        signal_cycle_length=lambda _:150.,signal_live_phases=lambda _:('p1','p2'),
        signal_effective_green_total=lambda _:138.,ramp_to_freeway={'RM':'FW_E'},
        freeway_vsl_zone_free=[1],freeway_vsl_zone_heads={'FW_E':[0,1,2]},
        freeway_vsl_zone_head_of_cell={'FW_E':[0,1,2]})
    cfg=NS(network=net,freeway_follower=NS(vsl_set=[50,60,70,80,90,100,110]),mpc=NS(horizon_steps=3))
    ref=ControlAction(green_times={'SC1_p1':70.,'SC1_p2':68.,'SC1_p3':0.,'SC1_p4':0.},offsets={'SC1':19.},
        vsl={'FW_E':110.,'FW_E__seg0':110.,'FW_E__seg1':110.,'FW_E__seg2':110.},diagnostics={'rw_meter_green_RM':10.})
    options=dict(fd_green_sec=1.,fd_offset_sec=1.,fd_meter_green_sec=1.,fd_vsl_kmh=10.,control_blocks=3)
    if mode:
        base={k:copy.deepcopy(getattr(ref,k)) for k in ('green_times','offsets')} if mode=='freeway_only' else {'meter_green_sec':10,'vsl_kmh':110}
        options['actuator_scope']=scope.configure({'mode':mode,'baseline':base},cfg)
    net.sdmpc_options=options
    entries=[('green_times',k,v,10.,None) for k,v in ref.green_times.items()]+[('offsets','SC1',19.,15.,150.),('diagnostics','rw_meter_green_RM',10.,2.,None),('vsl','FW_E__seg1',110.,40.,None)]
    box=FixedMoveBox(tuple(entries),'test')
    monkeypatch.setattr(sig,'native_clock_basis',lambda *a:None)
    monkeypatch.setattr(sig,'phase_bounds',lambda *a:{'p1':(2.,136.),'p2':(2.,136.)})
    monkeypatch.setattr(sig,'validate_vector',lambda *a:None)
    monkeypatch.setattr(sig,'validate_control',lambda *a:None)
    monkeypatch.setattr(rm,'operating_green_allowed',lambda *a:True)
    monkeypatch.setattr(rm,'prepare_control',lambda *a:None)
    def decode(out,previous,cfg,greens):
        out.diagnostics.update({'rw_meter_green_'+k:v for k,v in greens.items()});return out
    monkeypatch.setattr(rm,'candidate_from_greens',decode)
    return cfg,ref,box,options

@pytest.mark.parametrize('mode,kinds,n',[('freeway_only',{'meter','vsl'},6),('urban_only',{'green','offset'},6),(None,{'green','offset','meter','vsl'},12)])
def test_all_prediction_blocks_remove_only_inactive_axes(monkeypatch,mode,kinds,n):
    cfg,ref,box,options=fixture(monkeypatch,mode)
    coord=sdmpc_sequence.SequenceCoordinates(cfg,ref,box,options)
    assert len(coord.axes)==n
    assert {a['kind'] for a in coord.axes}==kinds
    assert coord.owners==('SC1','FW_E') # All cost owners remain, including inactive.
    z=coord.encode(ref)
    for j,a in enumerate(coord.axes):
        if a['kind']=='meter': z[j]=-0.2
        elif a['kind']=='vsl': z[j]=-10/110
        elif a['kind']=='green': z[j]=1/150
        else:z[j]=1/150
    out=coord.decode(z,ref)
    for c in sdmpc_sequence.actions(out,3):scope.check(c,options,cfg)

@pytest.mark.parametrize('mode,field',[('freeway_only','offsets'),('freeway_only','green_times'),('urban_only','diagnostics'),('urban_only','vsl')])
def test_inactive_mutation_rejected(monkeypatch,mode,field):
    cfg,ref,box,options=fixture(monkeypatch,mode)
    values=getattr(ref,field);key=next(iter(values));values[key]-=1
    with pytest.raises(ValueError,match='Inactive'):scope.check(ref,options,cfg)

def test_default_noop_and_invalid_scope(monkeypatch):
    cfg,ref,box,options=fixture(monkeypatch,None)
    assert scope.configure(None,cfg) is None
    for value in ({'mode':'both','baseline':{}},{'mode':'urban_only','baseline':{'meter_green_sec':8,'vsl_kmh':110}}):
        with pytest.raises(ValueError):scope.configure(value,cfg)
