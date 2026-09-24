r"""WP-E re-pin (plan section 5): pure rules on synthetic inputs, then the built pack on disk.

    PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \
        diagnostics/sdmpc_n31_20260924/tests/test_repin_scenario_v2.py

The second half needs the outputs of `repin_scenario_v2.py build` (they are part of the tree) and reads the
v2 network copy; it never writes into the tree and never starts VISSIM.
"""
from __future__ import annotations

import codecs
import importlib.util
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
N31D = HERE.parent
ROOT = N31D.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rp = _load('repin_scenario_v2', N31D / 'repin_scenario_v2.py')
BUILT = (ROOT / rp.SCENARIO_REL / rp.RECEIPT_NAME).is_file()
needs_build = pytest.mark.skipif(not BUILT, reason='repin outputs not built')


# --------------------------------------------------------------------------- synthetic XML
def network(inputs=('336', '480'), relflow=('2 0:2', '2 0:8'), dsd='120', lanes=2, seed='13', simres='1',
            extra_link=False, dc_points=(), sc_extra=False, collect='true'):
    link_extra = '<link no="3"><lanes><lane/></lanes></link>' if extra_link else ''
    points = ''.join(f'<dataCollectionPoint no="{p}" lane="1 1" pos="1"/>' for p in dc_points)
    sc_block = '<scDetRecConf><signalOutputConfigurationElement configName="SIM_SEK"/></scDetRecConf>' if sc_extra else ''
    lane_xml = '<lane/>' * lanes
    return ET.fromstring(f'''<network>
<simulation randSeed="{seed}" simRes="{simres}" simPeriod="9001"/>
<links><link no="1"><lanes>{lane_xml}</lanes></link><link no="2"><lanes><lane/></lanes></link>{link_extra}
<link no="10"><fromLinkEndPt lane="1 1" pos="5"/><toLinkEndPt lane="2 1" pos="0"/><lanes><lane/></lanes></link></links>
<vehicleInputs><vehicleInput no="1106" link="1" anmFlag="false" name=""><timeIntVehVols>
<timeIntervalVehVolume cont="false" timeInt="1 0" vehComp="1" volType="STOCHASTIC" volume="{inputs[0]}"/>
<timeIntervalVehVolume cont="false" timeInt="1 900000" vehComp="1" volType="STOCHASTIC" volume="{inputs[1]}"/>
</timeIntVehVols></vehicleInput></vehicleInputs>
<vehicleRoutingDecisionsStatic>
<vehicleRoutingDecisionStatic no="1130" link="1" pos="3"><vehRoutSta>
<vehicleRouteStatic no="1" destLink="2" destPos="4.5" relFlow="{relflow[0]}"><linkSeq><intObjectRef key="10"/></linkSeq></vehicleRouteStatic>
<vehicleRouteStatic no="2" destLink="2" destPos="9.5" relFlow="{relflow[1]}"><linkSeq><intObjectRef key="10"/></linkSeq></vehicleRouteStatic>
</vehRoutSta></vehicleRoutingDecisionStatic>
<vehicleRoutingDecisionStatic no="22" link="2" pos="1"><vehRoutSta>
<vehicleRouteStatic no="1" destLink="1" destPos="1.0" relFlow="2 0:35"/></vehRoutSta></vehicleRoutingDecisionStatic>
</vehicleRoutingDecisionsStatic>
<desSpeedDecisions><desSpeedDecision no="36" lane="1 1"><vehClassDesSpeedDistr>
<vehClassDesSpeedDistribution desSpeedDistr="{dsd}" vehClass="10"/></vehClassDesSpeedDistr></desSpeedDecision></desSpeedDecisions>
<signalHeads><signalHead no="30603" lane="2 1" pos="4" sg="5 1"/></signalHeads>
<dataCollectionPoints><dataCollectionPoint no="1" lane="1 1" pos="0"/>{points}</dataCollectionPoints>
<signalControllers><signalController no="5" progNo="1" type="FIXEDTIME" offset="0" supplyFile2="#data#a.sig">{sc_block}<sgs/></signalController></signalControllers>
<evaluation><dataColl collectData="{collect}"/></evaluation>
</network>''')


def test_characterize_accepts_exactly_the_new1_kinds():
    old = network()
    new = network(inputs=('302.4', '432.0'), relflow=('2 0:1', '2 0:9'), dsd='110', seed='31', simres='10',
                  dc_points=('910059',), sc_extra=True, collect='false')
    report = rp.characterize_changes(old, new)
    assert report['vehicleInputs']['changed'] == ['1106']
    assert report['vehicleRoutingDecisionsStatic']['relflow'] == {
        '1130': {'1': {'old': '2 0:2', 'new': '2 0:1'}, '2': {'old': '2 0:8', 'new': '2 0:9'}}}
    assert report['desSpeedDecisions']['distribution_changes'] == [{'old': '120', 'new': '110'}]
    assert report['dataCollectionPoints']['added'] == ['910059']
    assert report['signalControllers']['changed'] == ['5']
    assert report['simulation']['attributes'] == {'randSeed': {'old': '13', 'new': '31'}, 'simRes': {'old': '1', 'new': '10'}}
    assert report['evaluation']['settings'][0]['new'] == {'collectData': 'false'}
    assert rp.characterize_changes(old, network()) == {}


@pytest.mark.parametrize('kwargs, message', [
    (dict(lanes=3), 'unreviewed section: links'),
    (dict(extra_link=True), 'unreviewed section: links'),
])
def test_characterize_refuses_topology_changes(kwargs, message):
    with pytest.raises(rp.RepinError, match=message):
        rp.characterize_changes(network(), network(**kwargs))


def test_characterize_refuses_changes_beyond_the_rule():
    old, new = network(), network()
    new.find('.//vehicleInput').set('link', '2')                      # not a volume
    with pytest.raises(rp.RepinError, match='differ beyond'):
        rp.characterize_changes(old, new)
    new = network()
    new.find('simulation').set('simPeriod', '3601')                    # only seed and SimRes may move
    with pytest.raises(rp.RepinError, match='attributes changed'):
        rp.characterize_changes(old, new)
    new = network()
    new.find('vehicleRoutingDecisionsStatic').remove(new.find('.//vehicleRoutingDecisionStatic[@no="22"]'))
    with pytest.raises(rp.RepinError, match='removed'):
        rp.characterize_changes(old, new)


def test_section_diff_compares_the_root_and_refuses_repeated_sections():
    old, new = network(), network()
    new.set('vissimVersion', '2024.00 - 1')
    assert rp.section_diff(old, new) == {rp.ROOT_SECTION: {'attributes': {'vissimVersion': {'old': None, 'new': '2024.00 - 1'}}}}
    with pytest.raises(rp.RepinError, match=r'unreviewed section: \(root\)'):
        rp.characterize_changes(old, new)
    new = network()
    new.append(ET.fromstring('<links><link no="1"><lanes><lane/><lane/></lanes></link></links>'))   # a second <links>
    with pytest.raises(rp.RepinError, match=r"new network repeats top-level sections \['links'\]"):
        rp.characterize_changes(old, new)
    with pytest.raises(rp.RepinError, match='repeats top-level sections'):
        rp.native_diff(old, new)


def test_native_diff_keeps_the_prior_transfer_record_format():
    diff = rp.native_diff(network(), network(inputs=('1', '2')))
    assert set(diff) == {'links', 'signalHeads', 'vehicleInputs', 'vehicleRoutingDecisionsStatic',
                         'signalControllers', 'desSpeedDecisions', 'membership_basis'}
    assert diff['links'] == {'added': [], 'removed': [], 'changed': []}
    with pytest.raises(rp.RepinError, match='edge or lane identity'):
        rp.native_diff(network(), network(lanes=3))
    assert diff['vehicleInputs']['changed'] == ['1106']


# --------------------------------------------------------------------------- naming, rewriting
def test_target_name_is_declaration_stem_plus_pack_path_sha6():
    doc = {'scenario_derivation': {'source_declaration': {'path': 'diagnostics/control_area_membership.json'}}}
    name = rp.target_name('control_area_membership_6c3aee.json', doc)
    assert name == 'control_area_membership_' + rp.sha6(rp.PACK_REL + '/control_area_membership_6c3aee.json') + '.json'
    with pytest.raises(rp.RepinError):
        rp.target_name('membership_6c3aee.json', doc)


def rewriter():
    pack_rel = rp.PACK_REL + '/a_111111.json'
    pack_bytes = {pack_rel: b'{}'}
    new_pin = {'path': rp.SCENARIO_REL + '/a_222222.json', 'sha256': '0' * 64}
    return rp.Rewriter({pack_rel: new_pin['path']}, {pack_rel: new_pin}, pack_bytes), pack_rel, new_pin


def test_rewriter_repoints_network_pins_pack_pins_and_pack_paths():
    rewrite, pack_rel, new_pin = rewriter()
    doc = {'network': dict(rp.OLD_PIN, note='kept'), 'membership': {'path': pack_rel, 'sha256': rp.sha256_bytes(b'{}')},
           'membership_path': pack_rel, 'list': [pack_rel.replace('/', '\\')], 'other': 'outputs/x.json'}
    out = rewrite(doc)
    assert out['network'] == dict(rp.V2_PIN, note='kept')
    assert out['membership'] == new_pin and out['membership_path'] == new_pin['path'] and out['list'] == [new_pin['path']]
    assert out['other'] == 'outputs/x.json'
    assert [e['kind'] for e in rewrite.edits] == ['network_pin', 'pack_pin', 'pack_path', 'pack_path']


def test_rewriter_refuses_stale_pins_and_bare_fcb_references():
    rewrite, pack_rel, _ = rewriter()
    with pytest.raises(rp.RepinError, match='stale pin'):
        rewrite({'m': {'path': pack_rel, 'sha256': '1' * 64}})
    with pytest.raises(rp.RepinError, match='bare fcb'):
        rewrite({'s': rp.OLD_PIN['sha256']})
    with pytest.raises(rp.RepinError, match='another sha'):
        rewrite({'n': {'path': rp.OLD_PIN['path'], 'sha256': '2' * 64}})


def test_pack_closure_follows_declarations_and_adds_the_sg_plan():
    docs = {'a.json': {'x': rp.PACK_REL + '/b.json'}, 'b.json': {'p': {'path': rp.PACK_REL + '/profile.csv', 'sha256': '0' * 64}}}
    tuning = {'m': rp.PACK_REL + '/a.json', 'v': rp.PACK_REL + '/' + rp.RUNNER_CONFIG[0]}
    assert rp.pack_closure(tuning, docs) == {'a.json', 'b.json', 'profile.csv', rp.RUNNER_CONFIG[0], rp.SG_PLAN[0]}


# --------------------------------------------------------------------------- VBS
@pytest.mark.parametrize('bom, eol', [(True, '\n'), (False, '\r\n')])
def test_set_vsl_speeds_changes_one_line_only(bom, eol):
    text = eol.join(["' comment 한글", 'RW_A = "1"', 'RW_ALLOWED_VSL_SPEEDS = "50,60,70,80,90,100,115,120"', 'RW_B = "2"', ''])
    data = (codecs.BOM_UTF8 if bom else b'') + text.encode('utf-8')
    out, old = rp.set_vsl_speeds(data, rp.VSL_SPEEDS)
    assert old == [50, 60, 70, 80, 90, 100, 115, 120]
    assert out.startswith(codecs.BOM_UTF8) == bom
    a, b = data.split(b'\n'), out.split(b'\n')
    assert len(a) == len(b) and [i for i, (x, y) in enumerate(zip(a, b)) if x != y] == [2]
    assert b[2] == b'RW_ALLOWED_VSL_SPEEDS = "50,60,70,80,90,100,110"' + (b'\r' if eol == '\r\n' else b'')


def test_vsl_speeds_are_the_user_decision():
    assert rp.VSL_SPEEDS == (50, 60, 70, 80, 90, 100, 110)   # 2026-09-24: 10 km/h steps, c_max 110
    # One action set: the runner list, the tuning vsl_set and the plant reference vsl_set.
    config = _load('make_config_n31', N31D / 'make_config_n31.py')
    reference = _load('make_reference_config', N31D / 'make_reference_config.py')
    assert [float(v) for v in rp.VSL_SPEEDS] == config.VSL_SET == reference.VSL_SET


@pytest.mark.parametrize('text', ['RW_X = "1"\n', 'RW_ALLOWED_VSL_SPEEDS = "50"\nRW_ALLOWED_VSL_SPEEDS = "60"\n',
                                  'RW_ALLOWED_VSL_SPEEDS = "50,60,70,80,90,100,110"\n', 'RW_ALLOWED_VSL_SPEEDS = "fast"\n'])
def test_set_vsl_speeds_refuses(text):
    with pytest.raises(rp.RepinError):
        rp.set_vsl_speeds(text.encode(), rp.VSL_SPEEDS)


@pytest.mark.parametrize('speeds', [(), (80, 60, 110), (60, 60, 110)])
def test_set_vsl_speeds_refuses_a_bad_target(speeds):
    with pytest.raises(rp.RepinError, match='ascending and distinct'):
        rp.set_vsl_speeds(b'RW_ALLOWED_VSL_SPEEDS = "50,120"\n', speeds)


# --------------------------------------------------------------------------- evidence refresh and audits
class FakeSources:
    def __init__(self, training, old, new):
        self.training_tree, self.old_tree, self.new_tree = training, old, new


def test_relflow_audit_accepts_v2_copies_and_training_lineage_only():
    training = network(relflow=('2 0:5', '2 0:8'))
    old = new = network()
    sources = FakeSources(training, old, new)
    doc = {'schema': 'control-area-membership/v1', 'rows': [
        {'decision': '1130', 'route': '2', 'relflow_raw': '2 0:8'},       # equal to v2
        {'decision': '22', 'route': '1', 'relflow_raw': '2 0:35'}]}
    assert rp.relflow_audit('m', doc, sources, set()) == {'equal_v2': 2, 'lineage': []}
    lineage = {'schema': 'control-area-membership/v1', 'rows': [{'decision': '1130', 'route': '1', 'relflow_raw': '2 0:5'}]}
    result = rp.relflow_audit('m', lineage, sources, set())
    assert result['lineage'][0]['copy'] == '2 0:5' and result['lineage'][0]['v2'] == '2 0:2'
    with pytest.raises(rp.RepinError, match='neither v2'):
        rp.relflow_audit('m', lineage, sources, {'1130'})                  # a decision the v2 step changed
    stale = {'schema': 'control-area-membership/v1', 'rows': [{'decision': '1130', 'route': '1', 'relflow_raw': '2 0:7'}]}
    with pytest.raises(rp.RepinError, match='neither v2'):
        rp.relflow_audit('m', stale, sources, set())
    with pytest.raises(rp.RepinError, match='no audit rule'):
        rp.relflow_audit('m', {'schema': 'x', 'r': {'relFlow': '2 0:1'}}, sources, set())
    prehead = {'schema': 'native-input-prehead/v1', 'decision': '22', 'branches': {'1': {'rel_flow': '2 0:35'}}}
    assert rp.relflow_audit('p', prehead, sources, set())['equal_v2'] == 1


def test_relflow_audit_never_counts_two_missing_values_as_equal():
    bare = network()
    del bare.find(".//vehicleRoutingDecisionStatic[@no='22']/vehRoutSta/vehicleRouteStatic[@no='1']").attrib['relFlow']
    sources = FakeSources(bare, bare, bare)
    null_copy = {'schema': 'control-area-membership/v1', 'rows': [{'decision': '22', 'route': '1', 'relflow_raw': None}]}
    with pytest.raises(rp.RepinError, match='not a string'):
        rp.relflow_audit('m', null_copy, sources, set())
    text_copy = {'schema': 'control-area-membership/v1', 'rows': [{'decision': '22', 'route': '1', 'relflow_raw': '2 0:35'}]}
    with pytest.raises(rp.RepinError, match='carries no relFlow'):
        rp.relflow_audit('m', text_copy, sources, set())


def test_sig_copies_must_equal_the_training_folder(tmp_path):
    (tmp_path / '개 a.sig').write_bytes(b'a')
    (tmp_path / 'b.sig').write_bytes(b'b')
    assert rp.sig_equal_to_folder({'개 a.sig': b'a', 'b.sig': b'b'}, tmp_path) == 2
    with pytest.raises(rp.RepinError, match='b.sig is not a byte copy'):
        rp.sig_equal_to_folder({'b.sig': b'B'}, tmp_path)
    with pytest.raises(rp.RepinError, match='c.sig is not a byte copy'):
        rp.sig_equal_to_folder({'c.sig': b'c'}, tmp_path)


def test_stale_evidence_audit_refuses_unrefreshed_copies():
    changes = {'vehicleRoutingDecisionsStatic': {'changed': ['1130']}}
    rp.stale_evidence_audit('k', {'schema': 'known-wout-routes/v1', 'native_routes': {'1130:3': {}}}, changes)
    rp.stale_evidence_audit('s', {'schema': 'sc2001-corridor/v1', 'native_input_evidence': {'inputs': [{'intervals': [{'volume': '1'}]}]}}, changes)
    with pytest.raises(rp.RepinError, match='known routes'):
        rp.stale_evidence_audit('x', {'schema': 'x', 'routes': {'1130:3': {}}}, changes)
    with pytest.raises(rp.RepinError, match='demand volume'):
        rp.stale_evidence_audit('x', {'schema': 'x', 'i': {'volume': '1'}}, changes)
    with pytest.raises(rp.RepinError, match='desired-speed'):
        rp.stale_evidence_audit('x', {'schema': 'x', 'd': {'desSpeedDistr': '120'}}, changes)


def test_refresh_sc2001_refills_input_volumes_and_rereads_routes():
    old, new = network(), network(inputs=('302.4', '432.0'))
    doc = {'native_input_evidence': {'inputs': [rp.vehicle_input_evidence(old, '1106')]},
           'native_upstream_routes': {'22': rp.decision_evidence(old, '22')}}
    updates = rp.refresh_sc2001(doc, new)
    assert updates == {'/native_input_evidence/inputs/0': {'no': '1106', 'old_volumes': ['336', '480'],
                                                           'new_volumes': ['302.4', '432.0']}}
    assert doc['native_input_evidence']['inputs'][0] == rp.vehicle_input_evidence(new, '1106')
    doc['native_upstream_routes'] = {'1130': rp.decision_evidence(old, '1130')}
    with pytest.raises(rp.RepinError, match='upstream routing decision 1130'):
        rp.refresh_sc2001(doc, network(relflow=('2 0:1', '2 0:9')))


def test_refresh_known_wout_records_destination_updates_and_refuses_path_changes():
    tree = network()
    doc = {'native_routes': {'1130:1': {'path': ['1', '10', '2'], 'dest_pos': 4.0}}}
    assert rp.refresh_known_wout(doc, tree) == {'1130:1': {'old': 4.0, 'current': 4.5}}
    assert doc['native_routes']['1130:1']['dest_pos'] == 4.5
    with pytest.raises(rp.RepinError, match='physical path'):
        rp.refresh_known_wout({'native_routes': {'1130:1': {'path': ['1', '2'], 'dest_pos': 4.5}}}, tree)


# --------------------------------------------------------------------------- the built pack (real data)
def built_json(name):
    return json.loads((ROOT / rp.SCENARIO_REL / name).read_text(encoding='utf-8'))


@needs_build
def test_verify_regenerates_every_output_byte_for_byte(capsys):
    """From the pinned N31D copy only (--no-net): the copy-equals-NET check reads the stage-1 run folder."""
    assert rp.main(['verify', '--no-net']) == 0
    line = capsys.readouterr().out.strip().splitlines()
    assert len(line) == 1 and line[0].startswith('REPIN_VERIFY_OK files=70 ') and line[0].endswith('net=skipped(--no-net)')


@needs_build
def test_folders_hold_exactly_the_outputs():
    receipt = built_json(rp.RECEIPT_NAME)
    scenario = sorted(p.name for p in (ROOT / rp.SCENARIO_REL).iterdir())
    targets = sorted(Path(row['target']['path']).name for row in receipt['files'])
    assert scenario == sorted(targets + [rp.CONFIG_BASE_NAME, rp.RECEIPT_NAME])
    assert len([n for n in scenario if n.endswith('.json')]) == 20 + 3
    network_dir = sorted(p.name for p in (ROOT / rp.NETWORK_DIR_REL).iterdir())
    assert len([n for n in network_dir if n.endswith('.sig')]) == 42
    assert set(network_dir) - {n for n in network_dir if n.endswith('.sig')} == {rp.NET_INPX, 'sig_manifest.json'}


@needs_build
def test_every_sig_copy_equals_the_training_network_sibling():
    """NEW-1 '.sig unchanged', checked by the build itself and recorded in the receipt."""
    receipt = built_json(rp.RECEIPT_NAME)
    check = receipt['network']['sig_byte_equal_to']
    assert check['folder'] == 'network/real_world_gaepo_modi' and check['files'] == 42
    folder = ROOT / rp.NETWORK_DIR_REL
    sig = {p.name: p.read_bytes() for p in folder.glob('*.sig')}
    assert rp.sig_equal_to_folder(sig, ROOT / check['folder']) == 42


@needs_build
def test_every_declaration_targets_v2_and_only_the_seven_carry_prior_mismatch():
    receipt = built_json(rp.RECEIPT_NAME)
    rows = [r for r in receipt['files'] if r.get('schema') not in (None, rp.TRANSFER_SCHEMA)]
    assert len(rows) == 20
    carriers = set()
    for row in rows:
        doc = built_json(Path(row['target']['path']).name)
        derivation = doc['scenario_derivation']
        assert derivation['runtime_network'] == rp.V2_PIN
        assert derivation['source_declaration'] == row['source']
        if 'network' in doc:
            assert doc['network'] == rp.V2_PIN
        if 'prior_mismatch' in derivation:
            carriers.add(Path(row['source']['path']).name)
            assert derivation['prior_mismatch']['status'] == 'transferred_without_refit'
            assert derivation['prior_mismatch']['receipt']['path'].endswith('/historical_prior_transfer.json')
    assert carriers == set(rp.PRIOR_DECLARATIONS)


@needs_build
def test_transfer_receipt_keeps_training_network_and_prior_set():
    transfer = built_json(rp.TRANSFER_NAME)
    old = json.loads((ROOT / rp.PACK_REL / rp.TRANSFER_NAME).read_text(encoding='utf-8-sig'))
    assert transfer['schema'] == rp.TRANSFER_SCHEMA and transfer['predictive_accuracy_validated'] is False
    assert transfer['source_network'] == old['source_network'] and transfer['target_network'] == rp.V2_PIN
    key = lambda pins: {json.dumps(p, sort_keys=True) for p in pins}  # noqa: E731
    assert key(transfer['unchanged_prior_files']) == key(old['unchanged_prior_files'])
    assert transfer['repin_step']['from_network'] == rp.OLD_PIN
    assert set(transfer['repin_step']['native_changes']['vehicleRoutingDecisionsStatic']['changed']) == {'1130', '1131'}


@needs_build
def test_runtime_prior_transfer_and_native_service_checks_accept_the_pack():
    """The real runtime functions (scenario_prior_transfer, route_choice_corridor) on the built files."""
    from evaluation.controllers.scenario_prior_transfer import training_network
    from evaluation.controllers import route_choice_corridor as rc
    transfer = built_json(rp.TRANSFER_NAME)
    receipt = built_json(rp.RECEIPT_NAME)
    names = {Path(r['source']['path']).name: Path(r['target']['path']).name for r in receipt['files']}
    checked = 0
    for source in rp.PRIOR_DECLARATIONS:
        doc = built_json(names[source])
        for pointer, pin in [(p['at'], p) for p in doc['scenario_derivation']['prior_mismatch']['priors']]:
            node, holder = doc, doc      # the runtime passes the nearest dict that carries the transfer receipt
            for part in pointer.strip('/').split('/')[:-1]:
                node = node[part]
                if 'historical_prior_transfer' in node:
                    holder = node
            assert 'historical_prior_transfer' in holder
            assert training_network(holder, {k: pin[k] for k in ('path', 'sha256')}) == transfer['source_network']
            checked += 1
        if doc.get('native_fixed_service', {}).get('calibrated_discharge'):
            assert rc._calibrated_native_service(doc, doc['native_fixed_service']) > 0
            checked += 1
    assert checked == 7   # 5 training-network proofs + the 1099/1100 service calibration identities


@needs_build
def test_sig_supply_files_sit_beside_the_pinned_network():
    """route_choice_corridor.py:260 reads <network folder>/<supplyFile2>; each .sig pin equals the v2 copy."""
    folder = ROOT / rp.NETWORK_DIR_REL
    tree = ET.parse(folder / rp.NET_INPX).getroot()
    for sc in tree.findall('./signalControllers/signalController'):
        supply = sc.get('supplyFile2', '')
        if supply:
            assert (folder / supply.removeprefix('#data#')).is_file()
    for name in ('route_choice_corridor_1099_sc15_calibrated_23ec67.json', 'route_choice_corridor_1100_sc15_calibrated_f2a618.json'):
        receipt = built_json(rp.RECEIPT_NAME)
        target = next(Path(r['target']['path']).name for r in receipt['files'] if r['source']['path'].endswith(name))
        pin = built_json(target)['native_fixed_service']['sig_file']
        sig = folder / Path(pin['path']).name
        assert rp.sha256_bytes(sig.read_bytes()) == pin['sha256']


@needs_build
def test_sig_manifest_is_readable_by_the_launch_plan():
    lp = _load('launch_plan', N31D / 'tools' / 'launch_plan.py')
    table = lp.sig_table(json.loads((ROOT / rp.SIG_MANIFEST_REL).read_text(encoding='utf-8')))
    folder = ROOT / rp.NETWORK_DIR_REL
    assert len(table) == 42
    assert all(rp.sha256_bytes((folder / name).read_bytes()) == sha for name, sha in table.items())


@needs_build
def test_config_base_repoints_every_pack_path_and_passes_the_path_preflight():
    config_path = ROOT / rp.SCENARIO_REL / rp.CONFIG_BASE_NAME
    text = config_path.read_text(encoding='utf-8')
    assert rp.PACK_REL not in text and rp.OLD_PIN['sha256'] not in text and rp.OLD_PIN['path'] not in text
    config = json.loads(text)
    assert config['execution']['signal_vbs_config'] == rp.SCENARIO_REL + '/lane_native_b110.vbs'
    assert config['observation']['physical_branch_projection']['source']['network'] == rp.V2_PIN
    evidence = config['urban']['known_wout_route_evidence']
    assert rp.sha256_bytes((ROOT / evidence['path']).read_bytes()) == evidence['sha256']
    assert config['_repin']['source_config']['path'] == rp.OBS1_REL
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts' / 'preflight_tuning_paths.py'), str(config_path), '--quiet'],
                            capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


@needs_build
def test_runner_config_allows_exactly_50_to_110_each_with_a_v2_distribution():
    receipt = built_json(rp.RECEIPT_NAME)
    check = receipt['runner_config_check']
    assert check['allowed_vsl_speeds'] == [50, 60, 70, 80, 90, 100, 110] and check['seg_bounds_cells'] == {'E': 21, 'W': 21}
    assert check['allowed_speeds_without_distribution'] == []
    constants = rp.vbs_constants((ROOT / rp.SCENARIO_REL / rp.RUNNER_CONFIG[1]).read_bytes())
    assert constants['RW_ALLOWED_VSL_SPEEDS'] == '50,60,70,80,90,100,110'
    tree = ET.parse(ROOT / rp.NETWORK_DIR_REL / rp.NET_INPX).getroot()
    names = {x.get('no'): x.get('name') for x in tree.findall('./desSpeedDistributions/desSpeedDistribution')}
    # The distribution NUMBER is the speed: the runner writes it as the DesSpeedDistr id.
    assert all(names.get(str(v)) == f'{v} km/h' for v in rp.VSL_SPEEDS)


def test_runner_writes_the_speed_as_the_distribution_number():
    """run_real_world_stackelberg_controller.vbs: DesSpeedDistr(class) := CLng(speed), read back equal."""
    text = (ROOT / 'scripts' / 'run_real_world_stackelberg_controller.vbs').read_text(encoding='utf-8', errors='replace')
    assert 'attributeName = "DesSpeedDistr(" & CStr(vehClassNo) & ")"' in text
    assert 'dsd.AttValue(attributeName) = CLng(speedKph)' in text
    assert 'SetClassSpeedChecked = (CLng(CDbl(readback)) = CLng(CDbl(speedKph)))' in text
    # Every row's speed must be in the runner config's allowed list before any write.
    assert 'Not IsCsvFiniteNumber(parts(6), RW_ALLOWED_VSL_SPEEDS)' in text


def test_lineage_relflow_copies_have_no_runtime_reader():
    """relflow_audit keeps lineage copies (derivation-network values); nothing under evaluation/ reads them."""
    readers = []
    for path in (ROOT / 'evaluation').rglob('*.py'):
        text = path.read_text(encoding='utf-8', errors='replace')
        if re.search(r"relflow_raw|mixed_transfer_road_routes", text):
            readers.append(str(path))
    assert readers == []


DONOR_STATE = rp.DONOR_RUN / f'decisions_{rp.DONOR_RUN.name}' / 'state_000001.json'


@needs_build
@pytest.mark.skipif(not DONOR_STATE.is_file(), reason='donor fcb SDMPC run absent')
def test_configure_runtime_accepts_the_v2_pack_like_the_fcb_pack():
    """runtime_setup.configure_runtime (every pack validator) on the donor t=1 state: fcb control vs v2.

    Without a lane plant on both sides (the v1 plant pins fcb349d3; the v2 plant is WP-C's). The CLI
    `repin_scenario_v2.py configure-check` runs t=1, 150 and 900.
    """
    [(sec, keys, enabled)] = rp.configure_check(rp.DONOR_RUN, (1,))
    assert sec == 1 and keys > 300 and enabled > 30
