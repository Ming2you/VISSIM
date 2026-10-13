"""Actuator ablation only; keep all traffic states and Omega cost owners."""
import copy
import math

def configure(spec, cfg):
    if spec is None:
        return None
    if not isinstance(spec, dict) or set(spec) != {'mode', 'baseline'}:
        raise ValueError('Actuator scope requires mode and baseline')
    mode = spec['mode']
    expected = {'green_times', 'offsets'} if mode == 'freeway_only' else {'meter_green_sec', 'vsl_kmh'}
    if mode not in ('freeway_only', 'urban_only') or set(spec['baseline']) != expected:
        raise ValueError('Unknown or incomplete actuator scope')
    base = spec['baseline']
    if mode == 'freeway_only':
        if (set(base['offsets']) != set(cfg.network.signals)
                or set(base['green_times']) != {s+'_'+p for s in cfg.network.signals for p in ('p1','p2','p3','p4')}):
            raise ValueError('Fixed urban baseline must cover all controlled signals')
        for mapping in base.values():
            if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in mapping.values()):
                raise ValueError('Invalid fixed urban command')
    elif base != {'meter_green_sec': 10, 'vsl_kmh': 110}:
        raise ValueError('Urban-only baseline is native OPEN meters and DSD110')
    return copy.deepcopy(spec)

def allows(options, kind):
    spec = options.get('actuator_scope')
    return spec is None or ((kind in ('meter','vsl')) == (spec['mode']=='freeway_only'))

def check(control, options, cfg):
    spec = options.get('actuator_scope')
    if spec is None:
        return
    base = spec['baseline']
    if spec['mode']=='freeway_only':
        for field in ('green_times','offsets'):
            actual = getattr(control, field)
            if any(abs(float(actual[k])-v)>1e-9 for k,v in base[field].items()):
                raise ValueError('Inactive urban actuator changed: '+field)
    else:
        if any(control.diagnostics['rw_meter_green_'+r]!=base['meter_green_sec'] for r in cfg.network.ramps):
            raise ValueError('Inactive RM must remain native OPEN')
        if not control.vsl or any(v!=base['vsl_kmh'] for v in control.vsl.values()):
            raise ValueError('Inactive VSL must remain110')
