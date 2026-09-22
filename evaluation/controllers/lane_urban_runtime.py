"""Two-way finite urban receiver for the physical10643 off-ramp.

The three local roads have distinct storage stocks. Existing upstream travel
and queues remain upstream owners until an actual lane-cell admission. The
legacy three stopline services are replaced by this transport's physical exits.
No historical background arrivals are injected into the coupled network.
"""
from __future__ import annotations
import copy
import math
from collections import Counter, defaultdict

from evaluation.controllers.physical_urban_transport import FIFO, tagged


def _debit_stock(stock, amount):
    """Subtract an accepted fluid transfer without retaining a negative ULP.

    Only arithmetic roundoff may be zeroed. A physical overdraw still raises
    at the mutation site; the global stock/constraint validators stay strict.
    """
    if not all(math.isfinite(v) and v >= 0 for v in (stock, amount)):
        raise ArithmeticError('Invalid local urban stock or accepted transfer')
    remainder=stock-amount
    tolerance=16*max(math.ulp(stock),math.ulp(amount))
    if remainder < -tolerance:
        raise ArithmeticError(f'Local urban accepted transfer exceeds its source stock: {stock=:.17g}, {amount=:.17g}, {remainder=:.17g}, {tolerance=:.17g}')
    return max(0.,remainder)


def _debit_movement_transfers(queues, transfers, source_keys):
    """Debit each shared movement once for all accepted lane admissions.

    Allocation already consumed the labelled entry FIFOs. Sequentially
    subtracting their packets from a shared mirror can cancel to a small
    residual whose ULP no longer represents the original arithmetic scale.
    Sum the actual receipts accurately before applying the unchanged overdraw
    check. Do not change the allocation, route labels or emitted transfers.
    """
    amounts=defaultdict(list)
    for source,target,packets in transfers:
        if source[0]!='external':continue
        key=source_keys[source[1]]
        if key.startswith('movement:'):
            amounts[key.split(':',1)[1]].extend(n for label,n in packets)
    updated={m:_debit_stock(queues[m],math.fsum(values)) for m,values in amounts.items()}
    queues.update(updated)


class CandidateSignalProgram:
    def __init__(self):
        self.control = self.cfg = None

    def state_at(self, time, sg, *, controller_offset_sec):
        from evaluation.controllers.signal_actuation_contract import phase_fraction
        if self.cfg is None or self.cfg.simulation.T_u_sec != 1 or controller_offset_sec != 0:
            raise ValueError('Local urban transport lacks its one-second candidate clock')
        phase = {2:'SC1004_p3',5:'SC1004_p4'}[sg]
        value = phase_fraction(self.control,self.cfg,{'signal':'SC1004','phase':phase},int(time)-1)
        if value not in (0.,1.):
            raise ValueError('Local physical signal is not integral-second RED/GREEN')
        return 'GREEN' if value else 'RED'


class LaneUrbanRuntime:
    def __init__(self, coupled_port, cfg, *, movement_by_exit, side_port=None, side_fifo=None):
        if set(movement_by_exit) != {10634,10635,10642}:
            raise ValueError('Every physical urban exit requires its canonical movement')
        self.port = coupled_port
        self.movements = dict(movement_by_exit)
        self.exits_by_movement = {m:c for c,m in self.movements.items()}
        if len(self.exits_by_movement) != 3:
            raise ValueError('Physical exits must not share a model movement')
        self.local_storage = {road:'lane_urban_'+str(road) for road in self.port.urban.edges}
        self.side_port, self.side_fifo = side_port, side_fifo
        if (side_port is None) != (side_fifo is None):
            raise ValueError('Observed10700 requires both physical travel and labelled inventory')
        if side_port is not None:
            self.local_storage[10700] = 'lane_urban_10700'
        self.pending = {}
        self.arrival_tags = {}
        self.entry_paths = {}
        self.future_shares = {}
        self.off_storage = cfg.network.off_ramp_storage_link['OR_F_E']
        self.origin = 'in_SC1004_W'
        for connector,m in self.movements.items():
            spec=cfg.network.urban_movements[m]
            if spec.get('origin') != self.origin or spec.get('ramp'):
                raise ValueError('Local urban exit changed canonical movement ownership')
        self.last_step = int(self.port.urban.time)-1

    def bind_service_ownership(self,cfg):
        """Use the reference CTM's FD at the heads it now owns.

        Preserve a single shared10634 receipt budget for the downstream route
        corridor. The old measured aggregate service is retained as provenance,
        not imposed as a second bottleneck inside the selected lane plant.
        """
        from evaluation.controllers import local_signal_service as pool
        net=cfg.network
        spec=net.route_choice_corridor
        rates={str(c):len(self.port.urban.exits[c]['lanes'])*self.port.urban.capacity_rate*3600.
               for c in self.movements}
        changed={}
        for item in spec.get('corridors',[spec]):
            for movement,turn in item['turns'].items():
                if turn['connector']!='10634':continue
                changed[movement]=turn['service_veh_h']
                turn['service_veh_h']=rates['10634']
                turn['service_source']='lane_plant_triangular_fd'
                net.movement_capacity_by_movement_veh_h[movement]=rates['10634']
        if set(changed)!=set(pool.MEMBERS):
            raise ValueError('Lane service replacement does not own the complete10634 group')
        for movement in changed:
            spec['turns'][movement]['service_veh_h']=rates['10634']
        for connector,m in self.movements.items():
            net.movement_capacity_by_movement_veh_h[m]=rates[str(connector)]
        net.lane_plant_service_ownership={'source':'reference_lane_fd','rates_veh_h':rates,
                                        'replaced_aggregate_rates_veh_h':changed}
        pool.configure(cfg,{'urban':{'shared_local_service_pool':True}})

    def schedule_upstream(self,state,cfg,step,amount,*,entry,shares=None,distance_m=None,speed_kmh=None):
        """Travel to the local CTM entry, retaining its destination/lane class.

        These tags are subsets of in_SC1004_W storage. They never create an
        additional population or replay measured future background arrivals.
        """
        from src.models import urban_queue_model as uqm
        if not math.isfinite(amount) or amount<0:raise ValueError('Invalid local upstream receipt')
        if not amount:return
        shares=self.future_shares[entry] if shares is None else shares
        if abs(math.fsum(shares.values())-1.)>1e-9 or any(v<0 or not math.isfinite(v) for v in shares.values()):
            raise ValueError('Local upstream destinations do not conserve population')
        distance=self.entry_paths[entry] if distance_m is None else distance_m
        speed=self.port.urban.speed*3.6 if speed_kmh is None else speed_kmh
        due=int(step)+max(1,math.ceil(distance/(max(speed,1e-9)/3.6)))
        for movement,fraction in shares.items():
            if movement not in self.exits_by_movement and movement!='SC1004_W_to_onE':
                raise ValueError('Unmodelled local upstream destination')
            key=(movement,entry=='city')
            row=self.arrival_tags.setdefault(due,Counter())
            row[key]+=amount*fraction
        uqm._schedule(state.urban_arrival_buffer,self.origin,due,amount)
        uqm._schedule(state.urban_storage_release_buffer,self.origin,due,amount)

    def consume_upstream(self,state,cfg,step,amount):
        from evaluation.controllers.control_area_objective import emit_transfer
        tags=self.arrival_tags.pop(step,{})
        if abs(math.fsum(tags.values())-amount)>1e-7:
            raise ArithmeticError('Local upstream arrivals lost their physical source tags')
        for (movement,city),n in tags.items():
            state.urban_movement_queue[movement]+=n
            self.register_ready(movement,n,city_amount=n if city else 0.)
            emit_transfer(state,cfg,'storage:'+self.origin,'movement:'+movement,n,preserve_area=True)

    def register_ready(self, movement, amount, *, city_amount=0.):
        """Tag subsets of an existing movement queue; this creates no stock.

        Non-city arrivals have traversed70 and enter126. The declared city
        branch10640 enters71 lanes4/5 and must not acquire the on-ramp choice.
        Equal entry-lane shares are an explicit closure for future fluid arrivals.
        """
        if movement not in self.exits_by_movement:
            return
        if not math.isfinite(amount) or not 0 <= city_amount <= amount+1e-8:
            raise ValueError('Invalid classified upstream local arrivals')
        destination=self.exits_by_movement[movement]
        for road,lanes,n in ((126,(1,2),max(0.,amount-city_amount)),(71,(4,5),city_amount)):
            for lane in lanes:
                self.pending.setdefault((movement,road,lane),FIFO()).append((destination,None),n/len(lanes))

    def assert_pending(self,state):
        for m in self.exits_by_movement:
            n=math.fsum(q.stock for (movement,road,lane),q in self.pending.items() if movement==m)
            if abs(n-state.urban_movement_queue[m]) > 1e-7:
                raise ArithmeticError('Local entry tags differ from their sole upstream queue: '+m)

    def sync_stores(self,state,cfg):
        urban=self.port.urban
        amounts=Counter()
        for (road,lane,cell),queue in urban.cells.items():amounts[road]+=queue.stock
        if self.side_port is not None:amounts[10700]=self.side_port.stock
        for road,key in self.local_storage.items():
            state.urban_link_storage[key]=_debit_stock(cfg.network.urban_link_storage_veh[key],amounts[road])
        state.urban_link_storage[self.off_storage]=_debit_stock(cfg.network.urban_link_storage_veh[self.off_storage],sum(p.stock for p in self.port.lanes))

    def advance(self,state,control,cfg,step):
        from src.models import urban_queue_model as uqm
        from evaluation.controllers.control_area_objective import emit_transfer,get_ledger
        from evaluation.controllers.urban_flow_accounting import _receive_corridor
        if step != self.last_step+1 or step != self.port.urban.time:
            raise ValueError('Noncontiguous coupled local urban step')
        self.assert_pending(state)
        ledger=get_ledger(state)
        capture=ledger is not None and ledger.captures_response
        urban=self.port.urban
        if not isinstance(urban.program,CandidateSignalProgram):
            raise ValueError('Coupled urban transport must use the applied candidate signal clock')
        urban.program.control,urban.program.cfg=control,cfg
        external={}
        source_keys={}
        for (m,road,lane),queue in self.pending.items():
            name=f'upstream:{m}:{road}:{lane}'
            external[name]=((road,lane,0),queue)
            source_keys[name]='movement:'+m
        for g,p in enumerate(self.port.lanes):
            offered=max(0.,min(p.stock,p.envelope.qmax,p.sending_bound(step+1-p.start)-p.departed))
            prefix=FIFO(copy.deepcopy(list(self.port.fifo[g].q)))
            external[f'off:{g}']=((126,g+1,len(urban.edges[126])-2),FIFO(prefix.take(offered)))
            source_keys[f'off:{g}']='storage:'+self.off_storage
        if self.side_port is not None:
            p=self.side_port
            offered=max(0.,min(p.stock,p.envelope.qmax,p.sending_bound(step+1-p.start)-p.departed))
            prefix=FIFO(copy.deepcopy(list(self.side_fifo.q)))
            external['side10700']=((71,1,0),FIFO(prefix.take(offered)))
            source_keys['side10700']='storage:'+self.local_storage[10700]
        exit_room={}
        for connector,m in self.movements.items():
            receiver=cfg.network.urban_movements[m]['receiving_link']
            if receiver not in state.urban_link_storage:
                raise ValueError('Physical urban exit lacks its finite downstream receiver')
            room=uqm._effective_available_space(state,cfg,receiver)
            from evaluation.controllers.route_choice_corridor import intended_departure
            service=intended_departure(state,control,cfg,m,room,step)
            exit_room[connector]=room if service is None else min(room,service)
        try:
            if (getattr(cfg.network, 'sdmpc_options', None) or {}).get('fifo_batch', False):
                accepted=urban.step(external,exit_receiving=exit_room,indexed_lateral=True)
            else:
                accepted=urban.step(external,exit_receiving=exit_room)
        finally:
            # Never retain the entire cfg/action graph in a candidate's copy.
            urban.program.control=urban.program.cfg=None
        for g,p in enumerate(self.port.lanes):
            name=f'off:{g}'
            n=math.fsum(v for label,v in accepted.get(name,()))
            served=p.release(step,1,n*3600.)
            if abs(n-served)>1e-7:raise ArithmeticError('Off-ramp sending/urban receiving mismatch')
            actual=Counter()
            for label,amount in self.port.fifo[g].take(n):actual[label]+=amount
            expected=Counter()
            for label,amount in accepted.get(name,()):expected[label]+=amount
            if any(abs(actual[k]-expected[k])>1e-7 for k in actual.keys()|expected.keys()):
                raise ArithmeticError('Physical off-ramp transfer changed a vehicle label')
            self.port.left[g].update(actual)
        if self.side_port is not None:
            n=math.fsum(v for label,v in accepted.get('side10700',()))
            served=self.side_port.release(step,1,n*3600.)
            if abs(n-served)>1e-7:raise ArithmeticError('10700 sending/receiving mismatch')
            self.side_fifo.take(n)
        exit_accepted=Counter()
        _debit_movement_transfers(state.urban_movement_queue,urban.last_transfers,source_keys)
        for source,target,packets in urban.last_transfers:
            n=math.fsum(v for label,v in packets)
            if source[0]=='external':
                key=source_keys[source[1]]
            else:key='storage:'+self.local_storage[source[0]]
            if target[0]=='exit':
                connector=target[1];m=self.movements[connector]
                receiver=cfg.network.urban_movements[m]['receiving_link']
                state.urban_link_storage[receiver]=_debit_stock(state.urban_link_storage[receiver],n)
                emit_transfer(state,cfg,key,'storage:'+receiver,n,route_key='movement:'+m)
                if not _receive_corridor(state,cfg,m,n,step):
                    due=step+uqm._link_delay_steps(state,cfg,receiver)
                    if receiver in uqm.approach_routing(cfg):uqm._schedule(state.urban_arrival_buffer,receiver,due,n)
                    uqm._schedule(state.urban_storage_release_buffer,receiver,due,n)
                exit_accepted[connector]+=n
            else:
                destination='storage:'+self.local_storage[target[0]]
                if key!=destination:
                    # Admission to a travel cell is not stopline service. In
                    # particular movement:<id>->storage:<id> must not masquerade
                    # as a canonical movement event in the shared NP ledger.
                    emit_transfer(state,cfg,key,destination,n,preserve_area=True,
                        route_key='lane_urban_transfer:'+key+'->'+destination)
        self.sync_stores(state,cfg)
        self.port.check()
        self.assert_pending(state)
        if capture:
            sent, received = defaultdict(Counter), defaultdict(Counter)
            for source,target,packets in urban.last_transfers:
                n=math.fsum(v for _,v in packets)
                sent[source][str(target)]+=n
                received[target][str(source)]+=n
            for source,limit in urban.last_sending_limits.items():
                ledger.record_resource_allocation('lane_urban_sending',str(source),limit,dict(sent[source]))
            for target,limit in urban.last_receiving_limits.items():
                ledger.record_resource_allocation('lane_urban_receiving',str(target),limit,dict(received[target]))
            for connector,limit in exit_room.items():
                ledger.record_resource_allocation('lane_urban_exit_receiving',str(connector),limit,
                    {'lane_urban:'+str(connector):exit_accepted[connector]})
            for key,queue in urban.cells.items():
                ledger.record_state_upper_bound('lane_urban_cell',str(key),queue.stock,urban.cap[key])
            ledger.complete_constraint_coverage('lane_urban_allocator')
        self.last_step=step
        return {'lane_urban_exit_veh':math.fsum(exit_accepted.values()),
                'lane_urban_stock_veh':math.fsum(q.stock for q in urban.cells.values())}


def observe_ready(state,cfg,movement,amount,*,city_amount=0.):
    runtime=getattr(state,'lane_urban_runtime',None)
    if runtime is not None:runtime.register_ready(movement,amount,city_amount=city_amount)


def is_local_movement(state,movement):
    runtime=getattr(state,'lane_urban_runtime',None)
    return runtime is not None and movement in runtime.exits_by_movement
