"""Explicit reservoir families for saved-response accounting (no plant changes)."""
from collections import defaultdict


def family_keys(movements, origins):
    origins = set(origins)
    return {'storage:' + origin for origin in origins} | {
        'movement:' + key for key, spec in movements.items()
        if spec.get('origin') in origins
    }


def stock_total(row, keys):
    return sum(sum(row['stocks'].get(key, {}).values()) for key in keys)


def boundary_ledger(transfers, keys, start, end):
    incoming, outgoing = defaultdict(float), defaultdict(float)
    for row in transfers:
        if row['start_sec'] < start or row['end_sec'] > end:
            continue
        source, target = row['source'], row['target']
        if target in keys and source not in keys:
            incoming[str(source)] += row['vehicles']
        if source in keys and target not in keys:
            outgoing[str(source)] += row['vehicles']
    return dict(incoming_by_source=dict(incoming), outgoing_by_source=dict(outgoing),
                incoming=sum(incoming.values()), outgoing=sum(outgoing.values()))


def crossing_edges(edges, links):
    return (sorted((u, v) for u, v in edges if u not in links and v in links),
            sorted((u, v) for u, v in edges if u in links and v not in links))
