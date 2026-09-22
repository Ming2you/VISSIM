"""Conserved lane-local gap transport probe; not a production adapter.

Finite response v=min(v_free, positive gap / headway) is a hypothesis motivated
by measured startup waves. Its headway is NOT claimed to equal a driver delay.
Fractional vehicle packets retain positions and footprints; no gain fitting.
"""
from pathlib import Path
import sys,math,copy,json,hashlib,unittest,argparse
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
import canonical_harness as ch
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_spatial_supply import ReceivingEnvelope

HERE=Path(__file__).resolve().parent


from evaluation.controllers.physical_urban_transport import CumulativeLane


class CumulativeTests(unittest.TestCase):
    def full(self):return CumulativeLane(150,900,60,[(900-6*i,0,4.5) for i in range(150)],0,3.2557309454394003)

    def test_saturated_external_service_is_not_counted_twice(self):
        for service in (360,900):
            p=self.full();counts={}
            for t in range(180):
                p.release(t,1,service)
                if t+1 in (60,180):counts[t+1]=p.departed
            self.assertAlmostEqual((counts[180]-counts[60])*30,service)

    def test_intrinsic_flow_limit_is_separate_from_outlet_service(self):
        p=self.full()
        for t in range(120):p.release(t,1,3600)
        self.assertAlmostEqual(p.departed,p.envelope.qmax*120)

    def test_red_and_green_do_not_add_another_service_headway(self):
        p=self.full()
        for t in range(30):p.release(t,1,0)
        self.assertEqual(p.departed,0)
        for t in range(30,90):p.release(t,1,900)
        self.assertAlmostEqual(p.departed,15)

    def test_empty_travel_and_unused_service(self):
        p=CumulativeLane(10,60,36,[],0,3)
        p.release(0,1,3600);p.receiving(1);p.accept(1,.1)
        for t in range(1,7):p.release(t,1,0)
        self.assertEqual(p.departed,0)
        p.release(7,1,180);self.assertAlmostEqual(p.departed,.05)
        p.release(8,1,180);self.assertAlmostEqual(p.departed,.1)
        self.assertAlmostEqual(p.stock,0)

    def test_no_early_travel_exit(self):
        p=CumulativeLane(10,60,36,[],0,3)
        p.release(0,1,3600);p.receiving(1);p.accept(1,.1)
        for t in range(1,6):p.release(t,1,3600)
        self.assertEqual(p.departed,0)
        p.release(6,1,3600);self.assertAlmostEqual(p.departed,.1)

    def test_full_link_departure_space_propagates_with_delay(self):
        p=CumulativeLane(10,60,36,[(6*i,0,4.5) for i in range(1,11)],0,3)
        for t in range(20):
            p.release(t,1,360)
            self.assertAlmostEqual(p.receiving(1),0)
        p.release(20,1,360);self.assertAlmostEqual(p.receiving(1),.1)

    def test_fractional_acceptance_conserves_during_continuous_input(self):
        p=CumulativeLane(10,60,36,[],0,3)
        for t in range(120):
            p.release(t,1,360)
            n=min(.13,p.receiving(1));p.accept(t+1,n)
            self.assertAlmostEqual(p.stock,p.initial+p.admitted-p.departed)
        self.assertGreater(p.admitted,10)


class SpatialLane:
    def __init__(self,capacity,length,speed,vehicles,start,headway,clearance,*,delayed=False):
        if min(capacity,length,speed,headway,clearance)<=0:raise ValueError('Positive transport data required')
        # vehicles = current position, speed, measured physical vehicle length.
        if not vehicles:raise ValueError('Current measured composition required for this bounded probe')
        if any(not 0<=p<=length or v<0 or size<=0 for p,v,size in vehicles):raise ValueError('Invalid current vehicle')
        self.capacity=capacity;self.length=length;self.vfree=speed/3.6;self.headway=headway
        self.mean_footprint=sum(size+clearance for p,v,size in vehicles)/len(vehicles)
        self.packets=[dict(x=p,w=1.,footprint=size+clearance) for p,v,size in sorted(vehicles,reverse=True)]
        self.initial=self.stock;self.admitted=self.departed=self.residence_veh_h=0.
        self.internal_in=self.internal_out=0.;self.time=start;self.counters=0
        self.delayed=delayed;self.nodes={};self.next_id=0
        if delayed:
            if headway!=int(headway) or headway<1:raise ValueError('Delay needs integer observed seconds')
            ordered=sorted(vehicles,reverse=True)
            for i,p in enumerate(self.packets):
                previous=self.packets[i-1] if i else None
                correction=(previous['x']-p['x']-previous['footprint']) if previous and ordered[i][1]<1 and ordered[i-1][1]<1 else 0.
                self._register(p,previous,start,ordered[i][1]/3.6,correction)
        if self.stock>self.capacity+1e-8:raise ValueError('Initial storage exceeded')

    @property
    def stock(self):return math.fsum(p['w'] for p in self.packets)

    @property
    def ready(self):return math.fsum(p['w'] for p in self.packets if p['x']>=self.length-1e-8)

    def receiving(self):
        if not self.packets:return self.capacity
        tail=self.packets[-1];gap=tail['x']-tail['w']*tail['footprint']
        # A front may enter at x=0 with the rear outside the connector. At most
        # one such boundary vehicle is represented; do not erase its full mass.
        positional=0. if gap < -1e-8 else 1.+max(0.,gap)/self.mean_footprint
        return max(0.,min(self.capacity-self.stock,positional))

    def check(self):
        if abs(self.stock-self.initial-self.admitted+self.departed)>1e-7:raise ArithmeticError('Spatial mass imbalance')
        if self.stock>self.capacity+1e-7 or any(p['w']<=0 or not 0<=p['x']<=self.length+1e-8 for p in self.packets):
            raise ArithmeticError('Spatial stock/position invalid')
        if any(a['x']<b['x']-1e-8 for a,b in zip(self.packets,self.packets[1:])):raise ArithmeticError('Packet overtaking')
        self.counters+=1

    def _register(self,p,leader,t,speed,correction=0.):
        p.update(key=self.next_id,leader=None if leader is None else leader['key'],correction=correction,
            rear_history={t-j:p['x']-speed*j-p['w']*p['footprint'] for j in range(int(self.headway)+1)})
        self.nodes[self.next_id]=p;self.next_id+=1

    def _record_rears(self,t):
        for p in self.nodes.values():
            rear=(self.length+(t-p['exit_time'])*self.vfree) if 'exit_time' in p else p['x']-p['w']*p['footprint']
            p['rear_history'][t]=rear
            for old in list(p['rear_history']):
                if old<t-self.headway:del p['rear_history'][old]

    def release(self,t,dt,service):
        if abs(t-self.time)>1e-8 or dt!=1 or service<0:raise ValueError('Contiguous1s spatial transport required')
        before=self.stock;old=[dict(p) for p in self.packets];speeds=[]
        for i,p in enumerate(self.packets):
            if self.delayed:
                target=self.nodes[p['leader']]['rear_history'][t+dt-self.headway]-p['correction'] if p['leader'] is not None else math.inf
                if i:target=min(target,old[i-1]['x'])
                speed=min(self.vfree,max(0.,target-p['x'])/dt)
            else:
                gap=(old[i-1]['x']-old[i-1]['w']*old[i-1]['footprint']-p['x']) if i else math.inf
                speed=min(self.vfree,max(0.,gap)/self.headway)
            speeds.append(speed);p['x']=min(self.length,p['x']+speed*dt)
        q=service/3600.;available=dt;amount=0.;residence=before*dt
        while self.packets and self.packets[0]['x']>=self.length-1e-8 and q>0 and available>0:
            p=self.packets[0];travel=(self.length-old[0]['x'])/speeds[0] if speeds[0]>0 else 0.
            available=min(available,max(0.,dt-travel));served=min(p['w'],q*available)
            if served<=0:break
            # Constant-rate discharge during the remaining service interval.
            residence-=served*(available-served/(2*q));p['w']-=served;amount+=served
            available-=served/q
            if p['w']<=1e-12:
                if self.delayed:p['exit_time']=t+dt
                self.packets.pop(0);old.pop(0);speeds.pop(0)
            else:break
        self.departed+=amount;self.residence_veh_h+=residence/3600.;self.time=t+dt
        if self.delayed:self._record_rears(self.time)
        self.check()
        return amount

    def accept(self,t,amount,**unused):
        if abs(t-self.time)>1e-8 or amount<0 or amount>self.receiving()+1e-7:raise ArithmeticError('Spatial admission exceeds current entrance room')
        if amount>1e-12:
            # Ordered fluid packets, at most1veh each. The final packet may
            # straddle the inlet, consistent with front-crossing inventory.
            n=amount;new=[]
            while n>1e-10:
                w=min(1.,n if n<=1 else (n-math.floor(n) or 1.))
                new.append(dict(x=max(0.,n-1)*self.mean_footprint,w=w,footprint=self.mean_footprint));n-=w
            if self.packets and new[0]['x']>self.packets[-1]['x']-self.packets[-1]['w']*self.packets[-1]['footprint']+1e-7:
                raise ArithmeticError('Incoming packets overlap previous tail')
            if self.delayed:
                leader=self.packets[-1] if self.packets else None
                for p in new:self._register(p,leader,t,0.);leader=p
            self.packets.extend(new)
        self.admitted+=amount;self.check()


class TransportTests(unittest.TestCase):
    def test_delayed_release_does_not_jump_through_two_stopped_vehicles(self):
        p=SpatialLane(5,12,36,[(12,0,4.5),(6,0,4.5),(0,0,4.5)],0,2,1.5,delayed=True)
        for t in range(4):
            p.release(t,1,3600)
            self.assertEqual(p.packets[-1]['x'],0)
        p.release(4,1,3600);self.assertGreater(p.packets[-1]['x'],0)

    def test_delayed_fractional_traffic_conserves_and_clears(self):
        p=SpatialLane(10,60,36,[(40,0,4.5)],0,2,1.5,delayed=True)
        p.accept(0,2.4)
        for t in range(100):p.release(t,1,900)
        self.assertAlmostEqual(p.stock,0);self.assertAlmostEqual(p.departed,3.4)

    def test_tail_blocked_despite_total_empty_storage(self):
        p=SpatialLane(8,60,36,[(0,0,4.5),(6,0,4.5),(60,0,4.5)],0,2,1.5)
        self.assertEqual(p.receiving(),0)
        p.release(0,1,3600)
        self.assertEqual(p.departed,1);self.assertEqual(p.receiving(),0)
        self.assertEqual(p.packets[-1]['x'],0)

    def test_fractional_admission_and_discharge_conserve(self):
        p=SpatialLane(10,60,36,[(40,0,4.5)],0,2,1.5)
        p.accept(0,2.4)
        for t in range(100):p.release(t,1,900)
        self.assertAlmostEqual(p.stock,0);self.assertAlmostEqual(p.departed,3.4)
        self.assertGreater(p.residence_veh_h,0)

    def test_unused_service_not_banked(self):
        p=SpatialLane(8,60,36,[(0,0,4.5)],0,2,1.5)
        for t in range(6):p.release(t,1,3600)
        self.assertEqual(p.departed,0)
        p.release(6,1,0);self.assertEqual(p.departed,0)
        p.release(7,1,360);self.assertAlmostEqual(p.departed,.1)

    def test_full_initial_overlap_is_not_repositioned(self):
        p=SpatialLane(10,60,36,[(20,0,4.5),(15,0,4.5)],0,2,1.5)
        p.release(0,1,0)
        self.assertEqual(p.packets[-1]['x'],15)
        self.assertEqual(p.stock,2)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--anchor-service',action='store_true');parser.add_argument('--delayed',action='store_true');parser.add_argument('--cumulative',action='store_true');args=parser.parse_args()
    if args.delayed and args.cumulative:raise ValueError('Select one spatial law')
    name='off_spatial_transport'+('_cumulative' if args.cumulative else '')+('_delay' if args.delayed else '')+('_anchor' if args.anchor_service else '')+'_v1'
    out=HERE/name;out.mkdir(exist_ok=False)
    suite=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(CumulativeTests if args.cumulative else TransportTests))
    if not suite.wasSuccessful():raise AssertionError('Transport invariants failed')
    e.save(out/'tests.json',dict(passed=True,tests=suite.testsRun))
    cfg=e.load(HERE/'merge10681_conflict_v1/evaluation/through_only.json')
    cfg['freeway']['physical_offramp_lanes']={'10643':{'entry_groups':[0,1],'history_sec':150}}
    config=out/'config.json';e.save(config,cfg)
    recording=e.load(HERE/'vehicle_lengths_native_v1/analysis/frames.json')
    current=next(r['vehicles'] for r in recording['frames'] if r['time_s']==2400);del recording
    seed,folder,bank,start=CASES[1];assert seed==23 and start==2400
    data=e.ObservationData(folder);model=e.load_base_model(data.geometry,config);prior=model._config
    def configured(road,p):
        value=prior(road,p)
        if road=='FW_E':value.network.terminal_zero_gradient=True
        return value
    model._config=configured
    params=e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    lane=e.load(H/'lane_group_response_20260919/observations_v1/s23.json');origin=e.load(HERE/'port_positions_v1/s23.json');protocol=e.load(bank/'protocol.json')
    headway=e.load(HERE/'off_queue_release_v1/result.json')['pair_lag_s'];assert headway==2
    wave=e.load(HERE/'off_spatial_supply_v1/result.json')['wave_m_s']
    files=[Path(__file__),config,e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',
        HERE/'vehicle_lengths_native_v1/analysis/frames.json',HERE/'off_queue_release_v1/result.json',HERE/'off_spatial_supply.py',HERE/'off_spatial_supply_v1/result.json']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if args.anchor_service:
        from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.urban_receiving_probe import dataset,features
        calibration=HERE/'urban_receiving_lag_probe_v1/result.json'
        selected=next(r for r in e.load(calibration)['models'] if r['name']=='history_signal_state')
        coef=np.array(selected['coefficients_by_lane']);lag=selected['signal_lag_s']
        urban=HERE/'urban_drain_observations_v5'
        urban_paths=[urban/'s23_none.csv',urban/'s23_none_evidence.json']
        observed,program,offset=dataset(*urban_paths)
        past={t:r for t,r in observed.items() if t<=start};del observed
        anchor=features(past,program,offset,start,lag)
        for p in [calibration,*urban_paths]:pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    e.save(out/'protocol.json',dict(pins=pins,headway_s=headway,clearance_m=1.5,seed=seed,start=start,
        future_inputs=False,no_gain_fitting=True,new_native_runs=0,anchor_service=args.anchor_service,delayed_rear_history=args.delayed,cumulative_boundary=args.cumulative,
        wave_m_s=wave if args.cumulative else None,
        hypotheses=(['Existing NC13 measured wave, unchanged nominal spacing/capacity and connector travel speed define one triangular FD for both boundaries.',
            'Current initial positions are projected by the existing finite-spacing envelope; projection errors are reported. Current speeds/lengths are not new FD states.',
            'No lateral sources in this zero-past-exchange state.1s uniform-flux cost integration; mainline admits at existing10s interval ends.'] if args.cumulative else ['Measured2s pair lag used as a finite gap-response scale, not a validated equality.',
            'Native current vehicle lengths plus configured W74ax1.5m; future mean composition held at cutoff.',
            'Fractional vehicles, finite ordered packets, front-crossing entry allowance; no lane exchange in this initial history.',
            'Free motion uses existing connector travel speed. No explicit acceleration or driver heterogeneity dynamics.'])))
    init=ch.LaneResolvedDelayedPort.__init__;exchange=ch.LaneResolvedDelayedPort._exchange;advance=PhysicalLaneGroups.advance
    results={};base={}
    for mode in ('lane_reference','spatial'):
        costs={};summaries={}
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},{d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)],
                'initial_ramp_origin':origin['counts'][str(start)],'initial_off_eligible':origin['eligible_before_off'][str(start)]}}
            if args.anchor_service:
                for step in w['boundary_steps']:
                    x=anchor.copy();lo,hi=step['window_start_s'],step['window_end_s']
                    for i,sg in enumerate((2,5)):
                        x[3+i]=sum(program.state_at(s,sg,controller_offset_sec=offset)=='GREEN' for s in range(lo-lag+1,hi-lag+1))/(hi-lo)
                    service=np.maximum(0.,x@coef)*3600
                    step['off_drain_vph']['10643']=float(service.sum())
                    step['off_lane_drain_vph']['10643']=service.tolist()
            tracked=[];offers=[]
            def initialize(self,capacity,length,speed,cohorts,t,rates):
                init(self,capacity,length,speed,cohorts,t,rates)
                assert sorted(cohorts)==sorted([p,v,l] for vid,l,p,v,size,kind in current)
                assert all(x==0 for row in rates for x in row),'Lateral spatial transport remains unqualified'
                self.lanes=[(CumulativeLane(capacity/2,length,speed,[(p,v,size) for vid,l,p,v,size,kind in current if l==g],t,wave) if args.cumulative else
                    SpatialLane(capacity/2,length,speed,[(p,v,size) for vid,l,p,v,size,kind in current if l==g],t,headway,1.5,delayed=args.delayed)) for g in (1,2)]
                self.initial=self.stock;tracked.append(self)
            def keep_lanes(self,dt):
                if self in tracked:return
                return exchange(self,dt)
            def spatial_supply(self,state,control,demand,cfg,**kw):
                if self.road=='FW_E':
                    assert len(tracked)==1
                    lanes=tracked[0].lanes;caps=copy.deepcopy(kw['offramp_group_capacity_veh_h'])
                    old=list(caps['10643']);new=[min(old[g],p.receiving()/self.dt) for g,p in enumerate(lanes)]+[0.]
                    caps['10643']=new;kw['offramp_group_capacity_veh_h']=caps
                    offers.append(dict(time_s=state.time_sec,old=old,new=new,
                        stock=[p.stock for p in lanes],tail=[None if args.cumulative else p.packets[-1]['x'] if p.packets else None for p in lanes]))
                return advance(self,state,control,demand,cfg,**kw)
            if mode=='spatial':
                ch.LaneResolvedDelayedPort.__init__=initialize;ch.LaneResolvedDelayedPort._exchange=keep_lanes;PhysicalLaneGroups.advance=spatial_supply
            try:p=e.simulate(model,w,params)
            finally:
                ch.LaneResolvedDelayedPort.__init__=init;ch.LaneResolvedDelayedPort._exchange=exchange;PhysicalLaneGroups.advance=advance
            if mode=='lane_reference':base[arm]=p
            checks=audit(p,base[arm]);costs[arm]=parts(p)
            summaries[arm]=dict(offers=offers,checks=checks,score=e.score_rollout(data,start,p,'FW_E') if arm=='none' else None,
                port_checks=sum(x.counters for port in tracked for x in port.lanes),
                initial_projection_max_m=[x.envelope.projection_max_m for port in tracked for x in port.lanes] if args.cumulative else [])
            e.save(out/f'prediction_{mode}_{arm}.json',p)
        delta={a:{k:v-costs['none'][k] for k,v in r.items()} for a,r in costs.items() if a!='none'}
        for d in delta.values():d['total']=sum(d.values())
        results[mode]=dict(costs=costs,deltas=delta,summaries=summaries)
        print(mode,delta,'NC objective',summaries['none']['score']['objective'],flush=True)
    for file,pin in pins.items():assert hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,production_adopted=False,qualified=False,new_native_runs=0,source_pins_verified=True))


if __name__=='__main__':main()
