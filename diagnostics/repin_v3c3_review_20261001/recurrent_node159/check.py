"""Cached three-block node-response diagnosis, not a traffic forecast."""
import itertools
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
BLOCKS = ('request20', 'receiving21', 'merge21')
LO, HI = 2820.1, 2970.1


def main():
    assert not (HERE / 'protocol.json').exists(), 'Preserve any previous attempt'
    protected = h.read(h.R / 'coupled_recovery158/forecast/protocol.json')
    pins = {str(Path(__file__)): h.sha(__file__)}

    def read(path):
        pins[str(path)] = h.sha(path)
        return h.read(path)

    exits = read(h.R / 'exit_sending131/attempt2/steps.json')
    receiving = read(h.R / 'receiving_lane152/steps.json')
    prior = read(h.R / 'exit_recovery156/receiving_probe.json')
    mapping = read(h.F / 'route_inventory/mapping31.json')
    bounds = mapping['freeway_model_links']['FW_E']['segment_bounds_m']
    length_m = bounds[21] - bounds[20]
    exit_lookup = {(e['case'], round(e['start'], 6)): e for e in exits}
    receiving_lookup = {(r['arm'], round(r['lo'], 6)): r for r in receiving if r['lane'] == 1}
    h.save(HERE / 'protocol.json', dict(
        previous_goal_turn='NO_PROGRESS: explained existing131/150. Revalidated158 terminal completion and rejected response; no owned live Python/VISSIM process found.',
        question='Which current-state block loses the native middle150 VSL discharge response after158 fixes early20N/v?',
        prior_checked=['Claude P_PLANT FIFO cautions', '100/101 joint-boundary and lane-density probes',
                       '110 interaction/merge chain', '131 measured requests', '134 population turnover',
                       '136 command exposure', '139 closing-pressure rejection', '156 native receiving', '158 rejected combination'],
        scope='Seed67 RM release110/90,2820.1-2970.1,cell20 exit10483 and21lane1;148 and158 existing forecasts.',
        blocks=dict(request20='Current exit/through requests together; preserve class and speed coupling.',
                    receiving21='Shared lane21 budget before ramp reservation.',
                    merge21='Actual accepted merge reservation; observed5s counts spread uniformly for diagnostic only.'),
        method='Eight algebraic combinations of predicted/native blocks at each saved1s step. Native current5s states held to next sample. No traffic/state integration, fitting or new controller candidates.',
        baseline_contract='All-model formula exactly reproduces saved off acceptance, receiving minus merge, and inactive branch storage in this window.',
        limits=['All-native and hybrid calculations use future observations relative to2670.1, exclusively for cause isolation.',
                'Mixed states need not coexist in a vehicle-conserving trajectory. These are not feasible interventions, capacity estimates or gain predictions.',
                'Merge timing within5s is unknown. Uniform observed merge loses pulse timing; same convention as156.',
                'Permutation-average accounting is a decomposition of this algebraic output, not a causal VISSIM attribution.',
                'Single previously inspected state; no independent validation or fullOmega/SDMPC qualification.'],
        budget=dict(new_rollouts=0, fits=0, native=0, FZP=0, cached_model_arms=4),
        protected_sha256=protected['protected_sha256'], STOP=protected['STOP']))
    h.save(HERE / 'status.json', dict(status='running'))
    all_rows, tables, decompositions = [], [], []
    max_error = 0.
    for model in ('spatial_context148', 'coupled_recovery158'):
        totals = {}
        for arm in ('release', 'release_vsl90'):
            path = h.R / model / 'forecast/training' / ('s67_late_' + arm + '.json.gz')
            pred = read(path)
            diag = pred['diagnostics']['roads'][0]['joint_lane_region']
            rec = {round(r['time_s'], 6): r for r in diag['receiving_rows'] if r['lane'] == 1}
            merge = {round(r['time_s'] - 1., 6): r for r in diag['rows'] if r['cell'] == 21 and r['lane'] == 1}
            junctions = [j for j in diag['junction_rows'] if LO - 1e-6 <= j['time_s'] < HI - 1e-6]
            assert len(junctions) == 150
            sums = {mask: 0. for mask in range(8)}
            for j in junctions:
                t = round(j['time_s'], 6)
                sample = round(LO + 5 * math.floor((t - LO + 1e-6) / 5), 6)
                e, r = exit_lookup[arm, sample], receiving_lookup[arm, sample]
                assert sample <= t + 1e-6 and t < sample + 5 - 1e-6
                model_demand = (j['off_request_veh'], j['through_request_veh'])
                native_demand = (e['qmean'] / 5.,
                    (e['native_lane_n'] - e['n0']) * e['native_lane_v'] / (3.6 * length_m))
                model_supply = rec[t]['accepted_budget_veh']
                native_supply = r['supply_left5'] / 5.
                model_merge = merge[t]['merge_veh']
                native_merge = r['physical_merge'] / 5.
                assert abs(j['off_request_veh'] - j['off_before_veh']) < 1e-9
                assert abs(max(0., model_supply - model_merge) - j['through_receiving_veh']) < 1e-9
                outputs = {}
                for mask in range(8):
                    off, through = native_demand if mask & 1 else model_demand
                    supply = native_supply if mask & 2 else model_supply
                    ramp = native_merge if mask & 4 else model_merge
                    factor = min(1., max(0., supply - ramp) / through) if through > 1e-12 else 1.
                    q = off * factor
                    assert 0. <= q <= off + 1e-10
                    outputs[mask] = q
                    sums[mask] += q
                error = abs(outputs[0] - j['off_accepted_veh'])
                max_error = max(max_error, error)
                assert error < 1e-9
                all_rows.append(dict(model=model, arm=arm, time_s=t, native_sample_s=sample,
                    model_requests=model_demand, native_requests=native_demand,
                    model_supply=model_supply, native_supply=native_supply,
                    model_merge=model_merge, native_merge=native_merge, accepted=outputs))
            expected = next(w for w in prior['windows'] if w['arm'] == arm and abs(w['lo'] - LO) < 1e-6)
            assert abs(sums[7] - expected['left_observed_merge']) < 1e-8
            totals[arm] = sums
        deltas = {m: totals['release_vsl90'][m] - totals['release'][m] for m in range(8)}
        for mask in range(8):
            tables.append(dict(model=model, native_blocks=[b for i,b in enumerate(BLOCKS) if mask & (1 << i)],
                mask=mask, off110=totals['release'][mask], off90=totals['release_vsl90'][mask], difference=deltas[mask]))
        contribution = {b: 0. for b in BLOCKS}
        for order in itertools.permutations(range(3)):
            mask = 0
            for i in order:
                nxt = mask | (1 << i)
                contribution[BLOCKS[i]] += (deltas[nxt] - deltas[mask]) / 6.
                mask = nxt
        residual = deltas[7] - deltas[0] - sum(contribution.values())
        assert abs(residual) < 1e-9
        decompositions.append(dict(model=model, predicted_response=deltas[0], native_conditional_response=deltas[7],
            actual_response=14., permutation_average=contribution, residual=residual,
            interpretation='Algebraic response attribution only; not causal shares or a conservative rollout.'))
    for path, digest in {**pins, **protected['protected_sha256']}.items():
        assert h.sha(path) == digest, path
    assert h.sha(protected['STOP']['path']) == protected['STOP']['sha256']
    h.save(HERE / 'rows.json', all_rows)
    h.save(HERE / 'assessment.json', dict(tables=tables, decompositions=decompositions,
        baseline_steps=600, exact_max_error=max_error, native156_matched=True,
        source_sha256=pins, core=True, STOP=True, adopted=False, goal_complete=False))
    h.save(HERE / 'status.json', dict(status='complete_conditional_diagnostic', new_rollouts=0,
        new_fits=0, native=0, FZP=0, goal='ACTIVE_NOT_QUALIFIED'))
    for row in tables:
        print(row)
    for row in decompositions:
        print(row)


if __name__ == '__main__':
    main()
