"""One diagnostic: bind ramp admission mixture to the current source lanes.

This is NOT a production option or an independent per-lane node solver. Keep
the existing proportional two-lane receiving bound, coefficients and source
debit; replace only the historical re-mixing at this known physical boundary.
"""
from pathlib import Path
import hashlib, importlib.util, json

HERE = Path(__file__).resolve().parent
P = HERE.parent / 'recovery2700'
read = lambda p: json.loads(p.read_bytes())


def mixture(rows, geometry):
    counts = [0.] * len(geometry['ramp_lanes'])
    for cohort, amount in rows:
        if cohort['target'] != geometry['ramp'] or amount <= 0:
            continue
        shares = cohort['lane68']['shares']
        eligible = sum(shares.get(lane, 0.) for lane in geometry['ramp_lanes'])
        assert eligible > 0
        for lane, index in geometry['ramp_lanes'].items():
            counts[index] += amount * shares.get(lane, 0.) / eligible
    total = sum(counts)
    return counts, tuple(n / total for n in counts) if total else None


def install():
    from evaluation.controllers import route_choice_corridor as rc
    from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime
    original_request, original_commit = rc.known_legsplit_requests, rc.known_legsplit_commit
    original_finish = LaneRampRuntime.finish
    rows, pending = [], {}

    def request(state, cfg, storage, reach, arrived, step):
        result = original_request(state, cfg, storage, reach, arrived, step)
        spec = cfg.network.known_legsplit_routes
        if result is None or storage != spec['storage']:
            return result
        geometry = spec['entry_lane_receiving']; ramp = geometry['ramp']
        assert geometry['ramp_lanes'] == {'1': 0, '2': 1}
        assert not cfg.network.on_ramp_to_movement[ramp]
        assert ramp in cfg.network.gate_onramp_queue_ramps
        sources = [name for name, splits in cfg.network.boundary_out_ramp_split.items()
                   if ramp in splits.get('ramps', {})]
        assert sources == [storage], sources
        buffer = state.lane_ramp_runtime.buffers[ramp]
        assert abs(state.ramp_queue[ramp] - buffer.snapshot()['connector_veh']) < 1e-7
        counts, shares = mixture(state.known_legsplit_route_state['plan']['rows'], geometry)
        assert abs(sum(counts) - result.get(ramp, 0.)) < 1e-7
        historical = buffer.lane_arrival_shares if not rows else rows[0]['historical_shares']
        row = dict(step=step, request_by_lane=counts, historical_shares=list(historical),
                   shares=list(shares or buffer.lane_arrival_shares),
                   room_by_lane=[b.current_admission_space() for b in buffer._lane_buffers])
        rows.append(row); pending[id(state)] = row
        if shares is not None:
            buffer.lane_arrival_shares = shares
        return result

    def commit(state, cfg, receipts, step):
        spec = cfg.network.known_legsplit_routes; geometry = spec['entry_lane_receiving']
        row = pending.get(id(state))
        accepted = sum(n for source, ramp, n in receipts
                       if source == spec['storage'] and ramp == geometry['ramp'])
        before = mixture([(c, c['vehicles'] * rc._known_ramp_lane_share(cfg, c))
                          for c in state.known_legsplit_route_state['cohorts']
                          if c['target'] == geometry['ramp']], geometry)[0]
        result = original_commit(state, cfg, receipts, step)
        after = mixture([(c, c['vehicles'] * rc._known_ramp_lane_share(cfg, c))
                         for c in state.known_legsplit_route_state['cohorts']
                         if c['target'] == geometry['ramp']], geometry)[0]
        if row is not None:
            debits = [a-b for a,b in zip(before,after)]
            assert abs(sum(debits)-accepted) < 1e-7
            assert all(abs(n-accepted*s) < 1e-7 for n,s in zip(debits,row['shares']))
            row.update(accepted=accepted, source_lane_debit=debits,
                       historical_remixing_l1=sum(abs(n-accepted*s)
                           for n,s in zip(debits,row['historical_shares'])))
        else:
            assert accepted == 0
        return result

    def finish(runtime, state):
        row = pending.pop(id(state), None)
        buffer = runtime.buffers['RM_C10681']
        before = [b.cumulative_admitted_veh for b in buffer._lane_buffers]
        result = original_finish(runtime, state)
        admitted = [b.cumulative_admitted_veh-n for b,n in zip(buffer._lane_buffers,before)]
        if row is not None:
            row['ramp_lane_admission'] = admitted
            assert all(abs(a-b) < 1e-7 for a,b in zip(admitted,row['source_lane_debit']))
        else:
            assert abs(sum(admitted)) < 1e-7
        return result

    rc.known_legsplit_requests, rc.known_legsplit_commit = request, commit
    LaneRampRuntime.finish = finish
    return rows


def main():
    import os, sys
    root = HERE.parents[3]
    sys.path[:0] = [str(root), str(root/'vendor/NumSim-mine')]
    for path, expected in read(HERE/'plan.json')['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    os.environ['NUMSIM_REPO_ROOT'] = str(root/'vendor/NumSim-mine')
    loader = importlib.util.spec_from_file_location('fresh2700_canonical', P/'forecast.py')
    forecast = importlib.util.module_from_spec(loader); loader.loader.exec_module(forecast)
    forecast.OUT = HERE/'forecast2700'
    rows = install()
    forecast.main()
    assert rows and all('ramp_lane_admission' in row for row in rows)
    (HERE/'lane_trace.json').write_text(json.dumps(dict(rows=rows, forecasts=1,
        production_changes=False, independent_lane_receiving=False,
        scope='Current predicted source mixture; all other original receiving bounds retained.'),
        indent=2, allow_nan=False)+'\n', encoding='utf8')


if __name__ == '__main__':
    main()
