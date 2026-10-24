"""Assess the single completed pair; do not tune or re-run."""
from pathlib import Path
import gzip,hashlib,json,pickle

HERE=Path(__file__).resolve().parent;A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc16_aggregate323/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc10_north325/forecast2400')
PINS={}
def read(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)

def main():
    assert not (HERE/'review.json').exists()
    results={};summaries={}
    for label,folder in [('before323',OLD),('gate325',NEW)]:
        summary=read(folder/'summary.json');summaries[label]=summary
        assert summary['forecasts']==2 and not summary['future_observation_inputs']
        for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        results[label]={}
        for arm in ('hold','city'):
            s=summary['results'][arm];response=read(folder/(arm+'.response.json.gz'))
            assert s['writer_three_blocks'] and s['conservation_states']==4 and s['shared_constraints']['feasible']
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            assert s['resource_max_exceedance']<1e-7
            tr=[x for x in response['transfers'] if x['source'] in {'movement:SC12_N_SC6_to_S_SC16','movement:SC12_N_SC6_to_W_SC11'} and x['source']!=x['target']]
            results[label][arm]=dict(omega_ttt_veh_h=s['omega_ttt_veh_h'],p1_counts=[sum(x['vehicles'] for x in tr if t<=x['start_sec']<t+150) for t in (2400,2550,2700)],
                p1_head_time_cost=-sum(x['vehicles']*(2850-x['start_sec'])/3600 for x in tr),
                endpoint_sec=s['wall_sec'],resource_max_exceedance=s['resource_max_exceedance'],
                writer_three_blocks=True,conservation_states=4,shared_constraints_feasible=True)
    gate=read(NEW/'north_gate_checks.json');application=read(NEW/'north_gate_application.json')
    assert application['initial_gate_veh']==11 and not application['future_observation_inputs']
    gate_summary={}
    for arm,g in gate.items():
        assert abs(g['received']-g['discharged']-g['remaining'])<1e-7
        assert len(g['history'])==45 and all(not x for x in g['initial_known_route_tags_at_blocks'])
        assert all(not (r['green_sec']==0 and r['discharged']>1e-8) for r in g['history'])
        gate_summary[arm]=dict(received=g['received'],discharged=g['discharged'],remaining=g['remaining'],
            positive_green_capacity_binding=[dict(sec=r['sec'],ready=r['ready_before'],capacity=r['budget']) for r in g['history'] if r['positive_green_capacity_binding']],
            initial_tags_consumed=True,red_discharges=0)
    native=read(A/'sc12_platoon324/assessment.json')
    prior=read(A/'sc16_aggregate323/review.json')
    delta={k:r['city']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h'] for k,r in results.items()}
    local_delta={k:r['city']['p1_counts'][0]-r['hold']['p1_counts'][0] for k,r in results.items()}
    changes=[]
    for k in summaries['gate325']['results']['hold']['costs_by_stock']:
        d={v:s['results']['city']['costs_by_stock'][k]-s['results']['hold']['costs_by_stock'][k] for v,s in summaries.items()}
        changes.append(dict(stock=k,before_delta=d['before323'],after_delta=d['gate325'],change=d['gate325']-d['before323']))
    changes.sort(key=lambda r:-abs(r['change']))
    fixture=A/'citysplit287/forecast2400/initial.pickle';PINS[str(fixture)]=hashlib.sha256(fixture.read_bytes()).hexdigest()
    cfg,_,_=pickle.loads(fixture.read_bytes())
    rate=sum(cfg.network.movement_capacity_by_movement_veh_h[m] for m in ('SC12_N_SC6_to_S_SC16','SC12_N_SC6_to_W_SC11'))
    bound=rate*34/3600
    assert abs(bound-11.59090909090909)<1e-8 and native['results']['hold']['native_blocks'][0]['p1_count']==14
    report=dict(status='complete_middle_signal_direction_local_only_whole_gain_unqualified',results=results,gate=gate_summary,
        delta_omega_veh_h=delta,native_delta_omega_veh_h=prior['native_delta_omega_veh_h'],
        gain_error_reduction_veh_h=abs(prior['native_delta_omega_veh_h']-delta['before323'])-abs(prior['native_delta_omega_veh_h']-delta['gate325']),
        first_block_p1_count_delta=local_delta,native_first_block_p1_count_delta=-9,
        major_stock_delta_changes=changes[:15],
        next_operand=dict(movement_rate_sum_veh_h=rate,green_sec=34,entire_green_upper_bound_veh=bound,native_hold_count=14,
            explanation='Even with instantaneous available stock the retained SC12 north service bound excludes the observed14 vehicles; the gate also delays incoming stock into the end of this green. Diagnose shared physical service and post-signal moving speed together before another run.'),
        budget=dict(candidate_sets=1,forecasts450=2,tests=6,optimizer=0,ad=0,native=0,fzp=0,fits=0,production_changes=0,push=0),
        candidate_adopted=False,goal_complete=False,source_pins=PINS,
        next_step='Do not grid-fit SC10 rate or ETA. Check Claude/shared physical head resource implementation for SC12 north: retained1227veh/h total cap permits11.59 versus observed14 in the full34s green. Separate this service mismatch from post-gate moving-speed/10s arrival rounding. Keep source318 boundary admission effects separate. Only evidence-backed shared-service/transport correction merits one further pair; do not repeat unchanged AD/optimizer/native.',
        limits=['Current11 pre-signal vehicles are now gated, but first-block hold count falls14 observed /11.59 before /7.54 after. Local paired direction improvement is not overall fit.',
                'Whole city-minus-hold TTT remains negative while native is positive; no production or controller-gain qualification.',
                '4200veh/h provisional SC10 bound binds in each2-second initial green. It is not independently calibrated.',
                'Parent finite storage and existing receiving constraints pass; sub-link lane FIFO and gap acceptance remain approximate.',
                'This is the development state and fixed executed controls; no unused-state, AD or fresh SDMPC choice qualification.'])
    (HERE/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('OMEGA_DELTA',delta,'NATIVE',report['native_delta_omega_veh_h'],'GAIN_ERROR_REDUCTION',report['gain_error_reduction_veh_h'])
    print('FIRST_BLOCK_DELTA',local_delta,'NATIVE',-9)
    print('SERVICE_BOUND',report['next_operand'])

if __name__=='__main__':main()
