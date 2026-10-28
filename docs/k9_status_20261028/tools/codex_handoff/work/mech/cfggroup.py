import csv, os, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, 'cfg_leaf_diff.csv'), encoding='utf-8')))
RULES = [
    ('meta', ('/name', '/description', '/_n31_note', '/_area_revision', '/_repin', '/_canonical')),
    ('meter_decision', ('/adapter/joint_owner_game/max_leader_candidates', '/adapter/sdmpc_meter_neighbor_audit',
                        '/adapter/sdmpc_response_cap_cache', '/actuation/real_world_ramp_metering')),
    ('vsl', ('/adapter/sdmpc_vsl_activation_secant', '/config_overrides/freeway_follower/vsl_set', '/freeway/vsl_zone',
             '/actuation/vsl_command_distribution', '/freeway/physical_vsl_sign_binding', '/freeway/observed_vsl_history')),
    ('ramp_plant', ('/freeway/physical_ramp_', '/freeway/ramp_reference_contract', '/urban/single_lane_causal_receiving')),
    ('freeway_plant', ('/freeway/lane_plant', '/freeway/segment_params', '/config_overrides/network/v_free',
                       '/freeway/multirate_exchange_sec', '/freeway/offramp_route_inventory', '/freeway/offramp_split_forecast')),
    ('ramp_arrival_forecast', ('/calibration_override/prediction',)),
    ('omega_area', ('/control_area_objective',)),
    ('network_pin_and_pack_paths', ('/observation', '/execution', '/urban/capacity/head_free_service',
                                    '/urban/capacity/head_resource_contract', '/urban/movements', '/urban/native_internal_inputs',
                                    '/urban/physical_ramp_branches', '/urban/route_choice_corridor', '/urban/sc2001_corridor',
                                    '/urban/shared_approach', '/urban/known_wout_route_evidence')),
    ('codex_urban_model', ('/urban/known_wout_', '/urban/storage_release_guard', '/urban/calibrated_aggregate',
                           '/urban/capacity/regular_alias_pool', '/urban/queue', '/urban/arrival', '/urban/ramp/initial_gate_city_lock',
                           '/urban/ramp/native_gate_travel', '/urban/ramp/gate_entry_capacity_per_lane_veh_h',
                           '/urban/sc1001_', '/urban/shared_sc1001_approach', '/urban/multirate_exchange_sec',
                           '/urban/route_corridor_aggregate_step_sec', '/urban/preserve_direct_offramp_destinations',
                           '/config_overrides/network/urban_movements')),
    ('ours_urban_fixes', ('/urban/stopline_approach', '/urban/wout_exit_law', '/urban/sc1002w_saturation',
                          '/urban/sc109w_through_saturation', '/urban/wout_side_handoff', '/urban/capacity/head_floor_seed',
                          '/urban/ramp/offramp_direct_share', '/urban/beta')),
    ('runtime', ('/runtime',)),
]
groups = collections.defaultdict(lambda: collections.Counter())
unassigned = []
for r in rows:
    p = r['pointer']
    for name, prefixes in RULES:
        if any(p.startswith(x) for x in prefixes):
            groups[name][r['kind']] += 1
            break
    else:
        unassigned.append((r['kind'], p))
total = collections.Counter()
for name, _ in RULES:
    c = groups[name]
    total.update(c)
    print(f"{name:28s} only_codex={c['only_codex']:3d} only_ours={c['only_ours']:3d} diff={c['diff']:3d} sum={sum(c.values())}")
print('TOTAL', dict(total), sum(total.values()))
print('UNASSIGNED', unassigned)
