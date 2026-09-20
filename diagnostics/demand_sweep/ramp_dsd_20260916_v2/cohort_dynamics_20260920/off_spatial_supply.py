"""Conditional test of finite-wave receiving, before changing the plant.

Nonempty-link Hopf-Lax receiving envelope for a triangular FD. Initial vehicle
positions are conservatively projected to finite jam spacing; projection error
is reported, not hidden. Windows with lane exchange are excluded, not silently
treated as single-lane LWR. This test does not identify unserved demand.
"""
from pathlib import Path
import sys
import math
import bisect
import statistics
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES

HERE=Path(__file__).resolve().parent


class ReceivingEnvelope:
    def __init__(self,length,spacing,v_free,wave,positions):
        if any(not math.isfinite(x) or x<=0 for x in (length,spacing,v_free,wave)):
            raise ValueError('Positive finite link geometry and wave speeds required')
        p=sorted(positions);self.length=length;self.spacing=spacing;self.wave=wave
        self.initial=len(p);self.capacity=length/spacing;self.jam=1/spacing
        self.critical=self.jam*wave/(v_free+wave);self.qmax=v_free*self.critical
        self.lag=length/wave
        if len(p)>self.capacity+1e-8 or any(not 0<=x<=length for x in p):
            raise ValueError('Initial vehicles exceed physical storage/position range')
        # Isotonic least-squares projection: no lost vehicles, no extra storage.
        # Adjacent microscopic gaps may be smaller than the mean jam spacing.
        blocks=[]
        for i,x in enumerate(p):
            blocks.append([x-(i+1)*spacing,1])
            while len(blocks)>1 and blocks[-2][0]/blocks[-2][1]>blocks[-1][0]/blocks[-1][1]:
                b=blocks.pop();blocks[-1][0]+=b[0];blocks[-1][1]+=b[1]
        offsets=[];room=length-len(p)*spacing
        for total,n in blocks:offsets.extend([min(room,max(0.,total/n))]*n)
        self.positions=[u+(i+1)*spacing for i,u in enumerate(offsets)]
        self.projection_max_m=max((abs(a-b) for a,b in zip(p,self.positions)),default=0.)
        self.points=sorted({0.,length,*self.positions,*(x-spacing for x in self.positions)})

    def initial_prefix(self,x):
        return sum(min(1.,max(0.,(x-(p-self.spacing))/self.spacing)) for p in self.positions)

    def initial_bound(self,elapsed):
        limit=min(self.length,self.wave*elapsed)
        points=[p for p in self.points if p<=limit]+[limit]
        return self.qmax*elapsed+min(-self.initial_prefix(x)+self.critical*x for x in points)

    def offer(self,elapsed,dt,admitted,departures):
        if not elapsed>=dt>0 or admitted<0:raise ValueError('Invalid causal receiving interval')
        # departures is D(t), at every integer second since initialization;
        # only observations <= the CURRENT interval start may be provided.
        if len(departures)-1>elapsed-dt+1e-8:raise ValueError('Future departure observations supplied')
        bound=self.initial_bound(elapsed)
        lagged=elapsed-self.lag
        if lagged>=0:
            if lagged>len(departures)-1+1e-8:raise ValueError('Wave reaches beyond known departure history')
            lo=int(lagged);hi=min(lo+1,len(departures)-1);f=lagged-lo
            delayed=departures[lo]*(1-f)+departures[hi]*f
            bound=min(bound,delayed+self.capacity-self.initial)
        return max(0.,min(self.qmax*dt,bound-admitted))


class ReceivingTests(unittest.TestCase):
    def test_full_link_cannot_reuse_departure_space_before_wave_arrives(self):
        p=ReceivingEnvelope(60,6,10,3,list(range(6,61,6)))
        self.assertAlmostEqual(p.offer(10,10,0,[0]),0.)
        history=[min(t*p.qmax,1.) for t in range(12)]
        self.assertAlmostEqual(p.offer(21,10,0,history),p.qmax)

    def test_empty_link_is_capacity_limited(self):
        p=ReceivingEnvelope(60,6,10,3,[])
        self.assertAlmostEqual(p.offer(10,10,0,[0]),10*p.qmax)

    def test_initial_position_projection_preserves_mass_and_finite_storage(self):
        p=ReceivingEnvelope(60,6,10,3,[2,4,5,58,59])
        self.assertAlmostEqual(p.initial_prefix(60),5.)
        self.assertTrue(all(b-a>=6-1e-9 for a,b in zip([0]+p.positions,p.positions)))
        self.assertLessEqual(p.positions[-1],60)

    def test_initial_location_changes_supply_at_equal_total_stock(self):
        upstream=ReceivingEnvelope(60,6,10,3,[6,12,18,24,30])
        downstream=ReceivingEnvelope(60,6,10,3,[36,42,48,54,60])
        self.assertAlmostEqual(upstream.offer(5,5,0,[0]),0.)
        self.assertGreater(downstream.offer(5,5,0,[0]),0.)

    def test_future_departures_are_rejected(self):
        p=ReceivingEnvelope(60,6,10,3,[])
        with self.assertRaises(ValueError):p.offer(10,10,0,[0,1])


def main():
    out=HERE/'off_spatial_supply_v1';out.mkdir(exist_ok=False)
    test=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReceivingTests))
    assert test.wasSuccessful()
    observed=e.load(HERE/'off_space_wave_v2/result.json')
    train=[r for r in observed['results']['13']['events'] if 1050<=r['leader_start_s']<3300
           and r['lane']==2 and r['lag_s']>0 and r['stopped_gap_m']<=20]
    wave=sum(r['stopped_gap_m'] for r in train)/sum(r['lag_s'] for r in train)
    profile=e.load(MODEL/'port_profile.json');results={}
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,HERE/'port_origin_split_v1/config.json')
        port=model.offramps['10643'];length=port['length_m'];spacing=length*port['lanes']/port['storage_capacity_veh']
        frames={r['time_s']:{vid:(lane,p,v) for vid,lane,p,v in r['vehicles']}
                for r in e.load(HERE/f'off_space_wave_v2/s{seed}_frames.json')['frames']}
        rows=[];excluded=[]
        for cutoff in range(1050,4201,150):
            # Require a full150s without internal source/sink from lane change.
            exchanges=[]
            for t in range(cutoff+1,cutoff+151):
                a,b=frames[t-1],frames[t]
                exchanges.extend((t,vid) for vid in set(a)&set(b) if a[vid][0]!=b[vid][0])
            if exchanges:excluded.append({'start':cutoff,'lane_changes':len(exchanges)});continue
            for lane in (1,2):
                initial=[p for l,p,v in frames[cutoff].values() if l==lane]
                envelope=ReceivingEnvelope(length,spacing,profile['travel_speed_kmh']['10643']/3.6,wave,initial)
                admitted=[0];departed=[0]
                for t in range(cutoff+1,cutoff+151):
                    a,b=frames[t-1],frames[t]
                    admitted.append(admitted[-1]+sum(b[v][0]==lane for v in set(b)-set(a)))
                    departed.append(departed[-1]+sum(a[v][0]==lane for v in set(a)-set(b)))
                for delta in range(0,150,10):
                    current=frames[cutoff+delta];vehicles=sorted((p,v) for l,p,v in current.values() if l==lane)
                    native=admitted[delta+10]-admitted[delta]
                    offer=envelope.offer(delta+10,10,admitted[delta],departed[:delta+1])
                    point=max(0.,envelope.capacity-len(vehicles))
                    assert len(vehicles)==len(initial)+admitted[delta]-departed[delta]
                    rows.append({'start_s':cutoff+delta,'initialization_s':cutoff,'lane':lane,
                        'actual_arrivals':native,'point_free_veh':point,'point_capped_veh':min(point,envelope.qmax*10),
                        'finite_wave_offer_veh':offer,'underbound_veh':max(0.,native-offer),
                        'entry_near_stopped':bool(vehicles and vehicles[0][0]<6 and vehicles[0][1]<5),
                        'initial_position_projection_max_m':envelope.projection_max_m})
        selected=[r for r in rows if r['lane']==2]
        summary={'evaluated_10s_lane2':len(selected),'excluded_150s_windows_with_lane_changes':len(excluded),
            'below_observed_by_more_than_one':sum(r['underbound_veh']>1+1e-9 for r in selected),
            'max_underbound_veh':max((r['underbound_veh'] for r in selected),default=0.),
            'finite_offer_below_point_capped':sum(r['finite_wave_offer_veh']<r['point_capped_veh']-1e-7 for r in selected),
            'entry_near_stopped_samples':sum(r['entry_near_stopped'] for r in selected),
            'entry_near_stopped_mean_offers':{key:statistics.mean(r[key] for r in selected if r['entry_near_stopped'])
                for key in ('point_capped_veh','finite_wave_offer_veh','actual_arrivals')}
                if any(r['entry_near_stopped'] for r in selected) else {}}
        results[str(seed)]={'summary':summary,'rows':rows,'excluded':excluded}
        print(seed,summary,flush=True)
    e.save(out/'result.json',{'wave_m_s':wave,'wave_training':'seed13 NC1050..3300 lane2 stable stopped pairs only',
        'training_events':len(train),'tests_passed':test.testsRun,'results':results,'no_gain_fitting':True,
        'source':'https://arxiv.org/html/1405.7080v1','native_runs_started':0,'adopted':False,
        'scope':'Conditional10s capacity-bound check using known current cumulative entries and PAST exits only; not a450s autonomous forecast.',
        'identification_limit':'Actual admitted flow is a lower bound on feasible service, not observed demand or saturation capacity. Lower offers are not scored as better merely because arrivals were small.',
        'projection':'Isotonic initial position projection preserves every vehicle and total storage; spatial displacement recorded per window.'})


if __name__=='__main__':main()
