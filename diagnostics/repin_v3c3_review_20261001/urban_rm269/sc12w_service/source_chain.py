"""Reuse the completed candidate ledger to separate ready supply and service."""
import gzip,hashlib,json
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent;H=HERE.parent
PINS={}
def read(p,compressed=False):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if compressed else b)
def main():
    out=HERE/'source_chain.json';assert not out.exists()
    folder=HERE/'forecast2400_checked';state=read(folder/'state.json');net=read(folder/'network.json')
    native=read(H/'native_beta/assessment.json')['head_departures2400']
    result={}
    for arm in ('hold','selected'):
        response=read(folder/(arm+'.response.json.gz'),True)
        residence={r['end_sec']:r['model_stock_veh'] for r in response['residence'] if r['stage']=='urban'}
        bins={t:[] for t in (2400,2550,2700)}
        for row in response['transfers']:
            t=2400+int((row['start_sec']-2400)//150)*150
            if t in bins:bins[t].append(row)
        groups={}
        for prefix,origin in [('SC6_S_SC12_','SC12_to_SC6'),('SC12_S_SC16_','SC16_to_SC12'),('SC16_S_SC109_','SC109_to_SC16')]:
            members={'movement:'+m for m in net['urban_movements'] if m.startswith(prefix)}
            initial={'movement:'+m:n for m,n in state['urban_movement_queue'].items()}
            rows=[]
            for i,t in enumerate(bins):
                before=initial if t==2400 else residence[t]
                ready0=sum(before.get(m,0) for m in members);ready1=sum(residence[t+150].get(m,0) for m in members)
                arrived=sum(r['vehicles'] for r in bins[t] if r['target'] in members and r['source'] not in members)
                departed=sum(r['vehicles'] for r in bins[t] if r['source'] in members and r['target'] not in members)
                assert abs(ready0+arrived-departed-ready1)<1e-7
                sources=defaultdict(float)
                for r in bins[t]:
                    if r['target']=='storage:'+origin and r['source']!=r['target']:sources[r['source'] or r['route_key']]+=r['vehicles']
                label=prefix.split('_SC')[0]
                observed=native[arm].get(label,{}).get('actual',[])
                rows.append(dict(start_sec=t,ready_start=ready0,arrived=arrived,departed=departed,ready_end=ready1,
                    same_arrivals_unlimited_service_available=ready0+arrived,
                    prior_qualified_native_all_head=observed[i] if observed else None,incoming_storage_by_source=dict(sources)))
            groups[origin]=rows
        result[arm]=groups
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report=dict(status='complete_existing_response_reuse',arms=result,new_forecasts=0,new_native=0,coefficients_fitted=0,
        scope='Ready count balance and source attribution for the completed SC12W candidate. Unlimited-service availability holds model arrivals fixed; not a rerun or a physically realizable full network counterfactual.',
        limitations=['All-phase available vehicles are an upper bound and may be in the wrong movement/phase; do not infer local saturation from this sum.',
            'Native head targets reuse the existing qualified aggregate definitions; per-route causation is not established.'],source_pins=PINS)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for arm,groups in result.items():
        for g,rows in groups.items():print(arm,g,[(r['start_sec'],round(r['same_arrivals_unlimited_service_available'],2),round(r['departed'],2),r['prior_qualified_native_all_head']) for r in rows])
if __name__=='__main__':main()
