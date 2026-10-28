"""P0-1 child (amendment C1 section 4, P0-1): runs the codex code COPIES in TC1/cx_copy (never CX itself).

    python -B c1_p0_cx.py <cx_copy root> <out dir>
(a) cx_copy diagnostics/build_control_area_membership.py expand_controlled_intersection_area on the OU Omega635
    (git show c20aff1d, 30abb1db...) with the v3c3 network (git show c20aff1d), the cx_copy mapping / territory (B0's
    inputs): JSON without previous_membership / area_revision_sources == B0F membership.json without them; B0F's two
    keys follow the B0 rule (previous_membership = {Omega635 path with backslashes, 30abb1db...}); bytes with the two
    B0F keys in B0's data_like (CRLF as the codex file) == 9bb740b3...
(b) PN:21-56 route part (ported; physical_membership_from_ledger / turn_membership / path_membership from cx_copy) on the
    base contract (git show c20aff1d, 11d0db79...) with the reproduced Omega701: bytes == 08fec9c7..., turns refreshed.
Writes <out>/membership_repro.json, route_contract_repro.json, cx_result.json (flags, counts, sha only)."""
import copy
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CXC = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(CXC))
sys.dont_write_bytecode = True
GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
REV = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'
B0F = Path(r'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410/diagnostics/b0_v3c3')
BS = chr(92)
OM635_REL = 'diagnostics/sdmpc_n31_20260924/scenario/control_area_membership_213a5d.json'
NET_REL = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
BASE_RC = 'diagnostics/control_area_route_contract_physical_routes.json'


def show(rel):
    return subprocess.run(['git', '-C', GWT8, 'show', REV + ':' + rel], capture_output=True, check=True).stdout


def sha(b):
    return hashlib.sha256(b).hexdigest()


def data(x):
    return (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8')


def data_like(x, raw_template):
    b = data(x)
    return b.replace(b'\n', b'\r\n') if b'\r\n' in raw_template else b


res = {}
from diagnostics.build_control_area_membership import expand_controlled_intersection_area  # noqa: E402

om635_raw = show(OM635_REL)
om635 = json.loads(om635_raw)
net_raw = show(NET_REL)
res['network_sha256'] = sha(net_raw)
tree = ET.fromstring(net_raw)
mapping = json.loads((CXC / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_bytes())
terr = json.loads((CXC / 'outputs/urban_player_territory_v2_20260907.json').read_bytes())
om701 = expand_controlled_intersection_area(om635, tree, mapping, terr)
b0_raw = (B0F / 'omega701' / 'membership.json').read_bytes()
b0 = json.loads(b0_raw)
strip = lambda d: {k: v for k, v in d.items() if k not in ('previous_membership', 'area_revision_sources')}
res['membership_equal_without_two_keys'] = strip(om701) == strip(b0)
res['previous_membership_rule'] = b0.get('previous_membership') == {'path': OM635_REL.replace('/', BS), 'sha256': sha(om635_raw)}
cx701 = json.loads((CXC / 'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json').read_bytes())
res['area_revision_sources_equal_b0f'] = b0.get('area_revision_sources') == cx701.get('area_revision_sources')   # B0 rule
om701_full = copy.deepcopy(om701)
om701_full['previous_membership'] = copy.deepcopy(b0['previous_membership'])
om701_full['area_revision_sources'] = copy.deepcopy(b0['area_revision_sources'])
raw = data_like(om701_full, b0_raw)
(OUT / 'membership_repro.json').write_bytes(raw)
res['membership_bytes_sha256'] = sha(raw)
res['inside_outside'] = [len(om701['inside_links']), len(om701['outside_links'])]
res['omega635_sha256'] = sha(om635_raw)

from evaluation.controllers.control_area_objective import physical_membership_from_ledger  # noqa: E402
from evaluation.controllers.control_area_join import turn_membership  # noqa: E402
from evaluation.controllers.physical_movement_routes import path_membership  # noqa: E402
base_raw = show(BASE_RC)
res['base_contract_sha256'] = sha(base_raw)
physical = physical_membership_from_ledger(om701_full)
routes = json.loads(base_raw)
refreshed = 0
for key, row in routes.items():                                                       # PN:27-47
    if not key.startswith('movement:'):
        continue
    turns = row.get('physical_turns', [])
    for turn in turns:
        prior = copy.deepcopy(turn)
        turn.update(path_membership(turn['path'], physical) if 'path' in turn else turn_membership(turn, physical))
        refreshed += int(turn != prior)
    patterns = {(t['source_inside'], t['target_inside'], t['outward_crossings_per_vehicle'], t['inward_crossings_per_vehicle']) for t in turns}
    if len(patterns) == 1:
        si, ti, ex, en = patterns.pop()
        row.update(source_inside=si, target_inside=ti, inside_to_inside=float(ti), outside_to_inside=float(ti),
                   outward_crossings_per_vehicle=ex, inward_crossings_per_vehicle=en,
                   status='unique' if len(turns) == 1 else 'same_transition', unresolved_reason=None)
    elif patterns:
        row.update(source_inside=None, target_inside=None, inside_to_inside=None, outside_to_inside=None,
                   outward_crossings_per_vehicle=None, inward_crossings_per_vehicle=None,
                   status='mixed_transition', unresolved_reason='Expanded area still requires separate physical branch weights.')
    sides = {t['source_inside'] for t in turns}
    if len(sides) == 1:
        side = sides.pop()
        arrival = routes['arrival:' + key.split(':', 1)[1]]
        arrival.update(target_inside=side, inside_to_inside=float(side), outside_to_inside=float(side))
for key, row in routes.items():                                                       # PN:48-55
    if not key.startswith('input:'):
        continue
    sources = row.get('physical_sources', [])
    for s in sources:
        s['inside'] = physical[str(s['link'])]
    sides = {s['inside'] for s in sources}
    if len(sides) == 1:
        side = sides.pop()
        row.update(status='unique', target_inside=side, event_kind='generation' if side else 'outside_generation', unresolved_reason=None)
    elif sides:
        row.update(status='mixed_transition', target_inside=None, event_kind='unresolved_generation')
rc = data(routes)                                                                     # PN:56
(OUT / 'route_contract_repro.json').write_bytes(rc)
res['route_contract_sha256'] = sha(rc)
res['refreshed_turns'] = refreshed
res['route_contract_equals_b0f'] = rc == (B0F / 'omega701' / 'route_contract.json').read_bytes()
(OUT / 'cx_result.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
print('C1_P0_CX ok', json.dumps({k: v for k, v in res.items() if k not in ('network_sha256',)}))
