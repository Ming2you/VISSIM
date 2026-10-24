"""Causal repeated-history boundary ablation, keeping every 150s total.

It is not an urban green/offset forecast or an identified signal-period model:
the network has multiple native cycle lengths. The last150s waveform is repeated
only to test information lost by averaging. It must not be promoted merely on
fit without tracing each port's feeding/draining signals and travel times.
No future arrival or drainage sample is accessed.
"""
from study import *

def phase_window(case,item,kind):
    w=copy.deepcopy(item['window']);cutoff=item['start'];data=case['data'];period=150
    for step in w['boundary_steps']:
        future_end=(step['window_start_s']//30+1)*30
        past_end=cutoff-((cutoff-future_end)%period)
        assert cutoff-period<past_end<=cutoff
        if kind in ['arrivals','both']:
            for mid,r in case['model'].ramps.items():
                step['ramp_arrival_vph'][mid]=float(data.ports[past_end,str(r['connector'])]['arrivals_veh'])*120.
        if kind in ['drain','both']:
            for conn in case['model'].offramps:
                step['off_drain_vph'][conn]=float(data.ports[past_end,conn]['departures_veh'])*120.
    # Holding the total fixed separates timing information from demand scaling.
    for key in ['ramp_arrival_vph','off_drain_vph']:
        for conn in w['boundary_steps'][0][key]:
            before=sum(s[key][conn] for s in item['window']['boundary_steps'])
            after=sum(s[key][conn] for s in w['boundary_steps'])
            if abs(before-after)>1e-7:raise AssertionError(('Changed boundary total',key,conn,before,after))
    return w

def main():
    out=HERE/'phase_probe_v1';out.mkdir(exist_ok=False);cases=build_cases()
    params=e.load(BASE/'selected_parameters.json')['parameters'];results={}
    for kind in ['arrivals','drain','both']:
        results[kind]={}
        for seed,case in cases.items():
            modified={**case,'items':{name:{**item,'window':phase_window(case,item,kind)} for name,item in case['items'].items()}}
            results[kind][str(seed)]=assess(modified,{},params)
            r=results[kind][str(seed)]
            print(kind,seed,'loss',round(r['absolute_loss'],4),round(r['response_loss'],4),
                'deltas',{a:round(x['predicted_total'],4) for a,x in r['deltas'].items()},flush=True)
    e.save(out/'results.json',{'records':results,'history_sec':150,'total_arrivals_and_drainage_per_cycle_preserved':True,
        'scope':'Repeated150s history waveform hypothesis only; actual signal periods differ. No future observations, no command reward, no flow/capacity bonus'})

if __name__=='__main__':main()
