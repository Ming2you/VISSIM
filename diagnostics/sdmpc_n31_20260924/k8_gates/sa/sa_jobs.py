"""Plan and run the SA gate rollout jobs (sa_worker.py), strictly one process at a time, BELOW_NORMAL.

    python -B sa_jobs.py [--root R] [--out O] [--tree L] [--arms A,B] [--plan-only|--dry-run] [--hooks] <family>

family   jobs (label = sa_common.job_label)                                                     gates
  tl3      TL3 9 T x {OBS, A1} x arms, H3, REFERENCE                                           G-EB-1/3/4/10/11
  long     TL3 900 H24, 2700 H42, 4950 H27 x {OBS, A1} x arms (segment 6)                       G-EB-5/7
  c11      TL3 9 T x {C00, C11, C12} x arms, H3 OBS (three-block plans)                          G-EB-8
  tan      TL3 9 T x arms, H3 OBS, surrogate reverse AD + FW_W(T+450) tape sweep                 G-EB-8
  dp       DP 17 T x arms, H1 A1 (deployed forecast)                                            G-EB-3(d)/10 (+report)
  fh       FH 5 seeds x 9 T x arms, H3 OBS (FD2) + FD7 gate demand + FD5 VSL 110;              G-EB-3/6/10/11
           event states (vissim_ref.json) also H6
  h0       FH captures with the transplant disabled (_fhoff), seed 31, H3 OBS, TL3 settings     H-0
  h3       FH seed 31 self transplant, H3 OBS with TL3 settings (no FD5/FD7)                    H-3
  h4       one FH job (s41 @2700, judging arm, H3 OBS) run twice (rep1, rep2)                    H-4
  h5       FH frames T-150 / T / T+150 (same FZP island of T), H1 OBS, judging arm             H-5, G-EB-3 exclusion
  adfull   2700 REF / M2ALL, judging arm, non-surrogate AD (state_error), H3 A1                  G-EB-11(e)
  tl3m     amendment 13: TL3m = R-obs seeds 31/43/47 (--seeds, default 31,43,47) x 9 T x arms,   G-EB-3/6 (judged)
           H3 OBS on each seed's own template (TL3 capture --robs-seed S; s31 = the tl3 labels),
           + the judging arm's H6 OBS on the seed's VISSIM event states (vissim_ref.json); OBS
           entry = the seed's EO; a seed whose R-obs validity record is 'invalid' is left out
--arms default: BASE,SAF,SAG for tl3 (SAG on the OBS entry only) and fh (SAG only on the event states' H6),
BASE,SAF for long/c11/tan/dp/h0/h3, SAF for h4/h5/adfull.  SAG (report arm, D-K8-1) runs only at the declared places
FH event 14 H6 and TL3 9 H3 OBS (AMENDMENT_1 r2 §3.0, AMENDMENT_5 §1): any other SAG request is refused.
--hooks: run with PYTHONPATH sa_hooks (G-EB-13 TL3 job; the label gets variant HOOK so the hooked job never stands in
for, or is skipped as, the plain TL3 job of G-EB-1/11).  G-EB-13 judges the fixed job TL3_2700_SAF_OBS_H3_HOOK
(`tl3 --hooks --T 2700 --arms SAF`) and every other TL3 SAF hook job present (AMENDMENT_6 §3); --plan-only writes
job.pickle files; --dry-run prints.  declared_keyed() lists the declared key-on jobs and captures for G-EB-2.
Outputs <out>/sa/jobs/<tree>/<label>/{job.pickle, result.pickle, summary.json, log.txt[, hook/]}; skips a label whose
summary.json exists.  Captures (sa_capture.py) and vissim_ref.json (sa_vissim_ref.py) must exist first: a job whose
capture inputs are missing (capture.json, template.pickle, and for a horizon beyond the captured forecast
forecast_long.pickle with capture.json forecast_long_len >= H and forecast_long_prefix_equal true, K8 amendment 7 §4;
sa_common.job_inputs_missing) is not started and writes nothing (SA_JOB_SKIP_NO_CAPTURE -> absent -> INCOMPLETE,
review r4 B-r4-1).  A summary.json whose run ended on its own missing capture input
(sa_common.job_input_absent) is moved to stale_input_absent_<k>.json (hook/ to stale_hook_<k>/) and the job rerun
once its inputs exist; any other summary.json keeps the label skipped.
K8b-0 (K8_PREDECLARATION_AMENDMENT_16 r2): (1) blind guard (sections 0.2 / 5.4; since K9-1-0 sa_common.k91_guard of
AMENDMENT_19 r2 sections 0.4 / 3.1-4 / 5.4: K8b and K9 keys of the template's tuning and capture metadata, the stage
--gates-stage k91t --declaration-sha <amendment 19 sha> only, non-scalar jobs (tangent / adfull / c11 / tan / hooks)
refused on a judging state whatever the tree, and before the stage a judging state opens only the section 0.4 closed
list: G1 BASE TL3 s31 9 x {OBS, A1} H3 REFERENCE scalar, G2 TL3 s31 2700 k86h SAF OBS H3); (2) wall-clock pairs (section 5.3.1): every started job writes vissim_counts.json next to
its summary (VISSIM process count right before the worker starts and right after it ends, Get-Process read only, the
invocation id and its sequence number), which sa_wallpairs.py reads to find the clean BASE -> SAF pairs."""
import json
import os
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402
import k92_common as k92c  # noqa: E402  K9-2-0 blind guard (amendment 24 section 3.1-3a)

c = sc.c
FAMILIES = ('tl3', 'long', 'c11', 'tan', 'dp', 'fh', 'h0', 'h3', 'h4', 'h5', 'adfull', 'tl3m')
DEFAULT_ARMS = {'tl3': 'BASE,SAF,SAG', 'long': 'BASE,SAF', 'c11': 'BASE,SAF', 'tan': 'BASE,SAF',
                'dp': 'BASE,SAF', 'fh': 'BASE,SAF,SAG', 'h0': 'BASE,SAF', 'h3': 'BASE,SAF', 'h4': 'SAF',
                'h5': 'SAF', 'adfull': 'SAF', 'tl3m': 'BASE,SAF'}
DEFAULT_SEEDS = {'tl3m': sc.TL3M_SEEDS}       # every other family: the FH fit seeds (sc.FH_SEEDS)
SAG_FAMILIES = ('tl3', 'fh')          # the only families with a declared SA-G place (amendment 5 §1)
DEFAULT_EO = Path(r'D:\VISSIM_runs\20260930_v3c2\reports\nc_analysis\eo')   # v3c2 EO = v3c3 bytes (PREDECL §0 TL3)
LONG_SEGMENT = 6
PROFILES = {'C00': (1, (0.0, 0.0, 0.0)), 'C11': (1, (6.0, 10.0, 10.0)), 'C12': (-1, (6.0, 10.0, 10.0))}
ACTIONS_AD = {'REF': 'REFERENCE',
              'M2ALL': {'meters': {m: 2 for m in ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484',
                                                 'RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')}}}


def parse():
    ap = c.add_nc3(c.parser(__doc__))
    ap.add_argument('family', choices=FAMILIES)
    ap.add_argument('--tree', default='k86')
    ap.add_argument('--arms')
    ap.add_argument('--T', help='comma list of T (default: the family default)')
    ap.add_argument('--seeds', help='comma list (default: 31,41,43,47,53; tl3m: 31,43,47)')
    ap.add_argument('--eo-root', default=str(DEFAULT_EO))
    ap.add_argument('--hooks', action='store_true')
    ap.add_argument('--chain', choices=('site', 's3site'), default='site')
    ap.add_argument('--s3-table')
    ap.add_argument('--plan-only', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    sc.add_k8b_stage_args(ap)
    return ap.parse_args()


def x10490():
    ev = c.R / 'diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_20261004.json'
    try:
        return float(json.loads(ev.read_text(encoding='utf-8'))['report']['x_10490_m'])
    except Exception:
        return sc.ONE_STATION_X10490_DEFAULT


def event_states():
    ref = sc.read_json(sc.sa_out() / 'vissim_ref.json')
    if not ref:
        return None
    out = set()
    for seed, row in ref['seeds'].items():
        for T, st in row['states'].items():
            if st.get('event_state'):
                out.add((int(seed), int(T)))
    return out


def base_job(args, harness, T, arm, entry, H, *, seed=None, frame_T=None, variant='REF', mode='scalar', rep=None,
             cap_harness=None, fh_off=False):
    frame_T = T if frame_T is None else frame_T
    if getattr(args, 'hooks', False) and variant == 'REF':
        variant = 'HOOK'                 # hooked REFERENCE job: its own label (G-EB-13), never a plain TL3 job
    # FH: the island seed; TL3 (amendment 13 TL3m): the R-obs seed (s31 / None = the R-obs3 folder, no tag)
    cap = sc.cap_dir(args.tree, cap_harness or harness, T, arm, seed=seed if harness in ('FH', 'TL3') else None,
                     frame_T=frame_T)
    if fh_off:
        cap = cap.parent / (cap.name + '_fhoff')
    label = sc.job_label(harness if not fh_off else 'FH0', T, arm, entry, H, seed=seed, frame_T=frame_T,
                         variant=variant, mode=mode, rep=rep)
    labels_only = getattr(args, 'labels_only', False)        # declared_keyed(): labels / folders, no file read
    job = dict(schema='k8-sa-job/v1', label=label, harness=harness, T=T, seed=seed if seed is not None else 31,
               frame_T=frame_T, arm=arm, entry=entry, H=H, variant=variant, mode=mode, tree=args.tree,
               template=str(cap / 'template.pickle'), forecast_long=str(cap / 'forecast_long.pickle'),
               coord=str(cap / 'coord.pickle'), x10490_m=None if labels_only else x10490(), action='REFERENCE',
               obs_entry=None, gate_demand=None, vsl110=False, segment=(LONG_SEGMENT if H > LONG_SEGMENT else H))
    if entry == 'OBS' and not labels_only:
        import sa_fh
        eo_seed = seed if (harness in ('FH', 'TL3') and seed is not None) else 31   # TL3m: the seed's own EO
        job['obs_entry'] = sa_fh.eo_entry_rates(Path(args.eo_root) / f's{eo_seed}_v3c2nc', T, H)
        job['eo_dir'] = str(Path(args.eo_root) / f's{eo_seed}_v3c2nc')
    if variant in PROFILES:
        sign, profile = PROFILES[variant]
        job['action'] = {'offramp_profile': {'signal': 'SC1001', 'sign': sign, 'profile': list(profile)}}
    return job


def fh_extras(args, job, seed, T, H):
    """FD7 gate demand from the seed's FZP link 32 (x2 ext parquet) and FD5 VSL 110."""
    job['vsl110'] = True
    if getattr(args, 'labels_only', False):
        return job
    ext = c.OUT / 'opt1v2' / 'data' / f'e_s{seed}_ext.parquet'
    if getattr(args, 'dry_run', False):
        job['gate_demand'] = {sc.GATE: f'<dry-run: {ext} exists={ext.is_file()}>'}
        return job
    import pandas as pd
    import sa_fh
    df = pd.read_parquet(ext, columns=['SIMSEC', 'NO', 'LINK'])
    job['gate_demand'] = {sc.GATE: sa_fh.gate_rates(df, T, H)}
    job['gate_demand_source'] = {'path': str(ext), 'sha256': sc.sha256_file(ext)}
    return job


def plan(args):
    fam = args.family
    arms = (args.arms or DEFAULT_ARMS[fam]).split(',')
    if sc.REPORT_ARM in arms and fam not in SAG_FAMILIES:
        raise SystemExit(f'SAG is a report arm run only at FH event H6 and TL3 9 H3 OBS (K8 amendment 5 §1); '
                         f'refused in family {fam}')
    Ts = [int(x) for x in args.T.split(',')] if args.T else None
    seeds_arg = getattr(args, 'seeds', None)
    seeds = ([int(s) for s in seeds_arg.split(',') if s] if seeds_arg
             else list(DEFAULT_SEEDS.get(fam, sc.FH_SEEDS)))
    for s in seeds:
        sc.guard_tl3m_seed(s) if fam == 'tl3m' else sc.guard_seed(s)
    jobs = []
    if fam == 'tl3':
        for T in Ts or sc.GRID9:
            for entry in sc.ENTRIES:
                for arm in arms:
                    if arm == sc.REPORT_ARM and (args.hooks or not sc.sag_allowed('TL3', entry, 3)):
                        continue                  # SAG: TL3 9 H3 OBS only (never a hooked job)
                    jobs.append(base_job(args, 'TL3', T, arm, entry, 3))
    elif fam == 'long':
        for T, H in sc.LONG_H.items():
            if Ts and T not in Ts:
                continue
            for entry in sc.ENTRIES:
                for arm in arms:
                    jobs.append(base_job(args, 'TL3', T, arm, entry, H))
    elif fam == 'c11':
        for T in Ts or sc.GRID9:
            for arm in arms:
                for variant in PROFILES:
                    jobs.append(base_job(args, 'TL3', T, arm, 'OBS', 3, variant=variant))
    elif fam == 'tan':
        for T in Ts or sc.GRID9:
            for arm in arms:
                job = base_job(args, 'TL3', T, arm, 'OBS', 3, variant='TAN', mode='ad')
                job['tangent_owner'] = 'SC1001'
                jobs.append(job)
    elif fam == 'dp':
        for T in Ts or sc.DP_T:
            for arm in arms:
                jobs.append(base_job(args, 'DP', T, arm, 'A1', 1))
    elif fam == 'fh':
        events = event_states()
        if events is None:
            raise SystemExit('vissim_ref.json missing (sa_vissim_ref.py) - needed for the event states')
        for seed in seeds:
            for T in Ts or sc.GRID9:
                for arm in arms:
                    if arm != sc.REPORT_ARM:
                        jobs.append(fh_extras(args, base_job(args, 'FH', T, arm, 'OBS', 3, seed=seed), seed, T, 3))
                    if (seed, T) in events:
                        jobs.append(fh_extras(args, base_job(args, 'FH', T, arm, 'OBS', 6, seed=seed), seed, T, 6))
    elif fam == 'h0':
        for T in Ts or sc.GRID9:
            for arm in arms:
                jobs.append(base_job(args, 'FH', T, arm, 'OBS', 3, seed=31, fh_off=True))
    elif fam == 'h3':
        for T in Ts or sc.GRID9:
            for arm in arms:   # variant TLS = TL3 settings (no FD5/FD7), so the label differs from the fh family's
                jobs.append(base_job(args, 'FH', T, arm, 'OBS', 3, seed=31, variant='TLS'))
    elif fam == 'h4':
        for rep in (1, 2):
            jobs.append(fh_extras(args, base_job(args, 'FH', 2700, arms[0], 'OBS', 3, seed=41, rep=rep), 41, 2700, 3))
    elif fam == 'h5':
        for seed in seeds:
            for T in Ts or sc.GRID9:
                for f in (T - 150, T, T + 150):
                    for arm in arms:
                        jobs.append(fh_extras(args, base_job(args, 'FH', T, arm, 'OBS', 1, seed=seed, frame_T=f),
                                              seed, T, 1))
    elif fam == 'adfull':
        for (T, act) in sc.AD_FULL:
            for arm in arms:
                job = base_job(args, 'TL3', int(T), arm, 'A1', 3, variant='AD' + act, mode='ad_full')
                job['action'] = ACTIONS_AD[act]
                jobs.append(job)
    elif fam == 'tl3m':
        # amendment 13: each R-obs seed's own deployed template (TL3 capture --robs-seed S), OBS entry, H3 for every
        # arm, H6 for the judging arm on the seed's VISSIM event states; a seed with an invalid R-obs record leaves
        events = event_states()
        if events is None:
            raise SystemExit('vissim_ref.json missing (sa_vissim_ref.py) - needed for the event states')
        keep = sc.tl3m_seeds_not_invalid()
        for seed in seeds:
            if seed not in keep:
                if not getattr(args, 'labels_only', False):
                    print(f'SA_TL3M_SEED_LEFT_OUT s{seed}: R-obs validity record invalid (amendment 13)', flush=True)
                continue
            for T in Ts or sc.GRID9:
                for arm in arms:
                    jobs.append(base_job(args, 'TL3', T, arm, 'OBS', 3, seed=seed))
                    if arm == sc.JUDGING_ARM and (seed, T) in events:
                        jobs.append(base_job(args, 'TL3', T, arm, 'OBS', 6, seed=seed))
    events = event_states() if fam == 'fh' else None
    for job in jobs:
        if job['arm'] == sc.REPORT_ARM and not sc.sag_allowed(
                job['harness'], job['entry'], job['H'], variant=job['variant'], mode=job['mode'],
                event_state=None if events is None else (job['seed'], job['T']) in events):
            raise SystemExit(f'SAG job outside the declared places refused: {job["label"]} (K8 amendment 5 §1)')
    return jobs


def declared_keyed(tree):
    """AMENDMENT_6 §3 (G-EB-2): the declared key-on runs = every SAF job of every family at its defaults (T, seeds)
    + the SAG 23 (FH event H6 14 + TL3 OBS H3 9) + the G-EB-13 judged hook job; captures = the template folders of
    those jobs + ROBS61 61 (SAF).  Amendment 13: the tl3m family is one of those families (SAF H3 OBS + event H6 of
    every TL3m seed whose R-obs validity record is not invalid) and ROBS61 61 SAF is listed for each such R-obs seed.
    Labels and folders only (no EO, parquet or evidence read); needs vissim_ref.json for the event states (SystemExit
    otherwise).  Returns (job labels, capture folders, n SAG jobs)."""
    jobs = declared_keyed_jobs(tree)
    labels = sorted({j['label'] for j in jobs})
    caps = {str(Path(j['template']).parent) for j in jobs}
    # ROBS61 61 SAF of R-obs3 and (amendment 13) of every other TL3m R-obs seed whose validity record is not invalid
    caps |= {str(sc.cap_dir(tree, 'ROBS61', T, sc.JUDGING_ARM, seed=s)) for s in sc.tl3m_seeds_not_invalid()
             for T in sc.ROBS61_T}
    caps |= {str(sc.cap_dir(tree, 'ROBS61', T, sc.JUDGING_ARM)) for T in sc.ROBS61_T}
    return labels, sorted(caps), sum(1 for j in jobs if j['arm'] == sc.REPORT_ARM)


def declared_keyed_jobs(tree):
    """The declared key-on job dicts behind declared_keyed() (labels-only plans: label, arm, template, H,
    forecast_long; G-EB-2 reads an SAG job's capture inputs from them, AMENDMENT_8 §2)."""
    from types import SimpleNamespace

    def args_of(family, arms, T=None, hooks=False):   # seeds None = the family default (FH seeds; tl3m: 31,43,47)
        return SimpleNamespace(family=family, arms=arms, T=T, seeds=None, tree=tree, eo_root='.', hooks=hooks,
                               chain='site', s3_table=None, plan_only=False, dry_run=True, labels_only=True)
    jobs = []
    for fam in FAMILIES:
        arms = [a for a in DEFAULT_ARMS[fam].split(',') if a in sc.KEYED_ARMS]
        if arms:
            jobs += plan(args_of(fam, ','.join(arms)))
    hooked = [j for j in plan(args_of('tl3', sc.JUDGING_ARM, T=str(sc.G13_HOOK_T), hooks=True))
              if j['label'] == sc.G13_JUDGED_HOOK_JOB]
    if len(hooked) != 1:
        raise SystemExit('G-EB-13 judged hook job not planned: ' + sc.G13_JUDGED_HOOK_JOB)
    return jobs + hooked


def set_aside_input_absent(tree, out):
    """Review r4 B-r4-1: a summary.json whose run ended on its own missing capture input (sc.job_input_absent) is not a
    result.  Called once the inputs exist: it is moved to stale_input_absent_<k>.json and its hook/ folder to
    stale_hook_<k>/ (read by no gate or hook count; k never reused), so the job runs again.  Any other summary is kept
    (the label stays skipped).  Returns True when moved."""
    try:
        s = sc.read_json(out / 'summary.json')
    except ValueError:
        return False
    if sc.job_input_absent(s, tree) is None:
        return False
    k = 1
    while (out / f'stale_input_absent_{k}.json').exists() or (out / f'stale_hook_{k}').exists():
        k += 1
    os.replace(out / 'summary.json', out / f'stale_input_absent_{k}.json')
    if (out / 'hook').exists():
        os.replace(out / 'hook', out / f'stale_hook_{k}')
    return True


RUN = {'invocation': None, 'seq': 0}


def k8b_job_guard(args, job):
    """Blind guard (K9-1-0: sa_common.k91_guard, amendment 19 r2 sections 0.4 / 3.1-4 / 5.4) on the tuning the job's
    template was captured with (the capture record's tuning path and sha256, plus the K8b / K9 metadata keys of that
    record) and on the job itself (harness, arm, entry, H, variant, mode, hooks); without a capture record nothing
    runs anyway (job_inputs_missing), so no tuning is read then."""
    try:
        rec = sc.read_json(Path(job['template']).parent / 'capture.json')
    except ValueError:
        rec = None
    if not isinstance(rec, dict):
        return []
    path = (rec.get('tuning') or {}).get('path')
    meta = rec.get('metadata') or {}
    extra = [f'capture metadata {k}' for k in sc.GUARD_META_KEYS + k92c.K92_META_KEYS if k in meta]
    kw = dict(op='job', harness=job['harness'], arm=job['arm'], entry=job.get('entry'), H=job.get('H'),
              variant=job.get('variant', 'REF'), mode=job.get('mode', 'scalar'), hooks=bool(getattr(args, 'hooks', False)),
              arm_sha=(rec.get('tuning') or {}).get('sha256'))
    keys = k92c.k92_guard(path, job.get('seed'), job['T'], args, f'job {job["label"]}', extra_keys=extra, **kw)
    if int(job.get('frame_T', job['T'])) != int(job['T']):
        k92c.k92_guard(path, sc.ROBS_SEED, job['frame_T'], args, f'job frame {job["label"]}', extra_keys=keys, **kw)
    return keys


def write_vissim_counts(out, rec):
    sc.write_json(out / 'vissim_counts.json', rec)


def run_job(args, job):
    out = sc.job_dir(args.tree, job['label'])
    lacking = sc.job_inputs_missing(job)             # review r4 B-r4-1: no worker without its capture inputs
    if not args.dry_run and not args.plan_only:
        k8b_job_guard(args, job)
    if args.dry_run:
        print(f'DRY {job["label"]} inputs={"ok" if not lacking else "MISSING " + ",".join(lacking)} -> {out}')
        return
    if (out / 'summary.json').is_file():
        if args.plan_only or lacking or not set_aside_input_absent(args.tree, out):
            print(f'SA_JOB_SKIP {job["label"]}', flush=True)
            return
        print(f'SA_JOB_RERUN_INPUT_ABSENT {job["label"]} (earlier summary set aside)', flush=True)
    if lacking and not args.plan_only:
        print(f'SA_JOB_SKIP_NO_CAPTURE {job["label"]} missing={",".join(lacking)} '
              f'capture={Path(job["template"]).parent}', flush=True)
        return
    out.mkdir(parents=True, exist_ok=True)
    (out / 'job.pickle').write_bytes(pickle.dumps(job, protocol=5))
    if args.plan_only:
        return
    # amendment 13: a TL3m job of R-obs s43 / s47 runs with that run's provenance env (s31 / FH: R-obs3, as before)
    env = sc.base_env_for(job.get('seed') if job.get('harness') == 'TL3' else None,
                          hook_dir=(out / 'hook') if args.hooks else None)
    if args.hooks:
        chain = sc.GATES_DIR / ('s3site' if args.chain == 's3site' else 'site') / 'sitecustomize.py'
        env.update(K8_SA_CHAIN_SITE=str(chain), K8_SA_HOOK='1')
        if args.chain == 's3site':
            env['K8_S3_TABLE_JSON'] = str(Path(args.s3_table).resolve())
        env['PYTHONPATH'] = str(HERE / 'sa_hooks') + ';' + env['PYTHONPATH'].split(';', 1)[1]
    import time
    if RUN['invocation'] is None:
        RUN['invocation'] = '%s_%d' % (time.strftime('%Y%m%d_%H%M%S'), os.getpid())
    RUN['seq'] += 1
    pre, t_start = sc.vissim_count(), time.time()
    code, wall = c.run([c.PY, '-B', str(HERE / 'sa_worker.py'), str(out / 'job.pickle'), str(out / 'result.pickle')],
                       out / 'log.txt', env)
    write_vissim_counts(out, {'schema': 'k8b-vissim-counts/v1', 'label': job['label'], 'arm': job['arm'],
                              'invocation': RUN['invocation'], 'seq': RUN['seq'], 'vissim_count_pre': pre,
                              'vissim_count_post': sc.vissim_count(), 'start': t_start, 'end': time.time(),
                              'exit': code})
    s = sc.read_json(out / 'summary.json', {}) or {}
    print(f'SA_JOB {job["label"]} exit={code} wall={wall} ok={s.get("ok")} objective={s.get("objective_repr")}',
          flush=True)


def main():
    args = parse()
    c.apply(args)
    jobs = plan(args)
    if not args.dry_run:
        c.lower_priority()
    queue = sc.sa_out() / 'jobs' / args.tree / f'queue_{args.family}.json'
    if not args.dry_run:
        sc.write_json(queue, [j['label'] for j in jobs])
    print(f'SA_JOBS_PLAN family={args.family} tree={args.tree} n={len(jobs)} root={c.R}', flush=True)
    for job in jobs:
        run_job(args, job)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
