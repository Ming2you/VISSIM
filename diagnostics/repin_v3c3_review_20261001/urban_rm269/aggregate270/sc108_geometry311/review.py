"""Same-command whole-area and corridor comparison; no recalibration."""
from pathlib import Path
import gzip
import hashlib
import json

HERE=Path(__file__).resolve().parent
A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc108_side310/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc108_geometry311/forecast2400')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/'comparison.json').exists()
    heads=read(A/'exit_timing309/sc109_chain.json')
    pins={};results={}
    movements={'SC108_side':['SC108_W_to_E_SC109'],
        'SC108_main':['SC108_W_SC107_to_E_SC109','SC108_W_SC107_to_S'],
        'SC109_through':['SC109_W_SC108_to_E'], 'SC109_left':['SC109_W_SC108_to_N_SC16']}
    for version,folder in (('old',OLD),('new',NEW)):
        doc=read(folder/'summary.json')
        assert doc['status']=='complete' and doc['forecasts']==2 and doc['native_runs']==doc['optimizer_calls']==0
        assert doc['canonical_state_error_before_projection']==0
        for p,h in doc['source_pins'].items():assert sha(p)==h,p
        pins[str(folder/'summary.json')]=sha(folder/'summary.json')
        results[version]={}
        for arm in ('hold','city'):
            r=doc['results'][arm]
            assert r['writer_three_blocks'] and r['conservation_states']==4
            path=folder/(arm+'.response.json.gz');pins[str(path)]=sha(path)
            response=json.loads(gzip.decompress(path.read_bytes()))
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            assert not response['physical_native_fidelity_certificate']
            assert r['resource_max_exceedance']<1e-7
            counts={}
            for label,keys in movements.items():
                keys={'movement:'+k for k in keys}
                rows=[x for x in response['transfers'] if x['source'] in keys and x['source']!=x['target']]
                counts[label]=dict(count=sum(x['vehicles'] for x in rows),
                    count150=[sum(x['vehicles'] for x in rows if t<=x['start_sec']<t+150) for t in (2400,2550,2700)],
                    departure_cost_endpoint=-sum(x['vehicles']*(2850-x['end_sec'])/3600 for x in rows))
            results[version][arm]=dict(omega_ttt_veh_h=r['omega_ttt_veh_h'],counts=counts,shared_constraints=r['shared_constraints'],
                costs_by_stock=r['costs_by_stock'],predicted_merge=r['predicted_merge'],wall_sec=r['wall_sec'])
    deltas={k:r['city']['omega_ttt_veh_h']-r['hold']['omega_ttt_veh_h'] for k,r in results.items()}
    native=5.28666666666649
    counts={}
    for arm in ('hold','city'):
        counts[arm]={key:dict(native=heads['native_head_summary'][arm][ref]['count150'],
            old=results['old'][arm]['counts'][key]['count150'],new=results['new'][arm]['counts'][key]['count150'])
            for key,ref in [('SC108_side','SC108_side_p3'),('SC108_main','SC108_W_p3'),('SC109_through','SC109_W_p3')]}
    for p in (A/'sc108_side310/support.json',A/'sc108_side310/candidate.py',A/'sc109_composite308/candidate.py',HERE/'candidate.py',HERE/'tests.log',Path(__file__),A/'exit_timing309/sc109_chain.json'):
        pins[str(p)]=sha(p)
    report=dict(status='complete_bounded_sc108_geometry_response',goal_complete=False,adopted=False,results=results,
        delta_omega_veh_h=deltas,native_delta_omega_veh_h=native,
        absolute_gain_error_reduction_veh_h=abs(deltas['old']-native)-abs(deltas['new']-native),
        count_comparison=counts,source_pins=pins,
        budget=dict(full450=2,parameter_sets=0,ad=0,optimizer=0,native=0,fzp_scans=0),
        limits=['Shared NP/NUF feasibility is reported per arm, never assumed from physical conservation. A failing arm cannot be presented as a feasible controller candidate.',
                'The earlier past-GREEN service floor is retained unchanged. Geometry changes storage/clock only, with observed initial stocks and pending arrival times conserved.',
                'One development state; head counts differ spatially from model departures.',
                'Native actual admissions and disappearance remain separate accounting terms.',
                'A local count improvement is not certification of whole-area choice or unseen-state generalization.'])
    (HERE/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('OMEGA',deltas,'NATIVE',native,'ERROR_REDUCTION',report['absolute_gain_error_reduction_veh_h'])
    print('COUNTS',json.dumps(counts))
    print('WALL',{k:{a:r['wall_sec'] for a,r in v.items()} for k,v in results.items()})


if __name__=='__main__':main()
