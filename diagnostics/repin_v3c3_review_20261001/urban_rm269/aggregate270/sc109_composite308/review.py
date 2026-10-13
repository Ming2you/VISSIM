"""Compare one composite with the retained306 responses and closed native counts."""
from pathlib import Path
import gzip
import hashlib
import json
import pickle

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
OLD=Path('E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2')
NEW=Path('E:/VISSIM_analysis/20261010_sc109_composite308/forecast2400_v2')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/'comparison.json').exists()
    cfg,_,_=pickle.loads((A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    native=read(A/'timing307/source_limits.json')['arms']
    head_truth=read(A/'cityresponse290/assessment.json')['head_counts']
    movement_sets={
        'SC109_left':{'SC109_W_SC108_to_N_SC16'},
        'SC16_south':{k for k,v in cfg.network.urban_movements.items() if k.startswith('SC16_S_') and v['phase']=='SC16_p1'},
        'SC12_south':{k for k,v in cfg.network.urban_movements.items() if k.startswith('SC12_S_') and v['phase']=='SC12_p1'},
        'SC6_south':{'SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104'},
    }
    result={};pins={}
    for version,folder in [('previous',OLD),('composite',NEW)]:
        doc=read(folder/'summary.json')
        assert doc['status']=='complete' and doc['forecasts']==2
        assert doc['canonical_state_error_before_projection']==0
        assert doc['native_runs']==doc['optimizer_calls']==doc['fits']==0
        for p,h in doc['source_pins'].items(): assert sha(p)==h,p
        pins[str(folder/'summary.json')]=sha(folder/'summary.json')
        result[version]={}
        for arm in ('hold','city'):
            summary=doc['results'][arm]
            assert summary['writer_three_blocks'] and summary['conservation_states']==4
            assert summary['shared_constraints']['feasible'] and summary['resource_max_exceedance']<1e-7
            path=folder/(arm+'.response.json.gz');pins[str(path)]=sha(path)
            response=json.loads(gzip.decompress(path.read_bytes()))
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            assert not response['physical_native_fidelity_certificate']
            assert abs(sum(sum(r['inside_veh'].values())*r['dt_h'] for r in response['residence'])-summary['omega_ttt_veh_h'])<1e-7
            counts={}
            for label,movements in movement_sets.items():
                records=[t for t in response['transfers'] if (t['source'] or '').removeprefix('movement:') in movements and t['target']!=t['source']]
                model=[sum(t['vehicles'] for t in records if at<=t['start_sec']<at+150) for at in (2400,2550,2700)]
                if label=='SC6_south':
                    observed=[r['actual'] for r in head_truth[arm] if r['group']=='SC6_S' and r['phase']=='p1']
                else:
                    observed=[b['heads'][label]['native_known']+b['heads'][label]['native_unresolved_tail'] for b in native[arm]]
                assert len(observed)==3
                counts[label]=dict(model=model,native=observed,
                    absolute_error_sum=sum(abs(m-n) for m,n in zip(model,observed)),
                    time_weighted_lower=-sum(t['vehicles']*(2850-t['start_sec'])/3600 for t in records),
                    time_weighted_upper=-sum(t['vehicles']*(2850-t['end_sec'])/3600 for t in records))
            result[version][arm]=dict(omega_ttt_veh_h=summary['omega_ttt_veh_h'],counts=counts,
                predicted_merge=summary['predicted_merge'],endpoint_wall_sec=summary['wall_sec'],
                shared_feasible=True,physical_checks=True,costs_by_stock=summary['costs_by_stock'])
    delta={v:r['city']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h'] for v,r in result.items()}
    for arm in ('hold','city'):
        assert result['previous'][arm]['predicted_merge']==result['composite'][arm]['predicted_merge']
    changes={}
    for v,arms in result.items():
        h,c=arms['hold']['costs_by_stock'],arms['city']['costs_by_stock']
        changes[v]={k:c.get(k,0)-h.get(k,0) for k in h.keys()|c.keys() if abs(c.get(k,0)-h.get(k,0))>1e-8}
        assert abs(sum(changes[v].values())-delta[v])<1e-7
    for p in [Path(__file__),HERE/'candidate.py',HERE/'tests_v2.log',A/'timing307/source_limits.json',A/'cityresponse290/assessment.json']:
        pins[str(p)]=sha(p)
    report=dict(status='complete_bounded_composite_supply_improved_gain_unqualified',goal_complete=False,
        results=result,delta_omega_veh_h=delta,native_delta_omega_veh_h=5.28666666666649,
        costs_by_stock_delta=changes,source_pins=pins,
        budget=dict(full450=2,ad=0,optimizer=0,new_fits=0,native=0,fzp_scans=0),
        decision='Retain diagnostic evidence but do not promote the composite or increase the SC109 rate again. Whole-city gain changes only0.125vehh; old3300 qualification is still absent. Reconcile remaining boundary-exit timing and actual admissions before further local rate changes.',
        limits=['Model transfer and native head locations differ. Block count errors include temporal/spatial boundary offset.',
                'Composite response at one development state only; not an unseen-state or native control gain validation.',
                'No alternative coefficient fit; original two pre-forecast setup failures are retained.'])
    (HERE/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('DELTA',delta)
    for arm in ('hold','city'):
        print(arm,{k:dict(previous=result['previous'][arm]['counts'][k]['absolute_error_sum'],
                         composite=result['composite'][arm]['counts'][k]['absolute_error_sum']) for k in movement_sets})


if __name__=='__main__': main()
