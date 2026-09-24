"""obs150 signal clock (WP-B1, plan B4): exact green intervals of one 150 s window.

Every signal-state change in the run happens at an integer second (PRB g):
COM writes are made only at integer stops and native fixed-time programs
switch at integer program seconds (V0-9 asserts that for the 42 .sig files).
VISSIM updates the signal groups, and with them every signal head, once per
simulation second at its end; vehicles respond to the head in the next time
step (Vissim 2020 manual 2.17.3, p. 616). So one window is 150 one-second slots
(t, t+1], each governed by the update at t:

- native SG: the ``.sig`` program ``prog id=progNo`` (NEW-9). The update at t
  shows the program state at phase (t - offset) mod cycle; see NATIVE_STEP_RULE.
- COM-owned SG: the runner's own log (``start`` + ``write``/``fail``/``own``
  events, CONTRACT 2.3 / 4.3). A write at the stop t reads back at once, but
  the stop comes after the update at t: the heads take it at t+1
  (COM_HEAD_DELAY_S). The slot (t, t+1] therefore holds what the stops up to
  t-1 wrote; ``start`` is the state before the writes at T-150 and an event at
  T-1 reaches only the next window. A ``fail`` makes the SG unverified until
  its next successful ``write``; ``own(true)`` without a write at the same stop
  does too. An ``own`` change moves the owner with the same delay.

The ``.lsa`` file is not used (PRB h: it lacks COM writes and lags).
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_contract import ObsContractError

# V0-4 (diagnostics/obs150_20260924/tests/test_clock_probe.py), probe run PR,
# 750-900 s: gt_sig.csv (SigState read at every 0.1 s pause x, 1500 steps x
# SC1004 SG2/SG5, SC5 SG2 and the COM meter SC9106 SG1) and gt_veh.csv.
# - native: the read at x equals the program state at phase (x - offset) mod
#   cycle, the state at the END of the step (x-0.1, x]: 6000/6000 steps.
#   Transitions show at the integer stop itself (SC1004 SG2 is GREEN first at
#   825.0 = phase 0), and the lead vehicle stopped at each native head moves at
#   s+0.1 (3/3 green starts). So a program green [s, e) in phase seconds is the
#   true-time green (s, e] after the offset shift. 'program_state_at_step_start'
#   (read at x = program at x-0.1) misses both ends of all 3 native greens in
#   the window (6 steps) and is refused.
# - COM (D10): the meter written GREEN at the stop 850 reads back GREEN at 850.0,
#   yet its stopped lead vehicles on both lanes keep speed 0 through 851.0 and
#   move at 851.1, one second after the native case, both lanes alike. The
#   once-a-second head update explains it (the write comes after the update at
#   850), as does the SimRes 1 replay, where COM LDP(t) matched source(t-1)
#   (reports/20260911_decision_runtime/NATIVE_PRESTEP_ALIGNMENT_V2_VALIDATION.md).
#   A COM green written at t and ended by a write at t' is (t+1, t'+1] for the
#   vehicles (CONTRACT 2.3). A runner that emulates a native program through
#   COM must write at t the state of t+1: frame advance 1 (VBS OBS150_FRAME_ADVANCE).
NATIVE_STEP_RULE = 'program_state_at_step_end'
COM_HEAD_DELAY_S = 1
SECONDS_MS = 1000


def _require(condition, message):
    if not condition:
        raise ObsContractError(message)


def _sgkey_order(key):
    sc, sg = key.split('-')
    return int(sc), int(sg)


# --------------------------------------------------------------------------
# .sig -> SigProgram (for Obs150Context.sig_table)
# --------------------------------------------------------------------------
def sig_program_from_file(sc, path, prog_no, *, sha256=None):
    """SigProgram of program prog_no in one .sig file; every time must be a whole second.

    green_s holds, per SG of the program, the merged GREEN spans [start, end) in
    program seconds (0 <= start < end <= cycle); a span that wraps the cycle end
    stays two pieces. An SG that is never green maps to (). The sha256 is of the
    file bytes; pass sha256 to pin it.
    """
    from plant.src.vissim_strict.signal_program import SignalProgramError, parse_sig_definition

    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha256 is not None:
        _require(digest == sha256, f'.sig bytes differ from their pin: {source}')
    try:
        definition = parse_sig_definition(source)
    except SignalProgramError as error:
        raise ObsContractError(f'.sig does not compile: {source}: {error}') from error
    _require(hashlib.sha256(source.read_bytes()).hexdigest() == digest, f'.sig changed while reading: {source}')
    program = definition.programs.get(int(prog_no))
    _require(program is not None, f'{source.name} has no program {prog_no}')
    _require(program.cycle_length_ms % SECONDS_MS == 0 and program.program_offset_ms % SECONDS_MS == 0,
             f'SC {sc} program {prog_no}: cycle/offset are not whole seconds')
    green = {}
    for sg, timeline in program.sg_timelines.items():
        pieces = []
        for interval in timeline.intervals:
            _require(interval.start_ms % SECONDS_MS == 0 and interval.end_ms % SECONDS_MS == 0,
                     f'SC {sc} SG {sg}: a state change is not on a whole second')
            if interval.state != oc.GREEN_STATE:
                continue
            a, b = interval.start_ms // SECONDS_MS, interval.end_ms // SECONDS_MS
            if pieces and pieces[-1][1] == a:
                pieces[-1] = (pieces[-1][0], b)
            else:
                pieces.append((a, b))
        green[str(sg)] = tuple(pieces)
    return oc.SigProgram(str(sc), str(source), digest, int(prog_no), program.program_offset_ms // SECONDS_MS,
                         program.cycle_length_ms // SECONDS_MS, green)


def program_green_at(program, sg, t):
    """Native state of the slot (t, t+1]: program GREEN at phase (t - offset) mod cycle (NATIVE_STEP_RULE)."""
    _require(NATIVE_STEP_RULE == 'program_state_at_step_end', 'Only the V0-4 native step rule is implemented')
    spans = program.green_s.get(str(sg))
    _require(spans is not None, f'SC {program.sc} program {program.prog_no} has no SG {sg}')
    phase = (t - program.offset_s) % program.cycle_s
    return any(a <= phase < b for a, b in spans)


def verify_run_sig_files(sig_table, network_dir, scs):
    """The run network folder holds byte-identical copies of the pinned .sig files."""
    for sc in sorted(scs, key=int):
        program = sig_table[sc]
        copy = Path(network_dir) / Path(program.path).name
        _require(copy.is_file(), f'Run network folder lacks {copy.name} (SC {sc})')
        _require(hashlib.sha256(copy.read_bytes()).hexdigest() == program.sha256,
                 f'Run network .sig of SC {sc} differs from sig_manifest')


# --------------------------------------------------------------------------
# Contract interface (plan 1.9)
# --------------------------------------------------------------------------
def windows(signal_log, sig_table, window, *, network_dir=None, programless_scs=frozenset()):
    """Clocks of every SG listed in signal_log.start over window (T-150, T].

    Returns {'<sc>-<sg>': {'green': [(a, b)...], 'native_sec', 'controlled_sec',
    'unverified_sec', 'complete'}} with integer absolute seconds (a, b].
    signal_log.start is the state before the writes at the stop T-150 and the
    events are the stops T-150 <= t < T (CONTRACT 4.3); the slot (t, t+1] takes
    the events up to t - COM_HEAD_DELAY_S. t=1 (window None) has no closed window
    and returns {}. complete is False when the SG has unverified seconds or the
    runner marked the log incomplete. network_dir (keyword): the run's network
    folder; the .sig of every SC used natively in the window must be
    byte-identical there. programless_scs (keyword): fixed-time SCs of the network
    with no .sig supply file; their native seconds count as unverified. Any other
    native SC missing from sig_table is an error.
    """
    _require(not set(programless_scs) & set(sig_table), 'An SC cannot be both program-less and in sig_table')
    if window is None:
        return {}
    _require(isinstance(window, dict) and set(window) == {'start_s', 'end_s'}, 'window must be {start_s, end_s}')
    start, end = window['start_s'], window['end_s']
    _require(type(start) is int and type(end) is int and end - start == oc.DECISION_INTERVAL_SEC
             and end % oc.DECISION_INTERVAL_SEC == 0, 'A clock window is one 150 s window (T-150, T]')
    oc.validate_signal_log(signal_log, start, end)
    by_key = defaultdict(lambda: defaultdict(list))
    for event in signal_log['events']:
        by_key[f'{event[1]}-{event[2]}'][event[0]].append(event)
    log_complete = signal_log['complete']
    clocks, native_scs = {}, set()
    for key in sorted(signal_log['start'], key=_sgkey_order):
        sc, sg = key.split('-')
        entry = signal_log['start'][key]
        owner = entry['owner']
        state = entry.get('state')
        verified = entry.get('verified', True)
        program = None
        green_slots, native, controlled, unverified = [], 0, 0, 0
        events = by_key.get(key, {})
        for t in range(start, end):
            # the head update at t shows what the stops up to t - 1 wrote (COM_HEAD_DELAY_S)
            for event in events.get(t - COM_HEAD_DELAY_S, ()):
                kind = event[3]
                if kind == 'own':
                    owner = 'com' if event[4] else 'native'
                    state, verified = None, not event[4]
                elif kind == 'write':
                    state, verified = event[4], True
                else:  # fail: the SG state is unknown until the next successful write
                    state, verified = None, False
            if owner == 'native' and sc in programless_scs:
                # A fixed-time SC with no .sig supply file (the ramp meters 9101-9108) has no
                # program to integrate; its native state before the runner owns it is unknown.
                unverified += 1
            elif owner == 'native':
                if program is None:
                    program = sig_table.get(sc)
                    _require(program is not None, f'Native SG {key} has no .sig program in the table')
                    native_scs.add(sc)
                native += 1
                if program_green_at(program, sg, t):
                    green_slots.append(t)
            elif verified:
                controlled += 1
                if state == oc.GREEN_STATE:
                    green_slots.append(t)
            else:
                unverified += 1
        green = []
        for t in green_slots:
            if green and green[-1][1] == t:
                green[-1] = (green[-1][0], t + 1)
            else:
                green.append((t, t + 1))
        clocks[key] = {'green': green, 'native_sec': native, 'controlled_sec': controlled,
                       'unverified_sec': unverified, 'complete': unverified == 0 and log_complete}
    if network_dir is not None and native_scs:
        verify_run_sig_files(sig_table, network_dir, native_scs)
    oc.validate_clocks(clocks, window)
    return clocks


def green_seconds(clock):
    return sum(b - a for a, b in clock['green'])
