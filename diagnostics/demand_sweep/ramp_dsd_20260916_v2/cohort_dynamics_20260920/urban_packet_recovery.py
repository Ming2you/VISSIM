"""Bounded71 body-coherent recovery experiment, never a production adapter.

One vehicle owns one longitudinal position. A pending lane change occupies
both lanes for space only, and is counted once for mass and waiting cost.
Known signals and past-only entry forecasts drive the local experiment.
"""
from pathlib import Path
from collections import Counter, defaultdict
import sys, copy, math, hashlib, argparse, unittest
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.route_access_observer import e, observe, geometry
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_route_transport import unassigned_continuation
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_receiving_probe import dataset

HERE=Path(__file__).resolve().parent


class LaneBodies:
    def __init__(self,past,start,network,program,offset,lag,change_time,cooperative=False):
        if any(t>start for t in past):raise ValueError('Future traffic is not an initial condition')
        self.time=start;self.start=start;self.program=program;self.offset=offset
        self.lag=lag;self.change_time=change_time;self.cooperative=cooperative
        root=ET.parse(network).getroot();self.routes,self.exits=geometry(network)
        links={int(x.get('no')):x for x in root.findall('./links/link')}
        behavior=next(x for x in root.findall('./drivingBehaviors/drivingBehavior') if x.get('no')=='1')
        self.gap=float(behavior.get('w74ax'));self.speed=float(links[71].get('mesoSpeed'))/3.6
        self.stop={int(h.get('lane').split()[1]):float(h.get('pos')) for h in root.findall('./signalHeads/signalHead') if h.get('lane','').startswith('71 ')}
        self.emergency={d:float(links[d].get('emergStopDist')) for d in self.exits}
        self.entry={}
        for link in links.values():
            p=link.find('./toLinkEndPt')
            if p is not None and p.get('lane','').startswith('71 '):
                first=int(p.get('lane').split()[1]);count=len(link.findall('./lanes/lane'))
                for lane in range(first,first+count):
                    if lane in self.entry:raise ValueError('Ambiguous lane entry geometry')
                    self.entry[lane]=float(p.get('pos'))
        current=observe(past[start],self.routes,self.exits)
        self.nodes={v['vehicle']:self.node(v) for v in current['vehicles'] if v['link']==71}
        self.initial=set(self.nodes);self.admitted=set();self.departed={};self.events=[]
        self.hist={t:{v[0]:v[3] for v in past[t]['vehicles'] if v[1]==71}
                   for t in range(start-lag,start+1)}
        self.pending=[];self.next_id=-1;self.offered=0;self.vehicle_seconds=0.;self.outside_seconds=0.
        self.checks=0;self.history=defaultdict(list)
        for t in range(start-149,start+1):
            before={v[0] for v in past[t-1]['vehicles'] if v[1]==71}
            state=observe(past[t],self.routes,self.exits)
            for v in state['vehicles']:
                if v['link']==71 and v['vehicle'] not in before:
                    self.history[(t-start-1)%150].append(v)
        self.initial_overlap=self.overlaps({i:v['x'] for i,v in self.nodes.items()})
        self.check()

    def node(self,v):
        lane=v['lane'];target=None;finish=None
        if v['lane_change'] in ('Left','Right') and v['current_lane_change_destination']:
            target=v['current_lane_change_destination']
            if target==lane:
                lane=target-1 if v['lane_change']=='Left' else target+1
            if abs(target-lane)!=1:raise ValueError('Unsupported current maneuver')
            finish=self.time+1 # Remaining fraction is unresolved at1s recording.
        return dict(id=v['vehicle'],lane=lane,x=v['position_m'],length=v['length_m'],dest=v['connector'],
                    fallback=unassigned_continuation(v,self.routes),target=target,finish=finish)

    @staticmethod
    def lanes(v):return {v['lane'],v['target']} if v['target'] else {v['lane']}

    def green(self,t,lane):return self.program.state_at(t,2 if lane<=3 else 5,controller_offset_sec=self.offset)=='GREEN'

    def destination(self,v):
        if v['dest'] is not None:return v['dest']
        if v['fallback']:
            candidates=[d for d,x in self.exits.items() if v['lane'] in x['lanes'] and x['position_m']>=v['x']-1e-8]
            if candidates:return min(candidates,key=lambda d:self.exits[d]['position_m'])
        return None

    def route_limit(self,v):
        d=self.destination(v)
        if d is None:return max(x['position_m'] for x in self.exits.values())
        ex=self.exits[d];lane=v['target'] or v['lane']
        if lane in ex['lanes']:return math.inf
        changes=min(abs(lane-l) for l in ex['lanes'])
        # Native connector rule is a hypothesis for the stopping frontier;
        # integer rounding/lateral body geometry are not reproduced here.
        return ex['position_m']-self.emergency[d]-5*(changes-1)-(2.5 if lane%2 else 0.)

    def overlaps(self,positions):
        result=set()
        for lane in range(1,6):
            cars=sorted((v for v in self.nodes.values() if lane in self.lanes(v)),key=lambda v:positions[v['id']])
            for back,front in zip(cars,cars[1:]):
                if positions[front['id']]-front['length']<positions[back['id']]-1e-7:
                    result.add((back['id'],front['id'],lane))
        return result

    def check(self):
        if set(self.nodes)&set(self.departed):raise ArithmeticError('Vehicle both present and departed')
        if set(self.nodes)|set(self.departed)!=self.initial|self.admitted:raise ArithmeticError('Vehicle conservation failed')
        if len(self.pending)+len(self.admitted)!=self.offered:raise ArithmeticError('Boundary demand disappeared')
        if any(not math.isfinite(v['x']) or v['length']<=0 for v in self.nodes.values()):raise ArithmeticError('Invalid body state')
        overlap=self.overlaps({i:v['x'] for i,v in self.nodes.items()})
        if overlap-self.initial_overlap:raise ArithmeticError(('New body overlap',overlap-self.initial_overlap))
        self.initial_overlap &= overlap
        self.checks+=1

    def step(self):
        t=self.time;old=copy.deepcopy(self.nodes);old_n=len(old)
        destinations={i:self.destination(v) for i,v in old.items()}
        proposed={};free={};past=self.hist[t+1-self.lag]
        # Newell-like longitudinal motion. No second service/headway ceiling.
        for i,v in old.items():
            limit=v['x']+self.speed
            for lane in self.lanes(v):
                leaders=[w for w in old.values() if w['id']!=i and lane in self.lanes(w) and w['x']>=v['x']]
                if leaders:
                    lead=min(leaders,key=lambda w:(w['x'],w['id']))
                    now_gap=max(0.,lead['x']-lead['length']-v['x'])
                    gap=min(self.gap,now_gap)
                    limit=min(limit,past.get(lead['id'],lead['x'])-lead['length']-gap)
            lane=v['target'] or v['lane']
            if v['x']<=self.stop[lane] and not self.green(t+1-self.lag,lane):
                limit=min(limit,self.stop[lane]-self.gap)
            if v['target'] and v['finish']>t+1 and destinations[i] is not None:
                limit=min(limit,self.exits[destinations[i]]['position_m'])
            free[i]=max(v['x'],limit)
            proposed[i]=max(v['x'],min(free[i],self.route_limit(v)))
        # Mandatory changes are considered downstream first. There is no
        # arbitrary exchange-rate bonus and no simultaneous swap of full lanes.
        for i in sorted(old,key=lambda j:(-old[j]['x'],j)):
            v=self.nodes[i];d=self.destination(v)
            if v['target'] or d is None or v['lane'] in self.exits[d]['lanes']:continue
            if v['x']>self.exits[d]['position_m']:continue
            required=self.exits[d]['lanes'];lane=v['lane']+(1 if v['lane']<min(required) else -1)
            others=[w for j,w in self.nodes.items() if j!=i and lane in self.lanes(w)]
            front=min((w for w in others if proposed[w['id']]>=v['x']),key=lambda w:proposed[w['id']],default=None)
            back=max((w for w in others if proposed[w['id']]<v['x']),key=lambda w:proposed[w['id']],default=None)
            x=free[i]
            x=min(x,self.exits[d]['position_m'],self.route_limit(dict(v,target=lane)))
            if front:x=min(x,proposed[front['id']]-front['length']-self.gap)
            if v['x']<=self.stop[lane] and not self.green(t+1,lane):x=min(x,self.stop[lane]-self.gap)
            rear=(old[back['id']]['x'] if self.cooperative else proposed[back['id']])+v['length']+self.gap if back else -math.inf
            if x<v['x']-1e-8 or x<rear-1e-8:continue
            if back and self.cooperative:proposed[back['id']]=min(proposed[back['id']],x-v['length']-self.gap)
            proposed[i]=x;v['target']=lane;v['finish']=t+1+self.change_time
            self.events.append(dict(time_s=t+1,event='change_start',vehicle=i,source=v['lane'],target=lane))
        for i,v in self.nodes.items():
            v['x']=proposed[i]
            if v['target'] and v['finish']<=t+1:
                v['lane']=v['target'];v['target']=None;v['finish']=None
                self.events.append(dict(time_s=t+1,event='change_complete',vehicle=i,lane=v['lane']))
        # Collision checking also covers the temporary occupation of two lanes.
        self.check()
        for i,v in list(self.nodes.items()):
            # Use the exit chosen BEFORE moving; an unrouted vehicle that just
            # crossed a connector must not lose that exit from its candidate set.
            d=destinations[i]
            if not v['target'] and d is not None and v['lane'] in self.exits[d]['lanes'] and v['x']>=self.exits[d]['position_m']:
                self.departed[i]=dict(time_s=t+1,connector=d)
                del self.nodes[i]
                self.events.append(dict(time_s=t+1,event='exit',vehicle=i,connector=d))
        for template in self.history[(t-self.start)%150]:
            v=self.node(template);v.update(id=self.next_id,x=self.entry[template['lane']],lane=template['lane'],target=None,finish=None)
            self.next_id-=1;self.pending.append(v);self.offered+=1
        pending=[]
        for v in self.pending:
            others=[w for w in self.nodes.values() if v['lane'] in self.lanes(w)]
            overlap=any(not (v['x']+self.gap<=w['x']-w['length'] or w['x']+self.gap<=v['x']-v['length']) for w in others)
            if overlap:pending.append(v)
            else:self.nodes[v['id']]=v;self.admitted.add(v['id'])
        self.pending=pending
        self.vehicle_seconds+=old_n # Start-of-step count, exactly one per body.
        self.outside_seconds+=len(self.pending)
        self.time=t+1;self.hist[self.time]={i:v['x'] for i,v in self.nodes.items()}
        self.check()


class Contracts(unittest.TestCase):
    def toy(self,nodes,green=True):
        class Signal:
            def state_at(self,*a,**kw):return 'GREEN' if green else 'RED'
        p=LaneBodies.__new__(LaneBodies)
        p.time=p.start=0;p.program=Signal();p.offset=0;p.lag=p.change_time=2;p.cooperative=False
        p.gap=1.5;p.speed=10.;p.stop={i:79. for i in range(1,6)}
        p.exits={10634:dict(lanes=[1,2,3],position_m=81.),10635:dict(lanes=[4,5],position_m=81.),10642:dict(lanes=[1],position_m=37.)}
        p.emergency={i:5. for i in p.exits};p.entry={i:3. for i in range(1,6)}
        p.nodes={v['id']:v for v in copy.deepcopy(nodes)};p.initial=set(p.nodes);p.admitted=set();p.departed={};p.events=[]
        p.hist={t:{v['id']:v['x'] for v in nodes} for t in (-2,-1,0)}
        p.pending=[];p.next_id=-1;p.offered=0;p.vehicle_seconds=p.outside_seconds=0.;p.checks=0;p.history=defaultdict(list)
        p.initial_overlap=set();p.check();return p

    def vehicle(self,i,lane,x,dest):return dict(id=i,lane=lane,x=x,length=4.,dest=dest,fallback=False,target=None,finish=None)

    def test_pending_change_has_one_cost_and_two_occupied_lanes(self):
        v=self.vehicle(1,3,20.,10635);v.update(target=4,finish=2)
        p=self.toy([v]);self.assertEqual(p.lanes(p.nodes[1]),{3,4})
        p.step();p.step();self.assertEqual(p.vehicle_seconds,2.);self.assertEqual(p.nodes[1]['lane'],4)

    def test_full_conflicting_heads_cannot_exchange_through_each_other(self):
        p=self.toy([self.vehicle(1,3,73.,10635),self.vehicle(2,4,73.,10634)],green=False)
        for _ in range(5):p.step()
        self.assertEqual(len(p.nodes),2);self.assertFalse(p.events);self.assertEqual(p.vehicle_seconds,10.)

    def test_unrouted_normal_exit_is_retained_after_crossing(self):
        v=self.vehicle(1,1,80.,None);v['fallback']=True;p=self.toy([v]);p.step()
        self.assertEqual(p.departed[1]['connector'],10634);self.assertEqual(len(p.nodes),0)

    def test_pending_body_does_not_travel_outside_road(self):
        v=self.vehicle(1,3,80.,10635);v.update(target=4,finish=3);p=self.toy([v])
        p.step();self.assertEqual(p.nodes[1]['x'],81.);self.assertFalse(p.departed)
        p.step();self.assertEqual(p.nodes[1]['x'],81.);p.step();self.assertIn(1,p.departed)

    def test_new_projected_overlap_is_rejected(self):
        p=self.toy([self.vehicle(1,3,50.,10634),self.vehicle(2,3,60.,10634)])
        p.nodes[2]['x']=52.
        with self.assertRaises(ArithmeticError):p.check()

    def test_reservation_uses_capped_leader_position(self):
        a=self.vehicle(1,3,80.,10635);a.update(target=4,finish=3)
        b=self.vehicle(2,2,70.,10635)
        p=self.toy([a,b]);p.step()
        self.assertFalse(p.overlaps({i:v['x'] for i,v in p.nodes.items()}))
        self.assertLessEqual(p.nodes[2]['x'],p.nodes[1]['x']-p.nodes[1]['length'])

    def test_future_initial_observation_is_rejected(self):
        with self.assertRaises(ValueError):LaneBodies({2:{}},1,None,None,0,2,2)


def main():
    suite=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    if not suite.wasSuccessful():raise AssertionError('Body transport contracts failed')
    out=HERE/'urban_packet_recovery_v3';out.mkdir(exist_ok=False)
    e.save(out/'tests.json',dict(passed=True,contracts=suite.testsRun))
    network=HERE/'route_state_native_v1/none_s23/source/baseline.inpx'
    proof=HERE/'urban_drain_observations_v5/s23_none_evidence.json'
    _,program,offset=dataset(proof.with_name('s23_none.csv'),proof)
    # Existing NC13 queue-wave lag, not fitted to these control outcomes.
    constants=e.load(HERE/'off_spatial_transport_cumulative_v1/protocol.json')
    lag=int(constants['headway_s']);change_time=lag
    summaries={};pins={}
    for case in ('none_s23','vsl_s23'):
        path=HERE/'route_state_native_v1'/case/'analysis/frames.json'
        frames={f['time_s']:f for f in e.load(path)['frames']}
        for start in (2523,2823):
            past={t:f for t,f in frames.items() if start-150<=t<=start}
            for cooperative in (False,True):
                name=f'{case}_{start}_'+('yield' if cooperative else 'fixed_gap')
                model=LaneBodies(past,start,network,program,offset,lag,change_time,cooperative)
                trace=[]
                try:
                    for _ in range(25):
                        model.step()
                        trace.append(dict(time_s=model.time,n=len(model.nodes),departed=len(model.departed),outside_n=len(model.pending),
                                          nodes=list(copy.deepcopy(model.nodes).values())))
                    status='COMPLETED'
                except Exception as error:
                    status='FAILED';failure=repr(error)
                summary=dict(status=status,initial_n=len(model.initial),departed=len(model.departed),
                             final_n=len(model.nodes),outside_n=len(model.pending),checks=model.checks,
                             body_ttt_veh_s=model.vehicle_seconds,failure=failure if status=='FAILED' else None)
                summaries[name]=summary
                e.save(out/f'{name}.json',dict(summary=summary,trace=trace,events=model.events,departed=model.departed,
                                              final_nodes=model.nodes,initial_ids=sorted(model.initial)))
                print(name,summary,flush=True)
        pins[str(path.relative_to(e.ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for p in (Path(__file__),network,proof,proof.with_name('s23_none.csv'),HERE/'off_spatial_transport_cumulative_v1/protocol.json'):
        pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    e.save(out/'result.json',dict(summaries=summaries,source_pins=pins,production_adopted=False,qualified=False,
        future_traffic_inputs=False,lag_s=lag,change_duration_s=change_time,new_native_runs=0,
        assumptions=['One critical urban link only; upstream boundary repeats its past150s accepted entries.',
                     'Integer vehicles, dual-lane space during changes, one mass/cost account per vehicle.',
                     'Change duration provisionally equals existing2s lag; not calibrated as native lane-change duration.',
                     'Initial ongoing maneuvers have unresolved remaining duration, provisionally1s.',
                     'Constant free speed and delayed position following do not reproduce full microscopic acceleration.',
                     'No normal-release labels or future disappearance is used in the forecast.']))


def matched_fluid():
    """Same cutoff/link/arrival forecast for the prior fluid representation."""
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_route_transport import UrbanTransport,FIFO,tagged
    out=HERE/'urban_packet_matched_fluid_v1';out.mkdir(exist_ok=False)
    network=HERE/'route_state_native_v1/none_s23/source/baseline.inpx'
    proof=HERE/'urban_drain_observations_v5/s23_none_evidence.json'
    _,program,offset=dataset(proof.with_name('s23_none.csv'),proof)
    constants=e.load(HERE/'off_spatial_transport_cumulative_v1/protocol.json')
    wave=e.load(HERE/'off_spatial_supply_v1/result.json')['wave_m_s']
    summaries={};pins={}
    for case in ('none_s23','vsl_s23'):
        path=HERE/'route_state_native_v1'/case/'analysis/frames.json'
        frames={f['time_s']:f for f in e.load(path)['frames']}
        for start in (2523,2823):
            past={t:f for t,f in frames.items() if start-150<=t<=start}
            body=LaneBodies(past,start,network,program,offset,int(constants['headway_s']),int(constants['headway_s']))
            current=observe(past[start],body.routes,body.exits)
            current['vehicles']=[v for v in current['vehicles'] if v['link']==71]
            model=UrbanTransport(current,network,program,offset,body.speed,6.,wave,True,(),True)
            assert model.initial==Counter({tagged(v):1. for v in current['vehicles']})
            pending=defaultdict(FIFO);trace=[];nxt=-1
            for t in range(start,start+25):
                # LaneBodies admits at the END of this same1s interval. The
                # fluid solver must see those offers only on the following step.
                model.step({str(lane):((71,lane,0),q) for lane,q in pending.items()})
                for v in body.history[(t-start)%150]:
                    label=(v['connector'],nxt);nxt-=1
                    pending[v['lane']].append(label,1.)
                    if unassigned_continuation(v,body.routes):model.unrouted_labels.add(label)
                trace.append(dict(time_s=t+1,departed=[[[*label],n] for label,n in model.departed.items()],
                                  outside_n=sum(q.stock for q in pending.values()),n=sum(model.counts().values())))
            summary=dict(initial_n=sum(model.initial.values()),departed=sum(model.departed.values()),
                         final_n=sum(model.counts().values()),outside_n=sum(q.stock for q in pending.values()),checks=model.checks,
                         body_ttt_veh_s=model.vehicle_seconds,projection_m=model.projection)
            name=f'{case}_{start}';summaries[name]=summary
            e.save(out/f'{name}.json',dict(summary=summary,trace=trace,initial_ids=sorted(body.initial)))
            print(name,summary,flush=True)
        pins[str(path.relative_to(e.ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for p in (Path(__file__),HERE/'urban_route_transport.py',network,proof,proof.with_name('s23_none.csv'),HERE/'off_spatial_supply_v1/result.json'):
        pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    e.save(out/'result.json',dict(summaries=summaries,source_pins=pins,qualified=False,
        scope='71 only, identical cutoff and past-arrival templates. Integer boundary admission versus fluid admission remains a representation difference.',
        boundary_clock='Offers created at interval end; body may insert them immediately at entry position, fluid uses next update. This creates up to1s of boundary timing difference; initial-cohort events are primary comparison.',
        future_traffic_inputs=False,production_adopted=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--matched-fluid',action='store_true');args=parser.parse_args()
    if args.matched_fluid:matched_fluid()
    else:main()
