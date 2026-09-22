"""Opt-in conservative spatial initialization across the126->10641 connection.

Microscopic vehicle counts can exceed a short lane's mean-spacing capacity.
Retain every vehicle, route and lane, projecting the upstreammost excess into
the real upstream lane only when that lane has space. No capacity or demand
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
    for lane in (1, 2):
        source = sorted((v for v in result['vehicles'] if v['link'] == 10641 and v['lane'] == lane),
                        key=lambda v: (v['position_m'], v['vehicle']))
        excess = max(0, len(source)-math.floor(length/spacing+1e-9))
        if not excess:
            continue
        upstream = [v for v in result['vehicles'] if v['link'] == 126 and v['lane'] == lane]
        if len(upstream)+excess > math.floor(upstream_end/spacing+1e-9):
            raise ValueError('Initial excess has no physical upstream lane space; cannot discard it or enlarge capacity')
        for vehicle in source[:excess]:
            if not 0 <= vehicle['position_m'] <= length:
                raise ValueError('Invalid observed connector position')
            moves.append(dict(vehicle=vehicle['vehicle'], lane=lane, source_link=10641,
                target_link=126, source_position_m=vehicle['position_m'], target_position_m=upstream_end,
                backward_boundary_distance_m=vehicle['position_m'], vehicles=1.0))
            vehicle['link'], vehicle['position_m'] = 126, upstream_end
    if Counter(v['vehicle'] for v in result['vehicles']) != Counter(v['vehicle'] for v in current['vehicles']):
        raise AssertionError('Initialization projection lost vehicle identities')
    return result, dict(schema='conservative-initial-lane-projection/v1', moves=moves,
        observed_vehicles=len(current['vehicles']), projected_vehicles=len(result['vehicles']),
        capacities_changed=False, native_vehicles_moved=False,
        scope='Prediction initialization only; upstream displacement is a declared spatial approximation')
