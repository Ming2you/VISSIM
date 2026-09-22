"""Finite connector heads and actual merges in the full coupled candidate.

Ramp stock is mirrored in TrafficState.ramp_queue for the existing urban
receivers and cost accounting; buffers are an internal decomposition, not an
additional stock. Upstream rejected traffic stays with its existing owner.
"""
from __future__ import annotations
import copy
import math

from evaluation.controllers.physical_ramp_boundary import (
    PhysicalRampBoundary, LaneResolvedRampBoundary, gap_acceptance_supply_vph)


class LaneRampRuntime:
    def __init__(self, component, specs, state, *, cycle_sec):
        if set(specs) != set(component.ramps):
            raise ValueError('All eight physical ramp initial states are required')
        self.cycle_sec = cycle_sec
        self.receiving_nodes = copy.deepcopy(component.ramp_receiving_nodes)
        self.lane_coupling = copy.deepcopy(component.ramp_lane_coupling)
        self.buffers = {}
        for name, spec in specs.items():
            cls = LaneResolvedRampBoundary if name in self.receiving_nodes else PhysicalRampBoundary
            extra = ({'lane_exchange_rates_per_sec': component.ramp_lane_exchange[name]}
                     if name in component.ramp_lane_exchange else {})
            self.buffers[name] = cls(**spec, **extra)
        self.predebited = None
        self.assert_mirror(state)

    def assert_mirror(self, state):
        for name, buffer in self.buffers.items():
            snapshot = buffer.snapshot()
            if (abs(snapshot['connector_veh']-state.ramp_queue[name]) > 1e-7
                    or snapshot['outside_component_backlog_veh'] > 1e-8):
                raise ArithmeticError('Physical ramp and sole urban stock owner disagree: '+name)

    def receiving_space(self, state, name):
        buffer = self.buffers[name]
        pending = state.ramp_queue[name]-buffer.snapshot()['connector_veh']
        if pending < -1e-7:
            raise ArithmeticError('Urban receiver removed uncommitted ramp stock')
        return max(0., buffer.current_admission_space()-max(0., pending))

    def advance(self, state, control, demand, freeway, *, service):
        """Advance old ramp cohorts, debit merges, then expose finite entry room."""
        from evaluation.controllers import area_freeway_accounting as accounting
        from evaluation.controllers.control_area_objective import get_ledger, emit_transfer
        if self.predebited is not None:
            raise ValueError('Previous physical ramp/urban transfer has not completed')
        self.assert_mirror(state)
        if set(service) != set(self.buffers):
            raise ValueError('Every ramp requires its actual physical head command')
        ledger = get_ledger(state)
        releases, group_releases, receipts = {}, {}, {}
        for road, cfg in freeway.configs.items():
            if cfg.simulation.T_f_sec != 1:
                raise ValueError('Coupled physical ramps require a one-second clock')
            dt = cfg.simulation.T_f_h
            from evaluation.controllers.sdmpc_prediction_cache import ramp_query_control
            scratch, unlimited = copy.copy(state), ramp_query_control(control)
            scratch.ramp_queue = dict(state.ramp_queue)
            for name in cfg.network.ramps:
                cap = cfg.network.ramp_capacity_veh_h[name]
                scratch.ramp_queue[name] = math.nextafter(cap*dt, math.inf)
                unlimited.ramp_metering[name] = cap
            selected, _ = accounting._mn.compute_ramp_release_flows(
                scratch, unlimited, demand, cfg, include_current_arrivals=False)
            plant = freeway.lanes.get(road)
            for name in cfg.network.ramps:
                buffer = self.buffers[name]
                rate = canonical_rate = selected[name]
                mapping = self.lane_coupling.get(name)
                lanes = None
                node = self.receiving_nodes.get(name)
                if mapping is not None:
                    if plant is None or not isinstance(buffer, LaneResolvedRampBoundary):
                        raise ValueError('Physical lane receiving requires lane buffers and mainline state')
                    conditions = plant.ramp_lane_conditions(name, mapping, cfg)
                    lanes = [min(rate/buffer.lanes, r['space_vph']) for r in conditions]
                    if node:
                        lanes = [min(q, gap_acceptance_supply_vph(r['conflicting_vph'],
                            node['critical_gap_sec'], node['followup_sec'])) for q,r in zip(lanes,conditions)]
                    rate = math.fsum(lanes)
                else:
                    if plant is not None:
                        rate = min(rate, plant.ramp_supply(name, cfg))
                    if node:
                        i = cfg.network.ramp_merge_segment_index[name]-1
                        if i < 0:
                            raise ValueError('Ramp gap supply lacks upstream physical cell')
                        split = math.fsum(cfg.network.off_ramp_split_ratio[o] for o in cfg.network.off_ramps
                                         if cfg.network.off_ramp_segment_index[o] == i)
                        if not 0 <= split <= 1:
                            raise ValueError('Invalid upstream physical off-ramp split')
                        conflict = (plant.conflict_vph_per_lane(name) if plant is not None else
                            state.freeway_density[road][i]*state.freeway_speed[road][i]*(1-split))
                        rate = min(rate, buffer.lanes*gap_acceptance_supply_vph(conflict,
                            node['critical_gap_sec'], node['followup_sec']))
                before = state.ramp_queue[name]
                receipt = buffer.advance_local_interval(start_sec=freeway.time_sec, duration_sec=1.,
                    cycle_sec=self.cycle_sec, receiving_budget_veh=rate*dt,
                    **({'receiving_budget_by_lane_veh':[q*dt for q in lanes]} if lanes is not None else {}),
                    request_arrivals_veh=0., allow_partial_cycle=True, **service[name])
                merged = receipt['accepted_merge_veh']
                state.ramp_queue[name] -= merged
                emit_transfer(state,cfg,'ramp:'+name,'merge_pending:'+name,merged,preserve_area=True)
                releases[name] = merged/dt
                if mapping is not None:
                    values = [0.]*len(plant.n[cfg.network.ramp_merge_segment_index[name]])
                    for group, row in zip(mapping, receipt['lane_receipts']):
                        values[group] += row['accepted_merge_veh']/dt
                    group_releases[name] = values
                if ledger is not None and ledger.captures_response:
                    source = {'ramp:'+name:merged}
                    for kind, limit in (('stock',before),('canonical_receiving',canonical_rate*dt),
                                        ('physical_receiving',rate*dt),('eligible',receipt['eligible_merge_veh'])):
                        ledger.record_resource_allocation('physical_ramp_merge_'+kind,name,limit,source)
                    for index, row in enumerate(receipt.get('lane_receipts',[receipt])):
                        ledger.record_resource_allocation('physical_ramp_head_service',name+':'+str(index),
                            row['head_service_limit_veh'],{'head:'+name:row['head_service_veh']})
                receipts[name] = receipt
        self.predebited = dict(releases)
        self.assert_mirror(state)
        return releases, group_releases, receipts

    def finish(self, state):
        if self.predebited is None:
            raise ValueError('Physical ramp heads were not advanced')
        for name, buffer in self.buffers.items():
            pending = state.ramp_queue[name]-buffer.snapshot()['connector_veh']
            if pending < -1e-7:
                raise ArithmeticError('Urban transfer over-drew physical ramp stock')
            buffer.admit_current(max(0.,pending))
        self.predebited = None
        self.assert_mirror(state)


def receiving_space(state, cfg, name):
    """Default is exactly the existing aggregate room calculation."""
    runtime = getattr(state, 'lane_ramp_runtime', None)
    if runtime is not None:
        return runtime.receiving_space(state,name)
    net = cfg.network
    cap = net.ramp_queue_cap(name) if hasattr(net,'ramp_queue_cap') else float(net.ramp_queue_max_veh)
    return max(0., cap-max(0.,state.ramp_queue.get(name,0.)))
