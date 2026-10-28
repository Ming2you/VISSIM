# A0 per-decision wall-time breakdown for every replay on this PC and the codex-PC record.
# Sources (read only): action_T.joint.progress.jsonl (stage clock), action_T.decision_budget.json,
# action_T.joint.json (physical_response_cache rows, selection.tangent_derivatives, meter_neighbor_audit),
# cpu_load.csv (typeperf samples of this PC during the replay).
# usage: s22_profile_all.py out.json
import csv, glob, json, os, statistics, sys

A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
DEC = 'decisions_sdmpc31_sdmpc8100_s29'
REC = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/' + DEC


def load(p):
    return json.loads(open(p, 'rb').read().decode('utf-8-sig'))


def stages(d, t6):
    rows = [json.loads(l) for l in open(d + '/action_' + t6 + '.joint.progress.jsonl', encoding='utf-8')]
    res = {'pfo_sec': None, 'pfo_predictions': 0, 'caps': [], 'neighbor': None}
    cur = None
    region = 'pre'
    sec_start = None
    nb = None
    prev_e = 0.0
    for r in rows:
        s, e = r['stage'], r.get('elapsed_sec', 0.0)
        if s == 'sdmpc_pfo_start':
            res['pre_joint_sec'] = round(e, 3); region = 'pfo'
        elif s == 'sdmpc_pfo_done':
            res['pfo_sec'] = round(r.get('seconds', 0.0), 3); region = 'between'
        elif s == 'sdmpc_candidate_start':
            if cur is not None:
                cur['wall_sec'] = round(e - cur['_t0'], 3); res['caps'].append(cur)
            cur = {'_t0': e, 'np_cap': r.get('np_cap'), 'nuf': r.get('nuf'), 'derivatives_reused': False,
                   'tangent_sec': 0.0, 'tangents': 0, 'secant_sec': 0.0, 'secant_evaluations': 0,
                   'step_batch_sec': 0.0, 'step_predictions': 0}
            region = 'cap'
        elif s == 'sdmpc_meter_neighbors_start':
            if cur is not None:
                cur['wall_sec'] = round(e - cur['_t0'], 3); res['caps'].append(cur); cur = None
            nb = {'_t0': e, 'predictions': 0, 'batches': 0}; region = 'nb'
        elif s == 'sdmpc_meter_neighbors_done':
            nb['wall_sec'] = round(e - nb['_t0'], 3)
            nb['additional_predictions'] = r.get('additional_predictions')
            nb['selected'] = r.get('selected')
        elif s == 'sdmpc_completed':
            if cur is not None:
                cur['wall_sec'] = round(e - cur['_t0'], 3); res['caps'].append(cur); cur = None
            res['joint_end_sec'] = round(e, 3)
        if region == 'pfo' and s == 'sdmpc_surrogate_batch_start':
            res['pfo_predictions'] += r.get('predictions', 0)
        if region == 'cap' and cur is not None:
            if s == 'sdmpc_derivatives_reused':
                cur['derivatives_reused'] = True
            elif s == 'sdmpc_tangent_done':
                cur['tangent_sec'] += r.get('seconds', 0.0); cur['tangents'] += 1
            elif s == 'sdmpc_derivatives_start':
                sec_start = e; cur['secant_evaluations'] += r.get('evaluations', 0)
            elif s == 'sdmpc_derivatives_done' and sec_start is not None:
                cur['secant_sec'] += e - sec_start; sec_start = None
            elif s == 'sdmpc_surrogate_batch_start' and sec_start is None:
                cur['step_predictions'] += r.get('predictions', 0)
            elif s == 'sdmpc_surrogate_batch_done' and sec_start is None:
                cur['step_batch_sec'] += r.get('seconds', 0.0)
        if region == 'nb' and nb is not None and s == 'sdmpc_surrogate_batch_start':
            nb['predictions'] += r.get('predictions', 0); nb['batches'] += 1
        prev_e = e
    els = [r.get('elapsed_sec', 0.0) for r in rows]
    gaps = [b - a for a, b in zip(els, els[1:])]
    res['max_progress_gap_sec'] = round(max(gaps), 3) if gaps else None
    res['first_progress_elapsed_sec'] = round(els[0], 3) if els else None
    for c in res['caps']:
        c.pop('_t0', None)
        for k in ('tangent_sec', 'secant_sec', 'step_batch_sec'):
            c[k] = round(c[k], 3)
        c['unlogged_sec'] = round(c['wall_sec'] - c['secant_sec'] - c['step_batch_sec'], 3)
    if nb is not None:
        nb.pop('_t0', None)
    res['neighbor'] = nb
    return res


def joint_parts(d, t6):
    j = load(d + '/action_' + t6 + '.joint.json')
    prc = j.get('physical_response_cache', {})
    rows = prc.get('rows', [])
    sc = [r['wall_sec'] for r in rows if r.get('scalar_rollouts')]
    tg = [r['wall_sec'] for r in rows if r.get('tangent_rollouts')]
    sel = j.get('selection', {})
    td = sel.get('tangent_derivatives', []) or []
    out = {
        'requests': prc.get('requests'), 'cache_hits': prc.get('cache_hits'),
        'scalar_rollouts': len(sc), 'scalar_rollout_sum_sec': round(sum(sc), 3),
        'scalar_rollout_median_sec': round(statistics.median(sc), 3) if sc else None,
        'tangent_rollouts': len(tg), 'tangent_rollout_sum_sec': round(sum(tg), 3),
        'tangent_rollout_median_sec': round(statistics.median(tg), 3) if tg else None,
        'tangent_derivatives': [{'tangent_sec': round(t.get('tangent_sec', 0.0), 3), 'reverse_sec': round(t.get('reverse_sec', 0.0), 3),
                                 'wall_incl_spawn_sec': round(t.get('wall_sec_including_spawn', 0.0), 3)} for t in td],
        'sdmpc_after_pfo_seconds': sel.get('sdmpc_after_pfo_seconds'),
        'sdmpc_after_pfo_rollouts': sel.get('sdmpc_after_pfo_rollouts'),
        'leader_objective': j.get('leader_objective'),
    }
    gm = {}
    for r in sel.get('gradient_rows', []) or []:
        k = (r.get('kind'), r.get('derivative_method'))
        gm[str(k)] = gm.get(str(k), 0) + 1
    out['gradient_rows_by_kind_method'] = gm
    del j
    return out


def cpu_load(d):
    p = os.path.dirname(os.path.dirname(os.path.dirname(d))) + '/cpu_load.csv'
    if not os.path.exists(p):
        return None
    vals, q = [], []
    with open(p, encoding='utf-8', errors='replace') as f:
        rd = csv.reader(f)
        next(rd, None)
        for row in rd:
            try:
                vals.append(float(row[1])); q.append(float(row[2]))
            except (ValueError, IndexError):
                pass
    if not vals:
        return None
    return {'samples': len(vals), 'cpu_total_pct_mean': round(statistics.mean(vals), 1),
            'cpu_total_pct_median': round(statistics.median(vals), 1), 'queue_len_mean': round(statistics.mean(q), 2)}


def profile(d, T, label):
    t6 = '%06d' % T
    b = load(d + '/action_' + t6 + '.decision_budget.json')
    row = {'label': label, 'T': T, 'budget_wall_sec': round(b['wall_sec'], 3), 'main_cpu_sec': b.get('cpu_sec'),
           'load_and_model_prepare_sec': round(b['inclusive_scopes']['load_and_model_prepare']['wall_sec'], 3),
           'final_output_sec': round(b['inclusive_scopes']['final_action_validation_and_output']['wall_sec'], 3)}
    row.update(stages(d, t6))
    row['outside_joint_sec'] = round(row['budget_wall_sec'] - row.get('joint_end_sec', 0.0), 3)
    row.update(joint_parts(d, t6))
    if label != 'recorded':
        row['cpu_load'] = cpu_load(d)
        st = load(os.path.dirname(os.path.dirname(os.path.dirname(d))) + '/replay_state.json')
        row['process_wall_sec'] = st.get('wall_sec')
        row['extra_env'] = st.get('extra_env')
    return row


items = []
for T in (900, 2700, 4950):
    items.append(('recorded', T, REC))
for st in sorted(glob.glob(A0 + '/out/*/T*/replay_state.json')):
    dd = os.path.dirname(st).replace('\\', '/')
    label, T = dd.split('/')[-2], int(dd[-6:])
    f = dd + '/files/sdmpc/' + DEC
    if os.path.exists(f + '/action_%06d.joint.progress.jsonl' % T) and os.path.exists(f + '/action_%06d.decision_budget.json' % T):
        items.append((label, T, f))
res = []
for label, T, d in items:
    try:
        res.append(profile(d, T, label))
    except Exception as e:
        res.append({'label': label, 'T': T, 'error': repr(e)})
    print(label, T, 'done', flush=True)
json.dump(res, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
