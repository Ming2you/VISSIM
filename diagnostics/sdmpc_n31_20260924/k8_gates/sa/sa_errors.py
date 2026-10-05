"""One failure classification for every K8-6 SA harness record (K8 amendment 7 §2; stdlib only, so the adapter child
sa_cap_child.py and the rollout worker sa_worker.py import it in their own processes, sa_common re-exports it).

kind  error_kind(text): the first key of KINDS found in the traceback text ('Ledger' -> stocks, review N-r4-2: the
      former capture table lacked it); 'other' for any other error, None without a text.
site  error_site(text): where the exception was raised, read from the traceback the child recorded -- the innermost
      frame of the project: 'harness' for the K8 gate harness (any path under k8_gates/: sa_worker, sa_cap_child,
      sa_fh, the hook sites sa_hooks / site / s3site), 'runtime' for the code the deployed adapter path runs:
      evaluation/ (the SA module evaluation/controllers/stopline_approach.py and the adapter included), vendor/, and
      the diagnostics/ modules the runtime imports (metanet_calibration_v1 canonical_harness / extract_observations,
      capture_native_runtime_errors; no other diagnostics/ code runs in a harness process); frames of the standard
      library or of installed packages are skipped (an exception raised in numpy called by runtime code is a runtime
      exception).  None when the text holds no project frame (no traceback recorded).
Amendment 7 §2: an SAF run FAILS only when its child recorded a traceback raised in runtime code (site 'runtime');
every harness / infrastructure cause -- the process died or was stopped (no child record), its input was absent, a
time-out, a failure record written by the parent alone, a probe or harness-stage exception (site 'harness' or None)
-- is INCOMPLETE (rerun).  SAG (report arm, D-K8-1) fails G-EB-2 only for an invariant / route / stocks violation
raised in runtime code; any other SAG failure is reported and does not hold G-EB-2 completeness.
log_error_site(text): the same site for a process log (full adapter runs): only the traceback that ended the process
counts -- the last one in the log, with at most LOG_TRAILING_LINES non-empty lines after its exception line."""
import re

KINDS = (('StoplineInvariantError', 'invariant'), ('StoplineRouteError', 'route'), ('StoplineInitError', 'init'),
         ('StoplineConfigError', 'config'), ('assert_stocks', 'stocks'), ('Ledger', 'stocks'))
INVARIANT_KINDS = ('invariant', 'route', 'stocks')
RUNTIME_DIRS = ('evaluation', 'vendor', 'diagnostics')   # diagnostics/ outside k8_gates/: runtime-imported modules
HARNESS_DIRS = ('k8_gates',)
HARNESS_FILES = ('sitecustomize.py', 'sa_worker.py', 'sa_cap_child.py')
THIRD_PARTY_DIRS = ('site-packages', 'dist-packages')
LOG_TRAILING_LINES = 8
TRACEBACK = 'Traceback (most recent call last):'
_FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line \d+, in ')


def error_kind(text):
    if not text:
        return None
    text = str(text)
    for key, name in KINDS:
        if key in text:
            return name
    return 'other'


def frame_site(path):
    """'runtime' | 'harness' | None (standard library, installed package, <frozen ...>, <string>)."""
    parts = [p for p in str(path).replace('\\', '/').lower().split('/') if p]
    if not parts or parts[-1].startswith('<') or any(p in THIRD_PARTY_DIRS for p in parts):
        return None
    if parts[-1] in HARNESS_FILES or any(p in HARNESS_DIRS for p in parts):
        return 'harness'
    if any(p in RUNTIME_DIRS for p in parts):
        return 'runtime'
    return None


def frames(text):
    return [m.group('path') for m in (_FRAME.match(line) for line in str(text or '').splitlines()) if m]


def error_site(text):
    for path in reversed(frames(text)):
        site = frame_site(path)
        if site is not None:
            return site
    return None


def log_error_site(text, trailing=LOG_TRAILING_LINES):
    """Site of the traceback that ended a process, from its log (None when the log does not end on one)."""
    text = str(text or '')
    at = text.rfind(TRACEBACK)
    if at < 0:
        return None
    lines = text[at:].splitlines()[1:]
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i][:1] in (' ', '\t')):
        i += 1                                              # frame, source and caret lines are indented
    if i >= len(lines):
        return None                                         # cut before the exception line
    after = [ln for ln in lines[i + 1:] if ln.strip()]
    if len(after) > trailing:
        return None                                         # an earlier, handled traceback followed by more output
    return error_site(text[at:])


def classify(text):
    """(kind, site) of a recorded traceback text, as a child writes them into its record."""
    return error_kind(text), error_site(text)


_FRAME_FULL = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)\s*$')


def _runtime_rel(path):
    """The runtime frame path from its runtime folder on (evaluation/..., vendor/..., diagnostics/...), lower case
    with '/', so the same code under two roots compares equal."""
    parts = [p for p in str(path).replace('\\', '/').lower().split('/') if p]
    for i, p in enumerate(parts):
        if p in RUNTIME_DIRS:
            return '/'.join(parts[i:])
    return '/'.join(parts)


def traceback_signature(text):
    """K8 amendment 13 (G-EB-14 R-obs T=1/150, amendment 9 precedent "same place, same exception"): the signature of
    the LAST traceback in `text` = (exception line, runtime frames as (path from the runtime folder, line, function),
    innermost last).  None when the text holds no traceback with an exception line.  Two failures are "identical"
    when their signatures are equal: the same exception type and message and the same runtime call path to the same
    line (harness, standard library and installed-package frames are left out)."""
    text = str(text or '')
    at = text.rfind(TRACEBACK)
    if at < 0:
        return None
    frames_, exc = [], None
    for ln in text[at:].splitlines()[1:]:
        m = _FRAME_FULL.match(ln)
        if m:
            if frame_site(m.group('path')) == 'runtime':
                frames_.append((_runtime_rel(m.group('path')), int(m.group('line')), m.group('func')))
            continue
        if ln.strip() and ln[:1] not in (' ', '\t'):
            exc = ln.strip()                                # the exception line ends the traceback
            break
    if exc is None:
        return None
    return exc, tuple(frames_)
