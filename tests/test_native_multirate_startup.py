"""Do not reinterpret the initial native1s command as an aligned MPC state."""
import copy
import pytest
from types import SimpleNamespace as NS
from evaluation.controllers.runtime_setup import native_startup_without_prediction
from evaluation.controllers import multirate_freeway as macro
from src.models.state import SimulationConfig

def inputs():
    return ({'freeway':{'multirate_exchange_sec':5},'urban':{'multirate_exchange_sec':10}},
        {'sim_sec':1,'obs150':{'sim_sec':1,'k':None,'window':None}})

def test_initial_native_command_has_no_prediction_and_preserves_observation():
    tuning,raw=inputs();before=copy.deepcopy((tuning,raw))
    assert native_startup_without_prediction(tuning,raw,'no-control')
    assert (tuning,raw)==before

@pytest.mark.parametrize('controller',['wu-link','diagnostic-vsl-rm',None])
def test_non_native_commands_cannot_skip_clock_validation(controller):
    tuning,raw=inputs();assert not native_startup_without_prediction(tuning,raw,controller)

@pytest.mark.parametrize('time',[0,5,10,150,750,900])
def test_regular_observations_keep_full_runtime(time):
    tuning,raw=inputs();raw['sim_sec']=raw['obs150']['sim_sec']=time
    assert not native_startup_without_prediction(tuning,raw,'no-control')

@pytest.mark.parametrize('key,value',[('k',1),('window',{'start_sec':0,'end_sec':150}),('sim_sec',150)])
def test_observation_contract_must_be_startup(key,value):
    tuning,raw=inputs();raw['obs150'][key]=value
    assert not native_startup_without_prediction(tuning,raw,'no-control')

def test_prediction_still_rejects_unaligned_state_then_accepts900():
    cfg=NS(simulation=SimulationConfig(T_f=1,T_u=1,control_interval=150),network=NS())
    road=NS(simulation=SimulationConfig(T_f=1,T_u=1))
    state=NS(time_sec=1.,lane_freeway_runtime=NS(time_sec=1.,lanes={},configs={'FW':road}),lane_ramp_runtime=NS(buffers={}))
    tuning,_=inputs()
    with pytest.raises(ValueError,match='freshly'):macro.configure(cfg,tuning,state)
    assert cfg.simulation.T_f_sec==1
    state.time_sec=state.lane_freeway_runtime.time_sec=900.
    macro.configure(cfg,tuning,state)
    assert cfg.simulation.T_f_sec==road.simulation.T_f_sec==5
