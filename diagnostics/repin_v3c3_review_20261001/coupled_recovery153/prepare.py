"""One frozen combination of previously identified inlet/recovery proposals."""
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE/'proposal.json').exists()
    pins = {}
    def read(p):
        pins[str(p)] = h.sha(p)
        return h.read(p)
    base = read(h.R/'lane_state132/eval_01/reference_config.json')
    inlet = read(h.R/'recovery19_151/candidate/reference_config.json')
    downstream = read(h.R/'onset_reaction134/candidate/reference_config.json')
    read(h.R/'receiving_lane152/assessment.json')
    read(h.R/'receiving_lane152/lane_balance.json')
    original = copy.deepcopy(base)
    override = base['freeway']['state_response']['FW_E']['cell_overrides']
    override['19']['anticipation']['downstream_lt_local'] = inlet['freeway']['state_response']['FW_E']['cell_overrides']['19']['anticipation']['downstream_lt_local']
    other = downstream['freeway']['state_response']['FW_E']['cell_overrides']['21']
    override['21']['anticipation']['downstream_lt_local'] = other['anticipation']['downstream_lt_local']
    override['21']['delta_merge'] = other['delta_merge']
    differences = []
    def check(a, b, path=''):
        assert type(a) is type(b), path
        if isinstance(a, dict):
            assert a.keys() == b.keys()
            for k in a: check(a[k], b[k], path+'/'+str(k))
        elif isinstance(a, list):
            assert len(a) == len(b)
            for i, (x, y) in enumerate(zip(a, b)): check(x, y, path+'/'+str(i))
        elif a != b: differences.append(dict(path=path, before=a, after=b))
    check(original, base)
    assert {x['path'] for x in differences} == {
        '/freeway/state_response/FW_E/cell_overrides/19/anticipation/downstream_lt_local',
        '/freeway/state_response/FW_E/cell_overrides/21/anticipation/downstream_lt_local',
        '/freeway/state_response/FW_E/cell_overrides/21/delta_merge'}
    candidate = HERE/'candidate'; candidate.mkdir()
    h.save(candidate/'reference_config.json', base)
    manifest = read(h.R/'lane_state132/eval_01/manifest.json')
    manifest['sources']['reference_config'] = dict(path=str((candidate/'reference_config.json').relative_to(h.ROOT)).replace('\\','/'), sha256=h.sha(candidate/'reference_config.json'))
    h.save(candidate/'manifest.json', manifest)
    h.save(HERE/'proposal.json', dict(
        previous_goal_turn='NO_PROGRESS explanation; current152 completes lane-specific receiving and conservation evidence.',
        hypothesis='19 excess inflow and21 slow drainage were corrected in separate conditional fits; combine exactly those frozen proposals once on corrected148 to test their coupled state/receiving feedback.',
        differences=differences, input_sha256=pins,
        no_new_fitting=True, no_future_forecast_inputs=True,
        prior_training='151 fits only67nominal110 current-state5x1s;134 fits only67nominal110 current-state speed response with observed next5s merge as conditional identification label. No observed future input in the autonomous tests.',
        source='Exact corrected148 physical equations. Only three listed coefficients change.21 delta0 is a falsifiable conditional proposal, not proof of absent physical merge friction;23 delta and all accepted-flow constraints remain.',
        budget=dict(parity450=1, autonomous450=8, independent450=0, new_fits=0, native=0, FZP=0),
        gate='Unchanged meaningful paired signs,response>=10%improvement,absolute<=110%,bestchoice regret<=.5,local discharge/merge/wait and conservation. Independent/fullOmega required before adoption.',
        limitations='Both seeds and individual proposals were previously inspected. This is a training interaction test, not holdout, and failure does not justify coefficient-combination grid expansion.'))
    print(differences)


if __name__ == '__main__': main()
