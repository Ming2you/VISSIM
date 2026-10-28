# J1 보고 고침 규칙 — 미삽입 ④b 를 첫 관측 차분으로 다시 셈 (D-K9-89 ⑦, 방법 D-K9-87) — 2026-10-26 KST, 재셈 실행 전 고정

- 무엇: J1 보고서 `AN/J1_REPORT.md`(sha256 `4bf31b134845401524c2a04032e79b41772cb0f6a8f7aef7b2d9e94d41f0bc52`)의 ④b·④·Ω 밖 (a) 칸(짝 d = J1 − NC3, 시드별·3시드)을 V-A r4 고침과 같은 방법·도구로 다시 셉니다. J1_REPORT 바이트는 바꾸지 않습니다. 결과는 고침 메모 `AN/J1_REPORT_CORRECTION.md` 로 붙입니다.
- 왜: 사용자 결정 D-K9-89 ⑦("J1_REPORT 에도 같은 고침 메모를 붙임", `SP/K9_1_J1_NOTES_20261013.md`:294, sha256 `d248605e…`). 방법은 D-K9-87("미삽입 ④b 주 값 = 첫 관측 차분", 같은 파일 :286). J1 의 ④b 방법(stage-1 재구성, 12입력 합집합, NC 앵커)은 J1 숫자 전에 고정한 방법이었습니다(`AN/ANALYSIS_METHOD.md` sha256 `7c5ef78f…` §2.2). 이번 고침은 **데이터를 본 뒤의 방법 변경**이고, 사용자 결정으로 하는 것입니다. 메모 머리에 이것을 밝힙니다.
- 고정: 이 문서와 도구의 sha256 을 `AN/corr/J1C_PINS.sha256` 과 `SP/codex_handoff/LOG.md` 에 적은 뒤에 재셈을 띄웁니다. 실행 뒤에는 규칙·도구를 고치지 않습니다. 이 규칙대로 할 수 없으면 멈추고 보고합니다.
- 표시: [실행] 명령으로 확인, [읽음] 파일을 읽어 확인, [추론] 시험하지 않은 판단. 판정 낱말은 쓰지 않습니다.

## 줄임말

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. AN = `SP/j1/analysis`. AV = `SP/k92/va/analysis`. CORR = `AN/corr`(이 고침의 작업 폴더). REP8 = `D:/VISSIM_runs/20261001_v3c3/reports/k8`.
- J1 = K8 동결본 폐루프 3시드 런, NC3 = 같은 시드 무제어 v3c3 런. 시드 = v3c3-s31(재실행)·v3c3-s41·v3c3-s43.
- 보고 = J1_REPORT 의 값. 고침 = 이 고침의 값. 재셈 = 고정된 r4 도구 사본으로 9런을 다시 센 출력(`CORR/out/r4_firstobs.json`).

## 1. 이미 본 것 (공개)

- [읽음] 이 J1 짝(J1 − NC3)의 첫 관측 차분 값은 V-A r4 메모(`AV/VA_REPORT_r4_CORRECTION.md`, sha256 `6127ce41…8225`) §3–§5·§7·§9 의 "J1R" 칸으로 이미 공개되었습니다(시드별 d, 3시드 요약, 표시 규칙 참고 칸, 입력별 d, 입력 1083 몫, Ω701 참고 줄). 그 값은 r4 도구가 J1 분석의 stage-1 스캔(`AN/scans/<런>/scan.json`)으로 낸 것입니다. 이 규칙은 그 값을 본 뒤에 씁니다.
- 아직 내지 않은 것: J1_REPORT 칸과의 대조(칸 목록, 바뀐 칸 수), §6 누적 칸(J1 의 꼴), 선언 14행 가운데 CI 가 0 을 포함하지 않는 행 수, 글 속 숫자.

## 2. 정의

1. 재셈: 고정된 r4 도구(`AV/r4/R4_PINS.sha256`)를 경로 상수만 바꾼 사본으로 다시 돌립니다. `r4_common.py` 는 `AV = os.path.dirname(R4)` 한 줄만 절대 경로로 바꾸고(사본이 CORR 에 있어서), `r4_fzp_first.py`·`r4_firstobs.py` 는 바이트 그대로입니다(sha 가 r4 고정값과 같음). 재셈은 r4 처럼 9런(V-A·J1·NC3)을 모두 셉니다. 이 메모는 그 가운데 J1R 짝(J1 − NC3)만 씁니다. V-A 짝 출력은 부산물이고 쓰지 않습니다.
2. 창·격자·귀속·짝 차 식은 r4 규칙(`AV/r4/COMPARE_RULE_R4.md` §2-1~5) 그대로입니다: 창 [5.1, 8995.1] s, 0.5 s 중점 격자, 150 s 칸, stage-1 첫 관측 귀속, d④b_k(J1 − NC3) = S_NC3,k − S_J1,k, 34입력 모두(합집합 없음), "그 밖 입력" = 1098·1099 밖 32입력.
3. d④ = d④a + d④b(재셈), d(Ω 밖 (a)) = d④ − d③. d③·d④a·제거 A 는 J1 분석 `AN/out/an_metrics.json` `deltas`, 제거 B 는 J1 검증 `AN/verify/out/v_metrics.json` `extra.rm_<런>.outside_omega` 의 차입니다(J1_REPORT 의 원천). 이 값들은 r4 가 쓴 V-A r3 `va_metrics.json` J1R 값과 같아야 합니다(K1).
4. 통계: `va_common.stats`(J1 `an_metrics.stats` 를 옮긴 같은 식; K3 에서 an 값으로 an 요약을 다시 내어 확인). 평균/NC % 분모 = `an_metrics.json` `summary.<줄>.nc`(J1_REPORT 의 분모, 재구성 수준값) 그대로.
5. 표시 규칙: J1 방법 §2.5(`AN/ANALYSIS_METHOD.md`:122-126) = `va_common.label`(읽는 법 W 를 제거 A·B 로 따로). K4 에서 an 값으로 an `labels_k8_5_5` 를 다시 내어 확인합니다. 3시드 평균 칸은 줄 평균으로 셉니다(an 과 같음).
6. 150 s 누적(J1_REPORT §6): d④ 칸 = an `bins_delta.M4 − M4b` + 재셈 d④b 칸, d(Ω 밖 (a)) 칸 = d④ 칸 − an `bins_delta.M3`. 누적 = 처음 c/150 칸 합(c = 900·1800·3600·5400·7200·9000). 3시드 평균 = 세 시드 칸의 평균. 보고 칸 = an `bins_delta` 의 같은 합(`AN/tools/an_tables.py` 와 같음).
7. 수준값(NC3·J1 런 하나의 ④b·④·Ω 밖 (a))은 다시 내지 않습니다. 첫 관측 차분은 짝 차만 냅니다. J1_REPORT §3.1·§4.1·§4.3·§5 의 NC3/J1 수준값 칸은 재구성 값으로 남고, 고친 d 와 그 수준값의 뺄셈은 맞지 않습니다.
8. 입력별(J1_REPORT §4.3): 재셈 `per_input_new.J1R`. 보고 합집합(12입력) 밖 입력은 어느 시드든 |d| ≥ 0.05 인 것만 줄로 적고, 나머지는 합 한 줄.
9. 참고 줄(J1_REPORT 칸이 아님, 표시 규칙 적용 안 함): Ω701 기준 Ω 밖 (a)(재셈 `omega701_reference.pairs.J1R`), 보고 합집합 12입력만 센 ④b(재셈 `M4b_r3union`).

## 3. 바뀜을 세는 법 (판정이 아님)

- 숫자 칸: J1_REPORT 표의 자릿수(veh·h 0.1, sd 0.1, 평균/NC % 0.01, 시드별 % 0.1)로 쓴 글자가 다르면 "바뀜"(`*`).
- 부호: 엄격 부호(< 0, = 0, > 0)가 다르면 "부호 바뀜"(`†`).
- 글 칸(표시 규칙 문구, CI 표시, 음/양 수): 글이 다르면 "바뀜". J1_REPORT §3.3 의 W 는 "제거 A 또는 B" 한 칸입니다. 새 W(A)·W(B) 가 같으면 그 글로, 다르면 둘을 나눠 적고 바뀜으로 셉니다.
- 대상 칸(245): §0 표 세 줄(④, Ω 밖 (a), ④b) × 9칸, §3.1 d 열 세 줄 × 3, §3.2 여섯 줄(④, ④b, Ω 밖 (a), 1098, 1099, 그 밖) × 13칸, §3.3 네 줄 × (d(④), d(④ − ③), d(④b), N, W), §4.1 "(같은 표)" 세 줄 × 8칸, §4.3 보고 합집합 12입력 × 3시드 d, §5 입력 1083 몫 3칸, §6 누적 ④·Ω 밖 (a) × 4(세 시드·평균) × 6시각.
- 선언 14행(§3.2 표) 가운데 CI 가 0 을 포함하지 않는 행 수: 보고 5행 → 고침 값(§0-7·§3.2 아래 글에 쓰인 수).
- 같은 숫자를 옮겨 적은 글(§0-1·2·5·7, §3.2 아래 글, §5 글, §6 아래 글, §10 표 14·16 줄, §11)은 메모에서 손으로 짚습니다.

## 4. 점검 (STOP = 메모에 숫자를 내지 않고 멈춤)

- K0 [STOP]: J1_REPORT sha256 = `4bf31b13…` 를 비교 도구와 메모 조립 도구가 실행 앞뒤로 확인.
- K1 [STOP]: an `deltas`(③·④a·④·④b·Ω 밖 (a)·제거 A·B·입력 줄)·`summary.nc`·합집합이 V-A r3 `va_metrics.json` J1R 값과 |차| ≤ 1e-9. 재셈이 읽은 J1·NC3 `scan.json` sha256 = an `per_run.<런>.scan_sha256`.
- K2 [STOP]: 재셈 J1R(`new_deltas`·`per_input_new`·`bins_new`·`summary_new`·`labels_new`·Ω701 참고)이 공개 r4 출력(`AV/r4/out/r4_firstobs.json`, sha256 `a8f2df7b…2f35`)과 |차| ≤ 1e-9, 표시 글 같음.
- K3 [STOP]: `va_common.stats` 가 an `deltas` 로 an `summary`(선언 14행)를 다시 냄(|차| ≤ 1e-9, CI 표시·음/양 같음). 비교 도구가 다시 낸 d④·d(Ω 밖 (a))·통계가 재셈 출력과 |차| ≤ 1e-9.
- K4 [STOP]: `va_common.label` 이 an 값으로 an `labels_k8_5_5` 의 N·W 를 다시 냄. 보고 W(A)·W(B) 가 같음(한 칸 W 가 성립).
- K5 [STOP]: an `bins_delta`(M4 − M4b) 칸 합 − an d④a ≤ 0.01, 재셈 d④b 칸 합 − 재셈 d④b ≤ 0.001, 비교 도구 칸 = 재셈 `bins_new` ≤ 1e-3.
- K6 [STOP]: 대상 칸마다 보고 값을 J1_REPORT 자릿수로 쓴 글자 = J1_REPORT 파일의 그 칸 글자(§5 글 속 숫자는 |차| ≤ 0.05).
- 재셈 도구 자체 점검 C1–C8(r4 규칙 §4): `r4_firstobs.py` 가 STOP 이면 출력이 없고 이 고침도 멈춥니다.
- [보고만] J1R 900 s 전 칸 d④b, 창 효과(주 값 − [0, 9000] s 꼴), 새 FZP 스캔과의 차.

## 5. 실행

- 자기 시험(고정 전, J1_REPORT 값만 씀): `j1c_selftest.py` = 같음 시험(새 값 := 보고 값 → 바뀜 0, 보고 글 대조) + 흔든 시험(합성 차 ±300·−200 veh·h → 부호·표시 글 바뀜을 잡음). 결과 `CORR/selftest/selftest.json` ALL_OK.
- 순서: 고정(J1C_PINS + LOG) → `j1c_launch.ps1` 이 `j1c_driver.ps1` 을 WMI 로 떼어 BELOW_NORMAL 로 띄움 → FZP 스캔 9개를 하나씩 → `r4_firstobs.py`(사본) → `j1c_compare.py` → 메모 원천 글 → `j1c_memo_build.py`(금지 낱말·Ω 표 점검, J1_REPORT 바이트 점검).
- 가드(r4 드라이버와 다름, 밝힘): 단계마다, 이 작업 흐름의 다른 무거운 python(관문 1 재생 `codexhandoff\gate1`, B 분석 도구 `codex_handoff\work\`, r4 도구)이 돌면 60 s 씩 기다리고 적습니다(12 h 넘으면 멈춤). B 런의 VISSIM·어댑터와 다른 세션의 프로세스는 기다리지 않고 BELOW_NORMAL 로 함께 돕니다(r4 드라이버의 A1 가드는 A1 이 끝나 쓰지 않음). 아무것도 끄지 않습니다. VISSIM 띄움 0.
- 환경: `PYTHONHASHSEED=0`, `python -B`, `PYTHONDONTWRITEBYTECODE=1`, OMP·OPENBLAS·MKL 스레드 1.
- 쓰는 곳: CORR, 메모 `AN/J1_REPORT_CORRECTION.md`(+ `.sha256`), 사본 `REP8/j1_analysis/J1_REPORT_CORRECTION.md`(+ `.sha256`)·`REP8/j1_analysis/corr/`, LOG. J1_REPORT·AN 의 다른 파일·AV/r4·런 폴더·인계 사본·GWT8·`D:/VISSIM-merge/frozen` 에는 쓰지 않습니다.

## 6. 도구 (`CORR/tools/`; sha256 은 `CORR/J1C_PINS.sha256`)

| 파일 | 하는 일 | 출처 |
|---|---|---|
| `r4_common.py` | 경로·창·격자 적분·서식 | r4 고정 `cd8b777e…` 의 경로 상수 한 줄 사본 |
| `r4_fzp_first.py` | 런 하나의 FZP 첫 관측 스캔 | r4 고정 `6548de5e…` 바이트 그대로 |
| `r4_firstobs.py` | 9런 재셈·C1–C8 점검 | r4 고정 `49b0d3e7…` 바이트 그대로 |
| `j1c_compare.py` | J1_REPORT 칸 대조·K0–K6·표 | 새로 씀 |
| `j1c_selftest.py` | 비교 도구 자기 시험 | 새로 씀 |
| `j1c_memo_build.py` | 메모 조립·점검 | 새로 씀(r4_memo_build 와 같은 점검) |
| `j1c_driver.ps1` | 단계 실행·가드 | r4_driver_v2 `732ab60f…` 사본(머리 글·로그 이름·가드·단계 목록) |
| `j1c_launch.ps1` | WMI 분리 발사 | r4_launch_v2 `0ff6007a…` 사본(드라이버 이름) |

- 사본은 고정된 `SP/codex_handoff/work/gate1/mkcopy.py`(`8ec4f60c…`)로 만들었고, 바뀐 줄 원문은 `CORR/copies_j1c_record.json`, 명세는 `CORR/spec_j1c_copies.json`(생성기 `CORR/make_spec_j1c.py`)에 있습니다.
- 고치지 않고 import 하는 파일: `AV/tools/va_common.py` `49681fa9…`, `AV/tools/va_report_build.py` `651812cd…`(금지 낱말 목록만).
