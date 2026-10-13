"""Complete current SC10 north source paths, including entry connectors.

The current static route may end before the next routing decision. It proves
the current corridor, not a future SC12 turn. Keep that turn unknown.
"""
from contextlib import contextmanager
import hashlib
import xml.etree.ElementTree as ET

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as gate
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331 import gate_coverage as post


def entry_paths(cfg, network):
    gate.require(hashlib.sha256(network).hexdigest() == gate.NETWORK_SHA, 'Unreviewed geometry')
    root = ET.fromstring(network)
    links = {node.get('no'): node for node in root.findall('./links/link')}
    stop = min(float(h.get('pos')) for h in root.findall('./signalHeads/signalHead')
               if h.get('lane').split()[0] == gate.TERMINAL)
    paths = {}
    sources = 0
    for movement, spec in cfg.network.urban_movements.items():
        if spec.get('receiving_link') != gate.TARGET:
            continue
        turns = cfg.network.control_area_routes['movement:' + movement]['physical_turns']
        gate.require(len(turns) == 1 and turns[0]['to_link'] == gate.SHARED[0],
                     'Incoming physical path ambiguous')
        path = [turns[0]['connector'], *gate.SHARED]
        gate.measure(path, links, 0., stop)
        for i in range(path.index(gate.GATE) + 1):
            suffix = path[i:]
            if suffix not in paths.setdefault(path[i], []):
                paths[path[i]].append(suffix)
        sources += 1
    gate.require(sources == 3, 'Source catalog changed')
    return paths


def current_route(row, root, paths, original):
    link = str(row[1])
    if link not in paths:
        return original(row, root)
    choices = paths[link]
    if not all(v is None for v in row[6:10]):
        gate.require(all(v is not None for v in row[6:9]) and row[8] == 'STATIC',
                     'Partial or unsupported route')
        decision = root.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{int(row[6])}']")
        route = None if decision is None else decision.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(row[7])}']")
        gate.require(route is not None, 'Current route absent from pinned network')
        native = [decision.get('link'), *[n.get('key') for n in route.findall('./linkSeq/intObjectRef')], route.get('destLink')]
        if gate.TERMINAL in native:
            return original(row, root)
        gate.require(native.count(link) == 1, 'Ambiguous current path')
        suffix = native[native.index(link):]
        gate.require(row[9] is None or (len(suffix) > 1 and str(int(row[9])) == suffix[1]),
                     'Route and next connector disagree')
        choices = [p for p in choices if p[:len(suffix)] == suffix]
        gate.require(choices, 'Current partial route leaves the source corridor')
    links = {n.get('no'): n for n in root.findall('./links/link')}
    stop = min(float(h.get('pos')) for h in root.findall('./signalHeads/signalHead')
               if h.get('lane').split()[0] == gate.TERMINAL)
    _, path = min((gate.measure(p, links, row[3], stop), p) for p in choices)
    gate.require(path.count(gate.GATE) == 1, 'Pre-gate vehicle must cross exactly one gate')
    return None, path


@contextmanager
def enabled(cfg, network):
    paths = entry_paths(cfg, network)
    with post.enabled(network) as receipt:
        old_pre, old_route = gate.PRE, gate.current_route
        gate.PRE = old_pre | set(paths)
        gate.current_route = lambda row, root: current_route(row, root, paths, old_route)
        try:
            yield dict(receipt, entry_paths=paths, partial_route_rule='current prefix only; future turn remains unknown')
        finally:
            gate.PRE, gate.current_route = old_pre, old_route
