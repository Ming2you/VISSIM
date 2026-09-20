"""Full450s gain test through the existing canonical conservation path.

Diagnostic scoped speed closure for port-free cells15..20 only. No adapter
copy, default change, future traffic, native run or direct cost correction.
"""
from pathlib import Path
import ast, copy, hashlib, json, sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import speed_population as p
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import urban_route_transport as urban
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups


def main():
    out = p.d.HERE / 'coupled_population_work_v1'
    original = PhysicalLaneGroups.advance
    model_path = p.d.HERE / 'crossseed_population_v1/nc33_full_model.json'
    doc = p.d.e.load(model_path)
    grid = np.array(doc['grid'])
    speeds = np.tile(grid, 3)
    kernels = {ast.literal_eval(k): np.array(v) for k, v in doc['kernels'].items()}
    initial_path = p.d.HERE / 'speed_population_increment_s10_mean_speed_v1/initials.json'
    initial = p.d.e.load(initial_path)['none']['2400']['populations']
    geometry_path = p.d.H / 'controller_response_s23_v1/none/geometry.json'
    geometry = p.d.e.load(geometry_path)
    geo = {r['cell']: r for r in geometry['cells'] if r['road'] == 'FW_E'}
    traces = []
    calls = 0

    def advance(self, state, control, demand, cfg, **kw):
        nonlocal calls
        if self.road != 'FW_E':
            return original(self, state, control, demand, cfg, **kw)
        assert self.sec == 1.
        assert all(len(self.n[c]) == 1 for c in p.m.CELLS)
        assert all(c not in self.partitions for c in p.m.CELLS)
        if not hasattr(self, '_diagnostic_population'):
            assert state.time_sec == 2400
            self._diagnostic_population = {c: np.array(initial[str(c)]) for c in p.m.CELLS}
            self._diagnostic_previous14 = self.v[14][0]
        old = {c: v.copy() for c, v in self._diagnostic_population.items()}
        stats = {c: p.moments(v, grid) for c, v in old.items()}
        for c in p.m.CELLS:
            assert abs(stats[c]['n'] - self.n[c][0]) < 1e-7
            assert abs(stats[c]['v'] - self.v[c][0]) < 1e-7
        n14 = sum(self.n[14])
        v14 = sum(n*v for n, v in zip(self.n[14], self.v[14])) / n14 if n14 else self.v[14][0]
        source_phase = p.phase(v14, self._diagnostic_previous14)
        old_row_count = len(self.rows)
        # Original allocation uses old stock/speed. Its METANET speed update
        # is replaced below only after all accepted transfers are available.
        answer = original(self, state, control, demand, cfg, **kw)
        rows = {r['cell']: r for r in self.rows[old_row_count:] if r['cell'] in p.m.CELLS}
        assert set(rows) == set(p.m.CELLS)
        outgoing, reacted = {}, {}
        for c, row in rows.items():
            assert abs(row['merge_in_veh']) + abs(row['off_out_veh']) + abs(row['exchanged_veh']) < 1e-10
            amount = row['mainline_out_veh']
            weights = old[c] * speeds
            if weights.sum() == 0:
                assert amount < 1e-10
                outgoing[c] = np.zeros_like(weights)
            else:
                outgoing[c] = weights * (amount / weights.sum())
            assert np.all(outgoing[c] <= old[c] + 1e-9)
            kernel = kernels[p.contexts(stats, c, geo, 'mean_speed')]
            reacted[c] = outgoing[c] @ kernel
        for c, row in rows.items():
            kernel = kernels[p.contexts(stats, c, geo, 'mean_speed')]
            remaining = (old[c] - outgoing[c]) @ kernel
            if c == 15:
                incoming = np.zeros_like(remaining)
                for node, weight in p.encode(v14, source_phase, grid):
                    incoming[node] += weight * row['longitudinal_in_veh']
            else:
                incoming = reacted[c-1]
                assert abs(incoming.sum() - row['longitudinal_in_veh']) < 1e-8
            population = remaining + incoming
            assert np.all(population >= -1e-9)
            actual = p.moments(population, grid)
            residual = actual['n'] - self.n[c][0]
            assert abs(residual) < 1e-7
            assert actual['sd']**2 <= actual['v'] * (grid[-1]-actual['v']) + 1e-7
            self._diagnostic_population[c] = population
            self.v[c][0] = actual['v']
            row['v_kmh'] = actual['v']
            state.freeway_speed['FW_E'][c] = actual['v']
            state.freeway_flow['FW_E'][c] = actual['n'] * actual['v'] / self.lengths[c]
            traces.append(dict(forecast=calls//450, time_s=state.time_sec+self.sec, cell=c,
                n=actual['n'], v=actual['v'], sd=actual['sd'], mass_residual=residual,
                incoming_veh=row['longitudinal_in_veh'], outgoing_veh=row['mainline_out_veh']))
        self._diagnostic_previous14 = v14
        calls += 1
        return answer

    files = [Path(__file__), Path(p.__file__), Path(urban.__file__), model_path, initial_path, geometry_path,
             p.d.ROOT/'evaluation/controllers/physical_lane_groups.py',
             p.d.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
             p.d.ROOT/'evaluation/controllers/physical_ramp_boundary.py', urban.e.CAL/'canonical_harness.py']
    frozen = {str(path.relative_to(p.d.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    p.d.e.save(out / 'protocol.json', dict(pins=frozen, train_seed=33, test_seed=23, cutoff_s=2400, horizon_s=450,
        causal_inputs_only=True, candidate_scope='Port-free downstream6cells speed distribution closure; canonical accepted flows and costs preserved.',
        upstream_population_approximation='Each actual predicted incoming cohort fromcell14 carries its model mean speed and previous-step acceleration class; no native future speed distribution.',
        source_transition='NCseed33 full recorded4500s; inspected development seed, no fresh holdout claim.',
        disabled_reference='Full prediction JSON must exactly match transport_step1_exchange_off_v2 before candidate execution.',
        qualified=False))
    options = dict(lateral_access=True, prefer_receiving=True, trace_limits=True, network_exit_intent=True,
        current_exit_intent=True, branch_partition='on', branch_exchange='off', partition_context='on', transport_step=1)
    reference_name = 'coupled_population_reference_v1'
    urban.run_probe(**options, output_name=reference_name)
    for arm in ('none', 'rm_ramp', 'vsl', 'both'):
        assert p.d.e.load(p.d.HERE/reference_name/f'prediction_{arm}.json') == p.d.e.load(p.d.HERE/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json')
    print('EXACT_REFERENCE_4', flush=True)
    candidate_name = 'coupled_population_candidate_v1'
    PhysicalLaneGroups.advance = advance
    try:
        urban.run_probe(**options, output_name=candidate_name)
    finally:
        PhysicalLaneGroups.advance = original
    assert calls == 1800
    reference = p.d.e.load(p.d.HERE/reference_name/'result.json')
    candidate = p.d.e.load(p.d.HERE/candidate_name/'result.json')
    for name, digest in frozen.items():
        assert hashlib.sha256((p.d.ROOT/name).read_bytes()).hexdigest() == digest
    p.d.e.save(out/'trace.json', traces)
    p.d.e.save(out/'result.json', dict(status='COUPLED450S_GAIN_CANDIDATE_NOT_QUALIFIED', calls=calls,
        population_cell_transitions=len(traces), max_mass_residual=max(abs(r['mass_residual']) for r in traces),
        reference_costs=reference['costs'], candidate_costs=candidate['costs'],
        reference_deltas=reference['deltas'], candidate_deltas=candidate['deltas'],
        reference_nc_score=reference['summaries']['none']['score'], candidate_nc_score=candidate['summaries']['none']['score'],
        exact_reference_forecasts=4, source_pins_verified=True, qualified=False, new_native_runs=0, production_changes=0))
    print('FULL_GAIN', candidate['deltas'], flush=True)


if __name__ == '__main__':
    main()
