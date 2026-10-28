# FO tree check (2026-10-27 KST, D-K9-113). Read-only. Derived from work/b1/b1_tree_check.py (B1, D-K9-90); differences:
# the codex freeze helper is imported from FRZ_B1 (same file as in FRZ_B0), and 'diff' takes --allow-changed and --allow-extra
# lists. Uses the helper (python -B, no writes) so the file table follows exactly the freeze exclusions (.git, __pycache__,
# .pytest_cache, __tangentcache__, *.pyc, the pytest scratch dir, root FREEZE.json).
#   python -B fo_tree_check.py table <root> <out.json>
#   python -B fo_tree_check.py diff <expected.json> <actual.json> <out.json> [--allow-changed <rel>]... [--allow-extra <rel>]...
#       <expected>/<actual> = a FREEZE.json or a table json (both carry 'files'). DIFF_OK when changed == the allowed changed list
#       exactly, extra == the allowed extra list exactly, and nothing is missing; otherwise DIFF_FAIL (exit 1).
import json, sys
sys.dont_write_bytecode = True
FRZ_B1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410'
sys.path.insert(0, FRZ_B1 + '/diagnostics/sdmpc_n31_20260924/tools')
import freeze_manifest as fm  # noqa: E402


def load_files(p):
    return json.load(open(p, encoding='utf-8-sig'))['files']


def main(a):
    if len(a) == 3 and a[0] == 'table':
        table, total = fm.hash_tree(a[1])
        out = {'root': a[1], 'file_count': len(table), 'total_bytes': total, 'tree_sha256': fm.tree_sha256(table), 'files': table}
        json.dump(out, open(a[2], 'w', encoding='utf-8'), indent=None, sort_keys=True)
        print('TABLE root=%s files=%d bytes=%d tree_sha256=%s' % (a[1], len(table), total, out['tree_sha256']))
        return 0
    if len(a) >= 4 and a[0] == 'diff':
        allow_c = [a[i + 1] for i in range(4, len(a) - 1) if a[i] == '--allow-changed']
        allow_e = [a[i + 1] for i in range(4, len(a) - 1) if a[i] == '--allow-extra']
        exp, act = load_files(a[1]), load_files(a[2])
        d = fm.diff_tables(exp, act)
        ok = (not d['missing'] and sorted(d['changed']) == sorted(allow_c) and sorted(d['extra']) == sorted(allow_e))
        out = {'expected': a[1], 'actual': a[2], 'allow_changed': allow_c, 'allow_extra': allow_e,
               'changed': d['changed'], 'changed_detail': {k: {'expected': exp[k], 'actual': act[k]} for k in d['changed']},
               'missing': d['missing'], 'extra': d['extra'], 'extra_detail': {k: act[k] for k in d['extra']},
               'expected_count': len(exp), 'actual_count': len(act),
               'expected_tree_sha256': fm.tree_sha256(exp), 'actual_tree_sha256': fm.tree_sha256(act), 'ok': ok}
        json.dump(out, open(a[3], 'w', encoding='utf-8'), indent=1, sort_keys=True)
        print('%s changed=%d missing=%d extra=%d expected=%d actual=%d' % (
            'DIFF_OK' if ok else 'DIFF_FAIL', len(d['changed']), len(d['missing']), len(d['extra']), len(exp), len(act)))
        return 0 if ok else 1
    print('usage: table <root> <out> | diff <exp> <act> <out> [--allow-changed rel]... [--allow-extra rel]...', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
