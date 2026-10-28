# B1 tree check (2026-10-26, D-K9-90). Read-only. Uses the codex freeze helper of FRZ_B0 (imported, python -B, no writes)
# so the file table follows exactly the freeze exclusions (.git, __pycache__, .pytest_cache, __tangentcache__, *.pyc,
# the pytest scratch dir, root FREEZE.json).
#   python -B b1_tree_check.py table <root> <out.json>
#       file table of <root> (same walk/hash as freeze_manifest.build)
#   python -B b1_tree_check.py diff <expected.json> <actual.json> <out.json> [--allow <rel path>]...
#       <expected>/<actual> = a FREEZE.json or a table json (both carry 'files'). Prints DIFF_OK when the only
#       differences are 'changed' entries listed with --allow (each must actually differ); otherwise DIFF_FAIL.
import json, os, sys
FRZ_B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258'
sys.path.insert(0, FRZ_B0 + '/diagnostics/sdmpc_n31_20260924/tools')
import freeze_manifest as fm  # noqa: E402


def load_files(p):
    d = json.load(open(p, encoding='utf-8-sig'))
    return d['files']


def main(a):
    if len(a) == 3 and a[0] == 'table':
        table, total = fm.hash_tree(a[1])
        out = {'root': a[1], 'file_count': len(table), 'total_bytes': total, 'tree_sha256': fm.tree_sha256(table), 'files': table}
        json.dump(out, open(a[2], 'w', encoding='utf-8'), indent=None, sort_keys=True)
        print('TABLE root=%s files=%d bytes=%d tree_sha256=%s' % (a[1], len(table), total, out['tree_sha256']))
        return 0
    if len(a) >= 4 and a[0] == 'diff':
        allow = [a[i + 1] for i in range(4, len(a) - 1) if a[i] == '--allow']
        exp, act = load_files(a[1]), load_files(a[2])
        d = fm.diff_tables(exp, act)
        changed_detail = {k: {'expected': exp[k], 'actual': act[k]} for k in d['changed']}
        ok = (not d['missing'] and not d['extra'] and sorted(d['changed']) == sorted(allow))
        out = {'expected': a[1], 'actual': a[2], 'allow': allow, 'changed': d['changed'], 'changed_detail': changed_detail,
               'missing': d['missing'], 'extra': d['extra'], 'expected_count': len(exp), 'actual_count': len(act),
               'expected_tree_sha256': fm.tree_sha256(exp), 'actual_tree_sha256': fm.tree_sha256(act), 'ok': ok}
        json.dump(out, open(a[3], 'w', encoding='utf-8'), indent=1, sort_keys=True)
        print('%s changed=%d missing=%d extra=%d expected=%d actual=%d changed_list=%s' % (
            'DIFF_OK' if ok else 'DIFF_FAIL', len(d['changed']), len(d['missing']), len(d['extra']), len(exp), len(act), d['changed'][:10]))
        return 0 if ok else 1
    print(__doc__ or 'usage: table <root> <out> | diff <exp> <act> <out> [--allow rel]...', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
