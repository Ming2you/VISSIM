"""Complete primal-state comparison without per-leaf imports or ABC dispatch.

The sparse ledger equivalence is the same as the original worker comparison.
Only completed comparisons of the same object pair and field mode are reused.
Retaining the objects prevents id reuse while unpacking historical ledgers.
This module is deliberately outside tangent source instrumentation.
"""
from collections import deque, defaultdict
import math
import numbers
import pickle
from types import ModuleType

import numpy as np
from evaluation.controllers.sdmpc_dual import Dual, primal


def state_error(a, b, path='states', *, fast_records=False, compact_records=False):
    cache = {}
    unpacked = {}
    compacted = {}
    transfer_cache = {}
    from evaluation.controllers.sdmpc_tangent_audit import AuditBlock, pack as compact_pack, error as compact_error

    def compact(value):
        if type(value) is AuditBlock:
            return value
        key=id(value)
        if key not in compacted:
            compacted[key]=(value,compact_pack(unpack(value)))
        return compacted[key][1]

    def transfer_rows(value):
        if type(value) is not AuditBlock:
            return unpack(value)['transfers']
        key=id(value)
        if key not in transfer_cache:
            transfer_cache[key]=(value,pickle.loads(value.transfers))
        return transfer_cache[key][1]
    real_types = (float, int, bool, Dual, np.float64, np.float32, np.int64, np.int32)
    amounts = ('vehicles', 'ttd_veh', 'entered_veh')
    identities = ('stage', 'start_sec', 'end_sec', 'source', 'target', 'route_key')
    transfer_keys = frozenset(amounts+identities)
    allocation_keys = frozenset(('stage','start_sec','end_sec','kind','resource',
        'available_veh','accepted_by_source_veh','accepted_total_veh','exceedance_veh'))
    bound_keys = frozenset(('stage','start_sec','end_sec','kind','resource','value_veh','upper_veh'))

    def plain_record(row, allocation):
        # Only canonical records of plain values can take the C-level equality
        # shortcut. Unknown schemas, subclasses and AD operands use the complete
        # recursive comparator below; no AD comparison can create branch events.
        if type(row) is not dict or row.keys() != (allocation_keys if allocation else bound_keys):
            return False
        for name in ('stage','kind','resource'):
            if type(row[name]) is not str:return False
        numeric_keys = (('start_sec','end_sec','available_veh','accepted_total_veh','exceedance_veh')
                        if allocation else ('start_sec','end_sec','value_veh','upper_veh'))
        if any(type(row[k]) is not float or math.isnan(row[k]) for k in numeric_keys):return False
        if allocation:
            accepted=row['accepted_by_source_veh']
            if type(accepted) is not dict or any(type(k) is not str or type(v) is not float or math.isnan(v)
                                                for k,v in accepted.items()):return False
        return True

    def unpack(value):
        saved = unpacked.get(id(value))
        if saved is None:
            if type(value) is bytes:
                decoded = pickle.loads(value)
            else:
                from evaluation.controllers.sdmpc_tangent_records import unpack as decode_records
                decoded = decode_records(value)
            saved = (value, decoded)
            unpacked[id(value)] = saved
        return saved[1]

    def numeric(x, y, where):
        xx = x.value if isinstance(x, Dual) else float(x)
        yy = y.value if isinstance(y, Dual) else float(y)
        if xx == yy:
            return 0.
        if not math.isfinite(xx) or not math.isfinite(yy):
            raise ValueError('Nonfinite or mismatched state: '+where)
        return abs(xx-yy)

    def grouped(rows, where):
        groups = defaultdict(lambda: [[], [], []])
        for row in rows:
            if row.keys() != transfer_keys:
                raise ValueError('Unknown transfer schema in state comparison: '+where)
            key = tuple(row[k] for k in identities)
            dest = groups[key]
            for i, name in enumerate(amounts):
                value = row[name]
                dest[i].append(value.value if isinstance(value, Dual) else float(value))
        return {k: tuple(map(math.fsum, v)) for k, v in groups.items()}

    def visit(x, y, where):
        tx, ty = type(x), type(y)
        if (tx in real_types or isinstance(x, Dual)) and (ty in real_types or isinstance(y, Dual)):
            return numeric(x, y, where)
        if tx is str and ty is str:
            if x == y:
                return 0.
            raise ValueError('Mismatched state string: '+where)
        if x is None and y is None:
            return 0.
        if isinstance(x, ModuleType) or callable(x):
            if x is not y:
                raise ValueError('State model-code identity mismatch: '+where)
            return 0.
        # Ledger lists have different semantics from ordinary sequences.
        mode = ('transfers' if where.endswith('.transfers') else
                'packed' if where.endswith('._packed_response_records') else
                'allocations' if fast_records and where.endswith('.resource_allocations') else
                'bounds' if fast_records and where.endswith('.state_bounds') else 'state')
        key = (id(x), id(y), mode)
        old = cache.get(key)
        if old is not None:
            return old[2]
        # An in-progress pair breaks cycles, as in the original object check.
        # Keep references: a later temporary unpacked object may reuse an id.
        cache[key] = (x, y, 0.)
        result = body(x, y, tx, ty, where, mode)
        cache[key] = (x, y, result)
        return result

    def body(x, y, tx, ty, where, mode):
        if isinstance(x, np.ndarray) and isinstance(y, np.ndarray):
            if x.shape != y.shape:
                raise ValueError('State array shape mismatch: '+where)
            if x.dtype.kind in 'biuf' and y.dtype.kind in 'biuf':
                # Same scalar float conversion as the reference comparator.
                xx, yy = x.astype(float, copy=False), y.astype(float, copy=False)
                equal = xx == yy
                if not np.all(equal | (np.isfinite(xx) & np.isfinite(yy))):
                    raise ValueError('Nonfinite or mismatched state: '+where)
                if equal.all():
                    return 0.
                return float(np.max(np.abs(xx[~equal]-yy[~equal])))
            return visit(x.tolist(), y.tolist(), where)
        if isinstance(x, (numbers.Real, Dual)) and isinstance(y, (numbers.Real, Dual)):
            return numeric(x, y, where)
        if isinstance(x, dict) and isinstance(y, dict):
            if x.keys() != y.keys():
                raise ValueError('State keys mismatch: '+where)
            error = 0.
            for k, value in x.items():
                error = max(error, visit(value, y[k], where+'.'+str(k)))
            return error
        if isinstance(x, (tuple, list, deque)) and isinstance(y, tx):
            if mode == 'transfers':
                xx, yy = grouped(x, where), grouped(y, where)
                error = 0.
                for k in xx.keys() | yy.keys():
                    for v, w in zip(xx.get(k, (0., 0., 0.)), yy.get(k, (0., 0., 0.))):
                        error = max(error, numeric(v, w, where+'.route'))
                return error
            if len(x) != len(y):
                raise ValueError(f'State sequence length mismatch: {where}; {len(x)} vs {len(y)}')
            if mode == 'packed':
                if compact_records:
                    error = 0.
                    for i,(v,w) in enumerate(zip(x,y)):
                        cv,cw=compact(v),compact(w)
                        delta=compact_error(cv,cw)
                        if delta is None:
                            delta=visit(unpack(v),unpack(w),where+f'.unpacked[{i}]')
                        else:
                            delta=max(delta,visit(transfer_rows(v),transfer_rows(w),where+f'.unpacked[{i}].transfers'))
                        error=max(error,delta)
                    return error
                return visit([unpack(v) for v in x], [unpack(v) for v in y],
                             where+'.unpacked')
            error = 0.
            for i, (v, w) in enumerate(zip(x, y)):
                if (mode in ('allocations','bounds') and plain_record(v,mode=='allocations')
                        and plain_record(w,mode=='allocations') and v==w):
                    continue
                error = max(error, visit(v, w, where+f'[{i}]'))
            return error
        if hasattr(x, '__dict__') and tx is ty:
            if tx.__name__ == 'ModelAreaLedger' and hasattr(x, '_response'):
                def captured_count(ledger):
                    return len(ledger._response['transfers'])+sum(
                        len(transfer_rows(v))
                        for v in getattr(ledger, '_packed_response_records', ()))
                if x.event_count-captured_count(x) != y.event_count-captured_count(y):
                    raise ValueError('Unexplained ledger event counter mismatch: '+where)
                return visit({k: v for k, v in vars(x).items() if k != 'event_count'},
                             {k: v for k, v in vars(y).items() if k != 'event_count'}, where)
            return visit(vars(x), vars(y), where)
        if hasattr(tx, '__slots__') and tx is ty:
            slots = tx.__slots__
            if isinstance(slots, str):
                slots = (slots,)
            return max((visit(getattr(x, k), getattr(y, k), where+'.'+k)
                        for k in slots), default=0.)
        if x is y or (tx is ty and x == y):
            return 0.
        raise ValueError('Unsupported or mismatched state field: '+where+' '+tx.__name__)

    return visit(a, b, path)
