import ast
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}

def read(path):
    raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def main():
    assert not (HERE/'assessment.json').exists()
    previous=read(HERE.parent/'retained10638/assessment.json')
    for path,h in read(HERE/'executed_sources.json').items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
    cfg=read(HERE/'candidate_config.json');oldcfg=read(HERE.parent/'retained10638/candidate_config.json')
    manifest=read(ROOT/cfg['freeway']['lane_plant']);oldmanifest=read(ROOT/oldcfg['freeway']['lane_plant'])
    protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    oldprotocol=read(ROOT/oldmanifest['sources']['reference_protocol']['path'])
    calibration=protocol.pop('calibrated_discretionary_exchange')
    assert protocol['history_exchange'] is True and oldprotocol['history_exchange'] is False
    protocol['history_exchange']=False;assert protocol==oldprotocol
    manifest['sources']['reference_protocol']=oldmanifest['sources']['reference_protocol'];assert manifest==oldmanifest
    cfg['freeway']['lane_plant']=oldcfg['freeway']['lane_plant'];assert cfg==oldcfg
    cases={};wall=mass=route=resource=0.
    for seed,now,old in [('47','exchange47_v3','retained47_v2'),('43','exchange43_v3','retained43')]:
        prefix='closedloop_recorded2700_select_check_trace10681_' if seed=='47' else 'closedloop_recorded2250_lever450_trace10681_'
        folder=I/(prefix+now);before_folder=I/(prefix+old)
        summary=read(folder/'summary.json');old_summary=read(before_folder/'summary.json')
        assert not summary['future_observation_inputs'] and not summary['native_started']
        cases[seed]={}
        for key,r in summary['results'].items():
            arm=('hold' if seed=='47' else 'nc') if key=='held_actual' else key
            assert r['commands']==old_summary['results'][key]['commands']
            trace=read(folder/(key+'_RM_C10681_trace.json.gz'))
            old_trace=read(before_folder/(key+'_RM_C10681_trace.json.gz'))
            ports=trace['offramp_network_diagnostics'];local=trace['local_receiver_diagnostics']
            assert ports['states'][0]==old_trace['offramp_network_diagnostics']['states'][0]
            assert trace['mainline_diagnostics']['initial_and_block_states'][0]==old_trace['mainline_diagnostics']['initial_and_block_states'][0]
            assert local['states'][0]==old_trace['local_receiver_diagnostics']['states'][0]
            route=max(route,max(c['max_cell_residual'] for c in r['offramp_route_inventory_checks']))
            resource=max(resource,max(c['exceedance_veh'] for c in local['resources']))
            exchange={}
            for item in local['resources']:
                if item['kind']!='lane_urban_receiving':continue
                target=ast.literal_eval(item['resource'])
                for text,n in item['accepted_by_source_veh'].items():
                    source=ast.literal_eval(text)
                    if (source[0]==target[0]==71 and source[2]==target[2]
                            and {source[1],target[1]}=={4,5}):
                        name=f'{source[1]}->{target[1]}'
                        exchange[name]=exchange.get(name,0.)+n
            assert exchange.get('4->5',0)>0, 'Configured exchange had no actual transport'
            port_result={}
            for off,p in ports['states'][-1]['ports'].items():
                prior=previous['cases'][seed][arm]['ports'][off]
                port_result[off]=dict(native=prior['native'],before=prior['after'],after=dict(entry=p['admitted'],drain=p['departed'],final_stock=p['stock']))
                mass=max(mass,abs(p['stock']-p['initial']-p['admitted']+p['departed']))
            costs=dict(native_delta=previous['cases'][seed][arm]['costs']['native_delta'],
                before_delta=previous['cases'][seed][arm]['costs']['after_delta'],
                after_delta=r['ttt_omega_veh_h']-summary['results']['held_actual']['ttt_omega_veh_h'],
                after_omega=r['ttt_omega_veh_h'],after_outside=r['tracked_outside_residence_veh_h'])
            cases[seed][arm]=dict(ports=port_result,exchange_vehicles=exchange,costs=costs)
            wall+=r['wall_sec']
    assert max(mass,route,resource)<1e-7
    out=dict(status='COMPLETED_BOUNDED_EXCHANGE_EVALUATION_NOT_GAIN_QUALIFIED',cases=cases,
        forecasts=6,wall_sec=wall,max_mass_residual=mass,max_route_residual=route,max_resource_exceedance=resource,
        calibration=calibration,source_pins=pins,new_native=0,new_fzp_scan=0,coefficient_grid=0,goal_complete=False)
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for seed,arms in cases.items():
        for arm,r in arms.items():print(seed,arm,'10643',r['ports']['10643'],'exchange',r['exchange_vehicles'],'cost',r['costs'])
    print('WALL',wall,'MASS',mass,'ROUTE',route,'RESOURCE',resource)

if __name__=='__main__':main()
