---
name: vissim-k93-bundle2-d1d2-20261024
description: K9-3 묶음 2 = 결정점 1135 분할(D1)·SC1004 서쪽행 경계 용량(D2) 결함 수정, 설계 결정 12개 권장안 일괄(D-K9-80), 워크플로 진행 중 (2026-10-24)
metadata:
  type: project
---
K9-3 = 미터가 움직이게 하는 다섯 단계의 첫 단계(모형이 B1 램프 압력을 보게 함). 이것만으로 미터는 안 움직일 것으로 봄.
- D1: 모형 SPLIT /links/SC1004_W_out 행 (10646 0.5, 자유 0.333, 10681 0.167, 옛 망 2026-09-05 측정표) → v3c3 INPX 결정점 1135 relFlow (0.2, 0.2, 0.6), FZP V-A s31 0.201/0.208/0.592. 키 urban.k93_sc1004wout_split.
- D2: SC1004_S_to_W·SC1004_N_SC1003_to_W 206.53×1차로 → S→W U4 66|p2 F2 1,807.4, N→W 1,850(실측 아님, 신호 movement 유지). 키 urban.k93_sc1004w_boundary_capacity. 나머지 206.53 계열 146개는 미룸.
- 결정(D-K9-80): FZP 는 점검만(C-1 ±0.03, C-2 ±5 %), 런타임 키 단독 허용·배포는 둘 함께(make_config --k93b2), 증거 이름+sha, 블라인드 R-obs v3c3-s47 50상태 부분 노출(U4 66|p2 에 v3b-s47), J 전부·다르면 STOP, F 키 끔보다 크지 않음, 관문 뒤 연쇄 재생 → 폐루프(다시 물음).
- 브랜치 claude/k93-b2-20261024 from c20aff1d, 보충 35, 노트 scratchpad k8/k93/bundle2/, 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/k93_b2. 워크플로 wf_cf6d42db-34c(작업 wnpuuc695) — **10-24 밤 첫 단계(Declare A35)에서 사용자 뜻으로 멈춤**(커밋·보충 35·프로세스 0, codex 인계 검토 대기; 재개는 resumeFromRunId). 비용 어림 48–68 h.
**Why:** 사용자 D-K9-77(D1·D2 먼저)·D-K9-80. K9-2 의 STOP 교훈 10개를 처음부터 규칙에 넣음.
**How to apply:** STOP 오면 원인 설명 후 사용자 결정; 폐루프·푸시는 연쇄 재생 뒤 다시 물음. 관련 [[vissim-meter-never-asked-20261024]], [[vissim-boundary-movement-capacity-206]], [[vissim-j1-k8-results-20261015]].
