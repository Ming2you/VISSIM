import ast
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)


def lane_totals(local):
    out=Counter()
    for c in local['cells']:out['%s:%s'%tuple(c['cell'][:2])]+=c['stock']
    return dict(out)


def lateral(local):
    out=Counter()
    for r in local['resources']:
        if r['kind']!='lane_urban_receiving':continue
        target=ast.literal_eval(r['resource'])
        for k,n in r['accepted_by_source_veh'].items():
            source=ast.literal_eval(k)
            if source[0]==target[0]==71 and source[2]==target[2] and source[1]!=target[1]:
                out[f'{source[1]}->{target[1]}']+=n
    return dict(out)


def main():
    assert not (HERE/'assessment.json').exists()
    for p,h in read(HERE/'executed_sources.json').items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    native=read(HERE.parent/'retained10638/assessment.json')
    cfg=read(HERE/'candidate_config.json');base_cfg=read(HERE.parent/'retained10638/candidate_config.json')
    manifest=read(ROOT/cfg['freeway']['lane_plant']);base_manifest=read(ROOT/base_cfg['freeway']['lane_plant'])
    protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    base_protocol=read(ROOT/base_manifest['sources']['reference_protocol']['path'])
    fit=protocol.pop('compatible_71_balance');assert protocol==base_protocol
    manifest['sources']['reference_protocol']=base_manifest['sources']['reference_protocol'];assert manifest==base_manifest
    cfg['freeway']['lane_plant']=base_cfg['freeway']['lane_plant'];assert cfg==base_cfg
    cases={};wall=mass=route=resource=0.
    for seed,old in [('47','entry10643'),('43','retained43')]:
        prefix='closedloop_recorded2700_select_check_trace10681_' if seed=='47' else 'closedloop_recorded2250_lever450_trace10681_'
        folder=I/(prefix+'compatible71_'+seed);before=I/(prefix+old)
        summary=read(folder/'summary.json');base=read(before/'summary.json')
        assert not summary['future_observation_inputs'] and not summary['native_started']
        cases[seed]={}
        for key,r in summary['results'].items():
            arm=('hold' if seed=='47' else 'nc') if key=='held_actual' else key
            assert r['commands']==base['results'][key]['commands']
            tr=read(folder/(key+'_RM_C10681_trace.json.gz'));old_tr=read(before/(key+'_RM_C10681_trace.json.gz'))
            for field in ('offramp_network_diagnostics','local_receiver_diagnostics'):
                assert tr[field]['states'][0]==old_tr[field]['states'][0]
            assert tr['mainline_diagnostics']['initial_and_block_states'][0]==old_tr['mainline_diagnostics']['initial_and_block_states'][0]
            route=max(route,max(c['max_cell_residual'] for c in r['offramp_route_inventory_checks']))
            local=tr['local_receiver_diagnostics'];resource=max(resource,max(c['exceedance_veh'] for c in local['resources']))
            exchange=lateral(local);assert exchange.get('4->5',0)>0
            ports={}
            for off,p in tr['offramp_network_diagnostics']['states'][-1]['ports'].items():
                ref=native['cases'][seed][arm]['ports'][off]
                ports[off]=dict(native=ref['native'],before=ref['after'],after=dict(entry=p['admitted'],drain=p['departed'],final_stock=p['stock']))
                mass=max(mass,abs(p['stock']-p['initial']-p['admitted']+p['departed']))
            cases[seed][arm]=dict(ports=ports,lateral_all71=exchange,lateral_all71_before=lateral(old_tr['local_receiver_diagnostics']),
                local_final_before=lane_totals(old_tr['local_receiver_diagnostics']['states'][-1]),local_final_after=lane_totals(local['states'][-1]),
                costs=dict(native_delta=native['cases'][seed][arm]['costs']['native_delta'],before_delta=native['cases'][seed][arm]['costs']['after_delta'],
                    after_delta=r['ttt_omega_veh_h']-summary['results']['held_actual']['ttt_omega_veh_h'],after_omega=r['ttt_omega_veh_h'],after_outside=r['tracked_outside_residence_veh_h']))
            wall+=r['wall_sec']
    assert max(mass,route,resource)<1e-7
    out=dict(status='completed_single_state_conditioned_candidate_not_gain_qualified',cases=cases,wall_sec=wall,
        max_mass_residual=mass,max_route_residual=route,max_resource_exceedance=resource,calibration=fit,
        source_pins=PINS,full_forecasts=6,new_native=0,new_fzp_scan=0,coefficient_grids=0,goal_complete=False)
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for seed,arms in cases.items():
        for arm,r in arms.items():print(seed,arm,'10643',r['ports']['10643'],'EXCHANGE',r['lateral_all71'],'COST',r['costs'],'STOCK',r['local_final_after'])
    print('WALL',wall,'MASS',mass,'ROUTE',route,'RESOURCE',resource)


if __name__=='__main__':main()
