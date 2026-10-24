"""SC10N post-gate connectors already owned by the same aggregate storage.

Only extend observed-position coverage. Unknown destination remains unknown;
the existing beta consumes it later. Never send a post-gate vehicle back to SG4.
"""
from contextlib import contextmanager
import hashlib
import xml.etree.ElementTree as ET
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325 import candidate as gate

def connector_paths(network):
    if hashlib.sha256(network).hexdigest()!=gate.NETWORK_SHA:
        raise ValueError('Unreviewed physical geometry')
    root=ET.fromstring(network)
    paths={}
    decision=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='33']")
    for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
        path=[decision.get('link'),*[n.get('key') for n in route.findall('./linkSeq/intObjectRef')],route.get('destLink')]
        i,j=path.index(gate.GATE),path.index(gate.TERMINAL)
        if i>=j:raise ValueError('Gate/terminal order changed')
        for k in range(i+1,j):
            link=root.find(f"./links/link[@no='{path[k]}']")
            if link.find('fromLinkEndPt') is not None:
                suffix=path[k:j+1]
                paths.setdefault(path[k],[])
                if suffix not in paths[path[k]]:paths[path[k]].append(suffix)
    if set(paths)!={'10218','10223','10224'}:
        raise ValueError('Review changed post-gate connector catalog')
    return paths

def current_route(row,root,paths,original):
    link=str(row[1])
    if link not in paths or not all(v is None for v in row[6:10]):
        return original(row,root)
    # The current connector fixes a physical suffix, not a future destination.
    # For an unnamed route preserve the old shortest-path convention only for
    # the remaining transport, then leave destination splitting to baseline beta.
    links={n.get('no'):n for n in root.findall('./links/link')}
    stop=min(float(h.get('pos')) for h in root.findall('./signalHeads/signalHead')
             if h.get('lane').split()[0]==gate.TERMINAL)
    choices=[(gate.measure(path,links,row[3],stop),path) for path in paths[link]]
    distance,path=min(choices)
    if gate.GATE in path:raise ValueError('Post-gate vehicle sent upstream')
    return None,path

@contextmanager
def enabled(network):
    paths=connector_paths(network)
    old_post,old_route=gate.POST,gate.current_route
    gate.POST=old_post|set(paths)
    gate.current_route=lambda row,root:current_route(row,root,paths,old_route)
    try:yield dict(post_connector_paths=paths,unknown_turn_rule='unchanged baseline beta',
                   remaining_geometry='current connector position to terminal head',
                   source_stock_unchanged=True,new_fit=False)
    finally:gate.POST,gate.current_route=old_post,old_route
