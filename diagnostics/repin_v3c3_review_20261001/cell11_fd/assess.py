"""Compare one frozen FD candidate to six completed conserved baselines."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(path):
    raw=path.read_bytes();PINS[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def main():
    assert not (HERE/'assessment.json').exists()
    fit=read(HERE/'fit.json')
    base_manifest=read(HERE.parent/'retained10638/candidate_manifest.json')
    cfg=read(HERE/'candidate_config.json');base_cfg=read(HERE.parent/'retained10638/candidate_config.json')
    manifest=read(ROOT/cfg['freeway']['lane_plant'])
    ref=read(ROOT/manifest['sources']['reference_config']['path'])
    before_ref=read(ROOT/base_manifest['sources']['reference_config']['path'])
    assert abs(ref['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']*1.4-fit['candidate_effective_critical'])<1e-10
    ref['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']=before_ref['freeway']['physical_cell_fd']['FW_E']['11']['rho_crit']
    assert ref==before_ref,'More than one coefficient changed'
    manifest['sources']['reference_config']=base_manifest['sources']['reference_config']
    manifest['qualification']=base_manifest['qualification'];assert manifest==base_manifest
    cfg['freeway']['lane_plant']=base_cfg['freeway']['lane_plant'];assert cfg==base_cfg
    baseline_evidence=read(HERE.parent/'compatible71/assessment.json')
    native_speeds=read(HERE.parent/'entry10682/spatial.json')
    cases={};wall=mass=route=resource=0.;n=0
    for seed,previous in [('43','retained43'),('47','entry10643')]:
        prefix='closedloop_recorded2250_lever450_trace10681_' if seed=='43' else 'closedloop_recorded2700_select_check_trace10681_'
        folder=I/(prefix+'cell11_fd_'+seed);old=I/(prefix+previous)
        summary=read(folder/'summary.json');base=read(old/'summary.json')
        assert not summary['future_observation_inputs'] and not summary['native_started']
        assert set(summary['results'])==set(base['results'])
        cases[seed]={}
        for name,result in summary['results'].items():
            before=base['results'][name]
            arm=('nc' if seed=='43' else 'hold') if name=='held_actual' else name
            assert result['commands']==before['commands']
            tr=read(folder/(name+'_RM_C10681_trace.json.gz'))
            old_tr=read(old/(name+'_RM_C10681_trace.json.gz'))
            for k in ('offramp_network_diagnostics','local_receiver_diagnostics'):
                assert tr[k]['states'][0]==old_tr[k]['states'][0]
            assert tr['initial_stock']==old_tr['initial_stock'] and tr['initial_buffer']==old_tr['initial_buffer']
            assert tr['mainline_diagnostics']['initial_and_block_states'][0]==old_tr['mainline_diagnostics']['initial_and_block_states'][0]
            route=max(route,max(x['max_cell_residual'] for x in result['offramp_route_inventory_checks']))
            resource=max(resource,max(x['exceedance_veh'] for x in tr['local_receiver_diagnostics']['resources']))
            ports={}
            for off,p in tr['offramp_network_diagnostics']['states'][-1]['ports'].items():
                native=baseline_evidence['cases'][seed][arm]['ports'][off]
                ports[off]=dict(native=native['native'],before=native['before'],after=dict(entry=p['admitted'],drain=p['departed'],final_stock=p['stock']))
                mass=max(mass,abs(p['initial']+p['admitted']-p['departed']-p['stock']))
            speeds=[]
            if name=='held_actual':
                true=native_speeds['cases'][seed+'_'+arm]['rows']
                for old_state,new_state in zip(old_tr['mainline_diagnostics']['initial_and_block_states'],tr['mainline_diagnostics']['initial_and_block_states']):
                    assert old_state['time_sec']==new_state['time_sec']
                    for c in (9,10,11,12):
                        obs=next(x for x in true if x['time_sec']==new_state['time_sec'] and x['cell']==c)
                        speeds.append(dict(time_sec=new_state['time_sec'],cell=c,native=obs['native_mean_speed'],before=old_state['speed'][c],after=new_state['speed'][c]))
            costs=dict(native_delta=baseline_evidence['cases'][seed][arm]['costs']['native_delta'],
                before_delta=before['ttt_omega_veh_h']-base['results']['held_actual']['ttt_omega_veh_h'],
                after_delta=result['ttt_omega_veh_h']-summary['results']['held_actual']['ttt_omega_veh_h'],
                after_omega=result['ttt_omega_veh_h'],before_omega=before['ttt_omega_veh_h'],
                after_outside=result['tracked_outside_residence_veh_h'],before_outside=before['tracked_outside_residence_veh_h'])
            cases[seed][arm]=dict(ports=ports,speeds=speeds,costs=costs,ramps_before=before['ramps'],ramps_after=result['ramps'],
                stock_costs_before=before['cost_by_stock'],stock_costs_after=result['cost_by_stock'])
            n+=1;wall+=result['wall_sec']
            print(seed,arm,'10682',ports['10682'],'COSTS',costs)
            if speeds:print('END_SPEEDS',speeds[-4:])
    assert n==6 and max(mass,route,resource)<1e-7
    core=read(HERE.parent/'entry10682/verification.json')
    for path,h in core['production_unchanged'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()==core['stop_sha256']
    output=dict(status='completed_one_fd_candidate_pending_adoption_decision',cases=cases,forecasts=n,wall_sec=wall,
        mass_residual=mass,route_residual=route,resource_exceedance=resource,source_pins=PINS,
        production_unchanged=core['production_unchanged'],stop_sha256=core['stop_sha256'],new_native=0,new_fzp_scans=0,goal_complete=False,
        limitations=['Seed43/47 have been examined before; this is cross-state checking, not a new blind holdout.',
        'Seed47 pair changes city signals, not RM/VSL; RM gain qualification still requires the existing hold/release case.'])
    (HERE/'assessment.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SIX_COMPLETE',wall,mass,route,resource)


if __name__=='__main__':main()
