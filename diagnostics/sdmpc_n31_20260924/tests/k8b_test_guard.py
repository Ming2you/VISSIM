"""K8b keyed unit tests: which captured states they may open (K8b-0; K8_PREDECLARATION_AMENDMENT_16 r2 section 0.2).

A unit test that runs a K8b key (urban.sc1002w_saturation, urban.stopline_approach.city_arrival, urban.wout_exit_law)
reads only synthetic states or probe-sample captures (PROBE_SAMPLE.json: H3 24 + the long starts s43 2400 / s47 4800).
Before the judging stage a K8b-keyed test never opens a capture, template or replay of a judging state (GRID9 / DP_T of
every seed, the long judged starts, every other R-obs state of the judging seeds 31 / 43 / 47): refuse_judging raises
JudgingStateRefused (an error, never a skip), with the same list as the harness guard (sa_common.k8b_judging_state)."""
import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / 'k8_gates' / 'sa'


class JudgingStateRefused(RuntimeError):
    pass


def _sa_common():
    if str(HARNESS) not in sys.path:
        sys.path.insert(0, str(HARNESS))
    import sa_common
    return sa_common


def refuse_judging(seed, T, what='K8b keyed unit test'):
    """Raise JudgingStateRefused for a judging state (amendment 16 section 0.2); return (seed, T) otherwise."""
    sc = _sa_common()
    if sc.k8b_judging_state(seed, T):
        raise JudgingStateRefused(f'{what}: s{seed} T={T} is a judging state (amendment 16 section 0.2); '
                                  'K8b-keyed unit tests read synthetic states or probe-sample captures only')
    return int(seed), int(T)


def keyed_capture(folder, what='K8b keyed unit test'):
    """A capture folder a K8b-keyed test may read: its capture.json names (harness, seed, T, frame_T); every one of
    (seed, T) and (31, frame_T) must be a probe-sample state.  Returns the folder."""
    folder = Path(folder)
    rec = json.loads((folder / 'capture.json').read_text(encoding='utf-8'))
    seed = rec.get('seed') if rec.get('seed') is not None else 31
    refuse_judging(seed, rec['T'], what)
    if rec.get('frame_T') is not None and int(rec['frame_T']) != int(rec['T']):
        refuse_judging(31, rec['frame_T'], what)
    return folder
