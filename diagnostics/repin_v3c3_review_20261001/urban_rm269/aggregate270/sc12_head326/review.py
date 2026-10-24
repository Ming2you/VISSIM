"""Read the single326 pair and cached325/native comparisons, without fitting."""
from pathlib import Path
import gzip,hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
PINS={}
def read(path):
    path=Path(path);b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if path.suffix=='.gz' else b)

def main():
    assert not (HERE/'review.json').exists()
    result={};summaries={}
    for label,folder in [('gate325','20261010_sc10_north325'),('head326','20261010_sc12_head326')]:
        root=Path('E:/VISSIM_analysis')/folder/'forecast2400'
        s=read(root/'summary.json');summaries[label]=s;result[label]={}
        assert s['forecasts']==2 and not s['future_observation_inputs']
        for p,h in s['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        for arm in ('hold','city'):
            a=s['results'][arm];r=read(root/(arm+'.response.json.gz'))
            assert a['conservation_states']==4 and a['writer_three_blocks'] and a['shared_constraints']['feasible']
            assert a['resource_max_exceedance']<1e-7
            assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
            rows=[x for x in r['transfers'] if x['source'] in {'movement:SC12_N_SC6_to_S_SC16','movement:SC12_N_SC6_to_W_SC11'} and x['source']!=x['target']]
            result[label][arm]=dict(omega_ttt_veh_h=a['omega_ttt_veh_h'],endpoint_wall_sec=a['wall_sec'],
                p1_counts=[sum(x['vehicles'] for x in rows if t<=x['start_sec']<t+150) for t in (2400,2550,2700)],
                p1_head_time_cost=-sum(x['vehicles']*(2850-x['start_sec'])/3600 for x in rows),
                resource_max_exceedance=a['resource_max_exceedance'],writer_three_blocks=True,conservation_states=4,NP_NUF_feasible=True)
    native=read(A/'sc12_platoon324/assessment.json');prior=read(A/'sc10_north325/review.json')
    delta={k:v['city']['omega_ttt_veh_h']-v['hold']['omega_ttt_veh_h'] for k,v in result.items()}
    actual=prior['native_delta_omega_veh_h']
    gate=read(Path('E:/VISSIM_analysis/20261010_sc12_head326/forecast2400/gate_checks.json'))
    assert all(abs(g['received']-g['discharged']-g['remaining'])<1e-7 for g in gate.values())
    shifts=[]
    for k in summaries['head326']['results']['hold']['costs_by_stock']:
        d={v:s['results']['city']['costs_by_stock'][k]-s['results']['hold']['costs_by_stock'][k] for v,s in summaries.items()}
        shifts.append(dict(stock=k,before_delta=d['gate325'],after_delta=d['head326'],change=d['head326']-d['gate325']))
    shifts.sort(key=lambda x:-abs(x['change']))
    report=dict(status='complete_SC12_shared_nominal_cap_not_sufficient_for_whole_gain',results=result,
        native_p1_counts={a:[r['p1_count'] for r in native['results'][a]['native_blocks']] for a in ('hold','city')},
        delta_omega_veh_h=delta,native_delta_omega_veh_h=actual,
        gain_error_reduction_veh_h=abs(actual-delta['gate325'])-abs(actual-delta['head326']),
        first_block_p1_delta={k:v['city']['p1_counts'][0]-v['hold']['p1_counts'][0] for k,v in result.items()},
        top_stock_delta_changes=shifts[:12],candidate_adopted=False,goal_complete=False,
        budget=dict(candidate_sets=1,forecasts450=2,tests=6,native=0,fzp=0,optimizer=0,ad=0,fits=0,production_changes=0,push=0),
        conclusion='Increasing the SC12 north envelope and sharing it physically is insufficient: whole paired sign remains wrong. This nominal rate is not adopted or saturation-calibrated.',
        next_step='Stop SC10/SC12 rate, beta and ETA searches. Consolidate the remaining error by already observed source-admission and head-discharge timing contributions before choosing another structural change. Use source318 only as a conditional diagnosis; do not feed actual future admissions into autonomous validation. Preserve the qualified FW5/urban10 speedup and avoid another unchanged optimizer/native run.',
        limitations=['Shared three-head partial FIFO does not explicitly preserve two dedicated through-lane budgets when right is blocked.',
                    '1400veh/h/head is an existing nominal prior, not supported saturation data for this site.',
                    'One development state and executed controls, not held-out calibration or new controller selection.',
                    'Native boundary insertion differs across arms despite identical demand; this candidate does not correct boundary predictions.'],
        source_pins=PINS)
    (HERE/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('DELTA',delta,'NATIVE',actual,'ERROR_REDUCTION',report['gain_error_reduction_veh_h'])
    for label,r in result.items():print(label,{a:v['p1_counts'] for a,v in r.items()})
    print('NATIVE_P1',report['native_p1_counts'])

if __name__=='__main__':main()
