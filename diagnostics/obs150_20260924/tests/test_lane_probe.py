"""WP-B2 on the real probe run (PR): V0-5 (10643 ledger), V0-6 (origin), V0-7 (Edie).

Each test sees only what a decision at T=900 sees: Vehs(Current,6,All), the .mer
chunk between the t750 and t900 raw copies, the snapshots at 750 and 900 and the
.err. The truth is the 0.1 s trajectory gt_veh.csv of (750, 900].
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_lane_support as sup  # noqa: E402
from test_lane_support import c  # noqa: E402

from evaluation.controllers import obs150_lane as lane  # noqa: E402

TRUTH_10643 = {'1': {'10634': 2, '10642': 7}, '2': {'10634': 7, '10635': 9}}   # PR check_stdout (f)


@unittest.skipUnless(sup.probe_available(), 'probe run or v2 network not on this machine')
class Probe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs, cls.rows = sup.probe_obs(900)
        cls.frame_T, cls.frame_prev = sup.probe_frame(900), sup.probe_frame(750)
        cls.err = list(sup.probe_err_rows())
        cls.context = sup.probe_context()
        cls.terms = c.evaluate_boundaries(cls.obs, cls.context.detectors, cls.frame_T, cls.frame_prev, cls.err)
        cls.assignment = c.assign_window(cls.obs, list(cls.rows))

    def test_v0_5_10643_lane_by_destination(self):
        ledger, composition = lane.ledger_10643(self.context, self.terms, self.assignment, list(self.rows), self.err,
                                                self.frame_T, self.frame_prev, strict=True)
        self.assertEqual(ledger['by_lane'], TRUTH_10643)

    def test_v0_5_ledger_equals_the_trajectory_vehicle_by_vehicle(self):
        ledger, _ = lane.ledger_10643(self.context, self.terms, self.assignment, list(self.rows), self.err,
                                      self.frame_T, self.frame_prev, strict=True)
        got = {(v['veh'], v['lane'], v['connector']) for v in ledger['vehicles']}
        self.assertEqual(got, sup.gt_10643_exits())
        self.assertTrue(all(v['label_source'] != 'unidentified' for v in ledger['vehicles']))
        self.assertEqual(self.context.route_destinations_10643, sup.GT_ROUTE_DEST)

    def test_v0_5_station_identity_at_the_10643_exit(self):
        terms = self.terms['x10643_exit:10643']
        self.assertEqual(terms.cross, len(sup.gt_10643_exits()))
        self.assertTrue(terms.lane_exact)

    def test_v0_6_origin_identity_equals_first_appearances(self):
        """link 26 station at 40 m: in_0 = Vehs(40) + N[0,40)(900) - N[0,40)(750) + R."""
        terms = self.terms['source:FW_W']
        truth = sup.gt_first_appearances(26)
        self.assertEqual(terms.cross, len(truth))
        self.assertGreater(terms.n_end + terms.n_start, 0)          # the offset terms are really used
        # The runner's cumulative form (source_cumulative_vehs + N(T) + removals) at T=900.
        vehs = sup.probe_vehs()
        keys = [str(r.dcm_no) for r in self.context.boundaries['source:FW_W']]
        cumulative = {t: sum(vehs[t][k] for k in keys) for t in vehs}
        c_900 = sum(v for t, v in cumulative.items() if t <= 900)
        c_750 = sum(v for t, v in cumulative.items() if t <= 750)
        prev = c.evaluate_boundaries({'sim_sec': 750, 'detectors': {k: vehs[750][k] for k in vehs[750]}},
                                     self.context.boundaries['source:FW_W'], self.frame_prev,
                                     sup.probe_frame(600), self.err)['source:FW_W']
        admitted_900 = c_900 + terms.n_end
        admitted_750 = c_750 + prev.n_end
        self.assertEqual(admitted_900 - admitted_750, len(truth))

    def test_v0_7_edie_residuals(self):
        """Edie link-evaluation entries vs exact entries on 10681 (station) and 10643 (trajectory). Reported."""
        document = __import__('json').loads((sup.PROBE / 'results.json').read_text(encoding='utf-8'))
        volume = {int(r['link']): r['value'] for r in document['checks']['e']
                  if r.get('t') == 900 and r['form'] == 'AVG:LinkEvalSegs\\Volume(Current,6,All)'}
        net = sup.network()
        residuals = {}
        for link, exact in ((10681, self.terms['ramp_arrival:RM_C10681'].cross), (10643, sup.gt_entries(10643))):
            x = net.links[link]
            at_end = [r[3] for r in self.frame_T['vehicles'] if r[1] == link]
            at_start = [r[3] for r in self.frame_prev['vehicles'] if r[1] == link]
            residuals[link] = lane.edie_entries(volume[link], 150, x.length_m, x.eval_segment_m, at_end, at_start) - exact
        self.assertEqual(self.terms['ramp_arrival:RM_C10681'].cross, sup.gt_entries(10681))
        print('V0-7 Edie residuals [veh / 150 s]:', {k: v for k, v in residuals.items()})
        for link, value in residuals.items():
            self.assertLess(abs(value), 1e-6, f'Edie residual of {link} is {value}')

    def test_v0_7_edie_equals_the_station_identity_in_every_window(self):
        """300..1200: Edie entries of 10681 = cross(ramp_arrival); of 10643 = cross(x10643) + stock change."""
        document = __import__('json').loads((sup.PROBE / 'results.json').read_text(encoding='utf-8'))
        net = sup.network()
        for end in range(300, 1201, 150):
            volume = {int(r['link']): r['value'] for r in document['checks']['e'] if r.get('t') == end
                      and r['form'] == 'AVG:LinkEvalSegs\\Volume(Current,%d,All)' % (end // 150)}
            obs, rows = sup.probe_obs(end)
            frame_T, frame_prev = sup.probe_frame(end), sup.probe_frame(end - 150)
            terms = c.evaluate_boundaries(obs, self.context.detectors, frame_T, frame_prev, self.err)
            stock = lambda frame, link: [r[3] for r in frame['vehicles'] if r[1] == link]
            removed = sum(1 for x in c.window_removals(self.err, end - 150, end) if x['link'] == 10643)
            exact = {10681: terms['ramp_arrival:RM_C10681'].cross,
                     10643: terms['x10643_exit:10643'].cross + len(stock(frame_T, 10643))
                     - len(stock(frame_prev, 10643)) + removed}
            for link, count in exact.items():
                x = net.links[link]
                estimate = lane.edie_entries(volume[link], 150, x.length_m, x.eval_segment_m,
                                             stock(frame_T, link), stock(frame_prev, link))
                self.assertAlmostEqual(estimate, count, delta=1e-6, msg=f'{link} at {end}')

    def test_v0_5_tail_vehicles_are_found_in_real_frames(self):
        """The probe has no 10643 exit crossing in (T-1, T] at any T, so the tail branch is
        exercised by withholding the 10643 exit rows of the last 3 s (a .mer lag at that
        point only). The ledger must find those vehicles in the real frame_T (past p on 10643,
        or carrying RD 1126 on 126/10641), put them in their exit lane, leave a vehicle still
        in [p, x] out, and give the same (veh, lane, destination) set as the complete file."""
        x_dcps = {r.dcp_no for r in self.context.boundaries['x10643_exit:10643']}
        found = {'tail': set(), 'segment': set()}
        for end in (1050, 1200):
            with self.subTest(end=end):
                obs, rows = sup.probe_obs(end)
                rows = list(rows)
                frame_T, frame_prev = sup.probe_frame(end), sup.probe_frame(end - 150)
                terms = c.evaluate_boundaries(obs, self.context.detectors, frame_T, frame_prev, self.err)
                full, _ = lane.ledger_10643(self.context, terms, c.assign_window(obs, rows), rows, self.err,
                                            frame_T, frame_prev, strict=True)
                withheld = [r for r in rows if r.dcp in x_dcps
                            and max(t for t in (r.t_entry, r.t_exit) if t is not None) > end - 3]
                self.assertTrue(withheld)
                lagged_obs = sup.clone(obs)
                for r in withheld:
                    if r.ordinal is not None:
                        lagged_obs['mer']['records_cum_by_dcp'][str(r.dcp)] -= 1
                lagged_rows = [r for r in rows if r not in withheld]
                assignment = c.assign_window(lagged_obs, lagged_rows)
                entered = {r.veh for r in withheld if r.ordinal is not None}
                self.assertEqual(sum(assignment.tails[d] for d in x_dcps), len(entered))
                lagged, _ = lane.ledger_10643(self.context, terms, assignment, lagged_rows, self.err,
                                              frame_T, frame_prev, strict=True)
                key = lambda ledger: {(v['veh'], v['lane'], v['connector']) for v in ledger['vehicles']}
                self.assertEqual(key(lagged), key(full))
                via = {v['veh']: v['via'] for v in lagged['vehicles']}
                for veh in entered:
                    if veh in via:
                        self.assertEqual(via[veh], 'tail')
                        found['tail'].add(veh)
                    else:
                        found['segment'].add(veh)
        # Real coverage: 6692 (10641 lane 1), 8108 / 7892 (10641) crossed; 6284 is still on 10643 in [p, x].
        self.assertEqual(found, {'tail': {6692, 8108, 7892}, 'segment': {6284}})

    def test_rule_crosscheck_on_the_probe_run(self):
        """Two points at one position count the same vehicles: RULE 910045-47 = the 26/40 m station."""
        from evaluation.controllers import obs150_observation as ob
        document = __import__('json').loads((sup.PROBE / 'results.json').read_text(encoding='utf-8'))
        rule = {(r['t'], r['dcm']): r['vehs_k'] for r in document['checks']['d'] if 910000 <= r['dcm'] < 911000}
        vehs = sup.probe_vehs()
        pairs = ob.rule_crosscheck_pairs(self.context.detectors)
        self.assertEqual([(n, r.lane) for n, r in pairs], [(910045, 1), (910046, 2), (910047, 3)])
        compared = 0
        for t in sorted(vehs):
            obs = {'detectors': {str(r.dcm_no): vehs[t][str(r.dcm_no)] for r in self.context.detectors},
                   'rule_crosscheck': {str(n): rule[t, n] for n, _ in pairs}}
            compared += len(ob.check_rule_crosscheck(obs, self.context.detectors))
            self.assertGreater(sum(obs['rule_crosscheck'].values()), 0)
        self.assertEqual(compared, 3 * len(vehs))
        obs['rule_crosscheck']['910047'] += 1
        with self.assertRaisesRegex(sup.c.ObsContractError, 'differs from RULE measurement 910047'):
            ob.check_rule_crosscheck(obs, self.context.detectors)

    def test_lag_rule_holds_at_the_decision(self):
        self.assertTrue(self.assignment.lag_ok)
        x_tail = sum(self.assignment.tails[r.dcp_no] for r in self.context.boundaries['x10643_exit:10643'])
        self.assertGreaterEqual(x_tail, 0)


if __name__ == '__main__':
    unittest.main()
