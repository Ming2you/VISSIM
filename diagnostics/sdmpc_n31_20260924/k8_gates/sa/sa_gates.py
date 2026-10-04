"""SA gate calculators G-EB-0 ... G-EB-14 (K8 PREDECL §3.2 with AMENDMENT_1 r2 §3.0-§3.3 rows, AMENDMENT_2 N-A4/N-A9;
judging arm SA-F = storage observed_full, D-K8-1).  Pure functions of precomputed files; writes JSON + markdown.

    python -B sa_gates.py [--root R] [--out O] [--tree k86] [--base-tree k85] [--evidence-log F]
                          [--unit-log F [--unit-log F2 ...]] [--leader-review F] [--hooks-tag hooks]
                          [--only G-EB-3,...] [--dry-run]
        -> <out>/sa/gates/gates_<tree>.{json,md}

Inputs (all produced before this runs; a missing input makes the gate INCOMPLETE, never PASS):
  job summaries   sa_jobs.py families tl3 long c11 tan dp fh h5 adfull (+ the base tree's tl3 for G-EB-1)
  captures        sa_capture.py tl3 / dp / robs61 / fh (capture.json or capture_failed.json)
  vissim_ref.json sa_vissim_ref.py          compare/*.json  sa_compare.py g1 g9
  hooks_<tree>.json sa_hookcount.py         gates/smoke_<tree>.json  sa_smoke.py (H-5 exclusions, N5)
  --evidence-log  stdout of `python -B diagnostics/sdmpc_n31_20260924/stopline/build_sc1001eb_evidence.py --check`
  --unit-log      pytest 9 -v log(s), repeatable, or ONE combined -v run (AMENDMENT_6 §1): T2 (KeyAbsent*), T10
                  (ContiguousWalk*), T10b (PostService*), T13 (Tangent*) and the gate-stage captured-state rows of
                  test_stopline_approach_captured.py (T9b*, T9c*: G-EB-14) with their capture provenance lines.
                  Failures are read from the short test summary lines (a failed subTest leaves its progress row
                  PASSED); a missing row, a skip or an unattributed session failure is INCOMPLETE, never PASS or FAIL
  --leader-review G-EB-13 manual review {module:function: {"service_rate_in_cost": bool, "reason": str}}
Judging-arm principle (AMENDMENT_5 §1): every judged item is computed on SAF only; BASE is only the comparator (paired
increments, wall ratio); SAG items are reports; completeness is checked on the judging arm's inputs.  G-EB-2 alone
counts every keyed arm (SAF and SAG): an invariant violation is a code defect whatever the arm; any other SAG failure
is reported and never holds G-EB-2 (AMENDMENT_7 §2).  Failure classification (AMENDMENT_7 §2, sa_errors): a failed
run counts as a FAIL only when its child recorded a traceback raised in runtime code; harness / infrastructure causes
(killed, input absent, parent-only record, probe or harness exception, no traceback) are INCOMPLETE (rerun).  A
capture folder with capture.json is a capture (a capture_failed.json beside it is stale); a capture_failed.json the
child never wrote is 'killed' = unreadable (B-r3-3).  G-EB-11(d) / G-EB-13 need a valid instrument of a finished run
and G-EB-13 the BASE positive control (AMENDMENT_7 §3).
Verdict per gate: PASS (every judged item passes), FAIL (a judged item fails), INCOMPLETE (a judged item lacks
inputs).  Combination (§3.3 as amended): the judging arm SAF passes every judged item of G-EB-0..11 (11 with (d)(e)),
13 and 14 -> PROMOTE_ELIGIBLE (K8-7); any FAIL -> STOP (J1 held, D-K8-4; SA-G never changes the arm);
otherwise INCOMPLETE.  G-EB-12 (J1) is not computed here.  Harness operationalisations: sa_common.OPERATIONALISATIONS
(fixed before any gate output; listed in the report)."""
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402
import sa_hookcount as sh  # noqa: E402   (G-EB-13 instrument constants; stdlib only)
import sa_s3parity as S3P  # noqa: E402   (AMENDMENT_10 verdict for G-EB-11(e); stdlib only at import)
import sa_inputs as si  # noqa: E402
import sa_stats as ss  # noqa: E402
from sa_smoke import lane_stock_target  # noqa: E402

c = sc.c
J = sc.JUDGING_ARM
EVIDENCE_REL = 'diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_20261004.json'
CAPTURED_TESTS = 'test_stopline_approach_captured.py'      # gate-stage captured-state rows (AMENDMENT_5 §4)


# ------------------------------------------------------------------------------------------------ result helpers
def item(value, threshold, ok, judged=True, note=None, **extra):
    return dict(value=value, threshold=threshold, pass_=ok, judged=judged, note=note, **extra)


def gate(gid, title, harness, items, notes=(), missing=()):
    judged = [it['pass_'] for it in items.values() if it['judged']]
    if any(p is False for p in judged):
        v = 'FAIL'
    elif any(p is None for p in judged) or not judged:
        v = 'INCOMPLETE'
    else:
        v = 'PASS'
    return dict(id=gid, title=title, harness=harness, verdict=v, items=items, notes=list(notes),
                missing=sorted(set(missing)))


def pf(x):
    return None if x is None else bool(x)


def _ok(summary):
    return bool(summary and summary.get('ok'))


_STATUS = ('PASSED', 'FAILED', 'ERROR', 'SKIPPED', 'XFAIL', 'XPASS')
_STATUS_OF = {'XFAIL': 'SKIPPED', 'XPASS': 'SKIPPED'}          # an xfail / xpass is not a declared pass
_ROW = re.compile(r'^(\S+::\S+)(?:\s+(.*))?$')
_ORPHAN = re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s|$)')
_FAIL_LINE = re.compile(r'^(SUBFAILED|FAILED|ERROR)(?=[\[( ])')
_SUMMARY_HEADER = re.compile(r'^=+ short test summary info =+$')
_SESSION = re.compile(r'^=+ (.+ in [\d.]+s(?: \([^)]*\))?) =+$')
PROVENANCE_TAG = 'K8_SA_CAPTURE_PROVENANCE'                   # printed by test_stopline_approach_captured.py
_PROVENANCE = re.compile(PROVENANCE_TAG + r' (\{.*\})')


def _set_row(rows, nodeid, status):
    status = _STATUS_OF.get(status, status)
    if rows.get(nodeid) not in ('FAILED', 'ERROR'):            # a failure is never overwritten
        rows[nodeid] = status


def _parse_one_log(path):
    """One pytest 9 `-v` log (AMENDMENT_6 §1).  Rows come from the progress lines (`<nodeid> STATUS`, or a bare
    `<nodeid>` start line whose status word lands on a later line after interleaved output); failures come from the
    short test summary lines `^(SUBFAILED|FAILED|ERROR)([...]|(...))? <nodeid>` (canonical: a failed unittest subTest
    leaves its progress row PASSED); the session summary `N failed` / `N errors` must be fully attributed to summary
    lines with a node id, else the log has unattributed failures."""
    rows, known, failure_lines, provenance = {}, [], [], []
    session, in_summary, current = None, False, None
    for raw in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        s = raw.strip()
        p = _PROVENANCE.search(s)
        if p:
            try:
                rec = json.loads(p.group(1))
                provenance.append(rec if isinstance(rec, dict) else {'_error': 'not an object'})
            except ValueError as exc:
                provenance.append({'_error': repr(exc)[:200]})
            s = s[:p.start()].strip()                          # a start line the output was appended to
            if not s:
                continue
        sess = _SESSION.match(s)
        if sess:
            text = sess.group(1)
            session = {'text': text,
                       'failed': sum(int(n) for n in re.findall(r'(\d+) failed\b', text)),
                       'errors': sum(int(n) for n in re.findall(r'(\d+) errors?\b', text))}
            in_summary, current = False, None
            continue
        if _SUMMARY_HEADER.match(s):
            in_summary, current = True, None
            continue
        if in_summary:
            if _FAIL_LINE.match(s):
                failure_lines.append(s)
            continue
        if s.startswith(('=', '_')):                           # section headers end the progress phase
            current = None
            continue
        m = _ROW.match(s)
        if m and not _ORPHAN.match(s):
            nodeid, rest = m.group(1), (m.group(2) or '')
            if nodeid not in known:
                known.append(nodeid)
            w = re.match(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b', rest)
            if w:
                _set_row(rows, nodeid, w.group(1))
                current = None
            else:
                current = nodeid                               # start line; status follows on a later line
            continue
        o = _ORPHAN.match(s)
        if o and current is not None:
            _set_row(rows, current, o.group(1))
            current = None
    attributed, failed_ids = 0, []
    by_length = sorted(known, key=len, reverse=True)
    for fl in failure_lines:
        nodeid = next((n for n in by_length if (' ' + n + ' - ') in fl or fl.endswith(' ' + n)), None)
        if nodeid is None:                                     # no progress row: best-effort token before ' - '
            head = fl.split(' - ', 1)[0].split()
            tok = head[-1] if len(head) > 1 else None
            nodeid = tok if tok and ('::' in tok or tok.endswith('.py')) else None
        if nodeid is None:
            continue
        attributed += 1
        failed_ids.append(nodeid)
        rows[nodeid] = 'FAILED' if rows.get(nodeid) != 'ERROR' else 'ERROR'
    unattributed = None if session is None else max(0, session['failed'] + session['errors'] - attributed)
    return {'path': str(path), 'sha256': sc.sha256_file(path), 'rows': rows, 'session': session,
            'failure_lines': len(failure_lines), 'attributed': attributed, 'failed_ids': failed_ids,
            'unattributed': unattributed, 'provenance': provenance}


def parse_unit_log(paths):
    """All --unit-log files (AMENDMENT_6 §1: several logs, or one combined -v run).  None when no log is named;
    a named file that does not exist is recorded (every unit item is then INCOMPLETE)."""
    if not paths:
        return None
    if isinstance(paths, (str, Path)):
        paths = [paths]
    logs, missing = [], []
    for path in paths:
        if Path(path).is_file():
            logs.append(_parse_one_log(path))
        else:
            missing.append(str(path))
    rows = {}
    for log in logs:
        for nodeid, status in log['rows'].items():
            _set_row(rows, nodeid, status)
    return {'rows': rows, 'logs': logs, 'missing': missing,
            'provenance': [rec for log in logs for rec in log['provenance']]}


def _norm_path(p):
    try:
        return os.path.normcase(str(Path(p).resolve()))
    except (OSError, TypeError, ValueError):
        return None


def captured_provenance(results, tree, needs):
    """AMENDMENT_6 §1: a captured-state row counts only when the log's provenance lines (capture root, tree name,
    template sha256, printed by test_stopline_approach_captured.py) name <out>/sa/cap/<tree> and agree with that
    tree's capture.json.  Every provenance line of the given logs must agree (a log of another capture root, e.g.
    the toy captures of sawip/fakecap, makes the captured rows INCOMPLETE); `needs` = the (harness, arm) captures
    the row reads, all at one T."""
    if results is None:
        return {'ok': None, 'reason': 'no --unit-log'}
    root = _norm_path(sc.sa_out() / 'cap' / tree)
    bad, have = [], set()
    for rec in results['provenance']:
        try:
            key = (str(rec['harness']), int(rec['T']), str(rec['arm']))
        except (KeyError, TypeError, ValueError):
            bad.append(['unreadable provenance line', rec.get('_error')])
            continue
        why = []
        if rec.get('tree') != tree:
            why.append(f'tree {rec.get("tree")} != {tree}')
        if _norm_path(rec.get('root')) != root:
            why.append(f'root {rec.get("root")} != {root}')
        cap = sc.read_json(sc.cap_dir(tree, key[0], key[1], key[2]) / 'capture.json')
        if cap is None:
            why.append('capture.json missing')
        elif not rec.get('template_sha256') or cap.get('template_sha256') != rec.get('template_sha256') \
                or rec.get('capture_json_template_sha256') != rec.get('template_sha256'):
            why.append('template sha256 differs from capture.json')
        if why:
            bad.append([list(key), '; '.join(why)])
        else:
            have.add(key)
    if bad:
        return {'ok': None, 'reason': 'provenance mismatch', 'rows': bad[:10]}
    Ts = sorted({T for _h, T, _a in have})
    for T in Ts:
        if all((h, T, a) in have for h, a in needs):
            return {'ok': True, 'T': T, 'captures': sorted(f'{h}/{T}/{a}' for h, a in needs)}
    return {'ok': None, 'reason': 'no provenance line for ' + ', '.join(f'{h}/{a}' for h, a in needs),
            'have': sorted(f'{h}/{T}/{a}' for h, T, a in have)}


def unit_item(results, patterns, label, provenance=None):
    """Unit-log item (AMENDMENT_6 §1, every unit item): FAIL when a row or a summary failure line of a matching
    node id is FAILED/ERROR; else INCOMPLETE when no log is named or one is missing, when a log holding matching
    rows has failures the session summary cannot attribute (or no session summary), when a row is SKIPPED, when no
    row PASSED, or (captured-state rows) when the capture provenance is not verified; else PASS."""
    threshold = f'{label}: >= 1 PASSED, 0 SKIPPED, 0 FAILED (absence, skip or unattributed failure -> INCOMPLETE)'
    if results is None:
        return item(None, threshold, None, note='no --unit-log')
    if results['missing']:
        return item(None, threshold, None, note='unit log missing: ' + ', '.join(results['missing']))
    hit = {k: v for k, v in results['rows'].items() if any(p in k for p in patterns)}
    passed = sum(1 for v in hit.values() if v == 'PASSED')
    skipped = sum(1 for v in hit.values() if v == 'SKIPPED')
    bad = sorted(k for k, v in hit.items() if v in ('FAILED', 'ERROR'))
    unclear = [log['path'] for log in results['logs']
               if (log['session'] is None or log['unattributed']) and any(any(p in k for p in patterns)
                                                                          for k in log['rows'])]
    value = {'passed': passed, 'failed': bad[:10], 'skipped': skipped, 'unattributed_logs': unclear}
    if provenance is not None:
        value['provenance'] = provenance
        if provenance.get('ok') is not True:
            return item(value, threshold, None, note='capture provenance not verified: ' + str(provenance.get('reason')))
    if bad:
        return item(value, threshold, False)
    if unclear:
        return item(value, threshold, None, note='failures not attributable to node ids (session summary) or no '
                                                  'session summary in ' + ', '.join(unclear))
    return item(value, threshold, True if passed > 0 and skipped == 0 else None)


# ================================================================================================ G-EB-0
def g0(I, args):
    ev = c.R / EVIDENCE_REL
    items, missing = {}, []
    if not ev.is_file():
        return gate('G-EB-0', 'evidence values', 're-count (done)', {'evidence': item(None, 'present', None)},
                    missing=[str(ev)])
    doc = json.loads(ev.read_text(encoding='utf-8'))
    sha = sc.sha256_file(ev)
    log = Path(args.evidence_log).read_text(encoding='utf-8', errors='replace') if args.evidence_log and \
        Path(args.evidence_log).is_file() else None
    m = re.search(r'STOPLINE_EVIDENCE_OK sha256=([0-9a-f]{64})', log or '')
    items['builder_check'] = item(m.group(1) if m else None, 'builder --check OK, sha256 = evidence file ' + sha[:16],
                                  (m is not None and m.group(1) == sha) if log is not None else None,
                                  note=None if log is not None else 'no --evidence-log')
    inp = doc.get('inputs') or {}
    items['declarations'] = item({'a1v2': (inp.get('a1v2_visit') or {}).get('declaration_sha16'),
                                  's2': (inp.get('s2_lanefull') or {}).get('declaration_sha16')},
                                 '211a48c6b3e3f450 / 5864d5b1d518c34e',
                                 (inp.get('a1v2_visit') or {}).get('declaration_sha16') == '211a48c6b3e3f450'
                                 and (inp.get('s2_lanefull') or {}).get('declaration_sha16') == '5864d5b1d518c34e')
    items['geometry_sha12'] = item((inp.get('g2_inpx') or {}).get('extract_sha12'), '910bc37a8d69',
                                   (inp.get('g2_inpx') or {}).get('extract_sha12') == '910bc37a8d69')
    a = (doc.get('approaches') or {}).get('SC1001_EB') or {}
    items['amendment_keys'] = item(
        {'posthead_connectors': sorted(a.get('posthead_connectors') or {}), 'posthead_rehome': a.get('posthead_rehome'),
         'pre_stopline_links': a.get('pre_stopline_links')},
        '{10118,10368,10695} / {10695: SC1001_to_SC2002} / [32,10778,129,10777,127]',
        sorted(a.get('posthead_connectors') or {}) == ['10118', '10368', '10695']
        and a.get('posthead_rehome') == {'10695': 'SC1001_to_SC2002'}
        and a.get('pre_stopline_links') == ['32', '10778', '129', '10777', '127'])
    items['loso_recorded'] = item((inp.get('s2_loso') or {}).get('sha256'), 'recorded only', None, judged=False)
    return gate('G-EB-0', 'evidence values (spec 1.9 bit reproduction)', 're-count (done)', items,
                notes=['evidence sha256 ' + sha])


# ================================================================================================ G-EB-1
def g1(I, args):
    items = {}
    unit = parse_unit_log(args.unit_log)
    items['unit_T2'] = unit_item(unit, ('KeyAbsent',), 'T2')
    items['unit_T10'] = unit_item(unit, ('ContiguousWalk',), 'T10')
    items['unit_T10b'] = unit_item(unit, ('PostService',), 'T10b')
    g9 = I.compare(f'g9_{I.tree}')
    # AMENDMENT_7 §4 (review B-r5-1): the G-EB-9 rule -- a missing DP row or a row count != 17 is INCOMPLETE (the
    # former `A if C else B and not any(...)` put the missing test inside the else branch: one missing row -> FAIL).
    g9_rows = None if g9 is None else g9['result']
    t11 = (None if g9_rows is None or any('missing' in r for r in g9_rows.values()) or len(g9_rows) != len(sc.DP_T)
           else all(bool(r.get('meters') and r.get('normalisation') and r.get('sc109')) for r in g9_rows.values()))
    items['unit_T11'] = item(None, 'see G-EB-9 (DP meter tables / SC109 key on-off; missing row or != 17 rows -> '
                             'INCOMPLETE)', t11)
    d = I.compare(f'g1_{I.tree}_vs_{I.base_tree}')
    if d is None:
        for key in ('dp17', 'tl3', 'full2700'):
            items[key] = item(None, 'equal', None, note='compare g1 missing')
    else:
        r = d['result']
        dp = r['dp']
        items['dp17'] = item({T: (x.get('differ_excl_timing'), x.get('only_a'), x.get('only_b')) for T, x in dp.items()},
                             'numeric fields differ 0 (timing excluded), no one-sided field, 17 states',
                             None if any('missing' in x for x in dp.values()) or len(dp) != len(sc.DP_T)
                             else all(x['equal'] for x in dp.values()))
        tl = r['tl3']
        items['tl3'] = item({k: (x.get('differ_excl_timing'), x.get('objective_equal')) for k, x in tl.items()},
                            'TL3 9 x {OBS, A1} H3: objective repr and numeric fields equal',
                            None if any('missing' in x for x in tl.values()) or len(tl) != 2 * len(sc.GRID9)
                            else all(x['equal'] and x['objective_equal'] for x in tl.values()))
        fu = r['full'].get('2700') or {}
        items['full2700'] = item({k: fu.get(k) for k in ('objective', 'held_objective', 'csv_sha256', 'outcome',
                                                         'missing')},
                                 'objective / held repr equal', None if 'missing' in fu or not fu else fu.get('equal'),
                                 note='CSV byte equality reported: %s' % fu.get('csv_equal'))
    return gate('G-EB-1', 'key absent = previous runtime commit', 'unit + DP 17 + TL3 9x2 + full 2700', items,
                notes=[f'base tree {I.base_tree}', 'AMENDMENT_7 §2: a pair with a run that did not finish (absent, '
                       'killed, input absent, failed without a runtime traceback) or with both runs failed is '
                       'INCOMPLETE; both finished and one failed -> FAIL (sa_compare.pair_state)'])


# ================================================================================================ G-EB-2
def _arm_of_cap(folder):
    """Arm of a capture folder <.../<arm>> or <.../<arm>_fhoff> (H-0 transplant-disabled captures are key-on too)."""
    name = Path(folder).name
    return name[:-len('_fhoff')] if name.endswith('_fhoff') else name


def declared_runs(tree):
    """(job labels, capture folders, n SAG, {SAG label: job}, error) of the declared key-on runs
    (sa_jobs.declared_keyed; the SAG job dicts name their capture inputs, AMENDMENT_8 §2)."""
    try:
        import sa_jobs
        labels, caps, n_sag = sa_jobs.declared_keyed(tree)
        sag_jobs = {j['label']: j for j in sa_jobs.declared_keyed_jobs(tree) if j['arm'] == sc.REPORT_ARM}
        return labels, caps, n_sag, sag_jobs, None
    except SystemExit as exc:
        return None, None, None, None, str(exc)


G2_INVARIANT_KINDS = sc.INVARIANT_KINDS                        # every keyed arm (AMENDMENT_5 §1; sa_errors)
G2_SAF_CAPTURE_KINDS = G2_INVARIANT_KINDS + ('init',)           # SAF captures: an init refusal counts as well


def _arm_of_job(summary, label):
    """Arm of a job summary: job.arm, else the arm token of its label (a summary written before the job was read has
    an empty job, review r3 N-r3-6); None when neither names exactly one arm."""
    arm = (summary.get('job') or {}).get('arm')
    if arm in sc.ARMS:
        return arm
    toks = [a for a in sc.ARMS if a in str(label).split('_')]
    return toks[0] if len(toks) == 1 else None


def g2_failed_row(name, arm, rec, tail, capture=False):
    """AMENDMENT_7 §2 for one failed child record (job summary ok false / child-written capture failure): (bucket,
    row).  A violation = an invariant kind (SAF captures also init) raised in runtime code -> 'viol' (FAIL, any keyed
    arm).  SAF: any other failure with a runtime traceback -> 'other' (FAIL); without one (harness / infrastructure)
    -> 'unreadable' (INCOMPLETE).  SAG: everything else -> 'sag' (reported only, never holds G-EB-2)."""
    kind, site = sc.record_kind(rec), sc.record_site(rec)
    sag = arm != sc.JUDGING_ARM
    kinds = G2_SAF_CAPTURE_KINDS if (capture and not sag) else G2_INVARIANT_KINDS
    if site == 'runtime' and kind in kinds:
        return 'viol', [name, kind, tail]
    if sag:
        return 'sag', [name, kind, 'SAG failure, site %s (reported, AMENDMENT_7 §2)' % site, tail]
    if site == 'runtime':
        return 'other', [name, kind, tail]
    return 'unreadable', [name, kind, 'SAF failure without a runtime traceback (site %s): harness / infrastructure '
                          '-> rerun (AMENDMENT_7 §2)' % site, tail]


def g2(I, args):
    """Invariant violations over every keyed arm (AMENDMENT_5 §1) with the AMENDMENT_6 §3 completeness rule and the
    AMENDMENT_7 §2 failure classification (sa_errors, one table): a failure counts only when the child recorded a
    traceback raised in runtime code.  SAF: an invariant violation or any other runtime failure FAILS, an SAF job
    without SA.end_step FAILS, an SAF failure without a runtime traceback (killed capture, job without its capture
    input, harness / probe exception, no traceback) is unreadable -> INCOMPLETE (rerun).  SAG (report arm, D-K8-1):
    only an invariant / route / stocks violation raised in runtime code FAILS; every other SAG failure (and an SAG job
    without SA.end_step) is reported (item sag_reported, not judged) and does not hold G-EB-2: an SAG label or folder
    with an attempt record is present; an SAG job that sa_jobs never started because its capture failed or lacks job
    inputs is present and reported by its capture record (AMENDMENT_8 §2, sc.sag_capture_attempt).  A capture folder is
    read from capture.json when present (a capture_failed.json beside it is stale, review r3 B-r3-3)."""
    jobs = sorted((sc.sa_out() / 'jobs' / I.tree).glob('*/summary.json'))
    root = sc.sa_out() / 'cap' / I.tree
    folders_seen = sorted({p.parent for name in ('capture.json', 'capture_failed.json') for p in root.glob('**/' + name)})
    rows = {'viol': [], 'other': [], 'unreadable': [], 'sag': []}
    checked, no_checks = 0, []
    for p in jobs:
        s = json.loads(p.read_text(encoding='utf-8'))
        name = p.parent.name
        arm = _arm_of_job(s, name)
        if arm is None:
            if not s.get('ok'):                                # a failed run whose arm cannot be told
                rows['unreadable'].append([name, None, 'arm unknown', (s.get('error') or '')[-200:]])
            continue
        if arm not in sc.KEYED_ARMS:
            continue
        checked += 1
        sag = arm != sc.JUDGING_ARM
        tail = (s.get('error') or '')[-200:]
        absent = sc.job_input_absent(s, I.tree)
        if absent is not None:                                 # no capture input: not a result (B-r4-1)
            rows['sag' if sag else 'unreadable'].append([name, 'input_absent', 'job input absent (capture missing): '
                                                         + str(absent), tail])
        elif not s.get('ok'):
            bucket, row = g2_failed_row(name, arm, s, tail)
            rows[bucket].append(row)
        elif not (s.get('sa') or {}).get('end_step_calls'):
            if sag:
                rows['sag'].append([name, None, 'SAG job without SA.end_step (reported)', ''])
            else:
                no_checks.append(name)
    for d in folders_seen:
        arm = _arm_of_cap(d)
        if arm not in sc.KEYED_ARMS:
            continue
        rel = str(d.relative_to(sc.sa_out()))
        checked += 1
        name = 'capture.json' if (d / 'capture.json').is_file() else 'capture_failed.json'
        try:                          # capture_failed.json beside a capture.json is stale (B-r3-3)
            r = json.loads((d / name).read_text(encoding='utf-8'))
        except ValueError as exc:     # review r8 N-r8-2: a truncated record is an unreadable folder (INCOMPLETE)
            rows['unreadable'].append([rel, None, f'{name} unreadable ({type(exc).__name__}): rerun the capture', ''])
            continue
        if not isinstance(r, dict):
            rows['unreadable'].append([rel, None, f'{name} is not a JSON object: rerun the capture', ''])
            continue
        if name == 'capture.json' and r.get('ok') is not False:
            continue
        tail = (r.get('error') or r.get('log_tail') or '')[-200:]
        if sc.capture_failure_kind(r) == 'killed':
            rows['sag' if arm != sc.JUDGING_ARM else 'unreadable'].append(
                [rel, 'killed', 'no child record (stopped before its handler)', tail])
            continue
        bucket, row = g2_failed_row(rel, arm, r, tail, capture=True)
        rows[bucket].append(row)
    # AMENDMENT_6 §3 (review N-r2-3): every declared key-on job and capture must be there before G-EB-2 is judged.
    labels, folders, n_sag, sag_jobs, err = declared_runs(I.tree)
    if err is not None:
        absent_jobs, absent_caps, complete = [], [], False
    else:
        absent_jobs = []
        for lb in labels:
            if (sc.job_dir(I.tree, lb) / 'summary.json').is_file():
                continue
            # AMENDMENT_8 §2 (review N-r6-2): an SAG job never started because its capture failed or lacks inputs is
            # present and reported when its capture folder holds an attempt record (AMENDMENT_7 §2)
            attempt = sc.sag_capture_attempt(sag_jobs[lb]) if lb in sag_jobs else None
            if attempt is not None:
                rows['sag'].append([lb, 'not_started', 'SAG job not started: its capture attempt %s (reported, '
                                    'AMENDMENT_8 §2)' % attempt, ''])
            else:
                absent_jobs.append(lb)
        absent_caps = [f for f in folders if not ((Path(f) / 'capture.json').is_file()
                                                  or (Path(f) / 'capture_failed.json').is_file())]
        complete = not absent_jobs and not absent_caps and n_sag == sc.SAG_JOBS_DECLARED
    viol, other, unreadable, sag_reported = rows['viol'], rows['other'], rows['unreadable'], rows['sag']
    readable = complete and not unreadable
    items = {'violations': item(len(viol), 'I1-I11 (+ I10 premise ValueError, I6 assert_stocks) violations raised in '
                                           'runtime code = 0 (SAF and SAG; SAF captures also init)',
                                False if viol else (True if readable else None), rows=viol[:30]),
             'other_failures': item(len(other), 'SAF key-on runs that failed otherwise in runtime code (a runtime '
                                                'traceback recorded by the child, AMENDMENT_7 §2) = 0',
                                    False if other else (True if readable else None), rows=other[:30]),
             'checks_ran': item(len(no_checks), 'every SAF key-on job ran SA.end_step',
                                False if no_checks else (True if readable else None), rows=no_checks[:30]),
             'unreadable_runs': item(len(unreadable), 'no SAF key-on run left unreadable: SAF failure without a '
                                                      'runtime traceback (harness / infrastructure, AMENDMENT_7 §2), '
                                                      'capture killed before its child record (B-r3-3), job ended on '
                                                      'its own missing capture input (B-r4-1), failed run of unknown '
                                                      'arm, truncated / non-object capture record (N-r8-2) -> '
                                                      'INCOMPLETE (rerun), never FAIL',
                                     None if unreadable else (True if complete else None), rows=unreadable[:30]),
             'sag_reported': item(len(sag_reported), 'report: SAG failures other than an invariant violation raised in '
                                                     'runtime code, SAG jobs without SA.end_step, SAG jobs not started '
                                                     'for a failed / input-lacking capture (never hold G-EB-2, '
                                                     'AMENDMENT_7 §2, AMENDMENT_8 §2)', None, judged=False,
                                  rows=sag_reported[:30]),
             'declared_runs': item({'jobs': None if labels is None else len(labels),
                                    'captures': None if folders is None else len(folders), 'sag_jobs': n_sag,
                                    'absent_jobs': len(absent_jobs), 'absent_captures': len(absent_caps)},
                                   'every declared key-on job (all SAF + SAG %d) and capture present (amendment 6 §3; '
                                   'an SAG attempt record counts, AMENDMENT_7 §2; an SAG job not started for its '
                                   'failed / input-lacking capture counts by that capture record, AMENDMENT_8 §2)'
                                   % sc.SAG_JOBS_DECLARED, True if complete else None,
                                   note=err if err is not None else (None if n_sag == sc.SAG_JOBS_DECLARED else
                                                                     f'SAG jobs planned {n_sag} != declared '
                                                                     f'{sc.SAG_JOBS_DECLARED}'),
                                   rows=(absent_jobs + absent_caps)[:30])}
    missing = ['G-EB-2 job ' + lb for lb in absent_jobs] + ['G-EB-2 capture ' + f for f in absent_caps]
    missing += [f'G-EB-2 unreadable run {r[0]} ({r[2]})' for r in unreadable]
    if err is not None:
        missing.append('G-EB-2 declared list: ' + err)
    return gate('G-EB-2', 'invariants I1-I11 every step (key present)', 'every key-on job and capture', items,
                missing=missing,
                notes=[f'key-on runs read: {checked}', 'counts every keyed arm (SAF and SAG): an invariant '
                       'violation is an arm-independent code defect (AMENDMENT_5 §1)', 'judged only with every '
                       'declared key-on job and capture present (AMENDMENT_6 §3)', 'AMENDMENT_7 §2: a failure counts '
                       'only with a runtime traceback recorded by the child (sa_errors); SAF harness / infrastructure '
                       'failures are unreadable (INCOMPLETE, rerun); SAG failures other than an invariant violation '
                       'are reported only; stale capture_failed.json beside capture.json ignored (B-r3-3)'])


# ================================================================================================ G-EB-3
def g3(I, args):
    smoke = I.smoke()
    excl = {tuple(x) for x in ((smoke or {}).get('checks', {}).get('H-5', {}).get('excluded_G_EB_3') or [])}
    n5 = None if smoke is None else (smoke['checks']['H-5'].get('n5_exclusion_ok'))
    states = [st for st in I.fh_states() if st not in excl]
    rows, model, obs, pers, ready, stop, missing, missing_base = [], [], [], [], [], [], [], []
    inc = {off: [] for off in sc.PORTS}
    clusters = []
    for seed, T in states:
        sj = I.jobx('FH', T, J, 'OBS', 3, seed=seed)
        sb = I.jobx('FH', T, 'BASE', 'OBS', 3, seed=seed)
        ref = I.state_ref(seed, T)
        b1, bb = si.block(sj, 1), si.block(sb, 1)
        if b1 is None or ref is None or not ref.get('w_ports_T150') or not ref.get('w_ports_T'):
            missing.append(f'FH s{seed} {T}')
            continue
        m, o, o0 = b1['w_ports']['total'], ref['w_ports_T150']['total'], ref['w_ports_T']['total']
        model.append(m)
        obs.append(o)
        pers.append(abs(o0 - o))
        ready.append(b1['w_ready'])
        stop.append(ref['stop127_T150'])
        row = [seed, T, m, o, o0, b1['w_ready'], ref['stop127_T150']]
        if bb is not None:
            for off in sc.PORTS:
                oo = ref['w_ports_T150'][off]
                inc[off].append(abs(b1['w_ports']['port_' + off] - oo) - abs(bb['w_ports']['port_' + off] - oo))
            clusters.append(seed)
        else:
            missing_base.append(f'FH BASE s{seed} {T}')
        rows.append(row)
    # judging-arm completeness for (a)(b); (c) also needs the comparator BASE (AMENDMENT_5 §1)
    complete = not missing and len(model) == len(states)
    complete_c = complete and not missing_base
    a = ss.pair_stats(model, obs)
    pmae = ss.mean(pers)
    items = {}
    items['N5_exclusions'] = item(sorted(excl), '<= 5 of 45 pre-excluded (H-5), else G-EB-3 fails', n5)
    items['a_bias'] = item(a['bias'], '|mean bias| <= 50', None if not complete or a['bias'] is None
                           else abs(a['bias']) <= sc.G3_BIAS_MAX)
    items['a_mae'] = item(a['mae'], f'MAE <= persistence MAE of the same states ({pmae})',
                          None if not complete or a['mae'] is None else a['mae'] <= pmae)
    b = ss.pair_stats(ready, stop)
    items['b_G6_7'] = item({'bias': b['bias'], 'r': b['r'], 'n': b['n']}, '|b| <= 20 and r >= 0.5',
                           None if not complete or b['bias'] is None
                           else abs(b['bias']) <= sc.G3_G67_BIAS_MAX and b['r'] is not None and b['r'] >= sc.G3_G67_R_MIN)
    cvals, cok = {}, []
    for off in sc.PORTS:
        iid = ss.boot_ci_iid(inc[off], n=sc.BOOT_N, seed=sc.BOOT_SEED)
        clu = ss.boot_ci_cluster(inc[off], clusters, n=sc.BOOT_N, seed=sc.BOOT_SEED)
        cvals[off] = {'iid': iid, 'cluster': clu}
        cok += [iid['lo'] is not None and iid['lo'] <= 0.0, clu['lo'] is not None and clu['lo'] <= 0.0]
    items['c_ports'] = item(cvals, '95 % CI lower bound <= 0 for |err| increment (SAF - BASE), per port, iid and seed '
                                   'cluster bootstrap (2000, seed 0)', None if not complete_c else all(cok))
    # (d) G6-6 W_out on DP and TL3 (declared "DP·TL3 판정, FH 보고")
    for name, pairs in (('d_W_out_DP', [(T, I.jobx('DP', T, J, 'A1', 1)) for T in sc.DP_T]),
                        ('d_W_out_TL3', [(T, I.jobx('TL3', T, J, 'OBS', 3)) for T in sc.GRID9])):
        xs, ys, miss = [], [], 0
        for T, s in pairs:
            bk, r = si.block(s, 1), I.robs3(T + 150)
            if bk is None or r is None or bk.get('w_out_occ') is None:
                miss += 1
                continue
            xs.append(bk['w_out_occ'])
            ys.append(r['wout'])
        st = ss.pair_stats(xs, ys)
        items[name] = item(st, '|b| <= 5', None if miss or st['bias'] is None else abs(st['bias']) <= sc.G3_G66_BIAS_MAX,
                           note='(d) judged: strict reading fixed by AMENDMENT_5 §2-2 (row text "DP·TL3 판정" over the '
                                'verdict column "(a)(b)(c)"); DP and TL3 separately')
    # reports
    xs, ys = [], []
    for seed, T in I.fh_states():
        bk, ref = si.block(I.jobx('FH', T, J, 'OBS', 3, seed=seed), 1), I.state_ref(seed, T)
        if bk is not None and ref and ref.get('wout_T150') is not None:
            xs.append(bk['w_out_occ'])
            ys.append(ref['wout_T150'])
    items['d_W_out_FH_report'] = item(ss.pair_stats(xs, ys), 'report', None, judged=False)
    rep = {}
    for harness, Ts, entry, H in (('DP', sc.DP_T, 'A1', 1), ('TL3', sc.GRID9, 'OBS', 3)):
        xs, ys, r1, r2 = [], [], [], []
        for T in Ts:
            bk, r = si.block(I.jobx(harness, T, J, entry, H), 1), I.robs3(T + 150)
            if bk is None or r is None:
                continue
            xs.append(bk['w_ports']['total'])
            ys.append(r['w_ports']['total'])
            r1.append(bk['w_ready'])
            r2.append(r['stop127'])
        rep[harness] = {'a': ss.pair_stats(xs, ys), 'b': ss.pair_stats(r1, r2)}
    items['a_b_DP_TL3_report'] = item(rep, 'report (gate arrival not oracle there)', None, judged=False)
    base10695 = {}
    for seed, T in I.fh_states():
        cap = I.cap('FH', T, 'BASE', seed=seed)
        if cap and cap.get('ok'):
            base10695[f's{seed}_{T}'] = (((cap.get('probes') or {}).get('provenance') or {}).get('10695') or {}) \
                .get('storage:' + sc.GATE, 0.0)
    items['B1_base_10695_rearrival'] = item(base10695, 'report (AMENDMENT_1 G-EB-3 B1 note)', None, judged=False)
    return gate('G-EB-3', 'one step T+150 (W+ports, G6-7, port increments, G6-6)', 'FH 45 minus H-5 exclusions; '
                'DP 17 / TL3 9 for (d)', items, missing=missing + missing_base, notes=[f'states used {len(model)}', 'rows: seed, T, '
                'model W+ports, FZP T+150, FZP T, W ready, 127 stopped'] + [str(r) for r in rows[:60]])


# ================================================================================================ G-EB-4
def g4(I, args):
    rows, errs, miss, cell9 = [], [], 0, {}
    for T in sc.GRID9:
        s = I.jobx('TL3', T, J, 'OBS', 3)
        b3, r = si.block(s, 3), I.robs3(T + 450)
        if b3 is None or r is None:
            miss += 1
            rows.append([T, None, None, None])
            continue
        e = b3['fw_w_stock'] - r['fw_w_stock']
        errs.append(e)
        rows.append([T, b3['fw_w_stock'], r['fw_w_stock'], e])
        if T in sc.TL3_NONEVENT:
            cell9[T] = b3['cell9_v']
    items = {'per_state': item(rows, '|FW_W(T+450) - VISSIM| <= 50 in 9/9',
                               None if miss else all(abs(e) <= sc.G4_ABS_MAX for e in errs)),
             'cell9_nonevent': item(cell9, 'v(cell 9, T+450) > 60 km/h in the 4 non-event states',
                                    None if len(cell9) != len(sc.TL3_NONEVENT) or any(v is None for v in cell9.values())
                                    else all(v > sc.G4_CELL9_V_MIN for v in cell9.values())),
             'pr_relaxed_report': item({'median_abs': ss.median([abs(e) for e in errs]),
                                        'max_abs': max((abs(e) for e in errs), default=None)},
                                       'report: median <= 50, max <= 150', None, judged=False)}
    rep = {}
    for entry in ('A1',):
        rep[entry] = [[T, (si.block(I.jobx('TL3', T, J, entry, 3), 3) or {}).get('fw_w_stock'),
                       (I.robs3(T + 450) or {}).get('fw_w_stock')] for T in sc.GRID9]
    rep['FH'] = [[s, T, (si.block(I.jobx('FH', T, J, 'OBS', 3, seed=s), 3) or {}).get('fw_w_stock'),
                  ((I.state_ref(s, T) or {}).get('fw_w_stock') or {}).get(str(T + 450))] for s, T in I.fh_states()]
    items['A1_FH_report'] = item(rep, 'report', None, judged=False)
    sag = [[T, (si.block(I.jobx('TL3', T, sc.REPORT_ARM, 'OBS', 3), 3) or {}).get('fw_w_stock'),
            (I.robs3(T + 450) or {}).get('fw_w_stock')] for T in sc.GRID9]
    items['SAG_report'] = item(sag, 'report arm SAG, TL3 9 H3 OBS (never judged, D-K8-1 / AMENDMENT_5 §1)', None,
                               judged=False)
    cells = [((s or {}).get('or_d_w_cell')) for s in (I.jobx('TL3', T, J, 'OBS', 3) for T in sc.GRID9)]
    return gate('G-EB-4', '450 s FW_W', 'TL3 9 H3 OBS (judging arm)', items,
                notes=['OR_D_W cells reported by the worker (cell 9 audit): %s' % cells[:2]])


# ================================================================================================ G-EB-5
def g5(I, args):
    ref31 = (I.ref.get('seeds') or {}).get('31') or {}
    cum = ref31.get('eo_or_d_w_signal_cum') or {}
    cross = ref31.get('eb_crossing_times')
    items, rows = {}, {}
    for T, H in sc.LONG_H.items():
        s = I.jobx('TL3', T, J, 'OBS', H)
        judged = T in sc.LONG_JUDGED
        if not _ok(s):
            for k in ('series', 'stock', 'flow10491', 'eb', 'origin'):
                items[f'{T}_{k}'] = item(None, '-', None, judged=judged)
            continue
        series = g5_series_check(s, T, H)
        items[f'{T}_series'] = item(series, '(T, end] 1 s steps complete, t strictly increasing, recorder_errors [] '
                                            '(AMENDMENT_6 §3; else every item of this job INCOMPLETE)',
                                    True if series['ok'] else None, judged=judged)
        blocks = s['blocks']
        demote_after = None
        for b in blocks:
            if (b.get('blocked_steps') or {}).get('10638', 0.0) > sc.G5_10638_BLOCK_SHARE * sc.BLOCK_SEC:
                demote_after = b['t_end']
                break
        chk = {}
        for t in sc.LONG_CHECKPOINTS:
            k = int(round((t - T) / sc.BLOCK_SEC))
            r = I.robs3(t)
            if k < 1 or k > len(blocks) or r is None:
                chk[t] = None
                continue
            e = blocks[k - 1]['fw_w_stock'] - r['fw_w_stock']
            chk[t] = dict(model=blocks[k - 1]['fw_w_stock'], vissim=r['fw_w_stock'], err=e,
                          demoted=demote_after is not None and t > demote_after)
        judged_chk = [v for v in chk.values() if v is not None and not v['demoted']]
        items[f'{T}_stock'] = item(chk, 'FW_W stock within +-150 at 6300 / 6750 (checkpoints after the first 10638 '
                                        '>50 %-blocked block are report, D-EB-7)',
                                   None if any(v is None for v in chk.values()) else
                                   all(abs(v['err']) <= sc.G5_STOCK_TOL for v in judged_chk), judged=judged,
                                   demote_after=demote_after)
        horizon = H * sc.BLOCK_SEC
        p_flow, v_flow, end, keys_used = g5_flow10491(s, cum, T, H)
        items[f'{T}_flow10491'] = item({'plant_inflow_vph': p_flow, 'vissim_vph': v_flow, 'period_s': [T, end],
                                        'vissim_keys': keys_used,
                                        'plant_release_vph_full_horizon':
                                            sum(b['port_release']['10491'] for b in blocks) * 3600.0 / horizon},
                                       '10491 period mean flow within +-15 %, both sides cut at [T, 8970.1 s] '
                                       '(AMENDMENT_5 §2-4)',
                                       None if (not v_flow or p_flow is None) else
                                       abs(p_flow - v_flow) / v_flow <= sc.G5_FLOW_REL, judged=judged)
        p_eb, v_eb, _end = g5_eb_discharge(s, cross, T, H)
        items[f'{T}_eb'] = item({'plant_vph': p_eb, 'vissim_vph': v_eb, 'period_s': [T, end]},
                                'EB discharge (SG2+SG5) within +-15 %, same period cut (consistency check, N8)',
                                None if (not v_eb or p_eb is None) else abs(p_eb - v_eb) / v_eb <= sc.G5_FLOW_REL,
                                judged=judged)
        omax = max(b['origin_fw_w'] for b in blocks)
        items[f'{T}_origin'] = item(omax, 'FW_W origin queue < 100 over the horizon', omax < sc.G5_ORIGIN_MAX,
                                    judged=judged)
        if not series['ok']:                   # AMENDMENT_6 §3: an incomplete plant record is never judged
            for k in ('stock', 'flow10491', 'eb', 'origin'):
                items[f'{T}_{k}']['pass_'] = None
                items[f'{T}_{k}']['note'] = 'plant record incomplete: ' + '; '.join(series['reasons'])
        rows[T] = demote_after
    a1 = {T: [[b['t_end'], b['fw_w_stock']] for b in (I.jobx('TL3', T, J, 'A1', H) or {}).get('blocks') or []
              if b['t_end'] in sc.LONG_CHECKPOINTS] for T, H in sc.LONG_H.items()}
    items['A1_report'] = item(a1, 'report', None, judged=False)
    return gate('G-EB-5', 'long horizon (2700 H42, 4950 H27 judged; 900 H24 report)', 'TL3 OBS judging arm', items)


def g5_series_check(summary, T, H):
    """AMENDMENT_6 §3 (review N-r2-5): the judged job's plant per-second record over (T, end], end = the G-EB-5 cut.

    steps.t must hold every 1 s step of (T, end] exactly once (count = end - T, values T+1 ... end), be strictly
    increasing over the whole record, and inflow_10491 must be as long as t; the W departure series holds only the
    seconds with a W member departure (sparse by construction), so it is checked strictly increasing; the job's
    recorder_errors must be recorded and empty (the passive recorders swallow their exceptions)."""
    end = sc.g5_period_end(T, H)
    n_expected = int(round(end - float(T)))
    reasons = []
    errs = (summary or {}).get('recorder_errors')
    if errs is None:
        reasons.append('recorder_errors not recorded')
    elif errs:
        reasons.append(f'recorder_errors: {len(errs)}')
    steps = (summary or {}).get('steps') or {}
    ts = steps.get('t')
    window = []
    if ts is None:
        reasons.append('no per-second step record')
    else:
        if any(not (b > a) for a, b in zip(ts, ts[1:])):
            reasons.append('steps t not strictly increasing')
        if len(steps.get('inflow_10491') or []) != len(ts):
            reasons.append('inflow_10491 length differs from t')
        window = [t for t in ts if T < t <= end + 1e-9]
        if len(window) != n_expected or any(abs(t - (T + 1.0 + i)) > 1e-6 for i, t in enumerate(window)):
            reasons.append(f'(T, end] holds {len(window)} steps, not the {n_expected} 1 s steps T+1 ... {end}')
    ws = (summary or {}).get('w_departures_steps') or {}
    if ws.get('t') is None or ws.get('veh') is None or len(ws['t']) != len(ws['veh']):
        reasons.append('no W departure series')
    elif any(not (b > a) for a, b in zip(ws['t'], ws['t'][1:])):
        reasons.append('W departure t not strictly increasing')
    return {'ok': not reasons, 'reasons': reasons, 'steps_in_period': len(window), 'expected_steps': n_expected,
            'period_s': [T, end]}


def g5_flow10491(summary, cum, T, H):
    """Plant 10491 inflow and VISSIM OR_D_W_signal crossings over [T, min(T + H*150, 8970.1)] (AMENDMENT_5 §2-4).

    Returns (plant veh/h | None, VISSIM veh/h | None, plant-clock end, [VISSIM keys]).  The plant side sums the
    per-second landing record of the steps ending in (T, end]; the VISSIM side differences the EO cumulative crossings
    at T + 0.1 and end + 0.1 (8970.1 = the last complete 30 s window): no 9000.1 key is ever looked up."""
    end = sc.g5_period_end(T, H)
    dur = end - T
    a_, b_ = str(round(T + 0.1, 1)), str(round(end + 0.1, 1))
    v = ((cum[b_] - cum[a_]) * 3600.0 / dur) if a_ in cum and b_ in cum else None
    steps = (summary or {}).get('steps') or {}
    ts, flow = steps.get('t'), steps.get('inflow_10491')
    p = None
    if ts is not None and flow is not None and len(ts) == len(flow):
        p = math.fsum(x for t, x in zip(ts, flow) if T < t <= end + 1e-9) * 3600.0 / dur
    return p, v, end, [a_, b_]


def g5_eb_discharge(summary, cross, T, H):
    """Plant W member departures vs VISSIM 127 head crossings (s31) over the same cut period (AMENDMENT_5 §2-5)."""
    end = sc.g5_period_end(T, H)
    dur = end - T
    v = None
    if cross is not None:
        v = sum(1 for t in cross if T + 1e-6 < float(t) - 0.1 <= end + 1e-6) * 3600.0 / dur
    ws = (summary or {}).get('w_departures_steps') or {}
    p = None
    if ws.get('t') is not None and ws.get('veh') is not None and len(ws['t']) == len(ws['veh']):
        p = math.fsum(x for t, x in zip(ws['t'], ws['veh']) if T < t <= end + 1e-9) * 3600.0 / dur
    return p, v, end


# ================================================================================================ G-EB-6
def g6(I, args):
    items, missing = {}, []
    ev, nev = I.event_states(), I.nonevent_states()
    evset = set(ev)
    # (a) AMENDMENT_5 §1: judged on SAF only (45 H3 + 14 event H6, every job present and ok); BASE / SAG reported.
    blocks10481 = {}
    for arm in sc.ARMS:
        row = {'blocked_steps': 0.0, 'n_H3': 0, 'n_H6': 0, 'missing': []}
        for seed, T in I.fh_states():
            for H in (3, 6):
                if H == 6 and (seed, T) not in evset:
                    continue
                if arm == sc.REPORT_ARM and H == 3:
                    continue                                    # SAG runs H6 on the event states only
                v = si.blocked_steps(I.jobx('FH', T, arm, 'OBS', H, seed=seed), '10481')
                if v is None:
                    row['missing'].append(f'FH s{seed} {T} H{H}')
                    continue
                row['blocked_steps'] += v
                row['n_H%d' % H] += 1
        blocks10481[arm] = row
    saf = blocks10481[J]
    complete = (len(ev) == sc.EVENT_STATES_DECLARED and saf['n_H3'] == len(I.fh_states())
                and saf['n_H6'] == len(ev) and not saf['missing'])
    missing += [f'{J} ' + m for m in saf['missing']]
    items['a_10481'] = item({k: (v if k != 'missing' else len(v)) for k, v in saf.items()},
                            '10481 blocked steps = 0 on the judging arm SAF: all 45 FH H3 + all 14 event H6 jobs '
                            '(a missing SAF job -> INCOMPLETE; AMENDMENT_5 §1)',
                            None if not complete else saf['blocked_steps'] == 0)
    items['a_10481_BASE_SAG_report'] = item({arm: {k: (v if k != 'missing' else len(v)) for k, v in blocks10481[arm].items()}
                                             for arm in (sc.COMPARATOR_ARM, sc.REPORT_ARM)},
                                            'report (BASE comparator, SAG report arm; never judged)', None,
                                            judged=False)
    hits_b, b_rows = 0, []
    for seed, T in nev:
        s = I.jobx('FH', T, J, 'OBS', 3, seed=seed)
        x = si.blocked_any(s, '10491', 3)
        if x is None:
            missing.append(f'FH s{seed} {T} H3')
            continue
        hits_b += x
        b_rows.append([seed, T, x, ((s.get('sa') or {}).get('first_block_lanes'))])
    items['b_nonevent'] = item({'blocked_states': hits_b, 'n_states': len(nev)},
                               f'<= {sc.G6_B_MAX_STATES} of the {len(nev)} VISSIM non-event states with 10491 blocking',
                               None if len(b_rows) != len(nev) or len(nev) != sc.NONEVENT_STATES_DECLARED
                               else hits_b <= sc.G6_B_MAX_STATES,
                               rows=b_rows, note='N15 report: first-block lane stock by origin in rows')
    c_rows, c_ok = [], []
    for seed, T in ev:
        s = I.jobx('FH', T, J, 'OBS', 6, seed=seed)
        if not _ok(s):
            missing.append(f'FH s{seed} {T} H6')
            c_ok.append(None)
            continue
        tp = (s.get('first_block_t') or {}).get('10491')
        tv = (I.state_ref(seed, T) or {}).get('ext127_first500')
        if tp is None:
            c_rows.append([seed, T, None, tv, 'not blocked'])
            continue
        ok = tv is not None and tp >= tv - sc.G6_SLACK_S
        c_ok.append(ok)
        c_rows.append([seed, T, tp, tv, ok])
    items['c_timing'] = item(c_rows, 'plant first block >= VISSIM 127 extent >= 500 m first time - 30 s (blocked '
                                     'event states; consistency check, N8)',
                             None if any(o is None for o in c_ok) or len(ev) != sc.EVENT_STATES_DECLARED
                             else all(c_ok))
    hits_e, e_rows = 0, []
    for seed, T in ev:
        x = si.blocked_any(I.jobx('FH', T, J, 'OBS', 3, seed=seed), '10491', 3)
        if x is None:
            continue
        hits_e += x
        e_rows.append([seed, T, x])
    items['e_hit_rate'] = item({'hits': hits_e, 'n': len(e_rows)}, f'>= {sc.G6_E_MIN_HITS} of the 14 VISSIM event '
                               'states with 10491 blocking in [T, T+450]',
                               None if len(e_rows) != len(ev) or len(ev) != sc.EVENT_STATES_DECLARED
                               else hits_e >= sc.G6_E_MIN_HITS,
                               rows=e_rows)
    items['d_report'] = item([[r[0], r[1], (r[2] - r[3]) if (r[2] is not None and r[3] is not None) else None]
                              for r in c_rows], 'report: hit time error (plant - VISSIM); throughput at 3,276 m is not '
                                                'recorded by the worker', None, judged=False)
    sag = {f's{s}_{T}': si.blocked_any(I.jobx('FH', T, sc.REPORT_ARM, 'OBS', 6, seed=s), '10491', 3) for s, T in ev}
    items['SAG_report'] = item(sag, 'report arm (never judged, D-K8-1)', None, judged=False)
    return gate('G-EB-6', 'event regime', 'FH 45 H3 + event 14 H6 (judging arm)', items, missing=missing,
                notes=[f'event states {len(ev)}, non-event {len(nev)} (declared 14 / 31)'])


# ================================================================================================ G-EB-7
def _non_event_blocks(T, H, windows):
    out = []
    for k in range(1, H + 1):
        a, b = T + sc.BLOCK_SEC * (k - 1), T + sc.BLOCK_SEC * k
        if not any(w0 < b and w1 > a for w0, w1 in windows):
            out.append(k)
    return out


def g7(I, args):
    ref31 = (I.ref.get('seeds') or {}).get('31') or {}
    windows = ref31.get('spill_windows_W') or []
    cells30 = ref31.get('eo_cells30_FW_W') or {}
    items = {}
    for T, H in sc.LONG_H.items():
        s = I.jobx('TL3', T, J, 'OBS', H)
        if not _ok(s) or not cells30:
            items[f'{T}_collapse'] = item(None, '0', None)
            items[f'{T}_slow_ratio'] = item(None, '<= VISSIM + 0.05', None)
            continue
        ne = _non_event_blocks(T, H, windows)
        collapse = [b['k'] for b in s['blocks'] if b['k'] in ne and b['vmin_steps_cells_6_9'] > 0]
        items[f'{T}_collapse'] = item(collapse, 'cells 6-9 v_min collapse blocks in VISSIM non-event windows = 0',
                                      len(collapse) == 0)
        samples = dict(zip([round(t, 1) for t in s['samples30']['t']], s['samples30']['fw_w_v']))
        p_slow = v_slow = n_pairs = 0
        for k in ne:
            for cell in sc.SLOW_CELLS:
                vv, pv = [], []
                for j in range(1, 6):
                    t = T + sc.BLOCK_SEC * (k - 1) + 30 * j
                    row = (cells30.get(str(round(t + 0.1, 1))) or {}).get(str(cell))
                    if row and row[1] and row[0] is not None:
                        vv.append(row[0])
                    pvals = samples.get(round(float(t), 1))
                    if pvals is not None and cell < len(pvals) and pvals[cell] is not None:
                        pv.append(pvals[cell])
                if not vv or not pv:
                    continue
                n_pairs += 1
                v_slow += ss.mean(vv) < sc.G7_SLOW_KMH
                p_slow += ss.mean(pv) < sc.G7_SLOW_KMH
        pr, vr = (p_slow / n_pairs, v_slow / n_pairs) if n_pairs else (None, None)
        items[f'{T}_slow_ratio'] = item({'plant': pr, 'vissim': vr, 'pairs': n_pairs, 'non_event_blocks': len(ne)},
                                        'cells 10-30 v < 60 km/h block ratio <= VISSIM + 0.05 (non-event blocks)',
                                        None if pr is None else pr <= vr + sc.G7_RATIO_SLACK)
    items['event_windows_report'] = item(windows, 'report', None, judged=False)
    return gate('G-EB-7', 'FW_W blocking', 'TL3 OBS judging arm (900 H24, 2700 H42, 4950 H27)', items)


# ================================================================================================ G-EB-8
def _axis_sum(tan, key):
    vals = (tan or {}).get('values') or {}
    tot, rows = 0.0, []
    for a in (tan or {}).get('axes') or []:
        if str(a.get('key')) != key:
            continue
        v = vals.get(a['index'], vals.get(str(a['index'])))
        if v is None:
            return None, rows
        scale = float(a.get('scale') or 1.0)
        rows.append([a['index'], a.get('block'), v, scale, a.get('green_vector')])
        tot += v / scale
    return (tot if rows else None), rows


def g8(I, args):
    items, rows, flags, vectors = {}, [], [], {}
    for T in sc.GRID9:
        c00 = si.block(I.jobx('TL3', T, J, 'OBS', 3, variant='C00'), 3)
        c11 = si.block(I.jobx('TL3', T, J, 'OBS', 3, variant='C11'), 3)
        tan = (I.jobx('TL3', T, J, 'OBS', 3, variant='TAN', mode='ad') or {}).get('tangent')
        d = (c11['fw_w_stock'] - c00['fw_w_stock']) if (c00 and c11) else None
        g3_, r3 = _axis_sum(tan, 'p3')
        g4_, r4 = _axis_sum(tan, 'p4')
        sa_last = (I.jobx('TL3', T, J, 'OBS', 3) or {}).get('sa') or {}
        lane3 = (sa_last.get('step_diag_last') or {}).get('stopline_lane_full_steps_3')
        rows.append([T, d, None if g3_ is None else g3_ * sc.G8_GREEN_S,
                     ('no axis' if not r4 else (None if g4_ is None else g4_ * sc.G8_GREEN_S)),
                     lane3, (I.state_ref(31, T) or {}).get('lane3_full_frames_T_T450')])
        vectors[T] = [r[4] for r in r3]
        if T in sc.TL3_NONEVENT:
            flags.append(None if d is None else abs(d) <= sc.G8_DELTA_MAX)
            flags.append(None if g3_ is None else abs(g3_) * sc.G8_GREEN_S <= sc.G8_DELTA_MAX)
    items['nonevent'] = item(rows, '|C11 - C00| FW_W(T+450) <= 3 and |dFW_W/dg_p3| x 6 s <= 3 in the 4 non-event '
                                   'states', None if any(f is None for f in flags) or not flags else all(flags),
                             header=['T', 'C11-C00', 'dp3 x 6', 'dp4 x 6 (N6)', 'lane-3 room-0 steps (N6)',
                                     'VISSIM lane-3 full frames'])
    items['event_sign_report'] = item([r[:3] for r in rows if r[0] in sc.TL3_EVENT], 'report (sign)', None, judged=False)
    items['p3_axis_green_vectors_report'] = item(vectors, 'report: green_vector of the SC1001 p3 axes (the balanced '
                                                 '(+p3, -p4) pair; p4 has no axis of its own, AMENDMENT_5 §2-10)',
                                                 None, judged=False)
    return gate('G-EB-8', 'fictitious lever', 'TL3 non-event 4 states (judging arm)', items,
                notes=['tangent per second = axis derivative / axis scale; p3 axes summed over the blocks '
                       '(sa_common OPERATIONALISATIONS G-EB-8)'])


# ================================================================================================ G-EB-9
def g9(I, args):
    d = I.compare(f'g9_{I.tree}')
    if d is None:
        return gate('G-EB-9', 'K3 / G-SC109 unchanged', 'DP (T11)', {'g9': item(None, 'byte identical', None)})
    r = d['result']
    miss = [T for T, x in r.items() if 'missing' in x]
    ok = None if miss or len(r) != len(sc.DP_T) else all(x['meters'] and x['normalisation'] and x['sc109']
                                                         for x in r.values())
    return gate('G-EB-9', 'K3 / G-SC109 unchanged', 'DP 17 key on/off (T11)',
                {'byte_identical': item({T: [x.get('meters'), x.get('normalisation'), x.get('sc109'),
                                             x.get('n_meters'), x.get('n_sc109')] for T, x in r.items()},
                                        '8 meters service_by_green_veh_h, head-service normalisation, SC109 movements '
                                        'spec + capacity identical with the key on and off', ok)})


# ================================================================================================ G-EB-10
def g10(I, args):
    rep = {}
    for harness, Ts, entry, H, seeds in (('DP', sc.DP_T, 'A1', 1, (None,)), ('TL3', sc.GRID9, 'OBS', 3, (None,)),
                                         ('FH', sc.GRID9, 'OBS', 3, sc.FH_SEEDS)):
        rows = []
        for seed in seeds:
            for T in Ts:
                pair = {arm: I.jobx(harness, T, arm, entry, H, seed=seed) for arm in ('BASE', J)}
                b = {arm: si.block(s, 1) for arm, s in pair.items()}
                if any(v is None for v in b.values()):
                    continue
                cost = {}
                if _ok(pair['BASE']) and _ok(pair[J]):
                    for i, owner in enumerate(pair[J].get('costs_order') or []):
                        cost[owner] = pair[J]['costs'][i] - pair['BASE']['costs'][i]
                sa = (pair[J].get('sa') or {}).get('step_diag_last') or {}
                lane = b[J].get('sa_lane_served') or {}
                tot = sum(lane.values()) if lane else 0.0
                rows.append({'seed': seed, 'T': T,
                             'receivers': {r: [b['BASE']['receivers'].get(r), b[J]['receivers'].get(r)] for r in sc.RECEIVERS},
                             'ramp_queue': {r: [b['BASE']['ramp_queue'][r], b[J]['ramp_queue'][r]] for r in sc.ONE_RAMPS},
                             'e_approach_queue': [b['BASE']['e_approach_queue'], b[J]['e_approach_queue']],
                             'owner_cost_delta': cost,
                             'city_over_room_veh': sa.get('stopline_city_over_room_veh'),
                             'hol_unused_room_veh': sa.get('stopline_hol_unused_room_veh'),
                             'n_access_risk_steps': sa.get('stopline_n_access_risk_steps'),
                             'N9_e_recv_bound_sec': b[J]['e_recv_bound_sec'],
                             'N9_lane2_share': (lane.get('2', 0.0) / tot) if tot else None,
                             'N10_onE_threshold_steps': b[J]['onE_threshold_steps']})
        rep[harness] = rows
    b2 = {}
    for T in sc.DP_FULL_T:
        for arm in ('BASE', J):
            act = I.full_action(T, arm, args.hooks_tag)
            m = (act or {}).get('metadata') or {}
            sel = m.get('joint_leader_selection') or {}
            b2[f'{T}_{arm}'] = {'tangent_resources': [d.get('resources') for d in sel.get('tangent_derivatives') or []],
                                'meter_spill_veh_h': m.get('meter_spill_veh_h'),
                                'kind_service': {k: v for k, v in m.items() if 'kind_service' in k or 'net_inflow' in k}}
    items = {'side_effects_report': item(rep, 'report', None, judged=False),
             'B2_B6_full_decisions_report': item(b2, 'report (SC1001 N_P, meter_spill_veh_h)', None, judged=False)}
    return gate('G-EB-10', 'urban side effects (report)', 'DP / TL3 / FH', items)


# ================================================================================================ G-EB-11
def g11(I, args):
    items = {}
    ratios = []
    for seed, T in I.fh_states():
        a, b = I.jobx('FH', T, J, 'OBS', 3, seed=seed), I.jobx('FH', T, 'BASE', 'OBS', 3, seed=seed)
        if _ok(a) and _ok(b):
            ratios.append(a['wall_sec'] / b['wall_sec'])
    for T in sc.GRID9:
        for entry in sc.ENTRIES:
            a, b = I.jobx('TL3', T, J, entry, 3), I.jobx('TL3', T, 'BASE', entry, 3)
            if _ok(a) and _ok(b):
                ratios.append(a['wall_sec'] / b['wall_sec'])
    med = ss.median(ratios)
    items['wall_ratio'] = item({'median': med, 'pairs': len(ratios)}, 'median H3 wall ratio (SAF / BASE) <= 1.05',
                               None if med is None or len(ratios) < len(I.fh_states()) + 2 * len(sc.GRID9)
                               else med <= sc.G11_WALL_RATIO)
    sizes = {}
    for T in sc.DP_FULL_T:
        ra, rb = I.full_run(T, J, args.hooks_tag), I.full_run(T, 'BASE', args.hooks_tag)
        if ra and rb and ra.get('action_json_bytes') and rb.get('action_json_bytes'):
            sizes[T] = (ra['action_json_bytes'] - rb['action_json_bytes']) / rb['action_json_bytes']
    items['action_json'] = item(sizes, 'action JSON size (SAF vs BASE) <= +1 %',
                                None if len(sizes) != len(sc.DP_FULL_T) else all(v <= sc.G11_JSON_REL for v in sizes.values()))
    unit = parse_unit_log(args.unit_log)
    items['ad_vs_fd_T13'] = unit_item(unit, ('Tangent',), 'T13 (AD vs central difference <= 1e-6)')
    # (d) S3 31 sites + SA fold sites on the hooked SAF full decisions (and BASE attribution, N-A9).  AMENDMENT_7 §3:
    # judged only on a valid instrument of the same run (S3 + fold hook errors 0, every hook file final, no setup
    # error, stopline_approach patched) of a finished run (run.json exit 0 + action JSON); §2: fold-site events never
    # measured (ev_unevaluated > 0) are INCOMPLETE.  An observed exact != 0 S3 event or a dropped fold tangent on a
    # valid S3 count still fails (a count made is real).
    hk = I.hooks()
    d_rows, d_ok, attrib, d_missing = [], [], {}, []
    for T in sc.DP_FULL_T:
        runs = {arm: ((hk or {}).get('runs') or {}).get(f'full_{T}_{arm}') for arm in (J, 'BASE')}
        sa = runs[J]
        if not sa or 'missing' in sa:
            d_ok.append(None)
            d_missing.append(f'G-EB-11(d) hook run full_{T}_{J} absent')
            continue
        s3, ex = sa.get('s3_sites') or {}, sa.get('s3_extra') or {}
        valid = len(s3) >= 31 and not ex.get('anchor_mismatch') and all(v.get('patched', 0) > 0 for v in s3.values())
        exact = {sid: v.get('ev_exact_nonzero', 0.0) for sid, v in s3.items()}
        fold = sa.get('fold_sites') or {}
        dropped = {k: (fold.get(k) or {}).get('dropped', 0.0) for k in sh.RULE3_SITES}
        unevaluated = {k: (fold.get(k) or {}).get('ev_unevaluated', 0) for k in sh.RULE3_SITES
                       if (fold.get(k) or {}).get('ev_unevaluated', 0)}
        problems = hook_run_problems(sa) + g13_run_problems(I, f'full_{T}_{J}', args.hooks_tag)
        if not any(str(p).endswith('stopline_approach') for p in ((sa.get('fold_extra') or {}).get('patched') or [])):
            problems.append('fold sites not patched (no stopline_approach in the SA hook install list)')
        problems += [f'fold site {k} ev_unevaluated {v} (never measured, AMENDMENT_7 §2)'
                     for k, v in unevaluated.items()]
        observed_bad = any(v != 0 for v in exact.values()) or any(v != 0 for v in dropped.values())
        if not valid:
            ok = None
            d_missing.append(f'G-EB-11(d) full_{T}_{J}: S3 count invalid (sites < 31, anchor mismatch or unpatched '
                             'site)')
        elif observed_bad:
            ok = False
        elif problems:
            ok = None
            d_missing.append(f'G-EB-11(d) full_{T}_{J}: ' + '; '.join(problems))
        else:
            ok = True
        d_ok.append(ok)
        d_rows.append([T, valid, {k: v for k, v in exact.items() if v}, dropped,
                       {k: (fold.get('_skip_tiny_port_share') or {}).get(k) for k in ('ev_exact_nonzero',
                                                                                     'abs_dir_tangent_sum')},
                       problems, sum((v or {}).get('ev_unevaluated', 0) for v in s3.values())])
        base = runs['BASE'] or {}
        bs3 = base.get('s3_sites') or {}
        attrib[T] = {sid: {'SAF': exact.get(sid, 0.0), 'BASE': (bs3.get(sid) or {}).get('ev_exact_nonzero'),
                           'tag': ('BASE에도 있음' if (bs3.get(sid) or {}).get('ev_exact_nonzero') else 'SA-F에만 있음')}
                     for sid in exact if exact[sid]}
    items['d_s3_hooks'] = item(d_rows, '31 sites exact != 0 events = 0, SA rule-3 fold sites dropped tape = 0 '
                                       '(2700, 4950) on a valid instrument of a finished run with every fold event '
                                       'measured (AMENDMENT_7 §2-§3, else INCOMPLETE); N-A4 site 4 reported',
                               False if any(o is False for o in d_ok) else
                               (None if any(o is None for o in d_ok) or not d_ok else True), attribution=attrib,
                               row_header=['T', 'S3 count valid', 'S3 exact != 0', 'fold dropped', 'site 4 report',
                                           'instrument / run problems', 'S3 ev_unevaluated (report)'])
    e_rows, e_ok = [], []
    for T, act in sc.AD_FULL:
        s = I.job(sc.job_label('TL3', int(T), J, 'A1', 3, variant='AD' + act, mode='ad_full'))
        if not _ok(s):
            # AMENDMENT_7 §2: a failed SAF job fails only with a runtime traceback; otherwise INCOMPLETE (rerun)
            e_ok.append(None if s is None or not sc.failed_in_runtime(s) else False)
            par = (s or {}).get('s3_parity') or {}
            e_rows.append([T, act, None, None, None if s is None else [sc.record_kind(s), sc.record_site(s)],
                           par.get('excluded_records'), par.get('excluded_by_site'), par.get('sa_created')])
            continue
        err, match = s.get('max_primal_state_error'), s.get('complete_primal_state_match')
        par = s.get('s3_parity')
        if not isinstance(par, dict) or not par.get('installed') or not par.get('compares'):
            # AMENDMENT_10 §2: the comparison is judged through the S3 rule wrapper only; without its record (or when
            # the comparison bypassed it) the job is not readable -> INCOMPLETE (rerun), never PASS
            e_ok.append(None)
            e_rows.append([T, act, err, match, 'no AMENDMENT_10 S3 parity record of the comparison', None, None,
                           None])
            continue
        rule_ok, why = S3P.verdict(par, err, sc.G11_STATE_ERROR)
        e_ok.append(rule_ok and match is True)
        e_rows.append([T, act, err, match, (why or None) if match is True else (why + ['complete match not true']),
                       par.get('excluded_records'), par.get('excluded_by_site'), par.get('sa_created')])
    items['e_state_error'] = item(e_rows, 'non-surrogate AD SAF 2700 REF / M2ALL: state_error <= 1e-8 and complete '
                                          'primal state match (failures: §6-9 cause order, N-A3), compared under '
                                          'the AMENDMENT_10 S3 rule (K8-2 S3 tangent-only zero-primal non-SA ledger '
                                          'records set aside and counted per site; SA-created S3 records 0; any '
                                          'other mismatch fails)',
                                  None if any(o is None for o in e_ok) else all(e_ok),
                                  row_header=['T', 'action', 'state_error', 'complete match',
                                              'failure / rule reasons', 'S3 excluded records', 'S3 excluded by site',
                                              'SA-created S3 calls'])
    return gate('G-EB-11', 'time and derivatives', 'FH/TL3 walls, full decisions, T13, hooks, ad_full', items,
                missing=d_missing + ([] if hk is not None else ['hooks_%s.json' % I.tree]))


# ================================================================================================ G-EB-13
def g13_instrument_problems(run, expected):
    """Review r3 B-r3-4: why a hooked run's capacity-read instrument is not valid (empty list = valid).  A handler
    exception drops its count and only raises hook_errors (sa_hooks note()), so a run counts only with hook_errors =
    patch_errors = 0, an empty SA hook error list, no setup / chain error file, the _movement_capacity_flow patch in
    the install list, and a '<module>:<n> lines' patch for every plant module whose source has n > 0 capacity token
    lines (`expected`, sa_hookcount.line_patch_expected)."""
    fx = run.get('fold_extra')
    if not isinstance(fx, dict):
        return ['no SA hook instrument record (fold_extra)']
    why = []
    for k in ('hook_errors', 'patch_errors'):
        if fx.get(k):
            why.append(f'{k} {fx[k]}')
    if fx.get('errors'):
        why.append(f'SA hook errors ({len(fx["errors"])}): {str(fx["errors"][0])[:160]}')
    if run.get('setup_errors'):
        why.append(f'setup / chain error files ({len(run["setup_errors"])}): {str(run["setup_errors"][0])[:160]}')
    patched = [str(p) for p in (fx.get('patched') or [])]
    if not any(p.endswith(sh.CAPFLOW_PATCH) for p in patched):
        why.append('no patch ' + sh.CAPFLOW_PATCH)
    if not isinstance(expected, dict) or set(expected) != set(sh.PLANT_MODULES):
        why.append('line patch expectation absent (hooks json without line_patch_expected)')
    else:
        for mod, n in sorted(expected.items()):
            if n is None:
                why.append(f'plant source {mod}.py absent under the code root')
            elif n > 0 and not any(re.fullmatch(r'(?:.*\.)?' + re.escape(mod) + f':{int(n)} lines', p) for p in patched):
                why.append(f'no line patch {mod}:{int(n)} lines')
    return why


def g13_run_problems(I, name, hooks_tag):
    """Review r4 B-r4-2: why a judged hooked run did not run to its end (empty list = complete).  The SA hook writes
    its final record at exit (atexit), so a process that stopped before any rollout also leaves 'patched, 0 errors,
    0 plant reads': the hook record alone cannot show that the plant path was exercised.  full_<T>_<arm>: run.json of
    full/<tree>/<T>_<arm>_<hooks_tag> with exit 0 and action_json_bytes > 0; job_<label>: summary.json with ok true
    and sa.end_step_calls > 0."""
    if name.startswith('full_'):
        _, T, arm = name.split('_', 2)
        r = I.full_run(int(T), arm, hooks_tag)
        if r is None:
            return ['run.json absent']
        why = [] if r.get('exit') == 0 else [f'exit {r.get("exit")!r}']
        if not (isinstance(r.get('action_json_bytes'), (int, float)) and r['action_json_bytes'] > 0):
            why.append('no action JSON')
        return why
    s = I.job(name[len('job_'):])
    if s is None:
        return ['summary.json absent']
    why = [] if s.get('ok') is True else ['summary ok %r (%s)' % (s.get('ok'), s.get('error_kind'))]
    calls = (s.get('sa') or {}).get('end_step_calls')
    if not (isinstance(calls, (int, float)) and calls > 0):
        why.append('SA.end_step not called')
    return why


def hook_run_problems(run):
    """K8 amendment 7 §3 (reviews B-r5-2, N-r4-1): why the hook record of a run is not a valid instrument for G-EB-11(d)
    and G-EB-13 beyond g13_instrument_problems (empty list = valid): the chained S3 / site hook files of the same run
    (hook_*.json, s3_extra) with hook_errors = patch_errors = 0 and no errors, the SA hook files (sahook_*.json,
    fold_extra) with hook_errors = patch_errors = 0 and no errors, every hook file of both kinds a final (exit)
    record, and no setup / chain error file.  A hooks json written before the final flags were recorded cannot
    show them -> invalid."""
    why = []
    for label, key in (('S3 hook', 's3_extra'), ('SA fold hook', 'fold_extra')):
        x = run.get(key)
        if not isinstance(x, dict):
            why.append(f'no {label} record ({key})')
            continue
        for k in ('hook_errors', 'patch_errors'):
            if x.get(k):
                why.append(f'{label} {k} {x[k]}')
        if x.get('errors'):
            why.append(f'{label} errors ({len(x["errors"])}): {str(x["errors"][0])[:160]}')
        if 'non_final' not in x:
            why.append(f'{label} final flags not recorded (hooks json before amendment 7; rerun sa_hookcount.py)')
        elif x['non_final']:
            why.append(f'{label} files without their final record: {sorted(x["non_final"])[:5]}')
    if run.get('setup_errors'):
        why.append(f'setup / chain error files ({len(run["setup_errors"])}): {str(run["setup_errors"][0])[:160]}')
    return why


def g13(I, args):
    hk = I.hooks()
    items, plant, diag, leader, rows = {}, {}, {}, {}, []
    runs = (hk or {}).get('runs') or {}
    expected = (hk or {}).get('line_patch_expected')
    # AMENDMENT_6 §3 (review N-r2-2): the judged runs are the full 2700 / 4950 SAF decisions AND the fixed TL3 2700
    # SAF hook job (sc.G13_JUDGED_HOOK_JOB); every other TL3 SAF hook job present is judged with them by the same
    # criterion (plant reads 0).  A judged run that is absent, or has no SA hook record (sa_files 0), is never
    # skipped: it is counted INCOMPLETE (a read never counted cannot make plant_reads 0).  Review r3 B-r3-4: by the
    # same reason a judged run whose instrument is not valid (g13_instrument_problems, and AMENDMENT_7 §3
    # hook_run_problems: S3 / site hook errors 0, every hook file final) is INCOMPLETE.  Review r4 B-r4-2: and a
    # judged run that did not run to its end (g13_run_problems: full run.json exit 0 + action JSON, hook job summary
    # ok + SA.end_step called) is INCOMPLETE, whatever its hook record says.  AMENDMENT_7 §3 positive control: BASE
    # full 2700 / 4950 must show W member plant reads > 0, else INCOMPLETE.  Plant reads > 0 in a judged run fail.
    judged_hook = 'job_' + sc.G13_JUDGED_HOOK_JOB
    tl3 = sorted(k for k in runs if k.startswith('job_TL3_') and f'_{J}_' in k and k != judged_hook)
    names = [f'full_{T}_{J}' for T in sc.DP_FULL_T] + [judged_hook] + tl3
    absent = [n for n in names if n not in runs or 'missing' in runs[n]]
    no_sa = [n for n in names if n not in absent and (runs[n].get('sa_files') or 0) < 1]
    invalid = {n: g13_instrument_problems(runs[n], expected) + hook_run_problems(runs[n])
               for n in names if n not in absent and n not in no_sa}
    invalid = {n: why for n, why in invalid.items() if why}
    unfinished = {n: g13_run_problems(I, n, args.hooks_tag) for n in names}
    unfinished = {n: why for n, why in unfinished.items() if why}
    complete = hk is not None and not absent and not no_sa and not invalid and not unfinished
    for name in names:
        r = runs.get(name) or {}
        cl = r.get('cap_classified') or {}
        for k, v in (cl.get('plant') or {}).items():
            plant[f'{name}: {k}'] = v
        for k, v in (cl.get('diagnostic') or {}).items():
            diag[f'{name}: {k}'] = v
        for k, v in (cl.get('leader_or_other') or {}).items():
            leader.setdefault(k.split(' [', 1)[0], 0.0)
            leader[k.split(' [', 1)[0]] += v
        rows.append([name, sum((cl.get('plant') or {}).values()), sum((cl.get('diagnostic') or {}).values()),
                     sum((cl.get('leader_or_other') or {}).values()), len(cl.get('unresolved_lines') or {})])
    items['plant_reads'] = item(plant, 'W member capacity reads deciding service / admission / allocation in the plant '
                                       'rollout path (UFA, LOR, LC, AFA, SA) = 0 in every judged run (full 2700 / '
                                       '4950 SAF, %s, every other TL3 SAF hook job)' % sc.G13_JUDGED_HOOK_JOB,
                                False if sum(plant.values()) > 0 else (True if complete else None), rows=rows,
                                absent=absent, no_sa_record=no_sa, invalid_instrument=invalid,
                                run_not_finished=unfinished)
    items['diagnostic_reads_list'] = item(diag, 'listed only', None, judged=False)
    review = json.loads(Path(args.leader_review).read_text(encoding='utf-8')) if args.leader_review else None
    if not leader:
        lv = True
    elif review is None:
        lv = None
    else:
        unreviewed = [k for k in leader if k not in review]
        stop = [k for k in leader if (review.get(k) or {}).get('service_rate_in_cost') is True]
        lv = None if unreviewed else (False if stop else True)
    items['leader_reads'] = item(leader, 'leader reads by module:function; one used as a service rate in a candidate '
                                         'selection cost -> STOP, user (manual review file)', lv,
                                 note='STOP_USER when a reviewed read is a cost service rate' if lv is False else None)
    base = {T: ((runs.get(f'full_{T}_BASE') or {}).get('cap_classified') or {}).get('leader_or_other')
            for T in sc.DP_FULL_T}
    items['base_recount_report'] = item({'base': base, 'precount': ((hk or {}).get('precount') or {}).get('path')},
                                        'report (N12: BASE re-count vs P5b pre-count)', None, judged=False)
    control, control_missing = {}, []
    for T in sc.DP_FULL_T:
        r = runs.get(f'full_{T}_BASE')
        if not r or 'missing' in r:
            control[T] = None
            control_missing.append(f'G-EB-13 positive control full_{T}_BASE absent')
            continue
        reads = sum(((r.get('cap_classified') or {}).get('plant') or {}).values())
        control[T] = {'plant_reads': reads,
                      'instrument_problems': g13_instrument_problems(r, expected) + hook_run_problems(r),
                      'run_problems': g13_run_problems(I, f'full_{T}_BASE', args.hooks_tag)}
        if not reads > 0:
            control_missing.append(f'G-EB-13 positive control full_{T}_BASE: 0 W member plant reads (the instrument '
                                   'showed no read where the key-absent plant must read)')
    items['base_plant_reads_control'] = item(control, 'positive control (AMENDMENT_7 §3): BASE full 2700 and 4950 W '
                                                      'member capacity plant reads > 0, else INCOMPLETE (never FAIL)',
                                             None if control_missing else True)
    return gate('G-EB-13', 'consumer audit (B6)', 'full decisions 2700 / 4950 SAF + %s (+ every other TL3 SAF hook '
                'job), hooks' % sc.G13_JUDGED_HOOK_JOB, items,
                notes=[f'runs judged: {names}', 'instrument validity per judged run: hook_errors = patch_errors = 0, '
                       'no SA hook / setup error, %s patched, plant module line patches as expected (review r3 '
                       'B-r3-4); S3 / site hook errors 0 and every hook file final (AMENDMENT_7 §3)'
                       % sh.CAPFLOW_PATCH, 'run completeness per judged run: full run.json exit 0 with an action JSON, '
                       'hook job summary ok with SA.end_step called (review r4 B-r4-2)', 'positive control: BASE full '
                       '2700 / 4950 plant reads > 0 (AMENDMENT_7 §3)'],
                missing=(['hooks_%s.json' % I.tree] if hk is None else [])
                + ['G-EB-13 hook run absent: ' + n for n in absent] + ['G-EB-13 hook run without SA record: ' + n
                                                                        for n in no_sa]
                + ['G-EB-13 hook run with an invalid instrument: %s (%s)' % (n, '; '.join(why))
                   for n, why in invalid.items()]
                + ['G-EB-13 judged run not finished: %s (%s)' % (n, '; '.join(why)) for n, why in unfinished.items()]
                + control_missing)


# ================================================================================================ G-EB-14
def g14_init_row(cap, label, missing):
    """(i) for one capture: True = initialized with install_check, False = an initialization failure (a child-written
    failure record with a runtime traceback, AMENDMENT_7 §2, or metadata without stopline_approach_install_check),
    None = unreadable -> `missing` (no capture / killed / a failure without a runtime traceback; review r4 B-r4-3: an
    ok capture without its metadata block, the capture child found no adapter main frame -- a harness read failure,
    not an SA result)."""
    if cap is None:
        missing.append(label)
        return None
    if not cap.get('ok'):                 # a child-written failure record (I.cap returns None for a killed capture)
        if sc.failed_in_runtime(cap):    # AMENDMENT_7 §2: an initialization failure raised in runtime code
            return False
        missing.append(f'{label} capture failed without a runtime traceback (site {sc.record_site(cap)}: harness / '
                       'infrastructure, rerun; AMENDMENT_7 §2)')
        return None
    if 'metadata' not in cap:
        missing.append(f'{label} capture metadata absent (not read by the capture child)')
        return None
    return bool(cap.get('ok') and (cap.get('metadata') or {}).get('stopline_approach_install_check') is not None)


def g14_row_problems(cap):
    """Review r4 B-r4-3: why the (ii)(iii) row of a capture cannot be read (empty list = readable).  The capture child
    keeps an ok capture when its probe block raised (probes_error, no probes); reading probes or metadata with a
    default 0 would judge the harness failure (0 vehicles past the head -> PASS, > 0 -> FAIL)."""
    why = []
    if cap.get('probes_error'):
        tail = [ln for ln in str(cap['probes_error']).splitlines() if ln.strip()]
        why.append('capture probes failed: ' + (tail[-1].strip()[:160] if tail else '?'))
    pr = cap.get('probes')
    if not isinstance(pr, dict):
        why.append('capture probes absent')
    else:
        if not isinstance(pr.get('provenance'), dict):
            why.append('probes.provenance absent')
        if (pr.get('records') or {}).get('n10695') is None:
            why.append('probes.records.n10695 absent')
    if 'metadata' not in cap:
        why.append('capture metadata absent')
    else:
        init = (cap.get('metadata') or {}).get('stopline_approach_initial') or {}
        # AMENDMENT_7 §1 / AMENDMENT_8 §1: the kept shares (both branches, and the (d) one alone)
        for key in ('posthead_veh', 'posthead_receiver_shortfall_veh', 'posthead_rehome_shortfall_veh'):
            if init.get(key) is None:
                why.append(f'metadata.stopline_approach_initial.{key} absent')
    return why


def g14(I, args):
    items, rows, missing = {}, [], []
    init_ok = {'ROBS61': [0, 0], 'FH': [0, 0]}
    for T in sc.ROBS61_T:
        cap = I.cap('ROBS61', T, J)
        init_ok['ROBS61'][1] += 1
        if g14_init_row(cap, f'ROBS61 {T}', missing):
            init_ok['ROBS61'][0] += 1
    fh_caps = []
    for seed, T in I.fh_states():
        cap = I.cap('FH', T, J, seed=seed)
        init_ok['FH'][1] += 1
        if g14_init_row(cap, f'FH s{seed} {T}', missing):
            init_ok['FH'][0] += 1
            fh_caps.append((f's{seed}_{T}', cap))
    items['i_init'] = item(init_ok, 'initialization 61/61 and 45/45 with 0 errors, install_check present',
                           None if missing else all(a == b for a, b in init_ok.values()))
    # declared harness rows T9b (deployed captured template) and T9c (scratch-projection equivalence +-1e-9):
    # judged from the unit log of the captured-state tests (AMENDMENT_5 §4, review B-4)
    # AMENDMENT_6 §1: each row also needs the capture provenance of the captures it reads (TL3 BASE; T9c also the
    # T9C scratch) printed in the log and equal to <out>/sa/cap/<tree>/.../capture.json.
    unit = parse_unit_log(args.unit_log)
    items['unit_T9b'] = unit_item(unit, (CAPTURED_TESTS + '::T9b',), 'T9b on the deployed captured template',
                                  provenance=captured_provenance(unit, I.tree, (('TL3', 'BASE'),)))
    items['unit_T9c'] = unit_item(unit, (CAPTURED_TESTS + '::T9c',), 'T9c scratch projection with 10695 in the '
                                  'support table (+-1e-9)',
                                  provenance=captured_provenance(unit, I.tree, (('TL3', 'BASE'), ('T9C', 'BASE'))))
    ok_ii, n_ii = [], 0
    for T in sc.ROBS61_T:
        cap = I.cap('ROBS61', T, J)
        if cap and cap.get('ok'):
            fh_caps.append((f'robs_{T}', cap))
    for name, cap in fh_caps:
        why = g14_row_problems(cap)                       # review r4 B-r4-3: a probe failure is not judged
        if why:
            missing.append(f'G-EB-14 (ii)(iii) row {name}: ' + '; '.join(why))
            rows.append([name] + [None] * 11)
            continue
        pr = cap['probes']
        init = cap['metadata']['stopline_approach_initial']
        prov = pr['provenance']
        p127 = prov.get('127') or {}
        recv = sum(float(v) for k, v in p127.items() if k[len('storage:'):] in sc.RECEIVERS)
        post = float(init['posthead_veh'])
        kept = float(init['posthead_receiver_shortfall_veh'])        # AMENDMENT_7/8 §1: kept as 127 head ready packets
        kept_d = float(init['posthead_rehome_shortfall_veh'])        # AMENDMENT_8 §1: of which the 10695 (d) share
        p10695 = prov.get('10695') or {}
        on10695 = sum(float(v) for k, v in p10695.items()             # AMENDMENT_8 §1: the kept share's W queue
                      if k.startswith('movement:') and k[len('movement:'):] in sc.W_MEMBERS)
        res = {c_: (prov.get(c_) or {}).get('storage:' + sc.GATE, 0.0) for c_ in ('10118', '10368', '10695')}
        rec = pr['records']
        lanes = sum(float(v) for v in ((pr.get('sa') or {}).get('stock') or {}).values())
        ok = (abs(recv - (post - (kept - kept_d))) <= sc.MASS_TOL and all(v == 0.0 for v in res.values())
              and abs(float(p10695.get('storage:SC1001_to_SC2002', 0.0)) + kept_d - float(rec['n10695']))
              <= sc.MASS_TOL and abs(on10695 - kept_d) <= sc.MASS_TOL)
        n_ii += 1
        ok_ii.append(ok)
        rows.append([name, post, kept, kept_d, recv, init.get('posthead_rehomed_veh'), res, lanes,
                     lane_stock_target(rec),
                     sum(float(v) for v in ((pr.get('arrival') or {}).get(sc.GATE) or {}).values()),
                     (pr.get('sa') or {}).get('tags_total'), ok])
    items['ii_iii_posthead'] = item(n_ii, 'post-head mass (127 >= head + 10695 in_SC1001_W share) in the receivers '
                                          'up to their room: 127 receiver provenance = posthead_veh - '
                                          '(posthead_receiver_shortfall_veh - posthead_rehome_shortfall_veh) '
                                          '(AMENDMENT_7 §1: the rest stays a 127 head ready packet), no in_SC1001_W '
                                          'on 10118/10368/10695, 10695 receiver share + posthead_rehome_shortfall_veh '
                                          '= its count and the W member queue on 10695 = posthead_rehome_shortfall_veh '
                                          '(AMENDMENT_8 §1: the 10695 share beyond the room stays a lane 3 head ready '
                                          'packet) (+-1e-9); I11 asserted by SA.initialize (a violation '
                                          'fails the capture -> (i)); a row without its probes / metadata '
                                          '(probes_error) is INCOMPLETE (review r4 B-r4-3)',
                                    None if missing or not ok_ii else all(ok_ii), rows=rows,
                                    header=['state', '|A|', 'kept as 127 head packets (shortfall (a)+(d))',
                                            'of which 10695 (d)', '127 -> receivers', '10695 rehomed',
                                            'in_SC1001_W residual 10118/10368/10695', 'sum SA stock',
                                            'N127+N10777-|A|+N_tail129+M_other+N_shortfall_kept (AMENDMENT_5 §3, '
                                            'AMENDMENT_7/8 §1)', 'in_SC1001_W arrivals', 'sum tags', 'ok'])
    # AMENDMENT_7/8 §1: how often a post-head share exceeded its receiver's room, counted on the real captures
    kept_rows = [[r[0], r[2], r[3]] for r in rows if isinstance(r[2], (int, float)) and r[2] > 0.0]
    items['posthead_shortfall_report'] = item({'captures_read': n_ii, 'captures_with_shortfall': len(kept_rows),
                                               'kept_veh_total': sum(r[1] for r in kept_rows),
                                               'kept_10695_veh_total': sum(r[2] for r in kept_rows)},
                                              'report: post-head shares kept as 127 head packets for want of receiver '
                                              'room, branches (a) and (d) (AMENDMENT_7/8 §1 frequency)', None,
                                              judged=False, rows=kept_rows[:60])
    return gate('G-EB-14', 'post-head vehicles (B8 + B1)', 'R-obs3 61 key-on captures, FH 45 captures (SAF), unit '
                'T9b / T9c (captured-state tests)', items, missing=missing)


GATES = {'G-EB-0': g0, 'G-EB-1': g1, 'G-EB-2': g2, 'G-EB-3': g3, 'G-EB-4': g4, 'G-EB-5': g5, 'G-EB-6': g6,
         'G-EB-7': g7, 'G-EB-8': g8, 'G-EB-9': g9, 'G-EB-10': g10, 'G-EB-11': g11, 'G-EB-13': g13, 'G-EB-14': g14}
JUDGED_FOR_PROMOTION = ('G-EB-0', 'G-EB-1', 'G-EB-2', 'G-EB-3', 'G-EB-4', 'G-EB-5', 'G-EB-6', 'G-EB-7', 'G-EB-8',
                        'G-EB-9', 'G-EB-11', 'G-EB-13', 'G-EB-14')     # G-EB-10 report, G-EB-12 = J1


def combine(results):
    vs = {gid: results[gid]['verdict'] for gid in JUDGED_FOR_PROMOTION if gid in results}
    if any(v == 'FAIL' for v in vs.values()):
        return 'STOP'
    if len(vs) == len(JUDGED_FOR_PROMOTION) and all(v == 'PASS' for v in vs.values()):
        return 'PROMOTE_ELIGIBLE'
    return 'INCOMPLETE'


def _fmt(v):
    s = json.dumps(v, default=str) if not isinstance(v, (int, float, str, type(None))) else (
        f'{v:.6g}' if isinstance(v, float) and math.isfinite(v) else str(v))
    return s if len(s) <= 160 else s[:157] + '...'


def write_md(path, res):
    lines = [f'# SA gates ({res["tree"]}, judging arm {J})', '', f'combined (§3.3): **{res["combined"]}**', '',
             sc.md_table(['gate', 'verdict', 'harness'], [[g['id'], g['verdict'], g['harness']]
                                                          for g in res['gates'].values()]), '']
    for g in res['gates'].values():
        lines += [f'## {g["id"]} {g["title"]}: {g["verdict"]}', '', g['harness'], '']
        lines.append(sc.md_table(['item', 'judged', 'pass', 'threshold', 'value'],
                                 [[k, it['judged'], it['pass_'], it['threshold'], _fmt(it['value'])]
                                  for k, it in g['items'].items()]))
        if g['missing']:
            lines.append('\nmissing: ' + ', '.join(g['missing'][:20]))
        if g['notes']:
            lines.append('\nnotes: ' + ' / '.join(str(n) for n in g['notes'][:6]))
        lines.append('')
    lines += ['## harness operationalisations (fixed in sa_common.py before any gate output)', '']
    lines += [f'- {k}: {v}' for k, v in sc.OPERATIONALISATIONS.items()]
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    ap = c.parser(__doc__)
    ap.add_argument('--tree', default='k86')
    ap.add_argument('--base-tree', default='k85')
    ap.add_argument('--evidence-log')
    ap.add_argument('--unit-log', action='append', help='repeatable (AMENDMENT_6 §1)')
    ap.add_argument('--leader-review')
    ap.add_argument('--hooks-tag', default='hooks')
    ap.add_argument('--only', help='comma list of gate ids')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    dest = sc.sa_out() / 'gates' / f'gates_{args.tree}.json'
    wanted = [g for g in GATES if not args.only or g in args.only.split(',')]
    if args.dry_run:
        print('DRY gates', wanted, '->', dest)
        return 0
    I = si.Inputs(args.tree, args.base_tree)
    results = {}
    for gid in wanted:
        try:
            results[gid] = GATES[gid](I, args)
        except Exception as exc:
            import traceback
            results[gid] = gate(gid, 'calculator error', '-', {'error': item(repr(exc), '-', None)},
                                notes=[traceback.format_exc()[-1500:]])
    unit = parse_unit_log(args.unit_log)
    res = {'schema': 'k8-sa-gates/v1', 'tree': args.tree, 'base_tree': args.base_tree, 'judging_arm': J,
           'combined': combine(results) if not args.only else 'PARTIAL', 'gates': results,
           'operationalisations': sc.OPERATIONALISATIONS, 'missing_inputs': sorted(set(I.missing)),
           'unit_logs': None if unit is None else {
               'missing': unit['missing'],
               'logs': [dict({k: log[k] for k in ('path', 'sha256', 'session', 'failure_lines', 'attributed',
                                                  'unattributed', 'failed_ids')},
                             provenance_lines=len(log['provenance'])) for log in unit['logs']]}}
    sc.write_json(dest, res)
    write_md(dest.with_suffix('.md'), res)
    print('SA_GATES', res['combined'], {g: r['verdict'] for g, r in results.items()}, '->', dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
