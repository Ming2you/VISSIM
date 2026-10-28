"""보충 34 §3.1 순서 5 점검 (읽기 전용).

작업 CFG 대 `git cat-file blob e27ceac8:<CFG>` JSON 값 차이를 JSON 포인터로 냅니다.
기대: 정확히 /urban/capacity/head_floor_seed, /urban/sc109w_through_saturation 두 경로,
둘 다 작업 쪽에만. 두 값의 evidence_sha256 = 증거 파일(작업 트리) 바이트 sha256.
runtime.decision_error_policy = "hold_previous_on_exception" (작업·옛 CFG 둘 다).
쓰기 0 (표준 출력만). 인자 없음.
"""
import hashlib
import json
import subprocess
import sys

G = 'D:/VISSIM-merge/sim3-n31-k8'
CFG = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
BASE = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'
EXPECT_PATHS = ['/urban/capacity/head_floor_seed', '/urban/sc109w_through_saturation']
EXPECT_EVID = {
    '/urban/sc109w_through_saturation': (
        'diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json',
        'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712'),
    '/urban/capacity/head_floor_seed': (
        'diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json',
        'b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee'),
}


def esc(k):
    return str(k).replace('~', '~0').replace('/', '~1')


def deep_diff(a, b, p, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            q = p + '/' + esc(k)
            if k not in a:
                out.append((q, 'new_only'))
            elif k not in b:
                out.append((q, 'old_only'))
            else:
                deep_diff(a[k], b[k], q, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((p, 'list_len'))
        for i in range(min(len(a), len(b))):
            deep_diff(a[i], b[i], p + '/' + str(i), out)
    else:
        if type(a) is not type(b) or a != b:
            out.append((p, 'value'))


def ptr_get(doc, ptr):
    cur = doc
    for part in ptr.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        cur = cur[part]
    return cur


def main():
    ok = True
    old_bytes = subprocess.run(['git', '-C', G, 'cat-file', 'blob', BASE + ':' + CFG],
                               check=True, capture_output=True).stdout
    with open(G + '/' + CFG, 'rb') as f:
        new_bytes = f.read()
    print('old_sha256', hashlib.sha256(old_bytes).hexdigest(), 'bytes', len(old_bytes))
    print('new_sha256', hashlib.sha256(new_bytes).hexdigest(), 'bytes', len(new_bytes))
    old = json.loads(old_bytes.decode('utf-8'))
    new = json.loads(new_bytes.decode('utf-8'))
    out = []
    deep_diff(old, new, '', out)
    # deep_diff(a=old, b=new): 'new_only' = 키가 old에 없음 = 작업(새) 쪽에만.
    for p, kind in out:
        print('diff', p, kind)
    paths = sorted(p for p, _ in out)
    kinds = sorted(set(k for _, k in out))
    c_paths = paths == sorted(EXPECT_PATHS)
    c_kinds = kinds == ['new_only']
    print('check_two_paths', c_paths)
    print('check_new_side_only', c_kinds)
    ok = ok and c_paths and c_kinds
    for p in EXPECT_PATHS:
        v = ptr_get(new, p)
        rel, want = EXPECT_EVID[p]
        ev_ok = isinstance(v, dict) and v.get('evidence') == rel and v.get('evidence_sha256') == want
        with open(G + '/' + rel, 'rb') as f:
            fsha = hashlib.sha256(f.read()).hexdigest()
        print('value', p, json.dumps(v, ensure_ascii=False, sort_keys=True))
        print('evidence', p, 'declared_ok', ev_ok, 'file_sha256', fsha, 'file_eq_declared', fsha == want)
        ok = ok and ev_ok and fsha == want
    for name, doc in (('old', old), ('new', new)):
        pol = doc.get('runtime', {}).get('decision_error_policy')
        print('policy', name, pol)
        ok = ok and pol == 'hold_previous_on_exception'
    print('P5_ALL_OK' if ok else 'P5_FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
