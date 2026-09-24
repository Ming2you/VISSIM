"""C12: connector travel speeds of the v2 network from its own no-control FZP.

Plan C12 (N31 review B9): port_profile.travel_speed_kmh (LPR initialize: ramp
and off-ramp DelayedPort travel) was fitted on the base-120 run. This script
re-derives it from the v2 no-control run s31_v2nc with the SAME statistic as
ER.travel_profile (evaluate_response.py:60-71): per connector, the median of
length_m*3.6/residence_s over complete native traversals that depart at
t <= 900 s. Port events come from EO's own PortObserver
(extract_observations.py:205), fed by the same native_frames reader, in one
pass that stops after the first frame past 900 s (later frames cannot change a
departure at t <= 900).

Resolution: the v2 FZP was written every 5 s (prepared.json
vehicle_record_interval_sec 5, phase 0.1 s), so a raw residence (departure frame
minus arrival frame) is a multiple of 5 s. Off-ramp traversals last 5-15 s, so
the raw ER statistic is quantized far beyond the transit time itself (10682:
81.6 km/h raw against 101.9 at base 120). The recorded POS and SPEED of the
first and last on-connector rows place each endpoint inside its own 5 s
bracket: entry = t_first - pos/v, exit = t_last + (L - pos)/v, each clamped to
the bracket (v = 0 -> the whole bracket). The statistic stays the ER one
(median of L*3.6/residence over complete traversals departing at t <= 900 s);
only the residence is measured inside the recording interval instead of rounded
up to it. Both values are written for audit.

Selection (--select):
  interp     the bracket-resolved residence (default)
  quantized  the raw 5 s residence, i.e. ER.travel_profile verbatim
  b120       the base-120 values (the plan's C12 fallback)

Writes, under this folder only:
  obs/port_events_le900.csv       every port event with time_s <= 900 + one interval
  obs/port_travel_v2.json         the ER statistic, samples and quantization per connector
  port_profile.json               the pinned plant input (LPR reads travel_speed_kmh,
                                  occupancy_lane_loss) plus provenance
Run from the worktree root:
  python -B diagnostics/sdmpc_n31_20260924/port_profile_v2/extract_port_profile.py [--check]
Inputs are read only (D:\\VISSIM_runs\\..., the C1 geometry, the b120 profile).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUN = Path(r'D:\VISSIM_runs\20260923_stage1\s31_v2nc')
GEOMETRY = ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/'
            'observations/s31_v2nc_observations/geometry.json')
B120 = 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/merge_drain_response_20260919/decisions_v1/internal_cost/port_profile.json'
NETWORK_SHA256 = 'f475ce42b0afaceccfd7974066a7b040600ddb93849bcf09174cd794bc0b255b'
FZP_SHA256 = '4eb8e041f04d50473974023a677abff887094fd0606378732d1cd395b6bb16df'  # B110 s31_v2nc manifest.json fzp.file_sha256
LATEST_SEC = 900
OUT_EVENTS = HERE / 'obs' / 'port_events_le900.csv'
OUT_TRAVEL = HERE / 'obs' / 'port_travel_v2.json'
OUT_PROFILE = HERE / 'port_profile.json'
EVENT_FIELDS = ('time_s', 'vehicle', 'connector', 'kind', 'other_link', 'lane', 'position_m', 'speed_kmh',
                'residence_s', 'lower_time_s', 'upper_time_s', 'inferred_unique_connector_passage')


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 22), b''):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def scan(run=RUN, geometry_path=ROOT / GEOMETRY):
    """EO PortObserver over the native frames up to the first frame past LATEST_SEC."""
    from diagnostics.analyze_no_control_corridors import native_frames
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import PortObserver
    prepared = load(run / 'prepared' / 'prepared.json')
    receipt = load(run / 'run' / 'run.json')
    network = Path(receipt['network'])
    if receipt.get('native_preserve') is not True or receipt.get('completed') is not True:
        raise ValueError('A completed native-preserve run is required')
    if sha256_file(network) != NETWORK_SHA256:
        raise ValueError('Run network is not the v2 network f475ce42')
    geometry = load(geometry_path)
    if geometry['network']['sha256'] != NETWORK_SHA256:
        raise ValueError('Geometry belongs to another network')
    interval = int(prepared['vehicle_record_interval_sec'])
    fzps = list((run / 'run' / 'vissim_eval').glob('*.fzp'))
    if len(fzps) != 1:
        raise ValueError('Exactly one FZP required')
    fzp = fzps[0]
    before = fzp.stat()
    evidence = {'path': str(fzp), 'bytes': before.st_size}
    phase = 0.1 if interval == 5 else 0.0
    ports = PortObserver(geometry, interval_sec=interval, phase_sec=phase)
    last = None
    started = time.monotonic()
    for sec, frame in native_frames(fzp, evidence, deadline=started + 3600, interval_sec=interval, phase_sec=phase):
        ports.advance(sec, frame)
        last = sec
        if sec > LATEST_SEC:
            break
    after = fzp.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('FZP changed while scanning')
    if last is None or last <= LATEST_SEC:
        raise ValueError('FZP ended before the training window closed')
    file_sha = sha256_file(fzp)
    if file_sha != FZP_SHA256:
        raise ValueError('FZP differs from the one the b110 observations were extracted from')
    lengths = {str(b['connector']): float(b['length_m']) for b in geometry['boundaries']
               if b['kind'] in ('ramp', 'offramp')}
    source = {'run': str(run), 'network': {'path': str(network), 'sha256': NETWORK_SHA256},
              'fzp': {'path': str(fzp), 'bytes': before.st_size, 'sha256': file_sha,
                      'recording_interval_sec': interval, 'phase_sec': phase, 'last_frame_scanned_s': last},
              'geometry': {'path': GEOMETRY, 'sha256': sha256_file(geometry_path)},
              'port_observer': 'extract_observations.PortObserver', 'elapsed_sec_not_benchmark': time.monotonic() - started}
    return ports.events, lengths, interval, source


def travel(events, lengths, interval):
    """ER.travel_profile on the scanned events, raw and bracket-resolved residence.

    A departure event carries the last on-connector row (position, speed) and
    its frame is the first one off the connector; the paired arrival event
    carries the first on-connector row. Inferred skip passages (5 s mode) have
    no residence and are excluded, as ER excludes them.
    """
    quantized = {c: [] for c in lengths}
    resolved = {c: [] for c in lengths}
    residences = {c: [] for c in lengths}
    arrivals = {}
    for r in events:
        key = (r['vehicle'], str(r['connector']))
        if r['kind'] == 'arrival':
            arrivals[key] = r if not r.get('inferred_unique_connector_passage') else None
            continue
        if r['kind'] != 'departure':
            arrivals.pop(key, None)
            continue
        arrival = arrivals.pop(key, None)
        if float(r['time_s']) > LATEST_SEC:
            continue
        res = r.get('residence_s')
        if res is None or res == '' or float(res) <= 0:
            continue
        c = str(r['connector'])
        if arrival is None:
            raise ValueError('Complete traversal without its arrival row: %s %s' % key)
        length = lengths[c]
        quantized[c].append(length * 3.6 / float(res))
        residences[c].append(float(res))
        v1, v2 = float(arrival['speed_kmh']) / 3.6, float(r['speed_kmh']) / 3.6
        lead = min(float(interval), max(0.0, float(arrival['position_m'])) / v1) if v1 > 0 else float(interval)
        tail = min(float(interval), max(0.0, length - float(r['position_m'])) / v2) if v2 > 0 else float(interval)
        span = float(res) - interval + lead + tail
        if not span > 0:
            raise ValueError('Non-positive bracket-resolved residence: %s %s' % key)
        resolved[c].append(length * 3.6 / span)
    if any(not v for v in quantized.values()):
        raise ValueError('Missing pre-control connector travel sample: '
                         + ','.join(c for c, v in quantized.items() if not v))
    return {c: {'length_m': lengths[c], 'samples': len(quantized[c]),
                'travel_speed_kmh_interp': statistics.median(resolved[c]),
                'travel_speed_kmh_quantized': statistics.median(quantized[c]),
                'median_residence_s_quantized': statistics.median(residences[c]),
                'residence_values_s_quantized': sorted({round(x, 6) for x in residences[c]})}
            for c in lengths}


def profile(rows, b120, select):
    if select not in ('interp', 'quantized', 'b120'):
        raise ValueError('Unknown selection')
    if set(rows) != set(b120['travel_speed_kmh']):
        raise ValueError('v2 and b120 connector sets differ')
    if select == 'b120':
        return {c: float(b120['travel_speed_kmh'][c]) for c in rows}
    return {c: r['travel_speed_kmh_' + select] for c, r in rows.items()}


def build(select='interp', run=RUN):
    events, lengths, interval, source = scan(run)
    rows = travel(events, lengths, interval)
    b120_path = ROOT / B120
    b120 = load(b120_path)
    speeds = profile(rows, b120, select)
    travel_doc = {'schema': 'sdmpc31-port-travel/v1', 'statistic': 'evaluate_response.travel_profile (ER:60-71)',
                  'latest_training_sec': LATEST_SEC, 'source': source, 'connectors': rows,
                  'b120_travel_speed_kmh': b120['travel_speed_kmh']}
    document = {
        'occupancy_lane_loss': bool(b120['occupancy_lane_loss']),
        'travel_speed_kmh': speeds,
        'sample_counts': {c: rows[c]['samples'] for c in rows},
        'latest_training_sec': LATEST_SEC,
        'limits': b120['limits'],
        'provenance': {
            'schema': 'sdmpc31-port-profile/v2', 'plan': 'SDMPC31_OBS150_PLAN_20260924 C12',
            'selection': select,
            'statistic': ('median of length*3.6/residence over complete traversals departing at t <= 900 s '
                          '(ER.travel_profile); residence resolved inside the 5 s recording bracket'
                          if select == 'interp' else 'ER.travel_profile verbatim' if select == 'quantized'
                          else 'base-120 fallback (plan C12)'),
            'v2_run': source['run'], 'v2_fzp_sha256': source['fzp']['sha256'],
            'recording_interval_sec': interval, 'port_travel': 'obs/port_travel_v2.json',
            'b120': {'path': B120, 'sha256': sha256_file(b120_path)},
            'occupancy_lane_loss': 'kept from base-120 (plan C4(e): A/B in V3b)'}}
    return events, travel_doc, document


def dumps(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def events_bytes(events):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=EVENT_FIELDS, lineterminator='\n')
    writer.writeheader()
    for r in events:
        if float(r['time_s']) <= LATEST_SEC + 5:
            writer.writerow({k: r.get(k) for k in EVENT_FIELDS})
    return buffer.getvalue().encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--select', default='interp', choices=('interp', 'quantized', 'b120'))
    parser.add_argument('--check', action='store_true', help='re-derive and compare with the written files')
    args = parser.parse_args()
    events, travel_doc, document = build(args.select)
    outputs = {OUT_EVENTS: events_bytes(events), OUT_PROFILE: dumps(document)}
    travel_doc['source'].pop('elapsed_sec_not_benchmark', None)
    outputs[OUT_TRAVEL] = dumps(travel_doc)
    for path, data in outputs.items():
        if args.check:
            if path.read_bytes() != data:
                raise SystemExit('Differs from its generator: ' + path.name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print('PORT_PROFILE_OK select=%s connectors=%d' % (args.select, len(document['travel_speed_kmh'])))


if __name__ == '__main__':
    main()
