"""Compose independently supported past head services for offline diagnosis."""
from contextlib import contextmanager
from copy import deepcopy
from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc12w_service import candidate as west
from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc16_supply import candidate as east


def prepare(cfg, at):
    # Each component verifies its own unmodified parent and physical bindings.
    # Build independent copies, then commit disjoint verified changes together.
    parent = cfg.network
    groups = deepcopy(parent.regular_alias_pool['groups'])
    caps = dict(parent.movement_capacity_by_movement_veh_h)
    changed = set()
    metadata = {}
    for name, component in (('SC12W', west), ('SC16E', east)):
        isolated = deepcopy(cfg)
        result = component.install(isolated, at)
        net = isolated.network
        new = set(net.regular_alias_pool['groups']) - set(parent.regular_alias_pool['groups'])
        assert new == {component.GROUP}
        keys = {k for k in caps if net.movement_capacity_by_movement_veh_h[k]
                != parent.movement_capacity_by_movement_veh_h[k]}
        if keys != set(component.MEMBERS) or keys & changed or new & set(groups):
            raise ValueError('Candidate components overlap or alter unqualified members')
        assert net.urban_movements == parent.urban_movements
        assert net.urban_link_storage_veh == parent.urban_link_storage_veh
        caps.update({k: net.movement_capacity_by_movement_veh_h[k] for k in keys})
        groups.update({k: deepcopy(net.regular_alias_pool['groups'][k]) for k in new})
        metadata[name] = result
        changed |= keys
    return caps, groups, metadata


def install(cfg, at):
    caps, groups, metadata = prepare(cfg, at)
    cfg.network.movement_capacity_by_movement_veh_h = caps
    pool = deepcopy(cfg.network.regular_alias_pool)
    pool['groups'] = groups
    cfg.network.regular_alias_pool = pool
    cfg.network.combined298_service = metadata
    return metadata


def validate_turns(net):
    west.validate_turns(net)
    east.validate_turns(net)


@contextmanager
def hook():
    from evaluation.controllers import regular_alias_service
    original = regular_alias_service.configure
    def configure(cfg, tuning, raw):
        base = original(cfg, tuning, raw)
        metadata = install(cfg, int(raw['sim_sec']))
        return {**base, 'diagnostic_combined298_service': metadata}
    regular_alias_service.configure = configure
    try:
        yield
    finally:
        regular_alias_service.configure = original
