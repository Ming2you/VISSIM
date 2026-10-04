"""Compare completed native-routing candidate with its frozen routed baseline."""
import ast
import gzip
import hashlib
import importlib.machinery
import importlib.util
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
    before=read(HERE.parent/'offramp_route_reconcile/assessment.json')
    evidence=read(HERE/'native_evidence.json')
    protocol=read(HERE/'protocol.json')
    for text,sha in protocol['source_before'].items():
        if Path(text)!=Path('evaluation/controllers/offramp_routing.py'):
            assert hashlib.sha256((ROOT/text).read_bytes()).hexdigest()==sha
    from evaluation.controllers import offramp_routing as routing
    # Verify the old contract remains exactly equivalent with no opt-in policy.
    loader=importlib.machinery.SourceFileLoader('routing_before',str(HERE/'offramp_routing.before'))
    spec=importlib.util.spec_from_loader(loader.name,loader);old=importlib.util.module_from_spec(spec);loader.exec_module(old);old.ROOT=ROOT
    config=read(HERE/'candidate_config.json');base=read(HERE.parent/'offramp_route_reconcile/candidate_config.json')
    contract=read(ROOT/config['freeway']['offramp_route_inventory']);oldcontract=read(ROOT/base['freeway']['offramp_route_inventory'])
    mapping=read(ROOT/contract['mapping']['path']);legacy=routing.compile_inventory(oldcontract,mapping)
    assert legacy==old.compile_inventory(oldcontract,mapping)
    for fw,bounds in legacy['bounds'].items():
        for position in [0.,*bounds[:-1]]:
            assert routing._future_distribution(legacy,fw,position)==old._future_distribution(legacy,fw,position)
    config['freeway']['offramp_route_inventory']=base['freeway']['offramp_route_inventory'];assert config==base
    contrast={};wall=mass=route=resource=0.
    for seed in ('47','43'):
        name='closedloop_recorded2700_select_check_trace10681_' if seed=='47' else 'closedloop_recorded2250_lever450_trace10681_'
        previous=read(I/(name+('routed_ports47' if seed=='47' else 'routed_ports43'))/'summary.json')
        folder=I/(name+'unrouted'+seed);summary=read(folder/'summary.json')
        runtime=read(folder/'runtime.json')['offramp_route_inventory'];assert runtime['enabled']
        assert runtime['metadata']['offramp_route_inventory_source_sha256']==hashlib.sha256((HERE/'route_contract.json').read_bytes()).hexdigest()
        assert summary['future_observation_inputs'] is False and not summary['native_started']
        arms=(('hold','held_actual'),('selected','selected')) if seed=='47' else (('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both'))
        contrast[seed]={}
        for arm,key in arms:
            a=previous['results'][key];b=summary['results'][key]
            assert a['commands']==b['commands']
            if seed=='43':assert a['physical_cell_states'][0]==b['physical_cell_states'][0]
            wall+=b['wall_sec']
            route=max(route,max(r['max_cell_residual'] for r in b['offramp_route_inventory_checks']))
            t=read(folder/(key+'_RM_C10681_trace.json.gz'))['offramp_network_diagnostics']
            oldtrace=read(I/(name+('routed_ports47' if seed=='47' else 'routed_ports43'))/(key+'_RM_C10681_trace.json.gz'))['offramp_network_diagnostics']
            assert t['states'][0]==oldtrace['states'][0]
            ports={}
            for off,p in t['states'][-1]['ports'].items():
                native=before['cases'][seed][arm]['ports'][off]
                row={f:native['native_'+f] for f in ('entry','drain','final_stock')}
                now=dict(entry=p['admitted'],drain=p['departed'],final_stock=p['stock'])
                mass=max(mass,abs(p['stock']-p['initial']-p['admitted']+p['departed']))
                sending=[x for x in t['resources'] if x['kind']=='freeway_offramp_sending' and x['resource']==off]
                assert len(sending)==450
                assert abs(sum(x['accepted_total_veh'] for x in sending)-p['admitted'])<1e-7
                resource=max(resource,max(x['exceedance_veh'] for x in sending))
                ports[off]=dict(native=row,before={f:native['model_'+f] for f in row},after=now,
                    receiving_limited_seconds=sum(x['available_veh']-x['accepted_total_veh']>1e-8 for x in sending))
            ref='held_actual'
            costs=dict(before_delta_omega=a['ttt_omega_veh_h']-previous['results'][ref]['ttt_omega_veh_h'],
                       after_delta_omega=b['ttt_omega_veh_h']-summary['results'][ref]['ttt_omega_veh_h'],
                       native_delta_omega=before['cases'][seed][arm].get('native_delta_omega_veh_h'),
                       before_omega=a['ttt_omega_veh_h'],after_omega=b['ttt_omega_veh_h'])
            contrast[seed][arm]=dict(ports=ports,costs=costs,
                mae={stage:{f:sum(abs(p[stage][f]-p['native'][f]) for p in ports.values())/8
                            for f in ('entry','drain','final_stock')} for stage in ('before','after')},
                validation=b['validation'],canonical_quantity_constraints=b.get('canonical_quantity_constraints'))
    assert max(mass,route,resource)<1e-7
    result=dict(status='ROUTE_FREE_EXIT_REPAIRED_GAIN_STILL_UNQUALIFIED',cases=contrast,
                wall_sec=wall,forecasts=6,fit=0,new_native=0,new_fzp_scan=0,
                max_port_mass_residual=mass,max_route_partition_residual=route,max_resource_exceedance=resource,
                legacy_contract_compile_exact=True,source_pins=pins,goal_complete=False)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for seed,arms in contrast.items():
        for arm,d in arms.items():print(seed,arm,d['mae'],d['costs'])
    for seed,arm in [('47','hold'),('43','nc')]:
        print(seed,arm,contrast[seed][arm]['ports']['10638'])
    print('wall',wall,'mass',mass,'route',route)

if __name__=='__main__':main()

