"""Bounded saved 900--1050s ramp audit; no COM, FZP, rollout or fitting."""
import hashlib
import json
from pathlib import Path

from evaluation.controllers import obs150_contract as oc

HERE = Path(__file__).resolve().parent
ROOTS = {
    'current': Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29'),
    'previous': Path('D:/VISSIM_runs/20261004_sdmpc_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29'),
    'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc/decisions_sdmpc31_nc9000_s29'),
}


def main():
    out = HERE / 'first_interval_ramps.json'
    assert not out.exists(), 'Preserve completed evidence'
    pins, arms, initial = {}, {}, None

    def read(path):
        raw = path.read_bytes()
        pins[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    for name, root in ROOTS.items():
        before, after = (read(root / f'state_{t:06d}.json') for t in (900, 1050))
        if initial is None:
            initial = before['vehicle_records']
        assert initial == before['vehicle_records']
        bundle = oc.load_bundle(after)
        assigned = oc.assign_window(bundle.obs, bundle.mer_rows)
        assert assigned.lag_ok and (assigned.start_s, assigned.end_s) == (900, 1050)
        spec = after['obs150']['detector_config']
        detectors, detector_sha = oc.read_detector_csv(spec['path'], spec['sha256'])
        pins[spec['path']] = detector_sha
        boundaries = oc.evaluate_boundaries(bundle.obs, detectors, bundle.frame_end,
                                            bundle.frame_start, bundle.err_rows)
        # The canonical parser verifies the pinned MER/ERR/frame bytes and index.
        removals = oc.window_removals(bundle.err_rows, 900, 1050)
        action = read(root / 'action_000900.json') if name != 'nc' else None
        predicted = action['prediction']['state_summary']['ramp_queue'] if action else {}
        if action:
            assert action['prediction']['status'] == 'ok'
            assert action['prediction']['from_sim_sec'] == 900
            assert action['prediction']['target_sim_sec'] == 1050
        ramp_rows = {}
        ramps = sorted({r.ref for r in detectors if r.role == 'ramp_arrival'})
        assert len(ramps) == 8
        for ramp in ramps:
            arrivals = [r for r in detectors if r.role == 'ramp_arrival' and r.ref == ramp]
            links = {r.link for r in arrivals}
            assert len(links) == 1
            link = next(iter(links))
            heads = [r for r in detectors if r.role == 'meter_head' and r.link == link]
            positions = {r.lane: r.pos for r in heads}
            assert set(positions) == {r.lane for r in arrivals}
            frames = [[v for v in b['vehicle_records']['records'] if v['link_no'] == link]
                      for b in (before, after)]
            n0, n1 = map(len, frames)
            pre0, pre1 = [sum(v['position_m'] < positions[v['lane_no']] for v in vs) for vs in frames]
            removed = [v for v in removals if v['link'] == link]
            entry = boundaries['ramp_arrival:' + ramp]
            a = entry.cross
            h = sum(bundle.obs['detectors'][str(r.dcm_no)] for r in heads)
            merged = n0 + a - n1 - len(removed)
            assert merged >= 0
            # Single connector's physical ownership, not all approach traffic.
            if action:
                owner = action['projection_diagnostics']['physical_stock_assignment_by_link'][str(link)]
                assert owner == {'ramp:' + ramp: float(n0)}
            head_events = [e for r in heads for e in assigned.entries[r.dcp_no]]
            row = dict(connector=link,initial_veh=n0,end_veh=n1,
                prehead_initial_veh=pre0,prehead_end_veh=pre1,
                posthead_initial_veh=n0-pre0,posthead_end_veh=n1-pre1,
                arrivals_at_boundary=a,entry_detector_vehs=entry.vehs,
                entry_offset_n_start=entry.n_start,entry_offset_n_end=entry.n_end,
                entry_offset_removals=entry.removed,head_passages=h,
                merge_from_inventory_balance=merged,connector_removals=removed,
                arrival_mer_tail=sum(assigned.tails[r.dcp_no] for r in arrivals),
                head_mer_tail=sum(assigned.tails[r.dcp_no] for r in heads),
                repeated_head_vehicle_ids=len(head_events)-len({e.veh for e in head_events}),
                predicted_end_veh=predicted.get(ramp),
                predicted_end_error_veh=predicted[ramp]-n1 if action else None)
            ramp_rows[ramp] = row
        arms[name] = ramp_rows
    report = dict(status='PASS',window=[900,1050],arms=arms,source_sha256=pins,
        prediction_scope='Saved exact one-step endpoint connector stocks only; detailed predicted arrival/head/merge traces were not recorded.',
        observation_scope='Native detector counts corrected from 1m to connector entry; aggregate merges inferred by stock balance, not direct merge detections.',
        limits=['Pre/post classification is position based; cross-lane movement across unequal head positions can change it.',
                'Current versus previous differs in city commands too; do not attribute every change to RM.',
                'A single 150s endpoint cannot qualify gain, recovery, or all later states.',
                'No future measurements used as prediction inputs; no fit or new forecast.'],
        fzp_read=False,com_calls=0,new_rollouts=0,gain_qualified=False)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for ramp, row in arms['current'].items():
        print(ramp, {k:row[k] for k in ('initial_veh','arrivals_at_boundary','head_passages',
            'merge_from_inventory_balance','end_veh','predicted_end_veh','predicted_end_error_veh')})


if __name__ == '__main__':
    main()
