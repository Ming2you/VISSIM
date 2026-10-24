"""Identify connector travel from entry speed, separately from exit service."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.merge_drain_response_20260919.audit import *
import math

def travel(distance,speed,cruise,accel):
    v0=min(max(speed/3.6,0.),cruise/3.6);vc=cruise/3.6
    distance_acc=(vc*vc-v0*v0)/(2*accel)
    if distance<=distance_acc:return 2*distance/(math.sqrt(v0*v0+2*accel*distance)+v0)
    return (vc-v0)/accel+(distance-distance_acc)/vc

def pairs(data,c,end=4500):
    arrivals={r['vehicle']:r for r in data.events if r['connector']==c and r['kind']=='arrival'}
    return [{'arrival_sec':int(arrivals[r['vehicle']]['time_s']),'departure_sec':int(r['time_s']),
             'speed_kmh':float(arrivals[r['vehicle']]['speed_kmh']),
             'position_m':float(arrivals[r['vehicle']]['position_m']),
             'actual_sec':float(r['residence_s'])}
            for r in data.events if r['connector']==c and r['kind']=='departure' and r['residence_s']
            and float(r['time_s'])<=end and r['vehicle'] in arrivals and float(arrivals[r['vehicle']]['time_s'])>=900]

def main():
    out=HERE/'transit_fit_v1';out.mkdir(exist_ok=False)
    data=prepare_data(H/'controller_response_4500_v1/none')
    geometry={str(b['connector']):b for b in data.definitions.values() if b['kind']=='offramp'}
    speeds=e.load(BASE/'port_profile.json')['travel_speed_kmh']
    chosen={};fit={}
    for c in ['10483','10682']:
        samples=pairs(data,c);length=geometry[c]['length_m'];vc=speeds[c]
        candidates=[]
        for a in [.1,.2,.35,.5,.75,1.,1.5,2.,3.]:
            errors=[travel(max(0,length-r['position_m']),r['speed_kmh'],vc,a)-r['actual_sec'] for r in samples]
            candidates.append({'accel_mps2':a,'mae_sec':statistics.mean(abs(x) for x in errors),'bias_sec':statistics.mean(errors)})
        best=min(candidates,key=lambda r:r['mae_sec']);chosen[c]=best['accel_mps2']
        fit[c]={'samples':len(samples),'cruise_kmh':vc,'candidates':candidates,'selected':best}
    write(out/'fit.json',fit);result={}
    for seed,folder,bank,start in CASES:
        result[str(seed)]={}
        for arm in ['none','rm_ramp','vsl','both']:
            data=prepare_data(folder if arm=='none' else bank/'observations'/arm);rs={}
            for c in chosen:
                samples=[r for r in pairs(data,c) if start<r['departure_sec']<=start+450]
                length=geometry[c]['length_m'];vc=speeds[c];a=chosen[c]
                errors={name:[(max(0,length-r['position_m'])*3.6/vc if name=='constant' else
                    travel(max(0,length-r['position_m']),r['speed_kmh'],vc,a))-r['actual_sec'] for r in samples]
                    for name in ['constant','entry_speed']}
                rs[c]={'samples':len(samples),'actual_mean_sec':statistics.mean(r['actual_sec'] for r in samples),
                    'scores':{n:{'mae_sec':statistics.mean(abs(x) for x in er),'bias_sec':statistics.mean(er),
                                'predicted_mean_sec':statistics.mean(er)+statistics.mean(r['actual_sec'] for r in samples)} for n,er in errors.items()}}
            result[str(seed)][arm]=rs
        print(seed,result[str(seed)],flush=True)
    write(out/'evaluation.json',result)
    write(out/'protocol.json',{'training':'seed13 no-control arrivals after900; complete departures by4500',
        'metric':'Vehicle remaining traversal time after first native connector sample',
        'cruise':'Frozen pre900 connector transit proxy','controls_not_used_to_fit':True,
        'limitations':'Actual entry speed conditions the component test; this is not a coupled450s forecast. Censored vehicles excluded.',
        'selected_accel_mps2':chosen})

if __name__=='__main__':main()
