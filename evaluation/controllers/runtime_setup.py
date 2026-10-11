"""Ordered VISSIM runtime setup shared by the adapter, replay, and price workers.

Values and model structure are configured once in the parent/replay path.
Workers reinstall hooks from the configured network object without re-estimating
parameters or projecting observations again. No source execution is used here.
"""
from __future__ import annotations

from evaluation.controllers import freeway_local_state
from evaluation.controllers import link_predictor
from evaluation.controllers import offramp_routing
from evaluation.controllers import signal_actuation_contract
from evaluation.controllers import observation_projection
from evaluation.controllers.freeway_fd import install_freeway_fd_runtime, configure_state_response, configure_literature_vsl


def load_k8b_evidence(pin, schema, key):
    """K8b config key value {"evidence": <repository-relative path>, "evidence_sha256": <sha256 of its bytes>} ->
    (document, sha256).  Another shape, a path outside the repository, a sha mismatch or another schema is a
    configuration error (ValueError; K8_PREDECLARATION_AMENDMENT_16 r2 sections 2.0-3 / 2.0-6)."""
    import hashlib
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    if not isinstance(pin, dict) or set(pin) != {'evidence', 'evidence_sha256'}:
        raise ValueError(key + ' must be {"evidence": path, "evidence_sha256": sha256}')
    if not isinstance(pin['evidence'], str) or not pin['evidence'] or Path(pin['evidence']).is_absolute():
        raise ValueError(key + '.evidence must be a repository-relative path')
    digest = pin['evidence_sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError(key + '.evidence_sha256 must be 64 lowercase hex digits')
    path = (root / pin['evidence']).resolve(strict=True)
    if not path.is_relative_to(root.resolve()):
        raise ValueError(key + ' evidence resolves outside the repository')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(key + ' evidence sha256 mismatch: ' + str(path))
    document = json.loads(data.decode('utf-8'))
    if not isinstance(document, dict) or document.get('schema') != schema:
        raise ValueError(key + ' evidence schema must be ' + schema)
    return document, digest


WOUT_EXIT_LAWS = ('per_destination_class_v1',)


def install_wout_exit_law(cfg, tuning):
    """K8b-2 P-4' + P-4b (K8_PREDECLARATION_AMENDMENT_16 r2 sections 2.3 / 2.4 as corrected by AMENDMENT_17, variant
    of D-K8b-4; key urban.wout_exit_law = {"SC1001_W_out": {"law", "variant", "evidence", "evidence_sha256"}}):
    after the physical ramp names are final, cfg.network.wout_exit_law = {link: spec} with the evidence's classes,
    per-class destination shares, exit-law lengths (km) and the direct row (connector, group, residence length);
    destinations are 'free' and the runtime ramp keys of R_D_E / R_D_W.  Key absent: {} and nothing is set."""
    law = ((tuning or {}).get('urban') or {}).get('wout_exit_law')
    if law is None:
        return {}
    if not isinstance(law, dict) or not law:
        raise ValueError('urban.wout_exit_law must map W_out links to their exit law')
    net = cfg.network
    table = getattr(net, 'boundary_out_ramp_split', None) or {}
    out, meta = {}, {}
    for link, row in law.items():
        if not isinstance(row, dict) or set(row) != {'law', 'variant', 'evidence', 'evidence_sha256'}:
            raise ValueError('urban.wout_exit_law.%s must be {law, variant, evidence, evidence_sha256}' % link)
        if row['law'] not in WOUT_EXIT_LAWS:
            raise ValueError('urban.wout_exit_law.%s.law must be one of %s' % (link, WOUT_EXIT_LAWS))
        document, digest = load_k8b_evidence({'evidence': row['evidence'], 'evidence_sha256': row['evidence_sha256']},
                                             'k8b-wout-exit/v1', 'urban.wout_exit_law.' + link)
        v = document['values']
        if v['link'] != link or v['variant'] != row['variant'] or v['law'] != row['law']:
            raise ValueError('urban.wout_exit_law.%s: link / variant / law differ from the evidence' % link)
        if link not in table or not bool(getattr(net, 'leg_ramp_split_enabled', False)):
            raise ValueError('urban.wout_exit_law.%s needs the leg ramp split of that link' % link)
        ramp_of = v['ramp_of']
        if sorted(str(r) for r in (table[link].get('ramps') or {})) != sorted(ramp_of.values()):
            raise ValueError('urban.wout_exit_law.%s: runtime ramps %s differ from %s'
                             % (link, sorted(table[link].get('ramps') or {}), ramp_of))
        direct = v['direct']
        tails = getattr(net, 'offramp_direct_tail_by_offramp', None) or {}
        if direct is not None and tails.get(direct['group']) != link:
            raise ValueError('urban.wout_exit_law.%s: the direct row %s does not land on it' % (link, direct))
        dests = ('free',) + tuple(ramp_of[name] for name in ('R_D_E', 'R_D_W'))
        to_dest = {'free': 'free', **{name: ramp_of[name] for name in ramp_of}}
        shares, lengths = {}, {}
        for c in v['classes']:
            sh = {'free': float(v['shares'][c]['free'])}
            for name, ramp in ramp_of.items():
                sh[ramp] = float(v['shares'][c][name])
            if abs(sum(sh.values()) - 1.0) > 1e-12 or any(x < 0.0 for x in sh.values()):
                raise ValueError('urban.wout_exit_law.%s: shares of class %s must be >= 0 and sum to 1' % (link, c))
            shares[c] = sh
            lengths[c] = {to_dest[name]: (None if x is None else float(x)) for name, x in v['l_km'][c].items()}
            if set(lengths[c]) != set(dests):
                raise ValueError('urban.wout_exit_law.%s: lengths of class %s must name %s' % (link, c, dests))
        spec = {'link': link, 'law': row['law'], 'variant': v['variant'], 'dests': dests,
                'classes': tuple(v['classes']), 'i0_class': v['i0_class'], 'direct_class': v['direct_class'],
                's': shares, 'l_km': lengths,
                'direct': (None if direct is None else
                           {'off': str(direct['off']), 'group': str(direct['group']),
                            'l_residence_km': float(direct['l_residence_km'])}),
                'evidence_sha256': digest}
        if spec['i0_class'] not in spec['classes'] or (spec['direct_class'] is not None
                                                        and spec['direct_class'] not in spec['classes']):
            raise ValueError('urban.wout_exit_law.%s: i0 / direct class not among the classes' % link)
        out[link] = spec
        meta[link] = {'variant': v['variant'], 'law': row['law'], 'evidence_sha256': digest, 'dests': list(dests),
                      'shares': shares, 'l_km': lengths, 'direct': spec['direct']}
    net.wout_exit_law = out
    return {'k8b_p4': meta}


def install_sc1002w_saturation(cfg, tuning):
    """K8b-1 P-1 (K8_PREDECLARATION_AMENDMENT_16 r2 section 2.1, key urban.sc1002w_saturation): right after the
    measured movement capacity, the three SC1002 W internal movements take the U4 F2 saturation of their head groups
    (30|p3: 2 lanes, 30|p4: 1 lane, evidence k8b/sc1002w_saturation_v3c3_20261007.json) split by the template beta
    of this hook: C_E = 2 s_p3 b_E / (b_E + b_S), C_S = 2 s_p3 b_S / (b_E + b_S), C_N = s_p4.  It replaces the online
    measurement and the 206.53 constant of exactly these keys; every other movement keeps its bytes.  Key absent:
    {} and nothing is touched."""
    pin = ((tuning or {}).get('urban') or {}).get('sc1002w_saturation')
    if pin is None:
        return {}
    document, digest = load_k8b_evidence(pin, 'k8b-sc1002w-saturation/v1', 'urban.sc1002w_saturation')
    values = document['values']
    net = cfg.network
    caps = net.movement_capacity_by_movement_veh_h
    members = values['members']
    if set(members) != {'E', 'S', 'N'} or any(m not in net.urban_movements for m in members.values()):
        raise ValueError('urban.sc1002w_saturation members must be the three SC1002 W movements')
    s3, s4 = float(values['s_p3_veh_h_lane']), float(values['s_p4_veh_h_lane'])
    lanes3, lanes4 = float(values['lanes_p3']), float(values['lanes_p4'])
    beta = {d: float(net.urban_movements[m]['beta']) for d, m in members.items()}
    if not beta['E'] + beta['S'] > 0.0:
        raise ValueError('urban.sc1002w_saturation: beta_E + beta_S <= 0')
    before = {members[d]: caps.get(members[d]) for d in members}
    after = {members['E']: lanes3 * s3 * beta['E'] / (beta['E'] + beta['S']),
             members['S']: lanes3 * s3 * beta['S'] / (beta['E'] + beta['S']),
             members['N']: lanes4 * s4}
    for movement, capacity in after.items():
        caps[movement] = capacity
    return {'k8b_p1': {'before': before, 'after': after, 'beta': beta, 's_p3': s3, 's_p4': s4,
                       'evidence_sha256': digest}}


# ------------------------------------------------------------------------------------------- K9-1
# K8_PREDECLARATION_AMENDMENT_19 r2 sections 2.1-2.4 (sha 4ccfd8fd...): config keys only; every one absent = the
# K8b-5 (7e079efb) path.
def install_sc1001wout_saturation(cfg, tuning):
    """K9-1 W1 (section 2.1, key urban.sc1001_wout_saturation): right after the K8b-1 hook, the three SC1001 ->
    W_RAMP signal movements take C_m = s_g(m) x sum_{l in L(m)} b_m / sum_{m' in M(l)} b_m' (evidence values s, L(m),
    M(l); b = the template beta of this hook).  Only these three capacity keys change.  Key absent: {}."""
    pin = ((tuning or {}).get('urban') or {}).get('sc1001_wout_saturation')
    if pin is None:
        return {}
    document, digest = load_k8b_evidence(pin, 'k9-sc1001wout-saturation/v1', 'urban.sc1001_wout_saturation')
    v = document['values']
    net = cfg.network
    caps = net.movement_capacity_by_movement_veh_h
    members = v['members']
    if set(members) != {'E', 'N', 'S'} or any(m not in net.urban_movements for m in members.values()):
        raise ValueError('urban.sc1001_wout_saturation members must be the three SC1001 -> W_RAMP movements')
    beta, after, lanes = {}, {}, {}
    for key in ('E', 'N', 'S'):
        mv = members[key]
        s = float(v['s_veh_h_lane'][v['group_of'][key]])
        row = v['lanes'][key]
        total = 0.0
        for lane in row['lanes']:
            lane_key = '%s|%s' % (row['link'], lane)
            group = v['lane_members'][lane_key]
            if mv not in group or any(m not in net.urban_movements for m in group):
                raise ValueError('urban.sc1001_wout_saturation: lane %s members %s' % (lane_key, group))
            for m in group:
                beta[m] = float(net.urban_movements[m]['beta'])
            den = sum(beta[m] for m in group)
            if not den > 0.0:
                raise ValueError('urban.sc1001_wout_saturation: beta sum of lane %s <= 0' % lane_key)
            total += beta[mv] / den
        after[mv] = s * total
        lanes[mv] = ['%s|%s' % (row['link'], lane) for lane in row['lanes']]
    before = {mv: caps.get(mv) for mv in after}
    for mv, cap in after.items():
        caps[mv] = cap
    return {'k9_w1': {'before': before, 'after': after, 'beta': beta, 'lanes': lanes,
                      's': dict(v['s_veh_h_lane']), 'status': dict(v['status']), 'rule': v['rule'],
                      'evidence_sha256': digest}}


def install_wout_side_handoff(cfg, tuning):
    """K9-1 W2-A (section 2.2, key urban.wout_side_handoff): the SC1001_W_out exit law gains the class side (VISSIM
    side split, exit-law lengths l_side) and the SC2001 corridor hands its vehicles over at the merge (one branch
    wout_handover, sc2001_corridor.install_wout_handover).  Needs urban.sc2001_corridor and
    urban.wout_exit_law.SC1001_W_out (else ValueError).  Key absent: {}."""
    urban = (tuning or {}).get('urban') or {}
    pin = urban.get('wout_side_handoff')
    if pin is None:
        return {}
    if urban.get('sc2001_corridor') is None or not isinstance(urban.get('wout_exit_law'), dict) \
            or 'SC1001_W_out' not in urban['wout_exit_law']:
        raise ValueError('urban.wout_side_handoff needs urban.sc2001_corridor and urban.wout_exit_law.SC1001_W_out')
    document, digest = load_k8b_evidence(pin, 'k9-wout-side-handoff/v1', 'urban.wout_side_handoff')
    v = document['values']
    link = v['link']
    net = cfg.network
    spec = (getattr(net, 'wout_exit_law', None) or {}).get(link)
    if spec is None or getattr(net, 'sc2001_corridor', None) is None:
        raise ValueError('urban.wout_side_handoff: exit law of %s or the SC2001 corridor not installed' % link)
    if 'side' in spec['classes']:
        raise ValueError('urban.wout_side_handoff installed twice')
    from evaluation.controllers.urban_flow_accounting import WoutExitInvariantError
    ramp_of = v['ramp_of']
    if sorted(ramp_of.values()) != sorted(d for d in spec['dests'] if d != 'free'):
        raise ValueError('urban.wout_side_handoff: ramps %s differ from the exit law %s' % (ramp_of, spec['dests']))
    shares = {'free': float(v['shares']['free'])}
    lengths = {'free': float(v['l_km']['free'])}
    for name in ('R_D_E', 'R_D_W'):
        shares[ramp_of[name]] = float(v['shares'][name])
        lengths[ramp_of[name]] = float(v['l_km'][name])
    if abs(sum(shares.values()) - 1.0) > 1e-12 or any(x < 0.0 for x in shares.values()):
        raise WoutExitInvariantError('W_out exit law: side shares must be >= 0 and sum to 1 (+-1e-12)')
    if any(not x > 0.0 for x in lengths.values()):
        raise ValueError('urban.wout_side_handoff: side exit-law lengths must be > 0')
    spec['classes'] = tuple(spec['classes']) + ('side',)
    spec['s']['side'] = shares
    spec['l_km']['side'] = lengths
    spec['side_class'] = 'side'
    from evaluation.controllers import sc2001_corridor
    branch = sc2001_corridor.install_wout_handover(cfg, v)
    net.wout_side_handoff = {'link': link, 'evidence_sha256': digest}
    return {'k9_w2a': {'evidence_sha256': digest, 'link': link, 'shares': dict(shares), 'l_km': dict(lengths),
                       'x_side_m': v['x_side_m'], 'branch': branch}}


def install_freeway_runtime(adapter, cfg, tuning=None):
    """Restore hooks after their values were configured; also safe in spawn."""
    from src.controllers import wu_faithful_follower

    metadata = dict(adapter.install_freeway_vsl_zones(cfg, tuning))
    metadata.update(adapter.install_freeway_segment_runtime(cfg))
    if metadata.get("fw_vsl_zones_enabled"):
        from src.models import state as state_module
        # The legacy segment wrapper masks the inner zone marker. Preserve it
        # so repeated worker setup cannot remap a cell to its head twice and
        # then read the head's FD parameters as that cell's parameters.
        state_module.segment_vsl._rw_vsl_zone = True
    metadata.update(freeway_local_state.install(cfg, adapter._FW_SEG_CTX_STATE))
    metadata.update(link_predictor.install(cfg))
    metadata.update(install_freeway_fd_runtime(adapter, wu_faithful_follower, cfg, tuning))
    metadata.update(adapter.install_freeway_vsl_sequence_kbest(cfg, tuning))
    metadata.update(adapter.install_freeway_vsl_price_dedupe(cfg, tuning))
    return metadata


def configure_freeway_runtime(adapter, cfg, tuning, mapping, *, component_validation=False):
    # The calibrated VSL FD belongs to the coupled lane plant (CanonicalFreewayModel,
    # component_validation=True), whose kernels every SDMPC prediction steps. The
    # full follower/GNE/leader rollouts still use the legacy speed cap, so a full
    # controller tuning that asks for it is refused rather than silently mixed.
    # Only that component installs the cohort transport, so the key is refused
    # here too instead of being carried as a dead setting.
    freeway_model = tuning.get('freeway', {}) or {}
    if freeway_model.get('vsl_fd_response') and not component_validation:
        raise ValueError('Calibrated VSL FD response is component-only; local follower equivalence is not qualified')
    if 'component_vsl_transport' in freeway_model and not component_validation:
        raise ValueError('component_vsl_transport is component-only; only the lane-plant component installs it')
    metadata = dict(adapter.install_freeway_segment_lanes(cfg, tuning, mapping))
    freeway_settings = tuning.get("freeway", {}) or {}
    if "physical_vehicle_counts" in freeway_settings:
        flag = freeway_settings["physical_vehicle_counts"]
        if not isinstance(flag, bool):
            raise ValueError("freeway.physical_vehicle_counts must be a boolean")
        cfg.network.physical_vehicle_counts = flag
        metadata["freeway_physical_vehicle_counts"] = float(flag)
    metadata.update(adapter.install_freeway_lane_drop(cfg, tuning))
    metadata.update(adapter.install_freeway_two_branch_fd(cfg, tuning))
    metadata.update(configure_state_response(cfg, tuning))
    metadata.update(configure_literature_vsl(cfg, tuning))
    metadata.update(freeway_local_state.configure(cfg, tuning))
    metadata.update(link_predictor.configure(cfg, tuning))
    from evaluation.controllers import metanet_parameter_transfer
    metadata.update(metanet_parameter_transfer.configure(cfg, tuning, mapping))
    metadata.update(install_freeway_runtime(adapter, cfg, tuning))
    return metadata


def configure_runtime(adapter, cfg, tuning, mapping, state_json,
                      previous_action_path, detector_mapping, calibration,
                      TrafficState, physical_projection_input=None):
    """Configure and project with main()'s ordered model-installation sequence.

    cfg must already come from build_config with the caller's actual mode and
    controller. Input paths, calibration fingerprints, and forecast construction
    stay with the caller. The returned detector mapping includes movement merges.
    """
    timetable = (tuning or {}).get('prediction', {}).get('native_input_schedule', False)
    if not isinstance(timetable, bool):
        raise ValueError('prediction.native_input_schedule must be a boolean')
    if timetable and not (tuning or {}).get('urban', {}).get('native_internal_inputs'):
        raise ValueError('Native timetable requires the verified native_internal_inputs source contract')
    a = adapter
    lane_context=None
    lane_manifest=(tuning or {}).get('freeway',{}).get('lane_plant')
    spillback_projection=(tuning or {}).get('freeway',{}).get('lane_initial_spillback_projection',False)
    if type(spillback_projection) is not bool or (spillback_projection and lane_manifest is None):
        raise ValueError('freeway.lane_initial_spillback_projection requires a boolean and lane_plant')
    if lane_manifest is not None:
        if not isinstance(lane_manifest,str) or not lane_manifest:
            raise ValueError('freeway.lane_plant requires an explicit pinned manifest')
        from evaluation.controllers import lane_plant_runtime
        lane_context=lane_plant_runtime.load_sources(lane_manifest)
        lane_context['initial_spillback_projection']=spillback_projection
        if lane_context.get('plant_mode')=='v2':
            # coupled-lane-plant/v2 (obs150): the effective tuning must match
            # the manifest, and every consumer below reads the MERGED state.
            from evaluation.controllers.obs150_contract import validate_tuning_v2
            validate_tuning_v2(tuning,lane_context['document'])
        state_json,lane_observation=lane_plant_runtime.observe_state(lane_context,state_json)
        state_json=lane_plant_runtime.bind_current_routes(state_json,lane_observation)
    if (tuning or {}).get("freeway", {}).get("parameter_transfer"):
        from evaluation.controllers import metanet_parameter_transfer
        state_json = metanet_parameter_transfer.project_current(state_json, mapping)
    local_observation = bool(a._link_counts_from_local_observation(state_json)
                             and (detector_mapping or physical_projection_input is not None))
    metadata = dict(a.install_vissim_calibration_runtime_patches(cfg, calibration))
    metadata.update(a.install_tau_length_cap_patch(cfg))
    # Phase correction precedes beta pruning; measured beta needs a second prune.
    metadata.update(a.apply_movement_phase_correction(cfg, tuning))
    metadata.update(a.apply_nonexistent_movement_beta_zero(cfg, tuning))
    metadata.update(a.apply_dead_phase_beta_zero(cfg))
    metadata.update(a.install_vsl_metanet_rollout_runtime_patch(cfg, tuning))
    metadata.update(a.install_urban_stopline_storage(cfg, tuning))
    metadata.update(a.install_measured_turn_beta(cfg, tuning))
    metadata.update(a._relabel(a.apply_dead_phase_beta_zero(cfg, tuning=tuning), "after_measured_beta"))
    metadata.update(configure_freeway_runtime(a, cfg, tuning, mapping))
    metadata.update(a.install_leg_ramp_split_fold(cfg, tuning))
    detector_mapping, merged = a.install_merged_movements(cfg, tuning, detector_mapping)
    metadata.update(merged)
    if (tuning or {}).get('urban', {}).get('movements', {}).get('physical_phase_authority'):
        from evaluation.controllers.physical_movement_routes import configure_phase_authority
        metadata.update(configure_phase_authority(
            cfg, tuning, a.load_signal_group_actuation_plan(), state_json=state_json))
    metadata.update(a.install_unsignalized_turns(cfg, tuning, state_json))
    metadata.update(a.check_complete_beta_runtime(cfg, tuning, state_json))
    metadata.update(a.install_phase_vector_green_patch(cfg, tuning))
    metadata.update(a.install_movement_capacity_by_lanes(cfg, tuning))
    metadata.update(a.install_gate_onramp_queue(cfg, tuning))
    metadata.update(a.install_offramp_direct_landing(cfg, tuning))
    metadata.update(offramp_routing.install(cfg, tuning, state_json))
    metadata.update(a.install_offramp_landing_runtime(cfg))
    metadata.update(a.install_landing_storage(cfg, tuning))
    metadata.update(a.install_landing_storage_runtime(cfg))
    # Observed capacity already contains the native simultaneous-green effect.
    metadata.update(a.install_native_signal_structure(cfg, tuning))
    metadata.update(signal_actuation_contract.configure(cfg, tuning, a.load_signal_group_actuation_plan()))
    if getattr(cfg.network, 'native_signal_minimum_policy', None) == 'include_source_reference':
        metadata.update(a.validate_native_signal_runtime_source(cfg, state_json))
    from evaluation.controllers import head_service_resources
    from evaluation.controllers import signal_head_observation
    metadata.update(signal_head_observation.configure_head_free_service(cfg, tuning, state_json))
    metadata.update(head_service_resources.configure(
        cfg, tuning, state_json, a.load_signal_group_actuation_plan()))
    metadata.update(a.install_measured_movement_capacity(
        cfg, tuning, state_json, previous_action_path))
    metadata.update(install_sc1002w_saturation(cfg, tuning))     # K8b-1 P-1 (urban.sc1002w_saturation); {} absent
    metadata.update(install_sc1001wout_saturation(cfg, tuning))  # K9-1 W1 (urban.sc1001_wout_saturation); {} absent
    metadata.update(a.install_measured_far_reservoir_rates(
        cfg, tuning, state_json, previous_action_path))
    metadata.update(a.install_observed_backpressure_price(
        cfg, tuning, state_json, previous_action_path))
    metadata.update(a.install_far_ramp_capacity_patch(cfg))
    metadata.update(a.install_boundary_out_ramp_split(cfg, tuning))
    metadata.update(a.install_leg_ramp_split_runtime(cfg))
    detector_mapping, branch_metadata = observation_projection.install_physical_branch_projection(
        cfg, tuning, detector_mapping, link_counts=a._link_counts_from_local_observation(state_json))
    if branch_metadata.get("physical_branch_projection_enabled"):
        metadata.update(branch_metadata)
    branch_receiving = observation_projection.install_direct_branch_capacity_runtime(cfg)
    if branch_receiving.get("direct_branch_receiving_enabled"):
        metadata.update(branch_receiving)
    if (tuning or {}).get('urban', {}).get('movements', {}).get('physical_route_topology'):
        from evaluation.controllers import physical_movement_routes
        detector_mapping, topology_metadata = physical_movement_routes.configure_topology_repair(
            cfg, detector_mapping, tuning, state_json=state_json)
        metadata.update(topology_metadata)
    if 'dynamic_physical_route_topology' in (tuning or {}).get('urban', {}).get('movements', {}):
        from evaluation.controllers import area_dynamic_routes
        detector_mapping, dynamic_metadata = area_dynamic_routes.configure(
            cfg, detector_mapping, tuning, state_json=state_json)
        metadata.update(dynamic_metadata)
    if (tuning or {}).get('urban', {}).get('shared_approach'):
        from evaluation.controllers import shared_approach
        metadata.update(shared_approach.configure(cfg, tuning, state_json))
    if (tuning or {}).get('urban', {}).get('route_choice_corridor'):
        from evaluation.controllers import route_choice_corridor
        detector_mapping, choice_metadata = route_choice_corridor.configure(
            cfg, tuning, state_json, detector_mapping,
            per_lane_capacity_veh_h=metadata.get('movement_capacity_by_lanes_per_lane_veh_h'))
        metadata.update(choice_metadata)
        detector_mapping, state_json, choice_projection = route_choice_corridor.prepare_projection(
            cfg, detector_mapping, state_json)
        metadata.update(choice_projection)
    from evaluation.controllers import local_signal_service
    metadata.update(head_service_resources.finalize(cfg))
    metadata.update(local_signal_service.configure(cfg, tuning))
    if (tuning or {}).get('urban', {}).get('stopline_approach') is not None:
        # K8-6 SA hook #2: after the LSS/HSR pools are final, before any projection.
        from evaluation.controllers import stopline_approach
        metadata.update(stopline_approach.configure(cfg, tuning, state_json))
    if (tuning or {}).get('urban', {}).get('native_internal_inputs'):
        if tuning.get('urban', {}).get('movements', {}).get('native_input_signal_authority'):
            from evaluation.controllers.physical_movement_routes import configure_native_input_signal_authority
            detector_mapping, authority_metadata = configure_native_input_signal_authority(
                cfg, tuning, detector_mapping, state_json=state_json)
            metadata.update(authority_metadata)
        from evaluation.controllers import native_internal_input
        metadata.update(native_internal_input.configure(cfg, tuning, state_json, detector_mapping))
        detector_mapping, state_json, native_projection = native_internal_input.prepare_projection(
            cfg, detector_mapping, state_json)
        metadata.update(native_projection)
    if (tuning or {}).get('observation', {}).get('physical_support_repair'):
        from evaluation.controllers import projection_support
        detector_mapping, state_json, support_metadata = projection_support.configure(cfg, tuning, detector_mapping, state_json)
        metadata.update(support_metadata)
    if (tuning or {}).get('urban', {}).get('sc2001_corridor'):
        from evaluation.controllers import sc2001_corridor
        metadata.update(sc2001_corridor.configure(cfg, tuning, state_json))
        detector_mapping, state_json, corridor_projection = sc2001_corridor.prepare_projection(
            cfg, detector_mapping, state_json)
        metadata.update(corridor_projection)
    from evaluation.controllers import physical_ramp_branches
    detector_mapping, physical_ramp_metadata = physical_ramp_branches.configure(
        cfg, tuning, mapping, detector_mapping, state_json)
    metadata.update(physical_ramp_metadata)
    metadata.update(install_wout_exit_law(cfg, tuning))     # K8b-2 P-4' / P-4b (urban.wout_exit_law); {} absent
    metadata.update(install_wout_side_handoff(cfg, tuning))         # K9-1 W2-A (urban.wout_side_handoff); {} absent
    if lane_context is None:
        metadata.update(offramp_routing.configure_inventory(cfg, tuning, state_json, mapping))
    state = a.traffic_state_from_vissim(
        state_json, cfg, TrafficState, detector_mapping, calibration,
        physical_projection_input=physical_projection_input)
    if lane_context is None:
        metadata.update(offramp_routing.initialize_inventory(state, cfg, state_json))
    metadata.update(a.install_monitor_fixed_signal_runtime_patch(
        cfg, state_json, detector_mapping) or {})
    if local_observation:
        a.install_local_observation_runtime_guards()
    if 'conservative_initial_transit' in (tuning or {}).get('urban', {}):
        from evaluation.controllers import area_runtime
        metadata.update(area_runtime.configure_initial_transit(cfg, tuning, state))
    if getattr(cfg.network, 'shared_approach', None):
        from evaluation.controllers import shared_approach
        metadata.update(shared_approach.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(shared_approach.install(a, cfg))
    if getattr(cfg.network, 'sc2001_corridor', None):
        from evaluation.controllers import sc2001_corridor, urban_flow_accounting
        metadata.update(sc2001_corridor.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(urban_flow_accounting.install(a, cfg))
    if getattr(cfg.network, 'route_choice_corridor', None):
        from evaluation.controllers import route_choice_corridor, urban_flow_accounting
        metadata.update(route_choice_corridor.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(urban_flow_accounting.install(a, cfg))
    if getattr(cfg.network, 'native_internal_inputs', None):
        from evaluation.controllers import native_internal_input, native_input_routes, native_input_prehead, urban_flow_accounting
        metadata.update(native_internal_input.initialize(state, cfg, state_json, detector_mapping))
        metadata.update(native_input_routes.initialize(state, cfg, state_json))
        metadata.update(native_input_prehead.initialize(state, cfg, state_json))
        metadata.update(urban_flow_accounting.install(a, cfg))
    from evaluation.controllers import metanet_parameter_transfer
    metadata.update(metanet_parameter_transfer.configure_demand(cfg, mapping))
    if lane_context is not None:
        if lane_context.get('plant_mode')=='v2':
            # V-9 (repin plan 2026-10-01 K5): the tuning's VSL command map, the plant law (speed_scale) and
            # the runner allow-list are one family; the pinned reference and runner of this manifest.
            from evaluation.controllers import vsl_command_distribution
            vsl_command_distribution.check_family_files(tuning,lane_context['paths']['reference_config'],
                                                        lane_context['paths']['runner_config'])
        from evaluation.controllers import offramp_split_forecast   # K9-1 F17b (freeway.offramp_split_forecast)
        metadata.update(offramp_split_forecast.install(cfg, tuning, state_json, lane_observation))
        metadata.update(lane_plant_runtime.initialize(lane_context,lane_observation,cfg,state,detector_mapping,
                                                      previous_action_path=previous_action_path))
        if (tuning or {}).get('urban', {}).get('stopline_approach') is not None:
            # K8-6 SA hook #3: lane FIFO index over the projected stocks, before the area ledger seeds.
            from evaluation.controllers import stopline_approach
            # K8b-3 P-2 (urban.stopline_approach.city_arrival): gate beta / d_g before, initial W timing after; {} absent
            metadata.update(stopline_approach.city_arrival_prepare(state, cfg, state_json))
            metadata.update(stopline_approach.initialize(state, cfg, state_json, detector_mapping,
                                                         stopline_approach.seed_split_of(state), tuning=tuning))
            metadata.update(stopline_approach.city_arrival_initialize(state, cfg, state_json,
                                                                      stopline_approach.seed_split_of(state)))
    if (tuning or {}).get('control_area_objective', {}).get('enabled', False):
        from evaluation.controllers import area_runtime
        metadata.update(area_runtime.configure(a, cfg, tuning, state, detector_mapping))
        from evaluation.controllers import area_meter_finalization
        metadata.update(area_meter_finalization.configure(
            a, cfg, tuning, mapping, state_json, previous_action_path, state, calibration))
    from evaluation.controllers.route_choice_corridor import configure_known_legsplit
    metadata.update(configure_known_legsplit(cfg, tuning, state, state_json))
    if lane_context is not None:
        lane_plant_runtime.bind_area(state,cfg)
    return state, detector_mapping, metadata


def install_worker_runtime(adapter, cfg, state_json, detector_mapping):
    """Reinstall the existing worker hooks plus the shared freeway hooks."""
    a = adapter
    signal_actuation_contract.install_candidates(cfg)
    from evaluation.controllers import local_signal_service
    pool_metadata = local_signal_service.install(cfg)
    metadata = dict(a.install_monitor_fixed_signal_runtime_patch(
        cfg, state_json, detector_mapping) or {})
    metadata.update(pool_metadata)
    metadata.update(a.install_tau_length_cap_patch(cfg))
    metadata.update(a.install_far_ramp_capacity_patch(cfg))
    metadata.update(a.install_leg_ramp_split_runtime(cfg))
    metadata.update(a.install_offramp_landing_runtime(cfg))
    branch_receiving = observation_projection.install_direct_branch_capacity_runtime(cfg)
    if branch_receiving.get("direct_branch_receiving_enabled"):
        metadata.update(branch_receiving)
    metadata.update(a.install_landing_storage_runtime(cfg))
    metadata.update(install_freeway_runtime(a, cfg, None))
    if getattr(cfg.network, 'shared_approach', None):
        from evaluation.controllers import shared_approach
        metadata.update(shared_approach.install(a, cfg))
    if (getattr(cfg.network, 'sc2001_corridor', None)
            or getattr(cfg.network, 'route_choice_corridor', None)
            or getattr(cfg.network, 'native_internal_inputs', None)):
        from evaluation.controllers import urban_flow_accounting
        metadata.update(urban_flow_accounting.install(a, cfg))
    if getattr(cfg.network, 'control_area_enabled', False):
        from evaluation.controllers import area_runtime
        metadata.update(area_runtime.install(a, cfg))
    if getattr(cfg.network, "far_ramp_capacity_veh_h", None):
        import src.controllers.stackelberg_mpc as stackelberg_mpc
        if not getattr(stackelberg_mpc, "_rw_far_ramp_capacity_active", False):
            raise RuntimeError("price worker failed to restore measured far ramp capacity")
    return metadata
