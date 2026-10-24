"""Small XML-only regression; no controller imports, COM, FZP or network writes."""
from fractions import Fraction
import unittest
import xml.etree.ElementTree as ET

from diagnostics import prepare_fixed_beta300v3_network_arms as arm


class NetworkArmsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = arm.NETWORK.read_bytes()
        cls.expanded, cls.audit = arm.expand_routes(cls.raw)

    def test_source_pin_and_one_byte_distance_edit(self):
        self.assertEqual(arm.sha(self.raw), arm.NETWORK_SHA)
        out, audit = arm.distance_arm(self.raw)
        self.assertEqual(len(out), len(self.raw))
        self.assertEqual(sum(a != b for a, b in zip(out, self.raw)), 1)
        self.assertTrue(audit['xml_allowed_diff_pass'])
        self.assertEqual(len(audit['byte_preservation']['edits']), 1)

    def test_route_ids_and_exact_probability_products(self):
        mapping = self.audit['route_mapping']
        self.assertEqual(len(mapping), 9)
        for no, total in [('1123',Fraction(10)),('1124',Fraction(6)),('1125',Fraction(6))]:
            rows = [r for r in mapping if r['parent_decision'] == no]
            self.assertEqual([r['new_route'] for r in rows], ['4','5','6'])
            self.assertEqual(sum(Fraction(r['new_relative_weight']) for r in rows), total)
            self.assertEqual([r['conditional_branch_probability'] for r in rows], ['3/5','1/5','1/5'])
            self.assertTrue(all(r['upstream_probability_before_product'] == r['upstream_probability_after'] for r in rows))
        self.assertEqual(self.audit['retained_sibling_routes_raw_exact'], 6)
        self.assertNotIn(b'no="1135"', self.expanded[self.expanded.index(b'<vehicleRoutingDecisionsStatic>'):])

    def test_allowed_edit_records_reverse_to_original_bytes(self):
        restored = self.expanded
        for change in reversed(self.audit['byte_preservation']['edits']):
            start, end = change['output_range']
            self.assertEqual(restored[start:end].decode('utf-8'), change['after_utf8'])
            restored = restored[:start] + change['before_utf8'].encode('utf-8') + restored[end:]
        self.assertEqual(restored, self.raw)

    def test_lane_change_is_explicit_not_falsely_certified(self):
        row = next(r for r in self.audit['route_mapping'] if r['parent_decision']=='1124' and r['new_route']=='6')
        stem = next(x for x in row['road_lane_transitions'] if x['road']=='68')
        self.assertEqual(stem['entry_lanes'], [4])
        self.assertEqual(stem['exit_lanes'], [1,2])
        self.assertTrue(stem['lane_change_required'])
        self.assertFalse(row['lane_change_feasibility_or_success_proven'])

    def test_child_id_collision_and_vehicle_class_change_rejected(self):
        match = arm.element_span(self.raw, 'vehicleRoutingDecisionStatic', '1123')
        for modified in (match.group().replace(b'no="1"',b'no="4"',1),
                         match.group().replace(b'allVehTypes="true"',b'allVehTypes="false"',1)):
            raw = self.raw[:match.start()] + modified + self.raw[match.end():]
            with self.assertRaises(ValueError): arm.expand_routes(raw)

    def test_interval_and_unreviewed_branch_weight_rejected(self):
        for changed in (
            self.raw.replace(b'<timeIntervalSet no="VEHICLEROUTESTATIC">',b'<timeIntervalSet no="OTHER">',1),
            self.raw[:arm.element_span(self.raw,'vehicleRoutingDecisionStatic','1135').start()] +
            arm.element_span(self.raw,'vehicleRoutingDecisionStatic','1135').group().replace(b'relFlow="2 0:3"',b'relFlow="2 0:4"') +
            self.raw[arm.element_span(self.raw,'vehicleRoutingDecisionStatic','1135').end():],
        ):
            with self.assertRaises(ValueError): arm.expand_routes(changed)

    def test_disconnected_route_destination_and_lane_range_rejected(self):
        for kind in ('path','destination','lane'):
            root = ET.fromstring(self.expanded)
            dec = root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1124']")
            route = dec.find("./vehRoutSta/vehicleRouteStatic[@no='6']")
            links = {x.get('no'):x for x in root.findall('./links/link')}
            if kind == 'path': route.find('./linkSeq/intObjectRef').set('key','10629')
            elif kind == 'destination': route.set('destPos','0')
            else: links['10681'].find('fromLinkEndPt').set('lane','68 5')
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                arm.validate_route(dec, route, links)

    def test_output_cannot_target_original_or_diagnostics_root(self):
        for target in (arm.NETWORK, arm.ROOT/'diagnostics', arm.ROOT.parent/'escaped'):
            with self.assertRaises(ValueError): arm.output_path(target)


if __name__ == '__main__':
    unittest.main()
