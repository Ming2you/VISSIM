# LOG_GENERAL — 일반형 가드(D-K9-107) 작업 기록

- 이 파일은 날짜·시각(KST)을 붙여 아래로만 더합니다.
- 범위: `guard/general/` 아래 산출과 `D:/VISSIM-merge/k8_gate_trees/c1/guard_general/` 아래 무거운 출력.
- 읽기 전용 원칙: GWT8(c20aff1d), 탐침 트리, codex 트리, 동결본, 런 폴더, 인계 사본, Y: 에는 쓰지 않습니다. VISSIM·COM·러너·동결·plant 잡·결정 재생 0.

## 2026-10-27 16:24 KST — 재고 조사(Inventory) 시작

- 할 일: `general/INVENTORY.md` + `general/inventory.json`. (1) 제어 신호 17개의 머리 차로 묶음·저장 용량·현시·받는 쪽, (2) 머리 없는 공급 구간과 방류 서버, (3) 미터 8개 저장과 지금 M4, (4) 결정 시각 관측 가능성과 codex USG configure 가 이미 세는 것.
- 사용자 말(이번 요청): Ω701 = 보호망 + 바깥→안 접근로, Ω701 이 맞는 목적 영역. FW_W 는 거의 제어되지 않음 → 감시만. FW_E 가 개선의 대부분이고 FW_E 가 안 움직이는 게 더 문제. 도시도로 정의는 codex 판.
- heavy.lock 상태(16:20): 주인 `vsl_plant`(pid 34924, 16:16:47 시작). 무거운 FZP 스캔은 잠금이 풀린 뒤 차례로.

## 2026-10-27 16:37 KST — 망·설정 사실 추출, FZP 정지 간격 스캔 발사

- [실행] `general/tools/inv_net.py`(v3c3 .inpx `3de889f0…` 읽기) → `general/work/net_facts.json` sha `93b535fb0fd3bf02…`. 링크 1,236 · 신호 머리 537 · 신호 제어기 50 · 입력 34 · 정적 경로 결정 138 · 대기 계수기 98 · DCP 314.
- [실행] `general/tools/inv_usg_b.py` → B v3c3-s31 T=900 결정 JSON 의 codex USG observation(210 머리 차로) → `general/work/usg_b31_T900.json` sha `6ea25eb30bb64e78…`.
- [실행] `general/tools/inv_build.py` 초안(정지 간격 없이) → `general/work/inv_draft.json`. 머리 차로 235, 머리 없는 공급 구간 416, 미터 8, 진출 8.
- [실행] `general/tools/inv_spacing.py`(sha `ee6c8adf405425dc…`) 합성 FZP 자기 시험: 쌍 3개, 중앙 6.0 m(기대 6.0), 시험 잠금은 scratch 안 파일(실제 heavy.lock 손대지 않음).
- 정지 간격 정의(스캔 전 고정): 같은 프레임·같은 링크·차로에서 앞 위치로 정렬한 이웃 쌍, 둘 다 속도 < 1.0 km/h(제어기 관측 정지 문턱), d = 앞차 Pos − 뒷차 Pos(= 앞차 길이 + 간격). 권장 값 = 모든 정지 쌍 d 의 중앙값.
- [실행] 16:37 발사: `inv_spacing_launch.ps1` → WMI, BELOW_NORMAL, PID 37616, 대상 FZP 하나(NC3 v3c3-s31). 스크립트가 heavy.lock 을 배타 생성으로 잡고 끝에 자기 잠금만 지움. 출력 `D:/VISSIM-merge/k8_gate_trees/c1/guard_general/spacing_nc3_s31.json`.
- 16:35 확인: 앞 주인 vsl_plant 의 잠금은 이미 풀려 있었음(그쪽 잡 끝남, 우리 지움 아님).

## 2026-10-27 16:47 KST — 스캔 재발사(잠금 대기 간격만 바꿈)

- 16:45 에 vsl_plant 가 잠금을 풀고 곧바로 다시 잡았습니다(pre4). 우리 대기 간격 15 s 가 그 틈을 놓쳤습니다.
- [실행] 우리 프로세스만 멈춤(cmd 37616, python 48764; 그때 잠금 주인은 vsl_plant, 우리 아님). `inv_spacing.py` 의 대기 간격 15 s → 2 s 만 바꿈(셈 줄 불변). 재발사 PID 7680(WMI, BELOW_NORMAL). 다른 세션 프로세스·잠금은 건드리지 않음.

## 2026-10-27 16:53 KST — FZP 정지 간격 스캔 끝

- [실행] 잠금 획득 16:51:46(대기 302 s), 잡고 있던 시간 90.7 s, 16:53:17 자기 잠금만 지움. 그 뒤 잠금은 다른 워크플로(fwe_decomp, 16:59)가 잡음 — 우리와 무관.
- [실행] NC3 v3c3-s31 FZP(sha `f8476f83e2c70821…`, 프레임 1,799, 행 6,654,249 = OMEGA701 표의 행 수와 같음). 정지 쌍 1,224,818. 앞범퍼 거리 d 중앙 5.96 m(스캔 전 고정 규칙), 평균 6.41 m, 정지 틈 중앙 1.51 m. 앞차 ≥ 7 m 쌍 중앙 11.72 m. → `general/work/spacing_nc3_s31.json` sha `f2bd7561f3e45d4d…` (D: 출력과 같은 sha).
- 데이터 뒤 추가(스캔을 본 뒤): 평균 간격 6.41 m 변형, 차로 프레임 차 길이 + 1.51 m 의 “길이” 점유 변형.

## 2026-10-27 17:00 KST — 재고 조사 산출 (판정 아님)

- [실행] `inv_build.py` → `general/work/inv_build.json` sha `52d008ee67bef3a7…`: 제어 SC 17, 머리 235(현시 216 + 미드블록 18 + 영구 적색 1), 접근 묶음(SC×링크) 66, 머리 없는 공급 구간 416(링크 119·커넥터 297; Ω701 안 380), 미터 8, 진출 8, 정적 경로 362.
- [실행] codex USG 대조: B v3c3-s31 T=900 관측 210 차로와 용량·받는 쪽 차 0. USG 가 빼는 현시 차로 6(SC11 p1 ×2 = 상류 native SC18 머리, SC12 p3·p4 = 상류 native SC13 머리, SC7 공유 정지선 ×2).
- [실행] 위상: FW_E 진출 4개 중 10483(→124 차로 1)·10682(→121 차로 1)은 FW_W 미터 RM_C10480·RM_C10646 의 줄만 막을 수 있음. 10481 → 127(SC1001 p3/p4), 10643 → 126 → 71(SC1004 p3/p4).
- [실행] `inv_occ.py` → `general/work/occ.json` sha `cd4ba7f4d5edce57…`: V-A·B 상태 330개 + 차로 프레임(sha 대조). B 의 127 차로 1 최대 96/91/79대, 점유 ≥ 1.0 은 6 m·중앙·평균·길이 넷 모두 0결정(데이터 뒤). 용량 < 2대 짧은 구간 150개는 차 1대로 ≥ 1.0.
- [실행] `inv_final.py` → `general/inventory.json` sha `c8584f367c968888dd40d6674634b3c909c21a68536b5ad4d1ecae5368cbe9b1`, `general/INVENTORY.md` sha `da6ecda4413e37552274619c7def6ca71302f97dc723de59c4739c0da74084be`. 전체 sha 목록 `general/SHA256SUMS.txt`.
- 확인: GWT8 head `c20aff1d`, status 0줄. 런 폴더·동결본·codex·탐침 트리 쓰기 0. VISSIM·COM·러너·plant 잡 0. 봉인 시드·v3c3-s47·64cf-s59/61/67 열람 0. kill = 우리 대기 프로세스 둘만(16:47).

## 2026-10-27 17:10 KST — 자료 단계(DATA) 시작: 정의를 스캔 전에 고정

- 할 일: NC3·V-A·B·VSL-only × v3c3-s31/s41/s43(12런), 재고 구간마다 차로 점유 계열(결정 시각 150 s 스냅숏 + 300 s 칸, 900–9,000 s), 넘김 수(≥ 1.0·≥ 0.9, 차로·링크), 실제 번짐 사건과 첫 넘김의 시각 비교, B 결정 JSON 의 codex USG 발동 추출. 산출 `general/DATA.md` + `general/data.json`.
- 사용자 말 반영: Ω701 이 목적 영역(맞음), FW_E 가 주 개선 대상, FW_W 는 감시만, 도시도로 = codex 분할(D-K9-104).
- [실행] VSL-only 망(`baseline_s31_v3c3vsl.inpx`)과 NC3 망의 차이는 평가 출력 켜기·검지 측정 추가뿐(링크·커넥터·머리 기하 같음, `diff` 로 확인). 그래서 같은 재고 구간을 씁니다.
- 새 FZP 스캔이 필요한 까닭: NC3·VSL-only 는 결정 상태 파일이 없어 구간 점유가 없고, 네 팔 모두 5 s 단위 번짐 사건(꼬리 위치·정지 차)은 기존 출력에 없습니다(occ.json 은 V-A·B 결정 시각 대수만).
- 스캔 전 고정 정의(이번 결과를 보기 전에 정함. 다만 앞선 자료를 본 뒤라 모두 "데이터 뒤" 로 적음):
  - 구간 = `inv_occ.py` 의 구간 목록 그대로(현시 머리 차로 216, 공급 차로, 미터 머리 앞·접근 차로, D5) + 진출 착지 구간(착지 ~ 서버 쪽 끝, 착지 차로) + 고속도로 갈림 차로 창([갈림 − 500 m, 갈림]).
  - 점유 = 구간 안 차 수(FZP 앞끝 Pos 기준) ÷ (길이 ÷ 간격), 간격 6 m / 5.96 m / 6.41 m, 그리고 길이 점유 Σ(차 길이 + 1.51 m) ÷ 길이.
  - 스냅숏 = 결정 T(900, 1,050, …, 8,850 s; FZP 마지막 프레임 8,995.1 s 라 9,000 s 없음)의 프레임 T + 0.1 s. 300 s 칸 = 5 s 프레임의 시간 평균과 최대.
  - S0(위 끝 정지) = 구간 위 끝 12 m(구간이 더 짧으면 전체) 안에 속도 < 5 km/h 차가 있음.
  - S(번짐) = S0 이고, 그 차에서 아래로 이웃 차 사이 빈 틈(앞차 뒤끝 − 뒷차 앞끝) ≤ 20 m 로 이어진 줄이 구간 아래 끝에서 max(20 m, 0.2 × 길이) 안까지 닿음. 구간 길이 ≤ 12 m 면 S = S0.
  - 사건 = S 프레임 묶음(60 s 이하 틈은 이음). 위 교차로 막힘 = 위 경계가 정지선인 공급 구간의 S. 고속도로 차로 막힘 = 진출 커넥터 S0 그리고 갈림 차로 [갈림 − 100 m, 갈림] 에 속도 < 20 km/h 차가 있음.
  - 시각 비교: 사건 시작 t0 에 대해 [t0 − 300, t0] 안 첫 넘김 = 앞섬, (t0, 사건 끝] 안 첫 넘김 = 늦음, [t0 − 300, 사건 끝] 에 넘김 없음 = 놓침. 넘김 결정 T 에 대해 [T − 150, T + 300] 에 S 프레임이 없으면 = 헛켜짐.
- 실행 규칙: 한 프로세스가 FZP 12개를 차례로, 파일마다 heavy.lock 을 배타 생성으로 잡고 끝나면 자기 잠금만 지운 뒤 25 s 쉬고 다음. WMI 분리 발사, BELOW_NORMAL, PYTHONHASHSEED=0, python -B. B 결정 JSON(약 6 GB/시드) 읽기도 같은 잠금 아래 한 작업으로.

## 2026-10-27 17:13 KST — 구간 스캔 발사

- [실행] `general/tools/gd_scan.py` 합성 FZP 자기 시험(`gd_selftest.py`, 시험 잠금은 scratch 안 파일) 11항목 모두 맞음: 꽉 찬 줄 S0·S, 떨어진 정지 차 하나는 S0 만, 움직이는 차는 표시 없음, 고속도로 창 느린 차·평균 속도, 화물 차 섞인 줄 S.
- [실행] 17:13 발사 `gd_scan_launch.ps1` → WMI, BELOW_NORMAL, cmd PID 35340 / python PID 36832. 순서 B·V-A·NC3·VSL × v3c3-s31, s41, s43. 파일마다 heavy.lock 잡고 풀고 25 s 쉼. 출력 `D:/VISSIM-merge/k8_gate_trees/c1/guard_general/data/<런>.npz` + `.meta.json`, 기록 `gd_scan.log`.

## 2026-10-27 17:34 KST — 구간 스캔 끝, 분석 실행

- [실행] FZP 12개 스캔 끝(17:13:14–17:33:38). 파일마다 잠금 잡은 시간 23.9–33.3 s. VSL v3c3-s31 차례에서 다른 워크플로(vsl_plant, 17:15:33 잡음)를 574 s 기다림. 잠금 풀림 기록 12/12, 우리 python 프로세스 남은 것 0. 지금 잠금 주인은 vsl_plant(우리 아님).
- [실행] 대조: FZP 결정 스냅숏 대수 대 제어기 상태 파일 대수(V-A·B, occ.json): 같은 몫 0.986–0.988, 나머지는 ±1대(±2대 0–3칸).
- [실행] `gd_usg.py`: B 결정 JSON 165개의 앞부분(약 1 MB)만 읽어 codex USG 기록 추출(가벼운 일, 잠금 없이 2.5 s) → `general/work/data/usg_b.json`.
- [실행] `gd_analyze.py` → `general/work/data/data_full.json`(32 s). 결과 일부(시드 31 세 팔)를 본 뒤 "≥ 30 s 사건" 거름과 번짐 프레임 점유 분포를 더했습니다(데이터 뒤).

## 2026-10-27 17:46 KST — 자료 단계 산출 (판정 아님)

- [실행] `gd_analyze.py` 최종 실행 → `general/data.json`(= `work/data/data_full.json`). 결과를 본 뒤 더한 것(데이터 뒤): 엄격 번짐(S 이고 구간 차 80 % 이상 5 km/h 미만), 머리+공급 차로 용량 ≥ 5·≥ 10 대 민감도, 신호별 켜짐 결정 수.
- [실행] `gd_render.py` → `general/DATA.md`. sha 목록 `general/DATA_SHA256SUMS.txt`.
- 주요 사실(데이터 뒤): 머리 차로 S 순간 6 m 점유 중앙 0.90–0.92, ≥ 1.0 몫 13–25 %. 30 s 이상 번짐 사건 앞섬(차로 6 m ≥ 1.0) NC3 0.5–2.0 %, VSL-only 0.8–1.9 %, V-A 10.6–15.8 %, B 7.3–7.8 %; 헛켜짐 런마다 0–1. 127 차로 1 의 6 m ≥ 1.0 은 12런 0 결정. FW_E 진출 고속도로 막힘 런마다 0–45 s. 미터 머리 앞 6 m ≥ 1.0 0 결정(B RM_C10639 번짐 2,660·4,455 s 중에도). V-A 에서 켜질 구간: 6 m ≥ 1.0 39, ≥ 0.9 59, 길이 ≥ 1.0 52.
- 확인: GWT8 head `c20aff1d`, status 0줄. heavy.lock 없음, 우리 python 프로세스 0. 런 폴더·동결본·codex·탐침 트리 쓰기 0. 봉인 시드·v3c3-s47·64cf-s59/61/67 열람 0. 이 단계 kill = 우리 백그라운드 셸 둘(느린 대조 1, 진행 감시 tail 1)만.

## 2026-10-27 17:53 KST — 설계 r0 준비: 가장 가까운 꼴 둘을 기존 스캔 출력으로 셈 (가벼운 일)

- 까닭: 자료 단계(DATA)는 "차로 6 m ≥ 1.0 / ≥ 0.9 / 길이 ≥ 1.0 / 링크" 만 셌습니다. 사용자 말 그대로의 꼴이 사슬·미터에서 켜지지 않아, 설계 문서가 권할 "가장 가까운 꼴"(결정 시각 관측 번짐 S, 그리고 6 m ≥ 1.0 ∨ S)의 숫자가 필요했습니다.
- [실행] `general/work/gg_trig.py`(sha `1aa627c1fee75235…`) → `general/work/gg_trig.json`(sha `f25fe6344d87e7c5…`). 입력 = 기존 `guard_general/data/<런>.npz` 12개 + `segments.json` 만(FZP 읽기 0, VISSIM·COM 0). 4 s, 잠금 없이(npz 12개 약 18 MB 읽기). PYTHONHASHSEED=0, python -B. 정의는 `gd_analyze.py` 와 같음(앞섬 창 300 s, 헛켜짐 [T − 150, T + 300], ≥ 30 s 사건). 대조: 차로 6 m ≥ 1.0 의 머리 차로 칸이 DATA §5 표와 같음(예 NC3 v3c3-s31 577: 9/13/555 · 켜짐 18 · 헛 0).
- 데이터 뒤. S 꼴의 헛켜짐 0 은 구성상(결정 시각에 S 면 그 자체가 번짐 프레임)입니다.
- 확인: GWT8 head `c20aff1d`, status 0줄. heavy.lock 은 다른 워크플로 것(건드리지 않음). 런 폴더·동결본·codex·탐침 트리 쓰기 0. 봉인 시드·v3c3-s47·64cf-s59/61/67 열람 0.

## 2026-10-27 18:06 KST — gg_trig 다시 셈 (사슬 요약에서 짧은 구간 뺌)

- [실행] 사슬 요약(`/chains`)이 짧은 구간(6 m 용량 < 2대, 예 L:10643:126:1·2 = 5.9 m)을 포함해 차 1대로 켜지던 것을 고쳐 뺐습니다(종류별 `/agg`·`/dec_any` 는 처음부터 짧은 구간을 뺐음, 값 불변). `general/work/gg_trig.py` sha `8c3f6f046e014b08…` → `general/work/gg_trig.json` sha `212774be1ce22d21…`(앞 판 `f25fe634…` 는 덮어씀). 4 s, 잠금 없이, PYTHONHASHSEED=0, python -B. 데이터 뒤.

## 2026-10-27 18:12 KST — 설계 초안 r0 `general/GENERAL_GUARD_DESIGN.md` (판정 아님)

- [실행] 보충 C1-2 설계 초안 r0 를 씀. sha256 `a53cb4f334a8962373551495da400e2fc9c07effab5e449221bee85948d59516` (같은 폴더 `.sha256`). r2(`553227cd…`) §2 의 좁은 A+B 를 일반형 하나로 바꿈. D98(r2 §3; D98-5 글 한 줄만 고침)·스레드 정정(r2 §4 글자 그대로)·도시도로 정의(D-K9-104, codex 분할)·G6–G12(G10·G11 바뀜) 실음.
- 권장(데이터 뒤): 넘음 = U(차 수 ≥ 1.0 × 길이/6 m 또는 관측 번짐), 차로 단위, 짧은 구간(< 2대) 원천 제외, 공급 구간 사슬 이어짐 귀속, 진출 착지 원천, 미터 M4 0.9 + OR, codex 무게·반공간 r = 2 s, 구간 표 = 오프라인 증거(이름 + sha). 결정 질문 GG1–GG12.
- 사용자 말 그대로(차로 6 m ≥ 1.0)는 127·129·10491 사슬 12런 중 1결정(NC3 v3c3-s31 3,150 s), 미터 머리 앞 0결정이라 그대로 적고 가장 가까운 꼴 U 를 권함. U 는 B 사슬 1,950 / 1,800 / 1,800 s, V-A 머리+공급 53 / 54 / 54 결정(54 중).
- 확인: 코드·브랜치·커밋·푸시·동결 0, VISSIM·COM·러너·plant 잡·결정 재생·FZP 스캔 0, heavy.lock 안 잡음(남의 잠금 건드림 0), kill 0. 봉인 시드·v3c3-s47·64cf-s59/61/67 열람 0.

## 2026-10-27 18:52 KST — 설계 초안 r0 검토, r1 (판정 아님)

- 할 일: `general/GENERAL_GUARD_DESIGN.md` r0(`a53cb4f3…`)을 적대적으로 검토하고 고친 것을 r1 로. r0 는 `general/GENERAL_GUARD_DESIGN_r0.md`(같은 sha)로 남김. 검토 `general/REVIEW_GENERAL.md`.
- [실행] 가벼운 셈 둘(기존 npz 12개 + segments.json + inventory.json + 현시 계획만 읽음, FZP 0, 각 3 s 안, PYTHONHASHSEED=0, python -B): `general/work/review/gr_check.py`(`16c9cce3…`) → `gr_check.json`(`be9385c6…`), `gr_meter.py`(`074ee468…`) → `gr_meter.json`(`3c8b99ba…`). 그때 heavy.lock 은 다른 워크플로 것이었고 건드리지 않음(무거운 일 없어 잡지 않음).
- 찾은 것(데이터 뒤): 구간 겹침 61쌍·105구간(무게 이중 셈, 사슬 "다음 구간" 미정, 129 예가 표에 없는 구간 씀) · 받는 쪽 261 중 137 이 자료 밖 · 짧은 받는 쪽 × U 로 −1 결정 V-A 39 / 39 / 31(차 수만이면 16 / 23 / 11, codex B 실측 12 / 21 / 1) · FW_E 미터: r0 (가) B 꼴 RM_C10639 21 / 0 / 31·RM_C10681 15 / 13 / 18 미터·결정, (라) 14 / 0 / 26·0 / 2 / 1 · SC7 동시현시는 같은 무게에도 행 · "최대 2 s" 는 가중 초 · U 앞섬의 87–96 % 가 되풀이 번짐(구성상) · V-A 꼴 행 없는 결정 0 · 받는 쪽 없는 현시 머리 차로 3 · SC108 V-A s41 23 → 24.
- r1 반영: 겹침 최댓값·칸 그래프(차로 바꿈 포함)·`R:` 받는 쪽 구간·같은 무게 0·GG0·GG13 새로·GG6 권장 (가) → (라)·S_G K0·멈춤 6 독립 재계산·P0-15/17/18 고침·D-K9-110 FW_E 기준 줄 자리(§3.11)·결정 기록 sha 갱신(4d47ce5b…).
- r1 sha256 `cffbef23ad1c185174bb5639e7e062ab4f525b1924a9d35f36a83caaf85596b0`, 검토 sha256 `d4914bbd6b4e1b8ca4e91bffdf55b9f636f80f2ba5ce7e4fd0e3b8825bdf908c` (같은 폴더 `.sha256`).
- 확인: GWT8 head `c20aff1d`, status 0줄. 코드·브랜치·커밋·푸시·동결 0, VISSIM·COM·러너·plant 잡·결정 재생·FZP 스캔 0, kill 0. 봉인 시드·v3c3-s47·64cf-s59/61/67 열람 0. 탐침·codex 트리·동결본·런 폴더·인계 사본·Y: 쓰기 0.
