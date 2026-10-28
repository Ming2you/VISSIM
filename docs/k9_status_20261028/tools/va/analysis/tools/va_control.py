r"""V-A analysis step 4 (amendment 34 sec.8.3-4 SC109 p3, 8.3-5 (173,p4) floor and seed, 8.3-7 meters and VSL,
8.3-8 holds and "previous plan kept" (D-K9-69), 8.3-9 decision wall clock; J1 an_control.py form).
python -B va_control.py --profile va|selftest  ->  <out>/va_control.json
Per seed, the V-A run and the same-seed J1 run side by side.  Reads (read-only, after the runs ended): runlog, launch
log, runner action log CSV, action_<T>.json (61 per run), hold receipts action_<T>.hold.json, and the V-A / J1 stage-1
scan (zone veh_km for VSL exposure).  Objective values appear only as "plant 모형 값" (selected / held objective of
the leader selection, as J1).  BELOW_NORMAL.
Definitions (fixed before data):
  SDMPC decisions = T >= 900; warm-up = T < 900.  hold T = receipt action_<T>.hold.json or metadata key
  hold_previous_on_exception present.
  previous plan kept (sec.8.3-8 ii): SDMPC T >= 1050, not hold, and (ga) green_times and offsets equal (JSON values,
  ==) to the T-150 action JSON, (na) diagnostics.sdmpc_prediction_sequence absent, (da) repr(selected_objective) ==
  repr(held_objective) in metadata.joint_leader_selection.
  SC109 p3: green_times['SC109_p3'] <= 24.5 s over SDMPC decisions; count, first T, longest run of consecutive
  decisions (T step 150); p2/p3/p4 mean and max over all SDMPC decisions and over T >= 4350.
  (173,p4) floor: metadata keys head_discharge_floor_173_p4_<16 hex>; names (one per run?), first value, max, T where
  the value fell versus the previous decision (T after a hold listed apart), k92_hb_seed_binding == 1.0 count,
  head_observation_groups_carried / _updated sums, head_observation_prior_discarded == 1.0 T list, k92_w / k92_hb
  present counts.  Meter command changed = ramp_metering dict differs from the previous decision's."""
import csv
import json
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

HEADS = {'FW_E': ['FW_E__seg0', 'FW_E__seg5', 'FW_E__seg10', 'FW_E__seg15'],
         'FW_W': ['FW_W__seg0', 'FW_W__seg5', 'FW_W__seg10', 'FW_W__seg15']}
FLOOR_RE = re.compile(r'^head_discharge_floor_173_p4_[0-9a-f]{16}$')
DIGITS = re.compile(r'\d+(?:\.\d+)?')


def rd(p):
    with open(p, encoding='utf-8-sig', errors='replace') as f:
        return f.read()


def vget(v, k, road):
    x = v.get(k, v.get(road))
    return None if x is None else float(x)


def desc(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {'n': 0}
    s = sorted(xs)
    return {'n': len(s), 'min': s[0], 'median': statistics.median(s), 'mean': statistics.fmean(s), 'max': s[-1],
            'sum': sum(s)}


def longest_run(Ts, hits):
    best = cur = 0
    prev = None
    for T in Ts:
        if T in hits:
            cur = cur + 1 if (prev is not None and T - prev == 150 and prev in hits) else 1
            best = max(best, cur)
        prev = T
    return best


def num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def run(seed, info, scan_path):
    name = info['name']
    out = {'name': name}
    lines = rd(info['runlog']).splitlines()
    kv = {}
    for l in lines:
        m = re.match(r'^([A-Z0-9_]+)=(\S*)$', l)
        if m:
            kv.setdefault(m.group(1), []).append(m.group(2))
    out['runlog_counters'] = {k: kv.get(k) for k in ('DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_ON_EXCEPTION',
                                                    'DECISION_ERROR_POLICY', 'STAGE', 'SIM_SEC')}
    out['runlog_hold_lines'] = {k: sum(1 for l in lines if l.startswith(k)) for k in
                                ('DECISION_HOLD_ATTEMPT', 'DECISION_HELD_ON_EXCEPTION ', 'DECISION_HOLD_FAILED')}
    out['runlog_error_lines'] = sum(1 for l in lines if l.startswith('ERROR='))
    cd = {}
    for l in lines:
        m = re.match(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)', l)
        if m:
            cd[int(m.group(1))] = (float(m.group(2)), int(m.group(3)))
    launch = rd(info['launch']).splitlines()
    out['launch_exit'] = [l.strip() for l in launch if re.search(r'\bEXIT %s code=' % re.escape(name), l)]
    out['watchdog_exit'] = [l.strip() for l in launch if 'WATCHDOG_EXIT' in l]
    wx = [re.search(r'wall_sec=([0-9.]+)', l) for l in out['watchdog_exit']]
    out['run_wall_sec'] = float(wx[-1].group(1)) if wx and wx[-1] else None
    files = V.action_files(info['dec'])
    Ts = [T for T, _ in files]
    out['n_action_json'] = len(Ts)
    sd_T = [T for T in Ts if T >= 900]
    wu_T = [T for T in Ts if T < 900]
    out['warmup_T'] = wu_T
    out['exit_codes'] = dict(Counter(cd[T][1] for T in Ts if T in cd))
    out['wall_warmup'] = desc([cd[T][0] for T in wu_T if T in cd])
    out['wall_sdmpc'] = desc([cd[T][0] for T in sd_T if T in cd])
    out['wall_sdmpc_gt900_T'] = [T for T in sd_T if T in cd and cd[T][0] > 900]
    # hold receipts
    holds = {}
    for T in Ts:
        hp = os.path.join(info['dec'], 'action_%06d.hold.json' % T)
        if os.path.isfile(hp):
            h = V.load_json_bytes(hp)
            ex = h.get('exception') or {}
            hm = h.get('hold_previous_on_exception') or {}
            holds[T] = {'type': ex.get('type'), 'root_type': ex.get('root_type'),
                        'message_masked': DIGITS.sub('#', str(ex.get('message_first_line', '')))[:160],
                        'chain_length': hm.get('chain_length'), 'source_sim_sec': hm.get('source_sim_sec'),
                        'origin_sim_sec': hm.get('origin_sim_sec')}
    per = {}
    prev_doc = None
    for T, p in files:
        d = V.load_json_bytes(p)
        md = d.get('metadata') or {}
        r = {'vsl': {}, 'fut1': {}, 'fut2': {}}
        v = d.get('vsl') or {}
        for road, ks in HEADS.items():
            for k in ks:
                r['vsl'][k] = vget(v, k, road)
        seq = (d.get('diagnostics') or {}).get('sdmpc_prediction_sequence')
        r['has_pred_seq'] = seq is not None
        fut = (seq or {}).get('future') or []
        for i, key in ((0, 'fut1'), (1, 'fut2')):
            if i < len(fut):
                fv = fut[i].get('vsl') or {}
                for road, ks in HEADS.items():
                    for k in ks:
                        r[key][k] = vget(fv, k, road)
        r['ramp_metering'] = {k: float(x) for k, x in (d.get('ramp_metering') or {}).items()}
        gt = d.get('green_times') or {}
        r['sc109'] = {ph: num(gt.get('SC109_' + ph)) for ph in ('p1', 'p2', 'p3', 'p4')}
        jl = md.get('joint_leader_selection') if isinstance(md.get('joint_leader_selection'), dict) else {}
        r['selected_objective'] = jl.get('selected_objective')
        r['held_objective'] = jl.get('held_objective')
        r['sel_eq_held_repr'] = ('selected_objective' in jl and 'held_objective' in jl and
                                 repr(jl.get('selected_objective')) == repr(jl.get('held_objective')))
        r['selection_status'] = jl.get('selection_status')
        r['converged'] = jl.get('converged')
        r['feasible'] = jl.get('feasible')
        r['sdmpc_active'] = md.get('sdmpc_active')
        r['controller_status'] = md.get('controller_status') if isinstance(md.get('controller_status'), str) else None
        ic = md.get('stopline_approach_install_check')
        r['install_passed'] = ic.get('passed') if isinstance(ic, dict) else None
        r['install_seeded'] = ic.get('seeded_links') if isinstance(ic, dict) else None
        r['k9'] = {k: (k in md) for k in ('k9_w1', 'k9_w2a', 'k9_f17b')}
        r['k92'] = {k: (k in md) for k in ('k92_w', 'k92_hb', 'k92_hb_seed_binding')}
        r['k92_binding'] = md.get('k92_hb_seed_binding')
        r['floor'] = {k: md[k] for k in md if FLOOR_RE.match(k)}
        r['groups_carried'] = num(md.get('head_observation_groups_carried'))
        r['groups_updated'] = num(md.get('head_observation_groups_updated'))
        r['prior_discarded'] = md.get('head_observation_prior_discarded')
        r['hold'] = (T in holds) or ('hold_previous_on_exception' in md)
        if prev_doc is not None and prev_doc[0] == T - 150:
            r['same_green_offsets_as_prev'] = (d.get('green_times') == prev_doc[1].get('green_times') and
                                               d.get('offsets') == prev_doc[1].get('offsets'))
            r['meter_changed_vs_prev'] = r['ramp_metering'] != per[prev_doc[0]]['ramp_metering']
        else:
            r['same_green_offsets_as_prev'] = None
            r['meter_changed_vs_prev'] = None
        per[T] = r
        prev_doc = (T, {'green_times': d.get('green_times'), 'offsets': d.get('offsets')})
        del d, md, jl
    # (i) holds
    out['holds'] = {'count': len([T for T in Ts if per[T]['hold']]), 'T': [T for T in Ts if per[T]['hold']],
                    'receipts': {str(T): h for T, h in holds.items()}}
    # (ii) previous plan kept
    cand = [T for T in sd_T if T >= 1050 and not per[T]['hold']]
    ga = [T for T in cand if per[T]['same_green_offsets_as_prev'] is True]
    na = [T for T in cand if not per[T]['has_pred_seq']]
    da = [T for T in cand if per[T]['sel_eq_held_repr']]
    allc = [T for T in cand if T in ga and T in na and T in da]
    out['previous_plan_kept'] = {'candidates': len(cand), 'ga_same_green_offsets': len(ga), 'na_no_prediction_sequence': len(na),
                                 'da_selected_repr_eq_held': len(da), 'all_three': len(allc), 'all_three_T': allc,
                                 'ga_T': ga, 'na_T': na,
                                 'selection_status_all_three': dict(Counter(str(per[T]['selection_status']) for T in allc))}
    # SC109 p3
    p3hit = [T for T in sd_T if per[T]['sc109']['p3'] is not None and per[T]['sc109']['p3'] <= V.P3_THRESHOLD]
    out['sc109_p3'] = {'n_sdmpc': len(sd_T), 'le_24_5_count': len(p3hit), 'le_24_5_T': p3hit,
                       'first_T': p3hit[0] if p3hit else None, 'longest_run': longest_run(sd_T, set(p3hit))}
    for ph in ('p2', 'p3', 'p4'):
        out['sc109_p3'][ph] = {'all': desc([per[T]['sc109'][ph] for T in sd_T]),
                               'T_ge_4350': desc([per[T]['sc109'][ph] for T in sd_T if T >= 4350])}
    # (173,p4) floor and seed
    names = Counter()
    for T in Ts:
        for k in per[T]['floor']:
            names[k] += 1
    fl = []
    for T in Ts:
        vals = list(per[T]['floor'].values())
        fl.append((T, float(vals[0]) if len(vals) == 1 and num(vals[0]) is not None else None))
    present = [(T, x) for T, x in fl if x is not None]
    fell, fell_after_hold = [], []
    for (Ta, xa), (Tb, xb) in zip(present, present[1:]):
        if xb < xa:
            hold_between = any(per[T]['hold'] for T in Ts if Ta <= T < Tb)
            (fell_after_hold if hold_between else fell).append(Tb)
    out['floor_173_p4'] = {'names': dict(names), 'one_name_per_run': len(names) == 1,
                           'decisions_with_key': sum(1 for T in Ts if per[T]['floor']),
                           'decisions_with_more_than_one': sum(1 for T in Ts if len(per[T]['floor']) > 1),
                           'first_T': present[0][0] if present else None, 'first_value': present[0][1] if present else None,
                           'max': max(x for _, x in present) if present else None,
                           'fell_T': fell, 'fell_T_after_hold': fell_after_hold,
                           'seed_binding_eq_1_count': sum(1 for T in Ts if isinstance(per[T]['k92_binding'], float)
                                                           and per[T]['k92_binding'] == 1.0),
                           'seed_binding_eq_1_T': [T for T in Ts if isinstance(per[T]['k92_binding'], float)
                                                   and per[T]['k92_binding'] == 1.0],
                           'groups_carried_sum': sum(per[T]['groups_carried'] or 0.0 for T in Ts),
                           'groups_updated_sum': sum(per[T]['groups_updated'] or 0.0 for T in Ts),
                           'prior_discarded_eq_1_T': [T for T in Ts if per[T]['prior_discarded'] == 1.0],
                           'k92_present': {k: sum(1 for T in Ts if per[T]['k92'][k]) for k in ('k92_w', 'k92_hb',
                                                                                          'k92_hb_seed_binding')}}
    # VSL selection statistics (K7 sec.3.5, J1 form)
    vs = {}
    for road, ks in HEADS.items():
        dist = {k: dict(Counter('%g' % per[T]['vsl'][k] for T in sd_T)) for k in ks}
        any_lt = [T for T in sd_T if any((per[T]['vsl'][k] or 110) < 110 for k in ks)]
        trans = Counter()
        for a, b in zip(sd_T, sd_T[1:]):
            for k in ks:
                trans[('%g' % per[a]['vsl'][k], '%g' % per[b]['vsl'][k])] += 1
        fut = {}
        for key in ('fut1', 'fut2'):
            fut[key] = {k: dict(Counter('%g' % per[T][key][k] for T in sd_T if per[T][key].get(k) is not None)) for k in ks}
            fut[key]['any_lt110_T'] = [T for T in sd_T if any((per[T][key].get(k) or 110) < 110 for k in ks)]
        vs[road] = {'dist_by_head': dist, 'any_lt110_T': any_lt, 'frac_any_lt110': len(any_lt) / len(sd_T) if sd_T else None,
                    'first_T': any_lt[0] if any_lt else None, 'longest_run_decisions': longest_run(sd_T, set(any_lt)),
                    'transitions': {'%s->%s' % k: n for k, n in sorted(trans.items())}, 'future_blocks': fut}
    vs['n_with_future_blocks'] = sum(1 for T in sd_T if per[T]['has_pred_seq'])
    lt = [T for T in sd_T if any((per[T]['vsl'][k] or 110) < 110 for ks in HEADS.values() for k in ks)]
    eq = [T for T in sd_T if T not in lt]

    def objs(Tl):
        return {'n': len(Tl), 'selected_objective': desc([per[T]['selected_objective'] for T in Tl]),
                'held_objective': desc([per[T]['held_objective'] for T in Tl]),
                'selected_minus_held': desc([per[T]['selected_objective'] - per[T]['held_objective'] for T in Tl
                                             if per[T]['selected_objective'] is not None and per[T]['held_objective'] is not None]),
                'note': 'plant 모형 값 (VISSIM 결과 아님)'}
    vs['objective_lt110_decisions'] = objs(lt)
    vs['objective_110_decisions'] = objs(eq)
    sc = V.jload(scan_path)
    zones = sc['speed']['zones']
    nb = sc['n_bins']
    expo = defaultdict(float)
    cells = []
    for T in sd_T:
        b = T // 150
        if b >= nb:
            continue
        for road, ks in HEADS.items():
            for k in ks:
                m = per[T]['vsl'][k]
                if m is not None and m < 110:
                    x = zones[k]['veh_km'][b]
                    expo['%s|%g' % (road, m)] += x
                    cells.append({'T': T, 'zone': k, 'm': m, 'veh_km': x})
    vs['exposure_veh_km'] = dict(expo)
    vs['exposure_cells'] = cells
    vs['zone_total_veh_km'] = {k: sum(zones[k]['veh_km']) for ks in HEADS.values() for k in ks}
    out['vsl_stats'] = vs
    # meters
    out['meter_json_values'] = {m: dict(Counter('%g' % per[T]['ramp_metering'].get(m) for T in Ts if m in per[T]['ramp_metering']))
                                for m in sorted({m for T in Ts for m in per[T]['ramp_metering']})}
    out['meter_command_changed_decisions'] = sum(1 for T in Ts if per[T]['meter_changed_vs_prev'] is True)
    green, rate, vslrows = defaultdict(Counter), defaultdict(Counter), Counter()
    with open(info['action_csv'], newline='', encoding='utf-8-sig') as h:
        for r in csv.DictReader(h):
            if r['kind'] == 'ramp_meter':
                green[r['id']][r['green_sec']] += 1
                rate[r['id']][r['rate_vph']] += 1
            elif r['kind'] == 'vsl':
                vslrows[r['speed_kph']] += 1
    out['meter_written_green_sec'] = {k: dict(v) for k, v in sorted(green.items())}
    out['meter_written_rate_vph'] = {k: dict(v) for k, v in sorted(rate.items())}
    out['vsl_written_speed_rows'] = dict(vslrows)
    out['selection'] = {k: dict(Counter(str(per[T][k]) for T in sd_T)) for k in ('selection_status', 'converged', 'feasible',
                                                                               'sdmpc_active', 'controller_status')}
    out['install_check'] = {'passed': dict(Counter(str(per[T]['install_passed']) for T in sd_T)),
                            'seeded_links': dict(Counter(json.dumps(per[T]['install_seeded']) for T in sd_T))}
    out['k9_present'] = {k: sum(1 for T in sd_T if per[T]['k9'][k]) for k in ('k9_w1', 'k9_w2a', 'k9_f17b')}
    out['n_sdmpc'] = len(sd_T)
    return out


def main():
    prof = V.profile_from_argv()
    pin = V.require_pinned(prof, __file__)
    t0 = time.time()
    prio = V.set_below_normal()
    res = {'schema': 'k92-va-control/v1', 'profile': prof.name, 'pinned': pin, 'priority': hex(prio), 'runs': {},
           'wall_ratio': {}}
    for s in V.SEEDS:
        res['runs']['va_s%d' % s] = run(s, prof.va_run(s), os.path.join(V.scan_dir(prof, 'va_s%d' % s), 'scan.json'))
        res['runs']['j1_s%d' % s] = run(s, V.j1_run(s), os.path.join(V.scan_dir(prof, 'j1_s%d' % s), 'scan.json'))
        a = res['runs']['va_s%d' % s]['wall_sdmpc'].get('median')
        b = res['runs']['j1_s%d' % s]['wall_sdmpc'].get('median')
        res['wall_ratio']['s%d' % s] = {'va_sdmpc_median': a, 'j1_sdmpc_median': b,
                                        'ratio': (a / b) if a and b else None, 'g_k5_budget': V.G_K5_BUDGET,
                                        'note': '보고만 (폐루프 상태가 달라 G-K5와 같은 양이 아님)'}
        print('s%d done' % s, flush=True)
    res['elapsed_sec'] = round(time.time() - t0, 1)
    V.jdump(res, os.path.join(prof.out, 'va_control.json'))
    print('elapsed', res['elapsed_sec'])


if __name__ == '__main__':
    main()
