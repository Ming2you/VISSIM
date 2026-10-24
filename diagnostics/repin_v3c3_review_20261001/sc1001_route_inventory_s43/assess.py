"""Assess the frozen route/SC1001 combination and cached native flow ledger."""
import csv
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
C=HERE.parent/'sc1001_connection'
F=HERE.parent/'sc1001_independent_s43'
pins={}


def data(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest();return raw


def read(path):
    raw=data(path)
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def rows(path):return list(csv.DictReader(data(path).decode('utf-8-sig').splitlines()))


def main():
    target=HERE/'assessment.json'
    if target.exists():raise FileExistsError(target)
    old=read(I/'closedloop_recorded2250_lever450_sc1001_shared_history_s43/summary.json')
    new=read(I/'closedloop_recorded2250_lever450_sc1001_routed_history_s43/summary.json')
    comp=read(HERE/'comparison.json')
    base_config=read(C/'candidate_config.json');route_config=read(C/'candidate_route_inventory.json')
    route_path=route_config['freeway'].pop('offramp_route_inventory')
    assert route_config==base_config
    from evaluation.controllers import offramp_routing
    contract=read(ROOT/route_path)
    mapping=read(ROOT/contract['mapping']['path'])
    runtime=offramp_routing.compile_inventory(contract,mapping)
    assert hashlib.sha256(data(ROOT/contract['network']['path'])).hexdigest()==contract['network']['sha256']
    prior_flow=read(F/'freeway_flow_ledger.json')
    native_decomp=read(I/'seed43_fullplant_20260929/decomposition.json')
    arm_keys=(('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both'))
    native_windows={};report={};initial_cells=None;resource_max=route_max=0.
    signed={'source_admissions':1,'ramp_merges':1,'off_departures':-1,'terminal_exits_inferred':-1}
    for index,(arm,key) in enumerate(arm_keys):
        a,b=old['results'][key],new['results'][key]
        assert a['commands']==b['commands'] and a['physical_cell_states'][0]==b['physical_cell_states'][0]
        trace=read(C/f'sc1001_routed_history_s43_response_{index}.json.gz')
        assert len(trace['quantities']['owners'])==17
        resource_max=max(resource_max,trace['resource_max_exceedance'])
        for state in trace['route_inventory_checks']:
            route_max=max(route_max,max(x['max_cell_residual'] for x in state['roads'].values()))
        if initial_cells is None:initial_cells=trace['route_inventory_checks'][0]['route_stock']['cells']['FW_E']
        else:assert initial_cells==trace['route_inventory_checks'][0]['route_stock']['cells']['FW_E']
        flows=b['control_area']['flow_counts']
        off={c:flows['freeway:FW_E->storage:'+node] for c,node in
             {'10481':'OR_D_E_storage','10483':'lane_off_10483','10643':'OR_F_E_storage','10682':'lane_off_10682'}.items()}
        actual=prior_flow['arms'][arm]['native_off']
        cost=b['cost_by_stock'];before=a['cost_by_stock']
        report[arm]=dict(direct_off={c:dict(native=actual[c],before=prior_flow['arms'][arm]['predicted_off'][c],after=off[c])
                                     for c in ('10682','10483')},
            all_off_count_before=sum(prior_flow['arms'][arm]['predicted_off'].values()),
            all_off_count_after=sum(off.values()),all_off_native=sum(actual.values()),
            east_ttt=dict(native=native_decomp['arms'][arm]['native_30s_veh_h']['FW_E'],
                          before=before['freeway:FW_E'],after=cost['freeway:FW_E']),
            end_east_n=trace['route_inventory_checks'][-1]['roads']['FW_E']['total_veh'],
            resource_np=sum(x['net_inflow_veh'] for x in trace['quantities']['owners'].values()),
            resource_nuf=trace['quantities']['predicted_ramp_merge']['total_rate_veh_h'])
        folder=ROOT.parent/'control-full-review/diagnostics'/(
            'dsd110_20260923/response_recalibration_20260924/gain_response/seed43/none' if arm=='nc'
            else f'metanet_net_gain_goal_20260924/heldout43/observations/{arm}')
        path=folder/'flows_30s.csv'
        raw=rows(path)
        assert pins[str(path)]==prior_flow['source_pins'][str(path)]
        selected=[x for x in raw if x['road']=='FW_E' and float(x['window_start_s'])>=2250.1-1e-7
                  and float(x['window_end_s'])<=2700.1+1e-7]
        windows={}
        for row in selected:
            t=float(row['window_start_s']);w=windows.setdefault(t,dict(start=t,end=float(row['window_end_s']),
                start_n=0.,end_n=0.,**{k:0. for k in signed}))
            for k in signed:w[k]+=float(row[k])
            w['start_n']+=float(row['start_n_veh']);w['end_n']+=float(row['end_n_veh'])
            assert all(float(row[k])==0 for k in ('unexplained_entries','unexplained_losses','native_removals','conservation_residual_veh'))
        assert len(windows)==15 and len(selected)==465
        native_windows[arm]=windows
    assert resource_max<1e-7 and route_max<1e-7
    decomposition={}
    for arm in ('rm','vsl','both'):
        cumulative={k:0. for k in signed};integrals={k:0. for k in signed}
        first_source=None;actual_ttt=0.;time_rows=[]
        for t,w in sorted(native_windows[arm].items()):
            ref=native_windows['nc'][t];duration=(w['end']-t)/3600
            assert w['end']==ref['end']
            if first_source is None and w['source_admissions']!=ref['source_admissions']:first_source=[t,w['end']]
            assert abs(sum(cumulative.values())-(w['start_n']-ref['start_n']))<1e-9
            for k,sign in signed.items():
                change=sign*(w[k]-ref[k]);integrals[k]+=(cumulative[k]+change/2)*duration;cumulative[k]+=change
            assert abs(sum(cumulative.values())-(w['end_n']-ref['end_n']))<1e-9
            actual_ttt+=(w['start_n']-ref['start_n']+w['end_n']-ref['end_n'])*.5*duration
            time_rows.append(dict(start=t,end=w['end'],cumulative_stock_contributions=dict(cumulative),
                                  cumulative_ttt_contributions=dict(integrals)))
        assert abs(sum(integrals.values())-actual_ttt)<1e-9
        assert abs(actual_ttt-(native_decomp['arms'][arm]['native_30s_veh_h']['FW_E']-
                               native_decomp['arms']['nc']['native_30s_veh_h']['FW_E']))<1e-9
        decomposition[arm]=dict(ttt_veh_h=actual_ttt,contributions_veh_h=integrals,
            first_different_admission_bin=first_source,intervals=time_rows,
            interpretation='Exact30s stock-accounting identity, NOT causal source removal or a matched-demand counterfactual.')
    history={}
    recording=Path('D:/VISSIM_runs/20260929_seed43_observation2700/nc/decisions_sdmpc31_nc2700_s43')
    for t in (1800,1950,2100,2250):
        derived=read(recording/f'obs150/derived_{t:06d}.json')
        history[t]={c:derived['off_split'][c] for c in ('10682','10483')}
    initial={}
    for off in ('10682','10483'):
        cell=runtime['branches'][off]['source_cell'];stock=initial_cells[cell]
        target_stock=math.fsum(v for k,v in stock.items() if k.rsplit('|',1)[1]==off)
        assert target_stock==0 and all(k.startswith('observed_route:') for k in stock)
        initial[off]=dict(cell=cell,total=sum(stock.values()),target_stock=target_stock,route_classes=stock,
                          fixed_past_ratio=history[2250][off]['ratio'])
    assert runtime['merges']['RM_C10639']['weights'].get('10682',0)==0
    result=dict(status='ROUTE_CONSERVATION_IMPROVES_OFF_COUNTS_NOT_GAIN_QUALIFIED',cases=report,
        ranking=comp['omega_rank'],native_regret_veh_h=comp['selected_native_regret_veh_h'],
        marginal_costs={a:r['delta_vs_nc'] for a,r in comp['costs'].items()},
        native_east_ttt_flow_decomposition=decomposition,causal_past_splits=history,
        current_exit_cells=initial,compiled_merges=runtime['merges'],max_route_partition_residual=route_max,
        max_resource_exceedance=resource_max,completed_forecasts=4,
        compute_sec=sum(x['wall_sec'] for x in new['results'].values()),optimizer_iterations=0,new_native=0,fitting=0,
        limitations=['Existing seed43, not a new holdout.','0.1s native phase difference; no future flow injected.',
            'Source and routing are physically coupled: subtracting an accounting term is not a causal effect.',
            'No global coefficient change or new capacity/VSL reward.','Other network native deletions and missing uninserted waiting remain from prior comparison.'],
        source_pins=pins)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=report,flow_components={a:r['contributions_veh_h'] for a,r in decomposition.items()},
        rank=comp['omega_rank'],regret=comp['selected_native_regret_veh_h'],seconds=result['compute_sec']),ensure_ascii=False))


def rm47_ledger():
    """Read six completed native observation bundles; no model or FZP read."""
    from evaluation.controllers import obs150_contract as oc,offramp_routing
    from evaluation.controllers.obs150_observation import check_rule_crosscheck
    target=HERE/'native_rm47_flow_ledger.json'
    if target.exists():raise FileExistsError(target)
    proof=read(I/'native_rm_observation2700_writerfix_v3/analysis/summary.json')
    assert proof['paired_prefix_exact'] and all(a['native_execution_passed'] for a in proof['arms'].values())
    ramp_audit=read(I/'closedloop_recorded2700_lever450_rm_pair_s47_cell23_v4/ramp_response_audit.json')
    contract=read(I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first/route_inventory/contract.json')
    runtime=offramp_routing.compile_inventory(contract,read(ROOT/contract['mapping']['path']))
    links={int(k) for k,v in runtime['physical'].items() if v[0]=='FW_E'}
    ramps=[k for k,v in runtime['merges'].items() if v['freeway']=='FW_E']
    exits=[k for k,v in runtime['branches'].items() if v['freeway']=='FW_E']
    def count(raw):
        assert raw['vehicle_records']['complete']
        return sum(int(v['link_no']) in links for v in raw['vehicle_records']['records'])
    native={}
    for arm in ('hold','release'):
        directory=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3')/arm/f'decisions_sdmpc31_g_2700_{arm}_s47'
        previous=read(directory/'state_002700.json');windows=[]
        for wi,sec in enumerate((2850,3000,3150)):
            raw=read(directory/f'state_{sec:06d}.json');obs=raw[oc.RAW_STATE_KEY]
            detectors,_=oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
            oc.validate_raw(obs,detectors,expected_simres=oc.EXPECTED_SIMRES);check_rule_crosscheck(obs,detectors)
            bundle=oc.load_bundle(raw)
            boundary=oc.evaluate_boundaries(obs,detectors,bundle.frame_end,bundle.frame_start,bundle.err_rows)
            removed=oc.window_removals(bundle.err_rows,sec-150,sec)
            row=dict(start=sec-150,end=sec,initial=count(previous),final=count(raw),
                source=boundary['source:FW_E'].cross,terminal=boundary['chain_end:FW_E'].cross,
                merge=sum(ramp_audit['arms'][arm][r]['actual']['windows'][wi]['merge'] for r in ramps),
                off=sum(boundary['off_entry:'+r].cross for r in exits),
                removed=sum(int(v['link']) in links for v in removed))
            row['residual']=row['final']-(row['initial']+row['source']+row['merge']-row['off']-row['terminal']-row['removed'])
            assert row['residual']==0,(arm,sec,row)
            windows.append(row);previous=raw
        native[arm]=windows
    assert native['hold'][0]['initial']==native['release'][0]['initial']
    signs=dict(source=1,merge=1,off=-1,terminal=-1,removed=-1)
    cumulative={k:0. for k in signs};integrals={k:0. for k in signs};deltas=[]
    for a,b in zip(native['hold'],native['release']):
        changes={k:b[k]-a[k] for k in signs}
        for k,sign in signs.items():
            change=sign*changes[k];integrals[k]+=(cumulative[k]+change/2)*(a['end']-a['start'])/3600;cumulative[k]+=change
        assert abs(sum(cumulative.values())-(b['final']-a['final']))<1e-9
        deltas.append(dict(start=a['start'],end=a['end'],counts=changes,
                          stock_contributions=dict(cumulative),ttt_contributions=dict(integrals)))
    result=dict(native=native,release_minus_hold=deltas,ttt150_contributions_veh_h=integrals,
        ttt150_delta_veh_h=sum(integrals.values()),native_omega5s_delta_veh_h=proof['delta_TTT_veh_h'],
        source_pins=pins,new_forecasts=0,new_native=0,fzp_reads=0,
        scope='Exact integer150s observation boundary/stock ledger; trapezoid cost is coarse and differs from5sFZP cost.',
        limitations=['Stock-accounting identity, not an isolated causal contribution.',
                     'Source admission variation is not assigned to generation versus receiving.',
                     'Observed future data is evaluation only, never an autonomous model input.'])
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(contributions=integrals,windows=deltas,ttt150=result['ttt150_delta_veh_h']),ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1:]==['--rm47-ledger']:rm47_ledger()
    elif not sys.argv[1:]:main()
    else:raise SystemExit('usage: assess.py [--rm47-ledger]')
