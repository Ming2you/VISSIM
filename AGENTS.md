# AGENTS.md — Codex 진입점

Latest delivery checkpoint: `diagnostics/handoff_20260921_acceleration/README.md` supersedes the historical local-only notes below. This increment includes current-target acceleration diagnostics, rejected default-off memory/response-scale candidates, and all 60 saved local forecasts. Core/network/demand unchanged from fbdbeed; RM/VSL gain calibration remains NOT_QUALIFIED. Restore through the transport package first. Next: separate carried-velocity mixing from same-vehicle reaction error; that analysis has not been completed.


**현재 최우선 로컬 재개점:** `K/SPATIAL_ACCELERATION_AND_AUTONOMOUS_GATE.md`와`K/PLAN.md`를 읽는다. 대상 가감속 정보의100m 집계는 조건부 개선을 유지했지만, 기존 수송에 연결한 자기/이웃 반응 기억은각12개30초 비교 중11개 악화했다. 계수 고정·원래 물리 셀 크기의 속도식도NC30초4개 모두 악화해 기각했다. helper의두 선택 기능은기본비활성, 정본core/망/수요/native 변경없음. 다음은 현재→다음1초의 carried velocity(차량 혼합)와 실제 같은 차량 반응 장부를분리해 상태 갱신 오차를좁힌다. 조건부 효과를자율450초 이득으로대체하지마라.27pin/60궤적/4680보존/원래150초6개exact와parameterPASS, NOT_QUALIFIED. 이 후속은푸시미포함이다.

**푸시 후 최신 로컬 진단:** `K/INTERACTION_MEMORY_AND_TARGET_RESPONSE.md`와 `K/PLAN.md`를 먼저 읽는다. 같은 native 상태명의 지속시간 추가는 문제 구간을 개선하지 못해 기각했다. 현재 native 대상 차량의 직전 가감속은 조건부5초 RM/VSL 오차를약4% 줄이지만 문제 구간10초 편향+12.5km/h가 남아 자율/이득 검증 성공이 아니다. 다음은 해당 차량쌍 정보를 기존 공간 상태로 표현할 수 있는지 검사한 후 보존되는 이웃 반응의 짧은 자율 예측이다. core/기본설정/native 변경 없음, NOT_QUALIFIED. DESSPEED 기록2/3자리 차이로 중단한 첫 검사와 수정 검증을 모두 보존했다. 이 후속은 로컬이며 아래 푸시에 포함되지 않았다.

**최신 전달·재개점:** `diagnostics/handoff_20260921_transport/README.md`를 먼저 읽는다. 아래 이전 전달 이후의 초기 차량·말단·수송·통과시간 후속까지 포함한다. `K/TRANSPORT_DIFFUSION_AND_PASSAGE.md`와 `K/PLAN.md`가 최신 진단이다. 수치 퍼짐 감소 후보는12개 중10개 속도오차가 늘어 기본 비활성으로 기각했고, 앞선 RM 순위 일치도 말단 경계 변경에 유지되지 않았다. core/기준망/새native 변경 없음, **NOT_QUALIFIED**. 현재/과거 감속·추종 상태의 지속시간·회복 검토가 다음 단계이며 아직 결과는 없다. 과거 보고서의 ‘로컬·푸시 미포함’은 작성 당시의 기록이다.

**최신 재개점(2026-09-21)**: `docs/HANDOFF_20260921_gain_prediction.md`와 `diagnostics/handoff_20260921_matched_response/README.md`를 먼저 읽는다. 누적 모델 수정과 두2550초 상태의 후속48개 예측을 전달했다. 기존 이동거리·분기 후보는 RM 순위를 맞췄지만 이득 크기와 본선 부호를 충분히 설명하지 못한다. 기본 채택 없이 **NOT_QUALIFIED**다. 최신 결과·다음 작업은 `K/MATCHED_SPATIAL_RESPONSE.md`를 따른다.

1. 규칙·정본·함정은 `CLAUDE.md` 를 그대로 따른다(어댑터 1벌, `parameters.json` 단일 출처, vendor 무수정, `git add -A` 금지, 스위치는 config 키만).
2. **최신 현황·다른 컴퓨터에서의 재개**는 `docs/HANDOFF_20260919_cost_and_ramp_response.md`와 `diagnostics/handoff_20260919/README.md`를 먼저 읽는다. 기하 인계는 `docs/HANDOFF_20260916_geometry_actuator_response.md`에 있다. 현재는 사용자 수정 망의 동측 본선 입력만 0.8배인 조건이다. 과거 전역 80/50 조건과 다르며, 새 물리 기하의 full GNE 실행은 아직 지원하지 않는다. 9월 19일 단독 진단 MPC의 비용 집계를 수정했으나 RM/VSL 이득 예측 보정은 미완료다. 이전 controller 정의·8개 독립 미터·실제 합류량 기준 N_UF는 `docs/HANDOFF_20260913_controller_runtime.md`에 있다. 이전 문서의 수치가 최신 사용자 합의와 충돌하면 최신 인계를 따른다.
3. VISSIM 실런은 워크스테이션 한 대에서만 순차로 돈다. 다른 머신에서는 모형/코드 수정과 오프라인 결정 재현(`scripts/offline_harness_20260904.py`, 인계 문서 §5)·fzp 분석까지만 하고, 실런은 조율해서 넘긴다. 실런 중에는 `evaluation/controllers/vissim_stackelberg_adapter.py` 를 편집하지 않는다(결정마다 재-import).
4. 새 기능은 config 키 하나로 켜고(없으면 비트 동일), `python scripts/verify_parameters.py <config>` 가 PASS 여야 한다. 사본 어댑터를 만들면 검증 뒤 지운다.
