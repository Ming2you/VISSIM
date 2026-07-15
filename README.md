# VISSIM ↔ Numerical-Sim 통합 워크스페이스

PTV Vissim 2020 (SP14) 플랜트와 [Numerical-Sim](https://github.com/Ming2you/Numerical-Sim)
(Stackelberg MPC 계층 제어) 모델을 COM으로 결합해 컨트롤러를 라이브 평가하는 워크스페이스.

- **플랜트**: `network/modi_eval_vsl_8seg.inpx` — 도시 6교차로 그리드(A–F) + 양방향 freeway
  본선(방향당 8 제어 세그먼트, off-ramp S2/S4·on-ramp S3/S5, 세그먼트당 램프 1개) +
  D/F 트럼펫 인터체인지. 본선은 진입/유출 연장 링크(35–38)로 확장 (기존 링크 33/34 무수정).
- **모델 기준**: Numerical-Sim `feature/segment-agents-13p` (8-seg, merge 3/5, off 2/4).
- **결합**: `scripts/run_stackelberg_vissim_controller_8seg.vbs` (COM 러너, 180초 결정 주기,
  vehicle-scan 8-bin 상태, `_w` 펄스 수요 + WARMUP_NC 지원) ↔
  `evaluation/controllers/vissim_stackelberg_adapter.py` (state json → 모델 → action csv).

## 실행 방법 (요지)

```powershell
# 반드시 PowerShell에서 (한글 경로 때문에 Git Bash 금지), CodeMeter 서비스 확인
cscript //nologo scripts\run_stackelberg_vissim_controller_8seg.vbs `
  <net.inpx> <state.csv> <action.csv> <decisions_dir> `
  10800 <urbanVph> <freewayVph> 180 <seed> `
  evaluation\controllers\vissim_stackelberg_adapter.py `
  evaluation\calibration\vissim_network_calibration_v2_8seg_20260714.json `
  evaluation\configs\tuning_turning_ratios_route_manifest_v2_20260715.json `
  sym <controller> "0.5:3600:300:3600:300"
```

장기 런은 반드시 워치독 체인으로: `scripts/run_8seg_w_chain_watchdog.ps1`
(5분 무진행 → kill+재시작, resumable). VISSIM COM은 조용히 hang한다.

## 헤드라인 결과 (2026-07-15, sweet_190_w: T=10800, 웜업 3600s, 분석창 TTT veh·h)

| 컨트롤러 | 균일 턴비율 | v1 정렬(결함) | **v2 정렬+demand fix** |
|---|---|---|---|
| no-control | 2244.1 (기준) | — | — |
| PFO | +18.66% | +2.09%¹ | **+21.77%** |
| P-Stack | +3.73% | −0.62% | **−0.10%** |

¹ v1 PFO는 4-seed paired 스윕에서 +4.71% ± 3.71 (4/4 양수) — "우연한 마비"였음 (아래 참조).

1-step(180s) 예측오차 (total bias): v1 −414~−576 veh → **v2 −45~+78 veh** (≈90% 소거).

---

## ✅ 잘 된 것

1. **8-seg 플랜트 전환 완결** — 5-seg → 방향당 8-seg (세그먼트당 램프 1개, 수치모델과 1:1).
   기존 링크 무수정 원칙(연장 링크 + 4m 커넥터)으로 램프/라우팅 좌표 전부 보존.
   설치는 전부 COM 스크립트로 재현 가능 (`scripts/install_eval_vsl_8seg.vbs`).
2. **`_w` 웜업 구조 이식** — 수치모델의 펄스 사다리꼴(0.5×웜업 3600s → 300s 램프 →
   플래토 3600s → 300s 하강)과 WARMUP_NC(웜업 중 전 arm no-control)를 러너에 구현·검증.
3. **캘리브레이션 3연타로 예측오차 ~90% 소거**:
   - 턴비율 v2: route_manifest `link_seq` 직접 파싱으로 **경계 유출 포함 완전 β** 구축
     (`evaluation/configs/tuning_turning_ratios_route_manifest_v2_20260715.json`)
   - 러너 demand 수정: state json에 펄스 스케일 반영 (테일 2× 수요 예측 버그 제거)
   - VSL 110 km/h 속도분포 누락 발견·추가 (5-seg 시절부터 잠복)
4. **prediction audit 파이프라인 재가동** — 결정마다 1-step 예측 vs 실측이 자동 기록되고,
   오프라인 replay(`scripts/replay_discharge_hypothesis.py`)로 라이선스 없이 가설 검증 가능.
5. **P-Stack이 VISSIM에서 최초로 no-control 우위** (−0.62% v1 / −0.10% v2, 전 구성 강건).
   D램프 미터링 실작동 (587–1414 vph 가변). freeway 붕괴 레짐(sweet_190, 평균 59 kph)도
   새 수요 매핑으로 처음 열림 — 5-seg 시절 "메터링 무대 없음" 한계 해소.
6. **운영 안정화** — 워치독(5분 무진행 kill+재시작) 실전 검증(hang 1회 자동 복구),
   CodeMeter 정지/한글 경로 인코딩/PS 파이프 조기종료 등 gotcha 문서화.

## ❌ 잘 안 된 것 (정직한 기록)

1. **PFO의 urban green 채널은 이 플랜트에서 부러져 있음** — 오늘의 핵심 부정 결과.
   상태 예측이 거의 정확해진 v2에서도 +21.77%로 실패. 원인은 상태 예측이 아니라
   **green 응답 민감도(∂비용/∂green)**: 모델이 green 재배분의 이득을 과대평가해
   major 축을 굶기는(44~54s, 최소 22s) "자신 있게 틀린" 재배분을 한다.
   v1의 +2.09%는 틀린 턴비율이 만든 우연한 마비(green을 거의 안 움직임)였다.
2. **턴비율 v1의 데이터 버그** — 감사 diag 표(`urban_turn_split_diag.md`)가 같은 노드
   경계 유출을 조용히 제외하는 걸 그대로 신뢰 → 경계 유출 β 전부 누락 → 모델이 mass를
   내보낼 출구를 모름 (urban bias −474). 교훈: 파생 문서 말고 원본(manifest)에서 재구축.
3. **movement 용량 가설 기각** — "공통 상수 cap(1800)이 병목" 가설은 replay에서 4% 효과로
   기각. 구조 수정 전에 오프라인 replay로 가설을 죽인 것 자체는 잘한 프로세스.
4. **잔여 구조 bias** — 수요 레벨과 무관한 상수 ~200 veh의 링크 점유 과예측
   (모델-플랜트 링크 회계 offset), boundary 게이트 대기 과소예측(+90~150).
5. 잡버그들: PS 스크립트 무BOM(한글 경로 CP949 오독으로 27회 전멸), PS 함수 반환값
   파이프라인 오염(실패가 "all OK"로 오보), `tail -f`의 진행 파일 잠금 등 — 전부 수정·문서화.

## 📋 앞으로 해야 할 일

1. **green 응답(서비스) 곡선 재캘리브레이션** — 최우선 구조 타깃. 좌표 확정됨:
   모델의 `green_fraction × movement_capacity` 서비스가 green 변화의 실효익을 과대평가.
   후보 경로: `scripts/analyze_signal_green_fit.py`/서비스커브 자료로 green 민감도를
   플랜트에서 실측 후 candidate-ranking 레벨에서 검증. 그 전까지 **PFO green 채널 동결 권고**.
2. **링크 회계 offset (~200 veh) 해소** — 링크 지연 버퍼/저장 계상의 모델-플랜트 차이 진단.
3. **prediction audit scale 재적합** — 현재 스케일(freeway 0.651 등)은 2026-06 구모델 기준.
   `scripts/update_prediction_audit_calibration.py`로 8-seg 데이터 재적합 (진단용).
4. **155_w v2 재검증** — PFO −1.75%/P-Stack −0.61%가 v1 기준 → v2로 재확인.
5. **카나리아 3성분 재캘리브레이션** — leader_hinge/np_deadband/leader_mfd_far가
   구 merge {4,6} 기하 튜닝 (수치모델 쪽 결정, stackelberg_mpc.py 카나리아가 경고 중).
6. skew 셀(155_skew_w 등) VISSIM 대응 — `urban_west_east_ratio`의 러너 구현 필요.
7. P-Stack seed 스윕 — 현재 −0.1~−0.6%가 단일 seed. PFO처럼 4-seed paired로 유의성 확인.

## 저장소 구성

```
network/                  # VISSIM 플랜트 (8-seg 최신 + 5-seg 아카이브)
scripts/                  # COM 러너·설치·프로브·replay·워치독
evaluation/controllers/   # 어댑터 (vissim_stackelberg_adapter.py)
evaluation/calibration/   # 캘리브레이션 json (v2_8seg = 현행)
evaluation/configs/       # tuning json (턴비율 v2 = 표준)
evaluation/vsl_install/   # 8-seg 세그먼트/DSD 매핑
evaluation/runs/          # 결과 (state/action csv + 요약; 대용량 decision json은 제외)
```

주의: `evaluation/runs/*/decisions_*`(결정별 state/action json 원본)과 replay 원시 출력은
용량 문제로 커밋에서 제외 — 원본은 로컬 워크스페이스에 있음.
