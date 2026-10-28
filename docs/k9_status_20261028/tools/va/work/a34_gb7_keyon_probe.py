"""A34 Declare 사전 점검 (V-A 데이터 0; 읽기 전용). 경로·분류·개수만 출력, 값은 출력하지 않음.

(1) GWT8 HEAD의 gb7_allowed.py를 메모리에 싣고, 보충 24 §14.3의 R2-12 한 항목을 R2-11 바로 뒤에 넣은
    목록의 sha256을 계산해 기대 값(a8148f38…7af1)과 비교합니다(파일 쓰기 0).
(2) 기존 V-B 출력(보고 끝난 자료) VB-41w의 무제어 결정 T=1…750에서 B1 팔 대 OFF 팔 action JSON 차이
    경로를 og_common.deep_diff와 같은 규칙으로 내고, A = V ∪ A_K8 ∪ R2-12 안/밖으로 나눕니다.
    (같은 상태·같은 코드, 튜닝은 두 키만 다름 → 키 켬이 무제어 결정에 더하는 경로)
(3) R-obs3(v3c3-s31 NC) 원본 T=1·150·750·900 action JSON의 metadata 키 이름 가운데 k92_·(173,p4) 하한 키
    유무만 출력합니다.
"""
import hashlib
import json
import re
import subprocess
import sys
import types
from pathlib import Path

GWT8 = Path('D:/VISSIM-merge/sim3-n31-k8')
VB = Path('D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2/chain')
ROBS = Path('D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31')
EXPECT_LIST = 'a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1'
R2_12 = ('R2-12', 'R2', r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)',
         '어댑터 _LEGSPLIT_LAST 길이 진단 키: W_out 롤아웃 도착 유무에 따라 써짐, 계산 영향 0'
         '(ROOTCAUSE §6.1, D-K9-11·12). 재생 출력을 본 뒤 더한 항목 — D-K9-38 ④')


def load_gb7():
    src = subprocess.run(['git', '-C', str(GWT8), 'show',
                          'HEAD:diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py'],
                         capture_output=True, check=True).stdout.decode('utf-8')
    mod = types.ModuleType('gb7_allowed_head')
    exec(compile(src, 'gb7_allowed_head', 'exec'), mod.__dict__)
    return mod


def deep_diff(a, b, path='', out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append((f'{path}/{key}', 'only in ' + ('replay' if key in b else 'original')))
            else:
                deep_diff(a[key], b[key], f'{path}/{key}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'list length'))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                deep_diff(x, y, f'{path}[{i}]', out)
    elif a != b or type(a) is not type(b):
        out.append((path, 'value'))
    return out


def main():
    g = load_gb7()
    base_sha = g.list_sha256()
    entries = list(g.A_K8)
    idx = [e[0] for e in entries].index('R2-11')
    entries.insert(idx + 1, R2_12)
    g.A_K8 = tuple(entries)
    g._COMPILED = tuple((e[0], e[1], re.compile(e[2])) for e in g.A_K8)
    new_sha = g.list_sha256()
    rules = {}
    for e in g.A_K8:
        rules[e[1]] = rules.get(e[1], 0) + 1
    print('LIST head_sha=%s new_sha=%s expect_match=%s A_K8=%d %s' % (
        base_sha, new_sha, new_sha == EXPECT_LIST, len(g.A_K8), sorted(rules.items())))
    print('R2-12 table:', [(p, g.which(p)) for p in (
        '/diagnostics/leg_ramp_split_len_SC1001_W_out', '/diagnostics/leg_ramp_split_length_fallback',
        '/diagnostics/leg_ramp_split_req_last_SC1001_W_out', '/diagnostics/leg_ramp_split_u_on_last',
        '/diagnostics/leg_ramp_split_len_SC1001_W_out/x', '/diagnostics/leg_ramp_split_injected_RM_C10484')])
    hexkey = re.compile(r'_[0-9a-f]{16}$')
    union_outside = {}
    for t in ('000001', '000150', '000300', '000450', '000600', '000750'):
        off = json.loads((VB / 'vb41w_off' / 'dec' / f'action_{t}.json').read_text(encoding='utf-8-sig'))
        b1 = json.loads((VB / 'vb41w_b1' / 'dec' / f'action_{t}.json').read_text(encoding='utf-8-sig'))
        diffs = deep_diff(off, b1)
        outside = sorted({hexkey.sub('_<hash16>', p) + '  [' + k + ']' for p, k in diffs if not g.allowed(p)})
        inside = {}
        for p, _k in diffs:
            w = g.which(p)
            if w:
                inside[w] = inside.get(w, 0) + 1
        print('VB41w T=%s diffs=%d outside_A=%d inside_by_entry=%s' % (t, len(diffs), len(outside), sorted(inside.items())))
        for o in outside:
            union_outside[o] = union_outside.get(o, 0) + 1
    print('OUTSIDE_A union (path [kind] -> number of T among 6):')
    for o, n in sorted(union_outside.items()):
        print('  ', o, '->', n)
    for t in ('000001', '000150', '000750', '000900'):
        p = ROBS / 'decisions_sdmpc31_v3c3_nc_s31' / f'action_{t}.json'
        if not p.exists():
            cands = list(ROBS.glob(f'decisions_*/action_{t}.json'))
            p = cands[0] if cands else p
        m = json.loads(p.read_text(encoding='utf-8-sig')).get('metadata', {})
        ks = sorted(hexkey.sub('_<hash16>', k) for k in m if k.startswith('k92_') or k.startswith('head_discharge_floor_173_p4'))
        print('ROBS3 s31 T=%s metadata keys(k92_/floor_173_p4): %s' % (t, ks))


if __name__ == '__main__':
    sys.exit(main())
