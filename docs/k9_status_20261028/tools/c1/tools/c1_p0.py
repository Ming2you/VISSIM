"""C1 P0 (K8 amendment C1 a98580dd..., section 4: P0-1 ... P0-13) on the P0 tree TC1/trees/p0_<patch sha8>.

    python -B c1_p0.py <step> [...]      steps: p0_1 p0_2 p0_3 p0_4 p0_5 p0_6 p0_7 p0_8 p0_9 p0_10 p0_11 p0_13 values
                                         cfgrun <tag> <run> <T> <arm> [--tree NAME] [--controller C]  (one configure)
Outputs TC1/out/p0/<step>/ (result.json + inputs).  Heavy steps (p0_3 / p0_6 configure runs, p0_7 scan, p0_8 / p0_9
B decision reads) take the shared LOCK themselves and run one at a time.  Codex code (P0-1) runs from TC1/cx_copy
(sha-checked copies), python -B, env_hsw; PN:57-108 (P0-2) is ported here (B0 b0_make_v3c3.py 4d form, documents =
the closed list).  CX / FRZ_B1 are never written (CX git status and FRZ_B1 file count / newest mtime recorded).
BLIND: no objective / prediction value is printed or written; v3c3-s47 is never opened (P0-7 lists names only).
Stop rules (S-C1-2): a false P0-1/P0-2/P0-3/P0-5/P0-11/P0-13 condition writes verdict STOP in its result.json."""
import copy
import gzip
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1common as C  # noqa: E402

OUT = C.TC1 / 'out' / 'p0'
NUMBA = OUT / 'numba_cache'
MAN = json.loads((C.TOOLS / 'c1_probe_patch_manifest.json').read_text(encoding='utf-8'))
PATCH_SHA8 = MAN['patch_sha256'][:8]
P0TREE = C.TC1 / 'trees' / ('p0_' + PATCH_SHA8)
STATES = json.loads((C.DECL / 'c1_states.json').read_text(encoding='utf-8'))
ARMS = json.loads((C.TOOLS / 'arms' / 'ARMS.json').read_text(encoding='utf-8'))['arms']
P0_ARMS = ('off', 'omega', 'm', 'h', 'c1')
TOKEN_ARMS = ('off', 'omega', 'h', 'm', 'm_cap1', 'm_noheld', 'c1', 'c1m', 'azg', 'srg', 'hr', 'mlc')
TOKEN_SAME = ('off', 'omega', 'h', 'azg', 'srg', 'hr', 'mlc', 'c1m')
TOKEN_CHANGED = ('m', 'm_cap1', 'm_noheld', 'c1')
LOG = C.make_logger(OUT / 'logs' / 'c1_p0.log')
BS = chr(92)
OM701_REL = 'diagnostics/b0_v3c3/omega701/membership.json'
RC_REL = 'diagnostics/b0_v3c3/omega701/route_contract.json'
MAN_TARGET = 'diagnostics/sdmpc_n31_20260924/c1/evidence/plant_n31_v2_omega701.json'
PACK_POINTERS = ('/urban/movements/native_input_signal_authority', '/urban/native_internal_inputs',
                 '/observation/physical_support_repair', '/urban/sc2001_corridor',
                 '/urban/route_choice_corridor/evidence_paths/0', '/urban/route_choice_corridor/evidence_paths/1',
                 '/urban/route_choice_corridor/evidence_paths/2', '/urban/route_choice_corridor/evidence_paths/3')
PACK_SHA = {'native_input_1083_signal_authority_ver2_022a16.json': '8f65b25c7af1e2f4f83e07890bab90b07d0fe0af283180e3d51052757670a3a1',
            'native_internal_inputs_c92673.json': 'a23a13632f20cdb81824a406e0c3a83fa9b88cd3eb7f8d32fb33ce318fd820d8',
            'physical_projection_support_635_proposal_ec2393.json': '7d092b3db6e4107b47ecf751c60196e11a32120dc722d9221c1fb888d447faec',
            'sc2001_corridor_nc13_2d0c62.json': 'cc5e6863ca8f9ade6f47689db0ca83744b2ce1186f0d56a92ca8f55074a00c62',
            'route_choice_corridor_sc1004_calibrated_9e6354.json': '7067a6610b052830885bc56726d944f05fac48daf43dda8ba06fff4750f63716',
            'route_choice_corridor_1128_ver2_0fd58c.json': 'd92f90aacb24f44849826ab0c9ed41dd5574a596d27c6d6637ea709e52b2f4b1',
            'route_choice_corridor_1099_sc15_calibrated_e02d01.json': '8e40f046558d921868bc2f5db435ba131eece073e41052107496f6a541620306',
            'route_choice_corridor_1100_sc15_calibrated_05ed35.json': '59fa5c59d58c97c7170de273484ebfb002b158b9f6a2325b23accc3a260c850e'}
MANIFEST_SHA_NEW = '93f171437fbc55420e234a98efb262e83010566902a691a0cc438f17d247a4f7'
AREA_SHA_OLD = '4863f5ee5bae6dd47bd00d2adf4a437b9c5eed94f17d3af72fb647fdb31ade9d'
SUPPORT_NAME = 'physical_projection_support_635_proposal_ec2393.json'
EXPECTED_DIFFS = {
    'native_internal_inputs_c92673.json': ['/canonical_contract/path', '/canonical_contract/sha256', '/membership/path',
                                           '/membership/sha256'],
    'native_input_1083_signal_authority_ver2_022a16.json': ['/membership/path', '/membership/sha256'],
    'sc2001_corridor_nc13_2d0c62.json': ['/membership_path'],
    'route_choice_corridor_sc1004_calibrated_9e6354.json': ['/membership_path'],
    'route_choice_corridor_1128_ver2_0fd58c.json': ['/membership_path'],
    'route_choice_corridor_1099_sc15_calibrated_e02d01.json': ['/membership_path'],
    'route_choice_corridor_1100_sc15_calibrated_05ed35.json': ['/membership_path'],
    'MANIFEST': ['/membership/path', '/membership/sha256']}
SUPPORT_VALUE_PATHS = ['/evidence/10379/source_lineage/canonical_contract/path',
                       '/evidence/10379/source_lineage/canonical_contract/sha256',
                       '/evidence/336/downstream_path/canonical_contract/path',
                       '/evidence/336/downstream_path/canonical_contract/sha256']
PIN_EXCLUDED = {('omega701/membership.json', '/previous_membership')} | {
    ('omega701/membership.json', '/area_revision_sources/%d' % i) for i in range(4)}
SEVEN_GATES = ['input:gate:in_SC1004_S', 'input:gate:in_SC107_S', 'input:gate:in_SC108_S', 'input:gate:in_SC109_E',
               'input:gate:in_SC12_E', 'input:gate:in_SC16_E', 'input:gate:in_SC1_S']
E_M_ALLOWED = ('physical_ramp_branches/allow_zero_green', 'physical_ramp_branches/storage_release_guard', 'c1_port',
               'sdmpc_options/meter_neighbor_audit')
E_H_ALLOWED = tuple('physical_ramp_branches/ramps/%s/service_by_green_veh_h' % m for m in C.FWE) + ('c1_port',)


def ptr_get(doc, ptr):
    x = doc
    for part in ptr.strip('/').split('/'):
        x = x[int(part)] if isinstance(x, list) else x[part]
    return x


def result_write(step, res):
    path = OUT / step / 'result.json'
    C.write_json(path, res)
    LOG('RESULT %s verdict=%s sha256=%s' % (step, res.get('verdict'), C.sha256_file(path)))
    return path


def cx_status():
    r = subprocess.run(['git', '-C', str(C.CX), 'status', '--porcelain'], capture_output=True, text=True)
    n, newest = 0, 0.0
    for base, _dirs, files in os.walk(C.lp(C.FRZ_B1)):
        for f in files:
            n += 1
            try:
                newest = max(newest, os.stat(os.path.join(base, f)).st_mtime)
            except OSError:
                pass
    return {'cx_status_lines': len([l for l in r.stdout.splitlines() if l.strip()]), 'frz_b1_files': n,
            'frz_b1_newest_mtime': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(newest))}


# ================================================================================================ P0-1
CX_COPY = C.TC1 / 'cx_copy'
CX_FILES = ('diagnostics/build_control_area_membership.py',
            'diagnostics/repin_v3c3_review_20261001/urban_area263/prepare_next.py',
            'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json',
            'scripts/protected_ttt_from_fzp_20260828.py',
            'outputs/urban_player_territory_v2_20260907.json')


def p0_1():
    before = cx_status()
    if not CX_COPY.exists():
        CX_COPY.mkdir(parents=True)
        files = list(CX_FILES)
        for base, _dirs, fs in os.walk(C.CX / 'evaluation'):
            for f in fs:
                if '__pycache__' in base:
                    continue
                files.append(os.path.relpath(os.path.join(base, f), C.CX).replace(BS, '/'))
        copied = {}
        for rel in files:
            src, dst = C.CX / rel, CX_COPY / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(C.lp(src), C.lp(dst))
            a, b = C.sha256_file(src), C.sha256_file(dst)
            if a != b:
                raise SystemExit('cx copy differs: ' + rel)
            copied[rel] = a
        C.write_json(OUT / 'p0_1' / 'cx_copy_manifest.json', {'files': len(copied), 'sha256': copied})
        LOG('CX_COPY files=%d builder=%s pn=%s' % (len(copied), copied[CX_FILES[0]][:8], copied[CX_FILES[1]][:8]))
    env = C.env_hsw(C.child_env(NUMBA))
    rc, sec, text = C.run_capture([C.PY, '-B', str(C.TOOLS / 'c1_p0_cx.py'), str(CX_COPY), str(OUT / 'p0_1')],
                                  OUT / 'p0_1' / 'child.txt', env, cwd=CX_COPY)
    child = C.read_json(OUT / 'p0_1' / 'cx_result.json', {}) or {}
    after = cx_status()
    man = C.read_json(OUT / 'p0_1' / 'cx_copy_manifest.json', {}) or {}
    checks = {
        'child_exit_0': rc == 0,
        'builder_sha_567bca5f': (man.get('sha256') or {}).get(CX_FILES[0]) == '567bca5f4e4f955a5a27e762f4f242769dfa433bcffbc4b454aa75320f90dae5',
        'pn_sha_525897ad': (man.get('sha256') or {}).get(CX_FILES[1]) == '525897ada99ec2859bb83246c2dc95fb06e16a0d08000032ddc8bf444b8d3625',
        'membership_equal_without_two_keys': child.get('membership_equal_without_two_keys') is True,
        'previous_membership_rule': child.get('previous_membership_rule') is True,
        'area_revision_sources_equal_b0f': child.get('area_revision_sources_equal_b0f') is True,
        'membership_bytes_9bb740b3': child.get('membership_bytes_sha256') == '9bb740b321d28162c0e849b56e0e618adf4ec800caa60476c96f3fc469318d51',
        'inside_701_outside_535': child.get('inside_outside') == [701, 535],
        'route_contract_bytes_08fec9c7': child.get('route_contract_sha256') == '08fec9c71b1c612ad3f95555173e372fd2f9428ef58d7010246a00bf0b77063a',
        'refreshed_turns_57': child.get('refreshed_turns') == 57,
        'base_contract_11d0db79': child.get('base_contract_sha256') == '11d0db7977961a9a0dbca220e12d6db6f46085d2ec051b929f788595658224a9',
        'cx_written_0': before['cx_status_lines'] == 0 and after['cx_status_lines'] == 0,
        'frz_b1_unchanged': (before['frz_b1_files'], before['frz_b1_newest_mtime']) == (after['frz_b1_files'], after['frz_b1_newest_mtime'])}
    res = {'step': 'P0-1', 'checks': checks, 'child': child, 'cx_before': before, 'cx_after': after,
           'child_sec': round(sec, 1), 'verdict': 'PASS' if all(checks.values()) else 'STOP'}
    result_write('p0_1', res)


# ================================================================================================ P0-2
def pins(v, p=''):
    if isinstance(v, dict):
        if isinstance(v.get('path'), str) and 'sha256' in v:
            yield p, v['path'], v['sha256']
        for k, x in v.items():
            yield from pins(x, p + '/' + k)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from pins(x, p + '/%d' % i)


def membership_paths(v, p=''):
    if isinstance(v, dict):
        for k, x in v.items():
            if k == 'membership_path' and isinstance(x, str):
                yield p + '/' + k, x
            yield from membership_paths(x, p + '/' + k)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from membership_paths(x, p + '/%d' % i)


def p0_2():
    def norm(s):
        return s.replace(BS, '/')

    ouc = json.loads(C.git_show(C.OUC_REL))
    om635 = ouc['control_area_objective']['membership_path']
    base_rc = ouc['control_area_objective']['route_contract_path']
    om701_b = (C.B0F / 'omega701' / 'membership.json').read_bytes()
    rc_b = (C.B0F / 'omega701' / 'route_contract.json').read_bytes()
    replacements = {norm(om635): {'path': OM701_REL, 'sha256': C.sha256_bytes(om701_b)},
                    norm(base_rc): {'path': RC_REL, 'sha256': C.sha256_bytes(rc_b)}}
    manifest_key = norm(ouc['freeway']['lane_plant'])
    documents = {}
    for ptr in PACK_POINTERS + ('/freeway/lane_plant',):
        s = norm(ptr_get(ouc, ptr))
        documents[s] = json.loads(C.git_show(s))
    originals = copy.deepcopy(documents)
    support_key = norm(ouc['observation']['physical_support_repair'])
    support = copy.deepcopy(documents[support_key])
    detectors = json.loads(C.git_show(ouc['detector_mapping_json']))
    area = json.loads(om701_b)
    tree = ET.fromstring(C.git_show(area['network']['path']))
    nodes = {x.get('no'): x for x in tree.findall('./links/link')}
    added_support = []
    for added in area['controlled_intersection_expansion']['added_links']:          # PN:71-80
        link = added['link']
        node = nodes[link]
        end = node.find('toLinkEndPt')
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
    support['controlled_approach_revision'] = {'membership_path': OM701_REL, 'initial_stock_only': True,
                                               'added_unique_connector_support': added_support,
                                               'mixed_approaches': 'Retain existing physical route/record projection; do not invent equal destination shares.'}

    def target_of(s):
        return MAN_TARGET if s == manifest_key else 'diagnostics/b0_v3c3/evidence/' + Path(s).name

    replacements[support_key] = {'path': target_of(support_key), 'sha256': C.sha256_bytes(C.data(support))}
    documents[support_key] = support

    def rewrite(x):                                                                  # PN:88-95
        if isinstance(x, dict):
            if isinstance(x.get('path'), str) and norm(x['path']) in replacements and 'sha256' in x:
                return {**x, **replacements[norm(x['path'])]}
            return {k: rewrite(v) for k, v in x.items()}
        if isinstance(x, list):
            return [rewrite(v) for v in x]
        if isinstance(x, str) and norm(x) in replacements:
            return replacements[norm(x)]['path']
        return x

    for _ in range(len(documents) + 1):                                              # PN:96-104
        before = copy.deepcopy(replacements)
        for s, d in documents.items():
            revised = rewrite(d)
            if revised != d or s == support_key:
                replacements[s] = {'path': target_of(s), 'sha256': C.sha256_bytes(C.data(revised))}
        if before == replacements:
            break
    else:
        raise SystemExit('Area evidence dependency graph did not converge')
    written, results = {}, {}
    for s, d in documents.items():                                                   # PN:105-108 (to OUT only)
        if s not in replacements:
            continue
        raw = C.data(rewrite(d))
        if C.sha256_bytes(raw) != replacements[s]['sha256']:
            raise SystemExit('rewrite sha mismatch ' + s)
        name = 'MANIFEST' if s == manifest_key else Path(s).name
        dst = OUT / 'p0_2' / 'written' / Path(replacements[s]['path']).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)
        written[name] = C.sha256_bytes(raw)
        results[name] = json.loads(raw)
    exp = dict(PACK_SHA, MANIFEST=MANIFEST_SHA_NEW)
    bytes_ok = {n: written.get(n) == h for n, h in exp.items()}
    diffs = {}
    for s, d in originals.items():
        name = 'MANIFEST' if s == manifest_key else Path(s).name
        if name in results:
            diffs[name] = C.deep_diff(d, results[name])
    sup_old, sup_new = originals[support_key], results.get(SUPPORT_NAME, {})
    sd = diffs.get(SUPPORT_NAME, [])
    groups = {}
    for k in sd:
        groups[k.split('/')[1]] = groups.get(k.split('/')[1], 0) + 1
    new_lts = set(sup_new.get('link_to_storage', {})) - set(sup_old['link_to_storage'])
    new_ev = set(sup_new.get('evidence', {})) - set(sup_old['evidence'])
    aus = set((sup_new.get('controlled_approach_revision') or {}).get('added_unique_connector_support', []))
    added_links = {str(x['link']) for x in area['controlled_intersection_expansion']['added_links']}
    support_expected = sorted(['/link_to_storage/' + k for k in new_lts] + ['/evidence/' + k for k in new_ev]
                              + SUPPORT_VALUE_PATHS + ['/controlled_approach_revision'])
    diff_ok = {n: sorted(diffs.get(n, [])) == sorted(v) for n, v in EXPECTED_DIFFS.items()}
    diff_ok[SUPPORT_NAME] = sorted(sd) == support_expected and len(sd) == 63
    # path pins: B0F 10 files + the declared Omega701 manifest, resolved in the P0 tree (B0 layout + c20aff1d files)
    files = [('omega701/membership.json', C.B0F / 'omega701' / 'membership.json'),
             ('omega701/route_contract.json', C.B0F / 'omega701' / 'route_contract.json')]
    files += [('evidence/' + n, C.B0F / 'evidence' / n) for n in PACK_SHA]
    files += [('MANIFEST', C.DECL / 'plant_n31_v2_omega701.json')]
    total, judged_bad, excluded, backslash, mp = 0, [], [], 0, []
    for label, f in files:
        d = json.loads(Path(f).read_text(encoding='utf-8-sig'))
        for p, path, h in pins(d):
            total += 1
            rel = path.replace(BS, '/')
            tgt = P0TREE / rel
            row = {'file': label, 'pointer': p, 'backslash': BS in path, 'exists': tgt.is_file(),
                   'sha_ok': tgt.is_file() and C.sha256_file(tgt) == h,
                   'relative': not (rel.startswith('/') or ':' in rel or '..' in rel.split('/'))}
            if (label, p) in PIN_EXCLUDED:
                excluded.append(row)
                continue
            backslash += int(row['backslash'])
            if not (row['sha_ok'] and row['relative']):
                judged_bad.append(row)
        for p, path in membership_paths(d):
            mp.append({'file': label, 'pointer': p, 'value': path, 'exists': (P0TREE / path).is_file()})
    grep1 = subprocess.run(['git', '-C', str(C.GWT8), 'grep', '-n', 'area_membership_sha256', C.REV, '--', 'evaluation'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip().splitlines()
    grep2 = subprocess.run(['git', '-C', str(C.GWT8), 'grep', '-n', 'full_area_coverage_audit', C.REV, '--', 'evaluation'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip().splitlines()
    readers = sorted({':'.join(l.split(':')[1:3]) for l in grep2})
    checks = {
        'written_exactly_9': len(written) == 9 and set(written) == set(exp),
        'bytes_equal_table': all(bytes_ok.values()),
        'support_diff_63_expected': diff_ok[SUPPORT_NAME],
        'support_groups_29_33_1': groups == {'link_to_storage': 29, 'evidence': 33, 'controlled_approach_revision': 1},
        'other_doc_diffs_expected': all(v for k, v in diff_ok.items() if k != SUPPORT_NAME),
        'area_membership_sha_both_4863f5ee': (sup_old.get('full_area_coverage_audit', {}).get('area_membership_sha256') == AREA_SHA_OLD
                                             and sup_new.get('full_area_coverage_audit', {}).get('area_membership_sha256') == AREA_SHA_OLD),
        'aus_29_eq_new_lts_eq_new_evidence_subset_added': (len(aus) == 29 and aus == new_lts == new_ev and aus <= added_links),
        'pins_total_111': total == 111,
        'pins_judged_106_ok': total - len(excluded) == 106 and not judged_bad,
        'pins_excluded_5_exact': sorted((r['file'], r['pointer']) for r in excluded) == sorted(PIN_EXCLUDED),
        'pins_backslash_4': backslash == 4,
        'membership_path_6_all_b0': len(mp) == 6 and all(r['value'] == OM701_REL and r['exists'] for r in mp),
        'grep_area_membership_sha256_0': len(grep1) == 0,
        'full_area_coverage_audit_reader_projection_support_304_only': readers == ['evaluation/controllers/projection_support.py:304']}
    res = {'step': 'P0-2', 'checks': checks, 'written_sha256': written, 'bytes_ok': bytes_ok,
           'diff_counts': {k: len(v) for k, v in diffs.items()}, 'diff_ok': diff_ok, 'support_groups': groups,
           'added_support_n': len(added_support), 'pins': {'total': total, 'excluded': excluded,
                                                           'judged_bad': judged_bad, 'backslash_judged': backslash},
           'membership_path_fields': mp, 'grep_area_membership_sha256': grep1, 'full_area_coverage_audit_readers': readers,
           'replacement_targets': {k: v['path'] for k, v in replacements.items()},
           'verdict': 'PASS' if all(checks.values()) else 'STOP'}
    result_write('p0_2', res)


# ================================================================================================ configure runs
def run_dir_of(run):
    for kind, base in C.RUNS.items():
        d = base / run if kind != 'b' else None
        if d is not None and d.is_dir():
            return d
    raise SystemExit('run folder not found: ' + run)


def prepare(run, T, dest):
    C.blind_guard(run)
    dec = run_dir_of(run) / ('decisions_' + run)
    rec = dest.parent / (dest.name + '.prep.json')
    if (dest / 'replay_manifest.json').is_file() and rec.is_file():
        return C.read_json(rec)
    if dest.exists():
        dest.rename(dest.parent / ('%s_interrupted_%s' % (dest.name, time.strftime('%Y%m%d_%H%M%S'))))
    env = C.child_env(NUMBA)
    rc, sec, text = C.run_capture([C.PY, '-B', str(C.GPREP), str(dec), str(T), str(dest), str(rec)],
                                  dest.parent / (dest.name + '.prepare.txt'), env)
    r = C.read_json(rec) or {}
    if rc != 0 or not r.get('all_copies') or not r.get('state_obs150_directory_is_bundle') \
            or r.get('history_count') != r.get('history_expected'):
        raise SystemExit('PREPARE_FAILED %s T=%s rc=%s' % (run, T, rc))
    return r


def adapter_call(rd, root, tuning, controller=None, out_dir=None):
    """The k92_replay.py (c20aff1d) argument list and environment, with an explicit tuning file."""
    m = json.loads((rd / 'replay_manifest.json').read_text(encoding='utf-8-sig'))
    sec = int(m['sim_sec'])
    s6 = '%06d' % sec
    dec = Path(m['source_decisions'])
    run_dir = dec.parent
    run_name = re.sub(r'^decisions_', '', dec.name)
    C.blind_guard(run_name)
    prov = json.loads((run_dir / ('run_provenance_%s.json' % run_name)).read_text(encoding='utf-8-sig'))
    run_root = prov['workspace_root']

    def rebase(p):
        full = os.path.abspath(p)
        base = os.path.abspath(run_root).rstrip(BS) + BS
        return os.path.join(str(root), full[len(base):]) if full.lower().startswith(base.lower()) else p
    prev = str(dec / ('action_%06d.json' % int(m['previous_sec']))) if m.get('previous_sec') is not None else None
    if not controller:
        plan = json.loads((run_dir / 'launch_plan.json').read_text(encoding='utf-8-sig'))
        controller = plan['warmup_controller'] if sec < int(plan['control_start_sec']) else plan['controller']
    files = prov['files']
    mapping = rebase(files['control_mapping']['path'])
    calibration = rebase(files['calibration']['path'])
    runner_config = rebase(files['generated_vbs_config']['path'])
    det = ''
    for line in Path(runner_config).read_text(encoding='utf-8', errors='replace').splitlines():
        mm = re.match(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$', line)
        if mm:
            det = mm.group(1)
    adapter = str(root / 'evaluation' / 'controllers' / 'vissim_stackelberg_adapter.py')
    out_dir = Path(out_dir or rd / 'cfgonly')
    a = [adapter, '--state-json', m['state']['replay'], '--out-action-json', str(out_dir / ('action_%s.json' % s6)),
         '--out-action-csv', str(out_dir / ('action_%s.csv' % s6)), '--mapping-json', mapping, '--controller', controller]
    if det:
        a += ['--detector-mapping-json', det]
    a += ['--calibration-json', calibration, '--tuning-json', str(tuning)]
    if prev:
        a += ['--previous-action-json', prev]
    mode = str(prov['env'].get('RW_ADAPTER_MODE') or '')
    if mode:
        a += ['--mode', mode]
    env = C.child_env(NUMBA)
    env = {k: v for k, v in env.items() if not k.upper().startswith('RW_')}
    env.update({k: str(v) for k, v in prov['env'].items()})
    env['PYTHONPATH'] = C.DEPROOT + r'\sdmpc;' + C.DEPROOT + r'\sdmpc-numba'
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1', PYTHONHASHSEED='0',
               NUMBA_CACHE_DIR=str(NUMBA))
    python = str(prov['env'].get('RW_PYTHON') or '')
    return python, a, env, {'sim_sec': sec, 'controller': controller, 'previous': prev, 'run': run_name}


def cfg_run(tag, run, T, arm, tree=None, controller=None, base=None):
    root = tree or P0TREE
    base = base or (OUT / 'cfgruns')
    d = base / tag
    res_file = d / 'child' / 'configured.json'
    if res_file.is_file():
        return C.read_json(res_file)
    if (d / 'child' / 'configure_failed.json').is_file():
        return C.read_json(d / 'child' / 'configure_failed.json')
    C.require_space(LOG)
    tuning = C.TOOLS / 'arms' / (arm + '.json')
    if C.sha256_file(tuning) != ARMS[arm]['sha256']:
        raise SystemExit('arm tuning changed: ' + arm)
    prepare(run, T, d / 'bundle')
    python, a, env, info = adapter_call(d / 'bundle', root, tuning, controller=controller, out_dir=d / 'adapter_out')
    (d / 'child').mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc, sec, _ = C.run_capture([python, '-B', str(C.TOOLS / 'c1_p0_child.py'), str(d / 'child')] + a,
                               d / 'child.txt', env, cwd=root)
    rec = C.read_json(res_file) or C.read_json(d / 'child' / 'configure_failed.json') or {'ok': False, 'error': 'no record'}
    rec['_run'] = {'tag': tag, 'run': run, 'T': T, 'arm': arm, 'tree': Path(root).name, 'exit': rc,
                   'wall_sec': round(time.time() - t0, 1), **info}
    C.write_json(d / 'run.json', rec['_run'])
    LOG('CFGRUN %s run=%s T=%s arm=%s tree=%s exit=%s ok=%s wall=%.0f' % (tag, run, T, arm, Path(root).name, rc,
                                                                         rec.get('ok'), time.time() - t0))
    return rec


def gen(path):
    """list indices only (c1_p0_child writes them as '/[i]'); dict keys (link ids included) stay as they are."""
    return re.sub(r'/\[\d+\]', '/[*]', path)


def leaves_of(tag, base=None):
    with gzip.open((base or OUT / 'cfgruns') / tag / 'child' / 'cfgnet_leaves.json.gz', 'rt', encoding='utf-8') as g:
        return json.load(g)


def diff_set(a, b):
    keys = set(a) | set(b)
    return sorted({gen(k.lstrip('/')) for k in keys if a.get(k) != b.get(k)})


def under(path, allowed):
    return any(path == d or path.startswith(d + '/') for d in allowed)


def state_tag(st):
    return '%s_t%06d' % (st['run'].replace('sdmpc31_', ''), st['T'])


def p0_3():
    C.lock_acquire('p0_3 configure runs (5 states x 5 arms)', LOG)
    try:
        rows = {}
        for st in STATES['probe_decisions_T900']:
            ctl = 'wu-link' if st['kind'] == 'robs' else None
            for arm in P0_ARMS:
                tag = '%s__%s' % (state_tag(st), arm)
                rows[tag] = cfg_run(tag, st['run'], st['T'], arm, controller=ctl)
    finally:
        C.lock_release(LOG)
    p0_3_judge()


def p0_3_judge():
    res = {'step': 'P0-3', 'states': {}, 'checks': {}}
    s_add_sets, input_diffs = {}, {}
    all_ok = True
    for st in STATES['probe_decisions_T900']:
        stag = state_tag(st)
        recs = {arm: C.read_json(OUT / 'cfgruns' / ('%s__%s' % (stag, arm)) / 'child' / 'configured.json') for arm in P0_ARMS}
        ok = {arm: bool(r and r.get('ok')) for arm, r in recs.items()}
        row = {'ok': ok}
        if all(ok.values()):
            lv = {arm: leaves_of('%s__%s' % (stag, arm)) for arm in P0_ARMS}
            E = {arm: diff_set(lv['off'], lv[arm]) for arm in P0_ARMS if arm != 'off'}
            row['E'] = E
            row['E_M_within'] = all(under(p, E_M_ALLOWED) for p in E['m'])
            row['E_H_within'] = all(under(p, E_H_ALLOWED) for p in E['h'])
            union = set(E['omega']) | set(E['m']) | set(E['h'])
            row['E_C1_within_union'] = set(E['c1']) <= union
            row['E_C1_equals_union'] = set(E['c1']) == union
            row['E_M_outside'] = [p for p in E['m'] if not under(p, E_M_ALLOWED)]
            row['E_H_outside'] = [p for p in E['h'] if not under(p, E_H_ALLOWED)]
            off_mm, om_mm = recs['off'].get('model_membership') or {}, recs['omega'].get('model_membership') or {}
            s_add = sorted(set(om_mm.get('inside', [])) & set(off_mm.get('outside', [])))
            s_rem = sorted(set(om_mm.get('outside', [])) & set(off_mm.get('inside', [])))
            row['S_add_n'] = len(s_add)
            row['S_removed_n'] = len(s_rem)
            row['unresolved_n'] = [off_mm.get('unresolved_n'), om_mm.get('unresolved_n')]
            s_add_sets[stag] = s_add
            ri_off, ri_om = recs['off'].get('route_inputs') or {}, recs['omega'].get('route_inputs') or {}
            changed = sorted(k for k in set(ri_off) | set(ri_om) if (ri_off.get(k) or [None])[0] != (ri_om.get(k) or [None])[0])
            input_diffs[stag] = changed
            row['input_event_kind_changed'] = changed
            row['input_changes'] = {k: [ri_off.get(k), ri_om.get(k)] for k in changed}
            row['input_ok'] = changed == SEVEN_GATES and all((ri_off[k][0], ri_om[k][0]) == ('outside_generation', 'generation')
                                                             for k in changed)
            row['membership_sha'] = {arm: recs[arm].get('membership_sha256') for arm in P0_ARMS}
            all_ok &= row['E_M_within'] and row['E_H_within'] and row['E_C1_within_union'] and row['input_ok'] \
                and not s_rem
        else:
            row['errors'] = {arm: (r or {}).get('error') or (r or {}).get('collect_error') for arm, r in recs.items()
                             if not ok[arm]}
            all_ok = False
        res['states'][stag] = row
    same_s_add = len({tuple(v) for v in s_add_sets.values()}) == 1 and len(s_add_sets) == 5
    res['S_add'] = next(iter(s_add_sets.values())) if same_s_add else None
    res['S_add_by_state_n'] = {k: len(v) for k, v in s_add_sets.items()}
    res['checks'] = {'all_configured_25': all(all(r['ok'].values()) for r in res['states'].values()),
                     'E_M_E_H_E_C1_input_ok_each_state': all_ok, 'S_add_same_5_states': same_s_add,
                     'S_add_nonempty': bool(res['S_add'])}
    res['verdict'] = 'PASS' if all(res['checks'].values()) else 'STOP'
    result_write('p0_3', res)


# ================================================================================================ P0-4
def p0_4():
    cfgb_raw = (C.B0F / 'config_b0_v3c3.json').read_bytes()
    cfgb = json.loads(cfgb_raw)
    curves = {m: cfgb['freeway']['physical_ramp_head_service_veh_per_cycle'][m] for m in C.FWE}
    installed, dropped = {}, {}
    for m, curve in curves.items():
        table = {'0': 0., **{g: n * 3600 / 10 for g, n in curve.items()}}
        installed[m] = {g: s for g, s in table.items() if g != '9'}
        dropped[m] = {'9': '10'}
    rb = C.CP / 'readback' / 'out'
    head = {'schema': 'c1-head-service-fwe/v1',
            'decision': 'D-K9-94 Q4 (a): codex FW_E head curves; at install g9 is dropped and g10 kept (keep_green_10)',
            'values': {'meters': list(C.FWE), 'curves_veh_per_cycle': curves, 'full_service_rule': 'keep_green_10',
                       'installed_service_by_green_veh_h': installed, 'dropped': dropped,
                       'install_expression': 'n*3600/10 (CX lane_plant_runtime.py:618, OU physical_ramp_branches.py:86)'},
            'source': {'name': 'config_b0_v3c3.json', 'sha256': C.sha256_bytes(cfgb_raw),
                       'pointer': '/freeway/physical_ramp_head_service_veh_per_cycle',
                       'codex_install_code': {'name': 'lane_plant_runtime.py', 'lines': '616-620',
                                              'sha256': C.sha256_file(C.CX / 'evaluation/controllers/lane_plant_runtime.py')},
                       'codex_head': 'a49981ff'},
            'report_only': {'readback_k7': {'discharge.json': C.sha256_file(rb / 'discharge.json'),
                                            'headcurve.json': C.sha256_file(rb / 'headcurve.json'),
                                            'use': 'comparison only, not a value source (READBACK_METER.md section 2.2)'}}}
    raw = C.data(head)
    (OUT / 'p0_4').mkdir(parents=True, exist_ok=True)
    (OUT / 'p0_4' / 'head_service_fwe_c1.json').write_bytes(raw)
    decl = json.loads((C.DECL / 'head_service_fwe_c1.json').read_text(encoding='utf-8'))
    table_repr = {m: {g: repr(s) for g, s in t.items()} for m, t in installed.items()}
    summary = json.loads((C.DECL / 'SUMMARY.json').read_text(encoding='utf-8'))
    # Q26 provenance: where the curve (0.5 veh/lane per green-second, cap 4.2) is written (report only)
    hits = []
    pats = re.compile(r'physical_ramp_head_service_veh_per_cycle|head_service_veh_per_cycle|head[ -_]curve|0\.5 ?veh|4\.2')
    sealed = re.compile(r's(?:37|59|61|67)(?![0-9])', re.I)
    base = Path(r'D:/VISSIM_handoff/20261024')
    for p in sorted(base.rglob('*.md')):           # handoff documents only (no raw / derived data rows)
        rel = str(p.relative_to(base)).replace(BS, '/')
        if rel.split('/')[0] in ('raw', 'derived') or any(t in rel.lower() for t in C.BLIND_TOKENS) or sealed.search(rel):
            continue
        if p.stat().st_size > 5_000_000:
            continue
        try:
            for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                if sealed.search(line) or any(t in line.lower() for t in C.BLIND_TOKENS):
                    continue                       # never print a line naming a sealed / blind seed
                if 'physical_ramp_head_service' in line or ('head' in line.lower() and pats.search(line)):
                    hits.append({'file': rel, 'line': i, 'text': line.strip()[:220]})
        except OSError:
            pass
    cx_hits = subprocess.run(['git', '-C', str(C.CX), 'grep', '-n', 'physical_ramp_head_service_veh_per_cycle'],
                             capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.splitlines()
    checks = {'bytes_3933a882': C.sha256_bytes(raw) == '3933a882b7948abdae825731ecd06494dead4628d5d26c69d1d8f53dc6866333',
              'equals_declared_bytes': raw == (C.DECL / 'head_service_fwe_c1.json').read_bytes(),
              'installed_repr_equals_section_2_7': table_repr == summary['head_installed_repr'],
              'cfg_b_sha_729640af': C.sha256_bytes(cfgb_raw) == '729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983'}
    res = {'step': 'P0-4', 'checks': checks, 'q26_handoff_hits': hits[:200], 'q26_handoff_hits_n': len(hits),
           'q26_cx_code_hits': [h[:220] for h in cx_hits][:80],
           'verdict': 'PASS' if all(checks.values()) else 'STOP'}
    del decl
    result_write('p0_4', res)


# ================================================================================================ P0-5 / P0-11
def prev_greens(run, T):
    C.blind_guard(run)
    p = run_dir_of(run) / ('decisions_' + run) / ('action_%06d.csv' % (T - 150))
    import csv
    rows = [r for r in csv.DictReader(p.read_text(encoding='utf-8-sig').splitlines()) if r['kind'] == 'ramp_meter']
    return {r['id']: float(r['green_sec']) for r in rows}


def floor_of(prev, ratio_max, table_greens, base=2.0, cycle=10.0, change=2.0, trigger=0.9):
    """amendment C1 section 2.6 formula + RV-2 table lowering."""
    triggered = ratio_max is not None and ratio_max >= trigger - 1e-10
    floor = max(base, min(cycle, prev + change)) if triggered else base
    rounded_from = None
    if not any(g == floor for g in table_greens):
        lower = [g for g in table_greens if base <= g <= floor]
        rounded_from, floor = floor, float(max(lower))
    return triggered, floor, rounded_from


def p0_5():
    res = {'step': 'P0-5', 'states': {}}
    ok_all = True
    for st in STATES['probe_decisions_T900']:
        stag = state_tag(st)
        rec = C.read_json(OUT / 'cfgruns' / ('%s__c1' % stag) / 'child' / 'configured.json') or {}
        lrr = rec.get('lane_ramp_runtime')
        prev = prev_greens(st['run'], st['T'])
        rows = {}
        if not isinstance(lrr, dict) or set(lrr) != set(C.METERS):
            ok_all = False
            res['states'][stag] = {'error': 'lane_ramp_runtime missing or meters differ', 'meters': sorted(lrr or {})}
            continue
        for meter in C.METERS:
            lanes = lrr[meter]
            good = all(('error' not in l) and l.get('snapshot_keys_present') == ['upstream_travelling_veh', 'head_ready_veh']
                       and l.get('finite_positive_capacity') and l.get('finite_nonnegative_occupancy') for l in lanes)
            ratio = max((l.get('fill_fraction') for l in lanes if isinstance(l.get('fill_fraction'), float)), default=None)
            table = sorted(int(g) for g in (rec.get('service_tables') or {}).get(meter, {}))
            trig, floor, rounded = floor_of(prev[meter], ratio, table)
            rows[meter] = {'lanes': [{k: l.get(k) for k in ('lane', 'type', 'has_lane_buffers_attr', 'prehead_veh',
                                                            'capacity_veh', 'fill_fraction', 'head_position_m',
                                                            'lanes', 'spacing_m')} for l in lanes],
                           'names_ok': good, 'previous_green': prev[meter], 'triggered': trig, 'floor': floor,
                           'table_rounded_from': rounded, 'table_greens': table}
            ok_all &= good
        res['states'][stag] = rows
    res['checks'] = {'all_buffers_named_finite': ok_all}
    res['verdict'] = 'PASS' if ok_all else 'STOP'
    result_write('p0_5', res)


def f_count(u):
    return u + (1 if u >= 2 else 0)


def p0_11():
    r5 = C.read_json(OUT / 'p0_5' / 'result.json') or {}
    exp = {}
    for stag, rows in (r5.get('states') or {}).items():
        if 'error' in rows:
            exp[stag] = None
            continue
        ue = sum(1 for m in C.FWE if rows[m]['floor'] != 10)
        uw = sum(1 for m in C.FWW if rows[m]['floor'] != 10)
        all_prev10 = all(rows[m]['previous_green'] == 10 for m in C.METERS)
        exp[stag] = {'u_E': ue, 'u_W': uw, 'N_tighten': f_count(ue) + f_count(uw), 'release': 0,
                     'formula_applies': all_prev10, 'plan_blocks': [8, 6, 4]}
    out = OUT / 'p0_11' / 'selftest.json'
    if not out.is_file():
        env = C.child_env(NUMBA)
        env['PYTHONPATH'] = C.DEPROOT + r'\sdmpc;' + C.DEPROOT + r'\sdmpc-numba'
        rc, sec, _ = C.run_capture([C.PY, '-B', str(C.TOOLS / 'c1_selftest.py'), str(P0TREE), str(out)],
                                   OUT / 'p0_11' / 'selftest.txt', env)
    st = C.read_json(out) or {}
    formula = [c for c in st.get('cases', []) if c['name'] == 'neighbor_count_formula']
    checks = {'formula_selftest_true': bool(formula) and formula[0]['ok'],
              'selftest_all_true': bool(st.get('ok')),
              'expected_counts_all_states': all(v is not None for v in exp.values()) and len(exp) == 5}
    res = {'step': 'P0-11', 'expected': exp, 'checks': checks, 'selftest_sha256': C.sha256_file(out) if out.is_file() else None,
           'verdict': 'PASS' if all(checks.values()) else 'STOP'}
    result_write('p0_11', res)


# ================================================================================================ P0-6
def p0_6():
    st = STATES['probe_decisions_T900'][0]
    stag = state_tag(st)
    extra = [a for a in TOKEN_ARMS if a not in P0_ARMS]
    C.lock_acquire('p0_6 token configure runs (%d arms)' % len(extra), LOG)
    try:
        for arm in extra:
            cfg_run('%s__%s' % (stag, arm), st['run'], st['T'], arm)
    finally:
        C.lock_release(LOG)
    p0_6_judge()


def p0_6_judge():
    st = STATES['probe_decisions_T900'][0]
    stag = state_tag(st)
    tok = {}
    for arm in TOKEN_ARMS:
        r = C.read_json(OUT / 'cfgruns' / ('%s__%s' % (stag, arm)) / 'child' / 'configured.json') or {}
        tok[arm] = {'token': r.get('token'), 'ok': r.get('ok'), 'joint_max_leader_candidates': r.get('joint_max_leader_candidates'),
                    'audit_in_options': 'meter_neighbor_audit' in (r.get('sdmpc_options_keys') or [])}
    changed = {tok[a]['token'] for a in TOKEN_CHANGED}
    checks = {'all_ok': all(v['ok'] for v in tok.values()),
              'same_arms_eq_428e650d': all(tok[a]['token'] == C.TOKEN_OFF for a in TOKEN_SAME),
              'changed_arms_one_token_ne_off': len(changed) == 1 and C.TOKEN_OFF not in changed and None not in changed,
              'audit_key_only_in_changed_arms': all(tok[a]['audit_in_options'] == (a in TOKEN_CHANGED) for a in TOKEN_ARMS),
              'joint_cap_3_where_key': all(tok[a]['joint_max_leader_candidates'] == (3 if 'max_leader_candidates' in ARMS[a]['keys'] else 1)
                                           for a in TOKEN_ARMS)}
    res = {'step': 'P0-6', 'state': stag, 'tokens': tok, 'm_family_token': next(iter(changed)) if len(changed) == 1 else None,
           'checks': checks, 'verdict': 'PASS' if all(checks.values()) else 'STOP'}
    result_write('p0_6', res)


# ================================================================================================ P0-7
EXPOSURE_ROOTS = (Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8'), Path(r'D:/VISSIM-merge/k8b_commit_gates'),
                  Path(r'D:/VISSIM-merge/k8b_probe'), Path(r'D:/VISSIM-merge/k8b_miniprobe'),
                  Path(r'D:/VISSIM-merge/k8_gates_out_v2'), C.CP)
KEYS_RE = re.compile(rb'"(?:storage:|movement:|link:)?(?:37|127|129|10491|26)"\s*:')


def t_of(path):
    for m in re.finditer(r'(?:^|[^0-9])(\d{3,6})(?:[^0-9]|$)', path):
        v = int(m.group(1))
        if 150 <= v <= 9000 and v % 150 == 0:
            return v
    return None


def p0_7():
    C.lock_acquire('p0_7 exposure name scan', LOG)
    try:
        rows = []
        for root in EXPOSURE_ROOTS:
            for base, dirs, files in os.walk(C.lp(root)):
                rel_base = os.path.relpath(base, C.lp(root)).replace(BS, '/')
                sealed = 'sealed' in rel_base.lower()
                for f in files:
                    rel = (rel_base + '/' + f) if rel_base != '.' else f
                    low = rel.lower()
                    if not re.search(r's47(?![0-9])', low):
                        continue
                    full = os.path.join(base, f)
                    try:
                        size = os.path.getsize(full)
                    except OSError:
                        size = None
                    T = t_of(rel)
                    in_window = T is not None and 1050 <= T <= 8850
                    keys = None
                    if (not sealed and f.lower().endswith('.json') and size is not None and size <= 5_000_000):
                        try:
                            with open(full, 'rb') as h:
                                found = sorted({m.group(0).split(b'"')[1].decode() for m in KEYS_RE.finditer(h.read())})
                            keys = found
                        except OSError:
                            keys = None
                    rows.append({'root': str(root), 'path': rel, 'bytes': size, 'T': T, 'T_in_F_window': in_window,
                                 'sealed_root_names_only': sealed, 'key_names_matched': keys,
                                 'kind': Path(f).suffix.lower()})
    finally:
        C.lock_release(LOG)
    header = 'D-K9-84 Q3 의 Ω701 재집계는 V-A·J1·NC3 9런, R-obs 아님 [읽음 NOTES:277]'
    doc = {'first_line': header, 'scope': 'names and key names only (values never opened); sealed roots: names only',
           'roots': [str(r) for r in EXPOSURE_ROOTS], 'rows': rows}
    path = OUT / 'p0_7' / 'exposure_list.json'
    C.write_json(path, doc)
    summ = {'files': len(rows), 'in_window': sum(r['T_in_F_window'] for r in rows),
            'with_key_match': sum(1 for r in rows if r['key_names_matched']),
            'sealed_names_only': sum(r['sealed_root_names_only'] for r in rows),
            'by_root': {str(r): sum(1 for x in rows if x['root'] == str(r)) for r in EXPOSURE_ROOTS},
            'by_kind': {}}
    for r in rows:
        summ['by_kind'][r['kind']] = summ['by_kind'].get(r['kind'], 0) + 1
    res = {'step': 'P0-7', 'first_line': header, 'exposure_list_sha256': C.sha256_file(path), 'summary': summ,
           'verdict': 'REPORT'}
    result_write('p0_7', res)


# ================================================================================================ P0-8 / P0-9 (B, already seen)
B_SEEDS = (31, 41, 43)


def b_dec(seed):
    return C.RUNS['b'] / ('s%d' % seed) / 'sdmpc' / ('decisions_sdmpc31_sdmpc9000_s%d' % seed)


def p0_8():
    C.lock_acquire('p0_8 B decision JSON meter_operating_bounds RM_C10639', LOG)
    try:
        out = {}
        for seed in B_SEEDS:
            rows = []
            for T in range(900, 8101, 150):
                p = b_dec(seed) / ('action_%06d.json' % T)
                if not p.is_file():
                    rows.append({'T': T, 'missing': True})
                    continue
                d = json.loads(p.read_text(encoding='utf-8-sig'))
                mob = ((d.get('metadata') or {}).get('joint_leader_selection') or {}).get('meter_operating_bounds')
                r = (mob or {}).get('ramps', {}).get('RM_C10639') if isinstance(mob, dict) else None
                rows.append({'T': T, 'present': r is not None, 'triggered': (r or {}).get('triggered'),
                             'minimum_green_sec': (r or {}).get('minimum_green_sec'),
                             'previous_green_sec': (r or {}).get('previous_green_sec'),
                             'fill_fraction': [l.get('fill_fraction') for l in (r or {}).get('lanes', [])],
                             'prehead_veh': [l.get('prehead_veh') for l in (r or {}).get('lanes', [])],
                             'capacity_veh': [l.get('capacity_veh') for l in (r or {}).get('lanes', [])],
                             'executed_green': (d.get('diagnostics') or {}).get('rw_meter_green_RM_C10639')})
                del d
            out['v3c3-s%d' % seed] = rows
    finally:
        C.lock_release(LOG)
    summ = {}
    for k, rows in out.items():
        ff = [x for r in rows for x in (r.get('fill_fraction') or []) if isinstance(x, (int, float))]
        ph = [x for r in rows for x in (r.get('prehead_veh') or []) if isinstance(x, (int, float))]
        summ[k] = {'decisions': len(rows), 'present': sum(1 for r in rows if r.get('present')),
                   'triggered': sum(1 for r in rows if r.get('triggered')),
                   'fill_fraction_quantiles': quant(ff), 'prehead_veh_quantiles': quant(ph),
                   'floors': sorted({r.get('minimum_green_sec') for r in rows if r.get('present')}),
                   'executed_green_counts': counts([r.get('executed_green') for r in rows])}
    res = {'step': 'P0-8', 'by_seed': out, 'summary': summ,
           'readback_reference': 'READBACK g2 블록 미터 앞 중앙 42.6대 [읽음 RB:175]', 'verdict': 'REPORT'}
    result_write('p0_8', res)


def quant(xs):
    if not xs:
        return None
    s = sorted(xs)
    q = lambda f: s[min(len(s) - 1, int(round(f * (len(s) - 1))))]
    return {'n': len(s), 'min': s[0], 'p25': q(.25), 'median': q(.5), 'p75': q(.75), 'max': s[-1]}


def counts(xs):
    out = {}
    for x in xs:
        out[str(x)] = out.get(str(x), 0) + 1
    return out


def sg_green(csv_path, prefix):
    import csv
    rows = [r for r in csv.DictReader(Path(csv_path).read_text(encoding='utf-8-sig').splitlines())
            if r['kind'] == 'signal_sg' and r['id'].startswith(prefix)]
    if not rows:
        return None
    total = 0.0
    for r in rows:
        total += (150.0 / float(r['green_sec'])) * (float(r['p2_green']) - float(r['p1_green']))
    return total


def p0_9():
    C.lock_acquire('p0_9 B decision JSON SC1001 reads 900-2550', LOG)
    try:
        out = {}
        for seed in B_SEEDS:
            rows = []
            for T in range(900, 2551, 150):
                base = b_dec(seed) / ('action_%06d' % T)
                d = json.loads(Path(str(base) + '.json').read_text(encoding='utf-8-sig'))
                js = (d.get('metadata') or {}).get('joint_leader_selection') or {}
                lr = [r for r in js.get('local_rows', []) if r.get('owner') == 'SC1001']
                gr = [r for r in js.get('gradient_rows', []) if r.get('owner') == 'SC1001']
                rows.append({'T': T,
                             'sg2_plan_green': sg_green(str(base) + '.csv', 'SC1001_SG2_W'),
                             'sg5_plan_green': sg_green(str(base) + '.csv', 'SC1001_SG5_W'),
                             'green_times': {k: v for k, v in (d.get('green_times') or {}).items() if k.startswith('SC1001_')},
                             'offset': (d.get('offsets') or {}).get('SC1001'),
                             'own_cost_omega_partition': ((js.get('omega_partition') or {}).get('costs') or {}).get('SC1001'),
                             'price_gradient_first_iteration': (lr[0].get('price_gradient') if lr else None),
                             'price_gradient_last_iteration': (lr[-1].get('price_gradient') if lr else None),
                             'gradient_total_axes': [[r.get('kind'), r.get('key'), r.get('block'), r.get('total')] for r in gr][:12],
                             'next_prices_scaled': ((js.get('price_state') or {}).get('next_prices_scaled'))})
                del d
            out['v3c3-s%d' % seed] = rows
        va = {}
        for seed in B_SEEDS:
            run = 'sdmpc31_v3c3_k92va_s%d' % seed
            dec = C.RUNS['va'] / run / ('decisions_' + run)
            va['v3c3-s%d' % seed] = {T: sg_green(dec / ('action_%06d.csv' % T), 'SC1001_SG2_W') for T in range(900, 2551, 150)}
    finally:
        C.lock_release(LOG)
    summ = {}
    for k, rows in out.items():
        s2 = [r['sg2_plan_green'] for r in rows]
        s5 = [r['sg5_plan_green'] for r in rows]
        vs = list(va[k].values())
        summ[k] = {'S_SG2_B_plan': (math.fsum(s2) if None not in s2 else None),
                   'S_SG5_B_plan': (math.fsum(s5) if None not in s5 else None),
                   'S_SG2_VA_record': (math.fsum(vs) if None not in vs else None),
                   'nc3_sg2_green_only_900_2700': 540.0,
                   'offsets': [r['offset'] for r in rows]}
    res = {'step': 'P0-9', 'by_seed': out, 'summary': summ, 'va_sg2_by_T': va,
           'nc3_source': 'INPUT1099 r2 §2-6 / VERIFY_C_PREP §2 [읽음]: NC3 .sig prog 1 GREEN 만 900-2,700 s 540 s, SG5 288 s',
           'verdict': 'REPORT'}
    result_write('p0_9', res)


# ================================================================================================ P0-10
def p0_10():
    pats = {'link_129': re.compile(r"""['"]129['"]|\b129\b"""), 'link_10491': re.compile(r'10491'),
            'link_26': re.compile(r"""['"]26['"]"""), 'link_127': re.compile(r"""['"]127['"]""")}
    files = sorted(p for p in (P0TREE / 'evaluation' / 'controllers').glob('*.py'))
    hits = {k: [] for k in pats}
    for p in files:
        for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            for k, rx in pats.items():
                if rx.search(line):
                    hits[k].append('%s:%d: %s' % (p.name, i, line.strip()[:160]))
    data_hits = {}
    for rel in ('diagnostics/sdmpc_n31_20260924/plant_n31_v2.json', 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'):
        txt = (P0TREE / rel).read_text(encoding='utf-8')
        data_hits[rel] = {k: len(rx.findall(txt)) for k, rx in pats.items()}
    res = {'step': 'P0-10', 'code_hits_n': {k: len(v) for k, v in hits.items()},
           'code_hits': {k: v[:60] for k, v in hits.items()}, 'data_hits': data_hits, 'verdict': 'REPORT'}
    result_write('p0_10', res)


# ================================================================================================ P0-13
# N_C1 (amendment C1 section 6.3) BEFORE the amendment 21 section 6.1 list (with amendment 27 K92-N before its
# one-level gate-tree rule), then the run names; every rule in order on the whole string (amendment 27 section 2.1:
# the k92_compare.norm_s form, equal to 'first match' because a replaced <root> never matches again).
N_RULES = [
    (r'd:/vissim-merge/k8_gate_trees/c1/trees/[a-z0-9_]+', '<root>'),                                   # N_C1
    (r'd:/vissim-merge/k8_gate_trees/c1/out/(?:[a-z0-9_]+/)*?t[0-9]{6}(?:_[a-z0-9]+)*', '<bundle>'),    # N_C1
    (r'd:/vissim_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s[0-9]+', '<run>'),                       # N_C1
    (r'd:/vissim_runs/20261026_codex_b_v3c3/s[0-9]+/sdmpc', '<run>'),                                   # N_C1
    (r'sdmpc31_v3c3_k92va_s[0-9]+|sdmpc31_sdmpc9000_s[0-9]+', '<name>'),                                 # N_C1
    (r'd:/vissim-merge/frozen/sdmpc31_[0-9a-f]{8}_[0-9]{12}', '<root>'),                                 # A21
    (r'd:/vissim-merge/sim3-n31-k8', '<root>'),                                                          # A21
    (r'd:/vissim-merge/k8_gate_trees/(?:k92b1/(?:(?:a25|a26decl|a27)/)?(?!(?:a25|a26decl|a27)(?![a-z0-9_]))'
     r'|k92attrib/)[a-z0-9_]+(?=/|$)', '<root>'),                                                         # A27 K92-N
    (r'd:/vissim-merge/k8_gate_trees/(?:s31fail/tree74(?:_base|_f1)?|[a-z0-9_]+)', '<root>'),            # A21
    (r'd:/vissim_runs/20261001_v3c3/reports/k8/(?:offline_gates|offline_gates_k8h)/(?:[a-z0-9_]+/)*?t[0-9]{6}'
     r'(?:_[a-z0-9]+)*', '<bundle>'),                                                                     # A21
    (r'd:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+', '<run>'),                    # A21
    (r'd:/vissim_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s[0-9]+', '<run>'),                          # A21
    (r'sdmpc31_v3c3_k8j1[a-z]*_s[0-9]+|sdmpc31_v3c3_nc_s[0-9]+', '<name>')]                              # A21 3.


def n_norm(s):
    x = s.lower().replace('\\\\', '/').replace(BS, '/')
    for rx, rep in N_RULES:
        x = re.sub(rx, rep, x)
    return x


def p0_13():
    cases = [
        ('D:/VISSIM-merge/k8_gate_trees/c1/trees/probe_5cdc6eb1/evaluation/controllers/sdmpc.py', '<root>/evaluation/controllers/sdmpc.py'),
        ('D:\\VISSIM-merge\\k8_gate_trees\\c1\\trees\\c1_2_abcdef12\\evaluation\\x.py', '<root>/evaluation/x.py'),
        ('D:/VISSIM-merge/k8_gate_trees/c1/out/probe/dec/t000900_c1/replay/action_000900.json', '<bundle>/replay/action_000900.json'),
        ('D:/VISSIM-merge/k8_gate_trees/c1/out/commit/c1_2/t000900/replay', '<bundle>/replay'),
        ('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/decisions_sdmpc31_v3c3_k92va_s41/action_000750.json',
         '<run>/decisions_<name>/action_000750.json'),
        ('D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/decisions_sdmpc31_sdmpc9000_s43/action_000900.json',
         '<run>/decisions_<name>/action_000900.json'),
        ('D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31/decisions_sdmpc31_v3c3_nc_s31/action_000750.csv',
         '<run>/decisions_<name>/action_000750.csv'),
        ('sdmpc31_v3c3_k92va_s31', '<name>'), ('sdmpc31_sdmpc9000_s31', '<name>'),
        ('D:/VISSIM-merge/k8_gate_trees/c1/trees/base_c20aff1d/diagnostics/sdmpc_n31_20260924/config_n31_v2.json',
         '<root>/diagnostics/sdmpc_n31_20260924/config_n31_v2.json'),
        ('D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833/evaluation/controllers/sdmpc.py',
         '<root>/evaluation/controllers/sdmpc.py'),
        ('d:\\vissim-merge\\k8_gate_trees\\c1\\out\\gk0\\t004950_vas43\\state_004950.json', '<bundle>/state_004950.json')]
    rows = []
    for raw, want in cases:
        got = n_norm(raw)
        rows.append({'input': raw, 'want': want, 'got': got, 'ok': got == want})
    ok = all(r['ok'] for r in rows)
    res = {'step': 'P0-13', 'cases': rows, 'verdict': 'PASS' if ok else 'STOP'}
    result_write('p0_13', res)


# ================================================================================================ values
def values():
    path = C.C1D / 'C1_VALUES.json'
    if path.exists():
        raise SystemExit('C1_VALUES.json exists (never rewritten)')
    r = {s: C.read_json(OUT / s / 'result.json') for s in ('p0_1', 'p0_2', 'p0_3', 'p0_4', 'p0_5', 'p0_6', 'p0_7',
                                                          'p0_8', 'p0_9', 'p0_10', 'p0_11', 'p0_13')}
    doc = {'schema': 'c1-values/v1', 'amendment_sha256': C.AMEND_SHA, 'patch_sha256': MAN['patch_sha256'],
           'p0_tree': P0TREE.name,
           'p0_3': {k: v.get('E') for k, v in (r['p0_3'] or {}).get('states', {}).items()},
           'p0_3_S_add': (r['p0_3'] or {}).get('S_add'),
           'p0_3_input_changes': {k: v.get('input_event_kind_changed') for k, v in (r['p0_3'] or {}).get('states', {}).items()},
           'p0_5': (r['p0_5'] or {}).get('states'),
           'p0_6': {'tokens': {a: t['token'] for a, t in ((r['p0_6'] or {}).get('tokens') or {}).items()},
                    'm_family_token': (r['p0_6'] or {}).get('m_family_token')},
           'p0_7_exposure_list_sha256': (r['p0_7'] or {}).get('exposure_list_sha256'),
           'p0_11': (r['p0_11'] or {}).get('expected'),
           'verdicts': {k: (v or {}).get('verdict') for k, v in r.items()},
           'result_sha256': {k: (C.sha256_file(OUT / k / 'result.json') if (OUT / k / 'result.json').is_file() else None)
                             for k in r}}
    C.write_new(path, json.dumps(doc, indent=1, ensure_ascii=False, default=str) + '\n')
    LOG('C1_VALUES written sha256=%s' % C.sha256_file(path))


if __name__ == '__main__':
    C.set_below_normal()
    step = sys.argv[1] if len(sys.argv) > 1 else ''
    LOG('START %s argv=%s' % (step, sys.argv[1:]))
    if step == 'cfgrun':
        a = sys.argv[2:]
        tree = C.TC1 / 'trees' / a[a.index('--tree') + 1] if '--tree' in a else None
        ctl = a[a.index('--controller') + 1] if '--controller' in a else None
        base = C.TC1 / 'out' / 'dev' if tree is not None and tree.name.startswith('dev_') else None
        rec = cfg_run(a[0], a[1], int(a[2]), a[3], tree=tree, controller=ctl, base=base)
        print('CFGRUN ok=%s' % rec.get('ok'))
    elif step in ('p0_1', 'p0_2', 'p0_3', 'p0_4', 'p0_5', 'p0_6', 'p0_7', 'p0_8', 'p0_9', 'p0_10', 'p0_11', 'p0_13',
                  'values', 'p0_3_judge', 'p0_6_judge'):
        globals()[step]()
    else:
        raise SystemExit(__doc__)
    LOG('END %s' % step)
