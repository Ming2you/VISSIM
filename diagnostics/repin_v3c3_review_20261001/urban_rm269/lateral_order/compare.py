"""Score one fixed150 prediction against the retained baseline and native data."""
from pathlib import Path
import gzip,hashlib,importlib.util,json

HERE=Path(__file__).resolve().parent;H=HERE.parent
read=lambda p:json.loads(p.read_bytes())


def main():
    assert not (HERE/'comparison.json').exists()
    folder=HERE/'forecast2700'; result=read(folder/'summary.json')
    assert read(folder/'completion.json')['status']=='complete'
    assert result['forecasts']==1 and result['resource_max_exceedance']<=1e-7
    loader=importlib.util.spec_from_file_location('recovery_compare',H/'recovery2700/compare.py')
    helper=importlib.util.module_from_spec(loader);loader.loader.exec_module(helper)
    response=json.loads(gzip.decompress((folder/'applied.response.json.gz').read_bytes()))
    candidate=helper.summarize(response,result['known_endpoint_cohorts'],2700)
    prior=read(H/'recovery2700/comparison.json')
    initial=result['known_initial_cohorts']; final=result['known_endpoint_cohorts']
    initial4={tuple(c['lane68']['order']) for c in initial
              if c['target']=='RM_C10681' and c.get('lane68',{}).get('shares')=={'4':1.}}
    candidate['initial_lane4_RM_remaining']=sum(c['vehicles'] for c in final
        if c['target']=='RM_C10681' and tuple(c['lane68']['order']) in initial4)
    base_result=read(H/'recovery2700/forecast2700_v3/summary.json')
    report=dict(status='complete_diagnostic',native=prior['native'],
        baseline=prior['predictions']['fresh2700'],candidate=candidate,
        omega_model_delta_veh_h=result['omega_ttt_veh_h']-base_result['omega_ttt_veh_h'],
        resource_max_exceedance=result['resource_max_exceedance'],
        stock_cost_change={k:result['costs_by_stock'].get(k,0)-base_result['costs_by_stock'].get(k,0)
                           for k in set(result['costs_by_stock'])|set(base_result['costs_by_stock'])},
        forecasts=1,native_runs=0,full_sdmpc=0,new_fits=0,whole450_control_gain_qualified=False,
        independent_heldout=False,production_changes=False,
        source_pins={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                     (folder/'summary.json',H/'recovery2700/comparison.json',HERE/'candidate.py')})
    (HERE/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('native','baseline','candidate','omega_model_delta_veh_h')},indent=2))


if __name__=='__main__':main()
