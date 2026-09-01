# P-Stack Flagship 재작성 체크리스트

## 0. 선행
- [x] DEFAULT_REPO_ROOT를 NUMSIM_REPO_ROOT env 우선 + NumSim-mine 폴백으로 교체
- [x] NumSim-mine에서 flagship 러너 make_controller(L244-316)·per-step 로직(L925-1176) 원문 재확인 — plan.md와 3건 불일치(grid/horizon 3/forecast 길이), 러너 기준으로 정정. context-notes 기록

## 1. 컨트롤러 구성 (pstack-flagship 모드)
- [x] `--controller pstack-flagship` CLI choice 추가
- [x] F1StackelbergWuMeteredController 로드 (지역 import)
- [x] flagship cfg override 함수 (base < flagship < calibration < tuning 순서 유지)
- [x] cfg.mpc 동적 속성 setattr (OPT12 2종; leader_value_depth는 정식 필드로 확인 → cfg override)
- [x] controller/nash_solver 속성 세트 이식 (SEG13, 가격 4채널, cross OFF, δ300/trust0.20, f1_spillback 0, joint_green_offset, ramp_offset, inner_iters 4)
- [x] os.environ['NASH_SMAX']='10' 설정
- [x] BIAS_SAMPLE 활성 방식 러너 대조 후 이식 (grid 강제라 실질 불활성임을 문서화)
- [x] install_vissim_terminal_cost_objective 래핑 적용

## 2. per-step 로직 + 사이드카
- [x] 사이드카 JSON 읽기/쓰기 (pstack_flagship_runtime.json; 없으면 첫 스텝)
- [x] MS_ADAPT: 링크평균 밀도 |Δρ| 계산 → 래치(hold 5) → segment_metering_smoothness_weight 주입
- [x] FAR_GATE=3(실질 mode 2): capdrop 검출 + 히스테리시스 래치 → leader_mfd_far_enabled 개폐
- [x] SUP_PFO + SUP_GATE=fargate: PFO 에뮬레이션 cfg 사본 → 공통 V 채점 → 승자 집행, 게이트 ON 시 스킵
- [x] pstack-flagship 모드에서 post_guard PFO-fallback 기본 OFF (tuning으로 재활성 가능)
- [x] 결정 metadata에 ms_friction/fargate/sup_pick 기록 (하류 분석용)
- [x] forecast 길이 = horizon_steps + leader_value_depth (러너 L1044) — flagship 모드에서만

## 3. tuning JSON
- [x] real_world_modi_pstack_flagship_20260731.json (vissimdsd 체인 extends, adapter.flagship 섹션)
- [x] 8-seg 별도 tuning 불요 — 테스트는 flagship 체인 extends한 임시 저예산 tuning으로 충분

## 4. 검증
- [x] scripts/test_pstack_flagship_adapter.py 작성 (한국어 헤더 주석)
  - [x] 구성 검증: 모드 진입 후 controller/nash_solver/cfg 속성 전수 assert
  - [x] MS_ADAPT 래치 단위검증: 첫 스텝/미달/트리거/hold 만료/재트리거/다중 링크/신규 링크 무시
  - [x] 합성 state json 스모크: 결정 2회(사이드카 연속성 + MS 트리거 + fargate + SUP 게이트)
  - [x] 회귀: 동일 state로 기존 stackelberg 모드 무오류 (계약 보존)
- [x] 테스트 실행 전부 PASS (4/4)
- [x] 기존 모드 코드 경로 diff 검토 — 신규 분기 밖 변경은 `os` import, DEFAULT_REPO_ROOT(의도),
      build_config의 `flagship=False` 기본 kwarg(타 호출부 3곳 전부 키워드 인자라 무영향)뿐
- [x] 제어 활성화 유효성: 2회차에서 metering 1800→1500, VSL 120→100 (둘 다 용량/최대 미만 = 활성)
- [x] seg13_vsl_box_kmh 15 vs 20 A/B로 VSL 동결 여부 실증

## 5. 마무리
- [x] context-notes.md 결정 기록 최신화
- [ ] plan.md 후속 항목 재확인 (미해결 목록은 plan.md "후속" 절)
