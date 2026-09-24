r"""Re-pin the SDMPC lane-plant scenario pack onto the FW80/U90 v2 network (plan section 5, WP-E).

Generalises diagnostics/metanet_compare_20260921/prepare_scenario.py from "original declarations ->
one network" to "an existing pack -> the next network":

    source pack  diagnostics/lane_plant_20260921/scenario/   (21 files pinned to fcb349d3, "PACK")
    source tuning diagnostics/sdmpc_pfo_caps_20260922/config_candidate_obs1.json      ("OBS1")
    network       D:\VISSIM_runs\20260923_stage1\s31_v2nc\prepared\network\           ("NET", read-only)

Outputs (all under diagnostics/sdmpc_n31_20260924/, byte-exact by .gitattributes):

    network/baseline_s31_v2nc.inpx          byte copy of the NET .inpx (f475ce42)
    network/<42 .sig>                       byte copies of the supply files the .inpx references
    network/sig_manifest.json               name, sha256, bytes and controllers of each .sig
    scenario/<decl stem>_<sha6>.json        20 declarations; sha6 = sha256(PACK path)[:6]
    scenario/historical_prior_transfer.json regenerated receipt (training network -> v2)
    scenario/profile.csv                    byte copy (__default__,1.0: the v2 demand is inside the .inpx)
    scenario/lane_native_b110.vbs           lane_native.vbs with RW_ALLOWED_VSL_SPEEDS set to 50,60,...,110 only
    scenario/lane_native_b110_sgplan.vbs    byte copy (the runner loads <config>_sgplan.vbs by name)
    scenario/config_n31_v2.base.json        OBS1 with every pack path and network pin re-pointed
    scenario/repin_receipt.json             what was copied, rewritten and checked

Rules (user decisions of 2026-09-24):
- The v2 network differs from fcb349d3 only in demand, 1130/1131 relFlow, DSD 120->110, RULE detectors and
  output settings (NEW-1). characterize_changes() proves that and refuses any other difference, so every
  declaration derived from the unchanged sections (links, heads, connectors, routes, signal programs) is
  transferred as is. The 42 .sig files are byte copies of the ones beside the training network the pack was
  derived on (Sources refuses otherwise).
- Embedded copies of changed XML are refreshed from the v2 XML (SC2001 native input volumes) or re-read and
  compared (known W_out destinations, relFlow copies). stale_evidence_audit() refuses any other copy.
- D-B: the 7 prior-calibrated declarations are carried over unchanged in their priors, with the transfer
  receipt and scenario_derivation.prior_mismatch. Refit after the first 9000 s run.
- Training artifacts keep their original paths and bytes (scenario_prior_transfer.training_network).
- RW_ALLOWED_VSL_SPEEDS on the v2 path is exactly 50,60,70,80,90,100,110 (user decision 2026-09-24: 10 km/h
  steps, c_max 110; it replaced the first 60,80,110): the SDMPC/plant action set, each speed with a
  desSpeedDistribution of the same number in the v2 network (the runner writes DesSpeedDistr = CLng(speed)
  and requires the read-back number to equal it). The pack's 115/120 have no v2 use.

    python -B diagnostics/sdmpc_n31_20260924/repin_scenario_v2.py build [--network-from copy]
    python -B diagnostics/sdmpc_n31_20260924/repin_scenario_v2.py verify [--no-net]
    python -B diagnostics/sdmpc_n31_20260924/repin_scenario_v2.py configure-check [--sec 1 --sec 150 ...]

build writes the outputs (identical bytes are left alone); --network-from copy rebuilds from the pinned
N31D network copy instead of NET (same bytes, verified), so a rebuild need not read the stage-1 run folder.
verify regenerates every output in memory and compares bytes, then checks every pin; it needs NET only for
the "copy equals NET" check and skips that check with a note when NET is absent or --no-net is given. configure-check runs runtime_setup.configure_runtime (every pack
validator) on saved states of the fcb run sdmpc_lp_9000c twice, as recorded (OBS1 + fcb pack, the control)
and re-pointed at the v2 network (base config + v2 pack), without a lane plant on either side, and requires
the same enabled model pieces; it writes only to a temporary folder. One stdout line on success:
REPIN_OK / REPIN_VERIFY_OK / REPIN_CONFIGURE_OK.
The runtime validators still decide at the first native decision (G1 t=1); this is not a native run.
"""
from __future__ import annotations

import argparse
import codecs
import copy
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation.controllers.obs150_contract import EXPECTED_SIMRES  # noqa: E402  (contract 1.1: the network SimRes)

N31D_REL = 'diagnostics/sdmpc_n31_20260924'
TOOL_REL = N31D_REL + '/repin_scenario_v2.py'
SCENARIO_REL = N31D_REL + '/scenario'
NETWORK_DIR_REL = N31D_REL + '/network'
PACK_REL = 'diagnostics/lane_plant_20260921/scenario'
OBS1_REL = 'diagnostics/sdmpc_pfo_caps_20260922/config_candidate_obs1.json'

NET_DIR = Path(r'D:\VISSIM_runs\20260923_stage1\s31_v2nc\prepared\network')
NET_INPX = 'baseline_s31_v2nc.inpx'
V2_SHA256 = 'f475ce42b0afaceccfd7974066a7b040600ddb93849bcf09174cd794bc0b255b'
V2_PIN = {'path': NETWORK_DIR_REL + '/' + NET_INPX, 'sha256': V2_SHA256}
OLD_PIN = {'path': 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/source_dsd/baseline.inpx',
           'sha256': 'fcb349d341e69a9f5c0847ecfa242dd19db13bfab738d6331fbcd72a6f009bf4'}
SIG_COUNT = 42
SIG_MANIFEST_REL = NETWORK_DIR_REL + '/sig_manifest.json'
SIG_MANIFEST_SCHEMA = 'sdmpc31-sig-manifest/v1'
RECEIPT_SCHEMA = 'sdmpc31-scenario-repin/v1'
TRANSFER_SCHEMA = 'experimental-network-prior-transfer/v1'

# The pack, exactly (plan section 5 table). An extra or missing file is a refusal, not a guess.
DECLARATIONS = (
    'control_area_membership_6c3aee.json',
    'dynamic_area_routes_ver2_13108c.json',
    'head_free_service_10565_v1_d6d4f7.json',
    'head_service_resource_contract_f40085.json',
    'known_wout_routes_ver2_proposal_c394e0.json',
    'native_input_1083_signal_authority_ver2_a931a8.json',
    'native_input_1093_prehead_ver2_067f5f.json',
    'native_input_1096_route_ver2_bac3da.json',
    'native_internal_inputs_f8b338.json',
    'physical_movement_routes_ver2_e5a98c.json',
    'physical_phase_authority_local_504e5f.json',
    'physical_projection_support_635_proposal_cc280d.json',
    'physical_projection_support_ver2_41fb9b.json',
    'route_choice_corridor_1099_sc15_calibrated_23ec67.json',
    'route_choice_corridor_1100_sc15_calibrated_f2a618.json',
    'route_choice_corridor_1128_ver2_75d663.json',
    'route_choice_corridor_sc1004_calibrated_6eb99c.json',
    'sc2001_corridor_nc13_f76cd6.json',
    'shared_approach_c0716a.json',
    'topology_routes_v2_0e44f6.json',
)
TRANSFER_NAME = 'historical_prior_transfer.json'
PROFILE_NAME = 'profile.csv'
RUNNER_CONFIG = ('lane_native.vbs', 'lane_native_b110.vbs')
SG_PLAN = ('lane_native_sgplan.vbs', 'lane_native_b110_sgplan.vbs')
CONFIG_BASE_NAME = 'config_n31_v2.base.json'
RECEIPT_NAME = 'repin_receipt.json'
PACK_FILES = DECLARATIONS + (TRANSFER_NAME, PROFILE_NAME, RUNNER_CONFIG[0], SG_PLAN[0])

# D-B: prior-calibrated declarations carried over with receipts (plan section 9).
PRIOR_DECLARATIONS = (
    'dynamic_area_routes_ver2_13108c.json',
    'native_input_1093_prehead_ver2_067f5f.json',
    'native_internal_inputs_f8b338.json',
    'route_choice_corridor_1099_sc15_calibrated_23ec67.json',
    'route_choice_corridor_1100_sc15_calibrated_f2a618.json',
    'route_choice_corridor_sc1004_calibrated_6eb99c.json',
    'sc2001_corridor_nc13_f76cd6.json',
)
VSL_SPEEDS = (50, 60, 70, 80, 90, 100, 110)   # user decision 2026-09-24: 10 km/h steps; each needs a v2 distribution
FIRST_RUNTIME_CHECK = 'G1 t=1 decision: every validator runs in configure() before the first no-control action'


class RepinError(RuntimeError):
    """The re-pin refuses; nothing is guessed or defaulted."""


def require(condition, message):
    if not condition:
        raise RepinError(message)


# --------------------------------------------------------------------------- bytes, pins, JSON
def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha6(text):
    return sha256_bytes(text.encode('utf-8'))[:6]


def repo_path(rel, root=None):
    """A pin path as the runtime resolves it (ROOT / path; the pack still carries some backslash paths)."""
    return (root or ROOT) / rel.replace('\\', '/')


def read_pinned(pin, root=None):
    path = repo_path(pin['path'], root)
    require(path.is_file(), f'Pinned file missing: {pin["path"]}')
    data = path.read_bytes()
    require(sha256_bytes(data) == pin['sha256'], f'Pinned file bytes differ: {pin["path"]}')
    return data


def pin_of(rel, data):
    return {'path': rel, 'sha256': sha256_bytes(data)}


def load_json(data):
    return json.loads(data.decode('utf-8-sig'))


def dump_json(document):
    """UTF-8 without BOM, indent 2, LF, trailing newline; key order as built (deterministic)."""
    return (json.dumps(document, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def is_pin(obj):
    return (isinstance(obj, dict) and isinstance(obj.get('path'), str) and isinstance(obj.get('sha256'), str)
            and re.fullmatch(r'[0-9a-f]{64}', obj['sha256']) is not None)


def walk(obj, pointer=''):
    """(pointer, value) for every node, JSON-pointer style."""
    yield pointer, obj
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(value, pointer + '/' + str(key).replace('~', '~0').replace('/', '~1'))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk(value, f'{pointer}/{index}')


def norm(path_text):
    return path_text.replace('\\', '/')


# --------------------------------------------------------------------------- XML
def canonical(node, strip=(), drop_children=(), sort_children=False):
    if node is None:
        return None
    children = [canonical(child, strip, drop_children, sort_children) for child in node if child.tag not in drop_children]
    if sort_children:
        children.sort(key=repr)
    return (node.tag, tuple(sorted((k, v) for k, v in node.attrib.items() if k not in strip)), tuple(children))


def keyed(section):
    rows = {child.get('no'): child for child in section}
    return rows if None not in rows and len(rows) == len(section) else None


def int_key(text):
    return (len(text), text)


ROOT_SECTION = '(root)'


def top_sections(root, label):
    """The top-level tags of a network, each exactly once (find(tag) would read only the first of a repeat)."""
    tags = [child.tag for child in root]
    repeated = sorted({tag for tag in tags if tags.count(tag) > 1})
    require(not repeated, f'{label} network repeats top-level sections {repeated}')
    return tags


def section_diff(old_root, new_root):
    """Every top-level section that differs: own attributes, then added/removed/changed ids (keyed by 'no')
    or 'unkeyed' when the children carry no ids. The root element itself (tag, version, vissimVersion) is
    compared as ROOT_SECTION, and each network must hold every top-level section once."""
    tags = []
    for tag in top_sections(old_root, 'old') + top_sections(new_root, 'new'):
        if tag not in tags:
            tags.append(tag)
    out = {}
    if (old_root.tag, old_root.attrib) != (new_root.tag, new_root.attrib):
        row = {'attributes': {k: {'old': old_root.get(k), 'new': new_root.get(k)}
                              for k in sorted(set(old_root.attrib) | set(new_root.attrib)) if old_root.get(k) != new_root.get(k)}}
        if old_root.tag != new_root.tag:
            row['tag'] = {'old': old_root.tag, 'new': new_root.tag}
        out[ROOT_SECTION] = row
    for tag in tags:
        a, b = old_root.find(tag), new_root.find(tag)
        if a is None or b is None:
            out[tag] = {'presence': 'only_old' if b is None else 'only_new'}
            continue
        if canonical(a) == canonical(b):
            continue
        row = {}
        if a.attrib != b.attrib:
            row['attributes'] = {k: {'old': a.get(k), 'new': b.get(k)}
                                 for k in sorted(set(a.attrib) | set(b.attrib)) if a.get(k) != b.get(k)}
        ka, kb = keyed(a), keyed(b)
        if ka is None or kb is None:
            if [canonical(c) for c in a] != [canonical(c) for c in b]:
                row['unkeyed'] = True
            out[tag] = row
            continue
        added = sorted(kb.keys() - ka.keys(), key=int_key)
        removed = sorted(ka.keys() - kb.keys(), key=int_key)
        changed = [k for k in sorted(ka.keys() & kb.keys(), key=int_key) if canonical(ka[k]) != canonical(kb[k])]
        if added or removed or changed:
            row.update(added=added, removed=removed, changed=changed)
        out[tag] = row
    return out


# What NEW-1 says the v2 network changed, as checkable rules. A section not listed here, or a
# difference of a kind its rule does not allow, stops the re-pin.
CHANGE_RULES = {
    'vehicleInputs': {'changed': {'strip': ('volume',)}, 'meaning': 'demand volumes only (FW80/U90)'},
    'vehicleRoutingDecisionsStatic': {'changed': {'strip': ('relFlow',)}, 'meaning': 'route relFlow only'},
    'desSpeedDecisions': {'changed': {'strip': ('desSpeedDistr',)},
                          'meaning': 'desired speed distribution only'},
    'desSpeedDistributions': {'added': True, 'meaning': 'new distributions'},
    'dataCollectionPoints': {'added': True, 'meaning': 'RULE detector points'},
    'dataCollectionMeasurements': {'added': True, 'meaning': 'RULE detector measurements'},
    'signalControllers': {'changed': {'drop_children': ('scDetRecConf',), 'sort_children': True},
                          'meaning': 'detector-record output block (scDetRecConf) and child order only'},
    'evaluation': {'unkeyed': True, 'meaning': 'evaluation output settings (the runner sets them over COM)'},
    'simulation': {'attributes': ('randSeed', 'simRes'), 'meaning': 'saved seed and SimRes (runner sets the seed)'},
}


def characterize_changes(old_root, new_root):
    """Prove the v2 difference is exactly the NEW-1 kinds (plus seed/SimRes); refuse anything else."""
    diff = section_diff(old_root, new_root)
    report = {}
    for tag, row in diff.items():
        require(tag in CHANGE_RULES, f'v2 network differs in an unreviewed section: {tag} {row}')
        rule = CHANGE_RULES[tag]
        require('presence' not in row, f'{tag}: section present in one network only')
        entry = {'meaning': rule['meaning']}
        if 'attributes' in row:
            require(set(row['attributes']) <= set(rule.get('attributes', ())), f'{tag}: attributes changed {row["attributes"]}')
            entry['attributes'] = row['attributes']
        if row.get('unkeyed'):
            require(rule.get('unkeyed'), f'{tag}: unkeyed content changed')
            a, b = old_root.find(tag), new_root.find(tag)
            # Output configuration only (what VISSIM writes, not the traffic model): same blocks, any settings.
            require([c.tag for c in a] == [c.tag for c in b], f'{tag}: evaluation blocks added or removed')
            entry['settings'] = [{'element': ca.tag, 'old': dict(sorted(set(ca.attrib.items()) - set(cb.attrib.items()))),
                                  'new': dict(sorted(set(cb.attrib.items()) - set(ca.attrib.items()))),
                                  'content_changed': [canonical(x) for x in ca] != [canonical(y) for y in cb]}
                                 for ca, cb in zip(a, b) if canonical(ca) != canonical(cb)]
        require(not row.get('removed'), f'{tag}: elements removed {row.get("removed")}')
        if row.get('added'):
            require(rule.get('added'), f'{tag}: elements added {row["added"]}')
            entry['added'] = row['added']
        if row.get('changed'):
            require('changed' in rule, f'{tag}: elements changed {row["changed"]}')
            a, b = keyed(old_root.find(tag)), keyed(new_root.find(tag))
            still = [k for k in row['changed'] if canonical(a[k], **rule['changed']) != canonical(b[k], **rule['changed'])]
            require(not still, f'{tag}: {still} differ beyond "{rule["meaning"]}"')
            entry['changed'] = row['changed']
            if tag == 'vehicleRoutingDecisionsStatic':
                entry['relflow'] = {k: {r.get('no'): {'old': r.get('relFlow'), 'new': s.get('relFlow')}
                                        for r, s in zip(a[k].iter('vehicleRouteStatic'), b[k].iter('vehicleRouteStatic'))
                                        if r.get('relFlow') != s.get('relFlow')} for k in row['changed']}
            if tag == 'desSpeedDecisions':
                values = {(x.get('desSpeedDistr'), y.get('desSpeedDistr'))
                          for k in row['changed'] for x, y in zip(a[k].iter('vehClassDesSpeedDistribution'),
                                                                    b[k].iter('vehClassDesSpeedDistribution'))
                          if x.get('desSpeedDistr') != y.get('desSpeedDistr')}
                entry['distribution_changes'] = [{'old': o, 'new': n} for o, n in sorted(values)]
        report[tag] = entry
    return report


def native_diff(old_root, new_root):
    """prepare_scenario.py:28-50: the record format of historical_prior_transfer.actual_native_differences."""
    top_sections(old_root, 'old')
    top_sections(new_root, 'new')
    result = {}
    for section in ('links', 'signalHeads', 'vehicleInputs', 'vehicleRoutingDecisionsStatic',
                    'signalControllers', 'desSpeedDecisions'):
        a = {x.get('no'): x for x in old_root.find(section)}
        b = {x.get('no'): x for x in new_root.find(section)}
        changed = [key for key in sorted(a.keys() | b.keys(), key=int) if canonical(a.get(key)) != canonical(b.get(key))]
        result[section] = {'added': sorted(b.keys() - a.keys()), 'removed': sorted(a.keys() - b.keys()), 'changed': changed}
    a = {x.get('no'): x for x in old_root.find('links')}
    b = {x.get('no'): x for x in new_root.find('links')}
    require(set(a) == set(b), 'Membership transfer requires identical physical link identities')

    def signature(x):
        return (len(x.findall('./lanes/lane')),
                tuple(x.find(k).get('lane') if x.find(k) is not None else None for k in ('fromLinkEndPt', 'toLinkEndPt')))
    require(all(signature(a[k]) == signature(b[k]) for k in a), 'Physical membership transfer changes an edge or lane identity')
    result['membership_basis'] = 'Same link IDs, connector endpoints and lane identities; no territorial re-derivation'
    return result


def vehicle_input_evidence(tree, number):
    node = tree.find(f"./vehicleInputs/vehicleInput[@no='{number}']")
    require(node is not None, f'vehicle input {number} missing')
    row = dict(sorted(node.attrib.items()))
    row['intervals'] = [dict(sorted(x.attrib.items())) for x in node.findall('./timeIntVehVols/timeIntervalVehVolume')]
    return row


def decision_evidence(tree, number):
    node = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{number}']")
    require(node is not None, f'routing decision {number} missing')
    row = dict(sorted(node.attrib.items()))
    routes = []
    for route in node.findall('./vehRoutSta/vehicleRouteStatic'):
        item = dict(sorted(route.attrib.items()))
        item['path'] = [node.get('link')] + [x.get('key') for x in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
        routes.append(item)
    row['routes'] = routes
    return row


def route_relflow(tree, decision, route):
    node = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{decision}']"
                     f"/vehRoutSta/vehicleRouteStatic[@no='{route}']")
    require(node is not None, f'route {decision}:{route} missing')
    return node.get('relFlow')


def sig_controllers(tree):
    """{.sig name: [controller rows]}, and controllers that carry no supply file.

    'offset' is the .inpx signalController attribute ("0" on all 50 v2 controllers), not the programme offset,
    which lives in the .sig <prog offset> (NEW-9); obs150_signal_clock reads the .sig. No consumer reads this
    field (obs150_observation.sig_manifest_files and launch_plan.sig_table read name and sha256 only)."""
    by_sig, without = {}, []
    for sc in tree.findall('./signalControllers/signalController'):
        supply = sc.get('supplyFile2', '')
        row = {'sc': sc.get('no'), 'prog_no': int(sc.get('progNo')), 'type': sc.get('type'), 'offset': sc.get('offset')}
        if not supply:
            without.append(row)
            continue
        require(supply.startswith('#data#') and '/' not in supply and '\\' not in supply,
                f'SC {sc.get("no")} supply file is not a #data# sibling: {supply}')
        by_sig.setdefault(supply[len('#data#'):], []).append(row)
    return by_sig, sorted(without, key=lambda r: int(r['sc']))


def background_images(tree):
    return sorted({node.get('pathFilename', '') for node in tree.iter('backgroundImage') if node.get('pathFilename')})


def sig_equal_to_folder(sig, folder):
    """NEW-1 '.sig unchanged': every v2 supply file is a byte copy of the same-named file in folder."""
    for name, data in sorted(sig.items()):
        sibling = folder / name
        require(sibling.is_file() and sibling.read_bytes() == data,
                f'v2 {name} is not a byte copy of {sibling} (the .sig the pack declarations were derived from)')
    return len(sig)


# --------------------------------------------------------------------------- inputs
class Sources:
    """Everything the re-pin reads, loaded once and pinned."""

    def __init__(self, root=ROOT, net_dir=NET_DIR, network_from='net'):
        self.root = root
        self.net_dir = net_dir
        pack = root / PACK_REL
        present = sorted(p.name for p in pack.iterdir() if p.is_file())
        require(present == sorted(PACK_FILES), f'Pack differs from the plan list: extra {sorted(set(present) - set(PACK_FILES))} '
                                              f'missing {sorted(set(PACK_FILES) - set(present))}')
        self.pack = {name: (pack / name).read_bytes() for name in PACK_FILES}
        self.obs1 = (root / OBS1_REL).read_bytes()
        self.old_network = read_pinned(OLD_PIN, root)
        self.old_transfer = load_json(self.pack[TRANSFER_NAME])
        require(self.old_transfer.get('schema') == TRANSFER_SCHEMA, 'Pack transfer receipt schema')
        require(self.old_transfer['target_network'] == OLD_PIN, 'Pack transfer receipt does not target fcb349d3')
        self.training_pin = dict(self.old_transfer['source_network'])
        self.training_network = read_pinned(self.training_pin, root)
        # The v2 network: NET for a build, the pinned copy for verify (same bytes by construction).
        if network_from == 'net':
            source = net_dir / NET_INPX
            require(source.is_file(), f'NET network missing: {source}')
            self.network = source.read_bytes()
            self.sig_dir = net_dir
        else:
            self.network = read_pinned(V2_PIN, root)
            self.sig_dir = repo_path(NETWORK_DIR_REL, root)
        require(sha256_bytes(self.network) == V2_SHA256, 'v2 network sha differs from f475ce42 (plan N31 E7)')
        self.old_tree = ET.fromstring(self.old_network)
        self.new_tree = ET.fromstring(self.network)
        self.training_tree = ET.fromstring(self.training_network)
        by_sig, self.controllers_without_sig = sig_controllers(self.new_tree)
        names = sorted(p.name for p in self.sig_dir.iterdir() if p.is_file() and p.suffix.lower() == '.sig')
        require(sorted(by_sig) == names, f'.sig files beside the network differ from the .inpx references: '
                                         f'unreferenced {sorted(set(names) - set(by_sig))} missing {sorted(set(by_sig) - set(names))}')
        require(len(names) == SIG_COUNT, f'{len(names)} .sig files, expected {SIG_COUNT}')
        self.sig = {name: (self.sig_dir / name).read_bytes() for name in names}
        self.sig_controllers = {name: sorted(rows, key=lambda r: int(r['sc'])) for name, rows in by_sig.items()}
        # The .sig-derived declarations (phase authority, route-choice clocks, SG plan) were read beside the
        # training network (fcb349d3 has no .sig of its own), so the v2 copies must be those bytes.
        self.sig_reference = PurePosixPath(norm(self.training_pin['path'])).parent.as_posix()
        sig_equal_to_folder(self.sig, repo_path(self.sig_reference, root))


# --------------------------------------------------------------------------- network outputs
def sig_manifest(sources):
    return {
        'schema': SIG_MANIFEST_SCHEMA,
        'network': {'name': NET_INPX, **V2_PIN, 'bytes': len(sources.network)},
        'copied_from': str(NET_DIR),
        'copy_rule': 'The .inpx and the .sig supply files it references, byte for byte. Not copied: run outputs '
                     '(*.err, *.results) and the #data# background image (graphics only).',
        'background_images_not_copied': background_images(sources.new_tree),
        'files': [{'name': name, 'sha256': sha256_bytes(data), 'bytes': len(data), 'controllers': sources.sig_controllers[name]}
                  for name, data in sorted(sources.sig.items())],
        'controllers_without_sig': sources.controllers_without_sig,
    }


# --------------------------------------------------------------------------- naming and rewriting
def target_name(pack_name, document):
    """Declaration stem + sha6 of the PACK path it came from (prepare_scenario.py:76 naming rule)."""
    source = document['scenario_derivation']['source_declaration']['path']
    stem = PurePosixPath(norm(source)).stem
    match = re.fullmatch(re.escape(stem) + r'_([0-9a-f]{6})', PurePosixPath(pack_name).stem)
    require(match is not None, f'{pack_name}: name is not <declaration stem>_<6 hex>')
    return f'{stem}_{sha6(PACK_REL + "/" + pack_name)}.json'


class Rewriter:
    """PACK paths -> new files, fcb349d3 network pins -> v2. Records every rewritten pointer."""

    def __init__(self, path_map, pin_map, pack_bytes):
        self.path_map = path_map          # PACK rel -> new rel
        self.pin_map = pin_map            # PACK rel -> new pin (known once converted)
        self.pack_bytes = pack_bytes      # PACK rel -> bytes (a pin into the pack must be current)
        self.edits = []

    def __call__(self, obj, pointer=''):
        if isinstance(obj, dict):
            path = obj.get('path')
            if is_pin(obj) and norm(path) == OLD_PIN['path']:
                require(obj['sha256'] == OLD_PIN['sha256'], f'{pointer}: fcb network path with another sha')
                self.edits.append({'at': pointer, 'kind': 'network_pin'})
                return {**obj, **V2_PIN}
            if isinstance(path, str) and norm(path) in self.path_map:
                source = norm(path)
                if 'sha256' in obj:
                    require(obj['sha256'] == sha256_bytes(self.pack_bytes[source]), f'{pointer}: stale pin to {source}')
                self.edits.append({'at': pointer, 'kind': 'pack_pin'})
                return {**obj, **self.pin_map[source]}
            return {key: self(value, pointer + '/' + str(key).replace('~', '~0').replace('/', '~1'))
                    for key, value in obj.items()}
        if isinstance(obj, list):
            return [self(value, f'{pointer}/{index}') for index, value in enumerate(obj)]
        if isinstance(obj, str):
            if norm(obj) in self.path_map:
                self.edits.append({'at': pointer, 'kind': 'pack_path'})
                return self.path_map[norm(obj)]
            require(obj != OLD_PIN['sha256'] and norm(obj) != OLD_PIN['path'],
                    f'{pointer}: bare fcb network reference outside a pin')
        return obj


def pack_references(document):
    """PACK file names a document points at (pin paths and bare path strings)."""
    names = set()
    for _, value in walk(document):
        text = value.get('path') if isinstance(value, dict) else value if isinstance(value, str) else None
        if isinstance(text, str) and norm(text).startswith(PACK_REL + '/'):
            names.add(PurePosixPath(norm(text)).name)
    return names


def collect_priors(document, is_dynamic):
    """prepare_scenario.py:77-89: the training-artifact pins a prior transfer must list."""
    priors = []
    if document.get('schema') == 'route-choice-corridor/v1' and document.get('native_fixed_service', {}).get('calibrated_discharge'):
        priors.append(('/native_fixed_service/calibrated_discharge', document['native_fixed_service']['calibrated_discharge']))
    if document.get('service_resource_calibration'):
        priors.append(('/service_resource_calibration', document['service_resource_calibration']))
    if is_dynamic:
        priors.append(('/calibration', document['calibration']))
    for pointer, value in walk(document):
        if isinstance(value, dict) and 'calibration' in value and 'resolved_source_vehicles' in value:
            priors.append((pointer + '/calibration', value['calibration']))
    return priors


def pin_only(pin):
    return {k: pin[k] for k in ('path', 'sha256')}


# --------------------------------------------------------------------------- VBS
def set_vsl_speeds(data, speeds):
    """Set RW_ALLOWED_VSL_SPEEDS to exactly `speeds` (ascending); every other byte unchanged (BOM and line ends kept).

    Returns (bytes, the list it replaced). Refuses a missing or repeated line, a non-integer list, an empty or
    unsorted/duplicated target, and a no-op (the pack line must actually change)."""
    speeds = [int(v) for v in speeds]
    require(speeds and speeds == sorted(set(speeds)), f'VSL speeds must be ascending and distinct: {speeds}')
    bom = codecs.BOM_UTF8 if data.startswith(codecs.BOM_UTF8) else b''
    text = data[len(bom):].decode('utf-8')
    lines = text.split('\n')
    hits = [i for i, line in enumerate(lines) if line.startswith('RW_ALLOWED_VSL_SPEEDS')]
    require(len(hits) == 1, f'RW_ALLOWED_VSL_SPEEDS must appear once, found {len(hits)}')
    line = lines[hits[0]]
    ending = '\r' if line.endswith('\r') else ''
    match = re.fullmatch(r'RW_ALLOWED_VSL_SPEEDS = "([0-9]+(?:,[0-9]+)*)"', line[:len(line) - len(ending)])
    require(match is not None, 'RW_ALLOWED_VSL_SPEEDS is not a plain integer list')
    values = [int(x) for x in match.group(1).split(',')]
    require(values != speeds, f'RW_ALLOWED_VSL_SPEEDS already is {",".join(map(str, speeds))}')
    lines[hits[0]] = 'RW_ALLOWED_VSL_SPEEDS = "' + ','.join(str(v) for v in speeds) + '"' + ending
    return bom + '\n'.join(lines).encode('utf-8'), values


def vbs_constants(data):
    text = data.decode('utf-8-sig')
    return {m.group(1): m.group(2) for m in re.finditer(r'^(RW_[A-Z0-9_]+) = "([^"\r\n]*)"', text, re.M)}


def runner_config_check(data, tree):
    """The runner config names only elements the v2 network has; VSL speeds map to distributions."""
    constants = vbs_constants(data)
    links = {x.get('no') for x in tree.findall('./links/link')}
    scs = {x.get('no') for x in tree.findall('./signalControllers/signalController')}
    dsds = {x.get('no') for x in tree.findall('./desSpeedDecisions/desSpeedDecision')}
    distributions = {x.get('no') for x in tree.findall('./desSpeedDistributions/desSpeedDistribution')}
    lists = {key: [v for v in constants[key].split(',') if v] for key in (
        'RW_FW_E_CHAIN_LINKS', 'RW_FW_W_CHAIN_LINKS', 'RW_FREEWAY_LINKS', 'RW_RAMP_METER_CONNECTORS',
        'RW_RAMP_METER_SCS', 'RW_SIGNAL_SCS', 'RW_EXPECTED_VSL_DSD_IDS', 'RW_ALLOWED_VSL_SPEEDS')}
    for key in ('RW_FW_E_CHAIN_LINKS', 'RW_FW_W_CHAIN_LINKS', 'RW_FREEWAY_LINKS', 'RW_RAMP_METER_CONNECTORS'):
        require(set(lists[key]) <= links, f'{key} names links the v2 network lacks: {sorted(set(lists[key]) - links)}')
    for key in ('RW_RAMP_METER_SCS', 'RW_SIGNAL_SCS'):
        require(set(lists[key]) <= scs, f'{key} names controllers the v2 network lacks')
    require(set(lists['RW_EXPECTED_VSL_DSD_IDS']) <= dsds, 'RW_EXPECTED_VSL_DSD_IDS names absent decisions')
    require([int(v) for v in lists['RW_ALLOWED_VSL_SPEEDS']] == list(VSL_SPEEDS),
            f'RW_ALLOWED_VSL_SPEEDS is {lists["RW_ALLOWED_VSL_SPEEDS"]}, expected {list(VSL_SPEEDS)}')
    missing = [v for v in VSL_SPEEDS if str(v) not in distributions]
    require(not missing, f'v2 network lacks desSpeedDistribution {missing}')
    return {
        'elements_present': sorted(k for k in lists if k != 'RW_ALLOWED_VSL_SPEEDS'),
        'allowed_vsl_speeds': [int(v) for v in lists['RW_ALLOWED_VSL_SPEEDS']],
        'allowed_speeds_without_distribution': sorted(int(v) for v in lists['RW_ALLOWED_VSL_SPEEDS'] if v not in distributions),
        'seg_bounds_cells': {road: len(constants[f'RW_FW_{road}_SEG_BOUNDS'].split(',')) - 1 for road in ('E', 'W')},
    }


# --------------------------------------------------------------------------- evidence refresh and audits
def refresh_sc2001(document, tree):
    """Plan section 5: refill the embedded native input evidence from the v2 XML; routes are re-read."""
    updates = {}
    evidence = document['native_input_evidence']
    for index, row in enumerate(evidence['inputs']):
        fresh = vehicle_input_evidence(tree, row['no'])
        require(set(fresh) == set(row) and fresh['link'] == row['link'], f'SC2001 input {row["no"]} changed shape')
        if fresh != row:
            updates[f'/native_input_evidence/inputs/{index}'] = {
                'no': row['no'], 'old_volumes': [x['volume'] for x in row['intervals']],
                'new_volumes': [x['volume'] for x in fresh['intervals']]}
        evidence['inputs'][index] = fresh
    for key, row in document['native_upstream_routes'].items():
        fresh = decision_evidence(tree, key)
        require(fresh == row, f'SC2001 upstream routing decision {key} differs on v2')
    return updates


def refresh_known_wout(document, tree):
    """prepare_scenario.py:129-141 on the v2 XML."""
    updates = {}
    for key, row in document['native_routes'].items():
        decision, route = key.split(':')
        choice = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{decision}']")
        native = choice.find(f"./vehRoutSta/vehicleRouteStatic[@no='{route}']")
        actual = [choice.get('link')] + [x.get('key') for x in native.findall('./linkSeq/intObjectRef')] + [native.get('destLink')]
        require(actual == row['path'], 'Known route transfer changes its physical path: ' + key)
        position = float(native.get('destPos'))
        if position != row['dest_pos']:
            updates[key] = {'old': row['dest_pos'], 'current': position}
        row['dest_pos'] = position
    return updates


RELFLOW_KEYS = ('relFlow', 'rel_flow', 'relflow_raw')


def relflow_audit(name, document, sources, changed_decisions):
    """Account for every embedded relFlow copy; a copy no rule explains is a refusal.

    Rules: {decision, route, relflow_raw} rows (membership mixed transfer routes); native-input-prehead
    branches (route = branch key, decision = document decision); SC2001 upstream routes, which
    refresh_sc2001 already required equal to the v2 decision element.
    A copy equals the v2 XML, or it is lineage evidence: equal to the training network the declaration was
    derived on, for a decision the fcb->v2 step did not change (the pack carried it unchanged from there).
    """
    result = {'equal_v2': 0, 'lineage': []}
    for pointer, value in walk(document):
        if not isinstance(value, dict) or not any(key in value for key in RELFLOW_KEYS):
            continue
        parts = pointer.split('/')
        if {'decision', 'route', 'relflow_raw'} <= set(value):
            decision, route, copied = value['decision'], value['route'], value['relflow_raw']
        elif document.get('schema') == 'native-input-prehead/v1' and len(parts) == 3 and parts[1] == 'branches':
            decision, route, copied = document['decision'], parts[2], value['rel_flow']
        elif document.get('schema') == 'sc2001-corridor/v1' and pointer.startswith('/native_upstream_routes/'):
            result['equal_v2'] += 1   # the whole decision element was compared in refresh_sc2001
            continue
        else:
            raise RepinError(f'{name}{pointer}: a relFlow copy no audit rule covers')
        actual = route_relflow(sources.new_tree, decision, route)
        require(isinstance(copied, str), f'{name}{pointer}: relFlow copy is not a string ({copied!r})')
        require(actual is not None, f'{name}{pointer}: v2 route {decision}:{route} carries no relFlow')
        if actual == copied:
            result['equal_v2'] += 1
            continue
        training = route_relflow(sources.training_tree, decision, route)
        require(copied == training and str(decision) not in changed_decisions,
                f'{name}{pointer}: relFlow copy {copied!r} is neither v2 ({actual!r}) nor its derivation network ({training!r})')
        result['lineage'].append({'at': pointer, 'decision': str(decision), 'route': str(route), 'copy': copied,
                                  'previous_pack_network': route_relflow(sources.old_tree, decision, route), 'v2': actual})
    return result


def stale_evidence_audit(name, document, changes):
    """Refuse embedded copies of changed XML values other than the ones refreshed or re-read above."""
    changed_decisions = set(changes.get('vehicleRoutingDecisionsStatic', {}).get('changed', []))
    for pointer, value in walk(document):
        if isinstance(value, dict):
            for key in value:
                low = str(key).lower()
                require('desspeed' not in low, f'{name}{pointer}/{key}: embedded desired-speed evidence')
                if low == 'volume':
                    require(document.get('schema') == 'sc2001-corridor/v1' and pointer.startswith('/native_input_evidence/'),
                            f'{name}{pointer}: embedded demand volume outside the refreshed SC2001 evidence')
                if re.fullmatch(r'\d+:\d+', str(key)) and str(key).split(':')[0] in changed_decisions:
                    require(document.get('schema') == 'known-wout-routes/v1' and pointer == '/native_routes',
                            f'{name}{pointer}/{key}: route of a changed decision outside the re-read known routes')
            for key in ('decision', 'decision_no', 'native_decision'):
                require(str(value.get(key)) not in changed_decisions or 'relflow_raw' not in value,
                        f'{name}{pointer}: relFlow copy of a changed decision')


def pin_audit(rel, document, outputs, sources, exempt):
    """Every pin resolves (outputs by their new bytes); network pins are v2; .sig pins equal the v2 copies.

    An absolute path (another machine's provenance, e.g. physical_phase_authority native_clock_derivation)
    cannot resolve here; it is listed, never read, and may not be a network, .sig or pack pin.
    """
    count, external = 0, []
    sig_sha = {name: sha256_bytes(data) for name, data in sources.sig.items()}
    for pointer, value in walk(document):
        if not is_pin(value) or any(pointer == e or pointer.startswith(e + '/') for e in exempt):
            continue
        path = norm(value['path'])
        if PurePosixPath(path).is_absolute() or ':' in path:
            require(not path.lower().endswith(('.inpx', '.sig')), f'{rel}{pointer}: absolute network or .sig pin')
            external.append({'at': pointer, **pin_only(value)})
            continue
        data = outputs[path] if path in outputs else read_pinned(value, sources.root)
        require(sha256_bytes(data) == value['sha256'], f'{rel}{pointer}: pin bytes differ ({path})')
        if path.lower().endswith('.inpx'):
            require(pin_only(value) == V2_PIN, f'{rel}{pointer}: network pin is not the v2 network')
        if path.lower().endswith('.sig'):
            name = PurePosixPath(path).name
            require(sig_sha.get(name) == value['sha256'], f'{rel}{pointer}: .sig differs from the v2 network copy {name}')
        require(not path.startswith(PACK_REL + '/'), f'{rel}{pointer}: pin still into the fcb pack')
        count += 1
    for pointer, value in walk(document):
        if isinstance(value, str) and not any(pointer == e or pointer.startswith(e + '/') for e in exempt):
            require(not norm(value).startswith(PACK_REL + '/') and OLD_PIN['sha256'] not in value
                    and norm(value) != OLD_PIN['path'], f'{rel}{pointer}: reference to the fcb pack or network')
    return {'resolved': count, 'external_provenance': external}


# --------------------------------------------------------------------------- the build
DERIVATION_EXEMPT = ('/scenario_derivation/lineage', '/scenario_derivation/source_declaration')


def prior_block(name, document, priors, transfer_pin, changes):
    known = [f'{tag}: {changes[tag]["meaning"]} ({len(changes[tag].get("changed", changes[tag].get("added", [])))} elements)'
             for tag in ('vehicleInputs', 'vehicleRoutingDecisionsStatic', 'desSpeedDecisions') if tag in changes]
    block = {
        'status': 'transferred_without_refit',
        'decision': 'D-B (2026-09-24): carry the prior over with receipts, mark prior_mismatch, refit after the first 9000 s run',
        'priors': [{'at': pointer, **pin_only(pin)} for pointer, pin in priors],
        'receipt': transfer_pin,
        'target_network': dict(V2_PIN),
        'differences_since_previous_pack': known,
        'differences_since_training': 'receipt actual_native_differences (training network -> v2)',
        'refit_after': 'the first 9000 s SDMPC run (V5) and its paired no-control run (V4)',
    }
    if name == 'sc2001_corridor_nc13_f76cd6.json':
        calibration = document['calibration']
        block['embedded_prior'] = {'at': '/calibration', 'kind': calibration['kind'], 'run_id': calibration['run_id'],
                                   'simulation_seed': calibration['simulation_seed'],
                                   'training_fzp_path': calibration['fzp_path'], 'training_fzp_sha256': calibration['fzp_sha256'],
                                   'runtime_reads_training_fzp': calibration['runtime_reads_training_fzp']}
    if name == 'route_choice_corridor_sc1004_calibrated_6eb99c.json':
        block['embedded_prior'] = {'at': None, 'note': 'Calibrated by declaration (plan D-B); the declaration pins no '
                                                        'separate prior file or training run.'}
    return block


def pack_closure(obs1, documents):
    """PACK files reachable from the tuning (directly or through declarations); the SG plan rides on the runner config."""
    reached, frontier = set(), set(pack_references(obs1))
    while frontier:
        name = frontier.pop()
        reached.add(name)
        if name in documents:
            frontier |= pack_references(documents[name]) - reached
    if RUNNER_CONFIG[0] in reached:
        reached.add(SG_PLAN[0])
    return reached


def build_outputs(sources):
    """Every output as bytes (copies included), plus the receipt. Pure: reads sources only."""
    pack_bytes = {f'{PACK_REL}/{name}': data for name, data in sources.pack.items()}
    changes = characterize_changes(sources.old_tree, sources.new_tree)
    simres = sources.new_tree.find('simulation').get('simRes')
    require(simres == str(EXPECTED_SIMRES), f'v2 network SimRes {simres} differs from the contract ({EXPECTED_SIMRES})')
    outputs = copies(sources)

    manifest = sig_manifest(sources)
    outputs[SIG_MANIFEST_REL] = dump_json(manifest)
    manifest_pin = pin_of(SIG_MANIFEST_REL, outputs[SIG_MANIFEST_REL])

    documents = {name: load_json(sources.pack[name]) for name in DECLARATIONS}
    obs1 = load_json(sources.obs1)
    closure = pack_closure(obs1, documents)
    require(closure == set(PACK_FILES), f'Pack files the tuning does not reach: {sorted(set(PACK_FILES) - closure)}')
    path_map = {f'{PACK_REL}/{name}': f'{SCENARIO_REL}/{target_name(name, doc)}' for name, doc in documents.items()}
    path_map[f'{PACK_REL}/{TRANSFER_NAME}'] = f'{SCENARIO_REL}/{TRANSFER_NAME}'
    path_map[f'{PACK_REL}/{PROFILE_NAME}'] = f'{SCENARIO_REL}/{PROFILE_NAME}'
    path_map[f'{PACK_REL}/{RUNNER_CONFIG[0]}'] = f'{SCENARIO_REL}/{RUNNER_CONFIG[1]}'
    path_map[f'{PACK_REL}/{SG_PLAN[0]}'] = f'{SCENARIO_REL}/{SG_PLAN[1]}'
    require(len(set(path_map.values())) == len(path_map), 'Two pack files map to one name')
    pin_map = {}

    # profile, runner config, SG plan
    outputs[path_map[f'{PACK_REL}/{PROFILE_NAME}']] = sources.pack[PROFILE_NAME]
    runner_bytes, old_speeds = set_vsl_speeds(sources.pack[RUNNER_CONFIG[0]], VSL_SPEEDS)
    outputs[f'{SCENARIO_REL}/{RUNNER_CONFIG[1]}'] = runner_bytes
    outputs[f'{SCENARIO_REL}/{SG_PLAN[1]}'] = sources.pack[SG_PLAN[0]]
    runner_check = runner_config_check(runner_bytes, sources.new_tree)
    for name in (PROFILE_NAME, RUNNER_CONFIG[0], SG_PLAN[0]):
        pin_map[f'{PACK_REL}/{name}'] = pin_of(path_map[f'{PACK_REL}/{name}'], outputs[path_map[f'{PACK_REL}/{name}']])

    # the transfer receipt: training network -> v2 (priors unchanged)
    dynamic_rel = norm(obs1['urban']['movements']['dynamic_physical_route_topology'])
    priors = {name: collect_priors(doc, f'{PACK_REL}/{name}' == dynamic_rel) for name, doc in documents.items()}
    # Distinct training artifacts (the runtime checks membership: scenario_prior_transfer.training_network).
    unchanged = []
    for name in sorted(priors):
        for _, pin in priors[name]:
            if pin_only(pin) not in unchanged:
                unchanged.append(pin_only(pin))
    old_unchanged = {json.dumps(pin_only(pin), sort_keys=True) for pin in sources.old_transfer['unchanged_prior_files']}
    require({json.dumps(pin, sort_keys=True) for pin in unchanged} == old_unchanged,
            'The prior files found in the pack differ from the pack transfer receipt')
    for pin in unchanged:
        read_pinned(pin, sources.root)
    carriers = sorted(name for name, found in priors.items() if found)
    require(set(carriers) <= set(PRIOR_DECLARATIONS), f'Unlisted prior carriers: {sorted(set(carriers) - set(PRIOR_DECLARATIONS))}')
    old_transfer_pin = pin_of(f'{PACK_REL}/{TRANSFER_NAME}', sources.pack[TRANSFER_NAME])
    transfer = {
        'schema': TRANSFER_SCHEMA,
        'source_network': dict(sources.training_pin),
        'target_network': dict(V2_PIN),
        'predictive_accuracy_validated': False,
        'unchanged_prior_files': unchanged,
        'actual_native_differences': native_diff(sources.training_tree, sources.new_tree),
        'limitations': list(sources.old_transfer['limitations']) + [
            'The v2 network (FW80/U90 demand, 1130/1131 split, DSD 110) differs again from the pack network fcb349d3; '
            'see repin_step. The priors keep their training network and bytes.'],
        'repin_step': {
            'previous_transfer': old_transfer_pin,
            'from_network': dict(OLD_PIN),
            'to_network': dict(V2_PIN),
            'native_changes': changes,
        },
        'prior_mismatch': {
            'status': 'transferred_without_refit',
            'decision': 'D-B (2026-09-24): carry over with receipts; refit after the first 9000 s run',
            'declarations': sorted(path_map[f'{PACK_REL}/{name}'] for name in PRIOR_DECLARATIONS),
        },
    }
    outputs[f'{SCENARIO_REL}/{TRANSFER_NAME}'] = dump_json(transfer)
    transfer_pin = pin_of(f'{SCENARIO_REL}/{TRANSFER_NAME}', outputs[f'{SCENARIO_REL}/{TRANSFER_NAME}'])
    pin_map[f'{PACK_REL}/{TRANSFER_NAME}'] = transfer_pin

    rows, active = {}, set()

    def convert(name):
        source_rel = f'{PACK_REL}/{name}'
        if source_rel in pin_map:
            return pin_map[source_rel]
        require(name not in active, 'Cyclic scenario declarations: ' + name)
        active.add(name)
        document = copy.deepcopy(documents[name])
        for other in sorted(pack_references(document) & set(DECLARATIONS) - {name}):   # what it points at first
            convert(other)
        rewrite = Rewriter(path_map, pin_map, pack_bytes)
        lineage = document.pop('scenario_derivation')
        document = rewrite(document)
        row = {'source': pin_of(source_rel, sources.pack[name]), 'schema': document.get('schema'),
               'rewritten': rewrite.edits, 'prior_mismatch': name in PRIOR_DECLARATIONS}
        derivation = {'source_declaration': row['source'], 'runtime_network': dict(V2_PIN),
                      'accuracy_validation': 'pending', 'lineage': lineage,
                      'repin': {'tool': TOOL_REL, 'plan': 'SDMPC31_OBS150_PLAN_20260924 section 5',
                                'runtime_validation': FIRST_RUNTIME_CHECK,
                                'rewritten': {kind: sum(e['kind'] == kind for e in rewrite.edits)
                                              for kind in ('network_pin', 'pack_pin', 'pack_path')}}}
        if document.get('schema') == 'known-wout-routes/v1':
            derivation['actual_native_destination_updates'] = refresh_known_wout(document, sources.new_tree)
        if document.get('schema') == 'sc2001-corridor/v1':
            derivation['native_evidence_updates'] = refresh_sc2001(document, sources.new_tree)
        if document.get('schema') == 'physical-ramp-configuration/v1':
            connectors = document['shared_city_arrival']['movement_connectors']
            require(connectors.get('SC1004_W_to_E_SC1005') == '10634' and connectors.get('SC1004_W_to_N_SC1003') == '10635',
                    'Pack ramp configuration lost its prepare_scenario SC1004 connectors')
        if name in PRIOR_DECLARATIONS:
            derivation['prior_mismatch'] = prior_block(name, document, priors[name], transfer_pin, changes)
        stale_evidence_audit(name, document, changes)
        row['relflow_copies'] = relflow_audit(
            name, document, sources, set(changes.get('vehicleRoutingDecisionsStatic', {}).get('changed', [])))
        document['scenario_derivation'] = derivation
        data = dump_json(document)
        target = path_map[source_rel]
        outputs[target] = data
        pin_map[source_rel] = pin_of(target, data)
        row['target'] = pin_map[source_rel]
        rows[name] = row
        active.discard(name)
        return pin_map[source_rel]

    for name in DECLARATIONS:
        convert(name)

    # the base tuning: OBS1 with every pack path and network pin re-pointed
    rewrite = Rewriter(path_map, pin_map, pack_bytes)
    config = rewrite(obs1)
    config['name'] = 'sdmpc31_v2_repin_base_20260924'
    config['description'] = ('WP-E base (plan section 5): ' + OBS1_REL + ' with the scenario pack and network pins re-pointed '
                             'to the FW80/U90 v2 network f475ce42. Not launchable alone: freeway.lane_plant still selects '
                             'the v1 manifest; WP-C make_config_n31.py layers the v2 differences. | ' + obs1['description'])
    config['_repin'] = {'schema': 'sdmpc31-config-base/v1', 'source_config': pin_of(OBS1_REL, sources.obs1),
                        'tool': TOOL_REL, 'rewritten': rewrite.edits,
                        'prior_mismatch': sorted(path_map[f'{PACK_REL}/{name}'] for name in PRIOR_DECLARATIONS)}
    outputs[f'{SCENARIO_REL}/{CONFIG_BASE_NAME}'] = dump_json(config)
    config_pin = pin_of(f'{SCENARIO_REL}/{CONFIG_BASE_NAME}', outputs[f'{SCENARIO_REL}/{CONFIG_BASE_NAME}'])

    # audits over the new bytes (pins resolve against the outputs first, then the tree)
    audit = {}
    documents_out = {rel: load_json(data) for rel, data in outputs.items() if rel.endswith('.json')}
    for rel, document in sorted(documents_out.items()):
        exempt = DERIVATION_EXEMPT
        if rel.endswith('/' + TRANSFER_NAME):
            exempt = ('/source_network', '/repin_step/previous_transfer', '/repin_step/from_network')
        if rel == SIG_MANIFEST_REL:
            exempt = ()
        if rel.endswith('/' + CONFIG_BASE_NAME):
            exempt = ('/_repin/source_config',)
        audit[rel] = pin_audit(rel, document, outputs, sources, exempt)

    files = [rows[name] for name in DECLARATIONS]
    files.append({'source': old_transfer_pin, 'schema': TRANSFER_SCHEMA, 'target': transfer_pin,
                  'action': 'regenerated: training network kept, target v2, prior list checked equal'})
    for name, action in ((PROFILE_NAME, 'byte copy'),
                         (RUNNER_CONFIG[0], f'copy; RW_ALLOWED_VSL_SPEEDS {",".join(map(str, old_speeds))} -> '
                                            f'{",".join(map(str, VSL_SPEEDS))} (user decision 2026-09-24)'),
                         (SG_PLAN[0], 'byte copy; name follows the runner config (VBS LoadSignalGroupPlanConfig)')):
        files.append({'source': pin_of(f'{PACK_REL}/{name}', sources.pack[name]), 'target': pin_map[f'{PACK_REL}/{name}'],
                      'action': action})
    membership = pin_map[f'{PACK_REL}/control_area_membership_6c3aee.json']
    receipt = {
        'schema': RECEIPT_SCHEMA,
        'plan': 'D:\\VISSIM-merge\\evidence\\SDMPC31_OBS150_PLAN_20260924.md section 5 (WP-E); user decision D-B',
        'tool': TOOL_REL,
        'inputs': {'pack': PACK_REL, 'source_config': pin_of(OBS1_REL, sources.obs1), 'previous_network': dict(OLD_PIN),
                   'training_network': dict(sources.training_pin), 'network_source_folder': str(NET_DIR)},
        'network': {'inpx': dict(V2_PIN), 'sig_manifest': manifest_pin, 'sig_files': len(sources.sig),
                    'sig_byte_equal_to': {'folder': sources.sig_reference, 'files': len(sources.sig),
                                          'meaning': 'the .sig files beside the training network the pack was derived on'}},
        'native_changes_from_previous_pack': changes,
        'files': files,
        'config_base': config_pin,
        'runner_config_check': runner_check,
        'pin_audit': audit,
        'integration': {
            'plant_manifest_v2': {'sources.network': dict(V2_PIN),
                                  'sources.runner_config': pin_map[f'{PACK_REL}/{RUNNER_CONFIG[0]}'],
                                  'sources.sig_manifest': manifest_pin, 'membership': membership},
            'tuning': {'execution.signal_vbs_config': pin_map[f'{PACK_REL}/{RUNNER_CONFIG[0]}']['path'],
                       'extends_or_base': config_pin['path']},
            'launcher': {'DemandProfile': pin_map[f'{PACK_REL}/{PROFILE_NAME}'],
                         'network_copy_tool': 'D:\\VISSIM-merge\\tools\\prepare_sdmpc31_network.py'},
        },
        'runtime_validation': FIRST_RUNTIME_CHECK,
        'native_started': False,
    }
    outputs[f'{SCENARIO_REL}/{RECEIPT_NAME}'] = dump_json(receipt)
    return outputs, receipt


def copies(sources):
    """Large byte copies (not regenerated text): the .inpx and the .sig files."""
    out = {V2_PIN['path']: sources.network}
    out.update({f'{NETWORK_DIR_REL}/{name}': data for name, data in sources.sig.items()})
    return out


def expected_folders(outputs):
    return {
        SCENARIO_REL: sorted(PurePosixPath(rel).name for rel in outputs if rel.startswith(SCENARIO_REL + '/')),
        NETWORK_DIR_REL: sorted(PurePosixPath(rel).name for rel in outputs if rel.startswith(NETWORK_DIR_REL + '/')),
    }


def write_outputs(outputs, root=ROOT):
    written, kept = [], []
    for rel, data in sorted(outputs.items()):
        path = repo_path(rel, root)
        if path.is_file() and path.read_bytes() == data:
            kept.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_bytes(data)
        temporary.replace(path)
        written.append(rel)
    for folder, names in expected_folders(outputs).items():
        present = sorted(p.name for p in repo_path(folder, root).iterdir())
        require(present == names, f'{folder} holds files the re-pin did not make: {sorted(set(present) - set(names))}')
    return written, kept


def compare_outputs(outputs, root=ROOT):
    problems = []
    for rel, data in sorted(outputs.items()):
        path = repo_path(rel, root)
        if not path.is_file():
            problems.append(f'missing {rel}')
        elif path.read_bytes() != data:
            problems.append(f'differs {rel}')
    for folder, names in expected_folders(outputs).items():
        base = repo_path(folder, root)
        present = sorted(p.name for p in base.iterdir()) if base.is_dir() else []
        extra = sorted(set(present) - set(names))
        if extra:
            problems.append(f'unexpected in {folder}: {extra}')
    return problems


# --------------------------------------------------------------------------- offline configure() check
DONOR_RUN = Path(r'D:\VISSIM_runs\20260923_sdmpc\sdmpc_lp_9000c')
DEP_ROOT = Path(r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps')
CONFIGURE_SECONDS = (1, 150, 900)


def _donor_state(donor, sec, mode, workdir):
    """A fcb run's saved state, re-pointed at the v2 network for mode 'v2' (the control keeps it as is)."""
    name = donor.name
    state = json.loads((donor / f'decisions_{name}' / f'state_{sec:06d}.json').read_text(encoding='utf-8-sig'))
    manifest = json.loads((donor / f'run_provenance_{name}.json').read_text(encoding='utf-8-sig'))
    if mode == 'v2':
        inpx = repo_path(V2_PIN['path'])
        profile = repo_path(f'{SCENARIO_REL}/{PROFILE_NAME}')
        runner = repo_path(f'{SCENARIO_REL}/{RUNNER_CONFIG[1]}')
        manifest.pop('network_recording', None)          # v2 runs without -NetworkRecordingProof (NEW-2)
        manifest['files']['network'] = {'path': str(inpx), 'exists': True, 'sha256': V2_SHA256}
        manifest['demand_profile'] = str(profile)
        manifest['files']['demand_profile'] = {'path': str(profile), 'exists': True, 'sha256': sha256_bytes(profile.read_bytes())}
        manifest['files']['generated_vbs_config'] = {'path': str(runner), 'exists': True, 'sha256': sha256_bytes(runner.read_bytes())}
        manifest['signal_programs'] = [{'path': str(p), 'exists': True, 'sha256': sha256_bytes(p.read_bytes())}
                                       for p in sorted(inpx.parent.glob('*.sig'))]
        state['network_path'] = str(inpx)
        # The runner's internal-demand aggregate on the v2 volumes (native_internal_input.configure checks it).
        tree = ET.parse(inpx).getroot()
        import csv
        with open(ROOT / 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv', encoding='utf-8-sig') as handle:
            gates = {row['no']: row for row in csv.DictReader(line for line in handle if not line.startswith('#'))}
        inputs = {x.get('no'): x for x in tree.findall('./vehicleInputs/vehicleInput')}
        total = 0.0
        for number, gate in gates.items():
            if gate['status'] == 'internal' and number in inputs:
                rows = [(float(x.get('timeInt').split()[1]) / 1000, float(x.get('volume')))
                        for x in inputs[number].findall('./timeIntVehVols/timeIntervalVehVolume')]
                total += [volume for start, volume in rows if start <= state['sim_sec']][-1] * float(manifest['demand_scale'])
        state['demand']['urban_internal_volume_vph'] = total
    frame_raw = (donor / f'decisions_{name}' / 'lane_observations' / f'frame_{sec:06d}.json').read_bytes()
    frame = json.loads(frame_raw.decode('utf-16') if frame_raw.startswith((b'\xff\xfe', b'\xfe\xff')) else frame_raw.decode('utf-8-sig'))
    from evaluation.controllers.lane_plant_runtime import bind_current_routes
    state = bind_current_routes(state, {'frames': [frame]})   # what the lane plant does before configure
    manifest_path = Path(workdir) / f'manifest_{mode}_{sec}.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    state['run_provenance']['manifest_path'] = str(manifest_path)
    return state, manifest


def configure_one(mode, sec, donor, workdir):
    """runtime_setup.configure_runtime on a donor state; prints one JSON line of the *_enabled flags."""
    import os
    for path in (DEP_ROOT / 'sdmpc', DEP_ROOT / 'sdmpc-numba'):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.append(str(path))
    state, manifest = _donor_state(donor, sec, mode, workdir)
    if mode == 'v2':
        tuning = load_json((ROOT / SCENARIO_REL / CONFIG_BASE_NAME).read_bytes())
        tuning['execution']['native_signal_record'] = False     # plan C9 / NEW-2 (WP-C layers this)
    else:
        tuning = load_json((ROOT / OBS1_REL).read_bytes())
    # The v1 plant pins fcb349d3 and the v2 plant belongs to WP-C: both runs go without a lane plant.
    tuning['freeway'].pop('lane_plant', None)
    tuning['freeway']['lane_initial_spillback_projection'] = False
    for key, value in manifest['env'].items():
        os.environ[key] = value
    os.environ['RW_DECISION_FAIL_FAST'] = '1'
    os.chdir(ROOT)
    from evaluation.controllers import vissim_stackelberg_adapter as ad
    from evaluation.controllers.runtime_setup import configure_runtime
    mapping = json.loads((ROOT / tuning['mapping_json']).read_text(encoding='utf-8'))
    calibration = ad.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    ad.bind_joint_cli_module(tuning)
    ad.install_config_switches(tuning)
    detectors = ad.load_optional_json(str(ROOT / tuning['detector_mapping_json']))
    detectors, _ = ad.filter_midblock_links_from_detector_mapping(detectors, tuning)
    if isinstance(tuning.get('calibration_override'), dict):
        calibration = ad.deep_update(dict(calibration), tuning['calibration_override'])
    traffic_state = ad.repo_imports(ad.DEFAULT_REPO_ROOT)[4]
    cfg = ad.build_config(ad.DEFAULT_REPO_ROOT, float(state['control_interval_sec']), float(state['sim_period_sec']), 'fast-smoke',
                          calibration, tuning, local_observation=bool(ad._link_counts_from_local_observation(state) and detectors),
                          flagship=True)
    ad.install_adapter_calibration_fingerprints(cfg, tuning)
    _, _, metadata = configure_runtime(ad, cfg, tuning, mapping, state, '', detectors, calibration, traffic_state)
    flags = {k: v for k, v in sorted(metadata.items()) if k.endswith('_enabled') and isinstance(v, (int, float, bool))}
    print(json.dumps({'mode': mode, 'sec': sec, 'metadata_keys': len(metadata), 'flags': flags}, sort_keys=True))


def configure_check(donor, seconds):
    """Control (OBS1 + fcb pack) and v2 (base config + v2 pack) through configure(); flags must agree."""
    import subprocess
    import tempfile
    results = []
    with tempfile.TemporaryDirectory(prefix='repin_configure_') as workdir:
        for sec in seconds:
            outcome = {}
            for mode in ('control', 'v2'):
                run = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), 'configure-one', '--mode', mode,
                                      '--sec', str(sec), '--donor', str(donor), '--workdir', workdir],
                                     capture_output=True, text=True, encoding='utf-8', errors='replace')
                lines = [line for line in run.stdout.splitlines() if line.startswith('{"flags"')]
                require(run.returncode == 0 and len(lines) == 1,
                        f'configure {mode} t={sec} failed: {(run.stdout + run.stderr).strip().splitlines()[-3:]}')
                outcome[mode] = json.loads(lines[0])
            require(outcome['control']['flags'] == outcome['v2']['flags'], f't={sec}: enabled flags differ between control and v2')
            require(outcome['control']['metadata_keys'] == outcome['v2']['metadata_keys'], f't={sec}: metadata key counts differ')
            results.append((sec, outcome['v2']['metadata_keys'], sum(1 for v in outcome['v2']['flags'].values() if v)))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('command', choices=('build', 'verify', 'configure-check', 'configure-one'))
    parser.add_argument('--donor', default=str(DONOR_RUN), help='configure-check: a fcb SDMPC run folder with saved states')
    parser.add_argument('--sec', type=int, action='append', help='configure-check: decision times (default 1,150,900)')
    parser.add_argument('--mode', choices=('control', 'v2'))
    parser.add_argument('--workdir')
    parser.add_argument('--network-from', choices=('net', 'copy'), default='net',
                        help='build: read the v2 network from NET (default) or from the pinned N31D copy')
    parser.add_argument('--no-net', action='store_true', help='verify: skip the "copy equals NET" check (NET not read)')
    args = parser.parse_args(argv)
    try:
        if args.command == 'configure-one':
            configure_one(args.mode, args.sec[0], Path(args.donor), args.workdir)
            return 0
        if args.command == 'configure-check':
            results = configure_check(Path(args.donor), args.sec or CONFIGURE_SECONDS)
            print('REPIN_CONFIGURE_OK ' + ' '.join(f't={sec}:keys={keys},enabled={on}' for sec, keys, on in results))
            return 0
        if args.command == 'build':
            sources = Sources(network_from=args.network_from)
            outputs, receipt = build_outputs(sources)
            written, kept = write_outputs(outputs)
            print(f'REPIN_OK files={len(outputs)} written={len(written)} unchanged={len(kept)} '
                  f'network={V2_SHA256[:8]} sig={len(sources.sig)} declarations={len(DECLARATIONS)} '
                  f'prior_mismatch={len(PRIOR_DECLARATIONS)} network_from={args.network_from}')
            return 0
        sources = Sources(network_from='copy')
        outputs, receipt = build_outputs(sources)
        problems = compare_outputs(outputs)
        net_note = 'net=skipped(--no-net)' if args.no_net else 'net=absent(skipped)'
        if not args.no_net and (NET_DIR / NET_INPX).is_file():
            net = Sources(network_from='net')
            require(net.network == sources.network and net.sig == sources.sig, 'N31D network copy differs from NET')
            net_note = 'net=identical'
        require(not problems, 'Outputs differ from a fresh re-pin: ' + '; '.join(problems))
        print(f'REPIN_VERIFY_OK files={len(outputs)} pins={sum(v["resolved"] for v in receipt["pin_audit"].values())} {net_note}')
        return 0
    except RepinError as error:
        print(f'REPIN_ERROR {error}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
