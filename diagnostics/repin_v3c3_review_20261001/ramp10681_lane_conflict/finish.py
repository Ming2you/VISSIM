"""Close the bounded candidate, preserve evidence, and restore exact source bytes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = HERE / 'completion.json'
    assert not target.exists()
    a = read(HERE / 'assessment.json')
    tests = read(HERE / 'tests_corrected.json')
    assert a['forecasts'] == 6 and tests['passed'] and tests['tests'] == 33
    previous = read(HERE.parent / 'ramp10681_lane_handoff/completion.json')
    before = read(HERE / 'before.json')
    executed = read(HERE / 'executed_sources.json')
    stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert sha(stop) == previous['stop_sha256']
    for relative, digest in executed.items():
        assert sha(ROOT / relative) == digest, relative
        assert sha(HERE / 'executed_sources' / Path(relative).name) == digest, relative
        assert sha(HERE / (Path(relative).name + '.before')) == before[relative], relative
    # All validations precede restoration; no forecast processes remain active.
    for relative in before:
        (ROOT / relative).write_bytes((HERE / (Path(relative).name + '.before')).read_bytes())
    for relative, digest in before.items():
        assert sha(ROOT / relative) == digest, relative
    for path, digest in previous['previous_production_exact'].items():
        assert sha(Path(path)) == digest, path
    assert sha(stop) == previous['stop_sha256']
    result = dict(
        status='bounded_lane_conflict_candidate_not_adopted_sources_restored',
        goal_status='ACTIVE/NOT_QUALIFIED', tests=33, forecasts=6,
        forecast_compute_sec=a['wall_sec'], fit_calls=0,
        owned_sessions={'92458': 'EXIT0', '44733': 'EXIT0'},
        restored_exact=before, previous_production_exact=previous['previous_production_exact'],
        stop_sha256=sha(stop), new_native=0, new_fzp=0, push=0,
        mass_residual=a['mass_residual'], route_residual=a['route_residual'],
        resource_exceedance=a['resource_exceedance'],
        failures_preserved=['tests.json and tests.log: existing upstream cell incorrectly chosen as missing in fixture; corrected test passes without production relaxation'],
        conclusion='Receiving-lane conflict input improves merge counts107.37->119.03 and121.38->127.01 versus native134/150, but off10643 drainage and local congestion remain wrong; gain qualification fails.',
        next='Honor dynamics before cell calibration: reuse entry/drain/storage and causal transport evidence, separate10643 entry shortage from state-dependent downstream drainage. No repeated coefficient grid; only remaining local speed/recovery residuals warrant bounded cell fitting.',
        user_clarification='Only cell11 three-parameter trial was recalibrated recently, not all31cells; that trial was not adopted. Current work tests physical connections with coefficients fixed.')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ('status', 'tests', 'forecasts', 'forecast_compute_sec')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
