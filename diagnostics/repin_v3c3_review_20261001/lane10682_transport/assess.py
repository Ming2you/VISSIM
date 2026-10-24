"""Six bounded forecasts: paired native flow/storage and local recovery gates."""
import gzip
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}
def read(p):
    data=p.read_bytes();PINS[str(p)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)

def main():
    assert sys.argv[1:] in ([],['--multilane'])
    multi=bool(sys.argv[1:])
    output_path=HERE/('assessment_multilane.json' if multi else 'assessment.json')
    assert not output_path.exists()
    baseline_evidence=read(HERE.parent/'compatible71/assessment.json')
    native_speeds=read(HERE.parent/'entry10682/spatial.json')
    basecfg=read(HERE.parent/'retained10638/candidate_config.json')
    cfg=read(HERE/('candidate_multilane.json' if multi else 'candidate_config.json'));region=cfg['freeway'].pop('route_lane_regions')
    assert cfg==basecfg
    cases={};wall=mass=route=resource=0.;n=0
    for seed,label,previous in [('43','lane10682_transport_43v2','retained43'),
                               ('47','lane10682_transport_47v3','entry10643')]:
        prefix='closedloop_recorded2250_lever450_trace10681_' if seed=='43' else 'closedloop_recorded2700_select_check_trace10681_'
        if multi:label='lane10682_transport_multi'+seed
        folder=I/(prefix+label);old=I/(prefix+previous)
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
                native=baseline_evidence['cases'][seed][arm]['ports'][off]['native']
                oldp=old_tr['offramp_network_diagnostics']['states'][-1]['ports'][off]
                ports[off]=dict(native=native,
                    before=dict(entry=oldp['admitted'],drain=oldp['departed'],final_stock=oldp['stock']),
                    after=dict(entry=p['admitted'],drain=p['departed'],final_stock=p['stock']))
                mass=max(mass,abs(p['initial']+p['admitted']-p['departed']-p['stock']))
            speeds=[]
            if name=='held_actual':
                true=native_speeds['cases'][seed+'_'+arm]['rows']
                for old_state,new_state in zip(old_tr['mainline_diagnostics']['initial_and_block_states'],tr['mainline_diagnostics']['initial_and_block_states']):
                    assert old_state['time_sec']==new_state['time_sec']
                    for c in (9,10,11,12):
                        obs=next(x for x in true if x['time_sec']==new_state['time_sec'] and x['cell']==c)
                        speeds.append(dict(time_sec=new_state['time_sec'],cell=c,native=obs['native_mean_speed'],
                            before=old_state['speed'][c],after=new_state['speed'][c]))
            costs=dict(native_delta=baseline_evidence['cases'][seed][arm]['costs']['native_delta'],
                before_delta=before['ttt_omega_veh_h']-base['results']['held_actual']['ttt_omega_veh_h'],
                after_delta=result['ttt_omega_veh_h']-summary['results']['held_actual']['ttt_omega_veh_h'],
                after_omega=result['ttt_omega_veh_h'],before_omega=before['ttt_omega_veh_h'],
                after_outside=result['tracked_outside_residence_veh_h'],before_outside=before['tracked_outside_residence_veh_h'])
            cases[seed][arm]=dict(ports=ports,speeds=speeds,costs=costs,
                mae={stage:{f:sum(abs(p[stage][f]-p['native'][f]) for p in ports.values())/8
                    for f in ('entry','drain','final_stock')} for stage in ('before','after')},
                ramps_before=before['ramps'],ramps_after=result['ramps'],
                stock_costs_before=before['cost_by_stock'],stock_costs_after=result['cost_by_stock'])
            n+=1;wall+=result['wall_sec']
            print(seed,arm,'10682',ports['10682'],'10643',ports['10643'],'COSTS',costs,flush=True)
            if speeds:print('END_SPEEDS',speeds[-4:],flush=True)
    assert n==6 and max(mass,route,resource)<1e-7
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    stop_sha=hashlib.sha256(stop.read_bytes()).hexdigest()
    assert stop_sha=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    output=dict(status='completed_one_lane_transport_candidate_pending_decision',cases=cases,forecasts=n,wall_sec=wall,
        mass_residual=mass,route_residual=route,resource_exceedance=resource,source_pins=PINS,
        region=region,stop_sha256=stop_sha,new_native=0,new_fzp_scans=0,goal_complete=False,
        limitations=['Previously examined43/47 states, not fresh blind holdouts.',
        '47 pair changes city signals, not RM. No optimizer or controller qualification.',
        'Current inlet target/lane shares frozen; exchange rates from independent29 cache endpoints.',
        'Commands are prescribed; future native traffic states are not prediction inputs.'])
    output_path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('SIX_COMPLETE',wall,mass,route,resource)
if __name__=='__main__':main()
