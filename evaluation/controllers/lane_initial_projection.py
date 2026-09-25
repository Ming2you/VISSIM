"""Opt-in conservative spatial initialization across the126->10641 connection.

Microscopic vehicle counts can exceed a short lane's mean-spacing capacity.
Retain every vehicle and route, projecting the upstreammost excess into the
real upstream lane only when that lane has space; a 126 lane's own excess moves
sideways onto the other 126 lane. No capacity or demand
changes, no new receiving space, and no mutation of native observations.
"""
from collections import Counter
from copy import deepcopy
import math
import xml.etree.ElementTree as ET


def project(current, network, spacing):
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError('Positive finite initialization spacing required')
    root = ET.parse(network).getroot()
    links = {int(x.get('no')): x for x in root.findall('./links/link')}
    connector = links[10641]
    origin = connector.find('./fromLinkEndPt')
    target = connector.find('./toLinkEndPt')
    if (origin.get('lane') != '126 1' or target.get('lane') != '71 2'
            or len(connector.findall('./lanes/lane')) != 2
            or len(links[126].findall('./lanes/lane')) != 2):
        raise ValueError('Initial upstream projection needs the unchanged two-lane126->10641->71 connection')
    points = list(connector.find('./geometry/linkPolyPts'))
    length = sum(math.sqrt(sum((float(a.get(k, '0'))-float(b.get(k, '0')))**2
                 for k in ('x', 'y', 'zOffset'))) for a, b in zip(points, points[1:]))
    upstream_end = float(origin.get('pos'))
    result = deepcopy(current)
    moves = []
    # The 71 lanes that 10641 feeds (10641 lane k -> 71 lane k+1) can hold one more microscopic
    # vehicle than their mean-spacing storage up to the last 71 exit, as the local model sees them
    # (V5 sdmpc31_v2_s31, 1950 s: 14 on 71 lane 3, storage 81.24/6 = 13.5). Their upstreammost excess
    # moves onto the downstream end of the feeding 10641 lane first; the 10641 step below then carries
    # any 10641 excess on into 126. Other 71 lanes have no such connection and still fail closed.
    end71 = max(float(x.find('./fromLinkEndPt').get('pos')) for x in links.values()
                if x.find('./fromLinkEndPt') is not None
                and x.find('./fromLinkEndPt').get('lane', '').split()[0] == '71')
    for lane in (1, 2):
        lane71 = lane + 1
        source = sorted((v for v in result['vehicles'] if v['link'] == 71 and v['lane'] == lane71),
                        key=lambda v: (v['position_m'], v['vehicle']))
        excess = max(0, len(source)-math.floor(end71/spacing+1e-9))
        for vehicle in source[:excess]:
            if vehicle['position_m'] < 0:
                raise ValueError('Invalid observed link 71 position')
            moves.append(dict(vehicle=vehicle['vehicle'], lane=lane, source_link=71, source_lane=lane71,
                target_link=10641, source_position_m=vehicle['position_m'], target_position_m=length,
                backward_boundary_distance_m=vehicle['position_m'], vehicles=1.0))
            vehicle['link'], vehicle['lane'], vehicle['position_m'] = 10641, lane, length
    cap126 = math.floor(upstream_end/spacing+1e-9)
    for lane in (1, 2):
        source = sorted((v for v in result['vehicles'] if v['link'] == 10641 and v['lane'] == lane),
                        key=lambda v: (v['position_m'], v['vehicle']))
        excess = max(0, len(source)-math.floor(length/spacing+1e-9))
        if not excess:
            continue
        # Both 126 lanes together must hold it; the 126 step below balances a lane left above its storage.
        if sum(v['link'] == 126 for v in result['vehicles'])+excess > 2*cap126:
            raise ValueError('Initial excess has no physical upstream lane space; cannot discard it or enlarge capacity')
        for vehicle in source[:excess]:
            if not 0 <= vehicle['position_m'] <= length:
                raise ValueError('Invalid observed connector position')
            moves.append(dict(vehicle=vehicle['vehicle'], lane=lane, source_link=10641,
                target_link=126, source_position_m=vehicle['position_m'], target_position_m=upstream_end,
                backward_boundary_distance_m=vehicle['position_m'], vehicles=1.0))
            vehicle['link'], vehicle['position_m'] = 126, upstream_end
    # A 126 lane itself can hold one to three more microscopic vehicles than its mean-spacing storage
    # (network v3b no-control: 126 lane 2 above 152.46/6 = 25.4 in 84/40/26 of 1799 frames of s31/s41/s37,
    # up to 28; R-obs sdmpc31_v3b_nc_s31 stopped at 3150 s with 26). Its upstreammost excess moves sideways
    # onto the other 126 lane at the same position when that lane has room: both 126 lanes lead through
    # 10641 into 71, so no vehicle loses its exit. Without room it still fails closed.
    for lane in (1, 2):
        source = sorted((v for v in result['vehicles'] if v['link'] == 126 and v['lane'] == lane),
                        key=lambda v: (v['position_m'], v['vehicle']))
        excess = max(0, len(source)-cap126)
        if not excess:
            continue
        if excess > cap126-sum(v['link'] == 126 and v['lane'] == 3-lane for v in result['vehicles']):
            raise ValueError('Initial excess has no physical upstream lane space; cannot discard it or enlarge capacity')
        for vehicle in source[:excess]:
            if vehicle['position_m'] < 0:
                raise ValueError('Invalid observed link 126 position')
            moves.append(dict(vehicle=vehicle['vehicle'], lane=3-lane, source_link=126, source_lane=lane,
                target_link=126, source_position_m=vehicle['position_m'], target_position_m=vehicle['position_m'],
                backward_boundary_distance_m=0.0, vehicles=1.0))
            vehicle['lane'] = 3-lane
    if Counter(v['vehicle'] for v in result['vehicles']) != Counter(v['vehicle'] for v in current['vehicles']):
        raise AssertionError('Initialization projection lost vehicle identities')
    return result, dict(schema='conservative-initial-lane-projection/v1', moves=moves,
        observed_vehicles=len(current['vehicles']), projected_vehicles=len(result['vehicles']),
        capacities_changed=False, native_vehicles_moved=False,
        scope='Prediction initialization only; upstream displacement is a declared spatial approximation')
