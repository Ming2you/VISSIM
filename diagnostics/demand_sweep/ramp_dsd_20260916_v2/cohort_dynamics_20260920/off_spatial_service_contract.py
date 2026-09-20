"""Reject a spatial prototype that counts observed outlet headway twice.

This is an isolated saturated-queue interface test, not a VISSIM calibration.
No traffic coefficients, historical predictions, or production code are changed.
"""
from pathlib import Path
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_spatial_transport import SpatialLane, e, ch

HERE = Path(__file__).resolve().parent


def main():
    output = HERE / 'off_spatial_service_contract_v1.json'
    if output.exists():
        raise FileExistsError(output)
    vehicles = [(900 - 6 * i, 0, 4.5) for i in range(150)]
    rows = []
    for service in (360, 900, 1800):
        for mode in ('existing_delayed_port', 'gap_relaxation', 'delayed_rear_history'):
            if mode == 'existing_delayed_port':
                port = ch.DelayedPort(150, 900, 60, [(p, v, 1) for p, v, _ in vehicles], 0, interval_service=True)
            else:
                port = SpatialLane(150, 900, 60, vehicles, 0, 2, 1.5,
                                   delayed=mode == 'delayed_rear_history')
            counts = {}
            for t in range(240):
                port.release(t, 1, service)
                if t + 1 in (60, 180, 240):
                    counts[t + 1] = port.departed
            rate = (counts[180] - counts[60]) * 3600 / 120
            assert abs(port.stock - 150 + port.departed) < 1e-7
            rows.append(dict(mode=mode,service_vph=service,counts=counts,
                             realized_vph_60_to_180=rate,
                             relative_shortfall=1-rate/service,
                             observed_service_preserved=abs(rate/service-1) < .01))
    reference = [r for r in rows if r['mode'] == 'existing_delayed_port']
    assert all(r['observed_service_preserved'] for r in reference)
    assert not any(r['observed_service_preserved'] for r in rows if r not in reference)
    files = [Path(__file__), HERE/'off_spatial_transport.py', e.CAL/'canonical_harness.py']
    e.save(output, dict(status='SPATIAL_SERVICE_INTERFACE_REJECTED', rows=rows,
        setup=dict(initial_vehicles=150,length_m=900,spacing_m=6,free_speed_kmh=60,
                   prototype_response_scale_s=2,warmup_s=60,evaluation_s=[60,180]),
        interpretation='The supplied observed drainage already includes discharge headway. Fractional service depletion followed by packet catch-up introduces another serial delay. This test rejects that composition, not finite spatial propagation itself.',
        scope='Synthetic interface test; does not estimate native saturation capacity or explain every lane1 error.',
        source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        qualified=False,production_adopted=False,new_native_runs=0))
    for row in rows:
        print(row['mode'], row['service_vph'], round(row['realized_vph_60_to_180'], 6), flush=True)


if __name__ == '__main__':
    main()
