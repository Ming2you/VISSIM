"""One predeclared RM contrast; no cap search or optimized future state."""
import copy
from evaluation.controllers import physical_ramp_branches as ramps,sdmpc_sequence as seq
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal

TARGET='RM_C10681'
SAME=('green_times','offsets','vsl','inflow_outflow_allocation','N_P_star','N_UF_star')

def pair(reference,cfg,cap_action):
    reference=seq.first_action(reference)
    if reference.diagnostics['rw_meter_green_'+TARGET]!=2:
        raise ValueError('This declared case starts at the observed2-second10681 green')
    result={}
    for name in ('hold','release'):
        blocks=[];previous=reference
        for j in range(3):
            base=reference.copy()
            base.N_P_star=cap_action.N_P_star;base.N_UF_star=cap_action.N_UF_star
            greens={r:base.diagnostics['rw_meter_green_'+r] for r in base.ramp_metering}
            greens[TARGET]=2 if name=='hold' else 4+2*j
            block=ramps.candidate_from_greens(base,previous,cfg,greens)
            blocks.append(block);previous=block
        result[name]=blocks
    for held,released in zip(result['hold'],result['release']):
        for k in SAME:
            if not equal(getattr(held,k),getattr(released,k)):raise ValueError('Unrelated control changed: '+k)
        if {r for r in held.ramp_metering if held.ramp_metering[r]!=released.ramp_metering[r]}!={TARGET}:
            raise ValueError('Contrast is not isolated10681')
    return result
