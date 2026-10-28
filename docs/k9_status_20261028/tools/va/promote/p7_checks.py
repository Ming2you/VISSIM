"""보충 34 §3.2 점검 4·6 (읽기 전용). GWT8 작업 트리 gb7_allowed.py를 파일 경로로 불러
판정 표 6행(보충 24 §14.3)과 E_K92 경로 넷의 which()를 찍습니다. 쓰기 0(표준 출력만).
python -B, PYTHONDONTWRITEBYTECODE=1 로 돌립니다.
"""
import importlib.util
import sys

TARGET = 'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py'
TABLE = [
    ('/diagnostics/leg_ramp_split_len_SC1001_W_out', 'R2-12'),
    ('/diagnostics/leg_ramp_split_length_fallback', 'R2-12'),
    ('/diagnostics/leg_ramp_split_req_last_SC1001_W_out', None),
    ('/diagnostics/leg_ramp_split_u_on_last', None),
    ('/diagnostics/leg_ramp_split_len_SC1001_W_out/x', None),
    ('/diagnostics/leg_ramp_split_injected_RM_C10484', 'R2-11'),
]
E = [
    '/metadata/k92_w',
    '/metadata/k92_hb',
    '/metadata/k92_hb_seed_binding',
    '/metadata/head_discharge_floor_173_p4_e36d6761cfeac634',
]
LIST_SHA = 'a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1'


def main():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('gb7_allowed_k927_check', TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ok = True
    counts = {}
    for _id, rule, _p, _s in mod.A_K8:
        counts[rule] = counts.get(rule, 0) + 1
    print('V', len(mod.V), 'A_K8', len(mod.A_K8), 'counts', sorted(counts.items()))
    ok = ok and len(mod.V) == 7 and len(mod.A_K8) == 35 and counts == {'R1': 16, 'R2': 12, 'R3': 7}
    sha = mod.list_sha256()
    print('list_sha256', sha, sha == LIST_SHA)
    ok = ok and sha == LIST_SHA
    r212 = [e for e in mod.A_K8 if e[0] == 'R2-12']
    ids = [e[0] for e in mod.A_K8]
    print('R2-12 count', len(r212), 'position_after_R2-11', ids.index('R2-12') == ids.index('R2-11') + 1)
    ok = ok and len(r212) == 1 and ids.index('R2-12') == ids.index('R2-11') + 1
    for p, want in TABLE:
        got = mod.which(p)
        print('table', p, got, got == want)
        ok = ok and got == want
    for p in E:
        got = mod.which(p)
        print('E_in_A', p, got, got is None)
        ok = ok and got is None
    print('P7_CHECKS_ALL_OK' if ok else 'P7_CHECKS_FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
