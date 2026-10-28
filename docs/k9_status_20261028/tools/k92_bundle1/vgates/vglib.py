"""VerifyGates own helpers (no harness import).  Stub unpickler, JSON leaves, sha, long paths."""
import hashlib
import json
import os
import pickle
import sys

ALLOWED_REAL = ('builtins', 'collections', 'copyreg', 'numpy', 'numpy.core.multiarray', 'numpy._core.multiarray',
                'numpy.core.numeric', 'numpy._core.numeric', 'datetime', 'decimal', 'fractions', '_codecs',
                'pathlib', 'enum')


def lp(p):
    s = os.path.abspath(str(p))
    return s if s.startswith('\\\\?\\') else '\\\\?\\' + s


def sha_file(p):
    h = hashlib.sha256()
    with open(lp(p), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def rjson(p, default=None):
    try:
        with open(lp(p), 'rb') as f:
            return json.loads(f.read().decode('utf-8-sig'))
    except (OSError, ValueError):
        return default


def wjson(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, allow_nan=True, default=repr)
        f.write('\n')


def canon(x):
    return json.dumps(x, sort_keys=True, allow_nan=True, default=repr)


# ------------------------------------------------------------------ stub unpickler
class Stub(object):
    """Generic stand-in for a project class: keeps constructor args and state."""
    _vg_name = 'Stub'

    def __init__(self, *a, **k):
        self._vg_args = a
        self._vg_kw = k

    def __setstate__(self, state):
        if isinstance(state, tuple) and len(state) == 2 and (state[0] is None or isinstance(state[0], dict)):
            d, slots = state
            if d:
                self.__dict__.update(d)
            if slots:
                self.__dict__.update(slots)
        elif isinstance(state, dict):
            self.__dict__.update(state)
        else:
            self.__dict__['_vg_state'] = state

    def __repr__(self):
        return '<%s %s>' % (self._vg_name, sorted(k for k in self.__dict__)[:8])


_STUBS = {}


def stub_class(module, name):
    key = (module, name)
    if key not in _STUBS:
        _STUBS[key] = type(str(name), (Stub,), {'_vg_name': '%s.%s' % (module, name), '__module__': 'vgstub'})
    return _STUBS[key]


class StubUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.split('.')[0] in ('builtins', 'collections', 'copyreg', 'numpy', 'datetime', 'decimal',
                                    'fractions', '_codecs', 'pathlib'):
            return super().find_class(module, name)
        if module == 'enum':
            return super().find_class(module, name)
        return stub_class(module, name)


def load_stub(p):
    with open(lp(p), 'rb') as f:
        return StubUnpickler(f).load()


def attr(o, name):
    if isinstance(o, dict):
        return o[name]
    d = getattr(o, '__dict__', {})
    if name in d:
        return d[name]
    return getattr(o, name)


def num(v):
    """float of a capacity value (float, numpy scalar or a stub with .value)."""
    if v is None:
        return None
    if isinstance(v, Stub):
        d = v.__dict__
        if 'value' in d:
            return num(d['value'])
        if '_vg_args' in d and d['_vg_args']:
            return num(d['_vg_args'][0])
        raise ValueError('stub without value: %r' % v)
    return float(v)


def template_caps(p):
    """cfg.network.movement_capacity_by_movement_veh_h of owned[0] in a capture template.pickle (stub load)."""
    t = load_stub(p)
    owned = attr(t, 'owned')
    o0 = owned[0]
    cfg = attr(o0, 'cfg')
    net = attr(cfg, 'network')
    caps = attr(net, 'movement_capacity_by_movement_veh_h')
    if not isinstance(caps, dict):
        caps = dict(caps)
    return {str(k): num(v) for k, v in caps.items()}


# ------------------------------------------------------------------ JSON leaves
def leaves(x, path=''):
    """{path: leaf} for dict / list trees; list index as [i]."""
    out = {}
    if isinstance(x, dict):
        if not x:
            out[path + '/{}'] = '{}'
        for k, v in x.items():
            out.update(leaves(v, path + '/' + str(k)))
    elif isinstance(x, list):
        if not x:
            out[path + '/[]'] = '[]'
        for i, v in enumerate(x):
            out.update(leaves(v, '%s[%d]' % (path, i)))
    else:
        out[path] = x
    return out


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def same_num(a, b):
    if isinstance(a, float) and isinstance(b, float) and a != a and b != b:
        return True
    return a == b and type(a) is type(b) or (is_num(a) and is_num(b) and repr(float(a)) == repr(float(b))
                                             and type(a) is type(b))
