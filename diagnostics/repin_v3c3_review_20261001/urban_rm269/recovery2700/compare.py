"""Compare a fresh-state150 diagnostic to its parent450 continuation and native."""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json
HERE=Path(__file__).resolve().parent;H=HERE.parent
PINS={}
def read(path,compressed=False):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if compressed else data)
def summarize(response,cohorts,start):
    transfers=[r for r in response['transfers'] if start<=r['start_sec']<start+150]
    key='storage:SC1004_W_out'
    rows=[r for r in response['residence'] if r['stage']=='urban' and r['end_sec']==start+150]
    assert len(rows)==1
    return dict(arrival10681=sum(r['vehicles'] for r in transfers if r['source']==key and r['target']=='ramp:RM_C10681'),
        W_out_final=rows[0]['model_stock_veh'][key],
        lane68_final={str(l):sum(c['vehicles']*c.get('lane68',{}).get('shares',{}).get(str(l),0.) for c in cohorts) for l in range(1,5)},
        source66_to_W=sum(r['vehicles'] for r in transfers if r['source']=='movement:SC1004_S_to_W' and r['target']==key),
        W_in_by_source=dict(Counter({s:sum(r['vehicles'] for r in transfers if r['target']==key and r['source']==s)
                                    for s in {r['source'] for r in transfers if r['target']==key}})))
def main():
    assert not (HERE/'comparison.json').exists()
    audit=read(HERE/'audit.json');folder=HERE/'forecast2700_v3'
    assert read(folder/'completion.json')['status']=='complete'
    result=read(folder/'summary.json')
    assert result['forecasts']==1 and not result['future_observation_inputs']
    assert result['resource_max_exceedance']<=1e-7 and result['conservation_states']==2
    sources=[('continued_from2400',H/'connector_lane/forecast2400/selected.response.json.gz',
              read(H/'connector_lane/forecast2400/summary.json')['results']['selected']['known_endpoint_cohorts'][-1]),
             ('fresh2700',folder/'applied.response.json.gz',result['known_endpoint_cohorts'])]
    model={name:summarize(read(path,True),cohorts,2700) for name,path,cohorts in sources}
    obs=read(H/'wout_response/assessment_integer_ids.json')['arms']['selected'][-1]['native']
    native=dict(arrival10681=obs['ramps']['RM_C10681'],W_out_final=obs['final']['total'],
        lane68_final={str(l):obs['final']['lanes'].get('68:'+str(l),0) for l in range(1,5)},
        head66_proxy=obs['upstream_head_proxy']['from66'],W_out_removals=audit['arms']['selected']['blocks'][-1]['removals_W_out'])
    assert native['W_out_removals']==0
    errors={name:{'arrival10681':r['arrival10681']-native['arrival10681'],
                  'W_out_final':r['W_out_final']-native['W_out_final'],
                  'lane68_abs_sum':sum(abs(r['lane68_final'][k]-native['lane68_final'][k]) for k in native['lane68_final'])}
            for name,r in model.items()}
    # Never compare different2700 initial states as held-selected causal gain.
    report=dict(status='complete',native=native,predictions=model,errors=errors,
        future_state_reset_in_continuation=False,new_prediction_initializes_at2700=True,
        whole_450_gain_qualified=False,independent_heldout_validation=False,
        forecasts=1,new_fits=0,new_native=0,source_pins=PINS,
        limits=['Source66 head proxy and model W_out receipt occur at different positions.',
                'Fresh2700 uses its observed state; it does not repair the autonomous2400-to2850 prediction.',
                'No two-arm deltaTTT or SDMPC-selection qualification is claimed from this diagnostic.',
                'No W_out deletion in2700-2850 does not mean the entire network is deletion-free.'])
    (HERE/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('native','predictions','errors')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
