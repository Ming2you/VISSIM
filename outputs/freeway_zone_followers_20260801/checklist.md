# 4-zone freeway follower 구현 체크리스트 (2026-08-01)

기준 문서: `plan.md`. 최우선 불변조건은 `freeway_agent_groups` 미설정 시 기존 SEG13 비트 동일.

## A. NumSim-mine (브랜치 flagship-ms-adapt-clean)

- [x] `src/models/state.py` MPCConfig에 `freeway_agent_groups: Optional[Dict[str, Any]] = None` 신설
      → 검증: flagship cfg에서 값이 None (test `default_unchanged`)
- [x] `SegmentAgentModel`을 세그먼트 집합 소유로 일반화 (`segs: List[int]`, `seg`는 property)
      → 검증: 기존 `src/tests/test_segment_local_plant.py`가 `agent.seg`로 그대로 통과
- [x] `segment_zone_substep_local` 신설 + `segment_substep_local`을 단일 세그먼트 래퍼로
      → 검증: 링크 전진 비트 일치 테스트(`TestSegmentLocalExactness`) 통과
- [x] `build_segment_agent_models(cfg, link, groups=None)` — cfg에서 groups를 읽고 zone 생성
      → 검증: test `zone4_mapping` (zone id/segs/ramps가 plan.md 표와 일치)
- [x] 파티션 검증(전수 커버·비중복·연속·오름차순·범위) 실패 시 RuntimeError
      → 검증: test `partition_guards` (8종 위반 케이스)
- [x] `_solve_freeway_segment_agents` 다중 세그먼트 대응
  - [x] own-TTS = 소유 세그먼트 차량수 합 (한 번의 곱셈·한 번의 `+=` 유지)
  - [x] origin queue는 seg0 소유 zone에서 1회만
  - [x] radius-1 이웃 = zone 경계 **바깥** 인접 세그먼트 (이중계상 차단)
  - [x] ~~VSL 후보 = zone 균일 1차원~~ → **v2**: 세그먼트별 VSL + 좌표하강, 앵커는
        세그먼트 자신의 직전 VSL (`len(segs)==1`은 기존 열거 경로 유지)
  - [x] VSL 마찰 = `w · Σ_{s∈zone} |v_s − prev_v[s]|` (링크 총 마찰 스케일 보존)
  - [x] g_vsl 가격 = 소유 세그먼트별 `g_vsl[s]·(v_s − ref[s])` 합산
  - [x] h 교차가격의 v = 그 ramp의 merge 세그먼트 VSL
  - [x] 소유 ramp 복수 대응 (후보는 곱집합) — **zone 경로에서만 발화**(기본 경로는
        기존 `owned_ramps[0]` 절삭 유지)
  - [x] 궤적 교환에 소유 ramp release 전부 반영
  - [x] `preferred_meter` 키 = 링크 소유 ramp 전수 (zone 모드에서 assert)
  - [x] 좌표하강 sweep 수·수렴 여부 진단 기록
- [x] `freeway_agent_groups`가 SEG13 경로 밖에 꽂히면 `_solve_followers` 진입부에서 RuntimeError
- [x] zone 판정은 빌더가 채우는 `SegmentAgentModel.zone_mode`(len(segs)>1 휴리스틱 폐기)
- [x] zone 진단은 zone 모드에서만 + link 네임스페이스(`wu_zone_*_{link}_{zid}`)
- [x] 알 수 없는 링크 키 → RuntimeError (링크 부분 지정은 계속 허용)
- [x] zone_id 링크 내 중복 → RuntimeError
- [x] 세그먼트 인덱스 정수성 검사(3.7 절삭 금지, 3.0은 허용)
- [x] `mpc.freeway_zone_vsl_max_sweeps` 신설(기본 3)
- [x] **비트 동일 골든 회귀** — HEAD 7f10393 대비 6 케이스 완전 일치
      (E/F = 한 세그먼트 2 ramp 구성 포함)

## B. VISSIM (브랜치 pstack-flagship-controller)

- [x] `evaluation/configs/real_world_modi_pstack_flagship_segvsl_20260801.json` 신규 —
      actuation 정책만 `keep`으로 되돌린 **대조군**(zone 없음)
- [x] `evaluation/configs/real_world_modi_pstack_zone4_20260801.json`이 대조군을 extends
      → zone4 ↔ 대조군 차이 = `freeway_agent_groups` 하나
- [x] `tuning_to_config_overrides`가 `config_overrides.mpc`를 그대로 통과 — 어댑터 변경 불요
- [x] SUP_PFO 사본에서 `freeway_agent_groups`를 None으로 (seg13 박스 키와 동일 규약)
      → 이것만 어댑터 수정. 없으면 감독자 PFO가 가드에 걸려 즉사한다.
- [x] zone4 tuning notes에서 사실과 다른 문장 정정

## C. 테스트

- [x] `scripts/test_freeway_zone_followers.py` 9/9 PASS (프로덕션 매핑/캘리브레이션 사용)
- [x] `scripts/test_pstack_flagship_adapter.py` 4/4 PASS (회귀)
- [x] 신규 케이스: `single_segment_zone_parity` / `multi_ramp_gating` /
      `budget_projection_scope` / `segvsl_control`
- [x] 세그먼트 VSL 실집행 회귀 검사(`vsl_segment_overrides_cleared` 부재 + 세그먼트 키 16개)
- [x] NumSim 초점 서브셋 5개 모듈 — 사전 실패 3건 외 통과
- [ ] NumSim 전수 스위트 — 50분+ 소요로 미완(재실행 필요)

## 남은 일 (이번 범위 밖)

- [ ] flagship 5셀 런 레벨 비트 동일 (`work/bias_jobs.txt` P-STACK-…-JOINT) — 실행 시간이 커서 미수행
- [ ] zone4 vs `flagship_segvsl` 대조 A/B 실런 (정책 변화와 zone 효과 분리 측정)
- [ ] 좌표하강 sweep 예산 대비 해 품질·wall-time 측정
- [ ] FW_E 6:2 편중 경계 재지정 A/B
