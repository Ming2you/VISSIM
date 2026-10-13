"""Existing-response SC1 source split, with actual same-physical-head lower bounds."""
import gzip,hashlib,importlib.util,json,sys
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
loader=importlib.util.spec_from_file_location('clock_audit',H/'city_response/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def zipped(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(gzip.decompress(b))
def main():
    out=HERE/'assessment.json';assert not out.exists()
    net=read(H/'native_beta/forecast2400_checked/network.json')
    native=read(H/'service_ceiling/source_check.json')
    modes={'internal':'SC1_S_SC107_to_N_SC101','boundary':'SC1_S_to_N_SC101'}
    origins={'internal':'SC107_to_SC1','boundary':'in_SC1_S'}
    result={}
    for arm in ('hold','selected'):
        response=zipped(H/'native_beta/forecast2400_checked'/(arm+'.response.json.gz'))
        by_resource=defaultdict(dict);transfers=defaultdict(list)
        for row in response['resource_allocations']:
            if row['resource'] in modes.values():by_resource[row['resource'],int(row['start_sec'])][row['kind']]=row
        for row in response['transfers']:transfers[int(row['start_sec'])].append(row)
        res=[]
        for start in (2400,2550,2700):
            control=read(H/'selection2400_discrete'/arm/f'action_{start:06}.json')
            green=a.clock_slots(control,net,'SC1','p1',start)
            aliases={}
            for alias,m in modes.items():
                origin=origins[alias];stats=defaultdict(float)
                stats['rate_veh_h']=net['movement_capacity_by_movement_veh_h'][m]
                for i,t in enumerate(range(start,start+150)):
                    rr=by_resource[m,t];q=rr['urban_movement_stock']['available_veh'];intent=rr['urban_movement_intended_limit']['available_veh'];accepted=rr['urban_movement_intended_limit']['accepted_total_veh']
                    assert -1e-8<=accepted<=intent+1e-8 and intent<=q+1e-8
                    stats['accepted_veh']+=accepted;stats['requested_veh']+=intent;stats['receiver_rejection_veh']+=intent-accepted
                    if i==0:stats['initial_ready_veh']=q
                    if i==149:stats['last_step_ready_veh']=q
                    if green[i]:
                        stats['green_seconds']+=1
                        ceiling=stats['rate_veh_h']/3600
                        stats['nominal_service_envelope_veh']+=ceiling
                        if q<=1e-8:stats['green_queue_empty_sec']+=1
                        elif abs(intent-q)<=1e-8:stats['green_ready_limited_sec']+=1
                        elif abs(intent-ceiling)<1e-8:stats['green_rate_limited_sec']+=1
                        else:stats['green_other_limit_sec']+=1
                        if q>ceiling+1e-8:stats['queued_excess_exposure_veh_s']+=q-ceiling
                    for tr in transfers[t]:
                        if tr['target']=='movement:'+m and tr['source']!=tr['target']:stats['ready_arrivals_veh']+=tr['vehicles']
                        if tr['target']=='storage:'+origin and tr['source']!=tr['target']:stats['origin_arrivals_veh']+=tr['vehicles']
                        if tr['target']=='transit:gate:'+origin and tr['source']!=tr['target']:stats['external_gate_inflow_veh']+=tr['vehicles']
                aliases[alias]=dict(stats)
            observed=next(r for r in native['results'][arm] if r['start_sec']==start)
            res.append(dict(start_sec=start,known_native_through_lower_bound=observed['native_known_through_lower_bound'],aliases=aliases))
        result[arm]=res
        del response
    for path in (Path(__file__),H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md',
                 H.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md'):
        PINS[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    report=dict(status='complete_readonly',results=result,source_pins=PINS,
        limitations=['Alias queues are model populations, not distinct physical lanes; known native count is a three-lane lower bound.',
        'Empty/ready-limited labels use actual modeled queue and physical green. Receiving rejection is request minus accepted, not all upstream flow limitations.',
        'External input in transit is not yet ready at the head. No future native boundary was installed.'],
        new_forecasts=0,new_native=0)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

