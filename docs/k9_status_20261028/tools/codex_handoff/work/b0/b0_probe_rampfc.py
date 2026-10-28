# B0 ramp-arrival inspection (configure level, no decision, no VISSIM).  Runs the codex adapter as __main__ unchanged
# up to the end of its configure steps (as b0_probe_main.py 'configure'), then, with the configured cfg, writes
#   - cfg.network.ramps, ramp_to_freeway, on_ramp_to_movement, gate_onramp_queue_ramps, ramp_capacity_veh_h
#   - profiled_demand_rates(state) ramp_arrival under the B0 forecast object (RM_C keys, strict) and under the codex
#     group-key object (both read from the two b0 tunings), with the observed ramp_counts of the state
# to <out.json> and exits 0.  Descriptive only.
# usage: python -B b0_probe_rampfc.py <out.json> <tuning_b0> <tuning_groupkeys> <adapter.py> <adapter args...>
import copy, json, sys, runpy
out_path, tun_b0, tun_gk, adapter = sys.argv[1:5]
rest = sys.argv[5:]
from evaluation.controllers import sdmpc as _sdmpc  # noqa: E402
_orig = _sdmpc.install_cost_ownership


def _arg(name):
    return rest[rest.index(name) + 1]


def _hook(cfg, detector_mapping, *a, **k):
    out = _orig(cfg, detector_mapping, *a, **k)
    A = sys.modules['__main__']  # the running adapter module (runpy run_name='__main__'), with its runtime patches
    state = json.loads(open(_arg('--state-json'), encoding='utf-8').read())
    base_cal = A.load_optional_json(_arg('--calibration-json'))
    net = cfg.network
    res = {'state': _arg('--state-json'), 'sim_sec': state.get('sim_sec'),
           'ramps': list(net.ramps), 'ramp_to_freeway': dict(getattr(net, 'ramp_to_freeway', {})),
           'on_ramp_to_movement': {k: list(v) for k, v in dict(getattr(net, 'on_ramp_to_movement', {}) or {}).items()},
           'gate_onramp_queue_ramps': list(getattr(net, 'gate_onramp_queue_ramps', []) or []),
           'ramp_capacity_veh_h': dict(getattr(net, 'ramp_capacity_veh_h', {})),
           'state_ramp_counts': state.get('ramp_counts'), 'forecast': {}}
    for tag, path in (('b0_rmc_strict', tun_b0), ('codex_groupkeys', tun_gk)):
        tun = json.loads(open(path, encoding='utf-8-sig').read())
        cal = A.deep_update(copy.deepcopy(base_cal), tun.get('calibration_override', {}))
        try:
            fw, ub, ra, prof = A.profiled_demand_rates(state, cfg, cal, detector_mapping)
            res['forecast'][tag] = {'ramp_arrival': {k: float(v) for k, v in ra.items()},
                                    'total_vph': float(sum(ra.values())), 'profile': str(prof)}
        except Exception as exc:  # noqa: BLE001
            res['forecast'][tag] = {'error': type(exc).__name__ + ': ' + str(exc)[:300]}
    json.dump(res, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sys.stdout.write('B0_RAMPFC_DONE' + chr(10))
    sys.stdout.flush()
    raise SystemExit(0)


_sdmpc.install_cost_ownership = _hook
sys.argv = [adapter] + rest
runpy.run_path(adapter, run_name='__main__')
