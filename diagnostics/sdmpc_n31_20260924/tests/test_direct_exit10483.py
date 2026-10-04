"""A committed off-ramp exit must not become a new on-ramp choice."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from evaluation.controllers import route_choice_corridor as rc


class DirectExitTests(unittest.TestCase):
    def test_configuration_is_pinned_to_native_unique_path_and_snapshot(self):
        state,cfg,key = self.fixture(tagged=0.)
        del state.direct_exit_route_state
        del cfg.network.direct_exit_legsplit
        selected = Path(__file__).resolve().parents[1]/'integration_20260926/selected'
        pin = json.loads((selected/'scenario/topology_routes_v2_8ac6fd.json').read_bytes())['network']
        state.lane_offramp_runtime = NS(descriptions={'10483':dict(direct=True,target=key,to_link='124')},
            membership={'10483':True,'124':True})
        cfg.network.physical_ramp_branches = dict(network=pin)
        cfg.network.control_area_enabled = cfg.network.leg_ramp_split_enabled = True
        tuning = dict(urban=dict(preserve_direct_offramp_destinations=True))
        with patch.object(rc,'snapshot_network_sha256',return_value=pin['sha256']):
            evidence = rc.configure_direct_exit_legsplit(cfg,tuning,state,{})
        self.assertEqual(evidence['direct_exit10483_initial_tagged_veh'],0.)
        self.assertEqual(cfg.network.direct_exit_legsplit['native_route'],'1131:3')
        with patch.object(rc,'snapshot_network_sha256',return_value='wrong'):
            with self.assertRaisesRegex(ValueError,'network differs'):
                rc.configure_direct_exit_legsplit(cfg,tuning,state,{})

    def fixture(self, tagged=8., untagged=4., due=10):
        key = 'SC1001_W_out'
        cfg = NS(network=NS(direct_exit_legsplit=dict(storage=key, connector='10483'),
            urban_link_storage_veh={key:100.},
            boundary_out_ramp_split={key:dict(free=.25, ramps={'E':.5,'W':.25})}))
        state = NS(urban_link_storage={key:100.-untagged-tagged},
            urban_storage_release_buffer={key:{due:tagged}},
            direct_exit_route_state=dict(cohorts={},plan=None,received=0.,departed=0.))
        rc.direct_exit_receive(state,cfg,'10483',key,tagged,due)
        return state,cfg,key

    def commit(self, state, cfg, key, amounts, step=10):
        state.urban_link_storage[key] += sum(amounts.values())
        rc.direct_exit_commit(state,cfg,[(key,None if k=='free' else k,v) for k,v in amounts.items()],step)

    def test_only_proven_ready_cohort_is_removed_from_ramp_choices(self):
        state,cfg,key = self.fixture()
        requests = rc.direct_exit_requests(state,cfg,key,6.,12.,10)
        self.assertEqual(requests,dict(E=1.,W=.5,free=4.5))
        self.commit(state,cfg,key,requests)
        self.assertEqual(state.direct_exit_route_state['cohorts'],{10:4.})
        self.assertEqual(100.-state.urban_link_storage[key],6.)

    def test_blocked_exit_preserves_its_tag_and_other_ramp_receipts(self):
        state,cfg,key = self.fixture()
        rc.direct_exit_requests(state,cfg,key,6.,12.,10)
        self.commit(state,cfg,key,dict(E=1.,W=.5,free=0.))
        self.assertEqual(state.direct_exit_route_state['cohorts'],{10:8.})
        self.assertEqual(state.direct_exit_route_state['departed'],0.)
        self.assertEqual(100.-state.urban_link_storage[key],10.5)

    def test_limited_free_service_is_shared_proportionally_not_given_priority(self):
        state,cfg,key = self.fixture()
        rc.direct_exit_requests(state,cfg,key,6.,12.,10)
        self.commit(state,cfg,key,dict(E=.2,W=0.,free=2.25))
        self.assertEqual(state.direct_exit_route_state['cohorts'],{10:6.})
        self.assertEqual(state.direct_exit_route_state['departed'],2.)

    def test_pending_tags_do_not_steal_ready_untagged_sending(self):
        state,cfg,key = self.fixture(due=20)
        self.assertEqual(rc.direct_exit_requests(state,cfg,key,2.,4.,10),dict(E=1.,W=.5,free=.5))
        self.commit(state,cfg,key,dict(E=1.,W=.5,free=.5))
        self.assertEqual(state.direct_exit_route_state['cohorts'],{20:8.})

    def test_receipts_during_body_keep_their_original_due_time(self):
        state,cfg,key = self.fixture()
        requests = rc.direct_exit_requests(state,cfg,key,6.,12.,10)
        state.urban_link_storage[key] -= 3.
        state.urban_storage_release_buffer[key][20] = 3.
        rc.direct_exit_receive(state,cfg,'10483',key,3.,20)
        self.commit(state,cfg,key,requests)
        self.assertEqual(state.direct_exit_route_state['cohorts'],{10:4.,20:3.})
        self.assertEqual(state.direct_exit_route_state['received'],11.)

    def test_missing_reservations_and_mixed_membership_fail(self):
        state,cfg,key = self.fixture(due=20)
        state.urban_storage_release_buffer[key] = {}
        with self.assertRaisesRegex(ValueError,'travel reservation'):
            rc.direct_exit_requests(state,cfg,key,2.,4.,10)
        state._control_area_ledger = NS(stocks={'storage:'+key:dict(outside=1.)})
        with self.assertRaisesRegex(ValueError,'membership'):
            rc._direct_exit_check(state,cfg)

    def test_no_arrived_stock_never_allows_early_tag_departure(self):
        state,cfg,key = self.fixture(untagged=0.)
        with self.assertRaisesRegex(ValueError,'before shared travel'):
            rc.direct_exit_requests(state,cfg,key,0.,0.,10)

    def test_other_sources_other_storages_and_disabled_mode_are_untouched(self):
        state,cfg,key = self.fixture()
        before = copy.deepcopy(vars(state))
        rc.direct_exit_receive(state,cfg,'10682',key,3.,20)
        self.assertIsNone(rc.direct_exit_requests(state,cfg,'SC2001_S_out',2.,4.,10))
        self.assertEqual(vars(state),before)
        del cfg.network.direct_exit_legsplit
        self.assertIsNone(rc.direct_exit_requests(state,cfg,key,6.,12.,10))
        rc.direct_exit_receive(state,cfg,'10483',key,3.,20)
        rc.direct_exit_commit(state,cfg,[(key,'E',2.)],10)
        self.assertEqual(vars(state),before)


if __name__ == '__main__':
    unittest.main()
