"""make_config_n31.RAMP_FORECAST from the runtime network's no-control runs (v3b s31, s41, s37).

The adapter's local_ramp_arrival_forecast turns connector occupancy into arrivals as
count * 3600 / drain_sec, clipped at max_vph (vissim_stackelberg_adapter.py:9373-9412). Per physical
meter RM_C<connector>, from boundaries_30s.csv (FZP-derived, one row per 30 s window and boundary):
  q         merges into the freeway per hour ('crossings'), 900-5400 s
  N         vehicles on the connector at each 30 s FZP frame ('snapshot_n_veh'); this is the adapter's
            channel local_observation.link_counts[connector] (V5b state_T link_counts equal the V5b FZP
            count at T+0.1 s on all eight connectors at T = 2700 and 3300, and on seven at T = 3000)
  drain_sec mean(N) * 3600 / mean(q), three seeds pooled (Little's law; the 2026-08-30 script used the
            median occupancy, which is 0-8 s for the sparse 10480)
  max_vph   1.15 * max over seeds of q (the 2026-08-30 cap rule, scripts/calibrate_ramp_arrival_20260830.py)

Inputs: extract_observations.py over the network v3b no-control runs D:/VISSIM_runs/20260925_v3b/s{31,41,37}_v3bnc
(networks be0075bf / 261a1fb0 / f5c3d640, native_preserve, 9000 s, FZP 5 s, phase 0.1 s), written to
metanet_calibration_v1/v3b_nc_20260925/observations (receipts s{seed}_v3bnc_extraction_receipt.json beside it);
their sha256 are pinned here. The network is the current runtime network (user decision 2026-09-25: v3b = v2
f475ce42 + route fixes, link-40 left-turn share 1/3, revived-decision splits). Until 2026-09-25 the inputs were
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
OBS = ROOT / 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3b_nc_20260925/observations'
PATTERN = 's{seed}_v3bnc_observations'
INPUTS = {   # boundaries_30s.csv sha256 per seed (v3b NC)
    31: '8deebef9ca510a61c18babaf1c1c52d9f100f678eff280174ed553bee77615af',
    41: '5509f96992deb97049212544dfde04e0cc6045a0aeb2844c250b7807ccefad40',
    37: '956f3a8dda2053a20cb32c1ae37caddd3fc3655ec32563c7b20c8062eaf8a848',
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
