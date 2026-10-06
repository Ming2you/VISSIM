"""The user's area ends at controlled approaches, not their outward roads."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from diagnostics.build_control_area_membership import expand_controlled_intersection_area
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from evaluation.controllers.control_area_join import turn_membership

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def area():
    read=lambda p:json.loads((ROOT/p).read_bytes())
    old=read('diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/control_area_membership_213a5d.json')
    tree=ET.parse(ROOT/old['network']['path']).getroot()
    mapping=read('evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
    out=expand_controlled_intersection_area(old,tree,mapping,read('outputs/urban_player_territory_v2_20260907.json'))
    return old,out,tree,mapping

def test_approach66_is_inside_but_exit38_and67_are_not_added(area):
    old,new,_,_=area;physical=physical_membership_from_ledger(new)
    assert physical['66'] and not physical['38'] and not physical['67']
    assert set(old['inside_links'])<=set(new['inside_links'])

def test_all_controlled_heads_are_counted_without_counting_every_road(area):
    _,new,tree,mapping=area;physical=physical_membership_from_ledger(new)
    controlled={str(x['sc_no']) for x in mapping['signals']}
    heads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('sg').split()[0] in controlled]
    assert len(controlled)==17 and heads
    assert all(physical[h.get('lane').split()[0]] for h in heads)
    assert set(physical)=={x.get('no') for x in tree.findall('./links/link')}
    assert set(new['inside_links']).isdisjoint(new['outside_links']) and new['outside_links']

def test_new_connectors_join_included_roads_and_internal66_departure_is_not_exit(area):
    old,new,tree,_=area;physical=physical_membership_from_ledger(new)
    added=set(new['inside_links'])-set(old['inside_links'])
    for node in tree.findall('./links/link'):
        if node.get('no') not in added or node.find('fromLinkEndPt') is None:continue
        assert physical[node.find('fromLinkEndPt').get('lane').split()[0]]
        assert physical[node.find('toLinkEndPt').get('lane').split()[0]]
    turn=turn_membership({'from_link':'66','connector':'10631','to_link':'47'},physical)
    assert turn['source_inside'] and turn['target_inside']
    assert turn['outward_crossings_per_vehicle']==turn['inward_crossings_per_vehicle']==0

def test_area_builder_does_not_modify_old_definition_or_pn_classes(area):
    old,new,_,_=area
    assert '66' in old['outside_links'] and 'controlled_intersection_expansion' not in old
    for key in ('pn_internal_links','pn_perimeter_links','canonical_turn_connector_changes'):
        assert old[key]==new[key]
