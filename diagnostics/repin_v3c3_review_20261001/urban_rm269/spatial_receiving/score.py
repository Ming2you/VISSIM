"""Reuse closed response ledgers; report local timing and disjoint cost terms."""
from pathlib import Path
import gzip,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;H=HERE.parent
read=lambda p:json.loads(p.read_bytes())

def main():
    assert not (HERE/'assessment.json').exists()
    loader=importlib.util.spec_from_file_location('recovery_score',H/'recovery2700/compare.py')
    helper=importlib.util.module_from_spec(loader);loader.loader.exec_module(helper)
    folder=HERE/'forecast2700';assert read(folder/'completion.json')['status']=='complete'
    result=read(folder/'summary.json')
    assert result['forecasts']==1 and not result['future_observation_inputs']
    assert result['resource_max_exceedance']<=1e-7 and result['conservation_states']==2
    path=folder/'applied.response.json.gz'
    with gzip.open(path,'rt',encoding='utf8') as f:response=json.load(f)
    fresh=helper.summarize(response,result['known_endpoint_cohorts'],2700)
    baseline=read(H/'recovery2700/comparison.json')
    pair=read(HERE/'pair_comparison.json')
    assert all(x['feasible'] and x['resource_exceedance']<=1e-7
               for x in pair['models']['candidate']['arms'].values())
    terms={}
    for label,row in [('native',pair['native_delta'])]+[(k,v['delta']) for k,v in pair['models'].items()]:
        combined=row['mainline']+row['W_out']+row['ramp10681']
        terms[label]=dict(whole=row['omega'],mainline_plus_Wout_plus_ramp10681=combined,
                         remaining_city_and_other_ramps=row['omega']-combined)
    report=dict(status='complete_local_timing_improvement_not_control_qualified',
        fresh2700=dict(native=baseline['native'],baseline=baseline['predictions']['fresh2700'],candidate=fresh),
        paired450=pair['models']['candidate'],native_delta=pair['native_delta'],disjoint_cost_deltas=terms,
        completed_fixed_predictions=3,unit_tests=6,full_ad=0,full_sdmpc=0,new_native=0,new_fits=0,
        production_changed=False,control_gain_qualified=False,source_pins={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (Path(__file__),HERE/'pair_comparison.json',path,folder/'summary.json',H/'recovery2700/comparison.json')},
        limits=['Fresh2700 is a previously inspected development state, not held-out verification.',
                'Mainline subtotal contains both directions and all mainline effects; not10681 causal attribution.',
                'Remaining subtotal includes other ramps as well as urban roads.',
                'Native lane-change deletions and original replay prefix discrepancy remain recorded.',
                'Existing wave speed and mean travel speed reused; receiving-only hybrid is not a validated full ramp LTM.',
                'Short-run runtime is not an end-to-end SDMPC benchmark.'])
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(fresh=report['fresh2700'],costs=terms),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
