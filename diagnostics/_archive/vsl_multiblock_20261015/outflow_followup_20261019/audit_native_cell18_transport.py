"""Compare native Nv/L with observed discharge, accounting for spatial storage."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

A = Path(__file__).resolve().parent
O = A / 'interaction_response'
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def main():
    output = O / 'native_cell18_transport.json'
    assert not output.exists()
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    contract = read(ROOT / 'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
    rt = route.compile_inventory(contract, read(ROOT / contract['mapping']['path']))
    bounds = rt['bounds']['FW_E']
    length_m = bounds[19] - bounds[18]
    netfile = Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/network/sdmpc31_g_2250_hold_s29.inpx')
    raw = netfile.read_bytes()
    PINS[str(netfile)] = hashlib.sha256(raw).hexdigest()
    off = ET.fromstring(raw).find("./links/link[@no='10481']/fromLinkEndPt")
    assert off is not None
    parent_link = off.get('lane').split()[0]
    offset = rt['physical'][parent_link][1]
    off_fraction = (offset + float(off.get('pos')) - bounds[18]) / length_m
    assert 0 < off_fraction < 1
    actual = read(A / 'approach_flux.json')
    records = []
    for case in ('hold', 'single90', 'selected'):
        extracted = read(O / (case + '_records.json.gz'))
        frames = {}
        for row in extracted['rows']:
            if row[2] != 18 or row[0] < 2250:
                continue
            frames.setdefault(row[0], []).append((row[4], row[5]))
        run = Path(extracted['source']).parent.parent
        stem = 'vsl90' if case == 'single90' else case
        decisions = run / f'decisions_sdmpc31_g_2250_{stem}_s29'
        for t in (2250, 2400, 2550, 2700):
            state = read(decisions / f'state_{t:06d}.json')
            assert state['vehicle_records']['complete'] and state['sim_sec'] == t
            frames[t] = []
            for row in state['vehicle_records']['records']:
                link = str(row['link_no'])
                if link not in rt['physical']:
                    continue
                road, offset = rt['physical'][link]
                x = offset + row['position_m']
                if road == 'FW_E' and bounds[18] <= x < bounds[19]:
                    frames[t].append((x, row['speed_kph']))
        points = {}
        for t, vehicles in frames.items():
            points[t] = dict(n=len(vehicles), speed=math.fsum(v for _, v in vehicles) / len(vehicles),
                q_proxy_veh_s=math.fsum(v for _, v in vehicles) / (3.6 * length_m),
                moment=math.fsum((x - bounds[18]) / length_m for x, _ in vehicles))
        assert len(points) == 94
        cached = actual['cases'][case]
        for block in range(3):
            start, end = 2250 + block * 150, 2400 + block * 150
            times = sorted(t for t in points if start <= t <= end)
            assert times[0] == start and times[-1] == end
            left = math.fsum(points[t0]['q_proxy_veh_s'] * (t1 - t0) for t0, t1 in zip(times, times[1:]))
            right = math.fsum(points[t1]['q_proxy_veh_s'] * (t1 - t0) for t0, t1 in zip(times, times[1:]))
            proxy = .5 * (left + right)
            moment_delta = points[end]['moment'] - points[start]['moment']
            observed = {}
            for key in ('through:10481', 'off_entry:10481'):
                slab = cached['first_meter_storage'][key]
                observed[key] = cached['detector_counts150'][key][block] + slab[block + 1] - slab[block]
            predicted_face = proxy - moment_delta - off_fraction * observed['off_entry:10481']
            records.append(dict(case=case, block=block, start=start, end=end,
                transport_proxy=proxy, left_rule=left, right_rule=right,
                spatial_storage_moment_delta=moment_delta, off_exit_fraction=off_fraction,
                observed_mainline_face=observed['through:10481'], observed_off_face=observed['off_entry:10481'],
                storage_adjusted_mainline_proxy=predicted_face,
                adjusted_error=predicted_face - observed['through:10481'],
                start_state=points[start], end_state=points[end]))
    contrasts = []
    for case in ('single90', 'selected'):
        for blocks in (1, 2, 3):
            aa = [r for r in records if r['case'] == 'hold' and r['block'] < blocks]
            bb = [r for r in records if r['case'] == case and r['block'] < blocks]
            contrast = dict(case=case, horizon=blocks * 150)
            for key in ('transport_proxy', 'spatial_storage_moment_delta', 'observed_mainline_face', 'observed_off_face', 'storage_adjusted_mainline_proxy', 'adjusted_error'):
                contrast[key + '_delta'] = math.fsum(r[key] for r in bb) - math.fsum(r[key] for r in aa)
            contrasts.append(contrast)
    result = dict(status='complete_native_spatial_transport_identity_check', length_m=length_m,
        rows=records, contrasts=contrasts, source_pins=PINS,
        interpretation='Continuum first-position-moment identity: integrated Nv/L = mainline exit + off-exit-position fraction times off exit + change in spatial moment. This is checked with sampled native fields, not used as a future model input.',
        limitations=['Five-second velocity quadrature and rounded FZP positions/speeds are approximate; left/right are numerical choices, not confidence bounds.',
                     'No unobserved source or deletion inside cell18 is assumed in the identity; residual is retained rather than assigned to normal outflow.',
                     'Off-ramp source is inside cell18, not at its downstream face. Its actual position and separate detector counts are retained.',
                     'First-meter detector storage corrections retain the original no-unobserved-loss-in-that-meter qualification.'],
        new_native=0, new_fzp_streams=0, new_forecasts=0, new_fits=0, production_edits=0)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(length_m=length_m, off_fraction=off_fraction, contrasts=contrasts,
                         absolute_errors=[(r['case'],r['block'],r['adjusted_error']) for r in records]), indent=2))


if __name__ == '__main__':
    main()
