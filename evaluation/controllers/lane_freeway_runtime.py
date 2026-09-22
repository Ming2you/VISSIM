"""Candidate-owned stepping of the saved physical freeway reference.

The caller owns urban/ramp/connector transfers and supplies only accepted merge
flows and current receiving limits. This module never replays future boundary
measurements. Each road retains the reference's own parameters and geometry.
"""
from __future__ import annotations

import copy
import math


class LaneFreewayRuntime:
    def __init__(self, component, state, full_cfg, observation, parameters, *, off_splits):
        from evaluation.controllers import area_freeway_accounting as accounting
        from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups

        if component.base.simulation.T_f_sec != full_cfg.simulation.T_f_sec:
            raise ValueError('Physical plant and coupled freeway clocks differ')
        self.time_sec = state.time_sec
        self.configs, self.lanes = {}, {}
        self.roads = tuple(component.roads)
        self.offramps = copy.deepcopy(component.offramps)
        self.ramps = copy.deepcopy(component.ramps)
        if set(off_splits) != set(self.offramps):
            raise ValueError('All physical off-ramp split forecasts are required')
        for road in self.roads:
            cfg = component._config(road, parameters['by_direction'][road])
            # Area routes belong to the complete coupled network. Copy only the
            # accounting policy; physical dynamics remain the selected reference.
            for key, value in vars(full_cfg.network).items():
                if key.startswith('control_area_'):
                    setattr(cfg.network, key, copy.deepcopy(value))
            cfg.network.off_ramp_split_ratio = {o: float(off_splits[o]) for o in cfg.network.off_ramps}
            self.configs[road] = cfg
            spec = observation['lane_group_dynamics'].get(road)
            if spec is None:
                continue  # The reference keeps the western mainline aggregate.
            spec=copy.deepcopy(spec)
            spec['branch_partition_initial']={off:values for off,values in
                spec.get('branch_partition_initial',{}).items() if off in component.branch_partition}
            for off,parts in spec['branch_partition_initial'].items():
                cell=spec['off_access'][off]['cell']
                for rows in parts.values():
                    for row in rows:
                        if row['v_kmh'] is None:
                            if row['n_veh']!=0:raise ValueError('Occupied partition lacks observed speed')
                            row['v_kmh']=state.freeway_speed[road][cell]
            self.lanes[road] = PhysicalLaneGroups(spec, state, cfg, accounting,
                exchange_model=component.lane_exchange_model,
                interruption_gamma=component.lane_interruption_gamma,
                destination_policy=component.lane_destination_policy,
                momentum_advection=component.lane_momentum_advection,
                port_travel=component.lane_port_travel.get(road),
                position_aware_initial=component.port_initial_positions,
                upstream_exit_inventory={o: b for o, b in component.upstream_exit_inventory.items()
                                         if component.offramps[o]['road'] == road},
                ramp_conflict_through_inventory=[r for r in component.ramp_conflict_through_inventory
                                                if component.ramps[r]['road'] == road],
                branch_partition=[o for o in component.branch_partition if component.offramps[o]['road'] == road],
                partition_exchange=component.partition_exchange and any(
                    component.offramps[o]['road'] == road for o in component.branch_partition),
                partition_speed_context=component.partition_speed_context and any(
                    component.offramps[o]['road'] == road for o in component.branch_partition))
        if component.lane_groups_enabled != bool(self.lanes):
            raise ValueError('Enabled lane plant lacks its current lane observation')
        if component.upstream_exit_inventory:
            self.install_observed_exit_labels(observation['current_exit_labels'])

    def install_observed_exit_labels(self, labels):
        """Same current-route initialization as the reference experiment."""
        for road, plant in self.lanes.items():
            for off, fraction in plant.upstream_exit_inventory.items():
                table = labels[road][off]
                stop = plant.spec['off_access'][off]['cell']
                for i in range(stop+1):
                    eligible = plant.initial_off_eligible[off] if i == stop else plant.n[i]
                    values = []
                    for g, count in enumerate(eligible):
                        row = table[f'{i}:{g}']
                        if (abs(row['n']-count) > 1e-7 or
                            abs(row['known_off']+row['known_through']+row['unknown']-count) > 1e-7 or
                            any(not math.isfinite(row[k]) or row[k] < 0
                                for k in ('n', 'known_off', 'known_through', 'unknown'))):
                            raise ValueError('Current route labels do not partition observed stock')
                        values.append(row['known_off']+fraction*row['unknown'])
                    if i == stop:
                        plant.off[off] = values
                    else:
                        plant.upstream_off[off][i] = values
                plant.intent_initial[off] = sum(map(sum, plant.upstream_off[off])) + sum(plant.off[off])

    def advance(self, state, control, demand, *, ramp_releases, off_capacities,
                ramp_group_releases=None, off_group_capacities=None):
        from evaluation.controllers import area_freeway_accounting as accounting
        if state.time_sec != self.time_sec:
            raise ValueError('Noncontiguous physical freeway step')
        if set(ramp_releases) != set(self.ramps) or set(off_capacities) != set(self.offramps):
            raise ValueError('Physical stepping requires all eight ramps and eight off-ramps')
        if any(not math.isfinite(q) or q < 0 for q in (*ramp_releases.values(), *off_capacities.values())):
            raise ValueError('Invalid physical port flow')
        ttt, off_flows, diagnostics = 0., {}, {}
        for road in self.roads:
            cfg = self.configs[road]
            releases = {r: ramp_releases[r] for r in cfg.network.ramps}
            caps = {o: off_capacities[o] for o in cfg.network.off_ramps}
            plant = self.lanes.get(road)
            if plant is not None:
                cost, diagnostic = plant.advance(state, control, demand, cfg,
                    offramp_capacity_veh_h=caps, ramp_release_veh_h=releases,
                    ramp_group_release_veh_h={r: q for r, q in (ramp_group_releases or {}).items() if r in releases},
                    offramp_group_capacity_veh_h={o: q for o, q in (off_group_capacities or {}).items() if o in caps},
                    complete_allocator_scope=False)
                off_flows.update({o: sum(v)/cfg.simulation.T_f_h for o, v in plant.last_off_sent.items()})
            else:
                # Aggregate western equations are part of the chosen reference;
                # an unrequested western lane model is not manufactured here.
                from evaluation.controllers.sdmpc_prediction_cache import ramp_query_control
                no_meter = ramp_query_control(control)
                no_meter.ramp_metering.update(cfg.network.ramp_capacity_veh_h)
                _, release_diag = accounting._mn.compute_ramp_release_flows(
                    state, no_meter, demand, cfg, include_current_arrivals=False)
                cost, diagnostic = accounting._freeway_substep_events(state, control, demand, cfg,
                    offramp_capacity_veh_h=caps, ramp_release_veh_h=releases,
                    ramp_release_diagnostics=release_diag, update_ramp_queues=False, include_ramp_queue_ttt=False,
                    complete_allocator_scope=False)
                off_flows.update({o: diagnostic['offramp_flow_'+o] for o in caps})
            ttt += cost
            diagnostics[road] = diagnostic
            # Trace records are observation/debug output, never dynamical state.
            # Retaining450 histories in every finite-difference candidate would
            # consume memory without changing a subsequent flux or speed.
            if plant is not None:
                plant.rows.clear()
                plant.partition_rows.clear()
        # A full-network visit completes only after both independent road
        # allocators have recorded their actual resource constraints.
        accounting._area.get_ledger(state).complete_constraint_coverage('freeway_allocator')
        self.time_sec += self.configs[self.roads[0]].simulation.T_f_sec
        return ttt, off_flows, diagnostics
