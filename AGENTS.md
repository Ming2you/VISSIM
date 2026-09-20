# AGENTS.md — Codex 진입점

**최신 전달·재개점:** `diagnostics/handoff_20260921_transport/README.md`를 먼저 읽는다. 아래 이전 전달 이후의 초기 차량·말단·수송·통과시간 후속까지 포함한다. `K/TRANSPORT_DIFFUSION_AND_PASSAGE.md`와 `K/PLAN.md`가 최신 진단이다. 수치 퍼짐 감소 후보는12개 중10개 속도오차가 늘어 기본 비활성으로 기각했고, 앞선 RM 순위 일치도 말단 경계 변경에 유지되지 않았다. core/기준망/새native 변경 없음, **NOT_QUALIFIED**. 현재/과거 감속·추종 상태의 지속시간·회복 검토가 다음 단계이며 아직 결과는 없다. 과거 보고서의 ‘로컬·푸시 미포함’은 작성 당시의 기록이다.

**최신 재개점(2026-09-21)**: `docs/HANDOFF_20260921_gain_prediction.md`와 `diagnostics/handoff_20260921_matched_response/README.md`를 먼저 읽는다. 누적 모델 수정과 두2550초 상태의 후속48개 예측을 전달했다. 기존 이동거리·분기 후보는 RM 순위를 맞췄지만 이득 크기와 본선 부호를 충분히 설명하지 못한다. 기본 채택 없이 **NOT_QUALIFIED**다. 최신 결과·다음 작업은 `K/MATCHED_SPATIAL_RESPONSE.md`를 따른다.

1. 규칙·정본·함정은 `CLAUDE.md` 를 그대로 따른다(어댑터 1벌, `parameters.json` 단일 출처, vendor 무수정, `git add -A` 금지, 스위치는 config 키만).
2. **최신 현황·다른 컴퓨터에서의 재개**는 `docs/HANDOFF_20260919_cost_and_ramp_response.md`와 `diagnostics/handoff_20260919/README.md`를 먼저 읽는다. 기하 인계는 `docs/HANDOFF_20260916_geometry_actuator_response.md`에 있다. 현재는 사용자 수정 망의 동측 본선 입력만 0.8배인 조건이다. 과거 전역 80/50 조건과 다르며, 새 물리 기하의 full GNE 실행은 아직 지원하지 않는다. 9월 19일 단독 진단 MPC의 비용 집계를 수정했으나 RM/VSL 이득 예측 보정은 미완료다. 이전 controller 정의·8개 독립 미터·실제 합류량 기준 N_UF는 `docs/HANDOFF_20260913_controller_runtime.md`에 있다. 이전 문서의 수치가 최신 사용자 합의와 충돌하면 최신 인계를 따른다.
3. VISSIM 실런은 워크스테이션 한 대에서만 순차로 돈다. 다른 머신에서는 모형/코드 수정과 오프라인 결정 재현(`scripts/offline_harness_20260904.py`, 인계 문서 §5)·fzp 분석까지만 하고, 실런은 조율해서 넘긴다. 실런 중에는 `evaluation/controllers/vissim_stackelberg_adapter.py` 를 편집하지 않는다(결정마다 재-import).
4. 새 기능은 config 키 하나로 켜고(없으면 비트 동일), `python scripts/verify_parameters.py <config>` 가 PASS 여야 한다. 사본 어댑터를 만들면 검증 뒤 지운다.
