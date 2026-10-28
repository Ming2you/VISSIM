# -*- coding: utf-8 -*-
"""K9-2 V-A VerifyPromote r1 독립 점검 (K8 보충 34 §3.3, 작업 지시 VerifyPromote r1).

읽기 전용입니다.
- 하는 일: git 읽기 명령(rev-parse, cat-file, ls-tree, diff, log, check-attr, ls-files, status, stash list,
  for-each-ref, config --get, hash-object(쓰기 -w 없음), ls-remote)과 파일 읽기뿐. GIT_OPTIONAL_LOCKS=0으로
  status가 색인을 고쳐 쓰지 않게 합니다. GWT8 작업 트리·.git·동결본에 쓰지 않습니다.
- import하지 않는 것: make_config_n31.py, gb7_allowed.py, build_obs150_detectors.py, Promote 단계 스크립트
  (p5_json_diff.py, p7_edit.py, p7_checks.py). gb7_allowed.py는 git blob 소스를 자료로 읽어 ast로 상수만
  평가하고, canonical() 규칙(정렬 키, ensure_ascii=False, 구분자 (',', ':'), UTF-8 바이트 sha256)은 여기서
  따로 짭니다. 그 규칙이 소스의 규칙과 같은지는 (가) 소스 canonical()/list_sha256() AST가 e27ceac8과 같음,
  (나) 같은 규칙으로 낸 e27ceac8 목록 sha가 알려진 값 f954c2b0…와 같음으로 따로 확인합니다.
- 기대값은 보충 34(고정 sha a05592d4…205e) §3.1–§3.3, 보충 24(d46db6dc…) §14.3, Promote 기록의 커밋 sha에서
  옮겼고, 이 파일을 처음 돌리기 전에 sha256을 고정합니다.
- 쓰는 곳: --out JSON 하나와 표준 출력뿐.
- 끝 줄: 핵심 점검(CORE)이 모두 참이면 V_PROMOTE_CORE_ALL_OK, 아니면 V_PROMOTE_CORE_FAIL. 덧붙인 점검(EXTRA,
  보충 34가 요구하지 않은 것)은 따로 V_PROMOTE_EXTRA_ALL_OK / V_PROMOTE_EXTRA_FAIL.
"""
import argparse
import ast
import datetime
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys

GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
SP = ('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
      '491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
A24_FILE = SP + '/K8_PREDECLARATION_AMENDMENT_24.md'
A34_FILE = SP + '/K8_PREDECLARATION_AMENDMENT_34.md'
PROMOTE_DIR = SP + '/k92/va/promote'
WORK_DIR = SP + '/k92/va/work'

BRANCH = 'claude/k92-b1-20261016'
K8_BRANCH = 'claude/k8-sc1001eb-defects-20261004'
K8 = 'b9734abe1c83f95c9cec5fca5e42b7b18cd45991'
K926 = '11d99c2a4790f2bed1a610054e322ffff0253bc1'   # Promote 기록 값(여기서 git과 대조)
K927 = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'   # Promote 기록 값(여기서 git과 대조)
OLD6 = [  # (sha, 제목 앞머리) K9-2-5 … K9-2-0
    ('e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d', 'K9-2-5:'),
    ('bfd609c03a17b6f1ced27dd235f9ffe9634b4e0d', 'K9-2-4:'),
    ('b887f99f2f8441b6aa88c8633dff778c0fade91e', 'K9-2-3:'),
    ('2d5d95f05f83b06f841ac4f3ace46056f9ba3b2b', 'K9-2-2:'),
    ('7ed49cdfb548a0b82a8615f59a6650869de7c908', 'K9-2-1:'),
    ('1868b37cada2f44028c303cff445872dfa0bd42a', 'K9-2-0:'),
]
K925 = OLD6[0][0]
K923 = OLD6[2][0]
WHO = 'Ming2you <alsrjsrb1915@snu.ac.kr>'
TRAILER = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
SUBJ926 = ('K9-2-6: promote the bundle-1 arm config_n31_v2_k92b1.json bytes to config_n31_v2.json '
           '(V-A, runtime unchanged)')
SUBJ927 = ("K9-2-7: GB-7' allowed list entry R2-12 (leg_ramp_split length keys; amendment 24 section 14.3, "
           "D-K9-38 (4); diagnostics only)")

CFG = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
ARM = 'diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json'
GB7 = 'diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py'
EV_W = 'diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json'
EV_H = 'diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json'

A34_SHA = 'a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e'
A24_SHA = 'd46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc'
CFG_NEW_SHA = 'c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866'
CFG_NEW_BLOB = 'b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c'
CFG_NEW_SIZE = 278607
CFG_OLD_BLOB = '268ae47132443a4a97e87ffa51ca7f7f0c878586'
CFG_OLD_SHA_HEAD, CFG_OLD_SHA_TAIL = 'd0f9ef39', 'aec6'
CFG_OLD_SIZE = 278142
EV_W_SHA = 'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712'
EV_W_BLOB = '0399c3699c626e8bc33adc4180ce716873d8e4a1'
EV_H_SHA = 'b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee'
EV_H_BLOB = '6ed42f162c71d87520fa1849c70fc80b385646a3'
W_VALUE_REPR = '5209.8'
S_VALUE_REPR = '1045.1612903225805'
POLICY = 'hold_previous_on_exception'
TWO_PATHS = ['/urban/capacity/head_floor_seed', '/urban/sc109w_through_saturation']

GB7_OLD_BLOB = '9fd7d5194081a089298444351072a2d058af5aef'
GB7_OLD_SHA = 'c6f9ca1cbf1e1ac49f1bc7adf44e33add289fea5858be8f5884c7225753894c8'
GB7_OLD_SIZE = 11304
GB7_NEW_SHA = '61c70c222cf3bed2a0a299b539aa3fccad288c059b72be678cceda2c3dc6f319'  # Promote 기록 값
GB7_NEW_BLOB = '1ca72d81f6e63736fa835cd408c9c9d6b7563ffa'                        # Promote 기록 값
LIST_SHA_OLD_HEAD = 'f954c2b0'   # 보충 24 §14.3 :590
LIST_SHA_NEW = 'a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1'
PRINT_LINE = ('GB7_ALLOWED schema=k8-gb7-allowed/v1 V=7 A_K8=35 R1=16 R2=12 R3=7 list_sha256=' + LIST_SHA_NEW)
R2_12_PATTERN = r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)'
REASON_LEN = 117
REASON_SHA_HEAD = '7a51c150f6bc3cc4'
DOC_ANCHOR_PREFIX = '  A 밖 경로가 하나라도 다르면'
TABLE = [  # (경로, 보충 전 which, 보충 뒤 which)  보충 24 §14.3 표
    ('/diagnostics/leg_ramp_split_len_SC1001_W_out', None, 'R2-12'),
    ('/diagnostics/leg_ramp_split_length_fallback', None, 'R2-12'),
    ('/diagnostics/leg_ramp_split_req_last_SC1001_W_out', None, None),
    ('/diagnostics/leg_ramp_split_u_on_last', None, None),
    ('/diagnostics/leg_ramp_split_len_SC1001_W_out/x', None, None),
    ('/diagnostics/leg_ramp_split_injected_RM_C10484', 'R2-11', 'R2-11'),
]
E_PATHS = ['/metadata/k92_w', '/metadata/k92_hb', '/metadata/k92_hb_seed_binding',
           '/metadata/head_discharge_floor_173_p4_e36d6761cfeac634']
RUNTIME_DIRS = ['evaluation', 'vendor', 'plant', 'scripts']
PROMOTE_START = datetime.datetime(2026, 10, 23, 7, 59, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

CHECKS = []


def check(name, ok, detail, kind='CORE'):
    CHECKS.append({'name': name, 'kind': kind, 'ok': bool(ok), 'detail': detail})
    print('%s %-5s %s :: %s' % ('OK  ' if ok else 'FAIL', kind, name, json.dumps(detail, ensure_ascii=False)))


def git(*args, ok_codes=(0,), timeout=120):
    env = dict(os.environ)
    env['GIT_OPTIONAL_LOCKS'] = '0'
    env['GIT_TERMINAL_PROMPT'] = '0'
    p = subprocess.run(['git', '-C', GWT8, '-c', 'core.quotepath=off'] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)
    if p.returncode not in ok_codes:
        raise RuntimeError('git %s -> %d %s' % (' '.join(args), p.returncode, p.stderr.decode('utf-8', 'replace')))
    return p.returncode, p.stdout


def gtext(*args, **kw):
    return git(*args, **kw)[1].decode('utf-8')


def blob(rev, path):
    return git('cat-file', 'blob', '%s:%s' % (rev, path))[1]


def blob_id(rev, path):
    return gtext('rev-parse', '%s:%s' % (rev, path)).strip()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def git_blob_sha1(b):
    return hashlib.sha1(b'blob %d\x00' % len(b) + b).hexdigest()


def no_dup_pairs(pairs):
    seen = set()
    for k, _v in pairs:
        if k in seen:
            raise ValueError('duplicate JSON key %r' % k)
        seen.add(k)
    return dict(pairs)


def deep_diff(a, b, path, out):
    if type(a) is not type(b):
        out.append((path, 'type'))
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            kp = path + '/' + k
            if k not in a:
                out.append((kp, 'new_only'))
            elif k not in b:
                out.append((kp, 'old_only'))
            else:
                deep_diff(a[k], b[k], kp, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path, 'len'))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            deep_diff(x, y, '%s[%d]' % (path, i), out)
    elif repr(a) != repr(b):
        out.append((path, 'value'))


# ---------------------------------------------------------------- gb7 소스를 자료로 읽기 (import 없음)
def const_eval(node, env):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(const_eval(e, env) for e in node.elts)
    if isinstance(node, ast.List):
        return [const_eval(e, env) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {const_eval(k, env): const_eval(v, env) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = const_eval(node.left, env), const_eval(node.right, env)
        if not (isinstance(left, str) and isinstance(right, str)):
            raise ValueError('non-str add')
        return left + right
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    raise ValueError('unsupported node %s line %s' % (type(node).__name__, getattr(node, 'lineno', '?')))


def read_list(src_bytes):
    text = src_bytes.decode('utf-8')
    tree = ast.parse(text)
    env, nodes, funcs = {}, {}, {}
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            name = st.targets[0].id
            if name in ('LIST_SCHEMA', 'SCAN', 'V', '_SUB', 'A_K8'):
                env[name] = const_eval(st.value, env)
                nodes[name] = st.value
        if isinstance(st, ast.FunctionDef):
            funcs[st.name] = ast.dump(st, include_attributes=False)
        if isinstance(st, ast.If) and isinstance(st.test, ast.Compare) and isinstance(st.test.left, ast.Name) \
                and st.test.left.id == '__name__':
            funcs['__main__block'] = ast.dump(st, include_attributes=False)
    doc = ast.get_docstring(tree, clean=False)
    return {'text': text, 'env': env, 'nodes': nodes, 'funcs': funcs, 'doc': doc, 'tree': tree}


def canonical_sha(env):
    doc = {'schema': env['LIST_SCHEMA'], 'scan': env['SCAN'], 'V': list(env['V']),
           'A_K8': [list(e) for e in env['A_K8']]}
    s = json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return sha256(s.encode('utf-8'))


def which(env, path):
    if path in set(env['V']):
        return 'V'
    for entry_id, _rule, pattern, _src in env['A_K8']:
        if re.fullmatch(pattern, path):
            return entry_id
    return None


def quoted(line):
    i, j = line.index('"'), line.rindex('"')
    return line[i + 1:j]


def backticked_after(line, marker):
    k = line.index(marker) + len(marker)
    i = line.index('`', k)
    j = line.index('`', i + 1)
    return line[i + 1:j]


def parse_commit(sha):
    raw = git('cat-file', 'commit', sha)[1].decode('utf-8')
    head, _, msg = raw.partition('\n\n')
    hdr = {}
    for ln in head.split('\n'):
        k, _, v = ln.partition(' ')
        hdr.setdefault(k, []).append(v)
    return hdr, msg


def person(v):
    m = re.match(r'^(.*) (\d+) ([+-]\d{4})$', v)
    return m.group(1), int(m.group(2)), m.group(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    # ------------------------------------------------------------ 0. 근거 문서
    a34 = open(A34_FILE, 'rb').read()
    a24 = open(A24_FILE, 'rb').read()
    check('0.a34_sha', sha256(a34) == A34_SHA, sha256(a34))
    check('0.a24_sha', sha256(a24) == A24_SHA, sha256(a24))
    a34l = a34.decode('utf-8').split('\n')
    a24l = a24.decode('utf-8').split('\n')
    s926 = backticked_after(a34l[135], '첫 줄(고정): ')
    s927 = backticked_after(a34l[153], '첫 줄(고정): ')
    check('0.subjects_from_a34', s926 == SUBJ926 and s927 == SUBJ927, {'a34_136': s926, 'a34_154': s927})
    reason = quoted(a24l[591])
    docq = quoted(a24l[592])
    rsha = sha256(reason.encode('utf-8'))
    check('0.reason_a24_592', len(reason) == REASON_LEN and rsha.startswith(REASON_SHA_HEAD),
          {'len': len(reason), 'sha256': rsha})
    docline = '- ' + docq + '.'

    # ------------------------------------------------------------ 1. 커밋 목록·위생
    _, lg = git('log', '--format=%H%x00%P%x00%an%x00%ae%x00%cn%x00%ce%x00%s', '%s..HEAD' % K8)
    rows = [r.split('\x00') for r in lg.decode('utf-8').strip().split('\n')]
    shas = [r[0] for r in rows]
    exp = [K927, K926] + [s for s, _ in OLD6]
    check('1.log_8_in_order', shas == exp, shas)
    chain_ok = all(rows[i][1] == (exp[i + 1] if i + 1 < len(exp) else K8) for i in range(len(rows)))
    check('1.linear_single_parents', chain_ok, [r[1] for r in rows])
    who_ok = all('%s <%s>' % (r[2], r[3]) == WHO and '%s <%s>' % (r[4], r[5]) == WHO for r in rows)
    check('1.author_committer_all8', who_ok, sorted({'%s <%s>|%s <%s>' % (r[2], r[3], r[4], r[5]) for r in rows}))
    subj_ok = rows[0][6] == SUBJ927 and rows[1][6] == SUBJ926 and all(
        rows[2 + i][6].startswith(p) for i, (_s, p) in enumerate(OLD6))
    check('1.subjects', subj_ok, [r[6][:60] for r in rows])
    trailer_rows = {}
    for s in exp:
        hdr, msg = parse_commit(s)
        lines = msg.rstrip('\n').split('\n')
        a_name, a_t, a_tz = person(hdr['author'][0])
        c_name, c_t, c_tz = person(hdr['committer'][0])
        trailer_rows[s[:8]] = {
            'last_line_trailer': lines[-1] == TRAILER,
            'trailer_count': msg.count('Co-Authored-By:'),
            'blank_before_trailer': len(lines) >= 2 and lines[-2] == '',
            'ends_newline': msg.endswith('\n'),
            'parents': len(hdr.get('parent', [])),
            'extra_headers': sorted(k for k in hdr if k not in ('tree', 'parent', 'author', 'committer')),
            'author_eq_committer_time': (a_t, a_tz) == (c_t, c_tz),
        }
    new2_ok = all(trailer_rows[s[:8]]['last_line_trailer'] and trailer_rows[s[:8]]['trailer_count'] == 1
                  and trailer_rows[s[:8]]['ends_newline'] and trailer_rows[s[:8]]['parents'] == 1
                  and trailer_rows[s[:8]]['extra_headers'] == [] for s in (K926, K927))
    check('1.new2_trailer_hygiene', new2_ok, {k: trailer_rows[k] for k in (K926[:8], K927[:8])})
    all8_ok = all(v['last_line_trailer'] for v in trailer_rows.values())
    check('1.all8_last_line_trailer(§4.1)', all8_ok, {k: v['last_line_trailer'] for k, v in trailer_rows.items()},
          kind='EXTRA')
    # 본문 요소(§3.1·§3.2)
    _h6, m6 = parse_commit(K926)
    _h7, m7 = parse_commit(K927)
    body6 = {
        'new_sha': CFG_NEW_SHA in m6, 'new_blob': CFG_NEW_BLOB in m6, 'new_size': '278,607' in m6,
        'old_sha_head': CFG_OLD_SHA_HEAD in m6, 'old_blob': CFG_OLD_BLOB in m6,
        'two_paths': all(p in m6 for p in ['/urban/sc109w_through_saturation', '/urban/capacity/head_floor_seed']),
        'evidence_sha': 'b4b7294d' in m6 and 'b9fa1d01' in m6, 'policy': POLICY in m6,
        'step1_phrase': 'make_config --k92b1 --check run on the clean K9-2-5 tree before the byte copy (D-K9-72)' in m6,
        'D-K9-67': 'D-K9-67' in m6, 'D-K9-72': 'D-K9-72' in m6, 'a34_sha': A34_SHA in m6,
    }
    check('1.k926_body_items(§3.1)', all(body6.values()), body6)
    body7 = {
        'list_sha': LIST_SHA_NEW in m7, 'file_sha': GB7_NEW_SHA in m7, 'file_blob': GB7_NEW_BLOB in m7,
        'after_result_D-K9-38_4': 'after seeing replay output' in m7 and 'D-K9-38 (4)' in m7,
        'D-K9-12_not_reapplied': 'D-K9-12 exception' in m7 and 'not re-applied' in m7, 'a34_sha': A34_SHA in m7,
    }
    check('1.k927_body_items(§3.2)', all(body7.values()), body7)
    # Promote 메시지 파일과 바이트 대조(자료로만)
    mf = {}
    for s, fn in ((K926, 'msg_k926.txt'), (K927, 'msg_k927.txt')):
        _h, m = parse_commit(s)
        fb = open(PROMOTE_DIR + '/' + fn, 'rb').read()
        mf[fn] = {'equal': fb == m.encode('utf-8'), 'file_sha256': sha256(fb)}
    check('1.msg_files_equal_commit_messages', all(v['equal'] for v in mf.values()), mf, kind='EXTRA')

    # ------------------------------------------------------------ 2. diff 범위·K8 가지
    def raw(a, b, *paths):
        out = gtext('diff', '--raw', '-r', '--no-renames', '--no-abbrev', a, b, '--', *paths).strip()
        return [ln for ln in out.split('\n') if ln]
    r_all = raw(K925, K927)
    r_6 = raw(K925, K926)
    r_7 = raw(K926, K927)
    exp_all = [':100644 100644 %s %s M\t%s' % (CFG_OLD_BLOB, CFG_NEW_BLOB, CFG),
               ':100644 100644 %s %s M\t%s' % (GB7_OLD_BLOB, GB7_NEW_BLOB, GB7)]
    check('2.diff_e27ceac8_K927', sorted(r_all) == sorted(exp_all), r_all)
    check('2.diff_e27ceac8_K926', r_6 == [exp_all[0]], r_6)
    check('2.diff_K926_K927', r_7 == [exp_all[1]], r_7)
    rt_dirs_present = [d for d in RUNTIME_DIRS
                       if gtext('ls-tree', '-d', '--name-only', K927, d).strip() == d]
    rt = gtext('diff', '--name-status', K925, K927, '--', *RUNTIME_DIRS).strip()
    rt_head = gtext('diff', '--name-status', K925, 'HEAD', '--', 'evaluation', 'vendor').strip()
    check('2.runtime_dirs_unchanged', rt == '' and rt_head == '',
          {'present_dirs': rt_dirs_present, 'diff_e27_K927_eval_vendor_plant_scripts': rt,
           'diff_e27_HEAD_eval_vendor': rt_head})
    k8_local = gtext('rev-parse', 'refs/heads/' + K8_BRANCH).strip()
    k8_track = gtext('rev-parse', 'refs/remotes/origin/' + K8_BRANCH).strip()
    check('2.k8_branch_local_and_tracking', k8_local == K8 and k8_track == K8, [k8_local, k8_track])

    # ------------------------------------------------------------ 3. CFG 승격 바이트·JSON 차이
    old_b = blob(K925, CFG)
    new_b = blob(K926, CFG)
    new_b7 = blob(K927, CFG)
    arm_925 = blob(K925, ARM)
    arm_927 = blob(K927, ARM)
    ids = {
        'e27_CFG': blob_id(K925, CFG), 'K926_CFG': blob_id(K926, CFG), 'K927_CFG': blob_id(K927, CFG),
        'K923_ARM': blob_id(K923, ARM), 'e27_ARM': blob_id(K925, ARM), 'K927_ARM': blob_id(K927, ARM),
    }
    own = {'e27_CFG': git_blob_sha1(old_b), 'K926_CFG': git_blob_sha1(new_b), 'e27_ARM': git_blob_sha1(arm_925)}
    check('3.cfg_blob_ids', ids['e27_CFG'] == CFG_OLD_BLOB and ids['K926_CFG'] == CFG_NEW_BLOB
          and ids['K927_CFG'] == CFG_NEW_BLOB and own['K926_CFG'] == CFG_NEW_BLOB and own['e27_CFG'] == CFG_OLD_BLOB,
          {'git': ids, 'own_sha1': own})
    check('3.arm_unchanged_K923_to_K927', ids['K923_ARM'] == ids['e27_ARM'] == ids['K927_ARM'] == CFG_NEW_BLOB
          and own['e27_ARM'] == CFG_NEW_BLOB, ids)
    check('3.cfg_new_bytes', sha256(new_b) == CFG_NEW_SHA and len(new_b) == CFG_NEW_SIZE and new_b == arm_925
          and new_b == arm_927 and new_b == new_b7 and new_b.count(b'\r') == 0 and not new_b.startswith(b'\xef\xbb\xbf'),
          {'sha256': sha256(new_b), 'size': len(new_b), 'eq_arm_e27': new_b == arm_925, 'CR': new_b.count(b'\r')})
    osha = sha256(old_b)
    check('3.cfg_old_bytes', osha.startswith(CFG_OLD_SHA_HEAD) and osha.endswith(CFG_OLD_SHA_TAIL)
          and len(old_b) == CFG_OLD_SIZE and old_b.count(b'\r') == 0, {'sha256': osha, 'size': len(old_b)})
    jo = json.loads(old_b.decode('utf-8'), object_pairs_hook=no_dup_pairs)
    jn = json.loads(new_b.decode('utf-8'), object_pairs_hook=no_dup_pairs)
    dd = []
    deep_diff(jo, jn, '', dd)
    check('3.json_diff_exactly_two_new_only', dd == [(p, 'new_only') for p in TWO_PATHS], dd)
    vw = jn['urban']['sc109w_through_saturation']
    vh = jn['urban']['capacity']['head_floor_seed']
    ev = {}
    for tag, v, path, esha, eblob in (('W', vw, EV_W, EV_W_SHA, EV_W_BLOB), ('Hb', vh, EV_H, EV_H_SHA, EV_H_BLOB)):
        eb = blob(K926, path)
        eb7 = blob(K927, path)
        wt = open(os.path.join(GWT8, path), 'rb').read()
        ev[tag] = {
            'keys': sorted(v.keys()), 'evidence_path_ok': v.get('evidence') == path,
            'declared_sha': v.get('evidence_sha256'), 'blob_sha256': sha256(eb), 'worktree_sha256': sha256(wt),
            'blob_id': blob_id(K926, path), 'eq_K927': eb == eb7,
        }
        ev[tag]['ok'] = (ev[tag]['keys'] == ['evidence', 'evidence_sha256'] and ev[tag]['evidence_path_ok']
                         and v.get('evidence_sha256') == esha == sha256(eb) == sha256(wt)
                         and ev[tag]['blob_id'] == eblob and ev[tag]['eq_K927'])
    check('3.two_values_and_evidence_sha', ev['W']['ok'] and ev['Hb']['ok'], ev)
    pol = (jo.get('runtime', {}).get('decision_error_policy'), jn.get('runtime', {}).get('decision_error_policy'))
    check('3.policy_key_both', pol == (POLICY, POLICY), pol)
    # 덧붙임: 증거 파일의 값(지정한 잎만 읽음)
    ew = json.loads(blob(K926, EV_W).decode('utf-8'))['values']
    eh = json.loads(blob(K926, EV_H).decode('utf-8'))['values']
    vals = {'W.capacity_veh_h': repr(ew.get('capacity_veh_h')), 'W.capacity_repr': ew.get('capacity_repr'),
            'Hb.seed': repr(eh.get('seed')), 'Hb.seed_repr': eh.get('seed_repr')}
    check('3.evidence_values', vals['W.capacity_veh_h'] == W_VALUE_REPR and vals['Hb.seed'] == S_VALUE_REPR, vals,
          kind='EXTRA')

    # ------------------------------------------------------------ 4. gb7_allowed.py
    g_old = blob(K925, GB7)
    g_6 = blob(K926, GB7)
    g_new = blob(K927, GB7)
    gid = {'e27': blob_id(K925, GB7), 'K926': blob_id(K926, GB7), 'K927': blob_id(K927, GB7)}
    check('4.gb7_blob_ids', gid['e27'] == GB7_OLD_BLOB == gid['K926'] == git_blob_sha1(g_6)
          and gid['K927'] == GB7_NEW_BLOB == git_blob_sha1(g_new) and sha256(g_old) == GB7_OLD_SHA
          and len(g_old) == GB7_OLD_SIZE and g_6 == g_old, gid)
    check('4.gb7_new_bytes', sha256(g_new) == GB7_NEW_SHA and g_new.count(b'\r') == 0
          and not g_new.startswith(b'\xef\xbb\xbf') and g_new.endswith(b'\n'),
          {'sha256': sha256(g_new), 'size': len(g_new), 'CR': g_new.count(b'\r')})
    lo = read_list(g_old)
    ln_ = read_list(g_new)
    eo, en = lo['env'], ln_['env']
    sha_old = canonical_sha(eo)
    sha_new = canonical_sha(en)
    check('4.own_canonical_rule_matches_module(e27=f954c2b0…, funcs same)',
          sha_old.startswith(LIST_SHA_OLD_HEAD)
          and all(lo['funcs'].get(f) == ln_['funcs'].get(f) and f in lo['funcs']
                  for f in ('canonical', 'list_sha256', 'which', 'allowed', 'outside', '__main__block')),
          {'list_sha_e27': sha_old, 'funcs_present': sorted(ln_['funcs'])})
    counts = {}
    for _id, rule, _p, _s in en['A_K8']:
        counts[rule] = counts.get(rule, 0) + 1
    line = 'GB7_ALLOWED schema=%s V=%d A_K8=%d %s list_sha256=%s' % (
        en['LIST_SCHEMA'], len(en['V']), len(en['A_K8']), ' '.join('%s=%d' % kv for kv in sorted(counts.items())),
        sha_new)
    check('4.list_sha_and_counts', sha_new == LIST_SHA_NEW and line == PRINT_LINE,
          {'list_sha': sha_new, 'line': line})
    p7 = open(PROMOTE_DIR + '/p7_check3_gb7_main.out.txt', 'rb').read().decode('utf-8').strip()
    check('4.promote_print_line_record_equal', p7 == PRINT_LINE, p7, kind='EXTRA')
    ids_new = [e[0] for e in en['A_K8']]
    k = ids_new.index('R2-12') if 'R2-12' in ids_new else -1
    r212 = en['A_K8'][k] if k >= 0 else None
    struct = {
        'ids_unique': len(set(ids_new)) == len(ids_new),
        'old_plus_one_same_order': [e for e in en['A_K8'] if e[0] != 'R2-12'] == list(eo['A_K8']),
        'R2-12_right_after_R2-11': k > 0 and ids_new[k - 1] == 'R2-11',
        'R2-12_count': ids_new.count('R2-12'),
        'R2-12_rule': r212 is not None and r212[1] == 'R2',
        'R2-12_pattern': r212 is not None and r212[2] == R2_12_PATTERN,
        'R2-12_reason_eq_a24_592': r212 is not None and r212[3] == reason,
        'V_SCAN_SCHEMA_SUB_same': all(eo[x] == en[x] for x in ('V', 'SCAN', 'LIST_SCHEMA', '_SUB')),
        'V_len': len(en['V']),
    }
    check('4.r2_12_entry', all(v is True for kk, v in struct.items() if kk not in ('R2-12_count', 'V_len'))
          and struct['R2-12_count'] == 1 and struct['V_len'] == 7, struct)
    # 판정 표 6행, E 경로
    tab = [(p, which(eo, p), which(en, p)) for p, _b, _a in TABLE]
    check('4.judgement_table_6_rows', [(p, b, a) for p, b, a in tab] == TABLE, tab)
    ein = {p: (which(eo, p), which(en, p)) for p in E_PATHS}
    check('4.E_K92_paths_outside_A', all(v == (None, None) for v in ein.values()), ein)
    # 줄 단위 바이트 범위
    ol = g_old.decode('utf-8').split('\n')
    nl = g_new.decode('utf-8').split('\n')
    sm = difflib.SequenceMatcher(None, ol, nl, autojunk=False)
    ops = [op for op in sm.get_opcodes() if op[0] != 'equal']
    anchor = [i for i, s in enumerate(ol) if s.startswith(DOC_ANCHOR_PREFIX)]
    a_k8_node_old = lo['nodes']['A_K8']
    r211_end = [e.end_lineno for e in a_k8_node_old.elts
                if isinstance(e, ast.Tuple) and isinstance(e.elts[0], ast.Constant) and e.elts[0].value == 'R2-11']
    r212_node = [e for e in ln_['nodes']['A_K8'].elts
                 if isinstance(e, ast.Tuple) and isinstance(e.elts[0], ast.Constant) and e.elts[0].value == 'R2-12']
    rng = {'ops': ops, 'anchor_idx': anchor, 'r211_end_lineno': r211_end}
    ok_rng = (len(ops) == 2 and all(op[0] == 'insert' for op in ops) and len(anchor) == 1 and len(r211_end) == 1
              and len(r212_node) == 1)
    if ok_rng:
        (t1, i1, _i2, j1, j2), (t2, k1, _k2, l1, l2) = ops
        ins1 = nl[j1:j2]
        ins2 = nl[l1:l2]
        rng.update({'ins1': ins1, 'ins2_lines': l2 - l1, 'ins2_new_linenos': [l1 + 1, l2],
                    'r212_node_lines': [r212_node[0].lineno, r212_node[0].end_lineno]})
        ok_rng = (i1 == anchor[0] + 1 and ins1 == [docline]
                  and k1 == r211_end[0] and 1 <= (l2 - l1) <= 3
                  and r212_node[0].lineno == l1 + 1 and r212_node[0].end_lineno == l2
                  and nl.count(docline) == 1)
    check('4.byte_range_insert_only(docline+R2-12)', ok_rng, rng)
    ns = gtext('diff', '--numstat', K926, K927, '--', GB7).strip()
    check('4.numstat_+3_-0', ns == '3\t0\t' + GB7, ns)
    # 덧붙임: docstring 줄 위치가 docstring 안
    check('4.docline_inside_docstring', (docline + '\n') in (ln_['doc'] or '') or (ln_['doc'] or '').endswith(docline + '\n'),
          {'docline': docline}, kind='EXTRA')

    # ------------------------------------------------------------ 5. 작업 트리
    head = gtext('rev-parse', 'HEAD').strip()
    sym = gtext('symbolic-ref', 'HEAD').strip()
    st = gtext('status', '--porcelain=v1', '-uall').strip()
    cached = gtext('diff', '--cached', '--name-only').strip()
    stash = gtext('stash', 'list').strip()
    check('5.head_branch_status', head == K927 and sym == 'refs/heads/' + BRANCH and st == '' and cached == ''
          and stash == '', {'HEAD': head, 'symref': sym, 'status_lines': len(st.split('\n')) if st else 0,
                            'cached': cached, 'stash': stash})
    wt = {}
    for path, exp_blob in ((CFG, CFG_NEW_BLOB), (GB7, GB7_NEW_BLOB), (ARM, CFG_NEW_BLOB)):
        b = open(os.path.join(GWT8, path), 'rb').read()
        ho = gtext('hash-object', '--no-filters', '--', path).strip()
        lt = gtext('ls-tree', 'HEAD', '--', path).split()[2]
        attr = gtext('check-attr', 'text', '--', path).strip()
        eol = gtext('ls-files', '--eol', '--', path).strip()
        wt[path] = {'hash_object': ho, 'own_sha1': git_blob_sha1(b), 'ls_tree': lt, 'attr': attr,
                    'eol': ' '.join(eol.split()[:3])}
        wt[path]['ok'] = (ho == lt == git_blob_sha1(b) == exp_blob and attr.endswith(': text: unset')
                          and wt[path]['eol'] == 'i/lf w/lf attr/-text')
    check('5.worktree_blobs_eq_ls_tree_and_attrs', all(v['ok'] for v in wt.values()), wt)
    # 남은 파일: Promote 시작(07:59 KST) 뒤 바뀐 파일(.git 제외)
    thr = PROMOTE_START.timestamp()
    late = []
    walked = 0
    for root, dirs, files in os.walk(GWT8):
        dirs[:] = [d for d in dirs if d != '.git']
        for f in files:
            if root == GWT8 and f == '.git':
                continue
            walked += 1
            fp = os.path.join(root, f)
            try:
                if os.stat(fp).st_mtime >= thr:
                    late.append(os.path.relpath(fp, GWT8).replace('\\', '/'))
            except OSError:
                pass
    check('5.no_stray_files_since_0759', sorted(late) == sorted([CFG, GB7]), {'late': sorted(late), 'walked': walked})
    ign = gtext('status', '--porcelain=v1', '--ignored', '-uall').strip()
    ign_lines = [x for x in ign.split('\n') if x]
    check('5.ignored_only_lines', all(x.startswith('!! ') for x in ign_lines),
          {'ignored_count': len(ign_lines)}, kind='EXTRA')
    rc, hp = git('config', '--get', 'core.hooksPath', ok_codes=(0, 1))
    common = gtext('rev-parse', '--git-common-dir').strip()
    if not os.path.isabs(common):
        common = os.path.join(GWT8, common)
    hooks_dir = os.path.join(common, 'hooks')
    hooks = sorted(f for f in (os.listdir(hooks_dir) if os.path.isdir(hooks_dir) else []) if not f.endswith('.sample'))
    check('5.no_hooks', rc == 1 and hooks == [], {'hooksPath_rc': rc, 'non_sample_hooks': hooks}, kind='EXTRA')

    # ------------------------------------------------------------ 6. 푸시 없음
    up_rc, _ = git('config', '--get', 'branch.%s.remote' % BRANCH, ok_codes=(0, 1))
    track = gtext('for-each-ref', '--format=%(refname)', 'refs/remotes/').split('\n')
    track_k92 = [t for t in track if 'k92' in t]
    pts = {s[:8]: [r for r in gtext('for-each-ref', '--points-at', s, '--format=%(refname)').split('\n') if r]
           for s in (K926, K927)}
    lr = gtext('ls-remote', 'origin', timeout=180)
    lr_rows = [x.split('\t') for x in lr.strip().split('\n') if x]
    lr_k92 = [r for r in lr_rows if 'k92' in r[1]]
    lr_new = [r for r in lr_rows if r[0] in (K926, K927)]
    lr_k8 = [r[0] for r in lr_rows if r[1] == 'refs/heads/' + K8_BRANCH]
    check('6.not_pushed', up_rc == 1 and track_k92 == [] and lr_k92 == [] and lr_new == []
          and pts[K926[:8]] == [] and pts[K927[:8]] == ['refs/heads/' + BRANCH],
          {'upstream_rc': up_rc, 'tracking_k92': track_k92, 'ls_remote_k92': lr_k92, 'ls_remote_new_sha': lr_new,
           'local_refs_at': pts, 'ls_remote_rows': len(lr_rows)})
    check('6.k8_remote_unchanged', lr_k8 == [K8], lr_k8)

    # ------------------------------------------------------------ 7. Promote 기록 출력(자료) 대 첫 Declare 출력
    rec = {}
    for a, b in (('pre_edit_mkcfg_k92b1_check.out.txt', 'pre_mkcfg_k92b1_check.out.txt'),
                 ('post_copy_obs150_check.out.txt', 'pre_obs150_arm_check.out.txt')):
        pa = open(PROMOTE_DIR + '/' + a, 'rb').read()
        pb = open(WORK_DIR + '/' + b, 'rb').read()
        rec[a] = {'eq_declare_output': pa == pb, 'sha256': sha256(pa), 'lines': pa.count(b'\n')}
    errs = {f: os.path.getsize(PROMOTE_DIR + '/' + f) for f in os.listdir(PROMOTE_DIR) if f.endswith('.err.txt')}
    check('7.promote_check_outputs_eq_declare_and_err_empty',
          all(v['eq_declare_output'] and v['lines'] == 1 for v in rec.values()) and all(v == 0 for v in errs.values()),
          {'outputs': rec, 'err_sizes': errs}, kind='EXTRA')

    core = [c for c in CHECKS if c['kind'] == 'CORE']
    extra = [c for c in CHECKS if c['kind'] == 'EXTRA']
    res = {
        'schema': 'k92-va-verify-promote/v1', 'gwt8_head': head, 'k926': K926, 'k927': K927,
        'list_sha_new': sha_new, 'list_sha_e27': sha_old,
        'core_total': len(core), 'core_ok': sum(c['ok'] for c in core),
        'extra_total': len(extra), 'extra_ok': sum(c['ok'] for c in extra), 'checks': CHECKS,
    }
    with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write('\n')
    print('CORE %d/%d EXTRA %d/%d' % (res['core_ok'], res['core_total'], res['extra_ok'], res['extra_total']))
    print('V_PROMOTE_CORE_ALL_OK' if res['core_ok'] == res['core_total'] else 'V_PROMOTE_CORE_FAIL')
    print('V_PROMOTE_EXTRA_ALL_OK' if res['extra_ok'] == res['extra_total'] else 'V_PROMOTE_EXTRA_FAIL')
    return 0 if res['core_ok'] == res['core_total'] else 1


if __name__ == '__main__':
    sys.exit(main())
