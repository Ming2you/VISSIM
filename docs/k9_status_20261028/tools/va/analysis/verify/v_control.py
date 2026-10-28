# 검증자 자체: 제어 쪽 사실(§8.3-4 SC109 p3, §8.3-5 하한·씨앗, §8.3-7 미터·VSL, §8.3-8 유지·직전 계획 유지, §8.3-9 벽시계)
# action JSON·유지 영수증·런로그·launch 로그·러너 행동 로그 읽기 전용 (J1 검증 v_control.py 꼴, V-A·J1 같은 시드 나란히)
# 사용: python -B v_control.py --profile va|selftest
import csv, glob, io, json, os, re, statistics
from collections import Counter
from v_common import runs, profile, out_dir, jd, below_normal, SEEDS

below_normal()
prof = profile()
OUT = out_dir(prof)
RUNS = runs(prof)
HEADS = {'FW_E': ['FW_E__seg0', 'FW_E__seg5', 'FW_E__seg10', 'FW_E__seg15'],
         'FW_W': ['FW_W__seg0', 'FW_W__seg5', 'FW_W__seg10', 'FW_W__seg15']}
FL = re.compile(r'^head_discharge_floor_173_p4_[0-9a-f]{16}$')
res = {'profile': prof, 'runs': {}}


def longest(SD, hit):
    best = run = 0
    prev = None
    for T in SD:
        run = (run + 1 if (prev is not None and T - prev == 150 and prev in hit) else 1) if T in hit else 0
        best = max(best, run)
        prev = T
    return best


def isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


for s in SEEDS:
    for arm in ('j1', 'va'):
        t = '%s_s%d' % (arm, s)
        R = RUNS[t]
        dd = '%s/decisions_%s' % (R['dir'], R['name'])
        files = sorted(f for f in glob.glob(dd + '/action_*.json') if re.search(r'action_\d{6}\.json$', f))
        Ts = [int(re.search(r'action_(\d{6})\.json$', f).group(1)) for f in files]
        rec = {}
        prev = None
        for T, fp in zip(Ts, files):
            d = json.load(io.open(fp, encoding='utf-8'))
            md = d.get('metadata', {}) or {}
            jls = md.get('joint_leader_selection') or {}
            ps = (d.get('diagnostics') or {}).get('sdmpc_prediction_sequence')
            fut = []
            if isinstance(ps, dict) and isinstance(ps.get('future'), list):
                for k in range(min(2, len(ps['future']))):
                    fv = ps['future'][k].get('vsl') or {}
                    fut.append({z: fv.get(z) for z in HEADS['FW_E'] + HEADS['FW_W']})
            gt = d.get('green_times') or {}
            fk = {k: md[k] for k in md if FL.match(k)}
            hold = os.path.exists('%s/action_%06d.hold.json' % (dd, T)) or ('hold_previous_on_exception' in md)
            rec[T] = dict(vsl={z: (d.get('vsl') or {}).get(z) for z in HEADS['FW_E'] + HEADS['FW_W']}, rm=d.get('ramp_metering') or {},
                          sel=jls.get('selected_objective'), held=jls.get('held_objective'),
                          sel_eq=('selected_objective' in jls and 'held_objective' in jls and repr(jls['selected_objective']) == repr(jls['held_objective'])),
                          status=jls.get('selection_status'), has_ps=ps is not None, fut=fut,
                          p={ph: gt.get('SC109_' + ph) for ph in ('p2', 'p3', 'p4')},
                          same=(prev is not None and prev[0] == T - 150 and d.get('green_times') == prev[1] and d.get('offsets') == prev[2]),
                          has_prev=(prev is not None and prev[0] == T - 150),
                          floor=fk, k92=[k for k in ('k92_w', 'k92_hb', 'k92_hb_seed_binding') if k in md],
                          bind=md.get('k92_hb_seed_binding'), carried=md.get('head_observation_groups_carried'),
                          updated=md.get('head_observation_groups_updated'), pdisc=md.get('head_observation_prior_discarded'),
                          hold=hold)
            prev = (T, d.get('green_times'), d.get('offsets'))
            del d
        receipts = {}
        for hp in sorted(glob.glob(dd + '/action_*.hold.json')):
            h = json.load(io.open(hp, encoding='utf-8'))
            receipts[os.path.basename(hp)] = [(h.get('exception') or {}).get('type'), (h.get('exception') or {}).get('root_type')]
        runlog = open('%s/runlog_%s.txt' % (R['dir'], R['name']), encoding='utf-8', errors='replace').read()
        walls = {int(a): (float(b), int(c)) for a, b, c in re.findall(r'^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([\d.]+) result=exit=(-?\d+)', runlog, re.M)}
        cnt = {k: (re.findall(r'^%s=(\d+)' % k, runlog, re.M) or [None])[-1] for k in ('DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_ON_EXCEPTION')}
        launch = open('%s/launch_%s.log' % (R['dir'], R['name']), encoding='utf-8', errors='replace').read()
        wd = re.findall(r'WATCHDOG_EXIT code=(-?\d+) wall_sec=(\d+)', launch)
        rows = list(csv.DictReader(open('%s/action_%s.csv' % (R['dir'], R['name']), encoding='utf-8', errors='replace')))
        SD = sorted(T for T in rec if T >= 900)
        sdw = [walls[T][0] for T in SD if T in walls]
        p3hit = [T for T in SD if isnum(rec[T]['p']['p3']) and rec[T]['p']['p3'] <= 24.5]
        pstat = {}
        for ph in ('p2', 'p3', 'p4'):
            for nm, sel in (('all', SD), ('T_ge_4350', [T for T in SD if T >= 4350])):
                v = [rec[T]['p'][ph] for T in sel if isnum(rec[T]['p'][ph])]
                pstat['%s_%s' % (ph, nm)] = [statistics.fmean(v), max(v)] if v else None
        cand = [T for T in SD if T >= 1050 and not rec[T]['hold']]
        three = [T for T in cand if rec[T]['same'] and not rec[T]['has_ps'] and rec[T]['sel_eq']]
        names = Counter(k for T in Ts for k in rec[T]['floor'])
        pres = [(T, float(list(rec[T]['floor'].values())[0])) for T in Ts if len(rec[T]['floor']) == 1 and isnum(list(rec[T]['floor'].values())[0])]
        fell, fell_h = [], []
        for (Ta, xa), (Tb, xb) in zip(pres, pres[1:]):
            if xb < xa:
                (fell_h if any(rec[T]['hold'] for T in Ts if Ta <= T < Tb) else fell).append(Tb)
        vsl = {}
        for road in ('FW_E', 'FW_W'):
            below = [T for T in SD if any((rec[T]['vsl'][z] if rec[T]['vsl'][z] is not None else 110) < 110 for z in HEADS[road])]
            vsl[road] = dict(frac=len(below) / len(SD) if SD else None, first=below[0] if below else None, longest=longest(SD, set(below)),
                             below=below)
        mchg = sum(1 for T in Ts[1:] if rec[T]['has_prev'] and rec[T]['rm'] != rec[Ts[Ts.index(T) - 1]]['rm'])
        res['runs'][t] = dict(
            n_json=len(files), n_sdmpc=len(SD), counters=cnt, exit_codes=dict(Counter(c for w, c in walls.values())),
            warm_minmax=[min(walls[T][0] for T in Ts if T < 900 and T in walls), max(walls[T][0] for T in Ts if T < 900 and T in walls)],
            sdmpc_wall=dict(min=min(sdw), median=statistics.median(sdw), mean=statistics.fmean(sdw), max=max(sdw), sum=sum(sdw),
                            over900=sum(w > 900 for w in sdw)) if sdw else None,
            watchdog=wd, holds=[T for T in Ts if rec[T]['hold']], receipts=receipts,
            prev_plan=dict(cand=len(cand), ga=sum(rec[T]['same'] for T in cand), na=sum(not rec[T]['has_ps'] for T in cand),
                           da=sum(rec[T]['sel_eq'] for T in cand), three=three),
            p3=dict(count=len(p3hit), first=p3hit[0] if p3hit else None, longest=longest(SD, set(p3hit)), stats=pstat),
            floor=dict(names=dict(names), first=pres[0] if pres else None, max=max(x for _, x in pres) if pres else None, fell=fell,
                       fell_after_hold=fell_h, bind1=sum(1 for T in Ts if isinstance(rec[T]['bind'], float) and rec[T]['bind'] == 1.0),
                       carried=sum(rec[T]['carried'] for T in Ts if isnum(rec[T]['carried'])),
                       updated=sum(rec[T]['updated'] for T in Ts if isnum(rec[T]['updated'])),
                       pdisc1=[T for T in Ts if rec[T]['pdisc'] == 1.0],
                       k92=dict(Counter(k for T in Ts for k in rec[T]['k92']))),
            meters=dict(json=dict(Counter('%s=%s' % (k, v) for T in rec for k, v in rec[T]['rm'].items())), changed=mchg,
                        written=dict(Counter('%s|%s' % (r['rate_vph'], r['green_sec']) for r in rows if r['kind'] == 'ramp_meter'))),
            vsl=vsl, vsl_rows=dict(Counter(r['speed_kph'] for r in rows if r['kind'] == 'vsl')),
            status=dict(Counter(str(rec[T]['status']) for T in SD)),
            vsl_by_T={str(T): {z: rec[T]['vsl'][z] for z in HEADS['FW_E'] + HEADS['FW_W']} for T in rec})
    a = res['runs']['va_s%d' % s]['sdmpc_wall']
    b = res['runs']['j1_s%d' % s]['sdmpc_wall']
    res['runs']['ratio_s%d' % s] = (a['median'] / b['median']) if a and b else None
jd(res, os.path.join(OUT, 'v_control.json'))
print('ok')
