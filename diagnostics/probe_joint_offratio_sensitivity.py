"""Held-action150/450s private-cfg native joint-prior sensitivity; no optimizer."""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import hashlib,json,math,os,pickle,re,sys,time
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
CONFIG=ROOT/'diagnostics/route_choice_native_phase_integration_config.json'
RUN=ROOT/'evaluation/runs/codex_area_beta0_retry_s13_20260910'
DEC=RUN/('decisions_'+RUN.name)
NETWORK=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
GROUPS={
    'OR_F_E':{'decision':'1130','signal':'10643','direct':'10682','physical_order':['10643','merge10639','10682']},
    'OR_D_E':{'decision':'1131','signal':'10481','direct':'10483','physical_order':['10481','merge10490','10483']},
    'OR_D_W':{'decision':'1132','signal':'10491','direct':'10479','physical_order':['10479','merge10480','10491']},
    'OR_F_W':{'decision':'1133','signal':'10638','direct':'10645','physical_order':['10645','merge10646','10638']}}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def frozen(value):return hashlib.sha256(pickle.dumps(value,protocol=5)).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def native_joint():
    if sha(NETWORK)!='085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317':
        raise ValueError('Reviewed native network changed')
    tree=ET.parse(NETWORK).getroot();result={}
    for off,spec in GROUPS.items():
        decision=tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{spec['decision']}']")
        if decision.get('allVehTypes')!='true' or decision.get('routeChoiceMeth')!='STATIC':
            raise ValueError('Native decision population/choice method changed')
        weights=Counter();routes=[]
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            path=[decision.get('link')]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
            present=[name for name in ('signal','direct') if spec[name] in path]
            if len(present)>1:raise ValueError('A route reaches both off branches')
            branch=present[0] if present else 'through';raw=(route.get('relFlow') or '').strip()
            match=re.fullmatch(r'2 0:([0-9]+(?:\.[0-9]+)?)',raw) if raw else None
            if raw and match is None:raise ValueError('Unexpected native route interval')
            value=float(match.group(1)) if match else 1.
            weights[branch]+=value
            routes.append({'route':route.get('no'),'branch':branch,'weight':value,'raw_relflow':raw,'path':path})
        if set(weights)!=set(('signal','direct','through')) or len(routes)!=3:raise ValueError('Native joint support changed')
        total=sum(weights.values());offtotal=weights['signal']+weights['direct']
        result[off]={**spec,'weights':dict(weights),'routes':routes,'joint':{k:v/total for k,v in weights.items()},
                     'total_off':offtotal/total,'direct_given_off':weights['direct']/offtotal}
        for branch in ('signal','direct'):
            p=result[off]['total_off']*(result[off]['direct_given_off'] if branch=='direct' else 1-result[off]['direct_given_off'])
            assert math.isclose(p,result[off]['joint'][branch],abs_tol=1e-14)
    return result


def stock_view(state,cfg):
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    counts=continuity_vehicle_counts(state,cfg)
    off={}
    for name in cfg.network.off_ramps:
        targets={'signal':cfg.network.off_ramp_storage_link[name],
                 'direct':cfg.network.offramp_direct_tail_by_offramp[name]}
        off[name]={branch:{'stock_veh':cfg.network.urban_link_storage_veh[target]-state.urban_link_storage[target],
                          'capacity_veh':cfg.network.urban_link_storage_veh[target],'storage':target}
                   for branch,target in targets.items()}
    cells={link:[{'N_veh':n,'rho_veh_km_lane':state.freeway_density[link][i],
                   'speed_kph':state.freeway_speed[link][i],'effective_lanes':state.freeway_effective_lanes[link][i]}
                  for i,n in enumerate(rows)] for link,rows in counts.items()}
    return {'FW_count_veh':{k:sum(v) for k,v in counts.items()},'cells':cells,'off_branch':off,
            'ramp_queue_veh':dict(state.ramp_queue)}


def run_endpoint(name,cfg,state,action,forecast,depth):
    from evaluation.controllers import area_runtime,route_choice_corridor
    from src.simulation import coupling
    from src.controllers.rollout_endpoint import ObjectiveSpec,evaluate_price_point
    private_state,private_action,private_forecast=deepcopy((state,action,forecast[:depth]))
    calls=[];original=coupling.freeway_substep;schedule=coupling.schedule_offramp_arrivals
    control_fields=('green_times','offsets','vsl','ramp_metering')
    def observe(current,control,demand,used_cfg,*args,**kwargs):
        assert used_cfg is cfg
        assert all(getattr(control,k)==getattr(action,k) for k in control_fields),'Held control was finalized differently'
        before=stock_view(current,cfg);value=original(current,control,demand,used_cfg,*args,**kwargs)
        diag=value[1];after=stock_view(current,cfg)
        groups={off:{'accepted_veh':float(diag['offramp_flow_'+off])*cfg.simulation.T_f_h,
                     'blocked_veh':float(diag['offramp_blocked_flow_'+off])*cfg.simulation.T_f_h,
                     'receiving_capacity_veh_h':kwargs['offramp_capacity_veh_h'][off]} for off in cfg.network.off_ramps}
        for off,row in groups.items():
            row['requested_veh']=row['accepted_veh']+row['blocked_veh']
            link=cfg.network.off_ramp_from_freeway[off];index=cfg.network.off_ramp_segment_index[off]
            row['gross_sending_veh']=row['requested_veh']/cfg.network.off_ramp_split_ratio[off]
            row['model_link']=link;row['model_cell_zero_based']=index
        calls.append({'end_sim_sec':state.time_sec+(len(calls)+1)*cfg.simulation.T_f_sec,
                      'groups':groups,'before_freeway':before,'after_freeway':after,'landings':{},
                      'lane_diagnostics':{k:v for k,v in diag.items() if 'lane' in k or 'spill' in k}})
        return value
    def observe_landing(current,used_cfg,off,vehicles,index):
        assert used_cfg is cfg
        ledger=current._control_area_ledger
        before={branch:ledger.flow_counts.get('offramp_'+branch+':'+off,0.) for branch in ('signal','direct')}
        value=schedule(current,used_cfg,off,vehicles,index)
        accepted={branch:ledger.flow_counts.get('offramp_'+branch+':'+off,0.)-before[branch] for branch in before}
        assert math.isclose(sum(accepted.values()),value[0],abs_tol=1e-9)
        assert abs(value[1])<1e-8
        calls[-1]['landings'][off]={**accepted,'accepted_total_veh':value[0],'rejected_veh':value[1]}
        if len(calls[-1]['landings'])==len(cfg.network.off_ramps):calls[-1]['after_landings']=stock_view(current,cfg)
        return value
    with patch.object(coupling,'freeway_substep',observe),patch.object(coupling,'schedule_offramp_arrivals',observe_landing):
        point=evaluate_price_point(private_state,private_action,private_forecast,[],
            ObjectiveSpec(cfg,depth_override=depth,box_walk=False,score_mode='raw'))
    assert not point.aborted and len(calls)==15*depth
    for last in point.states:last._control_area_ledger.assert_stocks(area_runtime.model_inventory(last,cfg))
    last=point.states[-1];area=dict(point.control_area);flows=area.pop('flow_counts')
    groups={off:{'requested_veh':sum(x['groups'][off]['requested_veh'] for x in calls),
        'accepted_veh':sum(x['groups'][off]['accepted_veh'] for x in calls),
        'blocked_veh':sum(x['groups'][off]['blocked_veh'] for x in calls),
        'accepted_signal_veh':sum(x['landings'][off]['signal'] for x in calls),
        'accepted_direct_veh':sum(x['landings'][off]['direct'] for x in calls)} for off in cfg.network.off_ramps}
    for off,row in groups.items():
        assert math.isclose(row['accepted_veh'],row['accepted_signal_veh']+row['accepted_direct_veh'],abs_tol=1e-8)
    cell_ttt=sum(sum(row['after_landings']['FW_count_veh'].values())*cfg.simulation.T_f_h for row in calls)
    return {'name':name,'horizon_sec':depth*150,'area':area,'controlled_freeway_cell_ttt_veh_h':cell_ttt,
            'area_non_freeway_cell_ttt_veh_h':area['ttt_veh_h']-cell_ttt,'global_legacy_freeway_ttt_veh_h':point.freeway_ttt,
            'global_legacy_urban_ttt_veh_h':point.urban_ttt,'final_omega_veh':sum(v['inside'] for v in last._control_area_ledger.stocks.values()),
            'final_stock':stock_view(last,cfg),'off_flows':groups,'route_completeness':route_choice_corridor.diagnostics(last,cfg),
            'stock_closure_valid':True,'held_control_equal_every_substep':True,'trace':calls,'flow_ledger':flows}


def main():
    os.environ['RW_MAINLINE_SG_ONLY']='1';os.environ['RW_OFFSET_WRITER']='experiment'
    start=time.monotonic();native=native_joint()
    sources=list((ROOT/'evaluation/controllers').glob('*.py'))+list((ROOT/'vendor/NumSim-mine/src').rglob('*.py'))
    sources += [CONFIG,NETWORK,DEC/'state_001200.json',DEC/'action_001050.json',DEC/'action_001200.json',Path(__file__)]
    sources += [ROOT/'diagnostics'/x for x in ('control_area_membership.json','physical_projection_support_635_proposal.json',
        'route_choice_corridor_ver2.json','route_choice_corridor_1128_ver2.json','native_internal_input_1091_ver2.json',
        'total_offramp_ratio_audit.json','static_route_matched_cohorts.json')]
    from diagnostics.probe_model_area_integration import build_projected,replay_provenance
    sources += [ROOT/'evaluation/parameters.json',ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json']
    before={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(sources))}
    before.update(replay_provenance(load(CONFIG),*sources))
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,route_choice_corridor
    from src.models.state import ControlAction
    from src.models.demand import DemandStep
    cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(CONFIG,DEC/'state_001200.json',DEC/'action_001050.json',fixture_inputs=False)
    calibration=adapter.deep_update(dict(adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))),tuning.get('calibration_override',{}))
    forecast=adapter.demand_from_state(raw,cfg,DemandStep,3,calibration,detectors)
    action=adapter.control_from_json(DEC/'action_001200.json',cfg,ControlAction)
    original=frozen((cfg,state,action,forecast));overlay={'schema':'diagnostic-joint-offroute-overlay/v1','native_sources':native,'arms':{}}
    results=[]
    for name in ('current','native_total_only','native_joint'):
        private=deepcopy(cfg)
        if name!='current':private.network.off_ramp_split_ratio={off:row['total_off'] for off,row in native.items()}
        if name=='native_joint':private.network.offramp_direct_share_by_offramp={off:row['direct_given_off'] for off,row in native.items()}
        fields={'off_ramp_split_ratio':dict(private.network.off_ramp_split_ratio),
                'offramp_direct_share_by_offramp':dict(private.network.offramp_direct_share_by_offramp)}
        overlay['arms'][name]={'private_network_fields':fields,'implied_joint':{off:{
            'direct':fields['off_ramp_split_ratio'][off]*fields['offramp_direct_share_by_offramp'][off],
            'signal':fields['off_ramp_split_ratio'][off]*(1-fields['offramp_direct_share_by_offramp'][off]),
            'through':1-fields['off_ramp_split_ratio'][off]} for off in native}}
        for depth in (1,3):results.append(run_endpoint(name,deepcopy(private),state,action,forecast,depth))
    assert original==frozen((cfg,state,action,forecast)),'Original cfg/state/action/demand mutated'
    changed=[key for key,value in before.items() if sha(ROOT/key)!=value]
    if changed:raise ValueError('Sources changed during sensitivity: '+str(changed))
    prefix={row['name']:row for row in results if row['horizon_sec']==150}
    for row in results:
        if row['horizon_sec']==450:assert row['trace'][:15]==prefix[row['name']]['trace']
    trace={row['name']+'_'+str(row['horizon_sec']):row.pop('trace') for row in results}
    physical={off:{branch:{'connector':spec[branch],
        'observed_connector_veh':raw['vehicle_records']['full_network_link_counts'].get(spec[branch],0),
        'model_projection':state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].get(spec[branch],{})}
        for branch in ('signal','direct')} for off,spec in GROUPS.items()}
    output={'schema':'native-joint-offroute-sensitivity/v1','initial_sim_sec':1200,'action_sim_sec':1200,
        'config':str(CONFIG.relative_to(ROOT)),'source_sha256':before,'source_changes':changed,'inputs_unchanged':True,
        'initial_physical_connector_counts_and_projection':physical,
        'initial_route_completeness':route_choice_corridor.diagnostics(state,cfg),'initial_stock':stock_view(state,cfg),
        'overlay':overlay,'results':results,'elapsed_sec':time.monotonic()-start,
        'limitations':['Conditional native source priors applied to grouped average model flux, not calibrated unconditional branch demand.',
            'Current physical branch stocks/actions/capacities/cell positions/forecast are identical; future signal/direct allocations change together only in native_joint.',
            'Inter-diverge merging cohorts and physical branch order remain unresolved in the current grouped off-ramp representation.',
            'Historical missing current routes are explicitly held; these endpoints are exploratory model sensitivity, not validated live performance.',
            'Reported direct/signal stock and capacity are model landing receivers, not necessarily one physical connector; initial physical counts/projection are supplied separately.',
            'Global freeway TTT includes legacy off/ramp bookkeeping; primary reported area TTT/TD uses the union ledger.']}
    for file,value in [('joint_offratio_private_overlay.json',overlay),('joint_offratio_sensitivity.json',output),('joint_offratio_sensitivity_trace.json',trace)]:
        (ROOT/'diagnostics'/file).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'elapsed_sec':output['elapsed_sec'],'source_changes':changed,'initial_route':output['initial_route_completeness'],
        'results':[{'name':r['name'],'seconds':r['horizon_sec'],'TTT':r['area']['ttt_veh_h'],'TD':r['area']['ttd_veh'],
                    'FW_N':r['final_stock']['FW_count_veh'],'E8':r['final_stock']['cells']['FW_E'][8],
                    'off_flows':r['off_flows']} for r in results]},indent=2))


if __name__=='__main__':main()
