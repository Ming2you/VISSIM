"""Independent supply/FIFO constraints and saved autonomous outcome checks."""
import ast
import copy
import gzip
import itertools
import json
import math
from pathlib import Path
from types import SimpleNamespace as NS
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def preflight():
    s=h.read(HERE/'executed_function_sources.json')['RouteLaneRegion']
    ns=dict(math=math,copy=copy);exec(compile(s,'189_actual_candidate','exec'),ns)
    cls=ns['RouteLaneRegion'];checks=0
    # Independent 2-input node properties with both exit and ramp clipping.
    # Test full off blockage, demand-limited streams, priorities0/1, saturation.
    for R,D,E,C,A,p in itertools.product((0.,.1,1.,3.),(0.,.1,1.,4.),(0.,.3,2.),(0.,.2,3.),(0.,.1,1.,5.),(0.,.5,1.)):
        beta=min(1.,C/E) if E else 1.
        Dm=D*beta
        ramp=min(A,cls._shared_ramp_supply(R,Dm,p))
        factor=min(1.,C/E if E else 1.,(R-ramp)/D if D else 1.)
        main=D*factor;exit_flow=E*factor
        assert min(ramp,main,exit_flow)>=-1e-12
        assert ramp<=A+1e-12 and main<=D+1e-12 and exit_flow<=C+1e-12
        assert abs(ramp+main-min(R,A+Dm))<1e-12
        assert ramp+main<=R+1e-12
        if ramp<A-1e-12 and main<Dm-1e-12:
            assert abs(ramp-p*R)<1e-12 and abs(main-(1.-p)*R)<1e-12
        checks+=1
    # Check actual method wiring: a blocked off exit must NOT reserve space
    # for its immobilized through queue (naive raw-D sharing fails this test).
    obj=cls.__new__(cls);obj.road='FW_E';obj.ramp_access={'RM_C10490':0}
    obj.merge_priority={'RM_C10490':.5};obj.reciprocal_off='10483'
    obj.receiving_cells=[];obj.lengths=[1.]*31;obj.priority_rows=[]
    obj.stocks={21:[{'x|end':9.}],20:[{'x|end':1.,'x|10483':1.}]};obj.v={20:[3600.]}
    cfg=NS(simulation=NS(T_f_h=1/3600),network=NS(rho_max=10.,offramp_route_inventory={'merges':{'RM_C10490':{'cell':21}}}))
    blocked=obj.ramp_supply('RM_C10490',cfg,{'10483':0.},1.)
    assert blocked==3600.,blocked
    open_exit=obj.ramp_supply('RM_C10490',cfg,{'10483':3600.},2.)
    assert open_exit==1800.,open_exit
    obj.merge_priority['RM_C10490']=1.
    assert obj.ramp_supply('RM_C10490',cfg,{'10483':3600.},3.)==3600.
    old=ast.parse((HERE/'runner_before189.py.txt').read_text(encoding='utf8'))
    new=ast.parse((h.R/'state_lateral168/run.py').read_text(encoding='utf8'))
    a={n.name:ast.dump(n) for n in old.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in new.body if isinstance(n,ast.FunctionDef)}
    assert all(b[k]==v for k,v in a.items() if k!='queue178')
    proto=h.read(HERE/'protocol.json')
    for p,d in {**h.read(HERE/'pins.json'),**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(p)==d,p
    result=dict(status='pass',node_property_cases=checks,blocked_off_returns_supply=True,p1_is_disabled=True,prior_runner_functions_unchanged=True)
    h.save(HERE/'preflight.json',result);print(json.dumps(result))


def completed():
    out=HERE/'forecast';assessment=h.read(out/'assessment.json')
    assert assessment['status']=='complete' and assessment['forecasts']==13
    assert all(h.read(out/'old178_parity.json').values())
    rows=h.read(out/'rows.json');native=h.read(h.R/'ramp_motion187/summary.json')['rows']
    check_count=0;max_error=0.;details=[]
    def exact(a,b):
        nonlocal check_count,max_error
        e=abs(a-b);max_error=max(max_error,e);check_count+=1
        assert e<1e-8,(a,b,e)
    for r in [r for r in rows if r['horizon']==450 and r['mode']=='priority']:
        key=r['case']+'_'+r['arm']
        data=h.read(out/'priority'/(key+'_allocation.json.gz'))
        pred=h.read(out/'priority'/(key+'.json.gz'));base=h.read(out/'baseline'/(key+'.json.gz'))
        lane={(round(z['time_s'],6),z['cell'],z['lane']):z for z in data['lanes']}
        junction={round(z['time_s'],6):z for z in data['junction']}
        receiving={round(z['time_s'],6):z for z in data['receiving'] if z['cell']==21 and z['lane']==1}
        ramps={round(z['start_sec'],6):z for z in pred['ramps'] if z['ramp']=='RM_C10490'}
        assert len(data['allocation'])==450 and len(ramps)==450
        binding=0;opportunity_loss=0.;used=0.
        for z in data['allocation']:
            t=round(z['time_s'],6);e=round(t+1.,6)
            R=receiving[t]['accepted_budget_veh'];j=junction[t]
            D=j['through_request_veh'];E=j['off_request_veh'];C=z['exit_capacity_vph']/3600
            beta=min(1.,C/E) if E else 1.;Dm=D*beta
            # Verify the saved call against the separately executed plan ledgers.
            exact(z['mainline_raw_vph']/3600,D);exact(z['exit_request_vph']/3600,E)
            exact(z['receiving_vph']/3600,R);exact(z['off_factor'],beta)
            cap=min(R,max(.5*R,R-Dm));exact(z['ramp_budget_vph']/3600,cap)
            m=ramps[t]['accepted_merge_veh'];q=lane[e,21,1]['mainline_in_veh']
            exact(m,lane[e,21,1]['merge_veh'])
            exact(q,min(Dm,max(0.,R-m)))
            fifo=min(beta,max(0.,R-m)/D if D else 1.)
            exact(j['off_accepted_veh'],E*fifo)
            assert m<=cap+1e-8 and m+q<=R+1e-8
            assert ramps[t]['unused_receiving_budget_veh']>=-1e-8
            exact(ramps[t]['conservation_residual_veh'],0.)
            opportunity_loss+=R-cap;used+=m
            if abs(m-cap)<1e-8 and R-cap>1e-8:binding+=1
        ramp_summary=[]
        for connector in ('10639','10681','10490','10484'):
            rr='RM_C'+connector
            nr=next((n for n in native if n['case']==r['case'] and n['arm']==r['arm'] and n['connector']==connector),None)
            record=dict(connector=connector,actual_merge450=r['actual']['merges'][rr],
                        predicted_merge450=r['predicted']['merges'][rr])
            for label,forecast in [('baseline',base),('candidate',pred)]:
                a=[x for x in forecast['ramps'] if x['ramp']==rr]
                tick0=min(x['start_sec'] for x in a)
                sample=[x['start'] for x in a if round(x['start_sec']-tick0)%5==0]
                assert len(sample)==90
                record[label]=dict(merge450=sum(x['accepted_merge_veh'] for x in a),
                    posthead_mean5=sum(x['downstream_travelling_veh']+x['merge_ready_veh'] for x in sample)/90,
                    ready_mean5=sum(x['merge_ready_veh'] for x in sample)/90,
                    inside_cost1=sum(x['connector_ttt_veh_h'] for x in a),
                    outside_cost1=sum(x['start']['outside_component_backlog_veh'] for x in a)/3600)
            if nr:record['actual_posthead_mean5']=nr['posthead_mean_native5_left']
            ramp_summary.append(record)
        details.append(dict(case=r['case'],arm=r['arm'],binding_seconds=binding,
            allocated_opportunity_reduction_veh=opportunity_loss,actual_merged_veh=used,ramps=ramp_summary))
    gates={};regrets={}
    for horizon in ('150','450'):
        b=assessment['losses'][horizon]['baseline'];p=assessment['losses'][horizon]['priority']
        rr=[r for r in rows if r['mode']=='priority' and r['horizon']==int(horizon)]
        regrets[horizon]=[]
        for case in sorted({r['case'] for r in rr}):
            case_rows=[r for r in rr if r['case']==case]
            chosen=min(case_rows,key=lambda r:r['predicted']['ttt'])
            regrets[horizon].append(dict(case=case,chosen=chosen['arm'],actual_regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in case_rows)))
        gates[horizon]=dict(meaningful_signs=all(p['sign_correct'] for p in p['pairs'] if p['meaningful']),
            response=p['response']<=.9*b['response'],absolute=p['absolute']<=1.1*b['absolute'],
            regret=all(r['actual_regret']<=.5 for r in regrets[horizon]))
    preservation=h.read(out/'preservation.json')
    proto=h.read(HERE/'protocol.json')
    for path,digest in {**preservation['input_sha256'],**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    h.save(HERE/'verification.json',dict(status='pass',disabled_p1_four_tables_exact=True,
        node_plan_checks=check_count,max_difference=max_error,protected_and_STOP=True,forecast_count=13))
    h.save(HERE/'results.json',dict(status='complete',scope='East component, not wholeOmega',gates=gates,regrets=regrets,details=details,
        limitations=proto['limitations'],adopted=False))
    h.save(HERE/'completion.json',dict(status='complete',result='REJECTED' if not all(gates['450'].values()) else 'SCREEN_PASSED_ONLY',
        forecasts=13,seconds=assessment['seconds'],fit=0,VISSIM=0,FZP=0,push=False,production_adopted=False,full_goal='ACTIVE_NOT_QUALIFIED'))
    print(json.dumps(dict(gates=gates,checks=check_count,max_difference=max_error)))


if __name__=='__main__':
    import sys
    if '--completed' in sys.argv:completed()
    else:preflight()
