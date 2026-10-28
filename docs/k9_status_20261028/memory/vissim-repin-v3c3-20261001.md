---
name: vissim-repin-v3c3-20261001
description: "v3c3 재핀(v3c2 + DSD 81/91/101) 계획 일괄 승인(10-01) — K1–K6 결함 수정(v3c1 기반 GA 관문) → K7 재핀+단일값 VSL(어댑터 사상, L2 3차 보간) → 동결·푸시 → NC 6·RM 3·R-obs → GB 관문"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-10-01T00:58:35.795Z
---

- 계획: D:/VISSIM_runs/20260930_v3c2/reports/repin/REPIN_V3C2_PLAN.md (d4b70c02), 목록 52항목, 검토 REPIN_V3C2_PLAN_REVIEW.md(막힘 B1 provenance 예상 변경 열거, B2 하네스 재조준, B3 K6 고정 두 번째 워크트리).
- 사용자 결정(2026-10-01): 권장안 U1–U12 **일괄 승인**(커밋·푸시·동결·런 발사 포함). 핵심: 망 이름 **v3c3**(v3c2 + N1F 2단계 DSD 81/91/101 블록), NC 동일성 fit 5시드(+s37 해시만), 명령 공간 {80,90,100,110} 유지·어댑터 writer 가 81/91/101 로 사상(VBS 무변경), plant L2(A 1.33, E 0.87, m_v 정확값, (80,90,100,110) 네 점 3차 Lagrange — 110 좌기울기 0.010840), L1 은 생성기 옵션, 10490 은 같은 서비스 그룹의 가장 낮은 녹색 유지, E2 조용한 무시 설치 검사 포함, β 원천 routing_v3c3, 110 미만 쓰기는 첫 J1 런 감사, J1 은 PYTHONHASHSEED=0 고정.
- 이름: 브랜치 claude/repin-v3c3-20261001, 워크트리 D:/VISSIM-merge/sim3-n31-v3c3(9ed2ef0 에서 시작), 런 루트 D:/VISSIM_runs/20261001_v3c3, R-obs 루트 D:/VISSIM_runs/20261001_sdmpc31_v3c3.
- 진행(10-01): v3c3 망 빌드+GB-1 사전선언(wf_34fb6968-093), K1–K6 구현+GA 관문(wf_52852fd7-a01). 다음: K7(v3c3 sha 필요) → 동결 → 푸시 → R-obs·RM 발사 → GB-6~10.
- 묶음 2(도시)는 C3 v2 통과 뒤 따로 옮김. F10 보류, FW_W 구조 진단 진행 중.

- 사용자 결정(10-01 오후): 9000 s 폐루프에서 VSL 은 **단일값 + L2 로 켬**(V0 110 고정 권장을 택하지 않음). 단일값도 방류는 안 늘린다는 점(N1F)은 설명함 — L2 의 목적은 plant 가 VSL 허구 이득을 믿지 않게 하는 것. 첫 J1 런에서 110 미만 쓰기 감사(U9-a) 필수.
- 일정 추정(10-01 12:4x): K7·동결·R-obs·GB 관문 → 10-02 오후 기준선 폐루프 3시드 발사 → 10-03 아침 결과. SC1001 EB 결함은 그때도 남아 있음(기준선으로만 해석).

- 10-01 사건: v3c3 NC 2차 s53·s37 이 SIM_DONE(9000) 뒤 러너가 '^C' 로 중단(run.json completed false, 프로세스 없음, 원인 미상 — 어느 전사에도 kill 명령 없음). 내 감시 스크립트가 완료 확인 없이 verdict 를 돌려 gb1_verdict.json FAIL(MISSING) 이 생김 → gb1_verdict_PREMATURE_20261001T161617.json 로 보존, gb1_amendment_1.md 기록, 런 폴더는 *_interrupted_20261001_1339 로 보존 후 16:20 재발사. GB-1 은 s31/41/43/47 PASS. 교훈: verdict/판정은 완료 확인 조건 안에서만; PowerShell 변수는 대소문자 무시($r 가 $R 을 덮음).
- **사용자 요청(10-01 16:1x)**: U8(C3 2차) 끝나면 지금까지 한 작업·진행 중 작업·앞으로 보정 계획을 정리해 푸시. 위치 = v3c3 브랜치 diagnostics/worklog_20260930_1001/ (K7 커밋·푸시 뒤, 명시 경로 커밋).

- K7(커밋 5개, head 99dc641) 오프라인 관문 O-9 정지: O-3 무신호 목록 23→22(SC103_S_SC6_to_E 0.0472→0.0544), O-5 접선 연산 수 정확식 불일치(예측 비트 동일, κ 편차 ≤2.3e-13, 0 상쇄 횟수 차), O-7 문서, O-8 GWT6 떠돌이 .pyc. **사용자 결정(10-01 17:3x)**: O-3 은 **v3c1 목록 23개 유지**, O-5 는 값 수준 기준으로 정정, O-7·O-8 정리 → 재관문 → 동결·푸시·발사줄(wf_7b972e65-3d4). J1 은 발사기 규칙상 dev 런 동시 2개 → s31·s41 먼저, s43 다음.

- **GB-1 최종 PASS 6/6 (10-01 17:38)**: 재발사 s53·s37 정상 완료, s53 FZP payload = v3c2(K7 RA-1 의 v3c2 s53 대체가 유효), 봉인 s37 은 판정 단어만(전 항목 EQUAL/OK).

- **K7 푸시 완료(10-01 18:31)**: origin/claude/repin-v3c3-20261001 = 6c4c740 (K6 + K7 5 + 정정 2 커밋), FRZ_K7 = D:/VISSIM-merge/frozen/sdmpc31_6c4c7400_202610011831, 발사줄 D:/VISSIM_runs/20261001_v3c3/launch_lines_k7.txt. 정정 선언 K7_AMENDMENT_1.md(1b1d3955) + 결정 기록 K7_AMENDMENT_1_DECISION_NOTE.md(사용자가 O-3 옛 목록·O-5 값 기준 둘 다 승인). 19:10 R-obs3(sdmpc31_v3c3_nc_s31) + 19:11 RM s31/s41/s37(봉인) 발사. 다음: GB-5..GB-10 → J1 s31·s41(묶음 2, -AllowConcurrentDev 는 2번째만) → s43.

- **작업 정리 푸시(10-01 23:xx, 사용자 요청)**: origin/claude/repin-v3c3-20261001 = bd39205, diagnostics/worklog_20260930_1001/ (README 한국어 + 보고서 사본 84개 + SOURCES.json, 86파일). README 의 GB 표는 22:30 시점(GB-1·4·5·6·7 PASS, GB-8~10 진행 중) → GB 결과 나오면 후속 커밋으로 갱신.

- **GB-4..10+S 통과(10-04)**: GB-9 는 결과 본 뒤 판정기 수정(재생 폴더 경로 해시만 제외) → **사용자 수용(10-04)**, 기록 reports/gb/GB9_DECISION_NOTE.md. K7 재핀 검증 완료. SDMPC 반사실 8결정 모두 VSL 110 → J1 U9-a 공허 통과 가능. J1 은 K8(결함 수정+SC1001 EB 안 1 v2) 재동결 뒤(사용자 10-04).

**Why:** 재핀이 묶음 2 를 기다리면 v3c2 결정 상태가 없어 고속도로 선택 점검·폐루프가 막힘 → 사용자가 분리 선승인.
**How to apply:** 관문 실패 시 멈추고 보고. 푸시는 K7 오프라인 관문 통과 뒤. 관련 [[vissim-freeway-entry-dsd40-defect-20260930]], [[vissim-vsl-fixed-dsd-20260928]], [[vissim-network-v3c-20260927]].
