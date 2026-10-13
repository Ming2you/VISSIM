"""Inspect saved resource minima; do not infer binding from intended=accepted."""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
read=lambda p:json.loads(p.read_bytes())


def main():
    out=HERE/'service_limits.json'
    assert not out.exists()
    evidence=read(HERE/'assessment.json')
    network=read(H/'selection2400/network.json')
    result={}
    pins={}
    for arm in ('hold','selected'):
        p=H/'selection2400_discrete'/(arm+'_response.json.gz')
        b=p.read_bytes(); pins[str(p)]=hashlib.sha256(b).hexdigest()
        assert pins[str(p)]==evidence['source_pins'][str(p)]
        r=json.loads(gzip.decompress(b))
        interests={m for m in network['urban_movements'] if m.startswith(('SC12_S_','SC12_W_'))}
        resources=defaultdict(dict)
        for row in r['resource_allocations']:
            if row['resource'] in interests and row['kind'] in ('urban_movement_stock','urban_movement_intended_limit'):
                resources[row['resource'],row['start_sec']][row['kind']]=row
        bins={}
        for start in (2400,2550,2700):
            rows={}
            for m in sorted(interests):
                rows[m]=dict(positive_requests=0,positive_request_ready_stock_bound=0,
                    positive_request_below_ready_stock=0,receiver_or_later_limited=0,
                    no_ready_queue_steps=0,zero_intent_with_queue_steps=0,
                    peak_ready_stock_veh=0.,requested_veh=0.,accepted_veh=0.)
            for (m,t), kinds in resources.items():
                if not start<=t<start+150: continue
                assert set(kinds)=={'urban_movement_stock','urban_movement_intended_limit'}
                q=kinds['urban_movement_stock']['available_veh']
                intent=kinds['urban_movement_intended_limit']['available_veh']
                accepted=kinds['urban_movement_intended_limit']['accepted_total_veh']
                assert -1e-8<=accepted<=intent+1e-8 and intent<=q+1e-8
                x=rows[m]
                x['peak_ready_stock_veh']=max(x['peak_ready_stock_veh'],q)
                x['requested_veh']+=intent; x['accepted_veh']+=accepted
                if q<=1e-8: x['no_ready_queue_steps']+=1
                elif intent<=1e-8: x['zero_intent_with_queue_steps']+=1
                if intent>1e-8:
                    x['positive_requests']+=1
                    x['positive_request_ready_stock_bound']+=int(abs(intent-q)<=1e-8)
                    x['positive_request_below_ready_stock']+=int(intent<q-1e-8)
                    x['receiver_or_later_limited']+=int(accepted<intent-1e-8)
            arrival=Counter()
            for row in r['transfers']:
                if start<=row['start_sec']<start+150 and row['target']=='storage:SC16_to_SC12':
                    arrival[row['source'] or 'exogenous_boundary']+=row['vehicles']
            bins[str(start)]=dict(movements=rows,sc16_to_sc12_incoming_sources=dict(arrival))
        result[arm]=bins
        del r
    report=dict(status='complete',arms=result,source_pins=pins,new_forecasts=0,native_runs=0,
        rule='Separate available queue, intended=min(queue,green-service,other request limits), and actual accepted.',
        limitations=['A below-ready-stock intended limit alone cannot separate green exposure, service capacity, and pre-allocation corridor constraints.',
            'Zero intention with positive queue may be a red phase and is not a service fault.',
            'Sums of available queue across substeps are not vehicle inventory or independent service capacity.'])
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for a,bins in result.items():
        for t,d in bins.items():
            print(a,t,'S-through',d['movements']['SC12_S_SC16_to_N_SC6'],'incoming',d['sc16_to_sc12_incoming_sources'])
if __name__=='__main__': main()

