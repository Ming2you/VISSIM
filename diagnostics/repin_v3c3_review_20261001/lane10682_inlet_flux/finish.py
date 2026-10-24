"""Close one bounded inlet experiment; preserve its sources and restore the prior install."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output=HERE/'completion.json';assert not output.exists()
    a=json.loads((HERE/'assessment.json').read_bytes())
    tests=json.loads((HERE/'tests.json').read_bytes())
    assert a['forecasts']==6 and tests['passed'] and tests['tests']==26
    previous=json.loads((HERE.parent/'lane10682_cellfit/completion.json').read_bytes())
    executed=json.loads((HERE/'executed_sources.json').read_bytes())
    before=json.loads((HERE/'before.json').read_bytes())
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert sha(stop)==previous['stop_sha256']
    for relative,digest in executed.items():
        assert sha(ROOT/relative)==digest,relative
        assert sha(HERE/'executed_sources'/Path(relative).name)==digest,relative
        assert sha(HERE/(Path(relative).name+'.before'))==before[relative],relative
    for relative in before:
        (ROOT/relative).write_bytes((HERE/(Path(relative).name+'.before')).read_bytes())
    for relative,digest in before.items():assert sha(ROOT/relative)==digest,relative
    for path,digest in previous['previous_production_exact'].items():assert sha(Path(path))==digest,path
    assert sha(stop)==previous['stop_sha256']
    old=json.loads((HERE.parent/'lane10682_target_transport/assessment.json').read_bytes())
    original_comparison={}
    for seed,cases in a['cases'].items():
        original_comparison[seed]={}
        for arm,case in cases.items():
            base=old['cases'][seed][arm]
            original_comparison[seed][arm]=dict(
                ports={p:dict(original=base['ports'][p]['before'],current=x['after'],native=x['native'])
                       for p,x in case['ports'].items()},
                final_speeds=[dict(cell=x['cell'],native=x['native'],original=y['before'],current=x['after'])
                    for x,y in zip(case['speeds'][-4:],base['speeds'][-4:])],
                delta_omega=dict(native=case['costs']['native_delta'],original=base['costs']['before_delta'],current=case['costs']['after_delta']))
    (HERE/'original_comparison.json').write_text(json.dumps(original_comparison,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    result=dict(status='partial_structural_evidence_not_adopted_sources_restored',goal_status='ACTIVE/NOT_QUALIFIED',
        tests=26,forecasts=6,forecast_compute_sec=a['wall_sec'],fit_calls=0,
        owned_sessions={'11961':'EXIT0','31572':'EXIT0'},restored_exact=before,
        previous_production_exact=previous['previous_production_exact'],stop_sha256=sha(stop),
        new_native=0,new_fzp=0,push=0,mass_residual=a['mass_residual'],route_residual=a['route_residual'],
        resource_exceedance=a['resource_exceedance'],
        evidence=['Sparse inlet allocation caused much of the false upstream queue in the lane candidate.',
            '47cells9/10 recover35/39 to83/81kmh, similar to original aggregate84/81, not a novel overall improvement.',
            '43off10682entry126.74 improves over original140.42 versus113native, but cell10/11lane2 congestion remains missed.',
            '47off10643drain61.48 versus94native, close to original61.04; upstream/urban dynamics remain unresolved.',
            'Nativecell13lane2 is also less dense/faster than12; averaging alone does not explain missing localized merge congestion.',
            'No gain/AD/SDMPC qualification; do not extend scalar coefficient grids to hide remaining structure.'],
        next='Reuse these results. Separate actual10681 merge amount and receiving-lane allocation from localcell12 speed/relaxation/anticipation; retain8off entry/drain/storage ledger. No new rate grid or blanket lane-region expansion without causal evidence.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','tests','forecasts','forecast_compute_sec','new_native')},ensure_ascii=False))


if __name__=='__main__':main()
