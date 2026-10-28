"""ReviewDeclare A34 검토 점검 (읽기 전용, 2026-10-23). 출력은 sha·경로·개수·참거짓·설정 문자열뿐입니다.

1. VA/a34_pins.sha256 다시 대조(줄마다 sha256).
2. 승격 바이트: e27ceac8의 CFG·CFG-B1 바이트(sha256·크기·git blob)와 GWT8 작업 파일 바이트가 같은지,
   JSON 값 차이(이 파일의 raw_diff, gjudge.raw_diff와 같은 꼴) 경로·종류, 새 두 경로의 값(증거 경로·sha 문자열),
   runtime.decision_error_policy 값, 증거 파일 두 개의 바이트 sha = 값 안 evidence_sha256.
3. GB-7′ 목록: e27ceac8 gb7_allowed.py 소스를 메모리에서 실행 → R2-12를 R2-11 바로 뒤에 끼움(이유 글자 =
   보충 24 §14.3 :592 따옴표 안) → 목록 sha·항목 수·판정 표 6행·`python -B gb7_allowed.py`가 낼 줄.
   보충 34 §3.2의 이유 글자와 docstring 줄이 보충 24 글자와 같은지.
4. E_K92 네 경로가 보충 뒤 목록 A에 걸리는지(걸리면 E 조건이 무의미해짐).
5. FRZ_K8b FREEZE.json files 경로 집합 = git ls-tree -r b9734abe 경로 집합인지(동결 차이 대조의 전제).
자식 프로세스는 `git show`·`git ls-tree` 읽기뿐. 파일 쓰기는 --out 하나.
"""
import hashlib
import json
import re
import subprocess
import sys
import types
from pathlib import Path

sys.dont_write_bytecode = True
SP = Path('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
VA = SP / 'k92' / 'va'
GWT8 = Path('D:/VISSIM-merge/sim3-n31-k8')
BASE = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
K8B = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
CFG = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
ARM = 'diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json'
GB7 = 'diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py'
EXPECT_LIST = 'a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1'
FRZ_K8B = Path('D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def blob(b):
    return hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()


def git(*args):
    return subprocess.run(['git', '-C', str(GWT8)] + list(args), capture_output=True, check=True).stdout


def raw_diff(a, b, path='', out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append((f'{path}/{key}', 'presence', 'b_only' if key not in a else 'a_only'))
            else:
                raw_diff(a[key], b[key], f'{path}/{key}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'list_length', ''))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                raw_diff(x, y, f'{path}[{i}]', out)
    elif a != b or type(a) is not type(b):
        out.append((path, 'value' if type(a) is type(b) else 'type', ''))
    return out


def main(out_path):
    R = {}
    # 1. pins
    pins = (VA / 'a34_pins.sha256').read_text(encoding='utf-8').splitlines()
    bad = []
    for ln in pins:
        h, p = ln.split(' *', 1)
        q = Path(p)
        got = sha(q.read_bytes()) if q.is_file() else None
        if got != h:
            bad.append([p[-90:], h[:16], (got or 'MISSING')[:16]])
    R['pins'] = {'lines': len(pins), 'bad': bad}
    # 2. promotion bytes
    base_b, arm_b = git('show', f'{BASE}:{CFG}'), git('show', f'{BASE}:{ARM}')
    wt_base, wt_arm = (GWT8 / CFG).read_bytes(), (GWT8 / ARM).read_bytes()
    R['cfg'] = {'sha256': sha(base_b), 'blob': blob(base_b), 'size': len(base_b), 'worktree_same': wt_base == base_b,
                'crlf': base_b.count(b'\r')}
    R['arm'] = {'sha256': sha(arm_b), 'blob': blob(arm_b), 'size': len(arm_b), 'worktree_same': wt_arm == arm_b,
                'crlf': arm_b.count(b'\r')}
    A, B = json.loads(base_b.decode('utf-8')), json.loads(arm_b.decode('utf-8'))
    d = raw_diff(A, B)
    R['arm_minus_base'] = [list(x) for x in d]
    newv = {}
    for p, kind, side in d:
        cur = B
        for part in p.strip('/').split('/'):
            cur = cur[part]
        newv[p] = cur
    R['new_values'] = newv
    R['policy'] = [((A.get('runtime') or {}).get('decision_error_policy')),
                   ((B.get('runtime') or {}).get('decision_error_policy'))]
    ev = {}
    for p, v in newv.items():
        if isinstance(v, dict) and 'evidence' in v:
            fb = git('show', f"{BASE}:{v['evidence']}")
            ev[p] = {'evidence_file_sha256': sha(fb), 'pinned': v.get('evidence_sha256'),
                     'equal': sha(fb) == v.get('evidence_sha256'), 'blob': blob(fb)}
    R['evidence'] = ev
    # 3. GB-7' list
    a24 = (SP / 'K8_PREDECLARATION_AMENDMENT_24.md').read_text(encoding='utf-8').splitlines()
    a34 = (SP / 'K8_PREDECLARATION_AMENDMENT_34.md').read_text(encoding='utf-8').splitlines()
    l592 = a24[591]
    reason24 = l592[l592.index('"') + 1:l592.rindex('"')]
    l593 = a24[592]
    doc24 = l593[l593.index('"') + 1:l593.rindex('"')]
    l143 = a34[142]
    reason34 = re.search(r'글자 그대로 `([^`]+)`', l143).group(1)
    l144 = a34[143]
    doc34 = re.search(r'한 줄: `([^`]+)`', l144).group(1)
    R['reason'] = {'a24_line592_has_label': '이유 문구' in l592, 'equal_bytes': reason24 == reason34,
                   'len24': len(reason24), 'len34': len(reason34), 'sha24': sha(reason24.encode())[:16]}
    R['docline'] = {'a24': doc24, 'a34': doc34, 'a34_is_dash_a24_dot': doc34 == '- ' + doc24 + '.'}
    src = git('show', f'{BASE}:{GB7}').decode('utf-8')
    mod = types.ModuleType('gb7_base')
    exec(compile(src, 'gb7_allowed.py', 'exec'), mod.__dict__)
    R['list_before'] = {'sha': mod.list_sha256(), 'A_K8': len(mod.A_K8)}
    entries = list(mod.A_K8)
    idx = [e[0] for e in entries].index('R2-11')
    entries.insert(idx + 1, ('R2-12', 'R2', r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)', reason24))
    mod.A_K8 = tuple(entries)
    mod._COMPILED = tuple((i, r, re.compile(p)) for i, r, p, _s in mod.A_K8)
    counts = {}
    for _i, rule, _p, _s in mod.A_K8:
        counts[rule] = counts.get(rule, 0) + 1
    line = 'GB7_ALLOWED schema=%s V=%d A_K8=%d %s list_sha256=%s' % (
        mod.LIST_SCHEMA, len(mod.V), len(mod.A_K8), ' '.join('%s=%d' % kv for kv in sorted(counts.items())),
        mod.list_sha256())
    R['list_after'] = {'sha': mod.list_sha256(), 'expected': EXPECT_LIST, 'match': mod.list_sha256() == EXPECT_LIST,
                       'print_line': line}
    table = ['/diagnostics/leg_ramp_split_len_SC1001_W_out', '/diagnostics/leg_ramp_split_length_fallback',
             '/diagnostics/leg_ramp_split_req_last_SC1001_W_out', '/diagnostics/leg_ramp_split_u_on_last',
             '/diagnostics/leg_ramp_split_len_SC1001_W_out/x', '/diagnostics/leg_ramp_split_injected_RM_C10484']
    R['table'] = [[p, mod.which(p)] for p in table]
    # 4. E paths vs A
    E = ['/metadata/k92_w', '/metadata/k92_hb', '/metadata/k92_hb_seed_binding',
         '/metadata/head_discharge_floor_173_p4_e36d6761cfeac634', '/metadata/k92_w/after',
         '/metadata/k92_hb/evidence_sha256']
    R['E_in_A'] = [[p, mod.which(p)] for p in E]
    # 5. FRZ_K8b files set vs git ls-tree b9734abe
    fz = json.loads((FRZ_K8B / 'FREEZE.json').read_text(encoding='utf-8'))
    fset = set(fz['files'])
    tset = set(git('ls-tree', '-r', '--name-only', '-z', K8B).decode('utf-8').split('\0')) - {''}
    R['frz_k8b_vs_tree'] = {'files': len(fset), 'tree': len(tset), 'only_frz': sorted(fset - tset)[:20],
                            'only_tree': sorted(tset - fset)[:20], 'exclusions': fz.get('exclusions'),
                            'git': {k: fz['git'].get(k) for k in ('head', 'branch', 'status_entries')}}
    ns = git('diff', '--name-status', K8B, BASE).decode('utf-8').splitlines()
    st = {}
    for ln in ns:
        st[ln.split('\t')[0]] = st.get(ln.split('\t')[0], 0) + 1
    R['diff_b9734abe_e27ceac8'] = {'by_status': st, 'cfg_in': any(ln.endswith('\t' + CFG) for ln in ns),
                                   'gb7_in': any(ln.endswith('\t' + GB7) for ln in ns)}
    R['ALL_OK'] = (not bad and R['cfg']['worktree_same'] and R['arm']['worktree_same']
                   and sorted(p for p, _k, _s in d) == ['/urban/capacity/head_floor_seed', '/urban/sc109w_through_saturation']
                   and all(k == 'presence' and s == 'b_only' for _p, k, s in d)
                   and R['policy'] == ['hold_previous_on_exception'] * 2 and all(x['equal'] for x in ev.values())
                   and R['reason']['equal_bytes'] and R['list_after']['match']
                   and [w for _p, w in R['table']] == ['R2-12', 'R2-12', None, None, None, 'R2-11']
                   and all(w is None for _p, w in R['E_in_A'][:4]))
    Path(out_path).write_text(json.dumps(R, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')
    print(json.dumps({k: R[k] for k in ('pins', 'cfg', 'arm', 'arm_minus_base', 'policy', 'evidence', 'reason',
                                        'docline', 'list_before', 'list_after', 'table', 'E_in_A',
                                        'diff_b9734abe_e27ceac8', 'ALL_OK')}, ensure_ascii=False, indent=1))
    fr = R['frz_k8b_vs_tree']
    print('FRZ_K8B files=%d tree=%d only_frz=%s only_tree=%s exclusions=%s git=%s' % (
        fr['files'], fr['tree'], fr['only_frz'], fr['only_tree'], fr['exclusions'], fr['git']))
    print('NEW_VALUES', json.dumps(R['new_values'], ensure_ascii=False))
    print('ALL_OK' if R['ALL_OK'] else 'NOT_ALL_OK')


if __name__ == '__main__':
    main(sys.argv[1])
