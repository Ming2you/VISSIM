"""make_config_n31.RAMP_FORECAST from the runtime network's no-control runs (v3c1 fit seeds s31, s41, s43, s47, s53).

The adapter's local_ramp_arrival_forecast turns connector occupancy into arrivals as
count * 3600 / drain_sec, clipped at max_vph (vissim_stackelberg_adapter.py:9373-9412). Per physical
meter RM_C<connector>, from boundaries_30s.csv (FZP-derived, one row per 30 s window and boundary):
  q         merges into the freeway per hour ('crossings'), 900-5400 s
  N         vehicles on the connector at each 30 s FZP frame ('snapshot_n_veh'); this is the adapter's
            channel local_observation.link_counts[connector] (V5b state_T link_counts equal the V5b FZP
            count at T+0.1 s on all eight connectors at T = 2700 and 3300, and on seven at T = 3000)
  drain_sec mean(N) * 3600 / mean(q), five seeds pooled (Little's law; the 2026-08-30 script used the
            median occupancy, which is 0-8 s for the sparse 10480)
  max_vph   1.15 * max over seeds of q (the 2026-08-30 cap rule, scripts/calibrate_ramp_arrival_20260830.py)

Inputs: extract_observations.py over the network v3c1 no-control runs of the fit seeds
D:/VISSIM_runs/20260927_v3c1/s{31,41,43,47,53}_v3c1nc (networks 2577209b / 226baa37 / b8e7cf1f / ec0cd81d / 385f40da,
native_preserve, 9000 s, FZP 5 s, phase 0.1 s; the held-out seed 37 is never read), written to
metanet_calibration_v1/v3c1_nc_20260928/observations (receipts s{seed}_v3c1nc_extraction_receipt.json beside it);
their sha256 are pinned here. The network is the current runtime network (user approval 2026-09-28: v3c1 = v3b
be0075bf + the eight routing decisions 1160, 1162-1168). 2026-09-25..28 the inputs were the v3b NC s31/s41/s37
extractions (metanet_calibration_v1/v3b_nc_20260925, boundaries_30s.csv 8deebef9 / 5509f969 / 956f3a8d), which gave
drain 17.4/43.3/30.9/88.0/42.6/161.7/33.3/43.3 s and cap 219/2312/405/514/526/1216/839/611 veh/h. Until 2026-09-25
the inputs were
the v2 (f475ce42) stage-1 no-control runs, control_response_v2/inputs/b110_observations/s{seed}_v2nc_observations
(boundaries_30s.csv dfe33cf8 / f362f8ef / f7c6b612), which gave drain 16.6/43.4/30.2/88.0/42.9/160.7/34.6/47.7 s and
cap 277/2310/413/514/526/1217/819/686 veh/h (RM_C10480/10482/10646/10644/10639/10681/10490/10484).
A network change re-runs its no-control seeds, re-extracts them, re-points OBS/PATTERN/INPUTS and re-derives;
copy the result into make_config_n31.RAMP_FORECAST.
python -B diagnostics/sdmpc_n31_20260924/derive_ramp_forecast_n31.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OBS = ROOT / 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c1_nc_20260928/observations'
PATTERN = 's{seed}_v3c1nc_observations'
INPUTS = {   # boundaries_30s.csv sha256 per seed (v3c1 NC fit seeds; s37 held out)
    31: 'ab52fe80e0a2af481f720c353b0a3c1aff6a9f834753d9a94d3a057abe542294',
    41: 'ec2c977945b0e41e16380b797ac3bf31fe67555edd59fbfb29a445110a0bc315',
    43: 'f67e2508c71e7730e76806b3cf82bd56ff7c7071ff155c8abc6d9abce5df5fc1',
    47: '9365a93dfe4aa5dcfd3e0dcc96472a048bf2a1e7e9118e00a383c4e3620cdf46',
    53: '50dd5e9d377ae7823d84d6eb817894b91696970d50c04fa205d98910b34738da',
}
METERS = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
T0, T1 = 900.0, 5400.0


def windows(seed):
    path = OBS / PATTERN.format(seed=seed) / 'boundaries_30s.csv'
    if hashlib.sha256(path.read_bytes()).hexdigest() != INPUTS[seed]:
        raise ValueError('NC observation differs from its pin: ' + str(path))
    rows = {m: [] for m in METERS}
    with open(path, encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            if row['id'] in rows and T0 < float(row['window_end_s']) <= T1:
                rows[row['id']].append((float(row['crossings']), float(row['snapshot_n_veh'] or 0)))
    return rows


def derive():
    per_seed = {seed: windows(seed) for seed in INPUTS}
    drain, cap = {}, {}
    for m in METERS:
        q = [sum(c for c, _ in per_seed[s][m]) * 120.0 / len(per_seed[s][m]) for s in INPUTS]
        n = [st.mean(k for _, k in per_seed[s][m]) for s in INPUTS]
        drain[m] = round(st.mean(n) * 3600.0 / st.mean(q), 1)
        cap[m] = float(round(1.15 * max(q)))
    return {'queue_drain_horizon_sec_by_ramp': drain, 'max_vph_by_ramp': cap}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    values = derive()
    for key, table in values.items():
        print(key, table)
    if args.check:
        sys.path.insert(0, str(HERE))
        import make_config_n31
        if values != make_config_n31.RAMP_FORECAST:
            raise SystemExit('make_config_n31.RAMP_FORECAST differs from the derivation')
        print('RAMP_FORECAST_OK')


if __name__ == '__main__':
    main()
