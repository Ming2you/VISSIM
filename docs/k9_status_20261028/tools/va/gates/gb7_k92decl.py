"""K8 보충 34 §5.2 E_K92 판정 함수 (사용자 결정 D-K9-71). V-A 데이터 전에 쓰고 sha256을 보충 34에 고정합니다.

무엇을 하나
- GB-7′ T마다 조건 7과 해시 A/B 조건 1(= 9회 각각의 GB-7′ 조건 7)을 "A ∪ E_K92"로 셉니다.
  A = V ∪ A_K8 (FRZ_K92 `gb7_allowed.py`, R2-12 포함, 목록 sha a8148f38…7af1). 이 파일은 그 목록을 바꾸지 않습니다.
- E_K92 = 보충 24 §4.2 A_K92-M·H5 꼴의 선언 차이. 정확히 아래 네 경로만, 재생 쪽에만 있을 때만:
    E1 /metadata/k92_w                      값이 dict, evidence_sha256 = 고정값 = Root 증거 파일 바이트 sha256,
                                             u4_sha256 = 고정값, after 가 float 이고 repr = '5209.8'
    E2 /metadata/k92_hb                     값이 dict, evidence_sha256 = 고정값 = Root 증거 파일 바이트 sha256,
                                             rule_code_sha256 = 고정값
    E3 /metadata/k92_hb_seed_binding        값이 float 이고 0.0 또는 1.0
    E4 /metadata/<floor_key>                floor_key = 기대 이름(FRZ_K92 GB-7′·해시 A/B: R-obs3 v3c3-s31 이름
                                             head_discharge_floor_173_p4_e36d6761cfeac634), 값이 float 이고
                                             repr = '1045.1612903225805', 그리고 그 결정 재생 쪽
                                             k92_hb_seed_binding 이 float 1.0
  "재생 쪽에만" = 차이 종류가 presence 이고, 원본 metadata 에 그 키가 없고 재생 metadata 에 있음.
  양쪽에 있고 값이 다르면(옛 H5 (나) 꼴 포함) E_K92 가 아닙니다. 그 밖의 A 밖 경로가 하나라도 있으면 조건 7 거짓.
- 블라인드: 출력은 경로·차이 종류·참거짓·개수·sha 비교 결과뿐입니다. 값은 출력하지 않습니다.
- 차이 경로 꼴은 K8b 판정기 gjudge.raw_diff(= og_common.deep_diff = K7 gb_common.deep_diff) 그대로입니다.
- 이 모듈은 파일을 쓰지 않고, 자식 프로세스를 만들지 않으며, 저장소 코드를 import 하지 않습니다.
  allowed(목록 모듈 객체)와 root(증거 파일을 읽을 Root)는 부르는 쪽이 넘깁니다.
"""
import hashlib
from pathlib import Path

SCHEMA = 'k92-va-gb7-ek92/v1'
FLOOR_KEY_ROBS3_S31 = 'head_discharge_floor_173_p4_e36d6761cfeac634'
SEED_REPR = '1045.1612903225805'
W_AFTER_REPR = '5209.8'
W_EVIDENCE_REL = 'diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json'
W_EVIDENCE_SHA256 = 'b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712'
HB_EVIDENCE_REL = 'diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json'
HB_EVIDENCE_SHA256 = 'b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee'
U4_SHA256 = '22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b'
RULE_CODE_SHA256 = 'd9bd53920eea89ace2b71a589d780069c3c7191be889aca894994ddf65bcc106'
EXPECTED_LIST_SHA256 = 'a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1'
OUT_CAP = 200


def raw_diff(a, b, path='', out=None):
    """gjudge.raw_diff 그대로: (경로, 종류) 목록. 종류 = presence / list_length / value / type."""
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append((f'{path}/{key}', 'presence'))
            else:
                raw_diff(a[key], b[key], f'{path}/{key}', out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path, 'list_length'))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                raw_diff(x, y, f'{path}[{i}]', out)
    elif a != b or type(a) is not type(b):
        out.append((path, 'value' if type(a) is type(b) else 'type'))
    return out


def e_paths(floor_key=FLOOR_KEY_ROBS3_S31):
    """E_K92 경로 → 항목 id (정확히 네 경로)."""
    return {'/metadata/k92_w': 'E1', '/metadata/k92_hb': 'E2', '/metadata/k92_hb_seed_binding': 'E3',
            '/metadata/' + floor_key: 'E4'}


def _file_sha256(root, rel):
    p = Path(root) / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def _is_float(x):
    return type(x) is float


def check_entry(eid, key, a_md, b_md, kind, root):
    """한 E_K92 경로의 조건(참거짓 dict). 모두 참이어야 그 경로가 E_K92 안입니다."""
    c = {'kind_is_presence': kind == 'presence',
         'replay_only': isinstance(a_md, dict) and isinstance(b_md, dict) and key not in a_md and key in b_md}
    v = b_md.get(key) if isinstance(b_md, dict) else None
    if eid == 'E1':
        c['is_dict'] = isinstance(v, dict)
        v = v if isinstance(v, dict) else {}
        c['evidence_sha256_is_fixed'] = v.get('evidence_sha256') == W_EVIDENCE_SHA256
        c['evidence_sha256_is_root_file'] = (v.get('evidence_sha256') is not None
                                             and v.get('evidence_sha256') == _file_sha256(root, W_EVIDENCE_REL))
        c['u4_sha256_is_fixed'] = v.get('u4_sha256') == U4_SHA256
        c['after_float_repr_5209_8'] = _is_float(v.get('after')) and repr(v.get('after')) == W_AFTER_REPR
    elif eid == 'E2':
        c['is_dict'] = isinstance(v, dict)
        v = v if isinstance(v, dict) else {}
        c['evidence_sha256_is_fixed'] = v.get('evidence_sha256') == HB_EVIDENCE_SHA256
        c['evidence_sha256_is_root_file'] = (v.get('evidence_sha256') is not None
                                             and v.get('evidence_sha256') == _file_sha256(root, HB_EVIDENCE_REL))
        c['rule_code_sha256_is_fixed'] = v.get('rule_code_sha256') == RULE_CODE_SHA256
    elif eid == 'E3':
        c['float_0_or_1'] = _is_float(v) and v in (0.0, 1.0)
    elif eid == 'E4':
        c['float_repr_is_seed'] = _is_float(v) and repr(v) == SEED_REPR
        bnd = b_md.get('k92_hb_seed_binding') if isinstance(b_md, dict) else None
        c['binding_is_float_1'] = _is_float(bnd) and bnd == 1.0
    else:
        c['known_entry'] = False
    return c


def judge_cond7(original_doc, replay_doc, allowed, root, floor_key=FLOOR_KEY_ROBS3_S31):
    """GB-7′ 조건 7(그리고 해시 A/B 조건 1)의 두 판:
    c7_declared_A   = 선언 목록 A 만으로(보고만; B1 동결본에서는 거짓이 예상됨)
    c7_A_or_EK92    = A ∪ E_K92 (관문 판정에 씀; 보충 34 §5.2)."""
    diff = raw_diff(original_doc, replay_doc)
    paths = [p for p, _k in diff]
    out_a = set(allowed.outside(paths))
    ep = e_paths(floor_key)
    a_md = original_doc.get('metadata') if isinstance(original_doc, dict) else None
    b_md = replay_doc.get('metadata') if isinstance(replay_doc, dict) else None
    hits, still, checks = [], [], {}
    for p, kind in diff:
        if p not in out_a:
            continue
        eid = ep.get(p)
        if eid is None:
            still.append([p, kind])
            continue
        c = check_entry(eid, p[len('/metadata/'):], a_md, b_md, kind, root)
        checks[p] = {'entry': eid, 'checks': c, 'ok': all(c.values())}
        if checks[p]['ok']:
            hits.append([p, eid])
        else:
            still.append([p, kind])
    list_sha = allowed.list_sha256() if hasattr(allowed, 'list_sha256') else None
    return {'schema': SCHEMA, 'floor_key': floor_key, 'diff_count': len(paths),
            'allowed_list_sha256': list_sha, 'allowed_list_is_expected': list_sha == EXPECTED_LIST_SHA256,
            'outside_A': [[p, k] for p, k in diff if p in out_a][:OUT_CAP], 'outside_A_count': len(out_a),
            'c7_declared_A': not out_a,
            'ek92_hits': hits, 'ek92_checks': checks,
            'outside_A_and_EK92': still[:OUT_CAP], 'outside_A_and_EK92_count': len(still),
            'c7_A_or_EK92': not still}


def which(path, allowed, floor_key=FLOOR_KEY_ROBS3_S31, ek92_ok_paths=()):
    """항목 id(보고용 적중 수): A 항목 id, 조건을 채운 E_K92 경로면 'E1'…'E4', 아니면 'OUTSIDE'."""
    w = allowed.which(path)
    if w:
        return w
    if path in ek92_ok_paths:
        return e_paths(floor_key)[path]
    return 'OUTSIDE'
