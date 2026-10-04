import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}

def read(p):
    raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)

def main():
    target=HERE/'assessment.json'
    if target.exists():raise FileExistsError(target)
    baseline=read(HERE.parent/'unrouted10646/assessment.json')
    for p,digest in read(HERE/'executed_sources.json').items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
    beforecfg=read(HERE.parent/'unrouted10646/candidate_config.json');cfg=read(HERE/'candidate_config.json')
    oldm=read(ROOT/beforecfg['freeway']['lane_plant']);newm=read(ROOT/cfg['freeway']['lane_plant'])
    oldp=read(ROOT/oldm['sources']['reference_protocol']['path']);newp=read(ROOT/newm['sources']['reference_protocol']['path'])
    assert oldp['unrouted_continuation'] is False and newp['unrouted_continuation'] is True
    newp['unrouted_continuation']=False;assert newp==oldp
    newm['sources']['reference_protocol']=oldm['sources']['reference_protocol'];assert newm==oldm
    cfg['freeway']['lane_plant']=beforecfg['freeway']['lane_plant'];assert cfg==beforecfg
    cases={};wall=resource=mass=route=0.
    for seed,label in [('47','retained47_v2'),('43','retained43')]:
        prefix=('closedloop_recorded2700_select_check_trace10681_' if seed=='47'
                else 'closedloop_recorded2250_lever450_trace10681_')
        folder=I/(prefix+label);summary=read(folder/'summary.json')
        before=read(I/(prefix+'unrouted'+seed)/'summary.json')
        cases[seed]={}
        assert not summary['future_observation_inputs'] and not summary['native_started']
        for key,row in summary['results'].items():
            arm=('hold' if key=='held_actual' else key) if seed=='47' else ('nc' if key=='held_actual' else key)
            assert row['commands']==before['results'][key]['commands']
            wall+=row['wall_sec']
            trace=read(folder/(key+'_RM_C10681_trace.json.gz'))
            oldtrace=read(I/(prefix+'unrouted'+seed)/(key+'_RM_C10681_trace.json.gz'))
            ports=trace['offramp_network_diagnostics'];local=trace['local_receiver_diagnostics']
            assert ports['states'][0]==oldtrace['offramp_network_diagnostics']['states'][0]
            assert trace['mainline_diagnostics']['initial_and_block_states'][0]==oldtrace['mainline_diagnostics']['initial_and_block_states'][0]
            assert all(s['continuation'] for s in local['states'])
            route=max(route,max(r['max_cell_residual'] for r in row['offramp_route_inventory_checks']))
            resource=max(resource,max(r['exceedance_veh'] for r in local['resources']))
            result={}
            for off,p in ports['states'][-1]['ports'].items():
                old=baseline['cases'][seed][arm]['ports'][off]
                result[off]=dict(native=old['native'],before=old['after'],after=dict(
                    entry=p['admitted'],drain=p['departed'],final_stock=p['stock']))
                mass=max(mass,abs(p['stock']-p['initial']-p['admitted']+p['departed']))
            pending=[]
            for s,portsnap in zip(local['states'],ports['states']):
                tags=sum(p['vehicles'] for p in s['off10638_routes'])
                assert abs(tags-portsnap['ports']['10638']['stock'])<1e-7
                pending.append(dict(time_sec=s['time_sec'],off10638_tagged=tags,
                    unassigned_ready=sum(p['vehicles'] for q in s['unrouted_pending'] for p in q['packets']),
                    unassigned_travelling=sum(p['vehicles'] for p in s['arrival_tags'] if p['movement'] is None)))
            cases[seed][arm]=dict(ports=result,mae={stage:{f:sum(abs(p[stage][f]-p['native'][f]) for p in result.values())/8
                for f in ('entry','drain','final_stock')} for stage in ('before','after')},
                costs=dict(before_omega=before['results'][key]['ttt_omega_veh_h'],after_omega=row['ttt_omega_veh_h'],
                    before_delta=before['results'][key]['ttt_omega_veh_h']-before['results']['held_actual']['ttt_omega_veh_h'],
                    after_delta=row['ttt_omega_veh_h']-summary['results']['held_actual']['ttt_omega_veh_h'],
                    native_delta=baseline['cases'][seed][arm]['costs']['native_delta_omega']),
                pending=pending,model_last_local=local['states'][-1])
    assert max(route,resource,mass)<1e-7
    result=dict(status='RETAINED_ROUTE_CONNECTED_GAIN_NOT_QUALIFIED',cases=cases,forecasts=6,wall_sec=wall,
                max_port_mass_residual=mass,max_route_residual=route,max_local_resource_exceedance=resource,
                source_pins=pins,fit=0,new_native=0,new_fzp_scan=0,optimizer=0,goal_complete=False)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    for seed,arms in cases.items():
        for arm,row in arms.items():print(seed,arm,'10643',row['ports']['10643'],'mae',row['mae'],'cost',row['costs'])
    print('wall',wall,'mass',mass,'route',route,'resource',resource)

if __name__=='__main__':main()
