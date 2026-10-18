"""K9-2 bundle 1 passive plant-job record (K8_PREDECLARATION_AMENDMENT_24 sections 2.0-7, 3.1-3b, 3.3, 5.3, 7).
Stdlib only at import (sa_worker imports it before the tangent finder is installed); numpy is imported lazily when the
series file is written (after the rollout).  Primal reads of the control-area response rows only; every exception is
kept in the record's own 'errors' list (never in the summary): the summary.json leaf set is unchanged (section 2.0-7).

Outputs next to summary.json:
  k92_record.json  schema k92-record/v1: per block k (150 s) the 174-chain model stocks at the block end (the last
                   residence row ending at T0 + 150 k; movement:SC109_W_SC108_to_E, movement:SC109_W_SC108_to_N_SC16,
                   storage:SC108_to_SC109 and their sum), the departures of the two SC109 west movements in the block
                   (transfer rows whose source is movement:<m>), storage:SC109_E_out at the block end and its maximum,
                   OUTW (sum over rows of dt_h x sum_k (model_stock_veh[k] - inside_veh[k]), veh h) and its FEED-4 part,
                   the phantom movement:SC109_N_SC16_to_W_SC108 stock; horizon = first 3 blocks (450 s): the F model
                   sides M1 (chain at T+150 / T+450), M2 / M3 (departures in (T, T+150] / (T, T+450]), SC109_E_out
                   max / 220, the straight-capacity-bound and receiving-limited step counts of SC109_W_SC108_to_E;
                   the VISSIM side is never computed here: 'vissim' = null with reason 'k92_blind_s47' for v3c3-s47
                   (section 3.1-3b) and 'k92_vissim_ref' otherwise (joined by k92_vissim_ref.py outputs).
  k92_series.npz   every residence row: t_end, stage code, the model stock of every ledger key (rows x keys float64,
                   NaN when a key is absent in a row) + the transfer edges (source, target) seen -- read by the
                   G-K1 dynamic classifier (first differing row per key)."""
import json
import math
from array import array
from pathlib import Path

W = 'SC109_W_SC108_to_E'
L = 'SC109_W_SC108_to_N_SC16'
CHAIN = ('movement:SC109_W_SC108_to_E', 'movement:SC109_W_SC108_to_N_SC16', 'storage:SC108_to_SC109')
E_OUT_KEY = 'storage:SC109_E_out'
E_OUT_STORAGE = 220.0
PHANTOM = 'movement:SC109_N_SC16_to_W_SC108'
FEED4 = frozenset(('storage:in_SC1004_S', 'storage:in_SC108_S', 'storage:in_SC16_E', 'storage:in_SC109_E',
                   'movement:SC1004_S_to_E_SC1005', 'movement:SC1004_S_to_E_SC107', 'movement:SC1004_S_to_N_SC1003',
                   'movement:SC1004_S_to_W', 'movement:SC108_S_to_E_SC109', 'movement:SC108_S_to_N_SC7',
                   'movement:SC108_S_to_W', 'movement:SC108_S_to_W_SC107', 'movement:SC16_E_to_N_SC12',
                   'movement:SC16_E_to_S', 'movement:SC16_E_to_S_SC109', 'movement:SC16_E_to_W',
                   'movement:SC16_E_to_W_SC7', 'movement:SC109_E_to_N_SC16', 'movement:SC109_E_to_W_SC108'))
HORIZON_BLOCKS = 3
NAN = float('nan')
STAGES = {}
K92 = {'rows': [], 'keys': {}, 'edges': set(), 'dep': {}, 'errors': [], 'cap': None, 'seed_attr': None,
       'recv_limited': set(), 'responses': 0}


def _f(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    v = getattr(x, 'value', None)
    if v is None:
        v = getattr(x, '_validation_primal', None)
    try:
        return float(v)
    except Exception:  # noqa: BLE001
        return float('nan')


def note(exc):
    if len(K92['errors']) < 50:
        K92['errors'].append(repr(exc)[:400])


def network_facts(cfg):
    """Capacities of the two SC109 west movements and the H-b seed attribute of the rollout network (primal reads)."""
    try:
        caps = getattr(cfg.network, 'movement_capacity_by_movement_veh_h', None) or {}
        K92['cap'] = {W: _f(caps.get(W)), L: _f(caps.get(L))}
        seed = getattr(cfg.network, 'head_floor_seed', None)
        K92['seed_attr'] = ({'|'.join(k): _f(v) for k, v in seed.items()} if isinstance(seed, dict) else None)
    except Exception as exc:  # noqa: BLE001
        note(exc)


def collect(response, T0, dt):
    """Residence rows (all ledger keys, model stock and Omega-inside stock) and transfer rows of one endpoint call."""
    try:
        K92['responses'] += 1
        resp = response or {}
        for row in resp.get('residence') or []:
            if not isinstance(row, dict):
                continue
            mv, iv = row.get('model_stock_veh'), row.get('inside_veh')
            if not isinstance(mv, dict):
                continue
            stage = str(row.get('stage'))
            code = STAGES.setdefault(stage, len(STAGES))
            out_sum = feed = 0.0
            dt_h = _f(row.get('dt_h')) or 0.0
            keys = K92['keys']
            for k in mv:
                if k not in keys:
                    keys[k] = len(keys)
            vals = array('d', [NAN]) * len(keys)
            for k, v in mv.items():
                x = _f(v)
                if x is None:
                    continue
                vals[keys[k]] = x
                if isinstance(iv, dict):
                    a = _f(iv.get(k, 0.0))
                    if a is not None:
                        out_sum += x - a
                        if k in FEED4:
                            feed += x - a
            K92['rows'].append({'start': _f(row.get('start_sec')), 'end': _f(row.get('end_sec')), 'stage': code,
                                'dt_h': dt_h, 'vals': vals, 'outw': dt_h * out_sum, 'feed4': dt_h * feed})
        for row in resp.get('transfers') or []:
            if not isinstance(row, dict):
                continue
            src, tgt = str(row.get('source') or ''), str(row.get('target') or '')
            if src or tgt:
                K92['edges'].add((src, tgt))
            if src in ('movement:' + W, 'movement:' + L):
                end = _f(row.get('end_sec'))
                key = (src[9:], round(end, 6))
                K92['dep'][key] = K92['dep'].get(key, 0.0) + (_f(row.get('vehicles')) or 0.0)
    except Exception as exc:  # noqa: BLE001
        note(exc)


def on_alloc(intended, out, step):
    """_allocate_receiving_counts wrapper hook: SC109_W_SC108_to_E received less than intended at that step."""
    try:
        if W in intended:
            want, got = _f(intended[W]), _f(out.get(W, 0.0))
            if want > 1e-12 and got < want - 1e-9 and step is not None:
                K92['recv_limited'].add(int(step))
    except Exception as exc:  # noqa: BLE001
        note(exc)


def val(row, key):
    i = K92['keys'].get(key)
    if i is None or i >= len(row['vals']):
        return None
    x = row['vals'][i]
    return None if x != x else x


def keyed_of(job):
    """K9-2 metadata keys of the job's template capture record (k92_w / k92_hb present)."""
    try:
        rec = json.loads((Path(job['template']).parent / 'capture.json').read_text(encoding='utf-8'))
    except Exception:  # noqa: BLE001
        return None
    meta = (rec or {}).get('metadata') or {}
    return {k: (k in meta) for k in ('k92_w', 'k92_hb')}


def _block(t, T0, dt):
    return max(1, int(math.ceil((t - T0 - 1e-9) / dt)))


def build(job, T0, dt, H, keyed):
    rows = K92['rows']
    seed = job.get('seed')
    blocks = []
    for k in range(1, int(H) + 1):
        t_end = T0 + dt * k
        last = [r for r in rows if r['end'] is not None and abs(r['end'] - t_end) < 1e-6]
        in_blk = [r for r in rows if r['end'] is not None and T0 + dt * (k - 1) < r['end'] <= t_end + 1e-9]
        end_row = last[-1] if last else None
        chain = {key: (val(end_row, key) if end_row else None) for key in CHAIN}
        dep = {m: math.fsum(v for (mm, t), v in K92['dep'].items() if mm == m and T0 + dt * (k - 1) < t <= t_end + 1e-9)
               for m in (W, L)}
        eo = [x for x in (val(r, E_OUT_KEY) for r in in_blk) if x is not None]
        blocks.append({'k': k, 't_end': t_end, 'chain': chain,
                       'chain_sum': (math.fsum(v for v in chain.values()) if all(v is not None for v in chain.values())
                                     else None),
                       'departures': dep, 'e_out_end': val(end_row, E_OUT_KEY) if end_row else None,
                       'e_out_max': max(eo) if eo else None,
                       'outw_veh_h': math.fsum(r['outw'] for r in in_blk),
                       'feed4_veh_h': math.fsum(r['feed4'] for r in in_blk),
                       'phantom_end': val(end_row, PHANTOM) if end_row else None,
                       'rows': len(in_blk)})
    hb = blocks[:HORIZON_BLOCKS]
    hz_end = T0 + dt * HORIZON_BLOCKS
    hz_rows = [r for r in rows if r['end'] is not None and r['end'] <= hz_end + 1e-9]
    cap_w = (K92['cap'] or {}).get(W)
    dep_w_sec = {}
    for (m, t), v in K92['dep'].items():
        if m == W and t <= hz_end + 1e-9:
            dep_w_sec[t] = dep_w_sec.get(t, 0.0) + v
    bound = (sum(1 for v in dep_w_sec.values() if cap_w and v > 0.0 and v >= cap_w / 3600.0 - 1e-9)
             if cap_w else None)
    eo_hz = [x for x in (val(r, E_OUT_KEY) for r in hz_rows) if x is not None]
    horizon = {
        'blocks': len(hb),
        'm1_chain_T150': hb[0]['chain_sum'] if len(hb) > 0 else None,
        'm1_chain_T450': hb[2]['chain_sum'] if len(hb) > 2 else None,
        'm2_w_dep_T150': hb[0]['departures'][W] if len(hb) > 0 else None,
        'm2_w_dep_T450': math.fsum(b['departures'][W] for b in hb) if len(hb) > 2 else None,
        'm3_l_dep_T150': hb[0]['departures'][L] if len(hb) > 0 else None,
        'm3_l_dep_T450': math.fsum(b['departures'][L] for b in hb) if len(hb) > 2 else None,
        'e_out_max': max(eo_hz) if eo_hz else None,
        'e_out_max_over_220': (max(eo_hz) / E_OUT_STORAGE) if eo_hz else None,
        'outw_veh_h_450': math.fsum(r['outw'] for r in hz_rows),
        'feed4_veh_h_450': math.fsum(r['feed4'] for r in hz_rows),
        'w_capacity_bound_steps': bound, 'w_steps_with_departures': sum(1 for v in dep_w_sec.values() if v > 0.0),
        'w_receiving_limited_steps': sum(1 for s in K92['recv_limited'] if s + 1.0 <= hz_end + 1e-9),
        'phantom_end_450': hb[2]['phantom_end'] if len(hb) > 2 else None}
    blind = seed is not None and int(seed) == 47
    return {'schema': 'k92-record/v1', 'label': job.get('label'), 'harness': job.get('harness'), 'seed': seed,
            'T': job.get('T'), 'H': int(H), 'T0': T0, 'block_sec': dt, 'keyed': keyed, 'capacity': K92['cap'],
            'head_floor_seed_attr': K92['seed_attr'], 'blocks': blocks, 'horizon': horizon,
            'vissim': None, 'vissim_reason': 'k92_blind_s47' if blind else 'k92_vissim_ref',
            'rows': len(rows), 'keys': len(K92['keys']), 'edges': len(K92['edges']), 'responses': K92['responses'],
            'stages': dict(STAGES), 'errors': list(K92['errors'])}


def write(folder, job, T0, dt, H, keyed):
    folder = Path(folder)
    try:
        rec = build(job, T0, dt, H, keyed)
    except Exception as exc:  # noqa: BLE001
        note(exc)
        rec = {'schema': 'k92-record/v1', 'label': job.get('label'), 'errors': list(K92['errors']),
               'vissim': None, 'vissim_reason': 'k92_blind_s47' if str(job.get('seed')) == '47' else 'k92_vissim_ref'}
    try:
        import numpy as np
        keys = sorted(K92['keys'])
        col = [K92['keys'][k] for k in keys]
        arr = np.full((len(K92['rows']), len(keys)), np.nan)
        for i, r in enumerate(K92['rows']):
            row = np.frombuffer(r['vals'], dtype=np.float64)
            pad = np.full(len(K92['keys']), np.nan)
            pad[:len(row)] = row
            arr[i, :] = pad[col]
        edges = sorted(K92['edges'])
        np.savez_compressed(folder / 'k92_series.npz', keys=np.array(keys, dtype=object),
                            t_end=np.array([r['end'] for r in K92['rows']], dtype=float),
                            stage=np.array([r['stage'] for r in K92['rows']], dtype=np.int16), model=arr,
                            edges=np.array(edges, dtype=object).reshape(-1, 2),
                            stage_names=np.array(sorted(STAGES, key=STAGES.get), dtype=object))
        rec['series_file'] = 'k92_series.npz'
    except Exception as exc:  # noqa: BLE001
        note(exc)
        rec['errors'] = list(K92['errors'])
    (folder / 'k92_record.json').write_text(json.dumps(rec, indent=1, default=repr), encoding='utf-8')
    return rec
