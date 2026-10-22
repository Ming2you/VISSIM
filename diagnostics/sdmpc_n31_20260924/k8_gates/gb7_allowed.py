"""GB-7' 허용 차이 경로 A = V ∪ A_K8 (K8 보충 1 §D P10, §E). 닫힌 목록 상수입니다.

쓰는 법(진단 전용, 런타임과 무관):
    python -B gb7_allowed.py            # 목록 sha256과 항목 수를 찍습니다
    import gb7_allowed as g; g.allowed('/metadata/k9_w1')  -> True

- 경로 꼴은 K7 GB-7 판정기 `gb_common.deep_diff`와 같습니다: dict 키는 '/키', 리스트 원소는 '[i]'.
  예: '/metadata/run_provenance/inputs/tuning_json/sha256', '/prediction/state_summary/ramp_queue/RM_C10480'.
  한쪽에만 있는 키는 그 키의 경로 하나로, 길이가 다른 리스트는 리스트 경로 하나로 나옵니다.
- 규칙(보충 1 §E, 재생 전에 고정):
  V   = K7 GB-7 판정기의 휘발 7경로 그대로(`gb7_judge.py` V7).
  R1  = K8 diff가 새로 쓰는 키(그 키 아래 전체).
  R2  = K8(K8b·K9 포함)이 바꾸는 양에 결정론적으로 기대는 기존 경로.
  R3  = 실행 출처(run provenance). FRZ_K8 루트에서 재생하므로 R-obs3 원본(FRZ_K7 루트)의 루트 경로 값도 여기 듭니다.
        단, 기록된 상태·런 매니페스트에서 그대로 오는 경로 값은 루트가 바뀌어도 같으므로 넣지 않습니다(K8-0j2).
- 원천 훑기: 브랜치 diff bd39205..dad555ba(K8-7 커밋까지) 전체의 추가 줄. 훑은 결과와 분류는
  REP8 `D:/VISSIM_runs/20261001_v3c3/reports/k8/A_K8_LIST.md`에 있습니다.
- A_K8 항목은 "달라도 됨"이지 "달라야 함"이 아닙니다. 재생 출력을 본 뒤에는 이 목록에 더하지 않습니다.
  A 밖 경로가 하나라도 다르면(값·유무·형) GB-7' 실패 → STOP입니다(보충 1 §E).
- R2-12는 재생 출력을 본 뒤 더한 항목입니다(보충 1 §E '재생 출력을 본 뒤에는 더하지 않음'의 사후 예외, 사용자 결정 D-K9-38 ④, 보충 24 §14.3).
"""
import hashlib
import json
import re

LIST_SCHEMA = 'k8-gb7-allowed/v1'
SCAN = {'base': 'bd39205d7f0b2178ae9cd3be1232e00a84ee666f',
        'head': 'dad555baa9b0b285859ae53b842536de04789fcb',
        'declaration': 'K8_PREDECLARATION_AMENDMENT_1.md §D P10, §E (sha256 in the same folder .sha256)'}

# V: K7 GB-7 휘발 7경로(무제어 결정; GA 선언 §2.1, K7 선언 표 V). 정확히 같은 경로만.
V = (
    '/metadata/decision_wall_sec',
    '/metadata/prediction_wall_sec',
    '/prediction/wall_sec',
    '/run_provenance/inputs/state_json/path',
    '/run_provenance/inputs/state_json/sha256',
    '/metadata/run_provenance/inputs/state_json/path',
    '/metadata/run_provenance/inputs/state_json/sha256',
)

# 아래 정규식은 경로 전체와 맞아야 합니다(re.fullmatch). '(?:[/\[].*)?' = 그 키 아래 전체.
_SUB = r'(?:[/\[].*)?'

# (항목 id, 규칙, 정규식, 원천)
A_K8 = (
    # ---------------------------------------------------------------- R1: diff가 새로 쓰는 키
    ('R1-01', 'R1', r'.*/stopline_.*',
     '§E 규칙 1 `stopline_*`: stopline_approach.configure·install_check·initialize의 metadata stopline_approach_* · '
     'stopline_city_arrival_evidence_sha256, end_step·diagnostics의 stopline_* 계수, 자원 종류 stopline_lane_room '
     '(보충 5 N-3), 경로 키 stopline_internal:*, stopline_fold_carry_veh(N19)'),
    ('R1-02', 'R1', r'/metadata/k8b_p1' + _SUB, 'runtime_setup.install_sc1002w_saturation (K8b-1 P-1)'),
    ('R1-03', 'R1', r'/metadata/k8b_p4' + _SUB, 'runtime_setup.install_wout_exit_law (K8b-2 P-4\'/P-4b; W2-A가 side 부류를 덧붙임)'),
    ('R1-04', 'R1', r'/metadata/k8b_p2' + _SUB, 'stopline_approach.city_arrival_prepare (K8b-3 P-2)'),
    ('R1-05', 'R1', r'/metadata/k8b_p2_init' + _SUB, 'stopline_approach.city_arrival_initialize (K8b-3 P-2)'),
    ('R1-06', 'R1', r'/metadata/k9_w1' + _SUB, 'runtime_setup.install_sc1001wout_saturation (K9-1 W1)'),
    ('R1-07', 'R1', r'/metadata/k9_w2a' + _SUB, 'runtime_setup.install_wout_side_handoff (K9-1 W2-A)'),
    ('R1-08', 'R1', r'/metadata/k9_f17b' + _SUB, 'offramp_split_forecast.install (K9-1 F17b)'),
    ('R1-09', 'R1', r'/(?:metadata/)?projection_diagnostics/(?:residual_stopped_split_links|'
                    r'residual_stopped_ready_exceeds_stopped_links|residual_stopped_ready_exceeds_stopped_veh|'
                    r'storage_seed_split_by_link|storage_seed_split_rows|storage_seed_split_unattributed_veh)' + _SUB,
     'vissim_stackelberg_adapter.build_local_observation_summary·seed_urban_arrival_buffer (K8-4 S5; §E 규칙 1 '
     'storage_seed_split_by_link·위반 계수, 보충 9 projection_diagnostics 6키)'),
    ('R1-10', 'R1', r'/metadata/projection_(?:residual_stopped_split_links|residual_stopped_ready_exceeds_stopped_links|'
                    r'residual_stopped_ready_exceeds_stopped_veh|storage_seed_split_rows|'
                    r'storage_seed_split_unattributed_veh)',
     '어댑터 metadata[f"projection_{key}"] 숫자 거울(보충 9 metadata projection_* 숫자 키; K8-4 새 키만)'),
    ('R1-11', 'R1', r'.*/urban_link_storage_by_link' + _SUB, 'K8-4 국소 요약 키(보충 9)'),
    ('R1-12', 'R1', r'/metadata/sc2001_corridor/(?:branches|wout_handover)' + _SUB,
     'sc2001_corridor.install_wout_handover가 spec["branches"]·spec["wout_handover"]를 새로 씀(K9-1 W2-A; '
     'metadata.sc2001_corridor는 그 spec)'),
    ('R1-13', 'R1', r'/metadata/sc2001_corridor/calibration/priors/[^/]+/shares' + _SUB,
     'sc2001_corridor.install_wout_handover가 priors[*]["shares"] = {wout_handover: 1.0}로 새로 씀(K9-1 W2-A)'),
    ('R1-14', 'R1', r'.*/(?:sc2001:)?wout_handover' + _SUB,
     'W2-A 가지 이름 wout_handover와 경로 키 sc2001:wout_handover(대리 예측 flow_counts·가지별 수용량)'),
    ('R1-15', 'R1', r'.*/meter_spill_veh_h' + _SUB, 'sdmpc.omega_costs partition["meter_spill_veh_h"] (K8-3 S1-OWN, §E 규칙 1)'),
    ('R1-16', 'R1', r'.*/meter_spill_veh' + _SUB,
     'control_area_objective 체류 행 meter_spill_veh (K8-3 S1-OWN; ledger.meter_spill)'),
    # ---------------------------------------------------------------- R2: 결정론적 파생 기존 경로
    ('R2-01', 'R2', r'/(?:metadata/)?projection_diagnostics/moving_speed_correction' + _SUB, '§E 규칙 2'),
    ('R2-02', 'R2', r'/prediction/(?:state_summary|calibrated_state_summary|terminal_features|audit_calibration)' + _SUB,
     '§E 규칙 2'),
    ('R2-03', 'R2', r'/prediction_error/(?:scalar_errors' + _SUB + r'|mean_abs_scalar_error)', '§E 규칙 2'),
    ('R2-04', 'R2', r'/metadata/prediction_audit_[^/\[]*' + _SUB, '§E 규칙 2'),
    ('R2-05', 'R2', r'/metadata/prediction_[^/\[]*_error', '§E 규칙 2'),
    ('R2-06', 'R2', r'/metadata/prediction_total_model_vehicles_[^/\[]*', '§E 규칙 2'),
    ('R2-07', 'R2', r'/(?:metadata/)?projection_diagnostics/physical_stock_assignment_by_link/(?:127|10777|10695)' + _SUB,
     '§E 규칙 2: SA가 provenance를 고쳐 쓰는 링크 = 정지선 127, 연결 10777, posthead_rehome 10695 '
     '(stopline_approach.initialize; 증거 sc1001eb_evidence_v3c3_20261004.json)'),
    ('R2-08', 'R2', r'/metadata/joint_leader_selection/omega_partition' + _SUB,
     '§E 규칙 2 sdmpc.omega_costs 결과 경로(grep: sdmpc.py:971 omega_partition)'),
    ('R2-09', 'R2', r'/metadata/joint_leader_selection/tangent_derivatives\[\d+\]/surrogate_prediction/'
                    r'sdmpc_omega_partition' + _SUB,
     '§E 규칙 2 sdmpc.omega_costs 결과 경로(grep: area_follower_objective.py:562 sdmpc_omega_partition)'),
    ('R2-10', 'R2', r'/metadata/control_area_initial_inside_veh',
     '영역 첫 내부 대수: SA 초기화가 W 접근 재고(in_SC1001_W·수신 저장고)를 다시 놓은 뒤 area_runtime.configure가 셈'),
    ('R2-11', 'R2', r'/diagnostics/leg_ramp_split_(?:injected_[^/\[]*|storage_adjust_veh|tail_extra_exit_veh|'
                    r'receiving_rejected_veh)',
     '롤아웃 누적 _LEGSPLIT_LAST(urban_flow_accounting): W_out 출구 법칙(P-4\'/P-4b)·W2-A 인계·W 접근 재고(SA·S5)·'
     '신호 앞 수용(S1)에 기댐'),
    ('R2-12', 'R2', r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)',
     '어댑터 _LEGSPLIT_LAST 길이 진단 키: W_out 롤아웃 도착 유무에 따라 써짐, 계산 영향 0(ROOTCAUSE §6.1, D-K9-11·12). 재생 출력을 본 뒤 더한 항목 — D-K9-38 ④'),
    # ---------------------------------------------------------------- R3: 실행 출처
    ('R3-01', 'R3', r'/(?:metadata/)?run_provenance/(?:workspace_git_commit|execution_fingerprint_sha256)', '§E 규칙 3'),
    ('R3-02', 'R3', r'/(?:metadata/)?run_provenance/imported_modules' + _SUB, '§E 규칙 3'),
    ('R3-03', 'R3', r'/(?:metadata/)?run_provenance/inputs/[^/]+/sha256',
     '§E 규칙 3(배포 튜닝 sha); K8-2 판정기 RULE3와 같은 꼴(바뀐 입력 파일 어댑터·러너 VBS 포함)'),
    ('R3-04', 'R3', r'/(?:metadata/)?run_provenance/(?:workspace_root|numsim_repo_root)',
     '실행 출처: 재생 루트 FRZ_K8 ≠ R-obs3 루트 FRZ_K7(원본 61결정에서 루트 경로 값으로 열거)'),
    ('R3-05', 'R3', r'/(?:metadata/)?run_provenance/inputs/(?:adapter_py|calibration_json|control_mapping_json|'
                    r'detector_mapping_json|fixed_signal_schedule_py|intersection_adjacency_json|link_assignment_json|'
                    r'main_vbs_runner|numsim_default_yaml|parameters_json|parameters_py|storage_capacity_json|'
                    r'strict_signal_program_py|tuning_json|watchdog_wrapper)/path',
     '실행 출처: 루트 아래 입력 파일 경로(원본 61결정에서 FRZ_K7 루트를 담은 inputs/*/path 15개)'),
    ('R3-06', 'R3', r'/metadata/(?:detector_mapping_resolved_path|native_phase_share_map_path)',
     '실행 출처: 재생 루트에서 다시 푸는 파일 경로(run_provenance 밖; k91t 루트 결정에서 새 루트로 바뀜 확인)'),
    # R3-07 `/metadata/shared_approach/demand_profile/path`는 K8-0j2에서 뺐습니다(VerifyPromote r1 결함 D1).
    # 값은 기록된 런 매니페스트(run_provenance.manifest_path)의 demand_profile에서 그대로 와서 재생 루트와
    # 무관합니다(shared_approach.py:69-82). id는 다시 매기지 않습니다.
    ('R3-08', 'R3', r'/metadata/joint_leader_selection/tangent_derivatives\[\d+\]/transformed_source_sha256' + _SUB,
     '실행 출처: 변환 원천 해시 키(K8-3 관문 보고 §7-2; SDMPC 결정에만 있음)'),
)

_COMPILED = tuple((entry_id, rule, re.compile(pattern)) for entry_id, rule, pattern, _source in A_K8)
_V = frozenset(V)


def which(path):
    """경로가 든 항목 id('V' 또는 A_K8 id). A 밖이면 None."""
    if path in _V:
        return 'V'
    for entry_id, _rule, pattern in _COMPILED:
        if pattern.fullmatch(path):
            return entry_id
    return None


def allowed(path):
    """A = V ∪ A_K8 안이면 True."""
    return which(path) is not None


def outside(paths):
    """A 밖 경로만 순서대로 돌려줍니다(GB-7' 실패 후보)."""
    return [p for p in paths if not allowed(p)]


def canonical():
    """목록의 정규 JSON(정렬 키, ASCII 아님 허용, 구분자 고정)."""
    return json.dumps({'schema': LIST_SCHEMA, 'scan': SCAN, 'V': list(V),
                       'A_K8': [list(e) for e in A_K8]},
                      sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def list_sha256():
    """REP8에 적는 목록 sha256(정규 JSON의 UTF-8 바이트)."""
    return hashlib.sha256(canonical().encode('utf-8')).hexdigest()


if __name__ == '__main__':
    counts = {}
    for _id, rule, _p, _s in A_K8:
        counts[rule] = counts.get(rule, 0) + 1
    print('GB7_ALLOWED schema=%s V=%d A_K8=%d %s list_sha256=%s' % (
        LIST_SCHEMA, len(V), len(A_K8), ' '.join('%s=%d' % kv for kv in sorted(counts.items())), list_sha256()))
