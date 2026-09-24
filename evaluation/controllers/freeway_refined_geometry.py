"""Parent-preserving refined freeway partition for the v2 lane plant (plan C2).

The refinement logic is the one extract_observations.py applies with
``--refined-geometry`` (lines 607-616), factored out so the online plant builds
exactly the calibration geometry. The extractor itself is left untouched.

A refined partition only splits the 21 canonical cells; it never moves a
physical attachment. Every function here raises ValueError instead of
repairing a geometry. Nothing here runs in a tangent worker.
"""
from __future__ import annotations

import copy
import math

from evaluation.controllers.freeway_geometry import geometry_fingerprint

ROADS = ('FW_E', 'FW_W')
PARENT_CELLS = 21
BOUND_TOL_M = 1e-6


def _cells(geometry, road):
    rows = sorted((c for c in geometry['cells'] if c['road'] == road), key=lambda c: int(c['cell']))
    if [int(c['cell']) for c in rows] != list(range(len(rows))):
        raise ValueError('Freeway cells must be numbered 0..n-1 per road: ' + road)
    return rows


def apply_refined_partition(geometry, refined, *, pin):
    """Return a copy of ``geometry`` with the refined cells, bounds and port cells.

    geometry: the 21-cell physical_geometry(network, profile) of the live network.
    refined:  the pinned refined partition document (same physical topology).
    pin:      {'path', 'sha256'} of that document, recorded as refined_partition.
    """
    if geometry_fingerprint(refined) != geometry_fingerprint(geometry):
        raise ValueError('Refined physical topology differs from the network geometry')
    if geometry.get('refined_partition'):
        raise ValueError('Geometry is already refined')
    out = copy.deepcopy(geometry)
    out['cells'], out['bounds'] = copy.deepcopy(refined['cells']), copy.deepcopy(refined['bounds'])
    indices = {b['id']: b for b in refined['boundaries']}
    if set(indices) != {b['id'] for b in out['boundaries']}:
        raise ValueError('Refined partition boundary set differs')
    for b in out['boundaries']:
        b.update({k: indices[b['id']][k] for k in ('from_cell', 'to_cell')})
    out['refined_partition'] = {'path': pin['path'], 'sha256': pin['sha256']}
    validate_refinement(geometry, out)
    return out


def validate_refinement(parent_geometry, refined_geometry):
    """Children tile each canonical parent exactly and keep its lane-km."""
    for road in ROADS:
        parents = _cells(parent_geometry, road)
        cells = _cells(refined_geometry, road)
        if len(parents) != PARENT_CELLS:
            raise ValueError('Parent geometry must have the 21 canonical cells: ' + road)
        bounds = list(map(float, refined_geometry['bounds'][road]))
        if len(bounds) != len(cells) + 1:
            raise ValueError('Refined bounds do not cover the refined cells: ' + road)
        order = [int(c['parent_cell']) for c in cells]
        if order != sorted(order) or sorted(set(order)) != list(range(PARENT_CELLS)):
            raise ValueError('Refined cells must keep every parent, in order: ' + road)
        for c in cells:
            i = int(c['cell'])
            if abs(float(c['start_m'])-bounds[i]) > BOUND_TOL_M or abs(float(c['end_m'])-bounds[i+1]) > BOUND_TOL_M:
                raise ValueError('Refined cell differs from its bounds: %s %d' % (road, i))
        for p in parents:
            children = [c for c in cells if int(c['parent_cell']) == int(p['cell'])]
            if (abs(float(children[0]['start_m'])-float(p['start_m'])) > BOUND_TOL_M
                    or abs(float(children[-1]['end_m'])-float(p['end_m'])) > BOUND_TOL_M):
                raise ValueError('Refined children do not tile parent %s %s' % (road, p['cell']))
            lane_km = math.fsum(float(c['lane_km']) for c in children)
            if abs(lane_km-float(p['lane_km'])) > 1e-9:
                raise ValueError('Refined children change parent lane-km %s %s' % (road, p['cell']))
    for b in refined_geometry['boundaries']:
        for key in ('from_cell', 'to_cell'):
            value = b.get(key)
            if value is not None:
                n = len(_cells(refined_geometry, b['road']))
                if type(value) is not int or not 0 <= value < n:
                    raise ValueError('Refined port cell outside its road: ' + str(b['id']))


def parents(geometry):
    """{road: [parent_cell for each refined cell]}."""
    return {road: [int(c['parent_cell']) for c in _cells(geometry, road)] for road in ROADS}


def vsl_head_of_cell(parent_cells, heads):
    """Parent-space VSL zone table: each cell reads its parent's zone-head key.

    heads are the controller's 21-cell zone heads (e.g. [0, 5, 10, 15]). Cell i
    maps to the largest head <= parent(i), so the 21-key command a zone head
    carries is applied on every refined cell of that parent zone.
    """
    hs = sorted({int(h) for h in heads})
    if not hs or hs[0] != 0 or hs[-1] >= PARENT_CELLS:
        raise ValueError('Parent VSL zone heads must start at 0 inside the 21-cell grid')
    head_of, zone_of = [], []
    for p in parent_cells:
        z = max(j for j, h in enumerate(hs) if h <= p)
        zone_of.append(z)
        head_of.append(hs[z])
    return hs, head_of, zone_of


def collapse_to_parents(geometry):
    """The 21-cell geometry the refined one was split from (bench/test helper)."""
    out = copy.deepcopy(geometry)
    out.pop('refined_partition', None)
    cells = []
    for road in ROADS:
        rows = _cells(geometry, road)
        for p in range(PARENT_CELLS):
            children = [c for c in rows if int(c['parent_cell']) == p]
            length_km = math.fsum(float(c['length_km']) for c in children)
            lane_km = math.fsum(float(c['lane_km']) for c in children)
            pieces = []
            for c in children:
                for piece in c['physical_pieces']:
                    if pieces and pieces[-1]['link'] == piece['link'] and pieces[-1]['lanes'] == piece['lanes']:
                        pieces[-1] = {**pieces[-1], 'length_m': pieces[-1]['length_m']+piece['length_m']}
                    else:
                        pieces.append(dict(piece))
            cells.append({'road': road, 'cell': p, 'start_m': children[0]['start_m'], 'end_m': children[-1]['end_m'],
                          'length_km': length_km, 'lane_km': lane_km, 'effective_lanes': lane_km/length_km,
                          'canonical_segment_lanes': children[0]['canonical_segment_lanes'],
                          'physical_pieces': pieces})
        out['bounds'][road] = [c['start_m'] for c in cells if c['road'] == road] + [cells[-1]['end_m']]
    out['cells'] = cells
    table = parents(geometry)
    for b in out['boundaries']:
        for key in ('from_cell', 'to_cell'):
            if b.get(key) is not None:
                b[key] = table[b['road']][b[key]]
    return out
