"""Verify completed candidate transport and localize its remaining error."""
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:
        return json.load(f)


assert read(HERE/'status.json')['status']=='complete'
protocol=read(HERE/'protocol.json')
for p,h in protocol['pins'].items():
    assert sha(p)==h
pins=read(HERE.parent/'stop_population114/protocol.json')['input_pins']
blocks=read(HERE.parent/'lane_receiving107/blocks.json')
geometry=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
c=next(x for x in geometry['cells'] if x['road']=='FW_E' and x['cell']==19)
mid=(c['start_m']+c['end_m'])/2
results=[]
stock_error=flow_error=0.
for label,arm in [('candidate110','release'),('candidate90','release_vsl90')]:
    pred=load(HERE/(label+'.json.gz'))
    trace=read(HERE/(label+'_trace.json'))
    initial=2670.1
    bytime={round(x['time']-initial):x for x in trace}
    for x in pred['cells']:
        if x['cell']!=19:continue
        a=bytime[round(x['time_s']-initial)]
        stock_error=max(stock_error,abs(x['n_veh']-a['u']-a['d']))
    for x in pred['flows']:
        if x['cell']!=19:continue
        found=[a for a in trace if x['window_start_s']+1e-6<a['time']<=x['window_end_s']+1e-6]
        assert len(found)==30
        flow_error=max(flow_error,abs(sum(a['outflow'] for a in found)-x['downstream_crossings']))
    case='67_'+arm
    p=ROOT/pins[case]['path'];assert sha(p)==pins[case]['sha256']
    native=load(p)
    assert native['fields'][:4]==['cell','speed_kmh','x_m','lane']
    for w in range(3):
        start,end=initial+150*w,initial+150*(w+1)
        # Native frames are at block beginnings. Speeds are vehicle-time
        # weighted for each half, not the same vehicle cohort across arms.
        selected=[f for t,f in native['frames'].items() if start-1e-6<=float(t)<end-1e-6]
        assert len(selected)==30
        halves=[[],[]];counts=[0,0]
        for frame in selected:
            for v in frame.values():
                if v[0]!=19:continue
                h=int(v[2]>=mid);counts[h]+=1;halves[h].append(v[1])
        speed=[sum(x)/len(x) if x else None for x in halves]
        rows=[x for x in trace if start+1e-6<x['time']<=end+1e-6]
        assert len(rows)==150
        actual=next(x['actual'] for x in blocks if x['case']==case and x['duration_sec']==150 and abs(x['start']-start)<1e-6)
        base=load(HERE.parent/'jin_macro111'/('baseline_'+arm+'.json.gz'))
        baseline=sum(x['downstream_crossings'] for x in base['flows'] if x['cell']==19 and x['window_start_s']>=start-1e-6 and x['window_end_s']<=end+1e-6)
        results.append(dict(arm=arm,window=w,actual_cell19_out=actual,baseline_out=baseline,candidate_out=sum(x['outflow'] for x in rows),
                            native_mean_upstream_count=counts[0]/30,native_mean_downstream_count=counts[1]/30,
                            native_half_speed_kmh=speed,native_downstream_minus_upstream_speed=speed[1]-speed[0],
                            candidate_mean_upstream_count=sum(x['u'] for x in rows)/150,candidate_mean_downstream_count=sum(x['d'] for x in rows)/150,
                            caveat='Native stock is5s block-start average; candidate is1s block-end average. Conditional localization, not new prediction inputs.'))
assert stock_error<1e-7 and flow_error<1e-7
deltas=[]
for w in range(3):
    a,b=[next(x for x in results if x['arm']==arm and x['window']==w) for arm in ('release','release_vsl90')]
    deltas.append(dict(window=w,**{k:b[k]-a[k] for k in ('actual_cell19_out','baseline_out','candidate_out')}))
value=dict(results=results,deltas=deltas,stock_error_max=stock_error,flow_error_max=flow_error,
           decision=read(HERE/'assessment.json')['decision'],gain_qualified=False,production_unchanged=True)
(HERE/'localization.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value,ensure_ascii=False,indent=2))
