# AGENTS.md — Codex 진입점

**최신 SDMPC 재개점(2026-09-22)**: `docs/HANDOFF_20260922_PFO_CAP_SDMPC.md`를 먼저 읽는다. 매 주기 own-cost PFO → 달성 NP/실제 합류 NUF 상한 budget 초기화 구현 및 900초 저장 상태 실측 완료. 신규 테스트 재실행·원 actuator audit·다중 budget·다음 주기·native 검증은 남아 있다.

**최신 재개점(2026-09-21)**: `docs/HANDOFF_20260921_gain_prediction.md`와 `diagnostics/handoff_20260921/README.md`를 먼저 읽는다. 누적 모델 수정과 완료/기각 진단을 보존했으며 RM/VSL 순이득 보정은 여전히 NOT_QUALIFIED다. 아래 09-19 인계는 이전 단계 기록이다.

1. 규칙·정본·함정은 `CLAUDE.md` 를 그대로 따른다(어댑터 1벌, `parameters.json` 단일 출처, vendor 무수정, `git add -A` 금지, 스위치는 config 키만).
2. **최신 현황·다른 컴퓨터에서의 재개**는 `docs/HANDOFF_20260919_cost_and_ramp_response.md`와 `diagnostics/handoff_20260919/README.md`를 먼저 읽는다. 기하 인계는 `docs/HANDOFF_20260916_geometry_actuator_response.md`에 있다. 현재는 사용자 수정 망의 동측 본선 입력만 0.8배인 조건이다. 과거 전역 80/50 조건과 다르며, 새 물리 기하의 full GNE 실행은 아직 지원하지 않는다. 9월 19일 단독 진단 MPC의 비용 집계를 수정했으나 RM/VSL 이득 예측 보정은 미완료다. 이전 controller 정의·8개 독립 미터·실제 합류량 기준 N_UF는 `docs/HANDOFF_20260913_controller_runtime.md`에 있다. 이전 문서의 수치가 최신 사용자 합의와 충돌하면 최신 인계를 따른다.
3. VISSIM 실런은 워크스테이션 한 대에서만 순차로 돈다. 다른 머신에서는 모형/코드 수정과 오프라인 결정 재현(`scripts/offline_harness_20260904.py`, 인계 문서 §5)·fzp 분석까지만 하고, 실런은 조율해서 넘긴다. 실런 중에는 `evaluation/controllers/vissim_stackelberg_adapter.py` 를 편집하지 않는다(결정마다 재-import).
4. 새 기능은 config 키 하나로 켜고(없으면 비트 동일), `python scripts/verify_parameters.py <config>` 가 PASS 여야 한다. 사본 어댑터를 만들면 검증 뒤 지운다.
5. 계산시간을 보고할 때 SDMPC outer iteration 상한·실제 수락 횟수·수렴 여부를 함께 적는다. 단일 예측/Jacobian 측정이면 최적화 iteration을 실행하지 않은 시간이라고 명시한다. endpoint 호출 횟수나 QP 내부 반복을 SDMPC iteration 횟수로 부르지 않는다(2026-09-22 사용자 요청).
