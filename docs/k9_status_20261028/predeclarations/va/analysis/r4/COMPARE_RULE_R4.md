# V-A r4 고침 규칙 — 미삽입 ④b 를 첫 관측 차분으로 다시 셈 (D-K9-87) — 2026-10-26 KST, r4 숫자를 내기 전 고정

- 무엇: V-A 보고 r3(`AV/VA_REPORT.md`, sha256 `b57022e651adeefcaf1484993c20fd940b2e13012f0437e3a5b6c5ad6a20fc1b`)의 ④b(합·입력별)와 그것을 더한 ④·Ω 밖 (a) 칸을 다시 셉니다. r3 바이트는 바꾸지 않습니다. 결과는 고침 메모 `AV/VA_REPORT_r4_CORRECTION.md` 로 붙입니다.
- 왜: 사용자 결정 D-K9-87("미삽입 ④b 주 값 = 첫 관측 차분", 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` sha256 `67dcc32b…`). r3 의 ④b 방법(stage-1 재구성)은 V-A 데이터를 보기 전에 고정했던 방법입니다. 이번 고침은 **데이터를 본 뒤의 방법 변경**이고, 사용자 결정으로 하는 것입니다. 메모 머리에 이것을 밝힙니다.
- 고정: 이 문서와 도구 일곱 파일(`AV/r4/tools/`)의 sha256 을 `AV/r4/R4_PINS.sha256` 과 `codex_handoff/LOG.md` 에 적은 뒤에 실행합니다. 실행 뒤에는 규칙·도구를 고치지 않습니다. 이 규칙대로 할 수 없으면 멈추고 보고합니다.
- 표시: [실행] 명령으로 확인, [읽음] 파일을 읽어 확인, [추론] 시험하지 않은 판단. 판정 낱말은 쓰지 않습니다.

## 줄임말

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. AV = `SP/k92/va/analysis`. R4 = `AV/r4`.
- 런 9개 = V-A·J1·NC3(무제어) × v3c3-s31·v3c3-s41·v3c3-s43. 이름·경로는 r3 와 같습니다(`AV/tools/va_common.py`).
- 짝 A = V-A − NC3, 짝 B = V-A − J1, J1R(= 짝 B′) = J1 − NC3. Ω = 제어 영역 635링크(③). Ω701 = codex 목적 영역 701링크.
- FZP = VISSIM 차량 궤적 파일(5 s 프레임). 첫 관측 = 차량 번호가 FZP 에 처음 나온 프레임 시각.

## 1. 이미 본 것 (공개)

- [읽음] 이 9런의 첫 관측 차분 ④b 합은 [0, 9000] s 꼴로 이미 공개되었습니다(`codex_handoff/VERIFY_HANDOFF_RESULTS.md` §2.2 "우리 꼴 0–9000", `work/vhr/corr_tables.md` sha256 `73a4d89a…`). 이 규칙은 그 값을 본 뒤에 씁니다.
- 아직 내지 않은 것: r3 창([5.1, 8995.1] s)의 값, 입력별 값(stage-1 귀속), 3시드 통계, 표시 규칙 결과, 150 s 누적 칸, 입력 1083 몫, 칸별 바뀜 목록.

## 2. 정의

1. 창: r3 적분 창 [t0, t1] = [5.1, 8995.1] s(FZP 첫·끝 프레임). 러너 FZP 의 0.10 s 행은 r3 읽기 심과 같이 건너뜁니다.
2. 원천(주 값): 9런의 stage-1 `scan.json`. 입력 k 마다 `insertions[k].first_seen_times` = 그 입력에 귀속된 차량의 첫 관측 시각(귀속 = stage-1 규칙: 첫 관측 링크가 입력 링크이면 그 입력, 아니면 상류 추적). r3 의 입력별 줄과 같은 귀속입니다.
3. I_r,k(t) = 런 r 입력 k 에서 첫 관측 ≤ t 인 차량 수. S_r,k[칸] = ∫ I_r,k(t) dt / 3600, stage-1 과 같은 0.5 s 중점 격자, 150 s 칸(중점 기준).
4. 짝 차(검증된 식, `work/vhr/vhr_unins.py`): 같은 시드 두 런은 도착열이 같으므로 U_a − U_b = I_b − I_a. 그래서 d④b_k(a − b) = S_b,k − S_a,k.
5. 줄: ④b = 34입력 모두의 합(합집합 없음). ④b 중 입력 1098 = k 1098, 입력 1099 = k 1099, 그 밖 입력 = 나머지 32입력 합. (r3 의 "그 밖" 은 합집합 안 입력만이었습니다. 정의 차이를 메모에 적고, 참고로 r3 합집합 입력만 센 값도 냅니다.)
6. d④ = d④a(r3 값) + d④b(r4). d(Ω 밖 (a)) = d④ − d③(r3 값). ③·④a·제거 A·B 는 r3 `AV/out/va_metrics.json`(sha256 `1779890828ddf590e8d22f2275aadb75cc70ea11a168f9f4967400ec5196ef24`) 값 그대로입니다.
7. 수준값(런 하나의 ④b·④·Ω 밖 (a))은 다시 내지 않습니다. 첫 관측 차분은 짝 차만 냅니다. r3 의 수준값 칸은 재구성 값으로 남습니다.
8. 통계: r3 공통 도구 `va_common.stats`(sha256 `49681fa9…`, 고치지 않고 import)를 그대로 씁니다. 평균/NC % 의 분모는 그 짝의 r3 합집합 NC3 수준값(짝 A = U6(V-A), 짝 B·B′ = U9, J1R = U6(J1); r3 `summary.<줄>.nc`) 그대로입니다.
9. 표시 규칙: r3 의 `va_common.label` 그대로입니다(보충 34 §8.4). 시드별은 {d③ r3, d④ r4, d(Ω 밖 (a)) r4, d④b r4, 제거 A r3, 제거 B r3}, 3시드 평균은 같은 줄의 평균으로. 짝 A·B 는 r3 칸, J1R 은 참고(r3 에 표가 없음; `J1_REPORT.md` 는 이 메모가 고치지 않음).
10. 150 s 누적(§11): d④ 칸 = r3 `bins_delta.M4 − bins_delta.M4b` + d④b 칸(r4), d(Ω 밖 (a)) 칸 = d④ 칸 − r3 `bins_delta.M3`. 누적 = 처음 c/150 칸 합(c = 900·1800·3600·5400·7200·9000; `va_tables.py` 와 같음). 평균 = 세 시드 칸의 평균.
11. 입력 1083 몫(§5): k 1083 의 d(짝 A·B). r3 은 짝 A 가 합집합 밖이라 0 이었습니다.
12. 참고(r3 에 없는 칸, D-K9-87 "Ω635·Ω701 둘 다"): d(Ω701) = 9런 stage-1 `link_vh` 를 인계 `D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json`(sha256 `efdfaeb1…`)의 701링크로 더한 값의 짝 차. Ω 밖 (a) Ω701 기준 = d④ − d(Ω701). 표시 규칙은 적용하지 않습니다(규칙의 ③ 은 Ω635).

## 3. 바뀜을 세는 법 (판정이 아님)

- 숫자 칸: r3 표의 자릿수(veh·h 0.1, 평균/NC % 0.01, 시드별 % 0.1, sd 0.1)로 쓴 글자가 다르면 "바뀜"(표에서 `*`).
- 부호: 엄격 부호(< 0, = 0, > 0)가 다르면 "부호 바뀜"(표에서 `†`).
- 글 칸(표시 규칙 문구, CI 표시 "관측된 차이"·"0 포함", 음/양 수): 글이 다르면 "바뀜".
- 대상 칸: §3.1 시드별 d 네 열(짝 A, 짝 B′ [U9], 짝 B, J1R), §3.2 요약(짝 A·B·J1R), §3.3 표시(짝 A·B), §4.1 "(같은 표)" 세 줄, §5 입력 1083 몫, §11 누적(④·Ω 밖 (a)). 같은 숫자를 옮겨 적은 글(§0·§3.3 글·§4.1 글·§4.3 글·§13)은 메모에서 손으로 짚습니다.

## 4. 점검 (STOP = 메모에 숫자를 내지 않고 멈춤)

- C1 [STOP]: 9개 `scan.json` sha256 = r3 `va_metrics.json` 의 `per_run.*.scan_sha256`, J1·NC3 은 보충 34 §8.1 앞 16자와도 같음.
- C2 [STOP]: 런마다 프레임 1,799개, 5.1–8,995.1 s, 불규칙 0, 칸 60 × 150 s, 귀속 ambiguous·unattributed 0, 입력별 수 합 = `vehicles_seen`, 입력 집합 9런 같음, 첫 관측이 모두 창 안.
- C3 [STOP]: 런·입력마다 격자 적분과 닫힌 꼴 Σ(t1 − t첫관측)/3600 의 차 ≤ 1e-5 veh·h.
- C4 [STOP]: 새 FZP 스캔(`r4_fzp_first.py`, stage-1 과 독립)과 대조. 런마다 차량 수 = `vehicles_seen`, 프레임 1,799·5.1·8,995.1·불규칙 0, FZP 바이트 수 = scan 의 `fzp_bytes`, 닫힌 꼴 합 차 ≤ 1e-4. 짝마다 d④b 합 차 ≤ 0.01 veh·h.
- C5 [STOP]: 검증된 방법 재현. `work/vhr/scan_out/first_<런>.json` 9개로 [0, 9000] 꼴 d④b 합을 `vhr_v3c3_all.py` 의 식으로 다시 내어, VERIFY §2.2 "우리 꼴 0–9000" ④b 줄(−174.3 / −105.6 / −62.0, −264.3 / −134.5 / −9.6, +90.0 / +28.9 / −52.4)과 |차| ≤ 0.05.
- C6 [STOP]: r3 표시 규칙을 r3 `deltas`·평균으로 다시 내면 r3 `labels` 와 같음(짝 A·B). r3 보고서 바이트가 실행 앞뒤로 같음.
- C7 [STOP]: r3 `bins_delta.M4 − M4b` 칸 합과 r3 d④a 차 ≤ 0.01.
- C8 [보고만]: 900 s 전 칸(0–5)의 d④b 최대 |값|(r3 §12 는 모든 지표 0).
- [보고만] Ω701 참고 줄: 런마다 `link_vh` 전체 합과 `all_ttt` 차 ≤ 0.05(넘으면 STOP).

## 5. 실행

- 순서: `r4_selftest.py`(합성 자료만; 이미 ALL_OK) → 고정 → `r4_launch.ps1` 이 `r4_driver.ps1` 을 WMI 로 떼어 BELOW_NORMAL 로 띄움 → FZP 스캔 9개를 하나씩 → `r4_firstobs.py` → 메모 원천 글을 쓰고 `r4_memo_build.py` 로 조립(금지 낱말·Ω 표 점검, r3 바이트 점검).
- 드라이버는 단계마다, A1 결정 python 이 1,500 s 를 넘었거나 A1·r4 가 아닌 python 이 돌면 60 s 씩 기다리고 적습니다(12 h 넘으면 멈춤). 아무것도 끄지 않습니다.
- 환경: `PYTHONHASHSEED=0`, `python -B`, `PYTHONDONTWRITEBYTECODE=1`, OMP·OPENBLAS·MKL 스레드 1. 결정 재생이 아니라서 env_hsw 변수는 넣지 않습니다.
- 쓰는 곳: `AV/r4/`, 메모 `AV/VA_REPORT_r4_CORRECTION.md`(+ `.sha256`), 사본 `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va/`, LOG. 런 폴더·인계 사본·GWT8·frozen 에는 쓰지 않습니다.

## 6. 도구 (`AV/r4/tools/`, sha256)

| 파일 | 하는 일 | sha256 |
|---|---|---|
| `r4_common.py` | 경로·창·격자 적분·서식 | `cd8b777e7be92dc5cd0a20e491f1ce00419d4c0371e760a5fbafeb967094a902` |
| `r4_fzp_first.py` | 런 하나의 FZP 첫 관측 스캔(독립) | `6548de5eece5115db667e675501771e76a3875b18585da6ec6102f6225200161` |
| `r4_firstobs.py` | 본 계산·점검·칸 대조·표 | `49b0d3e73b8930505da840728a4f61a895cb89434cb6f2e50715283ebdc7ad0c` |
| `r4_selftest.py` | 합성 자료 자기 시험(파이프라인 건식 실행 포함) | `9e125512c70a672ed9d6b5e67cfc9cdccd4c8a7d97fd547151ea731abd53cbb6` |
| `r4_memo_build.py` | 메모 조립·점검 | `f05639cc66900064f79ee71446de6e715ea1cb2549a1e66d1595da8b0a5c16e8` |
| `r4_driver.ps1` | 단계 실행·A1 가드 | `0988188e40f4f882578ee8e819832599b59baa09060f0395f78872bd36bf22e4` |
| `r4_launch.ps1` | WMI 분리 발사 | `07f49fde0f07952eaf50e51f48469ea47d196992c835abeae52eaa4aae6ad61b` |

- 고치지 않고 import 하는 r3 파일: `AV/tools/va_common.py` `49681fa9fbe65317be682a9981f80ea482c828017a8f75d91ca53cb585cd9c6c`, `AV/tools/va_report_build.py` `651812cd4c0d2eaca6506c8ec0081bbfce72cd6cf0106b327198ef86a06f65dc`(금지 낱말 목록만).
