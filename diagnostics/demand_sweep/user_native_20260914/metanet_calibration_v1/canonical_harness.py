"""Offline freeway component of the canonical METANET, with explicit boundaries.

This is not the complete coupled MPC. The existing transition and geometry/FD
hooks perform every traffic update. Physical on/off connectors are separate
configured boundary ports; no destination inventory is inferred from future
trajectories. A fresh tracing ledger observes selected flows, never resets N/v.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import runtime_setup, area_freeway_accounting as accounting
from evaluation.controllers.control_area_objective import ModelAreaLedger
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
from src.models.state import TrafficState, ControlAction
from src.models.demand import DemandStep

DEFAULT_CONFIG = ROOT / "diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/joint_config_fidelity_v3_portable.json"
PARAMETER_BOUNDS = {
    "v_free_multiplier": [0.65, 1.25],
    "rho_crit_multiplier": [0.6, 1.4],
    "tau_sec": [12.0, 60.0],
    "nu_km2_h": [3.0, 90.0],
    "kappa_veh_km_lane": [5.0, 120.0],
    "delta_merge": [0.0, 1.0],
}
BASELINE_PARAMETERS = {
    "v_free_multiplier": 1.0, "rho_crit_multiplier": 1.0,
    "tau_sec": 18.0, "nu_km2_h": 30.0,
    "kappa_veh_km_lane": 40.0, "delta_merge": 0.3,
}
OPTIONAL_PARAMETER_BOUNDS = {"lane_drop_phi": [0.0, 6.0]}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_geometry_profile(profile, repository_root=ROOT):
    """Relocate an archived diagnostic path without weakening its content pin."""
    root = Path(repository_root).resolve()
    declared = str(profile['path']).replace('\\', '/')
    absolute = declared.startswith('/') or PureWindowsPath(declared).is_absolute()
    candidate = (Path(declared) if absolute else root / declared).resolve()
    foreign_absolute = absolute and not Path(declared).is_absolute()
    if foreign_absolute or not candidate.is_relative_to(root):
        # Saved observations predate portability and contain the former checkout.
        # Only the explicit repository diagnostics suffix may be relocated.
        parts = declared.split('/')
        if not absolute or parts.count('diagnostics') != 1 or '..' in parts:
            raise ValueError('Geometry profile path cannot be relocated inside this repository')
        candidate = root.joinpath(*parts[parts.index('diagnostics'):]).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError('Geometry profile resolves outside this repository')
    if sha256(candidate) != profile['sha256']:
        raise ValueError('Geometry profile changed after observation extraction')
    return candidate


def load_base_model(geometry, baseline_config=DEFAULT_CONFIG):
    return CanonicalFreewayModel(geometry, baseline_config)


class DelayedPort:
    """Finite connector stock with causal travel cohorts and separate drainage."""

    def __init__(self, capacity, length_m, travel_speed_kmh, cohorts, start_s):
        if (not all(math.isfinite(x) for x in (capacity, length_m, travel_speed_kmh, start_s))
                or min(capacity, length_m, travel_speed_kmh) <= 0 or start_s < 0):
            raise ValueError('Positive port geometry/travel speed required')
        if any(len(row) != 3 or not all(math.isfinite(float(x)) for x in row)
               or min(float(row[0]),float(row[1])) < 0 or float(row[2]) < 1 for row in cohorts):
            raise ValueError('Invalid observed connector position/speed/lane cohort')
        self.capacity = float(capacity)
        self.last_time_s = float(start_s)
        self.travel_s = float(length_m) / (float(travel_speed_kmh)/3.6)
        self.ready = 0.
        self.pending = [[start_s+max(0., length_m-float(p))/(travel_speed_kmh/3.6), 1.]
                        for p, _v, _lane in cohorts]
        self.initial = self.stock
        self.admitted = self.departed = 0.
        if self.stock > self.capacity+1e-8:
            raise ValueError('Observed initial connector stock exceeds declared capacity')

    @property
    def stock(self):
        return self.ready+sum(n for _t,n in self.pending)

    def release(self, start_s, dt_s, service_vph):
        if (not all(math.isfinite(x) for x in (start_s, dt_s, service_vph))
                or dt_s <= 0 or service_vph < 0 or start_s < self.last_time_s-1e-9):
            raise ValueError('Nonfinite, negative or backward connector drainage request')
        self.last_time_s = float(start_s)
        self.ready += sum(n for t,n in self.pending if t <= start_s+1e-9)
        self.pending = [[t,n] for t,n in self.pending if t > start_s+1e-9]
        amount = min(self.ready, max(0., service_vph)*dt_s/3600.)
        self.ready -= amount
        self.departed += amount
        return amount

    def accept(self, end_s, amount):
        if (not math.isfinite(end_s) or not math.isfinite(amount)
                or end_s < self.last_time_s-1e-9 or amount < 0):
            raise ValueError('Invalid connector admission time/amount')
        if self.stock+amount > self.capacity+1e-7:
            raise ArithmeticError('Connector admission violates finite storage')
        self.last_time_s = float(end_s)
        self.pending.append([end_s+self.travel_s, max(0., amount)])
        self.admitted += amount
        residual = self.stock-self.initial-self.admitted+self.departed
        if abs(residual) > 1e-7:
            raise ArithmeticError('Connector conservation failure')


class CanonicalFreewayModel:
    def __init__(self, geometry, baseline_config):
        if isinstance(geometry, (str, Path)):
            geometry = json.loads(Path(geometry).read_text(encoding="utf-8-sig"))
        self.geometry = copy.deepcopy(geometry)
        self.geometry_cells = {(r["road"], int(r["cell"])): r for r in geometry["cells"]}
        tuning = json.loads(Path(baseline_config).read_text(encoding="utf-8-sig"))
        if geometry.get('geometry_profile'):
            profile = geometry['geometry_profile']
            profile_path = resolve_geometry_profile(profile)
            from evaluation.controllers.freeway_geometry import geometry_fingerprint
            profile_document = json.loads(profile_path.read_text(encoding='utf-8'))
            if geometry_fingerprint(geometry) != profile_document['physical_geometry_sha256']:
                raise ValueError('Observed physical topology does not match geometry profile')
            tuning['freeway']['geometry_profile'] = str(profile_path)
        mapping = json.loads((ROOT / tuning["mapping_json"]).read_text(encoding="utf-8-sig"))
        if geometry['mapping']['sha256'] != sha256(ROOT / tuning['mapping_json']):
            raise ValueError('Observation geometry and model use different canonical mappings')
        cfg = adapter.build_config(ROOT / "vendor/NumSim-mine", 150.0, 9000.0,
                                   "normal", {}, tuning, local_observation=True, flagship=True)
        self.runtime_metadata = runtime_setup.configure_freeway_runtime(adapter, cfg, tuning, mapping)
        self.base = cfg
        self.roads = tuple(cfg.network.freeway_links)
        if set(self.geometry_cells) != {(r, c) for r in self.roads for c in range(21)}:
            raise ValueError("Expected all 42 canonical spatial cells")
        meter_groups = {str(r["id"]): r["model_ramp_key"] for r in mapping["ramp_meters"]}
        # Storage conversion uses the canonical vehicle spacing; it is geometry,
        # not a fitted spillback capacity or a future observed maximum.
        spacing = float(cfg.network.urban_avg_vehicle_length_m)
        ports = geometry["boundaries"]
        self.ramps = {str(r["id"]): {**r, "group": meter_groups[str(r["id"])],
            "storage_capacity_veh": r["length_m"]*r["lanes"]/spacing} for r in ports if r["kind"] == "ramp"}
        self.offramps = {str(r["connector"]): {**r,
            "storage_capacity_veh": r["length_m"]*r["lanes"]/spacing} for r in ports if r["kind"] == "offramp"}
        if len(self.ramps) != 8 or len(self.offramps) != 8:
            raise ValueError("Expected eight separate on-ramp and eight off-ramp ports")
        self.provenance = {
            "scope": "canonical freeway component; external ramp releases and off-ramp receiving boundaries; no coupled urban forecast or destination route inventory",
            "baseline_config": str(Path(baseline_config).relative_to(ROOT)),
            "baseline_config_sha256": sha256(baseline_config),
            "model_files": {str(p.relative_to(ROOT)): sha256(p) for p in (
                ROOT / "evaluation/controllers/vissim_stackelberg_adapter.py",
                ROOT / "evaluation/controllers/area_freeway_accounting.py",
                ROOT / "evaluation/controllers/control_area_objective.py",
                ROOT / "evaluation/controllers/freeway_fd.py",
                ROOT / "evaluation/controllers/freeway_geometry.py",
                ROOT / "evaluation/controllers/physical_ramp_boundary.py",
                ROOT / "evaluation/controllers/runtime_setup.py",
                ROOT / "evaluation/controllers/freeway_local_state.py",
                ROOT / "evaluation/controllers/link_predictor.py",
                ROOT / "evaluation/controllers/offramp_routing.py",
                ROOT / "evaluation/parameters.json",
                ROOT / "evaluation/parameters.py",
                ROOT / "vendor/NumSim-mine/src/models/metanet.py",
                ROOT / "vendor/NumSim-mine/src/models/state.py",
                ROOT / "vendor/NumSim-mine/src/models/demand.py",
                ROOT / "vendor/NumSim-mine/src/simulation/coupling.py",
                ROOT / "vendor/NumSim-mine/src/config/default.yaml",
                ROOT / tuning['mapping_json'],
                ROOT / tuning["freeway"]["segment_params"],
            )},
            "canonical_continuity_length_km": cfg.network.freeway_segment_length_km,
            "canonical_step_seconds": cfg.simulation.T_f_sec,
            "fd_family": "two_branch" if getattr(cfg.network, "vsl_fd_two_branch", False) else "exponential",
            "capacity_drop_discharge_phi": cfg.network.capacity_drop_discharge_phi,
            "lane_drop_phi": cfg.network.freeway_lane_drop_phi,
            "source_capacity_veh_h": cfg.network.freeway_capacity_veh_h,
            "parameter_bounds": PARAMETER_BOUNDS,
        }

    def _config(self, road, parameters):
        cfg = copy.deepcopy(self.base)
        net = cfg.network
        net.freeway_links = [road]
        rows = net.freeway_segment_params[road]
        allowed_bounds = {**PARAMETER_BOUNDS, **OPTIONAL_PARAMETER_BOUNDS}
        unknown = set(parameters) - allowed_bounds.keys()
        if unknown:
            raise ValueError("Unknown calibration parameters: " + repr(unknown))
        for key, value in parameters.items():
            lo, hi = allowed_bounds[key]
            if not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError("Calibration parameter outside predeclared bounds: " + key)
        net.v_free *= parameters.get("v_free_multiplier", 1.0)
        net.rho_crit *= parameters.get("rho_crit_multiplier", 1.0)
        for key, target, scale in (("tau_sec", "metanet_tau_h", 1/3600),
                                   ("nu_km2_h", "metanet_nu_km2_h", 1),
                                   ("kappa_veh_km_lane", "metanet_kappa_veh_km_lane", 1)):
            if key in parameters:
                setattr(net, target, parameters[key]*scale)
        for row in rows:
            row["v_free"] = row.get("v_free", self.base.network.v_free) * parameters.get("v_free_multiplier", 1.0)
            row["rho_crit"] = row.get("rho_crit", self.base.network.rho_crit) * parameters.get("rho_crit_multiplier", 1.0)
            for key, target, scale in (("tau_sec", "metanet_tau_h", 1/3600),
                                       ("nu_km2_h", "metanet_nu_km2_h", 1),
                                       ("kappa_veh_km_lane", "metanet_kappa_veh_km_lane", 1)):
                if key in parameters:
                    row[target] = parameters[key] * scale
        if "delta_merge" in parameters:
            net.metanet_delta_merge = parameters["delta_merge"]
        if "lane_drop_phi" in parameters:
            net.freeway_lane_drop_phi = parameters["lane_drop_phi"]
        # Eight physical ports use the existing configurable indices. Their
        # external releases do not need fictitious urban approach inventories.
        ramps = {k: v for k, v in self.ramps.items() if v["road"] == road}
        net.ramps = list(ramps)
        net.ramp_to_freeway = {k: road for k in ramps}
        net.ramp_merge_segment_index = {k: int(v["to_cell"]) for k, v in ramps.items()}
        net.ramp_capacity_veh_h = {k: float(v.get("service_capacity_veh_h", self.base.network.ramp_capacity_veh_h[v["group"]])) for k, v in ramps.items()}
        net.ramp_queue_max_veh_by_ramp = {k: float(v.get("storage_capacity_veh", self.base.network.ramp_queue_cap(v["group"]))) for k, v in ramps.items()}
        offramps = {k: v for k, v in self.offramps.items() if v["road"] == road}
        net.off_ramps = list(offramps)
        net.off_ramp_from_freeway = {k: road for k in offramps}
        net.off_ramp_segment_index = {k: int(v["from_cell"]) for k, v in offramps.items()}
        net.off_ramp_split_ratio = {k: 0.0 for k in offramps}
        net.off_ramp_storage_link = {k: "offline_off:" + k for k in offramps}
        for k, v in offramps.items():
            net.urban_link_storage_veh["offline_off:" + k] = float(v["storage_capacity_veh"])
        if hasattr(net, "offramp_route_inventory"):
            raise ValueError("Offline component must not inherit uninitialized destination inventories")
        return cfg

    def rollout(self, initial_cells, boundary_steps, overrides=None, initial_origin_queue=None, *, roads=None,
                port_dynamics=None, ramp_dynamics=None, vsl_zone_heads=None):
        """Advance one contiguous450s forecast; read observed cells only at t0.

        Boundary steps are10s dictionaries with source_demand_vph[road],
        ramp_release_vph[RM_C...], off_capacity_vph[connector], and
        off_split_ratio[connector]. Optional offramp_occupancy_veh supplies
        external receiving-storage boundary support, explicitly not FW states.
        Optional ramp_dynamics replaces only named external ramp releases with
        conserved travelling/head/merge buffers. Each step then requires explicit
        ramp_arrival_vph and ramp_head_service for those ramps. The canonical
        receiving query sees their predicted eligible stock, never future data.
        Optional vsl_zone_heads projects explicit physical actuator intervals onto
        this component's cells. Absent means the existing zone map is unchanged.
        """
        initial = {(r["road"], int(r["cell"])): r for r in initial_cells}
        starts = {float(r["time_s"]) for r in initial_cells}
        if len(starts) != 1 or not boundary_steps:
            raise ValueError("Exactly one observed initial frame and nonempty boundaries required")
        start = next(iter(starts))
        tf = float(self.base.simulation.T_f_sec)
        if len(boundary_steps) * tf != 450:
            raise ValueError("Every rollout must contain all450s at canonical step")
        for index, row in enumerate(boundary_steps):
            if row["window_start_s"] != start + index*tf or row["window_end_s"] != start + (index+1)*tf:
                raise ValueError("Boundary windows must be contiguous and begin at the observed cutoff")
        override_by = (overrides or {}).get("by_direction", {})
        cells, flows, details, port_rows = [], [], [], []
        selected_roads = self.roads if roads is None else tuple(roads)
        if not selected_roads or set(selected_roads) - set(self.roads):
            raise ValueError("Unknown/empty selected freeway directions")
        if vsl_zone_heads is not None:
            if not isinstance(vsl_zone_heads, dict) or not vsl_zone_heads or set(vsl_zone_heads)-set(self.roads):
                raise ValueError('Unknown or empty explicit VSL zone map')
            for road, heads in vsl_zone_heads.items():
                if (not isinstance(heads, list) or not heads or heads[0] != 0
                        or any(type(x) is not int or not 0 <= x < 21 for x in heads)
                        or heads != sorted(set(heads))):
                    raise ValueError('Explicit VSL heads must be sorted unique cell indices beginning at zero')
        ramp_specs = {}
        local_ramp_step = tf
        meter_cycle = None
        ramp_rows, ramp_metadata = [], {}
        if ramp_dynamics is not None:
            if (ramp_dynamics.get('schema') != 'physical-ramp-boundary/v1'
                    or not isinstance(ramp_dynamics.get('ramps'), dict)
                    or not ramp_dynamics['ramps']):
                raise ValueError('Unknown or empty physical ramp dynamics contract')
            ramp_specs = ramp_dynamics['ramps']
            if set(ramp_specs) - set(self.ramps):
                raise ValueError('Unknown physical ramp dynamics target')
            local_ramp_step = ramp_dynamics.get('local_step_sec', tf)
            if isinstance(local_ramp_step, bool) or local_ramp_step not in (1., tf):
                raise ValueError('Ramp local step must be1s or the unchanged freeway step')
            if local_ramp_step == 1.:
                meter_cycle = ramp_dynamics.get('meter_cycle_sec')
                if isinstance(meter_cycle, bool) or meter_cycle != tf:
                    raise ValueError('Local ramp cycle must explicitly equal the freeway interval')
        for road in selected_roads:
            cfg = self._config(road, override_by.get(road, {}))
            if vsl_zone_heads is not None and road in vsl_zone_heads:
                adapter.install_freeway_vsl_zones(cfg, {'freeway': {
                    'vsl_zone_heads': {road: vsl_zone_heads[road]}}})
            net = cfg.network
            lanes = net.freeway_segment_lanes[road]
            lengths = accounting.cell_lengths_km(cfg, road, len(lanes))
            state = TrafficState.initial(cfg)
            state.time_sec = start
            state.freeway_effective_lanes[road] = list(lanes)
            n0 = [float(initial[road, c]["n_veh"]) for c in range(21)]
            state.freeway_density[road] = [n/(lengths[c]*lanes[c]) for c,n in enumerate(n0)]
            state.freeway_speed[road] = [float(initial[road,c]["v_kmh"]) if initial[road,c]["v_kmh"] not in (None, "")
                                         else net.freeway_segment_params[road][c].get("v_free", net.v_free) for c in range(21)]
            state.mainline_origin_queue[road] = float((initial_origin_queue or {}).get(road, 0.0))
            state.urban_link_storage = dict(net.urban_link_storage_veh)
            control = ControlAction.uncontrolled(cfg)
            vsl_audit = None
            if vsl_zone_heads is not None:
                if getattr(net, 'freeway_buffer_segments', 0):
                    raise ValueError('Component VSL binding audit requires no external freeway buffer cells')
                vsl_audit = {'alpha_vsl': float(net.alpha_vsl),
                    'vsl_max': float(max(cfg.freeway_follower.vsl_set)),
                    'cells': [{'cell':i,'samples':0,'command_active_samples':0,
                        'desired_speed_binding_samples':0,'max_desired_speed_reduction_kmh':0.}
                        for i in range(21)]}
            ramp_buffers = {}
            for ramp in net.ramps:
                if ramp not in ramp_specs:
                    continue
                buffer = PhysicalRampBoundary(**ramp_specs[ramp])
                geometry = self.ramps[ramp]
                if (buffer.connector_id != str(geometry['connector']) or buffer.time_sec != start
                        or abs(buffer.length_m-geometry['length_m']) > 1e-8
                        or buffer.lanes != geometry['lanes']
                        or abs(buffer.spacing_m-net.urban_avg_vehicle_length_m) > 1e-8):
                    raise ValueError('Ramp dynamics geometry/time differs from physical port')
                ramp_buffers[ramp] = buffer
                ramp_metadata[ramp] = buffer.metadata()
            stores = {}
            if port_dynamics:
                if port_dynamics.get('schema') != 'physical-off-storage/v1':
                    raise ValueError('Unknown port dynamics contract')
                if not port_dynamics['occupancy_lane_loss']:
                    cfg.freeway_offramp_capacity_drop.enabled = False
                for off in net.off_ramps:
                    spec = self.offramps[off]
                    stores[off] = DelayedPort(spec['storage_capacity_veh'], spec['length_m'],
                        port_dynamics['travel_speed_kmh'][off], port_dynamics['initial_cohorts'][off], start)
            bucket = {c: {"downstream_crossings": 0.0, "source_admissions": 0.0,
                          "ramp_merges": 0.0, "off_departures": 0.0, "terminal_exits": 0.0} for c in range(21)}
            projections = speed_projections = 0
            residual_max = 0.0
            freeway_residence = requested_source = accepted_source = 0.0
            jam_exceedances = 0
            density_above_critical = negative_count = 0
            maximum_density_ratio = 0.0
            for step in boundary_steps:
                t = float(step["window_start_s"])
                if 'vsl_commands' in step:
                    control.vsl.update(step['vsl_commands'])
                releases = {r: float(step["ramp_release_vph"][r]) for r in net.ramps if r not in ramp_buffers}
                caps = {o: float(step["off_capacity_vph"][o]) for o in net.off_ramps}
                net.off_ramp_split_ratio = {o: float(step["off_split_ratio"][o]) for o in net.off_ramps}
                occupancy = step.get("offramp_occupancy_veh", {})
                for off in net.off_ramps:
                    storage = net.off_ramp_storage_link[off]
                    if off in stores:
                        store = stores[off]
                        store.release(t, tf, float(step['off_drain_vph'][off]))
                        state.urban_link_storage[storage] = max(0., store.capacity-store.stock)
                        caps[off] = max(0., store.capacity-store.stock)*3600/tf
                    elif off in occupancy:
                        state.urban_link_storage[storage] = max(0.0, net.urban_link_storage_veh[storage] - float(occupancy[off]))
                demand = DemandStep({road: float(step["source_demand_vph"][road])}, {}, {})
                interval_ramp_rows = []
                if ramp_buffers and local_ramp_step == 1.:
                    # Supply is queried once from the t-start freeway state.
                    # Scratch availability prevents today's post-head stock from
                    # being mistaken for the receiving CAPACITY. It creates no
                    # live vehicles or accepted-flow ledger entries.
                    supply_state = copy.copy(state)
                    supply_state.ramp_queue = dict(state.ramp_queue)
                    dt_h = cfg.simulation.T_f_h
                    for ramp in ramp_buffers:
                        cap = net.ramp_capacity_veh_h[ramp]
                        supply_state.ramp_queue[ramp] = math.nextafter(cap*dt_h, math.inf)
                        control.ramp_metering[ramp] = cap
                    selected, _ = accounting._mn.compute_ramp_release_flows(
                        supply_state, control, demand, cfg, include_current_arrivals=False)
                    for ramp, buffer in ramp_buffers.items():
                        budget_rate = float(selected[ramp])
                        if not math.isfinite(budget_rate) or budget_rate < 0:
                            raise ValueError('Invalid canonical ramp receiving budget')
                        arrival_vph = float(step['ramp_arrival_vph'][ramp])
                        if not math.isfinite(arrival_vph) or arrival_vph < 0:
                            raise ValueError('Ramp approach requests must be finite and nonnegative')
                        receipt = buffer.advance_local_interval(start_sec=t, duration_sec=tf,
                            cycle_sec=meter_cycle, receiving_budget_veh=budget_rate*dt_h,
                            request_arrivals_veh=arrival_vph*dt_h,
                            **step['ramp_head_service'][ramp])
                        accepted = receipt['accepted_merge_veh']
                        q = accepted/dt_h
                        coupling_roundoff = q*tf/3600.-accepted
                        if abs(coupling_roundoff) > 1e-8:
                            raise ArithmeticError('Ramp/freeway merge interface roundoff exceeds tolerance')
                        receipt.update(road=road, ramp=ramp,
                            canonical_receiving_budget_vph=budget_rate,
                            applied_merge_vph=q, merge_interface_roundoff_veh=coupling_roundoff)
                        interval_ramp_rows.append(receipt)
                        releases[ramp] = q
                        state.ramp_queue[ramp] = receipt['end']['merge_ready_veh']
                elif ramp_buffers:
                    for ramp, buffer in ramp_buffers.items():
                        eligible = buffer.begin_interval(t, tf)['eligible_merge_veh']
                        state.ramp_queue[ramp] = eligible
                        # The signal has already limited head crossing. Vehicles
                        # downstream of it retain only the canonical merge cap.
                        control.ramp_metering[ramp] = net.ramp_capacity_veh_h[ramp]
                    selected, _ = accounting._mn.compute_ramp_release_flows(
                        state, control, demand, cfg, include_current_arrivals=False)
                    dt_h = cfg.simulation.T_f_h
                    for ramp, buffer in ramp_buffers.items():
                        q = float(selected[ramp])
                        eligible = state.ramp_queue[ramp]
                        raw_amount = q*dt_h
                        if not math.isfinite(q) or q < 0 or raw_amount > eligible+1e-8:
                            raise ValueError('Canonical ramp merge exceeds eligible stock')
                        # Record, rather than conceal, rate/vehicle roundoff. The
                        # exact adjusted rate is used by the freeway and buffer.
                        while q*dt_h > eligible:
                            q = math.nextafter(q, 0.0)
                        amount = q*dt_h
                        buffer.commit_merge(amount)
                        service = step['ramp_head_service'][ramp]
                        buffer.apply_head_service(**service)
                        arrival_vph = float(step['ramp_arrival_vph'][ramp])
                        if not math.isfinite(arrival_vph) or arrival_vph < 0:
                            raise ValueError('Ramp approach requests must be finite and nonnegative')
                        receipt = buffer.finish_interval(arrival_vph*dt_h)
                        receipt.update(road=road, ramp=ramp,
                            canonical_selected_merge_vph=float(selected[ramp]),
                            applied_merge_vph=q, merge_roundoff_adjustment_veh=raw_amount-amount)
                        interval_ramp_rows.append(receipt)
                        releases[ramp] = q
                        state.ramp_queue[ramp] = receipt['end']['merge_ready_veh']
                before = accounting.continuity_vehicle_counts(state, cfg)[road]
                stocks = {"freeway:" + road: {"inside": sum(before)},
                          "origin:" + road: {"outside": state.mainline_origin_queue[road]},
                          **{"merge_pending:" + r: {"outside": q*tf/3600} for r,q in releases.items()}}
                trace = ModelAreaLedger(stocks, capture_response=True)
                trace.begin_response_step("freeway", t, t+tf)
                trace.expect_constraint_coverage("freeway_allocator")
                state._control_area_ledger = trace
                desired_speed = accounting._mn.effective_desired_speed_kmh
                observed_desired = []
                if vsl_audit is not None:
                    # Observe the actual call after its segment context is armed.
                    # The second pure FD evaluation disables only the speed cap;
                    # its result is diagnostic and never enters the transition.
                    def record_desired(*args, **kwargs):
                        value = desired_speed(*args, **kwargs)
                        if kwargs or len(args) != 10:
                            raise ValueError('Unexpected desired-speed call contract')
                        baseline_args = list(args)
                        baseline_args[5] = False
                        baseline_value = desired_speed(*baseline_args)
                        observed_desired.append((bool(args[5]), float(value), float(baseline_value)))
                        return value
                    accounting._mn.effective_desired_speed_kmh = record_desired
                try:
                    residence, diag = accounting._freeway_substep_events(state, control, demand, cfg,
                        offramp_capacity_veh_h=caps, ramp_release_veh_h=releases,
                        ramp_release_diagnostics={"total_no_meter_flow": sum(releases.values()), "mean_ramp_receiving_factor": 1.0},
                        update_ramp_queues=False, include_ramp_queue_ttt=False)
                finally:
                    if vsl_audit is not None:
                        accounting._mn.effective_desired_speed_kmh = desired_speed
                if vsl_audit is not None:
                    if len(observed_desired) != 21:
                        raise ValueError('Missing or extra component desired-speed observations')
                    for audit, (active, value, baseline_value) in zip(vsl_audit['cells'], observed_desired):
                        reduction = max(0., baseline_value-value)
                        audit['samples'] += 1
                        audit['command_active_samples'] += int(active)
                        audit['desired_speed_binding_samples'] += int(reduction > 1e-9)
                        audit['max_desired_speed_reduction_kmh'] = max(audit['max_desired_speed_reduction_kmh'], reduction)
                state.time_sec = t+tf
                ramp_rows.extend(interval_ramp_rows)
                freeway_residence += residence
                requested_source += demand.freeway_mainline[road]*tf/3600
                actual = {"mainline": [0.0]*21, "off": [0.0]*21, "ramp": [0.0]*21, "entry": 0.0}
                for row in trace._response["resource_allocations"]:
                    kind, value = row["kind"], row["accepted_total_veh"]
                    if kind == "freeway_mainline_sending":
                        actual["mainline"][int(row["resource"].rsplit(":",1)[1])] = value
                    elif kind == "freeway_terminal_sending":
                        actual["mainline"][-1] = value
                    elif kind == "freeway_entry_request":
                        actual["entry"] = value
                    elif kind == "freeway_offramp_sending":
                        actual["off"][net.off_ramp_segment_index[row["resource"]]] += value
                        if row['resource'] in stores:
                            stores[row['resource']].accept(t+tf, value)
                for off, store in stores.items():
                    port_rows.append({'time_s': t+tf, 'road': road, 'connector': off,
                        'n_veh': store.stock, 'ready_veh': store.ready,
                        'admitted_veh': store.admitted, 'departed_veh': store.departed,
                        'conservation_residual_veh': store.stock-store.initial-store.admitted+store.departed})
                for ramp, q in releases.items():
                    actual["ramp"][net.ramp_merge_segment_index[ramp]] += q*tf/3600
                after = accounting.continuity_vehicle_counts(state,cfg)[road]
                accepted_source += actual['entry']
                jam_exceedances += sum(rho > net.rho_max+1e-9 for rho in state.freeway_density[road])
                density_above_critical += int(diag['density_exceedance_count'])
                negative_count += sum(rho < -1e-9 for rho in state.freeway_density[road])
                maximum_density_ratio = max(maximum_density_ratio,max(state.freeway_density[road])/net.rho_max)
                for c in range(21):
                    incoming = actual["entry"] if c == 0 else actual["mainline"][c-1]
                    expected = before[c]+incoming+actual["ramp"][c]-actual["off"][c]-actual["mainline"][c]
                    residual_max = max(residual_max, abs(after[c]-expected))
                    bucket[c]["downstream_crossings"] += actual["mainline"][c] if c < 20 else 0.0
                    bucket[c]["terminal_exits"] += actual["mainline"][c] if c == 20 else 0.0
                    bucket[c]["source_admissions"] += actual["entry"] if c == 0 else 0.0
                    bucket[c]["ramp_merges"] += actual["ramp"][c]
                    bucket[c]["off_departures"] += actual["off"][c]
                projections += int(diag["density_projection_count"])
                speed_projections += int(diag["speed_projection_count"])
                if (t+tf-start) % 30 == 0:
                    for c,n in enumerate(after):
                        physical_area = float(self.geometry_cells[road,c]["lane_km"])
                        cells.append({"time_s": t+tf, "road":road,"cell":c,"n_veh":n,
                            "rho_veh_per_km_lane":n/physical_area,"rho_canonical":state.freeway_density[road][c],
                            "v_kmh":state.freeway_speed[road][c],"effective_lanes":state.freeway_effective_lanes[road][c]})
                        flows.append({"window_start_s":t+tf-30,"window_end_s":t+tf,"road":road,"cell":c,**bucket[c]})
                    bucket = {c:dict.fromkeys(bucket[c],0.0) for c in range(21)}
            details.append({"road":road,"start_s":start,"end_s":start+450,"density_projection_count":projections,
                "speed_projection_count":speed_projections,"continuity_residual_max_veh":residual_max,
                "jam_density_exceedance_count":jam_exceedances,"model_residence_10s_veh_h":freeway_residence,
                "canonical_density_above_critical_count":density_above_critical,"negative_density_count":negative_count,
                "maxdensity_ratio":maximum_density_ratio,
                "requested_source_veh":requested_source,"accepted_source_veh":accepted_source,
                "initial_origin_queue_veh":float((initial_origin_queue or {}).get(road,0)),
                "final_origin_queue_veh":state.mainline_origin_queue[road],"initial_n_veh":sum(n0),"final_n_veh":sum(after)})
            if ramp_buffers:
                residence_key = ('ramp_connector_residence_local_1s_veh_h' if local_ramp_step == 1.
                                 else 'ramp_connector_residence_10s_veh_h')
                details[-1][residence_key] = sum(buffer.connector_ttt_veh_h for buffer in ramp_buffers.values())
                details[-1]['ramp_ttt_scope'] = ('Local1s interval-start connector stock only; upstream outside-component backlog excluded'
                    if local_ramp_step == 1. else 'Interval-start connector stock only; upstream outside-component backlog excluded')
            if vsl_audit is not None:
                details[-1]['vsl_binding_audit'] = vsl_audit
        if any(not math.isfinite(row[key]) for row in cells for key in ("n_veh","v_kmh","rho_veh_per_km_lane")):
            raise ArithmeticError("Nonfinite canonical rollout")
        result = {"cells":cells,"flows":flows,"diagnostics":{"roads":details,"future_state_resets":0,"horizon_s":450}}
        if port_dynamics:
            result['ports'] = port_rows
            result['diagnostics']['dynamic_off_storage'] = True
        if ramp_dynamics is not None:
            result['ramps'] = ramp_rows
            result['diagnostics']['dynamic_ramp_boundary'] = {
                'schema': 'physical-ramp-boundary/v1', 'metadata': ramp_metadata,
                'outside_backlog_scope': 'Outside this freeway/connector component; caller must assign its real upstream area and cost',
                'other_ramps': 'Existing external release boundaries unchanged',
            }
            if local_ramp_step == 1.:
                result['diagnostics']['dynamic_ramp_boundary'].update(
                    local_step_sec=1., meter_cycle_sec=meter_cycle,
                    receiving_rule='Canonical10s t-start receiving budget with uniform1s rate envelope',
                    head_rule='Finite nominal post-head storage; preserve observed initial excess and block new head service until space opens')
        if vsl_zone_heads is not None:
            result['diagnostics']['explicit_vsl_zone_heads'] = copy.deepcopy(vsl_zone_heads)
        return result
