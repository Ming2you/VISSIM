"""Apply the frozen331 diagnostic model to current seed29 state4650 observations.

All service/split supports remain from training seed29. Only state assimilation
uses seed29 state4650 at4650. This is transfer validation, not fitting to the held-out arm.
"""
import hashlib
import json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331 import inputs, gate_coverage

HERE = Path(__file__).resolve().parent
A = HERE.parent
H = A.parent
ROOT = HERE.parents[4]


def apply_service_floor(cfg, at, evidence):
    """Transfer305's calibrated lower bound without lowering an observed floor."""
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305 import candidate as phase
    rate = phase.rate_from_support(evidence, at)
    net = cfg.network
    group = net.regular_alias_pool['groups'][phase.west.GROUP]
    if (set(group['members']) != set(phase.west.MEMBERS) or group['signal'] != 'SC12'
            or group['phase'] != 'SC12_p4' or group['receiver'] != 'SC12_to_SC6'):
        raise ValueError('Physical service binding changed')
    previous = group['service_veh_h']
    if previous <= 0 or any(net.movement_capacity_by_movement_veh_h[k] != previous
                            for k in phase.west.MEMBERS):
        raise ValueError('Shared service members disagree with the physical pool')
    selected = max(previous, rate)
    pool = deepcopy(net.regular_alias_pool)
    pool['groups'][phase.west.GROUP]['service_veh_h'] = selected
    caps = dict(net.movement_capacity_by_movement_veh_h)
    for key in phase.west.MEMBERS:
        caps[key] = selected
    net.regular_alias_pool = pool
    net.movement_capacity_by_movement_veh_h = caps
    net.sc12_phase305 = dict(previous_rate=previous, rate=selected,
        shared_members=list(phase.west.MEMBERS), support_starts=evidence['selected_support']['starts'],
        cutoff=2400, training_floor=rate, retained_higher_current_floor=previous > rate,
        scope='One shared physical head budget; frozen training lower bound, no seed29 state4650 fit.')
    return net.sc12_phase305


@contextmanager
def frozen_services():
    """Use the already fitted2400 service table without changing current time.

    combined298.prepare is stateless; its only time argument selects the
    supported diagnostic timestamp. Geometry/prior/service proofs still run.
    Current observations, native histories and all state projectors keep4650.
    """
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.combined298 import candidate
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305 import candidate as phase
    original = candidate.prepare
    original_phase = phase.install

    def prepare(cfg, at):
        if at != 4650:
            raise ValueError('This transfer wrapper is restricted to rm10681_transfer346')
        caps, groups, metadata = original(cfg, 2400)
        for record in metadata.values():
            assert record['cutoff_sec'] == 2400
            record['validation_at_sec'] = at
            record['support_origin'] = 'training seed29 frozen2400'
        return caps, groups, metadata

    candidate.prepare = prepare
    phase.install = apply_service_floor
    try:
        yield
    finally:
        candidate.prepare = original
        phase.install = original_phase


def apply(cfg, state, source, save, pins, adapter):
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import validate_turns
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306 import candidate as initial306
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc101_recombined import candidate as service304
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_composite308 import candidate as service308
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_side310 import candidate as service310
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_geometry311 import candidate as geometry311
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc107_shared316 import candidate as shared316
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317 import candidate as transport317
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320 import candidate as timing320
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321 import candidate as routes321
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc16_aggregate323 import candidate as aggregate323
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as gate325
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329 import candidate as routes329
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.selection336.binding import refresh

    at = int(state.time_sec)
    assert at == 4650
    raw, frame, current_pins = inputs.load(source, at)
    pins.update(current_pins)
    network_path = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    network = network_path.read_bytes()
    protocol_path = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/native_rm10681_reopen4650_238/protocol.json'
    protocol = json.loads(protocol_path.read_bytes())
    assert protocol['seed'] == 29
    assert hashlib.sha256(network).hexdigest() == protocol['network_sha256']
    pins[str(network_path)] = protocol['network_sha256']
    sides, membership = routes321.membership()
    pins[str(membership)] = hashlib.sha256(membership.read_bytes()).hexdigest()
    lanes = adapter._contiguous_stopline_queue(raw, per_lane=True)

    def mass():
        return {k: sum(v[k] for v in get_ledger(state).stocks.values()) for k in ('inside','outside')}

    initial = mass()
    receipts = {}

    def record(name, receipt):
        receipts[name] = receipt
        get_ledger(state).assert_stocks(model_inventory(state, cfg))
        assert all(abs(mass()[k]-v)<1e-7 for k,v in initial.items()), name
        save('installations.json', dict(at_sec=at, training_seed=29, validation_seed=29,
             fitted_to_validation=False, initial_mass=initial, current_mass=mass(), steps=receipts))

    # This stateless installer is restricted to its original diagnostic timestamps.
    # Reuse the frozen2400 calibration explicitly; do not present it as seed29 state4650 data.
    record('service304', dict(service304.install(cfg,2400), validation_at_sec=at,
                             support_origin='training seed29 frozen2400'))
    validate_turns(cfg.network)
    state, receipt = initial306.project(state,cfg,raw,frame,network,sides[initial306.LINK],lanes)
    record('initial306',receipt)
    record('service308', dict(service308.install(cfg,2400), validation_at_sec=at,
                             support_origin='training seed29 frozen2400'))
    record('service310',service310.install(cfg,at))
    record('geometry311',geometry311.install(cfg,state))
    receipt=shared316.install(cfg)
    receipt['owner_binding']=shared316.refresh_local(adapter._PHASE_VECTOR_FOLLOWER['ref'],cfg)
    record('shared316',receipt)
    record('transport317',transport317.install(cfg,state))
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339.project import install as project339
    state,receipt=project339(cfg,state,raw,frame,network,lanes)
    record('corridor339',receipt)
    state,receipt=aggregate323.install(cfg,state,raw,frame,network,lanes)
    record('aggregate323',receipt)
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.corridor339 import gate_coverage as coverage339
    with coverage339.enabled(cfg,network) as coverage:
        state,receipt=gate325.install(cfg,state,raw,frame,network,lanes)
    record('gate325',dict(receipt,physical_coverage=coverage))
    record('routes329',routes329.install(cfg,network))
    record('binding336',refresh(adapter._PHASE_VECTOR_FOLLOWER['ref'],cfg))
    return state
