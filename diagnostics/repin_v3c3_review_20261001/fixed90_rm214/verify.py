"""Independent receipts/stock/interval-cost check of the four saved forecasts."""
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PINS={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):
    p=HERE/name;PINS[name]=sha(p);raw=p.read_bytes()
    return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)

def main():
    protocol=read('protocol.json');summary=read('summary.json')
    assert read('completion.json')['status']=='COMPLETE'
    assert {k:sha(ROOT/k) for k in protocol['source_sha256']}==protocol['source_sha256']
    assert sha(Path(protocol['STOP']['path']))==protocol['STOP']['sha256']
    assert sha(HERE/'run.py')==protocol['driver_sha256']
    assert sha(Path(protocol['config']['path']))==protocol['config']['sha256']
    receipt=read('input_receipt.json')['replay_pair']
    assert receipt['seed']==47 and not receipt['future_states_used']
    cases={};intervals={};balance_max=0.;cost_error=0.;initial=None
    for name in ('hold110','release110','hold90','release90'):
        case=read(name+'.json');response=read(name+'_response.json.gz');cases[name]=case
        assert case['metrics']==summary['results'][name]
        assert case['validation']['all_actuator_and_step_constraints_checked']
        if initial is None:initial=case['stocks'][0]
        assert case['stocks'][0]==initial
        stocks=case['stocks'];assert [s['time_sec'] for s in stocks]==[2700,2850,3000,3150]
        for key in stocks[0]['stock'].keys()|stocks[-1]['stock'].keys():
            net=math.fsum(t['vehicles']*((t['target']==key)-(t['source']==key)) for t in response['transfers'])
            error=abs(stocks[-1]['stock'].get(key,0.)-stocks[0]['stock'].get(key,0.)-net)
            balance_max=max(balance_max,error);assert error<1e-7,(name,key,error)
        interval=[dict(omega=0.,east=0.,west=0.,ramps=0.,outside=0.) for _ in range(3)]
        for row in response['residence']:
            index=int((row['start_sec']-2700)//150)
            assert 0<=index<3 and row['end_sec']<=2700+150*(index+1)+1e-7
            assert abs(row['dt_h']-(row['end_sec']-row['start_sec'])/3600)<1e-10
            d=interval[index];stocks_now=row['model_stock_veh']
            for key,n in row['inside_veh'].items():
                assert 0<=n<=stocks_now[key]+1e-7
                d['omega']+=n*row['dt_h']
                d['outside']+=max(0.,stocks_now[key]-n)*row['dt_h']
                group='east' if key=='freeway:FW_E' else 'west' if key=='freeway:FW_W' else 'ramps' if key.startswith('ramp:') else None
                if group:d[group]+=n*row['dt_h']
        for k in interval[0]:
            error=abs(math.fsum(d[k] for d in interval)-case['metrics'][k])
            assert error<1e-7,(name,k,error)
            cost_error=max(cost_error,error)
        assert max((r['exceedance_veh'] for r in response['resource_allocations']),default=0.)<1e-7
        intervals[name]=interval
    for arm in ('hold','release'):
        a,b=cases[arm+'110'],cases[arm+'90']
        expected_rm=[2.,2.,2.] if arm=='hold' else [4.,6.,8.]
        assert [c['meters']['RM_C10484'] for c in a['commands']]==expected_rm
        for i in range(3):
            for key in ('green_times','offsets','meters'):
                assert a['commands'][i][key]==b['commands'][i][key]
            assert set(a['effective_cell_vsl'][i]['FW_E'])=={110.}
            assert set(b['effective_cell_vsl'][i]['FW_E'])=={90.,110.}
            assert a['effective_cell_vsl'][i]['FW_W']==b['effective_cell_vsl'][i]['FW_W']
            assert a['effective_cell_vsl'][i]['FW_E'][0]==b['effective_cell_vsl'][i]['FW_E'][0]==110.
        assert b['effective_cell_vsl'][0]==b['effective_cell_vsl'][1]==b['effective_cell_vsl'][2]
    changed=[i for i,(a,b) in enumerate(zip(cases['hold110']['effective_cell_vsl'][0]['FW_E'],cases['hold90']['effective_cell_vsl'][0]['FW_E'])) if a!=b]
    assert changed==[i for i,(a,b) in enumerate(zip(cases['release110']['effective_cell_vsl'][0]['FW_E'],cases['release90']['effective_cell_vsl'][0]['FW_E'])) if a!=b]
    for speed in ('110','90'):
        a,b=cases['hold'+speed],cases['release'+speed]
        for i in range(3):
            for key in ('vsl','green_times','offsets'):assert a['commands'][i][key]==b['commands'][i][key]
            assert [r for r in a['commands'][i]['meters'] if a['commands'][i]['meters'][r]!=b['commands'][i]['meters'][r]]==['RM_C10484']
    output=dict(passed=True,checks=dict(common_initial_stock=True,only_declared_actions_change=True,legal_sequences=True,
        entry110_unchanged=True,flow_balance_max=balance_max,interval_cost_error=cost_error,source_count=len(protocol['source_sha256']),STOP_unchanged=True),
        vsl90_effective_east_cells=changed,intervals=intervals,
        interval_release_minus_hold={speed:[{k:intervals['release'+speed][i][k]-intervals['hold'+speed][i][k]
            for k in intervals['hold'+speed][i]} for i in range(3)] for speed in ('110','90')},input_sha256=PINS,
        native90_verified=False,optimizer_selection_verified=False)
    (HERE/'verification.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:output[k] for k in ('passed','checks','vsl90_effective_east_cells','interval_release_minus_hold')}))

if __name__=='__main__':main()
