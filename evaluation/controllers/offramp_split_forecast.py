"""K9-1 F17b: FW_W exit share forecast (K8_PREDECLARATION_AMENDMENT_19 r2 section 2.3; key
freeway.offramp_split_forecast = {"evidence", "evidence_sha256"}, schema k9-offramp-split-forecast/v1).  Not a plant
module: computed at the capture point (runtime_setup, right before lane_plant_runtime.initialize) and applied by
lane_plant_runtime.initialize right before LaneFreewayRuntime is built (LPR:456): observation['off_split_ratio'][o]
(o in E_W) := s_hat_o(T), held over the horizon (the FD3 structure; only the value changes).

Window k = (T - 150 (k + 1), T - 150 k]; off_k / elig_k = the obs150 counts of that window (elig = off + through).
The current window comes from observation['off_split_history']; an earlier window from the previous decision's
obs150/derived_<T'>.json in the same decision bundle directory (obs150_contract.derived_path / resolve; every
earlier decision's observe_state wrote it, warm-up decisions included).  Candidates (evidence 'candidate'):
  C0 k = 0;  C1 k = 0..2;  C2 k = 0..5;  C4 every window ending in (0, T];  sum off / sum elig, 0.0 when sum elig = 0;
  C3 (n s150 + n0 s_prior(j)) / (n + n0), n = elig_0, s150 = C0, j = min(9, floor(T / 900)) (evidence prior).
A window document that is missing, of another run or of another window is a configuration error (ValueError): no
truncated variant.  Key absent: {} and nothing is set."""
from __future__ import annotations

import json

SCHEMA = 'k9-offramp-split-forecast/v1'
CANDIDATES = ('C0', 'C1', 'C2', 'C4', 'C3')
WINDOW = 150


def windows_of(candidate, T):
    """Window end times T' (0 < T' <= T, multiples of 150) a candidate pools (C3: the current window)."""
    T = int(T)
    if T % WINDOW:
        return []
    k = {'C0': 1, 'C3': 1, 'C1': 3, 'C2': 6, 'C4': T // WINDOW}[candidate]
    return [T - WINDOW * i for i in range(k) if T - WINDOW * i > 0]


def window_counts(obs, Tp, exits):
    """{o: (off_veh, eligible_exits_veh)} of the window ending at Tp from the bundle's derived document."""
    from evaluation.controllers import obs150_contract as oc
    path = oc.resolve(obs, oc.derived_path(int(Tp)))
    if not path.is_file():
        raise ValueError('freeway.offramp_split_forecast: window document missing: ' + str(path))
    doc = json.loads(path.read_text(encoding='utf-8'))
    if (doc.get('schema') != oc.DERIVED_SCHEMA or doc.get('sim_sec') != int(Tp) or doc.get('run_id') != obs.get('run_id')
            or doc.get('window') != {'start_s': int(Tp) - WINDOW, 'end_s': int(Tp)}):
        raise ValueError('freeway.offramp_split_forecast: window document of another run or window: ' + str(path))
    out = {}
    for o in exits:
        row = (doc.get('off_split') or {}).get(o)
        if row is None:
            raise ValueError('freeway.offramp_split_forecast: exit %s absent from %s' % (o, path))
        out[o] = (int(row['off_veh']), int(row['eligible_exits_veh']))
    return out


def forecast_values(values, T, current, history):
    """current = {o: (off, elig)} of the window ending at T; history = {T': {o: (off, elig)}} of earlier windows."""
    c = values['candidate']
    ws = windows_of(c, T)
    out, per_exit = {}, {}
    for o in values['exits']:
        o = str(o)
        rows = [(current[o] if Tp == int(T) else history[Tp][o]) for Tp in ws]
        off = sum(a for a, _b in rows)
        elig = sum(b for _a, b in rows)
        if c == 'C3':
            s150 = off / elig if elig else 0.0
            n = elig
            pr = values['prior'][o]
            n0 = float(pr['n0'])
            sp = float(pr['s_prior'][str(min(9, int(T) // 900))])
            s = s150 if n + n0 == 0 else (n * s150 + n0 * sp) / (n + n0)
        else:
            s = off / elig if elig else 0.0
        out[o] = s
        per_exit[o] = {'forecast': s, 'off_sum': off, 'elig_sum': elig, 'n_windows': len(rows)}
    return out, per_exit, ws


def install(cfg, tuning, state_json, observation):
    pin = ((tuning or {}).get('freeway') or {}).get('offramp_split_forecast')
    if pin is None:
        return {}
    from evaluation.controllers.runtime_setup import load_k8b_evidence
    from evaluation.controllers import obs150_contract as oc
    document, digest = load_k8b_evidence(pin, SCHEMA, 'freeway.offramp_split_forecast')
    values = document['values']
    if values.get('candidate') not in CANDIDATES:
        raise ValueError('freeway.offramp_split_forecast: unknown candidate %r' % values.get('candidate'))
    exits = [str(o) for o in values['exits']]
    obs = state_json.get(oc.RAW_STATE_KEY) if isinstance(state_json, dict) else None
    if not isinstance(obs, dict) or observation is None:
        raise ValueError('freeway.offramp_split_forecast needs the obs150 bundle and the lane observation')
    T = int(observation['information_cutoff_s'])
    hist = observation['off_split_history']
    ratio = observation['off_split_ratio']
    if set(exits) - set(hist) or set(exits) - set(ratio):
        raise ValueError('freeway.offramp_split_forecast: exits %s not all observed' % exits)
    current = {o: (int(hist[o]['off_veh']), int(hist[o]['eligible_exits_veh'])) for o in exits}
    history = {}
    for Tp in windows_of(values['candidate'], T):
        if Tp != T:
            history[Tp] = window_counts(obs, Tp, exits)
    forecast, per_exit, ws = forecast_values(values, T, current, history)
    for o in exits:
        per_exit[o]['c0'] = float(ratio[o])
        per_exit[o]['n'] = current[o][1]
        per_exit[o]['current_window'] = list(current[o])
    cfg.network.k9_offramp_split_forecast = dict(forecast)
    return {'k9_f17b': {'candidate': values['candidate'], 'T': T, 'evidence_sha256': digest,
                        'windows_end_s': ([min(ws), max(ws)] if ws else []), 'per_exit': per_exit}}


def apply(observation, forecast):
    """LPR:456 hook: replace the E_W shares the lane freeway runtime holds over the horizon."""
    ratio = observation['off_split_ratio']
    for o, s in forecast.items():
        if o not in ratio:
            raise ValueError('freeway.offramp_split_forecast: exit %s absent from the observation' % o)
        ratio[o] = float(s)
