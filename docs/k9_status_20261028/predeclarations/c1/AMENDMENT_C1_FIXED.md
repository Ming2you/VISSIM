# 보충 C1 고정점 (ReviewDeclare C1, 2026-10-27 KST)

이 파일이 고정점입니다. 아래 sha256 과 다른 보충 C1 로는 C1 의 어떤 단계(P0·미니 탐침·브랜치 `claude/c1-port-20261027` 만들기·커밋·관문·재생·판정·독립 검증)도 하지 않습니다(보충 C1 S-C1-1). 판정 단계 토큰 `c1t` 와 함께 쓰는 "보충 C1 고정판 sha" 는 아래 64자입니다. Declare 판 sha 는 앞 16자만 적습니다(되돌린 파일이 통과하지 않게, 보충 32·33 고정점과 같은 까닭). 이 시각 뒤에는 보충 C1 을 고치지 않습니다. 바꿔야 하면 새 보충에 까닭을 적습니다.

| 문서 | sha256 | 크기 |
|---|---|---|
| `SP/K8_PREDECLARATION_AMENDMENT_C1.md` (검토 판 = 고정판) | `a98580dd2d787007ab961d692668c4a4042c79d7993f87af972cbc19d1f53acf` | 156,456 B, 834줄, LF, CR 0 |
| [보충 C1 §0, §14] 선언 고정 목록 `C1D/declared/PINS_C1_DECLARE.sha256` (검토가 바꾸지 않음) | `ad84aa2f64754ed8e87a4a8834845520585ce1b6e377313621ba49c057fe3a28` | 53줄, `sha256sum -c` 53/53 OK |
| [보충 C1 §2.1] `c1_port` 구역 `C1D/declared/c1_port_section.json` (정규 JSON `c2f3cf19cf6d95e7…`, 검토가 바꾸지 않음) | `865cc354e498f1c77894f376e249682d52ee082639eaa585ec13af5f0d059654` | — |

- **고정 시각: 2026-10-27T11:57+09:00** [실행 `Get-Date` 11:57:06]. 고정판은 11:55 에 마지막으로 바뀌었고 그 뒤 바뀌지 않았습니다( 같은 폴더 위 `SP/K8_PREDECLARATION_AMENDMENT_C1.md.sha256` 도 위 값과 같음 [실행 `sha256sum -c` OK]).
- 줄임말: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CP = `SP/c_port`, C1D = `CP/c1`, GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, TC1 = `D:/VISSIM-merge/k8_gate_trees/c1`(아직 없음), RC1 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/c1`(보고 사본).
- 검토 전 판(`_r1`): `SP/K8_PREDECLARATION_AMENDMENT_C1_r1.md` = `f57821001a045064…`(106,033 B, 701줄; 64자는 그 `.sha256` 과 보충 C1 머리·§18). Declare 단계가 10:47 에 쓴 판과 바이트가 같습니다 [실행 `cmp`].
- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `bbfe77b087bf41c6ec7810b145d45802cc36efbad88622a09c6737f4467a8863`(작업 지시 값과 같음), 설계 초안 r2 `CP/C1_DESIGN_DRAFT.md` = `c32e1006…`, 종합 r2 `CP/C_PREP_RESULTS.md` = `4b58fb4e…`.
- 데이터: **C1 데이터 0개.** TC1 없음, `C1D/C1_VALUES.json`·`C1D/tools/` 없음, P0·탐침·관문·재생·plant 잡 출력 0 [실행]. GWT8 head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(브랜치 `claude/k92-b1-20261016`), `status --porcelain` 0줄, `claude/c1-port-*` 브랜치 0(만들지 않음), 푸시 0 [실행].
- 이 검토에서 한 일: 읽기 전용 점검과 가벼운 검토 도구 셋(실행 전 sha 를 LOG 에 고정). VISSIM·COM·러너·동결·결정 재생·plant 잡·커밋·브랜치·푸시 0. LOCK 0(가벼운 읽기만; 검토 중 `heavy.lock` 은 다른 워크플로가 가짐, 건드리지 않음). 끈 프로세스 = 내 검토 도구 3(`rev_c1_robs.py`, PID 20892) 하나 — V-A 결정 JSON 전부(약 10 GB)를 읽게 짜여 가벼운 일이 아니어서 출력 전에 끄고 가벼운 3b 로 바꿈. 다른 세션의 python(23292·21020)·VISSIM(4개)은 건드리지 않음. 쓴 곳: SP 의 보충 C1·`_r1`·두 `.sha256`, `C1D/review/`, 이 파일, `C1D/LOG.md` 덧붙임, RC1 사본. 동결본·런 폴더·CX·FRZ_B1·인계 사본·Y: 쓰기 0.
- 블라인드: 봉인 시드(37/59/61/67)·sealed/·codex 64cf 다른 시드 숫자 0, v3c3-s47 자료 0(F 표본·J-2 상태 열람 0). 목적값·예측값·SG2 녹색 숫자 출력 0(SG2 는 창 수·겹침·음수 여부만).
- 디스크: C: 약 25 GB, D: 약 222 GB 여유(8 GB 문턱 위) [실행 10:5x·11:5x].

태그: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.

---

## 1. 찾은 구멍과 고친 곳 (자세한 표는 보충 C1 §18.1)

| # | 구멍(Declare 판대로면) | 고침 |
|---|---|---|
| RV-1 | 녹색 0 금지(M3)의 새 거부가 우리 리더 씨앗 격자에서도 불려, 어느 미터든 실행 녹색이 2 가 되면 그 뒤 결정마다 ValueError(우리 SD 에는 codex `np_only` 가 없음) [실행: 8미터 모두 격자에 g0] | codex `np_only` 를 M3 키와 함께 옮김(PRB·AFO 서명, SD 두 호출; 키 끔 불변, 결정 값 불변 — SD 는 `np_values` 만 씀) |
| RV-2 | 머리 표(g9 뺌) + 저장 보호 codex 하한: 직전 g7 + 보호 → 하한 9 → 허용 집합 빔 → ValueError [실행: FW_E 4미터] | C1M `operating_bounds` 가 codex 함수 뒤에서 하한을 표 녹색으로 내림(9 → 8; 표에 있으면 codex 와 비트 같음) |
| RV-3 | G-K1 (h) "키 끔 가지 안 바뀐 줄 0" 이 선언된 공유 줄 편집과 모순 → 늘 거짓 | 편집 자리 닫힌 목록 E(22자리)와 키 끔 논거 |
| RV-4 | 옛 `k92_guard` 가 `c1t` 토큰을 SystemExit 로 거부하고 OUC 계열 튜닝의 K9-1 판정 상태 계산을 막음 → J·F 시작 불가; 탐침 도구 길 미정 | C1-0 `c1_guard` 정의(Z1·Z2·허용 목록 A·토큰 규칙·자체 시험), 탐침 길 |
| RV-5 | 팔을 시각("T > 900 → C1⁻")으로 정함; 포착·plant 잡도 `load_prices` 를 지나는데 규칙 없음 | 규칙 X⁻(직전 JSON 의 `sdmpc_state` 유무로). [실행] R-obs 행동은 모두 NoControl·`sdmpc_state` 없음 → R-obs 상태 계산(J-1·J-2·G-K1 동적 등)은 C1 그대로; 지금 계획에서 X⁻ 가 닿는 계산 없음 |
| RV-6 | P0-2 "연결자 지원 29 = membership 의 `added_unique_connector_support`" — 그 키는 membership 에 없음 → 늘 거짓 | 지지 문서 `/controlled_approach_revision` 로 바로잡음 |
| RV-7 | "모든 경로 칸이 상대·sha 맞음" 이 membership 출처 기록 5핀 때문에 늘 거짓; "63잎" 세는 꼴 미정(펴면 210); 7문서 기대 차이 없음 | 핀 점검 정의(111 = 판정 106 + 보고 5), K7 deep_diff 꼴, 기대 차이 표 |
| RV-8 | E_Ω 를 한 상태로 정해 다섯 상태에 댐; E_M·E_H 데이터 전 확인 없음 | P0-3 = 5상태 × 5팔, 상태별 집합·S_add |
| RV-9 | G-K2 (d) "Ω 목적 − OFF 목적 = 66링크 체류(1e-9)" 는 장부 코호트·7 gate 생성 표지 때문에 근거 없음 | 궤적 같음 + 목적 차 = L_Δ; D66 은 보고; F-Ω = D66 |
| RV-10 | C1 팔 G-K1 동적이 어느 커밋에도 없음; "C0 차이 없음" 규칙 미정 | C1-4 에 동적 33잡, K9-2 `c3_before_c0` 뜻, C0 = S_add |
| RV-11 | P0-5 가 `_lane_buffers` 를 모든 미터에 요구 → 늘 거짓 | codex `getattr` 꼴 |
| RV-12 | P0-1·P0-2 가 PN 을 그 자리에서 돌리면 CX 트리에 씀 | TC1 사본·옮긴 식, CX 쓰기 0 점검 |
| RV-13 / 13b | G-K5a 가 다른 세션 VISSIM 때문에 INCOMPLETE 위험; G-K5b 섞임 기록 없음 / S-C1-7 정의 변경 미기록·R-b "직전" 미정 | 시작 조건·VISSIM 개수 기록 / 적음 |
| RV-14 | 가드 교체로 기존 하네스 시험 인자 줄을 바꿔야 하면 U 와 충돌 | 보충 24 U 꼴 허용(단언 줄 0) |
| RV-15 | AFO·`c1_port.py` D5 차이가 허용 밖 → 보류 → STOP | A_C1 에 더함(같은 조건), 동결본 쪽 값 규칙 |
| RV-16–RV-25 | 출처 바로잡음(RM_C10490 곡선 = reference_config), 후보 수 세는 단위, 토큰 dict 순서 자리, G-K1 (d) 정적 조건·G-K4 팔, 7 gate 회계·소속 읽는 곳, G-K0 기준 하네스, `apply_tuning` 멱등, `cfg.network.c1_port`, UQM 줄 인용, 새 증거의 출처 글 한 곳 공개(+ 고정 파일 +11·+0.92 MB 확인) | 보충 C1 §18.1 |

- 바꾸지 않은 것: D-K9-91…95 의 뜻, `c1_port` 7키·값·repr, 선언 참조 8파일 바이트(고정 목록 53/53), 문턱(1.0158, 1,500 s, SG2 100 s, 탐침 멈춤 1–4), 상태 목록, SG2 식, S-C1-7 의 뜻, 커밋 순서.

## 2. 다시 확인했고 문제없는 것 (자세히는 보충 C1 §18.2)

1. Ω701 701/535, 더한 66 = 선언 목록, 4863f5ee 두 판 같음, manifest 차이 둘, 경로 계약 `11d0db79` → `08fec9c7` [실행].
2. 머리 설치 표 repr 4미터 = 증거, `{'9': '10'}` × 4, g10 = 지금 g10 [실행].
3. V-A T=900 토큰 세 시드 `428e650ded2f1cb8…`, T=750 미터 8개 g10·`sdmpc_state` 없음; SG2 행 꼴(창 1·겹침 0·음수 0), 창은 녹색만 [실행·읽음].
4. 코드 줄 인용(OU·CX) 대부분 맞음; 예외는 RV-24(UQM 줄)과 SEQ 인용(OU SEQ:116 을 더함) [읽음].
5. 튜닝 경로 따라 고정되는 파일: OUC 770 → C1 781(+0.92 MB), 폭증 없음 [실행].

## 3. 메인 세션이 할 일·사용자에게 알릴 것 (막힘 아님)

1. 사용자 보고에 적을 것: (가) **RV-1** — `np_only` 를 M3 와 함께 옮김. 설계 초안은 "Q4 (나)일 때만" 이었으나, 그러지 않으면 실행 녹색 2 에서 결정이 늘 실패함. 결정 값은 바뀌지 않음. (나) **RV-2** — 저장 보호 하한의 표 내림(직전 g7 → 8). Q4 (가)(g9 뺌)와 M4 를 함께 고른 데서 생기는 유일한 실현 가능 적응이고, 표에 하한이 있으면 codex 와 같음. (다) RV-5 — R-obs 기록은 NoControl 행동이라 J-1 을 C1⁻ 가 아니라 C1 팔로 셈. (라) 검토 도구 3 을 무겁게 짜서 내 PID 하나를 끈 일(출력 0).
2. 다음 단계: P0 — 보충 C1 §4(도구·패치 sha 를 첫 계산 전에 LOG 에 고정, CX·PN 은 TC1 사본으로, 무거운 일은 LOCK).
3. 남은 미해결: 없음.

## 4. 검토 도구와 출력 (`C1D/review/`; 읽기만 하는 점검, 판정에 쓰지 않음)

| 파일 | sha256 |
|---|---|
| `rev_c1.py` | `2919f53aa95abfac814173accd09e53d1ec7bb83e6179302ce6d252515d09d97` |
| `out/rev_c1.json` | `5811b5c934a5c66535100777d3546abd2d3ef77a6e8675acae5ac2b9e0c13263` |
| `rev_c1_pins.py` | `c782177d57d5046ad9f67c0d7fb42b2b882bd983b429efc5fea78f00d1c1db51` |
| `out/rev_c1_pins.json` | `b8044e3d86d27e180d4dc168aa94308faffa934f2318223b9bd896c08c52e9c6` |
| `rev_c1_robs.py`(중단, 출력 없음) | `2de28d864ea456b4ca12fc16902d5d1d07ca4957965c8826118d39618a0278df` |
| `rev_c1_robs2.py` | `ef8130f15e75ed4569710ce0f6687bd78c9b1002d7d8c9d00036c414ccd5410a` |
| `out/rev_c1_robs2.json` | `8b7e609ea93f3e2993258b747affdbf5f5a6a8c16e9905dd20feb3d452378a1b` |
| `ou/`(OU c20aff1d 블롭 사본, 읽기용) | — |
