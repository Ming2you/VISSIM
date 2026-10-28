# A1 frozen tree check (read-only). Usage: python -B a1_tree_check.py <FRZ> <out.json>
# 1) SOURCE_FILES.csv 3,638 rows sha in FRZ, 2) RESTORED_FILES.json 3,544 sha, 3) STANDIN_FILES.json 3 standin sha,
# 4) files outside the three lists: each must be byte-equal to the handoff code/ copy,
# 5) FRZ table == A0 code table minus caches and minus the A0-only file optimized_config_t2390.json,
# 6) FREEZE.json file table == FRZ table, FREEZE.json git status entries == RESTORED + STANDIN paths (all '??'),
# 7) PRE_A1 section 1 key file sha (prefix match).
import csv, hashlib, json, os, sys
BS = chr(92)
FRZ = sys.argv[1].replace(BS, '/')
A0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0'
A0CODE = A0 + '/code'
HCODE = 'D:/VISSIM_handoff/20261024/code'
A0_ONLY = 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config_t2390.json'


def longp(p):
    return BS + BS + '?' + BS + os.path.abspath(p).replace('/', BS)


def sha(p):
    h = hashlib.sha256()
    with open(longp(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def table(root, skip_git=True):
    out = {}
    lr = longp(root)
    for dp, dn, fn in os.walk(lr):
        for f in fn:
            full = os.path.join(dp, f)
            rel = full[len(lr) + 1:].replace(BS, '/')
            if skip_git and (rel == '.git' or rel.startswith('.git/')):
                continue
            if '/__pycache__/' in '/' + rel or '/__tangentcache__/' in '/' + rel or '/.pytest_cache/' in '/' + rel or rel.endswith('.pyc'):
                continue
            if rel == 'FREEZE.json':
                continue
            out[rel] = sha(root + '/' + rel)
    return out


def check(entries, key, tab):
    ok, bad = 0, []
    for path, want in entries:
        got = tab.get(path)
        if got is None:
            bad.append(('missing', path))
        elif got == want:
            ok += 1
        else:
            bad.append(('bad', path))
    return {'list': key, 'n': len(entries), 'ok': ok, 'bad': len(bad), 'examples': bad[:10]}


frz = table(FRZ)
a0 = table(A0CODE)
src = [(r['path'], r['sha256']) for r in csv.DictReader(open(HCODE + '/handoff/SOURCE_FILES.csv', encoding='utf-8-sig'))]
rst = [(r['path'], r['sha256']) for r in json.load(open(A0 + '/RESTORED_FILES.json', encoding='utf-8'))]
sti = [(r['path'], r['standin_sha256']) for r in json.load(open(A0 + '/STANDIN_FILES.json', encoding='utf-8'))]
out = {'frz': FRZ, 'frz_files': len(frz),
       'manifest_sha256': {'RESTORED_FILES.json': sha(A0 + '/RESTORED_FILES.json'), 'STANDIN_FILES.json': sha(A0 + '/STANDIN_FILES.json'),
                           'SOURCE_FILES.csv': sha(HCODE + '/handoff/SOURCE_FILES.csv')},
       'checks': [check(src, 'SOURCE_FILES.csv', frz), check(rst, 'RESTORED_FILES.json', frz), check(sti, 'STANDIN_FILES.json', frz)]}
known = {p for p, _ in src} | {p for p, _ in rst} | {p for p, _ in sti}
outside = sorted(k for k in frz if k not in known)
diff_h = []
for k in outside:
    hp = HCODE + '/' + k
    try:
        hs = sha(hp)
    except FileNotFoundError:
        diff_h.append(('missing_in_handoff', k)); continue
    if hs != frz[k]:
        diff_h.append(('differs_from_handoff', k))
out['outside_lists'] = {'n': len(outside), 'not_equal_to_handoff_copy': len(diff_h), 'examples': diff_h[:10]}
a0_cmp = {k: v for k, v in a0.items() if k != A0_ONLY}
out['vs_a0_code'] = {'a0_files_excl_cache': len(a0), 'a0_only_excluded': A0_ONLY if A0_ONLY in a0 else None,
                     'changed': sorted(k for k in a0_cmp.keys() & frz.keys() if a0_cmp[k] != frz[k])[:20],
                     'missing_in_frz': sorted(a0_cmp.keys() - frz.keys())[:20],
                     'extra_in_frz': sorted(frz.keys() - a0_cmp.keys())[:20]}
fz = json.load(open(longp(FRZ + '/FREEZE.json'), encoding='utf-8'))
out['freeze_json'] = {'sha256': sha(FRZ + '/FREEZE.json'), 'file_count': fz['file_count'], 'total_bytes': fz['total_bytes'],
                      'tree_sha256': fz['tree_sha256'], 'table_equal_to_frz': fz['files'] == frz,
                      'git_head': fz['git']['head'], 'git_branch': fz['git']['branch'], 'git_status_entries': fz['git']['status_entries'],
                      'git_status_sha256': fz['git']['status_sha256'], 'frozen': fz['frozen'], 'source': fz['source']}
st = fz['git']['status']
codes = sorted({e[:2] for e in st})
paths = {e[3:] for e in st}
out['freeze_json']['git_status_codes'] = codes
out['freeze_json']['git_status_paths_equal_restored_plus_standin'] = paths == ({p for p, _ in rst} | {p for p, _ in sti})
KEY = {'diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1': '8e95423b',
       'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1': 'b56e1b36',
       'scripts/run_real_world_stackelberg_controller.vbs': '14722088',
       'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/lane_native_b110.vbs': 'b74e05b2',
       'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/lane_native_b110_sgplan.vbs': 'ec731cab',
       'evaluation/controllers/vissim_stackelberg_adapter.py': 'a615d8ca',
       'evaluation/controllers/sdmpc.py': '5c1ba251',
       'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json': 'c9088262',
       'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx': '64cf5f55',
       'diagnostics/sdmpc_n31_20260924/tools/freeze_manifest.py': None,
       'tools/sdmpc31/freeze_worktree.ps1': None}
out['key_files'] = {k: {'sha256': frz.get(k), 'expected_prefix': v, 'ok': (frz.get(k) or '').startswith(v) if v else frz.get(k) is not None} for k, v in KEY.items()}
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:4000])
