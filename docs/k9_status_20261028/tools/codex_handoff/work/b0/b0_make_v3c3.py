# B0: re-pin the codex controller configuration (a49981ff, tuning c9088262) onto network v3c3 (3de889f0) in the
# b0 scratch tree only.  Read-only sources: the b0 tree's own codex files, and OUR v3c3 runtime files from the
# V-A frozen tree (D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833, never written).
# Every action is recorded in diagnostics/b0_v3c3/B0_REPIN_RECEIPT.json (class, source, target, sha).
# Classes: COPY_OURS (our v3c3 file, same relative path, byte copy), REGEN (codex builder logic re-run on v3c3
# inputs), PIN (pointer/pin swap only, content carried over), DECISION (user decision D-K9-84 Q6 / D-K9-87),
# FIX (our K8/K9 fix ported).  usage: python -B b0_make_v3c3.py
import copy, hashlib, json, os, sys, xml.etree.ElementTree as ET
BS = chr(92)
B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/code'
OURS = 'D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833'
OUT = 'diagnostics/b0_v3c3'
V3C3_NET_REL = 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
V3C3_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
CODEX_NET_SHA = '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
CODEX_TUNING = 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
CODEX_TUNING_SHA = 'c90882628ddc75c0c75c9a82771c96a50614b297839ec32c506859a969dc1df3'
receipt = []


def P(rel):
    return B0 + '/' + rel


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def sha_f(p):
    return sha_b(open(p, 'rb').read())


def read(rel):
    return json.loads(open(P(rel), 'rb').read())


def data(x):
    return (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8')


def data_like(x, raw_template):
    b = data(x)
    return b.replace(b'\n', b'\r\n') if b'\r\n' in raw_template else b


def write(rel, raw, cls, source, why):
    os.makedirs(os.path.dirname(P(rel)), exist_ok=True)
    if os.path.exists(P(rel)) and not rel.startswith(OUT + '/'):
        old = open(P(rel), 'rb').read()
        if old != raw:
            raise SystemExit('refuse to overwrite a codex file with different bytes: ' + rel)
    open(P(rel), 'wb').write(raw)
    receipt.append({'class': cls, 'target': rel, 'sha256': sha_b(raw), 'bytes': len(raw), 'source': source, 'why': why})
    return {'path': rel, 'sha256': sha_b(raw)}


def copy_ours(rel, why):
    raw = open(OURS + '/' + rel, 'rb').read()
    return write(rel, raw, 'COPY_OURS', {'path': OURS + '/' + rel, 'sha256': sha_b(raw)}, why)


# ---------- 1. our v3c3 network folder and scenario pack (same relative paths as our tree; absent in codex tree)
for sub in ('diagnostics/sdmpc_n31_20260924/network', 'diagnostics/sdmpc_n31_20260924/scenario', 'diagnostics/sdmpc_n31_20260924/obs150'):
    for f in sorted(os.listdir(OURS + '/' + sub)):
        if os.path.isfile(OURS + '/' + sub + '/' + f):
            copy_ours(sub + '/' + f, 'v3c3 network/scenario pack (K7 C-4/V-6 repin, our runtime); codex tree has no file here')
assert sha_f(P(V3C3_NET_REL)) == V3C3_SHA
GEO_REL = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c3_nc_20261001/observations/s31_v3c3nc_observations/geometry.json'
geo = copy_ours(GEO_REL, 'v3c3 lane-plant geometry (our plant_n31_v2.json source); R_NET 2.8: same cells/chains as codex 91a584ab, 14 leaves differ (pins + 1099 desired_source_demand)')

# ---------- 2. Omega701 on v3c3: codex builder expand_controlled_intersection_area on our v3c3 Omega635 document
sys.path.insert(0, B0)
sys.path.insert(0, B0 + '/scripts')
sys.dont_write_bytecode = True
from diagnostics.build_control_area_membership import expand_controlled_intersection_area  # noqa: E402
OM635_REL = 'diagnostics/sdmpc_n31_20260924/scenario/control_area_membership_213a5d.json'
mapping = read('evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
terr = read('outputs/urban_player_territory_v2_20260907.json')
tree_v3c3 = ET.parse(P(V3C3_NET_REL)).getroot()
om635 = read(OM635_REL)
assert om635['network']['sha256'] == V3C3_SHA
om701 = expand_controlled_intersection_area(om635, tree_v3c3, mapping, terr)
CODEX_OM701 = 'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'
cx701_raw = open(P(CODEX_OM701), 'rb').read()
cx701 = json.loads(cx701_raw)
for src in cx701['area_revision_sources']:
    assert sha_f(P(src['path'].replace(BS, '/'))) == src['sha256'], src
om701['previous_membership'] = {'path': OM635_REL.replace('/', BS), 'sha256': sha_f(P(OM635_REL))}
om701['area_revision_sources'] = copy.deepcopy(cx701['area_revision_sources'])
assert set(om701['inside_links']) == set(cx701['inside_links']) and set(om701['outside_links']) == set(cx701['outside_links'])
OM701_REL = OUT + '/omega701/membership.json'
om701_pin = write(OM701_REL, data_like(om701, cx701_raw), 'REGEN',
                  {'builder': 'diagnostics/build_control_area_membership.py:expand_controlled_intersection_area',
                   'input': OM635_REL, 'network': V3C3_NET_REL},
                  'codex Omega701 rule on v3c3; inside 701 / outside 535 = codex sets; previous_membership = our v3c3 Omega635')

# ---------- 3. Omega701 route contract on v3c3: prepare_next.py route logic (base contract + v3c3 physical membership)
from evaluation.controllers.control_area_objective import physical_membership_from_ledger  # noqa: E402
from evaluation.controllers.control_area_join import turn_membership  # noqa: E402
from evaluation.controllers.physical_movement_routes import path_membership  # noqa: E402
BASE_RC = 'diagnostics/control_area_route_contract_physical_routes.json'
assert sha_f(P(BASE_RC)) == sha_f(OURS + '/' + BASE_RC)
physical = physical_membership_from_ledger(om701)
routes = read(BASE_RC)
refreshed = 0
for key, row in routes.items():
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
for key, row in routes.items():
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
RC_REL = OUT + '/omega701/route_contract.json'
rc_raw = data(routes)
CODEX_RC = 'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/route_contract.json'
rc_pin = write(RC_REL, rc_raw, 'REGEN', {'builder': 'diagnostics/repin_v3c3_review_20261001/urban_area263/prepare_next.py (route part)',
               'input': BASE_RC, 'membership': OM701_REL},
               'refreshed turns %d; bytes equal to codex approaches_only/route_contract.json: %s' % (refreshed, rc_raw == open(P(CODEX_RC), 'rb').read()))

# ---------- 4. lane plant: reference config with the v3c3 FW_E sign cell (16 -> 18), manifest re-pinned
REF036 = 'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/expanded_joint/eval_036/reference_config.json'
ref_raw = open(P(REF036), 'rb').read()
ref = json.loads(ref_raw)
sc = ref['freeway']['component_vsl_transport']['FW_E']['sign_cells']
assert sc == [0, 3, 5, 8, 14, 16, 26, 28], sc
ref2 = copy.deepcopy(ref)
ref2['freeway']['component_vsl_transport']['FW_E']['sign_cells'] = [0, 3, 5, 8, 14, 18, 26, 28]
REF_REL = OUT + '/lane_plant/reference_config_eval036_sign18.json'
ref_pin = write(REF_REL, data_like(ref2, ref_raw), 'PIN',
                {'path': REF036, 'sha256': sha_b(ref_raw)},
                'eval_036 (64cf-s29 fit, D class kept) with FW_E sign_cells[5] 16 -> 18 = v3c3 DSD 63-66 cell (R_NET 2.4); no other leaf changed')
MAN = 'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/evidence/candidate_manifest.json'
man_raw = open(P(MAN), 'rb').read()
man = json.loads(man_raw)
ours_sig = 'diagnostics/sdmpc_n31_20260924/network/sig_manifest.json'
man['sources']['network'] = {'path': V3C3_NET_REL, 'sha256': V3C3_SHA}
man['sources']['geometry'] = {'path': GEO_REL, 'sha256': geo['sha256']}
man['sources']['reference_config'] = {'path': REF_REL, 'sha256': ref_pin['sha256']}
man['sources']['sig_manifest'] = {'path': ours_sig, 'sha256': sha_f(P(ours_sig))}
man['membership'] = {'path': OM701_REL, 'sha256': om701_pin['sha256']}
OBS_REL = 'diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv'
assert man['observation']['detectors']['sha256'] == sha_f(P(OBS_REL))
man['observation']['detectors'] = {'path': OBS_REL, 'sha256': sha_f(P(OBS_REL))}
man['qualification'] = man['qualification'] + ' | B0 2026-10-26: re-pinned to v3c3 3de889f0 (network, geometry, sig manifest, Omega701, sign cell 18); D-class parameters of 64cf-s29 kept.'
MAN_REL = OUT + '/lane_plant/candidate_manifest.json'
man_pin = write(MAN_REL, data_like(man, man_raw), 'PIN', {'path': MAN, 'sha256': sha_b(man_raw)},
                'lane plant manifest: network/geometry/reference_config/sig_manifest/membership re-pinned, detector table path = our v3c3 copy (same CSV bytes, v3c3 build sidecar); parameters/port_profile/reference_protocol/runner_config/refined_partition/detectors kept')

# ---------- 4b. native choice groups (urban_rm269/native_beta/physical_routes.json) on our v3c3 route evidence
NB = 'diagnostics/repin_v3c3_review_20261001/urban_rm269/native_beta/physical_routes.json'
nb_raw = open(P(NB), 'rb').read()
nb = json.loads(nb_raw)
PACK_ROUTES = 'diagnostics/sdmpc_n31_20260924/scenario/physical_movement_routes_ver2_35eb21.json'
CX_PACK_ROUTES = 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/physical_movement_routes_ver2_35eb21.json'
cxp = read(CX_PACK_ROUTES)
assert {k: v for k, v in nb.items() if k != 'native_choice_groups'} == cxp, 'native_beta is not codex pack + native_choice_groups'
nbv = read(PACK_ROUTES)
assert nbv['network']['sha256'] == V3C3_SHA
nbv['native_choice_groups'] = copy.deepcopy(nb['native_choice_groups'])
NB_REL = OUT + '/native_beta/physical_routes.json'
nb_pin = write(NB_REL, data_like(nbv, nb_raw), 'PIN',
               {'codex': NB, 'ours_pack': PACK_ROUTES},
               'our v3c3 pack route evidence + the 8 codex native_choice_groups unchanged (route ids/stoplines/expected specs); weights are read from the v3c3 network at runtime and every group is validated there (physical_movement_routes.configure_native_choice_groups)')

# ---------- 4c. overlay: codex contract = codex 64cf pack file + codex additions  ->  our v3c3 pack file + the same additions
CXPACK = 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/'
OURPACK = 'diagnostics/sdmpc_n31_20260924/scenario/'


def overlay(codex_rel, pack_name, out_rel, why):
    raw = open(P(codex_rel), 'rb').read()
    cx = json.loads(raw)
    cxp, op = read(CXPACK + pack_name), read(OURPACK + pack_name)
    pack_diff = sorted(k for k in set(cxp) | set(op) if cxp.get(k) != op.get(k))
    assert set(pack_diff) <= {'network', 'scenario_derivation'}, (pack_name, pack_diff)
    assert set(cxp) <= set(cx), (codex_rel, sorted(set(cxp) - set(cx)))
    out = copy.deepcopy(cx)
    for k in ('network', 'scenario_derivation'):
        if k in op:
            out[k] = copy.deepcopy(op[k])
    added = sorted(k for k in cx if k not in cxp)
    changed = sorted(k for k in cxp if cx[k] != cxp[k] and k not in ('network', 'scenario_derivation'))
    return write(out_rel, data_like(out, raw), 'PIN', {'codex': codex_rel, 'codex_pack': CXPACK + pack_name, 'ours_pack': OURPACK + pack_name,
                 'codex_added_keys': added, 'codex_changed_keys': changed},
                 why + '; network/scenario_derivation from our v3c3 pack, codex additions kept, runtime validators check them on v3c3')


AUTH = 'diagnostics/repin_v3c3_review_20261001/goal8_265/head47_right/authority.json'
AUTH_REL = OUT + '/goal8_265/authority.json'
auth_pin = overlay(AUTH, 'physical_phase_authority_local_1df35c.json', AUTH_REL, 'phase authority (goal8 head47_right)')

# ---------- 4d. Omega701 rebind of the v3c3 scenario-pack documents (port of urban_area263/prepare_next.py, lines 48-101)
#   codex: approaches_only/evidence/<name> = prepare_next(selected/scenario/<name>, Omega635 -> Omega701)
#   b0:    b0_v3c3/evidence/<name>        = same algorithm on OUR v3c3 pack (scenario/<name>) with the v3c3 Omega701
def norm(x):
    return x.replace(BS, '/')


EVID = 'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/evidence/'
pack_pointer_paths = ['/urban/capacity/head_free_service', '/urban/movements/dynamic_physical_route_topology',
                      '/urban/movements/native_input_signal_authority', '/urban/shared_approach', '/urban/sc2001_corridor',
                      '/urban/native_internal_inputs', '/urban/physical_ramp_branches', '/urban/known_wout_route_evidence/path',
                      '/observation/physical_support_repair']
tun0 = json.loads(open(P(CODEX_TUNING), 'rb').read())


def getp(d, path):
    for k in path.strip('/').split('/'):
        d = d[k]
    return d


src_names = set()
for ptr in pack_pointer_paths:
    src_names.add(getp(tun0, ptr).split('/')[-1])
for x in getp(tun0, '/urban/route_choice_corridor/evidence_paths'):
    src_names.add(x.split('/')[-1])
documents = {OURPACK + n: read(OURPACK + n) for n in sorted(src_names)}
replacements = {norm(OM635_REL): dict(om701_pin), norm(BASE_RC): dict(rc_pin)}
support_key = OURPACK + 'physical_projection_support_635_proposal_ec2393.json'
support = copy.deepcopy(documents[support_key])
detectors = read('evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json')
nodes = {x.get('no'): x for x in tree_v3c3.findall('./links/link')}
added_support = []
for added in om701['controlled_intersection_expansion']['added_links']:
    link = added['link']; node = nodes[link]; end = node.find('toLinkEndPt')
    if end is None or link in support['link_to_storage']:
        continue
    target = end.get('lane').split()[0]
    origins = detectors.get('link_to_origins', {}).get(target, [])
    if len(origins) != 1:
        continue
    support['link_to_storage'][link] = origins[0]
    support['evidence'][link] = {'to_link': target, 'physical_triplet': [node.find('fromLinkEndPt').get('lane').split()[0], link, target],
        'reason': 'Newly included approach connector has one existing downstream storage; restore its native initial stock channel, no new generation or capacity.'}
    added_support.append(link)
support['controlled_approach_revision'] = {'membership_path': OM701_REL, 'initial_stock_only': True, 'added_unique_connector_support': added_support,
    'mixed_approaches': 'Retain existing physical route/record projection; do not invent equal destination shares.'}
replacements[support_key] = {'path': OUT + '/evidence/' + support_key.split('/')[-1], 'sha256': sha_b(data(support))}
documents[support_key] = support


def rewrite(x):
    if isinstance(x, dict):
        if isinstance(x.get('path'), str) and norm(x['path']) in replacements and 'sha256' in x:
            return {**x, **replacements[norm(x['path'])]}
        return {k: rewrite(v) for k, v in x.items()}
    if isinstance(x, list):
        return [rewrite(v) for v in x]
    if isinstance(x, str) and norm(x) in replacements:
        return replacements[norm(x)]['path']
    return x


for _ in range(len(documents) + 1):
    before = copy.deepcopy(replacements)
    for s_, d_ in documents.items():
        revised = rewrite(d_)
        if revised != d_ or s_ == support_key:
            replacements[s_] = {'path': OUT + '/evidence/' + s_.split('/')[-1], 'sha256': sha_b(data(revised))}
    if before == replacements:
        break
else:
    raise AssertionError('Area evidence dependency graph did not converge')
evidence_map = {}
for s_, d_ in documents.items():
    name = s_.split('/')[-1]
    if s_ in replacements:
        raw_b = data(rewrite(d_))
        assert sha_b(raw_b) == replacements[s_]['sha256']
        cx_e = json.loads(open(P(EVID + name), 'rb').read()) if os.path.exists(P(EVID + name)) else None
        write(replacements[s_]['path'], raw_b, 'REGEN', {'builder': 'urban_area263/prepare_next.py rewrite (lines 48-101)', 'input': s_,
              'codex_counterpart': EVID + name if cx_e is not None else None},
              'our v3c3 pack document rebound to the v3c3 Omega701' + (' (+%d unique connector supports)' % len(added_support) if s_ == support_key else ''))
        evidence_map[name] = replacements[s_]['path']
    else:
        evidence_map[name] = s_

# ---------- 4e. network re-pin of codex route/head contracts (content carried over; runtime validators judge it on v3c3)
CODEX_NET_REL = 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
RV = 'diagnostics/repin_v3c3_review_20261001/'
cmap = {norm(CODEX_NET_REL): {'path': V3C3_NET_REL, 'sha256': V3C3_SHA},
        norm(CODEX_OM701): dict(om701_pin), norm(CODEX_RC): dict(rc_pin), norm(MAN): dict(man_pin),
        norm(NB): dict(nb_pin), norm(AUTH): dict(auth_pin)}
for name, target in evidence_map.items():
    t = {'path': target, 'sha256': sha_f(P(target))}
    cmap[norm(EVID + name)] = t
    cmap[norm(CXPACK + name)] = t
for f in os.listdir(P(CXPACK)):
    if f.endswith('.json') and os.path.exists(P(OURPACK + f)) and norm(CXPACK + f) not in cmap:
        cmap[norm(CXPACK + f)] = {'path': OURPACK + f, 'sha256': sha_f(P(OURPACK + f))}
REPIN = [RV + 'urban_rm269/sc6_queue/authority.json', RV + 'urban_rm269/sc6_queue/head_lane_support.json',
         RV + 'urban66_u7/contract.json', RV + 'urban_rm269/sc1_supply/contract.json',
         RV + 'unrouted10646/route_contract.json',
         'diagnostics/sdmpc_n31_20260924/integration_20260926/expanded036_9000_20260930/loss_onset2250/city_path/head_lane_support.json',
         'diagnostics/sdmpc_n31_20260924/integration_20260926/expanded036_9000_20260930/loss_onset2250/source_sc101/head_lane_support.json',
         RV + 'goal8_265/head47/physical_support.json',
         RV + 'urban_rm269/sc6_queue/head_resources.json']
repin_counts = {}


def repin_doc(x, cnt):
    if isinstance(x, dict):
        if isinstance(x.get('path'), str) and norm(x['path']) in cmap and 'sha256' in x:
            cnt['pin'] += 1
            return {**x, **cmap[norm(x['path'])]}
        return {k: repin_doc(v, cnt) for k, v in x.items()}
    if isinstance(x, list):
        return [repin_doc(v, cnt) for v in x]
    if isinstance(x, str):
        if norm(x) in cmap:
            cnt['path'] += 1
            return cmap[norm(x)]['path']
        if x == CODEX_NET_SHA:
            cnt['sha'] += 1
            return V3C3_SHA
    return x


for _ in range(len(REPIN) + 2):
    before = copy.deepcopy(cmap)
    for rel in REPIN:
        raw = open(P(rel), 'rb').read()
        cnt = {'pin': 0, 'path': 0, 'sha': 0}
        out = repin_doc(json.loads(raw), cnt)
        repin_counts[rel] = cnt
        cmap[norm(rel)] = {'path': OUT + '/' + rel[len('diagnostics/'):], 'sha256': sha_b(data_like(out, raw))}
    if before == cmap:
        break
else:
    raise AssertionError('contract re-pin did not converge')
for rel in REPIN:
    raw = open(P(rel), 'rb').read()
    cnt = {'pin': 0, 'path': 0, 'sha': 0}
    out = repin_doc(json.loads(raw), cnt)
    b = data_like(out, raw)
    assert sha_b(b) == cmap[norm(rel)]['sha256']
    write(cmap[norm(rel)]['path'], b, 'PIN', {'path': rel, 'sha256': sha_b(raw), 'rewritten': cnt},
          'codex contract with its network pin and pinned references re-pointed to v3c3 / b0 copies; contents (64cf derivation) unchanged')

# ---------- 5. tuning
tun_raw = open(P(CODEX_TUNING), 'rb').read()
assert sha_b(tun_raw) == CODEX_TUNING_SHA
tun = json.loads(tun_raw)
edits = []


def setp(path, value, cls, why):
    keys = path.strip('/').split('/')
    cur = tun
    for k in keys[:-1]:
        cur = cur[k]
    old = cur.get(keys[-1], '<absent>')
    if value == '<delete>':
        cur.pop(keys[-1])
    else:
        cur[keys[-1]] = value
    edits.append({'path': path, 'old': old, 'new': value, 'class': cls, 'why': why})


setp('/freeway/lane_plant', MAN_REL, 'PIN', 'v3c3 lane plant manifest')
setp('/control_area_objective/membership_path', OM701_REL, 'REGEN', 'Omega701 rebuilt on v3c3')
setp('/control_area_objective/route_contract_path', RC_REL, 'REGEN', 'Omega701 route contract rebuilt on v3c3')
setp('/observation/physical_branch_projection/source/network/path', V3C3_NET_REL, 'PIN', 'v3c3 network')
setp('/observation/physical_branch_projection/source/network/sha256', V3C3_SHA, 'PIN', 'v3c3 network')
setp('/urban/movements/physical_route_topology', NB_REL, 'PIN', 'native choice groups on v3c3 route evidence')
setp('/urban/movements/physical_phase_authority', AUTH_REL, 'PIN', 'phase authority overlay on v3c3 pack')
for ptr in pack_pointer_paths:
    name = getp(tun0, ptr).split('/')[-1]
    setp(ptr, evidence_map[name], 'REGEN' if evidence_map[name].startswith(OUT) else 'PIN', 'v3c3 pack document' + (' rebound to Omega701' if evidence_map[name].startswith(OUT) else ''))
    if ptr.endswith('/path'):
        setp(ptr[:-5] + '/sha256', sha_f(P(evidence_map[name])), 'PIN', 'pin of the v3c3 pack document')
setp('/urban/route_choice_corridor/evidence_paths', [evidence_map[x.split('/')[-1]] for x in getp(tun0, '/urban/route_choice_corridor/evidence_paths')], 'REGEN', 'v3c3 pack route-choice corridors rebound to Omega701')
for ptr, rel in (('/urban/capacity/head_resource_contract', RV + 'urban_rm269/sc6_queue/head_resources.json'),
                 ('/urban/capacity/regular_alias_pool', RV + 'urban_rm269/sc1_supply/contract.json'),
                 ('/urban/queue/head_lane_contract', RV + 'urban_rm269/sc6_queue/head_lane_support.json'),
                 ('/urban/arrival/kinematic_contract', RV + 'urban66_u7/contract.json'),
                 ('/freeway/offramp_route_inventory', RV + 'unrouted10646/route_contract.json')):
    assert norm(getp(tun0, ptr)) == rel, (ptr, getp(tun0, ptr))
    setp(ptr, cmap[norm(rel)]['path'], 'PIN', 'codex contract re-pinned to v3c3 (content carried over)')
# D-K9-84 Q6 decisions
off_cfg = read('diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/off_config.json')
assert off_cfg['adapter']['sdmpc_fixed_vsl'] == {'start_sec': 0, 'base_kmh': 110, 'zone_kmh': {}}
setp('/adapter/sdmpc_fixed_vsl', copy.deepcopy(off_cfg['adapter']['sdmpc_fixed_vsl']), 'DECISION', 'Q6b VSL fixed 110 = the codex off_config.json object (start 0, base 110, no zone)')
setp('/urban/calibrated_aggregate', '<delete>', 'DECISION', 'Q6c calibrated_aggregate OFF (64cf-s29 in-sample calibration not used)')
# D-K9-87 / H8: physical RM_C keys for the local ramp-arrival forecast (V-A tuning c8e3ee2c values) + strict keys
ours_tun = json.loads(open(OURS + '/diagnostics/sdmpc_n31_20260924/config_n31_v2.json', 'rb').read())
ofc = ours_tun['calibration_override']['prediction']['local_ramp_arrival_forecast']
setp('/calibration_override/prediction/local_ramp_arrival_forecast/queue_drain_horizon_sec_by_ramp',
     copy.deepcopy(ofc['queue_drain_horizon_sec_by_ramp']), 'FIX', 'H8 RM_C keys (our V-A tuning)')
setp('/calibration_override/prediction/local_ramp_arrival_forecast/max_vph_by_ramp',
     copy.deepcopy(ofc['max_vph_by_ramp']), 'FIX', 'H8 RM_C keys (our V-A tuning)')
setp('/calibration_override/prediction/local_ramp_arrival_forecast/strict_ramp_keys', True, 'FIX', 'H8 strict keys (our V-A tuning)')
setp('/runtime/decision_error_policy', 'hold_previous_on_exception', 'FIX', 'our K8-8 exception-only hold (D-K9-13, D-K9-84 Q6); codex value hold_previous')
setp('/runtime/decision_timeout_sec', '<delete>', 'FIX', 'no decision deadline with exception-only hold (StallSec bounds a decision); codex value 1800')
tun['name'] = tun['name'] + '_b0v3c3'
TUN_REL = OUT + '/config_b0_v3c3.json'
tun_pin = write(TUN_REL, data_like(tun, tun_raw), 'PIN', {'path': CODEX_TUNING, 'sha256': CODEX_TUNING_SHA}, 'B0 tuning; leaf edits listed in tuning_edits')
# counterfactual tuning for the ramp-arrival trace (H8): identical to the B0 tuning except the local ramp-arrival
# forecast object, which is the codex original (group keys R_D_W..., no strict_ramp_keys -> 120 s / 900 veh/h fallback)
tun_gk = copy.deepcopy(tun)
tun_gk['calibration_override']['prediction']['local_ramp_arrival_forecast'] = copy.deepcopy(
    json.loads(tun_raw)['calibration_override']['prediction']['local_ramp_arrival_forecast'])
# name kept identical so that the only difference is the forecast object
TUNGK_REL = OUT + '/config_b0_v3c3_groupkeys.json'
tungk_pin = write(TUNGK_REL, data_like(tun_gk, tun_raw), 'PIN', {'path': TUN_REL, 'sha256': tun_pin['sha256']},
                  'replay-only counterfactual: codex group-key ramp-arrival forecast restored; not a B arm')
rec = {'schema': 'b0-v3c3-repin/v1', 'tuning_groupkeys': tungk_pin, 'b0_code': B0, 'ours_source': OURS, 'network': {'path': V3C3_NET_REL, 'sha256': V3C3_SHA},
       'codex_network_sha256': CODEX_NET_SHA, 'tuning': tun_pin, 'tuning_edits': edits, 'files': receipt}
open(P(OUT + '/B0_REPIN_RECEIPT.json'), 'wb').write(data(rec))
print('files', len(receipt), 'tuning', tun_pin['sha256'], 'edits', len(edits))
print('evidence', json.dumps(evidence_map), 'added_support', len(added_support))
print('repin', json.dumps(repin_counts))
print('route_contract_equal_codex', rc_raw == open(P(CODEX_RC), 'rb').read(), 'refreshed', refreshed)
