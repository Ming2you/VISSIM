"""Immutable completed audit records; no traffic state or record is omitted.

The ledger owns append-only records. Freeze their containers once; snapshot
copies share the immutable block. Export always recreates independent mutable
containers in the same order and original list/tuple/dict types.
"""
from dataclasses import dataclass
from evaluation.controllers.sdmpc_dual import Dual


@dataclass(frozen=True, slots=True)
class FrozenRecords:
    kind: str
    entries: tuple

    def __deepcopy__(self, memo):
        return self

    def thaw(self):
        if self.kind == 'dict':
            return {key: thaw(value) for key, value in self.entries}
        if self.kind == 'list':
            return [thaw(v) for v in self.entries]
        if self.kind == 'tuple':
            return tuple(thaw(v) for v in self.entries)
        raise ValueError('Unknown immutable audit container')


def freeze(value):
    if type(value) in (type(None), bool, int, float, str, bytes) or isinstance(value, Dual):
        return value
    if type(value) is dict:
        if any(type(k) is not str for k in value):
            raise TypeError('Audit records require plain string keys')
        return FrozenRecords('dict', tuple((k, freeze(v)) for k, v in value.items()))
    if type(value) is list:
        return FrozenRecords('list', tuple(freeze(v) for v in value))
    if type(value) is tuple:
        return FrozenRecords('tuple', tuple(freeze(v) for v in value))
    raise TypeError('Unsupported mutable audit value: '+type(value).__name__)


def thaw(value):
    return value.thaw() if isinstance(value, FrozenRecords) else value


def unpack(value):
    from evaluation.controllers.sdmpc_tangent_audit import AuditBlock
    if type(value) is AuditBlock:
        return value.unpack()
    if isinstance(value, FrozenRecords):
        return value.thaw()
    if type(value) is bytes:
        import pickle
        return pickle.loads(value)
    raise TypeError('Unknown packed audit record representation')
