"""Validate current-route observations captured with the complete paused stock."""
from __future__ import annotations

from evaluation.controllers.projection_support import complete_records

ATTRIBUTES = {'veh_no': 'No', 'route_decision_no': 'RoutDecNo',
              'route_no': 'RouteNo', 'route_decision_type': 'RoutDecType'}


def complete_vehicle_routes(raw, *, required=False):
    """Return ID-indexed observations; None means the optional capture is absent.

    A null identity is an observed absence of a current route. It does not mean
    that the vehicle is eligible for a future decision at its current position.
    """
    envelope = raw.get('vehicle_routes')
    if envelope is None and not required:
        return None
    if not isinstance(envelope, dict) or envelope.get('schema_version') != 'vissim-vehicle-routes-v1':
        raise ValueError('A supported complete current-route capture is required')
    physical = complete_records(raw)
    records = envelope.get('records')
    if envelope.get('complete') is not True or not isinstance(records, list):
        raise ValueError('Current-route capture is incomplete')
    if envelope.get('source_attributes') != ATTRIBUTES:
        raise ValueError('Current-route source attributes differ from the qualified COM capture')
    if any(type(envelope.get(k)) is not int or envelope[k] != len(physical)
           for k in ('record_count', 'collection_count_before', 'collection_count_after')):
        raise ValueError('Current-route counts differ from the physical snapshot')
    if any(isinstance(envelope.get(k), bool) or envelope.get(k) != raw['sim_sec']
           for k in ('sim_sec_before', 'sim_sec_after')):
        raise ValueError('Current-route capture was not paused at the physical snapshot time')
    result = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != set(ATTRIBUTES):
            raise ValueError('Malformed current-route record')
        vehicle = row['veh_no']
        if type(vehicle) is not int or not 0 < vehicle <= 2147483647 or vehicle in result:
            raise ValueError('Invalid or repeated current-route vehicle ID')
        identity = (row['route_decision_no'], row['route_no'], row['route_decision_type'])
        if any(value is None for value in identity):
            if not all(value is None for value in identity):
                raise ValueError('Partially missing current-route identity')
        elif (any(type(value) is not int or not 0 < value <= 2147483647 for value in identity[:2])
              or not isinstance(identity[2], str) or not identity[2].strip()):
            raise ValueError('Invalid current-route identity')
        result[vehicle] = dict(row)
    if len(records) != len(physical) or set(result) != {row['veh_no'] for row in physical}:
        raise ValueError('Current-route IDs differ from the physical snapshot')
    return result
