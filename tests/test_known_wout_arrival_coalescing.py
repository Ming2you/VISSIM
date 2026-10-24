from copy import deepcopy
import pytest
from evaluation.controllers.route_choice_corridor import _known_coalesce_arrivals


def packet():
    return dict(target='prechoice',source='SC52',vehicles=.1,due=12,speed_kph=36.,
                lane68=dict(shares={'1':1.},order=(10,2.),exit_step=23))


def test_same_physical_arrival_joins_without_cutoff_or_input_mutation():
    a=packet();b=packet();b['vehicles']=1e-180
    before=deepcopy([a,b]);result=_known_coalesce_arrivals([a,b])
    assert len(result)==1 and result[0]['vehicles']==a['vehicles']+b['vehicles']
    assert [a,b]==before


@pytest.mark.parametrize('different',['source','target','due','lane','reservation','exit'])
def test_distinct_physical_arrivals_remain_distinct(different):
    a=packet();b=packet()
    if different=='source':b['source']='SC66'
    elif different=='target':b['target']='free'
    elif different=='due':b['due']+=1
    elif different=='lane':b['lane68']['shares']={'2':1.}
    elif different=='reservation':b['lane68']['order']=(11,2.)
    else:b['lane68']['exit_step']+=1
    assert len(_known_coalesce_arrivals([a,b]))==2


def test_vehicle_sensitivities_add_but_metadata_sensitivities_do_not_merge():
    from evaluation.controllers.sdmpc_dual import Dual,Trace,derivative
    trace=Trace([.01,.01]);a=packet();b=packet()
    a['vehicles']=Dual(.1,{0:1.},trace);b['vehicles']=Dual(.2,{1:1.},trace)
    merged=_known_coalesce_arrivals([a,b])
    assert len(merged)==1 and derivative(merged[0]['vehicles'])=={0:1.,1:1.}
    a['lane68']['shares']['1']=Dual(1.,{0:1.},trace)
    b['lane68']['shares']['1']=Dual(1.,{1:1.},trace)
    assert len(_known_coalesce_arrivals([a,b]))==2
