"""ReviewDeclare A30: own function-text comparison of the base and new k92t driver / judge (amendment 30 sections 3.2 /
3.3), top-level constants, and the persistence constants against the amendment text.  Code only; no data.

    python -B rv_static30.py <dest.json>
"""
import ast
import json
import sys
from pathlib import Path

KB = Path(__file__).resolve().parent.parent
AD = KB / 'a30decl'
PAIRS = {'driver': (KB / 'k92t' / 'k92t.py', AD / 'k92t30.py'),
         'judge': (KB / 'k92t' / 'k92t_judge.py', AD / 'k92t30_judge.py')}
DECL = {
    'driver': {
        'same': {'now', 'log', 'sha', 'write', 'read', 'space', 'env_for', 'step', 'tool', 'must', 'git', 'copy_file',
                 'copy_tree_rec', 'table_path', '_arm_of', 'jb_copies', 'snap'},
        'changed': {'stage_jb', 'require_prev', 'stop', 'finish', 'log_md', 'main'},
        'removed': {'stage_pre', 'stage_tree', 'stage_start', 'child', 'run_child', 'job_item', 'prep_root',
                    'stage_prep', 'stage_j0', 'stage_ja', 'stage_f', 'stage_post', 'chain', 'status'},
        'new': {'wjson', 'a30_sha', 'pins_check', 'inventory', 'inv_diff', 'f_labels', 'f_inputs_check',
                'persist_argv', 'stage_check30', 'stage_seal30', 'stage_f30', 'stage_post30', 'chain30', 'status30'}},
    'judge': {
        'changed': {'cmd_f', 'main'},
        'new': {'job_counts', 'cmd_fcount', 'persistence_report'},
        'removed': set()}}


def funcs(path):
    src = path.read_bytes().replace(b'\r\n', b'\n').decode('utf-8')
    tree = ast.parse(src)
    lines = src.split('\n')
    out = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            out[node.name] = '\n'.join(lines[node.lineno - 1 - len(node.decorator_list):node.end_lineno])
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            consts[node.targets[0].id] = '\n'.join(lines[node.lineno - 1:node.end_lineno])
    return out, consts


def main():
    res = {}
    for key, (a, b) in PAIRS.items():
        fa, ca = funcs(a)
        fb, cb = funcs(b)
        same = {n for n in fa if n in fb and fa[n] == fb[n]}
        changed = {n for n in fa if n in fb and fa[n] != fb[n]}
        removed = set(fa) - set(fb)
        new = set(fb) - set(fa)
        d = DECL[key]
        row = {'n_same': len(same), 'changed': sorted(changed), 'removed': sorted(removed), 'new': sorted(new),
               'changed_eq_decl': changed == d['changed'], 'removed_eq_decl': removed == d['removed'],
               'new_eq_decl': new == d['new']}
        if 'same' in d:
            row['same_eq_decl'] = same == d['same']
        row['const_changed'] = sorted(n for n in ca if n in cb and ca[n] != cb[n])
        row['const_removed'] = sorted(set(ca) - set(cb))
        row['const_new_n'] = len(set(cb) - set(ca))
        res[key] = row
    # persistence constants of both new files = the amendment text (section 2.2)
    sys.path.insert(0, str(AD))
    sys.dont_write_bytecode = True
    import importlib.util
    spec = importlib.util.spec_from_file_location('j30', AD / 'k92t30_judge.py')
    J = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(J)
    text_vr = (1200, 1500, 1950, 2850, 3300, 3450, 4200, 4650, 5100, 5550, 5700, 6000, 6150, 6450, 6600, 6900, 7050,
               7350, 7500, 7800, 7950)
    text_overlap = (1950, 3300, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350, 7500, 7800, 7950)
    res['persist'] = {'judge_vr_eq_text': J.PERSIST_VR_STATES == text_vr, 'judge_not': list(J.PERSIST_NOT),
                      'judge_overlap_eq_text': J.PERSIST_OVERLAP == text_overlap,
                      'measured_n': len(J.PERSIST_MEASURED), 'u4_rule': all(t + 0.1 >= 900 and t + 450.1 <= 9000
                                                                            for t in text_vr),
                      'excluded_rule': all(not (t - 450 + 0.1 >= 900) for t in J.PERSIST_NOT)}
    res['ok'] = all(v for r in (res['driver'], res['judge']) for k, v in r.items() if k.endswith('_eq_decl')) and all(
        v for k, v in res['persist'].items() if isinstance(v, bool))
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('RV30_STATIC ok=%s' % res['ok'])
    print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
