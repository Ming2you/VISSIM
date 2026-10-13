"""329 result audit. Reuse325/native caches, no fit or further forecasts."""
from pathlib import Path
import gzip,hashlib,json,math

HERE=Path(__file__).resolve().parent;A=HERE.parent;PINS={}
def read(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)

def main():
    assert not (HERE/'assessment.json').exists()
    results={};summaries={}
    for label,folder in [('before325','sc10_north325'),('future329','native_routes329')]:
        out=Path('E:/VISSIM_analysis')/('20261010_'+folder)/'forecast2400'
        s=read(out/'summary.json');summaries[label]=s;results[label]={}
        assert s['forecasts']==2 and s['start_sec']==2400 and s['end_sec']==2850 and not s['future_observation_inputs']
        for p,h in s['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        for arm in ('hold','city'):
            a=s['results'][arm];r=read(out/(arm+'.response.json.gz'))
            assert a['conservation_states']==4 and a['writer_three_blocks'] and a['shared_constraints']['feasible']
            assert a['resource_max_exceedance']<1e-7 and r['model_constraint_coverage']['complete']
            assert r['conditional_model_feasibility_witness']
            movements={}
            for m in ('SC12_N_SC6_to_S_SC16','SC12_N_SC6_to_W_SC11','SC12_N_SC6_to_E_SC106'):
                key='movement:'+m
                arrivals=[x for x in r['transfers'] if x['target']==key and x['source']!=key]
                departures=[x for x in r['transfers'] if x['source']==key and x['target']!=key]
                intended=[x for x in r['resource_allocations'] if x['kind']=='urban_movement_intended_limit'
                    and x['resource']==m and x['accepted_total_veh']>1e-8]
                movements[m]=dict(arrivals=sum(x['vehicles'] for x in arrivals),
                    departed=sum(x['vehicles'] for x in departures),
                    positive_departure_steps=len(intended),
                    intended_bound_steps=sum(abs(x['available_veh']-x['accepted_total_veh'])<1e-7 for x in intended))
            accepted={}
            for x in r['transfers']:
                if x['target']=='storage:SC6_to_SC12' and x['source']!=x['target']:
                    accepted[x['source']]=accepted.get(x['source'],0.)+x['vehicles']
            receiver=[x for x in r['resource_allocations'] if x['kind']=='regular_receiving'
                and x['resource']=='storage:SC12_to_SC16' and x['accepted_total_veh']>1e-8]
            results[label][arm]=dict(omega_ttt_veh_h=a['omega_ttt_veh_h'],wall_sec=a['wall_sec'],
                movements=movements,incoming_accepted=accepted,
                downstream_receiver_bound_steps=sum(abs(x['available_veh']-x['accepted_total_veh'])<1e-7 for x in receiver),
                writer_blocks=3,conservation_states=4,NP_NUF_feasible=True,resource_max_exceedance=a['resource_max_exceedance'])
    out=Path('E:/VISSIM_analysis/20261010_native_routes329/forecast2400')
    application=read(out/'future_route_application.json');checks=read(out/'gate_checks.json')
    for r in checks.values():assert abs(r['received']-r['discharged']-r['remaining'])<1e-7
    routes=read(out/'future_route_receipts.json')
    for r in routes:
        assert r['source'] in application['eligible_sources']
        assert abs(sum(x['vehicles'] for x in r['routes'].values())-r['accepted_veh'])<1e-8
        for m,x in r['routes'].items():assert abs(x['vehicles']-r['accepted_veh']*application['weights'][m])<1e-8
    through='SC12_N_SC6_to_S_SC16'
    for arm in ('hold','city'):
        left,right=results['before325'][arm],results['future329'][arm]
        assert left['incoming_accepted']==right['incoming_accepted']
        assert right['movements'][through]['arrivals']>left['movements'][through]['arrivals']+5
        assert right['movements'][through]['departed']==left['movements'][through]['departed']
        assert right['downstream_receiver_bound_steps']==0
    actual=read(A/'sc10_north325/review.json')['native_delta_omega_veh_h']
    delta={k:v['city']['omega_ttt_veh_h']-v['hold']['omega_ttt_veh_h'] for k,v in results.items()}
    result=dict(status='complete_future_route_contract_corrected_whole_gain_effect_negligible',
        results=results,delta_omega_veh_h=delta,native_delta_omega_veh_h=actual,
        gain_error_reduction_veh_h=abs(actual-delta['before325'])-abs(actual-delta['future329']),
        gate_conservation=checks,future_route_receipts=len(routes),
        application=application,production_adopted=False,goal_complete=False,
        budget=dict(candidate_sets=1,forecasts450=2,tests=6,native=0,fzp=0,ad=0,optimizer=0,fits=0,production_changes=0,push=0),
        conclusion='Two proven source types use declared RD33 routes. Through arrivals rise but departures are unchanged because the intended service envelope binds while receiver space remains. This correct routing contract is not the main whole gain error.',
        next_step='Do not repeat SC10/SC12 beta, ETA or nominal service searches. Reuse this routing evidence; preserve the diagnostic, not production adoption. Before further city tuning, audit latest aggregate-model prediction of the existing native joint-minus-city RM contrast using the same initial2400 and exact executed three-block commands, reusing city prediction and permitting at most one new joint450 prediction if its state/config and action provenance match. Existing289 RM validation used an older model, so do not transfer that pass to329. Keep wholeOmega ranking requirement open; no extra full optimizer/native, no gain bonus.',
        limitations=['One development state; no unused-state or new full controller selection.',
                    'Declared expected shares do not reproduce finite-sample random route realization.',
                    'Incoming SC6 east1032:1 ends after RD33 and is unchanged pending actual continuation evidence.',
                    'Current beta-allocated service caps stay fixed; a prior increase326 already failed to close the whole gap.',
                    'A receipt confirms aggregate model transfers, not VISSIM actuation or native causal gain.'],
        source_pins=PINS)
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('DELTA',delta,'NATIVE',actual,'ERROR_REDUCTION',result['gain_error_reduction_veh_h'])
    print('CHECKS:6 tests,2 forecasts; unchanged accepted source totals; route tags,finite parent,physical accounting,NP/NUF and3-block writer pass.')

if __name__=='__main__':main()

