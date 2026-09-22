"""Eight finite physical off-ramps between the freeway and urban owners.

Connector travel is part of its existing stock, never an additional queue.
The10643 outlet is advanced by LaneUrbanRuntime; the other seven retain the
reference DelayedPort law and drain only into available downstream storage.
"""
from __future__ import annotations
import math
from collections import defaultdict
from evaluation.controllers.lane_urban_runtime import _debit_stock


class LaneOfframpRuntime:
    def __init__(self, ports, descriptions, local_port, membership):
        if set(ports) != set(descriptions)-{'10643'}:
            raise ValueError('Exactly seven ordinary physical off-ramps required')
        self.ports=ports
        self.descriptions=descriptions
        self.local_port=local_port
        self.membership=membership
        self.last_drain=None

    def stock(self, off):
        return (math.fsum(p.stock for p in self.local_port.lanes) if off=='10643'
                else self.ports[off].stock)

    def assert_mirrors(self,state,cfg):
        for off,row in self.descriptions.items():
            key=row['storage']
            n=cfg.network.urban_link_storage_veh[key]-state.urban_link_storage[key]
            if abs(n-self.stock(off))>1e-7:
                raise ArithmeticError('Physical off-ramp differs from its sole stock owner: '+off)

    def drain(self,state,control,cfg,step,routing):
        from src.models import urban_queue_model as uqm
        from evaluation.controllers.control_area_objective import get_ledger,emit_transfer
        from evaluation.controllers.urban_flow_accounting import _receive_corridor
        from evaluation.controllers.route_choice_corridor import known_legsplit_receive
        if self.last_drain is not None and step!=self.last_drain+1:
            raise ValueError('Noncontiguous physical off-ramp drainage')
        self.assert_mirrors(state,cfg)
        ledger=get_ledger(state)
        departures=defaultdict(float)
        for off,port in self.ports.items():
            row=self.descriptions[off]
            key=row['storage']
            stock=port.stock
            requests=[]
            if row.get('local_upstream'):
                target=state.lane_urban_runtime.origin
                service=cfg.network.movement_capacity_veh_h*row['lanes']/3600.
                room=uqm._effective_available_space(state,cfg,target)
                requests.append((None,target,min(service,room),service,room))
            elif row['direct']:
                target=row['target']
                service=cfg.network.movement_capacity_veh_h*row['lanes']/3600.
                room=uqm._effective_available_space(state,cfg,target)
                requests.append((None,target,min(service,room),service,room))
            else:
                # Distinct movements retain the existing conditional weights;
                # their downstream room is consumed by actual accepted packets.
                reserved=defaultdict(float)
                for m in cfg.network.off_ramp_to_movement[row['group']]:
                    spec=cfg.network.urban_movements[m]
                    target=spec['receiving_link']
                    service=(uqm._movement_capacity_flow(control,cfg,m,spec)*
                             uqm._phase_green_fraction(control,cfg,spec,urban_step_index=step)/3600.)
                    room=max(0.,uqm._effective_available_space(state,cfg,target)-reserved[target])
                    amount=min(float(spec['beta'])*stock,service,room)
                    requests.append((m,target,amount,service,room))
                    reserved[target]+=amount
            limit=math.fsum(x[2] for x in requests)
            actual=port.release(step,1.,limit*3600.)
            if actual>limit+1e-7 or actual>stock+1e-7:
                raise ArithmeticError('Physical off-ramp exceeded available sending/service')
            if ledger.captures_response:
                ledger.record_resource_allocation('physical_offramp_stock',off,stock,{off:actual})
                ledger.record_resource_allocation('physical_offramp_service',off,limit,{off:actual})
            for movement,target,amount,service,room in requests:
                n=amount*actual/limit if limit else 0.
                if ledger.captures_response:
                    evidence={off+':'+str(movement):n}
                    ledger.record_resource_allocation('physical_offramp_target_room',off+':'+target,room,evidence)
                    ledger.record_resource_allocation('physical_offramp_target_service',off+':'+str(movement),service,evidence)
                if n<=0:continue
                state.urban_link_storage[key]+=n
                state.urban_link_storage[target]=_debit_stock(state.urban_link_storage[target],n)
                if row.get('local_upstream'):
                    emit_transfer(state,cfg,'storage:'+key,'storage:'+target,n,preserve_area=True)
                    state.lane_urban_runtime.schedule_upstream(state,cfg,step,n,entry='off10638')
                elif movement is None:
                    emit_transfer(state,cfg,'storage:'+key,'storage:'+target,n,
                        source_inside=self.membership[str(row['connector'])],
                        target_inside=self.membership[str(row['to_link'])])
                    due=step+uqm._link_delay_steps(state,cfg,target)
                    if getattr(cfg.network,'known_legsplit_routes',None):
                        known_legsplit_receive(state,cfg,n,due,off_ramp=row['group'])
                    if target in routing:uqm._schedule(state.urban_arrival_buffer,target,due,n)
                    uqm._schedule(state.urban_storage_release_buffer,target,due,n)
                else:
                    emit_transfer(state,cfg,'storage:'+key,'storage:'+target,n,route_key='movement:'+movement)
                    if not _receive_corridor(state,cfg,movement,n,step):
                        due=step+uqm._link_delay_steps(state,cfg,target)
                        if target in routing:uqm._schedule(state.urban_arrival_buffer,target,due,n)
                        uqm._schedule(state.urban_storage_release_buffer,target,due,n)
                departures[row['group']]+=n
        self.last_drain=step
        self.assert_mirrors(state,cfg)
        if ledger.captures_response:ledger.complete_constraint_coverage('physical_offramp_drain')
        return dict(departures)

    def capacities(self,state,cfg):
        self.assert_mirrors(state,cfg)
        caps={off:max(0.,state.urban_link_storage[row['storage']])*3600.
              for off,row in self.descriptions.items()}
        lanes=[min(p.capacity-p.stock,p.receiving(1.))*3600. for p in self.local_port.lanes]
        caps['10643']=min(caps['10643'],math.fsum(lanes))
        # The mainline has lane1,lane2,lanes3+ groups;10643 admits only the
        # first two physical lanes. The inaccessible group has zero room.
        return caps,{'10643':lanes+[0.]}

    def land(self,state,cfg,end,flows,group_flows):
        from evaluation.controllers.control_area_objective import get_ledger,emit_transfer
        ledger=get_ledger(state)
        if set(flows)!=set(self.descriptions):raise ValueError('Incomplete physical off-ramp landing')
        total=0.
        for off,row in self.descriptions.items():
            amount=flows[off]/3600.
            key=row['storage']
            room=state.urban_link_storage[key]
            if not math.isfinite(amount) or amount<0 or amount>room+1e-7:
                raise ArithmeticError('Freeway sent beyond finite connector storage')
            if off=='10643':
                by_lane=group_flows[off]
                if len(by_lane)!=2 or abs(math.fsum(by_lane)-amount)>1e-7:
                    raise ArithmeticError('Off-ramp lane admission disagrees with aggregate')
                for g,n in enumerate(by_lane):
                    p=self.local_port.lanes[g]
                    receiving=p.receiving(1.)
                    p.accept(end,n)
                    self.local_port.admit(g,n)
                    if ledger.captures_response:
                        ledger.record_resource_allocation('physical_offramp_lane_receiving',off+':'+str(g),receiving,{off:n})
            else:self.ports[off].accept(end,amount)
            state.urban_link_storage[key]=_debit_stock(room,amount)
            emit_transfer(state,cfg,'freeway:'+row['road'],'storage:'+key,amount,
                source_inside=True,target_inside=self.membership[str(row['connector'])])
            total+=amount
            if ledger.captures_response:
                ledger.record_resource_allocation('physical_offramp_landing_storage',off,room,{off:amount})
                ledger.complete_constraint_coverage('offramp_landing:'+off)
        self.assert_mirrors(state,cfg)
        ledger.complete_constraint_coverage('offramp_landing')
        return total
