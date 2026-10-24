"""Bind the fixed331 network to controller caches before any optimization."""
from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
from src.models.urban_queue_model import movement_specs
from src.controllers.local_signal_plant import build_local_model
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal


def refresh(follower, cfg):
    assert follower.cfg is cfg and follower._wu.cfg is cfg
    before = follower._specs
    invalidate_topology_cache(cfg.network)
    specs = movement_specs(cfg)
    assert set(before) == set(specs)
    changed = [m for m in specs if not equal(before[m], specs[m])]
    for m in changed:
        assert set(before[m]) == set(specs[m])
        assert all(equal(v, specs[m][k]) for k, v in before[m].items() if k != 'beta')
    follower._specs = follower._wu._specs = specs
    # Topology and phase membership are unchanged; coupling maps cache beta.
    last = follower._wu._last_offramp_flow
    has_last = follower._wu._has_last_offramp_flow
    follower._wu._build_coupling_maps()
    follower._wu._last_offramp_flow = last
    follower._wu._has_last_offramp_flow = has_last
    rebuilt = {}
    for owner, old in follower._local_models.items():
        model = build_local_model(cfg, owner, specs, follower._phase_movements)
        assert model.movements == old.movements
        if not equal(old, model): rebuilt[owner] = True
        follower._local_models[owner] = model
    assert equal(follower._specs, cfg.network.urban_movements)
    return dict(changed_specs=changed, rebuilt_local_models=list(rebuilt),
                movement_and_control_axes_unchanged=True,
                existing_cache_invalidator=True)
