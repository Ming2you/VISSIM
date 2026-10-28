"""gb7_k92decl.py 자기 시험(합성 21사례) + V-B 무제어 B1/OFF 출력 마른 점검. V-A 데이터 0, 읽기 전용(쓰기는 이 폴더
selftest/ 아래 합성 Root 하나와 결과 JSON 하나뿐). 출력은 경로·참거짓·개수뿐입니다.

목록 A: GWT8 커밋 K9-2-5(e27ceac8, 고정 커밋; HEAD 가 아님 — 관문 단계 HEAD = K9-2-7 에는 R2-12 가 이미 있음)의
gb7_allowed.py 를 메모리에 싣고 보충 24 §14.3 R2-12 를 R2-11 바로 뒤에 넣은 것(K9-2-7 이 파일로 만들 목록과 같은 sha
a8148f38…7af1 이어야 함; 다르면 멈춤). 합성 Root 의 증거 두 파일도 같은 커밋의 blob 바이트(git show)에서 만듭니다.
쓰는 곳: --out <폴더>(없으면 이 파일 옆 selftest/). 관문 단계 다시 돌리기(보충 34 §5.0 (iii))는 --out 을 OUTVA 아래 새
폴더로 주고 표준 출력을 새 파일로 받아 Declare 때 고정 출력과 바이트 비교합니다(표준 출력에는 경로가 없음).

기대(실행 전에 적음):
- 합성: 각 사례의 c7_A_or_EK92 가 EXPECT 표와 같음, S01·S02·S18 의 c7_declared_A 도 표와 같음.
- V-B 마른 점검 (VB-41w, 원본 역할 = OFF, 재생 역할 = B1, T = 1, 150, …, 750, Root = V-B 트리 VBT,
  하한 키 기대 이름 = v3c3-s41 이름 head_discharge_floor_173_p4_301ceabb95f116fa (K92_VALUES /p0_2/f_expected_floor_keys)):
  * E1·E2·E3 는 여섯 결정 모두 E_K92 안.
  * E4 는 T = 1·150 에서 E_K92 안. T = 300…750 에서는 binding_is_float_1 만 거짓 [추론: 사슬에서 앞 B1 결정이
    하한 키 = s 를 나르므로 carried = s, 씨앗이 엄격히 이기지 못해 묶임 0.0; GB-7′ 한 결정 재생은 앞 행동이 키 없는
    R-obs3 기록이라 이 나르기가 없음].
  * A ∪ E_K92 밖에 남는 것: T=1 없음(→ c7 참). T=150: head_observation_prior_discarded, n31_binding/vsl_cohort_
    initialization/{sha256,source}, prediction_error/source_action_json (4). T=300…750: head_observation_groups_carried,
    같은 사슬 경로 셋, 그리고 E4 하한 키 (5).
  * 같은 자료를 FRZ_K92 기대 이름(e36d6761cfeac634)으로 보면 B1 하한 키(301ceabb…)는 E_K92 경로가 아니어서 여섯 결정
    모두 A ∪ E_K92 밖에 남음(이름 조건이 실제 자료에서 걸리는지).
"""
import copy
import json
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gb7_k92decl as d  # noqa: E402

GWT8 = Path('D:/VISSIM-merge/sim3-n31-k8')
BASE_COMMIT = 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d'  # K9-2-5
OUT = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else HERE / 'selftest'
VBT = Path('D:/VISSIM-merge/k8_gate_trees/k92b1/vb2_e27ceac8')
VB = Path('D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2/chain')
FLOOR_S41 = 'head_discharge_floor_173_p4_301ceabb95f116fa'
R2_12 = ('R2-12', 'R2', r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)',
         '어댑터 _LEGSPLIT_LAST 길이 진단 키: W_out 롤아웃 도착 유무에 따라 써짐, 계산 영향 0'
         '(ROOTCAUSE §6.1, D-K9-11·12). 재생 출력을 본 뒤 더한 항목 — D-K9-38 ④')


def git_blob(rel):
    return subprocess.run(['git', '-C', str(GWT8), 'show', '%s:%s' % (BASE_COMMIT, rel)],
                          capture_output=True, check=True).stdout


def load_allowed():
    src = git_blob('diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py').decode('utf-8')
    g = types.ModuleType('gb7_allowed_mem')
    exec(compile(src, 'gb7_allowed_mem', 'exec'), g.__dict__)
    e = list(g.A_K8)
    e.insert([x[0] for x in e].index('R2-11') + 1, R2_12)
    g.A_K8 = tuple(e)
    g._COMPILED = tuple((x[0], x[1], re.compile(x[2])) for x in g.A_K8)
    if g.list_sha256() != d.EXPECTED_LIST_SHA256:
        raise SystemExit('LIST_SHA_MISMATCH %s' % g.list_sha256())
    return g


def synthetic_root():
    """합성 Root 둘: good = K9-2-5 증거 두 blob 바이트 사본, bad = W 증거 끝에 1바이트 더함."""
    base = OUT / 'ek92_roots'
    if base.exists():
        shutil.rmtree(base)
    for name in ('good', 'bad'):
        for rel in (d.W_EVIDENCE_REL, d.HB_EVIDENCE_REL):
            dst = base / name / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            data = git_blob(rel)
            if name == 'bad' and rel == d.W_EVIDENCE_REL:
                data += b'\n'
            dst.write_bytes(data)
    return base / 'good', base / 'bad'


def base_docs():
    orig = {'metadata': {'decision_wall_sec': 1.0, 'sim_sec': 300, 'other': 'x'},
            'green_times': {'SC1_p1': 30.0}, 'diagnostics': {}}
    rep = copy.deepcopy(orig)
    rep['metadata']['decision_wall_sec'] = 2.0  # V 경로
    rep['metadata']['k92_w'] = {'after': 5209.8, 'before': 1.0, 'evidence_sha256': d.W_EVIDENCE_SHA256,
                                'u4_sha256': d.U4_SHA256, 'lanes': 3}
    rep['metadata']['k92_hb'] = {'seed': 1045.1612903225805, 'evidence_sha256': d.HB_EVIDENCE_SHA256,
                                 'rule_code_sha256': d.RULE_CODE_SHA256}
    rep['metadata']['k92_hb_seed_binding'] = 1.0
    rep['metadata'][d.FLOOR_KEY_ROBS3_S31] = 1045.1612903225805
    return orig, rep


def cases():
    out = []
    o, r = base_docs()
    out.append(('S01_all_four_replay_only', o, r, True, False))
    o2, r2 = base_docs()
    o2['metadata'][d.FLOOR_KEY_ROBS3_S31] = 1500.0
    r2['metadata'][d.FLOOR_KEY_ROBS3_S31] = 1500.0
    r2['metadata']['k92_hb_seed_binding'] = 0.0
    out.append(('S02_T900_type_floor_both_equal_binding0', o2, r2, True, False))
    for name, fn in (
            ('S03_w_evidence_sha_changed', lambda m: m['k92_w'].__setitem__('evidence_sha256', 'c' + d.W_EVIDENCE_SHA256[1:])),
            ('S04_w_u4_sha_changed', lambda m: m['k92_w'].__setitem__('u4_sha256', 'f' + d.U4_SHA256[1:])),
            ('S05_w_after_1ulp', lambda m: m['k92_w'].__setitem__('after', 5209.800000000001)),
            ('S06_hb_evidence_sha_changed', lambda m: m['k92_hb'].__setitem__('evidence_sha256', 'c' + d.HB_EVIDENCE_SHA256[1:])),
            ('S07_hb_rule_sha_changed', lambda m: m['k92_hb'].__setitem__('rule_code_sha256', 'e' + d.RULE_CODE_SHA256[1:])),
            ('S10_binding_2', lambda m: m.__setitem__('k92_hb_seed_binding', 2.0)),
            ('S10b_binding_int_1', lambda m: m.__setitem__('k92_hb_seed_binding', 1)),
            ('S11_floor_name_hash_differs', lambda m: m.__setitem__(d.FLOOR_KEY_ROBS3_S31[:-1] + '5', m.pop(d.FLOOR_KEY_ROBS3_S31))),
            ('S12_floor_value_1ulp_larger', lambda m: m.__setitem__(d.FLOOR_KEY_ROBS3_S31, 1045.1612903225807)),
            ('S13_floor_replay_only_binding0', lambda m: m.__setitem__('k92_hb_seed_binding', 0.0)),
            ('S15_unlisted_new_key', lambda m: m.__setitem__('k92_other', 1.0)),
            ('S16_floor_without_binding_key', lambda m: m.pop('k92_hb_seed_binding')),
            ('S17_w_not_dict', lambda m: m.__setitem__('k92_w', 'x')),
    ):
        o, r = base_docs()
        fn(r['metadata'])
        out.append((name, o, r, False, False))
    o, r = base_docs()
    out.append(('S08_root_file_sha_differs', o, r, False, False, 'bad'))
    o, r = base_docs()
    o['metadata']['k92_w'] = dict(r['metadata']['k92_w'], before=2.0)
    out.append(('S09_w_both_sides_value_differs', o, r, False, False))
    o, r = base_docs()
    o['metadata']['k92_hb_seed_binding'] = 0.0
    out.append(('S09b_binding_both_sides_differs', o, r, False, False))
    o, r = base_docs()
    o['metadata'][d.FLOOR_KEY_ROBS3_S31] = 1000.0
    out.append(('S14_floor_both_sides_old_lt_s_new_eq_s', o, r, False, False))
    o, r = base_docs()
    r = copy.deepcopy(o)
    r['metadata']['decision_wall_sec'] = 2.0
    r['diagnostics']['leg_ramp_split_len_SC1001_W_out'] = 3.0
    out.append(('S18_A_only_V_and_R2_12', o, r, True, True))
    o, r = base_docs()
    o['metadata']['k92_w'] = r['metadata'].pop('k92_w')
    out.append(('S19_w_original_only', o, r, False, False))
    return out


def main():
    g = load_allowed()
    good, bad = synthetic_root()
    res = {'schema': 'k92-va-gb7-ek92-selftest/v1', 'module_sha256': __import__('hashlib').sha256(
        (HERE / 'gb7_k92decl.py').read_bytes()).hexdigest(), 'list_sha256': g.list_sha256(), 'synthetic': [], 'vb': [],
        'vb_name_cross': []}
    ok_syn = True
    for c in cases():
        name, o, r, exp_c7, exp_decl = c[:5]
        root = bad if len(c) > 5 else good
        j = d.judge_cond7(o, r, g, root)
        row = {'case': name, 'c7_A_or_EK92': j['c7_A_or_EK92'], 'expect': exp_c7, 'c7_declared_A': j['c7_declared_A'],
               'expect_declared': exp_decl, 'outside_A_and_EK92': j['outside_A_and_EK92'],
               'failed_checks': {p: [k for k, v in x['checks'].items() if not v] for p, x in j['ek92_checks'].items()
                                 if not x['ok']}}
        row['match'] = row['c7_A_or_EK92'] == exp_c7 and row['c7_declared_A'] == exp_decl
        ok_syn = ok_syn and row['match']
        res['synthetic'].append(row)
        print('SYN %-42s c7=%s expect=%s declared=%s match=%s failed=%s' % (
            name, row['c7_A_or_EK92'], exp_c7, row['c7_declared_A'], row['match'], row['failed_checks']))
    chain = {'/metadata/n31_binding/vsl_cohort_initialization/sha256', '/metadata/n31_binding/vsl_cohort_initialization/source',
             '/prediction_error/source_action_json'}
    ok_vb = True
    for t in (1, 150, 300, 450, 600, 750):
        s6 = '%06d' % t
        off = json.loads((VB / 'vb41w_off' / 'dec' / ('action_%s.json' % s6)).read_text(encoding='utf-8-sig'))
        b1 = json.loads((VB / 'vb41w_b1' / 'dec' / ('action_%s.json' % s6)).read_text(encoding='utf-8-sig'))
        j = d.judge_cond7(off, b1, g, VBT, floor_key=FLOOR_S41)
        still = {p for p, _k in j['outside_A_and_EK92']}
        hits = {p: e for p, e in j['ek92_hits']}
        failed = {p: [k for k, v in x['checks'].items() if not v] for p, x in j['ek92_checks'].items() if not x['ok']}
        if t == 1:
            exp_still, exp_failed = set(), {}
        elif t == 150:
            exp_still, exp_failed = chain | {'/metadata/head_observation_prior_discarded'}, {}
        else:
            exp_still = chain | {'/metadata/head_observation_groups_carried', '/metadata/' + FLOOR_S41}
            exp_failed = {'/metadata/' + FLOOR_S41: ['binding_is_float_1']}
        exp_hits = {'/metadata/k92_w': 'E1', '/metadata/k92_hb': 'E2', '/metadata/k92_hb_seed_binding': 'E3'}
        if t in (1, 150):
            exp_hits['/metadata/' + FLOOR_S41] = 'E4'
        m = still == exp_still and failed == exp_failed and hits == exp_hits and j['c7_declared_A'] is False \
            and j['c7_A_or_EK92'] == (t == 1)
        ok_vb = ok_vb and m
        res['vb'].append({'T': t, 'diff_count': j['diff_count'], 'outside_A_count': j['outside_A_count'],
                          'ek92_hits': sorted(hits.items()), 'failed_checks': failed,
                          'outside_A_and_EK92': sorted(still), 'c7_declared_A': j['c7_declared_A'],
                          'c7_A_or_EK92': j['c7_A_or_EK92'], 'match_expected': m})
        print('VB41w T=%s diffs=%d outsideA=%d hits=%s failed=%s still=%s c7=%s match=%s' % (
            s6, j['diff_count'], j['outside_A_count'], sorted(hits.values()), failed, sorted(still), j['c7_A_or_EK92'], m))
        jx = d.judge_cond7(off, b1, g, VBT)  # FRZ_K92 기대 이름으로
        stillx = {p for p, _k in jx['outside_A_and_EK92']}
        mx = ('/metadata/' + FLOOR_S41) in stillx and jx['c7_A_or_EK92'] is False
        ok_vb = ok_vb and mx
        res['vb_name_cross'].append({'T': t, 'floor_s41_key_still_outside': ('/metadata/' + FLOOR_S41) in stillx,
                                     'c7_A_or_EK92': jx['c7_A_or_EK92'], 'match_expected': mx})
        print('   name-cross (expect e36d… name): s41 floor key still outside=%s c7=%s match=%s' % (
            ('/metadata/' + FLOOR_S41) in stillx, jx['c7_A_or_EK92'], mx))
    res['synthetic_all_match'] = ok_syn
    res['vb_all_match'] = ok_vb
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'gb7_k92decl_selftest.json').write_text(
        json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print('SYNTHETIC_ALL_MATCH=%s VB_DRYCHECK_ALL_MATCH=%s list_sha256=%s' % (ok_syn, ok_vb, g.list_sha256()))
    print('ALL_OK' if ok_syn and ok_vb else 'NOT_OK')
    return 0 if ok_syn and ok_vb else 1


if __name__ == '__main__':
    sys.exit(main())
