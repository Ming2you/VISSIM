"""One finished selected450 prediction; no hold gain claim or future input."""
from pathlib import Path
from collections import Counter
import ctypes,gzip,hashlib,json,math,sys

HERE=Path(__file__).resolve().parent;H=HERE.parent
sys.path.insert(0,str(H))
from qualify_native2400 import validate_scope
PINS={}
def read(p,compressed=False):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if compressed else b)
def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not (HERE/'comparison.json').exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    p=read(HERE/'plan.json')
    for path,digest in p['source_pins'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    assert read(HERE/'forecast2400/completion.json')['status']=='complete'
    native=read(H/'wout_response/assessment_integer_ids.json')['arms']['selected']
    prior=read(H/'connector_lane/comparison.json')
    initial=read(HERE/'forecast2400/state.json')
    before=read(H/'connector_lane/forecast2400/state.json')
    import re
    normalized=lambda x:re.sub(r' at 0x[0-9A-Fa-f]+>',' at ADDRESS>',json.dumps(x,sort_keys=True))
    assert normalized(initial)==normalized(before),'Current physical/route state must be unchanged'
    results={};counts={};baselines={}
    for label,folder in [('connector_first',H/'connector_lane'),('shared_space',HERE)]:
        s=read(folder/'forecast2400/summary.json')
        assert not s['future_observation_inputs'] and s['native_runs']==s['optimizer_calls']==0
        if label=='shared_space':assert s['forecasts']==1 and list(s['results'])==['selected']
        record=s['results']['selected'];baselines[label]=record
        assert record['conservation_states']==4 and record['writer_validated'] and record['resource_max_exceedance']<=1e-7
        response=read(folder/'forecast2400/selected.response.json.gz',True)
        rows=[]
        for j,t in enumerate((2400,2550,2700)):
            transfers=[x for x in response['transfers'] if t<=x['start_sec']<t+150]
            arrived=sum(x['vehicles'] for x in transfers if x['source']=='storage:SC1004_W_out' and x['target']=='ramp:RM_C10681')
            cohorts=record['known_endpoint_cohorts'][j]
            final=[x for x in response['residence'] if x['stage']=='urban' and math.isclose(x['end_sec'],t+150)]
            assert len(final)==1
            resources=[x for x in response['resource_allocations'] if t<=x['start_sec']<t+150]
            connector=sum(x['accepted_total_veh'] for x in resources if x['kind']=='known_wout_connector_to_road' and x['resource']=='68:3')
            lateral=sum((x['accepted_by_source_veh'].get('lane:68:4',0.)) for x in resources
                        if x['resource']=='68:3' and x['kind']==('known_wout_shared_lane_receiving' if label=='shared_space' else 'known_wout_lateral_receiving'))
            rows.append(dict(start_sec=t,arrival10681=arrived,final_W_out=final[0]['model_stock_veh']['storage:SC1004_W_out'],
                final_road68_lane4=sum(c['vehicles']*c.get('lane68',{}).get('shares',{}).get('4',0.) for c in cohorts),
                connector_to_lane3=connector,lateral4to3=lateral,
                urban66_to_W=sum(x['vehicles'] for x in transfers if x['source']=='movement:SC1004_S_to_W' and x['target']=='storage:SC1004_W_out'),
                native_arrival10681=native[j]['native']['ramps']['RM_C10681'],
                native_final_W_out=native[j]['native']['final']['total'],
                native_final_road68_lane4=native[j]['native']['final']['lanes'].get('68:4',0),
                native66_head_proxy=native[j]['native']['upstream_head_proxy']['from66']))
        results[label]=rows
        counts[label]=dict(resources=Counter(x['kind'] for x in response['resource_allocations']),
            shared_rows=sum(x['kind']=='known_wout_shared_lane_receiving' for x in response['resource_allocations']))
        del response
    errors={label:{key:sum(abs(r[key]-r['native_'+key]) for r in rows)
            for key in ('arrival10681','final_W_out','final_road68_lane4')} for label,rows in results.items()}
    costs={label:{'omega':r['omega_ttt_veh_h'],'W_out':r['costs_by_stock']['storage:SC1004_W_out'],
                  'ramp10681':r['costs_by_stock']['ramp:RM_C10681']} for label,r in baselines.items()}
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=dict(status='complete_one_fixed_selected_prediction',forecasts=1,tests=52,new_native=0,new_optimizations=0,new_coefficients=0,
             initial_state_unchanged=True,comparisons=results,absolute_errors=errors,selected_costs=costs,
             selected_cost_change={k:costs['shared_space'][k]-costs['connector_first'][k] for k in costs['shared_space']},
             resource_records=counts,calibration_control_gate_passed=False,
             limitations=['Only selected command compared: no new hold-selected DeltaTTT estimate.',
             'Same previously used seed29/2400 state, not independent validation.',
             'Space allocation is a macroscopic proportional-demand assumption; not native right-of-way inference.',
             'Native66 head is offset from W_out entry, so it is a flow proxy.'],source_pins=PINS)
    (HERE/'comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:out[k] for k in ('comparisons','absolute_errors','selected_cost_change')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
