"""Independent narrow review probes for the unapplied shared-service patch.

No endpoint, optimizer, source mutation, or VISSIM. The proposal is loaded with
its author's isolated in-memory harness; only input/cache boundary cases differ.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from diagnostics.test_shared_service_pool import (
    ROOT, PATCH, TARGETS, proposed, inputs, local_args, accepted_trace, local,
    LinkAgentWuFollower, uqm,
)


def run():
    watched = [PATCH, ROOT / 'diagnostics/test_shared_service_pool.py',
               ROOT / 'evaluation/controllers/route_choice_corridor.py',
               ROOT / 'evaluation/controllers/runtime_setup.py',
               ROOT / 'vendor/NumSim-mine/src/controllers/local_signal_plant.py',
               ROOT / 'vendor/NumSim-mine/src/controllers/priced_wu_link_controller.py']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    output = {'scope': 'isolated proposal; one urban step only; no endpoint or optimizer',
              'source_sha256': hashes}
    with proposed() as (pool, route, runtime):
        cfg, state, action, demand, model, raw, detectors = inputs()
        args, kw = local_args(cfg, state, action, model)
        original = local.rollout_local_tts_ramp_aware(*args, **kw)
        pool.configure(cfg, {'urban': {'shared_local_service_pool': True}})
        enabled, receipts = accepted_trace(pool, lambda: local.rollout_local_tts_ramp_aware(*args, **kw))
        output['baseline'] = {'original_cost': original, 'enabled_cost': enabled,
                              'enabled_receipts': receipts}

        # All keys absent passes None-only validation and silently uses green/cycle.
        empty = dict(kw, gf_by_substep={})
        empty_cost, empty_receipts = accepted_trace(pool, lambda: local.rollout_local_tts_ramp_aware(*args, **empty))
        output['empty_physical_profiles'] = {
            'accepted_without_error': True, 'cost': empty_cost,
            'receipts': empty_receipts, 'actual_target_fractions': {m: kw['gf_by_substep'][m] for m in TARGETS},
            'fallback_fraction': args[10]['p3'] / cfg.network.cycle_length,
        }

        # Same timestamp/control/demand is not the same stock or coupling context.
        agent = LinkAgentWuFollower(cfg)
        agent.phase_price_local_cost_model = 'phased'
        context1 = agent._phase_refine_context(state, action, demand)
        setup1 = agent._phase_refine_signal_setup('SC1004', state, context1)
        changed = state.copy()
        off = 'OR_F_W'
        storage = cfg.network.off_ramp_storage_link[off]
        changed.urban_link_storage[storage] += 1.0  # One fewer observed vehicle.
        context2 = agent._phase_refine_context(changed, action, demand)
        setup2 = agent._phase_refine_signal_setup('SC1004', changed, context2)
        fresh = LinkAgentWuFollower(cfg)
        fresh.phase_price_local_cost_model = 'phased'
        fresh_context = fresh._phase_refine_context(changed, action, demand)
        fresh_setup = fresh._phase_refine_signal_setup('SC1004', changed, fresh_context)
        output['same_time_changed_stock'] = {
            'cached_context_reused': context2 is context1,
            'cached_setup_reused': setup2 is setup1,
            'original_off_stock': setup1['off_occ'][off],
            'cached_off_stock': setup2['off_occ'][off],
            'actual_changed_off_stock': fresh_setup['off_occ'][off],
        }

        # Existing local plant availability approximation: occupancy includes
        # immature ramp transit, whereas global service excludes it. This is
        # not introduced by the pool and must not be called newly equivalent.
        from evaluation.controllers import urban_flow_accounting as urban
        from evaluation.controllers import native_input_routes, native_input_prehead
        transit = state.copy()
        transit._control_area_ledger = None
        step = uqm._urban_step_index(transit, cfg)
        transit.offramp_transit_buffer.setdefault(storage, {})[step + 1] = setup1['off_occ'][off]
        transit.route_choice_corridor_state['last_step'] = step
        transit.route_choice_corridor_state['service_limit_veh'] = {}
        transit.route_choice_corridor_state['service_used_veh'] = {}
        native_input_routes.advance(transit, cfg, step)
        native_input_prehead.advance(transit, cfg, step)
        transit_args, transit_kw = local_args(cfg, transit, action, model)
        _, local_transit = accepted_trace(pool, lambda: local.rollout_local_tts_ramp_aware(*transit_args, **transit_kw))
        _, global_transit = accepted_trace(pool, lambda: urban._drain_offramp_storage_accounted(
            transit, action, cfg, {m: model.specs[m] for m in TARGETS}, step, {}))
        output['inherited_immature_transit_scope'] = {
            'synthetic_pending_veh': setup1['off_occ'][off], 'due_step': step + 1,
            'local_receipts': local_transit, 'global_receipts': global_transit,
            'classification': 'inherited availability approximation, not a new pool arithmetic error',
        }

        # The explicit public OFF configuration does not remove the ON view.
        result = pool.configure(cfg, {'urban': {'shared_local_service_pool': False}})
        after = local.rollout_local_tts_ramp_aware(*args, **kw)
        output['on_then_explicit_off_same_cfg'] = {
            'configure_metadata': result, 'view_remains_enabled': bool(pool.view(cfg)),
            'cost_after_off': after, 'exact_original': after == original,
        }
    output['source_changes'] = [str(p.relative_to(ROOT)) for p in watched
                                if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]]
    assert not output['source_changes']
    return output


if __name__ == '__main__':
    result = run()
    path = ROOT / 'diagnostics/review_shared_service_pool_edges.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, ensure_ascii=False, indent=2))
