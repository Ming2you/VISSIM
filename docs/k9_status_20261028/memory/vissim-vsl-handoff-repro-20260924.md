---
name: vissim-vsl-handoff-repro-20260924
description: 사용자 인계 VSL90(seed29, d80faf9) 은 이 PC 에서 native 로 비트 단위 재현됨. 우리 s31_v2fix90 은 이름만 같은 별도 실험 — 섞어 인용 금지
metadata:
  type: project
---

- **원본**: 망 64cf5f55, seed29, 900 s 부터 DSD63–66(6.342 km, lane drop 6.842 km 500 m 상류)만 110→90. 1099 v1 수요, 진입 vehComp 14 "Freeway entry DSD110", 분포 110 = 75–145(평균 112.3).
- **재현**: D:/VISSIM_runs/vsl_repro_s29 (패키지 native.py prepare + d80faf9 러너, -AllowConcurrent 용 키 1개만 추가). Ω 7263.26719444443/7094.754305555547, 동측 국소 19링크 −6.1531%, 전체+외부 −78.763697(−0.2721%) 전부 증거와 동일. REPRO_RESULT.md.
- **offline reproduce.py**: NC cells 한 값(t=2520.1 cell29 v_kmh) 1 ULP 차이로 exit 1, 나머지·예측 TTT·Δ 비트 동일. 추정=ucrt 수학 라이브러리 경로.
- **우리 fix90/fix70**(seed31, v2 수요, comp 1, 110=98–140, DSD51–66 from 1200 s): +358.8/+554.9 veh·h — 별도 실험의 유효한 손해.
- 지표 넷은 다르다: ①동측 본선 7링크 ②동측 국소 19링크(−6.153% 의 범위) ③Ω ④native 전체+외부 대기(−0.2721%). ⑤450 s offline 은 31셀+커넥터 8.
- seed43 은 같은 정책이 전체 비용 +67.6 손해, 450 s heldout 방향 실패 — 정상 결과로 보존. "90 에서 용량 증가" 를 전제로 보정하지 말 것(사용자 지시).
- sim3-n31 이식 plant 는 패키지 모형과 12 파일 다름(refined partition state_response 지연·physical_cell_fd·head service 제외) → 원본 재현 plant 대조는 패키지 코드로.

**Why:** fix90 을 원본 재현으로 착각해 Carlson 재적합으로 넘어가려다 사용자가 멈춤(2026-09-24).
**How to apply:** 인계 실험 관련 수치는 이 재현 폴더와 패키지 evidence 로만 인용. 새 후보·재보정 전에 조건 차이표부터. 관련 [[vissim-sdmpc31-obs150-state-20260924]].
