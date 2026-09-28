"""C-11 (network v3c1, user approval 2026-09-28, decision D2): the input-1083 source-link routing-decision guard.

physical_movement_routes.configure_native_input_signal_authority refused ANY routing decision on the physical source
link of input 1083 (link 21). Network v3c1 item V1 puts decision 1160 there. The guard now admits exactly the
decisions the pinned declaration names in inputs/1083/reviewed_source_decisions (only 1160), each equal to the
network element (number, link, position, every route's link path) and each route leaving through the declared
connector 10112 to 174; any other decision still refuses. Without the key the rule is the old one (bit-identical).
"""
from __future__ import annotations

import copy
import json
import unittest
import xml.etree.ElementTree as ET

import n31_fixtures as fx
from evaluation.controllers.physical_movement_routes import check_source_routing_decisions, source_decision_record

DECLARATION = fx.N31D / 'scenario/native_input_1083_signal_authority_ver2_022a16.json'
ROUTES = [{'no': '1', 'path': ['21', '10112', '174', '10281', '173', '10286', '1220009502']},
          {'no': '2', 'path': ['21', '10112', '174', '10280', '173', '10285', '1220000803']}]


def decisions(*extra):
    """A synthetic decision section: 1081 on the receiver 174, 1160 on the source 21, plus extra elements."""
    text = ('<vehicleRoutingDecisionsStatic>'
            '<vehicleRoutingDecisionStatic no="1081" link="174" pos="11.92270445631143"><vehRoutSta>'
            '<vehicleRouteStatic no="1" destLink="1220009502" relFlow="2 0:1"><linkSeq><intObjectRef key="10281"/>'
            '</linkSeq></vehicleRouteStatic></vehRoutSta></vehicleRoutingDecisionStatic>'
            '<vehicleRoutingDecisionStatic no="1160" link="21" pos="20.0"><vehRoutSta>'
            '<vehicleRouteStatic no="1" destLink="1220009502" relFlow="2 0:38"><linkSeq><intObjectRef key="10112"/>'
            '<intObjectRef key="174"/><intObjectRef key="10281"/><intObjectRef key="173"/><intObjectRef key="10286"/>'
            '</linkSeq></vehicleRouteStatic>'
            '<vehicleRouteStatic no="2" destLink="1220000803" relFlow="2 0:808"><linkSeq><intObjectRef key="10112"/>'
            '<intObjectRef key="174"/><intObjectRef key="10280"/><intObjectRef key="173"/><intObjectRef key="10285"/>'
            '</linkSeq></vehicleRouteStatic></vehRoutSta></vehicleRoutingDecisionStatic>'
            + ''.join(extra) + '</vehicleRoutingDecisionsStatic>')
    return list(ET.fromstring(text))


def row(reviewed=None):
    out = {'physical_path': ['21', '10112', '174']}
    if reviewed is not None:
        out['reviewed_source_decisions'] = reviewed
    return out


REVIEWED = [{'no': '1160', 'link': '21', 'pos': '20.0', 'routes': ROUTES, 'review': 'test'}]


class SourceDecisionGuardTests(unittest.TestCase):

    def test_without_the_key_the_old_rule_holds(self):
        # no decision on the source: admitted (v3b); a decision there: the old refusal, same message
        self.assertEqual(check_source_routing_decisions(decisions()[:1], row()), [])
        with self.assertRaisesRegex(ValueError, '^Native signal source acquired an unreviewed routing decision$'):
            check_source_routing_decisions(decisions(), row())

    def test_the_reviewed_decision_is_admitted(self):
        self.assertEqual(check_source_routing_decisions(decisions(), row(REVIEWED)), ['1160'])
        self.assertEqual(source_decision_record(decisions()[1]),
                         {'no': '1160', 'link': '21', 'pos': '20.0', 'routes': ROUTES})

    def test_any_other_source_decision_still_refuses(self):
        extra = ('<vehicleRoutingDecisionStatic no="1169" link="21" pos="30.0"><vehRoutSta>'
                 '<vehicleRouteStatic no="1" destLink="174"><linkSeq><intObjectRef key="10112"/></linkSeq>'
                 '</vehicleRouteStatic></vehRoutSta></vehicleRoutingDecisionStatic>')
        with self.assertRaisesRegex(ValueError, 'acquired an unreviewed routing decision'):
            check_source_routing_decisions(decisions(extra), row(REVIEWED))

    def test_a_changed_or_missing_reviewed_decision_refuses(self):
        moved = decisions()
        moved[1].set('pos', '25.0')
        with self.assertRaisesRegex(ValueError, 'differs from the network: 1160'):
            check_source_routing_decisions(moved, row(REVIEWED))
        rerouted = decisions()
        rerouted[1].find('./vehRoutSta/vehicleRouteStatic').set('destLink', '1220000803')
        with self.assertRaisesRegex(ValueError, 'differs from the network: 1160'):
            check_source_routing_decisions(rerouted, row(REVIEWED))
        with self.assertRaisesRegex(ValueError, 'missing from the network: 1160'):
            check_source_routing_decisions(decisions()[:1], row(REVIEWED))

    def test_a_route_through_another_turn_refuses(self):
        other = copy.deepcopy(REVIEWED)
        other[0]['routes'][0]['path'][1] = '10113'
        tree = decisions()
        tree[1].find('./vehRoutSta/vehicleRouteStatic/linkSeq/intObjectRef').set('key', '10113')
        with self.assertRaisesRegex(ValueError, 'leaves through another turn: 1160'):
            check_source_routing_decisions(tree, row(other))

    def test_malformed_records_refuse(self):
        for bad in ([{'no': 1160, 'link': '21', 'routes': ROUTES}], [{'no': '1160', 'link': '22', 'routes': ROUTES}],
                    [{'no': '1160', 'link': '21', 'routes': []}], REVIEWED + REVIEWED):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'malformed'):
                check_source_routing_decisions(decisions(), row(bad))
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            check_source_routing_decisions(decisions(), row({'1160': REVIEWED[0]}))

    def test_the_pinned_declaration_admits_exactly_1160_on_the_pinned_network(self):
        document = json.loads(DECLARATION.read_text(encoding='utf-8'))
        declared = document['inputs']['1083']
        self.assertEqual([r['no'] for r in declared['reviewed_source_decisions']], ['1160'])       # decision D2
        network = ET.parse(fx.ROOT / document['network']['path']).getroot()
        self.assertEqual(fx.sha256(fx.ROOT / document['network']['path']), document['network']['sha256'])
        found = network.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic')
        self.assertEqual(check_source_routing_decisions(found, declared), ['1160'])
        # the same network without the key refuses (the guard is live on v3c1)
        stripped = {k: v for k, v in declared.items() if k != 'reviewed_source_decisions'}
        with self.assertRaisesRegex(ValueError, 'acquired an unreviewed routing decision'):
            check_source_routing_decisions(found, stripped)
        amendments = document['scenario_derivation']['declaration_amendments']
        self.assertEqual([a['at'] for a in amendments],
                         ['/inputs/1083/native_route_prior', '/inputs/1083/reviewed_source_decisions'])


if __name__ == '__main__':
    unittest.main()
