# V-A 런 유효성 — 세 시드 (v3c3-s31 · v3c3-s41 · v3c3-s43) — 2026-10-24

- 이 문서는 V-A 분석 **전** 단계의 런 유효성 기록입니다. 보충 34 §7.1(개정 J1-A, 유지 결정은 따로 셈, 실패 시드 정의)과 §7.2(STOP 규칙)를 세 런에 적용했습니다.
- **성능 숫자는 하나도 계산·열람·출력하지 않았습니다.** Ω·TTT·지표 ①–④·Ω 밖 대기·차로변경 제거 대수·미삽입 대수·지연·목적값·녹색이 모두 0개입니다. 그래서 이 문서에는 Ω 표가 없습니다. Ω는 분석 단계에서 ④(전체·미삽입)와 Ω 밖을 같은 표에 두고 처음 냅니다(보충 34 §8.4).
- 판정 말(낫다·나쁘다 등)을 쓰지 않습니다. 항목은 참/거짓, 규칙은 "걸림/걸리지 않음"으로만 적습니다.
- 표시: **[실행]** 이번에 내 도구·명령으로 확인 · **[읽음]** 파일·문서를 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- **판: r3** (2026-10-24 KST, 글 고침만). r2는 `VAL/VALIDITY_VA_r2.md`(sha256 `8f57c3ab6364862603dc87d0be8f770f3ae6e8afcde4816e21731ddf9e2881f8`), r1은 `VAL/VALIDITY_VA_r1.md`(sha256 `2021bb11e91eb407c71267ea4645da4f7cd7499eabd38f5add563c30a7b6745b`)에 바이트 그대로 둡니다. r2에서 고친 것은 검증 `VA/analysis/VERIFY_VA_r1.md` §5의 B1–B3(고정 목록 줄 수 오기, 시드 접두어, 줄임말)과 같은 꼴의 글입니다. r3에서 고친 것은 검증 `VA/analysis/VERIFY_VA_r2.md` §5의 D2·D3(줄임말 풀이 두 곳)뿐입니다. 항목·숫자·참/거짓·STOP 결과·도구·고정 목록은 바꾸지 않았습니다. 바뀐 곳은 §13에 모두 적었습니다.

줄임말 (처음 한 번만 풉니다)
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`. VAL = `VA/validity`(이 단계의 쓰기 폴더). REPVA = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`(보고 사본 자리).
- RVA = V-A 런 폴더 `D:/VISSIM_runs/20261023_sdmpc31_k92`. RR = J1 런 폴더 `D:/VISSIM_runs/20261004_sdmpc31_k8`. NC3 = 같은 시드 무제어 v3c3 런 `D:/VISSIM_runs/20261001_v3c3/s<S>_v3c3nc/run`(J1 정의).
- V-A = 묶음 B1(W·H-b 두 키)을 배포한 폐루프 VISSIM 3시드 런. J1 = K8 동결본 폐루프 3시드 런(비교 대상, 이 단계에서는 도구 자기 시험에만 씀).
- FRZ_K92 = 동결본 `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833`(head `c20aff1d…`). FRZ_K8b = `…/sdmpc31_b9734abe_202610141821`. FRZ_K8 = `…/sdmpc31_74cd495f_202610131824`.
- J1-A = 런 하나가 유효한지 보는 조건 목록. 개정 J1-A = 유지 정책이 켜진 런의 J1-A(보충 21 §4.1). 유지(hold) = 결정이 예외로 죽으면 직전 명령을 다시 쓰는 장치. H-A = 유지 감사(보충 21 §4.2). J1-V = 같은 시드 무제어 런과 900 s 전까지 같은지 보는 짝 점검. U9-a = VSL 명령이 VISSIM까지 끊김 없이 쓰였는지 보는 감사.
- SDMPC = 이 계열의 모형예측 제어기(wu-link). VSL = 가변 속도 제한. FZP = VISSIM 차량 궤적 파일. WD = 감시 러너. S6 = 결정마다 어댑터 stdout·stderr를 남기는 캡처.
- W = SC109 서측 직진 용량 키(`k92_w`), H-b = (173, p4) 좌회전 하한 씨앗 키(`k92_hb`).
- [r2 더함] GWT8 = K9-2 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`(브랜치 `claude/k92-b1-20261016`). K8 가지 = 브랜치 `claude/k8-sc1001eb-defects-20261004`. K9-2-7 = GB-7′ 허용 목록 보충 커밋 `c20aff1d…`(FRZ_K92의 head). [r3 고침] GB-7′ = 무제어 61결정 재생 출력 대조 오프라인 관문(보충 34 §5.1). 디스크 여유의 GB는 기가바이트.
- [r2 더함] REP8 = `D:/VISSIM_runs/20261001_v3c3/reports/k8`(K8 단계 보고 사본 자리). R-obs3 = 러너로 돈 무제어 61결정 런 `D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31`(v3c3-s31; 보충 34 줄임말, NC3와 다른 런).
- [r2 더함] K7·K8 = 앞 단계 선언 문서(K8 = `SP/K8_PREDECLARATION.md`). K8b = J1 v3c3-s31 재실행 단계(그 동결본이 FRZ_K8b). K3 = K7 §3.3의 미터 점검 이름(쓴 녹색에 3 s 없음).
- [r3 더함] §3 표 '#' 칸의 항목 이름(S1–S6·K8·K8a·K8b·SIG1·SIG2·DEC1–DEC5·PROV1–PROV3·VSL1·VSL2·MTR)은 보충 34 §7.1과 J1 `VALIDITY.md` §2 표의 항목 이름입니다. 위의 문서·단계 이름 K8·K8b, 캡처 이름 S6과 다른 말이며, 뜻은 표의 '항목 (정의)' 칸을 따릅니다(표 칸 글 안의 "S6 캡처"는 위의 캡처 S6입니다).
- [r2 더함] H10 = T = 900 건강 점검(보충 34 §6.4) 10번 항목: launch 로그의 WD 정책 줄 수(WD 호출마다 1줄 = 2줄, 모두 hold, strict 0). G-H1 = 보충 21 §7.3 예외 주입 관문(오프라인에서 일부러 예외를 넣어 유지 영수증을 만듦). G-K5 = 보충 24의 결정 벽시계 예산 관문(1.0158).
- [r2 더함] S-VA-1–8 = 보충 34 §7.2의 V-A 단계 STOP 규칙. S-A34-1–10 = 보충 34 §9.2의 새 STOP 규칙.
- [r2 더함] VBS = 러너가 VISSIM을 COM(윈도 자동화 인터페이스)으로 돌리는 주 VBScript(`main_vbs_runner`). WMI = 윈도 관리 도구(`Win32_Process.Create`)로 세션과 떼어 프로세스를 띄우는 방법. BELOW_NORMAL = 낮은 프로세스 우선순위.
- 시드는 망 접두어를 붙여 v3c3-s31처럼 적습니다. [r2 더함] 파일·런·도구 이름(예: `va_check_s31.json`, `sdmpc31_v3c3_k92va_s43`)은 이름이라 그대로 둡니다. 그 이름 안의 시드 번호 31·41·43도 v3c3-s31·v3c3-s41·v3c3-s43입니다.

## 유지 표 (보충 21 §5 1–7번; 시드마다)

| 시드 | 런 이름 | 동결본 · head · 튜닝 sha | 유지 정책 | 유지 수 (SDMPC 55결정 중) | 유지 시간 |
|---|---|---|---|---|---|
| v3c3-s31 | `sdmpc31_v3c3_k92va_s31` | FRZ_K92 · `c20aff1d` · `c8e3ee2c…` | 켜짐 `hold_previous_on_exception` | **0 (0 %)** | 0 s |
| v3c3-s41 | `sdmpc31_v3c3_k92va_s41` | 같음 | 켜짐 | **0 (0 %)** | 0 s |
| v3c3-s43 | `sdmpc31_v3c3_k92va_s43` | 같음 | 켜짐 | **0 (0 %)** | 0 s |

- 유지 0의 근거(세 런 같음) [실행 `VAL/out/va_check_s<S>.json` `/hold_audit/absence_evidence`]: 영수증 `action_T.hold.json` 0, 유지 캡처 0, `*.hold_error.txt` 0, `*.failed_decision` 0, `*.error.txt` 0, 런로그 `DECISION_HOLD_ATTEMPT`·`DECISION_HELD_ON_EXCEPTION`·`DECISION_HOLD_FAILED` 0, 끝 요약 `DECISIONS_HELD_ON_EXCEPTION=0` 1줄, action JSON `metadata.controller_status` 61/61 `ok`, 유지 메타 키 0, state CSV 상태 61/61 `ok`.
- 유지 T 표·최장 연속·유지 직후 결정(§5 3–5번): 모두 해당 없음(유지 0). "유지 0" 한 줄로 갈음합니다(§5 7번).

---

## 0. 결론

1. **세 런 모두 개정 J1-A 스크립트 항목 27개가 참이고, J1-V 짝도 참입니다** [실행 §3, §6]. `failed_items = []` ×3.
2. **유지 결정은 따로 셌고 0개입니다.** 그래서 H-A1–H-A9는 모두 빈 검사이고 위반 0, INCOMPLETE 0입니다 [실행 §5].
3. **결정 수**: 세 런 모두 `action_\d{6}.json` 61개 = 예열 6 + SDMPC 55, `DECISIONS_OK=61` + `DECISIONS_HELD_ON_EXCEPTION=0`, `DECISIONS_FAILED=0`, 빠진 T·남는 T 0 [실행].
4. **`DECISION_FAILED`**: runlog·runlog.err·launch·wmi·`WATCHDOG_PROGRESS`·VISSIM `.err` 다섯 곳·S6 캡처 122개 모두 0 [실행]. **오류 파일**: `*.error.txt`·`*.hold_error.txt`·`*.failed_decision`·`attempt_*` 폴더·`NOT_LAUNCHED` 파일 모두 0, `runlog….txt.err` 0 B [실행].
5. **출처**: head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(읽는 법 A), 동결본 `FREEZE.json` `011f5be2…8476`, 튜닝 `c8e3ee2c…1866`, 망 `3de889f0…1c2e`, 환경 정책 hold·`RW_DECISION_FAIL_FAST=1`, 시드 = 31/41/43 — 세 런 모두 보충 34 §7.1 표와 같음 [실행 §4]. FRZ_K92를 지금 다시 해시해도 표의 10,569개 파일이 모두 같습니다 [실행 §7.6].
6. **W·H-b 키**: 61결정(SDMPC 55 포함) 모두 `k92_w`·`k92_hb`가 있고 (173, p4) 하한 키가 결정마다 정확히 1개, 런 안에서 이름이 하나뿐입니다. `k92_w.after` repr = `5209.8` 61/61 [실행 §7.2].
7. **T = 150 예상 계수**: `head_observation_prior_discarded = 1.0`이 세 런 모두 T = 150에서만 나옵니다(예상과 같음, J1-A 항목 아님) [실행 §7.1].
8. **실패 시드 0개.** 보충 34 §7.2의 S-VA-1–S-VA-8과 S-A34-8·9·10 중 걸린 것 0, 질문 지점(S-VA-6) 0 [실행·읽음 §8].
9. 따라서 **보충 34 규칙상 분석 단계(§8.0 순서: 보고 머리 → 분석)로 갈 수 있습니다.** 이 문서는 성능 숫자를 열지 않았으므로 분석 결과에 대해서는 아무것도 말하지 않습니다.

### 알릴 것 (판정에 영향 없음, 공개)

- (가) **런 최상위 `vissim_simulation_001.err`가 v3c3-s31·v3c3-s41에서 끝 판이 아닙니다** [실행 §7.5]. 두 파일 모두 311,296 B(= 4,096 × 76)이고 수정 시각이 런 끝보다 일찍(v3c3-s31 22:11:46, v3c3-s41 22:44:09)입니다. 끝 판은 `network/sdmpc31_<런>_001.err`(317,794 B / 316,153 B, 22:35:24 / 23:03:03)입니다. v3c3-s43과 J1 세 런은 두 파일이 바이트까지 같습니다. [추론] 두 런이 동시에 돌 때 러너가 VISSIM이 버퍼를 다 쓰기 전에 복사본을 만든 것으로 보입니다(시험하지 않음). 영향: 분석 도구는 Ω 밖 (d)·미삽입 등에 `network/…_001.err`(끝 판)를 읽고, 최상위 사본(`err_root`)은 출처 해시에만 씁니다 [읽음 `VA/analysis/tools/va_common.py:98-99`, `va_metrics.py:117-118`, `va_provenance.py:45`]. 이 단계의 `DECISION_FAILED` 셈은 두 파일 모두에서 0입니다.
- (나) **결정 벽시계**(보고만, 판정 아님; 보충 34 §8.3-9가 "G-K5와 같은 양이 아님"이라 적음) [실행 §7.3]: V-A SDMPC 중앙 536.55 / 559.38 / 473.02 s, J1 같은 시드 중앙 469.57 / 409.58 / 489.96 s, 비 1.1426 / 1.3657 / 0.9654 [계산], G-K5 예산 1.0158은 옆에 적기만 합니다. 900 s 넘는 결정 0, 최대 818.56 s(v3c3-s41) < `StallSec` 2,400 s.
- (다) 작업 지시 글의 분석 고정 목록 자리 `VA/launch/va_analysis_pins.sha256`은 실제로 `VA/analysis/va_analysis_pins.sha256`입니다. sha 앞 8자 `39a97e7f`는 지시 값과 같고, 목록은 20줄이며 20/20 OK입니다 [실행]. (r1은 이 자리를 "21/21 OK"로 잘못 적었습니다. 목록 파일은 2026-10-23 12:27 뒤 바뀌지 않았고 sha `39a97e7f…903e` 그대로라 이 단계 때도 20줄이었습니다 [실행 2026-10-24 09:3x `wc -l`·`sha256sum -c` 20/20]. §13.)
- (라) NC3 폴더를 찾을 때 `ls -d D:/VISSIM_runs/20261001_v3c3/s*_v3c3nc/run`을 한 번 돌려 폴더 **이름** 목록에 봉인 시드 하나와 v3c3-s47·s53 이름이 화면에 나왔습니다. 그 폴더 안의 어떤 파일도 열지 않았습니다. 짝 도구는 `find_rule_policy = None`으로 형제 폴더 glob을 막았습니다 [실행].
- (마) LOG의 내 시작 점검 줄에 launch 고정 목록 sha를 "fa5329c6…0b4b"로 잘못 적었고, 바로 다음 줄에 정정을 덧붙였습니다(옛 줄은 지우지 않음) [실행].

---

## 1. 시작 점검 [실행 2026-10-24 07:4x–07:58 KST]

| 확인 | 결과 |
|---|---|
| 보충 34 `SP/K8_PREDECLARATION_AMENDMENT_34.md` sha256 | `a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e` = 고정점 `VA/AMENDMENT34_FIXED.md`의 64자 값 = `.sha256` 파일 |
| 고정 목록 `VA/a34_pins.sha256` | 파일 sha `4e44741657dc483f…0403` = 고정점 값, `sha256sum -c` 83/83 OK |
| 발사 고정 목록 `VA/launch/launch_pins.sha256` | 파일 sha `fa5329c621b17cba…3a9c`, 8/8 OK |
| 분석 고정 목록 `VA/analysis/va_analysis_pins.sha256` | 파일 sha `39a97e7f5a95d3db…903e`, 20줄, 20/20 OK (r1의 "21/21"은 오기, §13) |
| 세 런 끝 | 러너 자기 로그 `EXIT <런> code=0` 각 1줄(launch·wmi 둘 다): v3c3-s31 2026-10-23 22:35:18, v3c3-s41 23:03:01, v3c3-s43 2026-10-24 07:40:02. `WATCHDOG_EXIT code=0` wall_sec 36,037 / 37,583 / 32,562, WD `OK … attempt=1` |
| 발사 거부 | `REFUSED`·`NOT_LAUNCHED` 줄 0, `NOT_LAUNCHED` 파일 0, 런마다 러너 `START <런>` 1줄 |
| 프로세스 | 발사 cmd PID 19740(v3c3-s31)·18580(v3c3-s41)·16932(v3c3-s43), 감시기 cmd 24564·powershell 8084, 러너 PID 18112·24848, VISSIM PID 22724·27572 모두 없음. `tasklist`에 VISSIM 0. 감시기 로그 끝 `AFTER_LAUNCH vissim_total=2`, `WATCHER_DONE`(22:37:27), `GIVE_UP` 없음 |
| 디스크 | C: 33 GB, D: 346 GB 여유(8 GB 이상) |
| 브랜치 | GWT8 HEAD `c20aff1d…`, `status --porcelain` 0줄, K8 가지 `claude/k8-sc1001eb-defects-20261004` = `b9734abe…`(읽기 명령만) |
| 건강 점검 T = 900(발사 단계 산출, 다시 열어 확인) | `VA/launch/health_s31_T900.json` `2f80fab6…`, `_s41` `dfc89a2b…`, `_s43` `fb567e55…` 모두 18/18 참, 하한 키 이름 v3c3-s31 `…_0d58a14f910af049`, v3c3-s41 `…_d53f3bddee47d38c`, v3c3-s43 `…_d7feec1450ade0a4` |

## 2. 도구 고정과 자기 시험

- `VAL/va_j1a.py`는 이 단계에서 새로 썼습니다(전에 없었음 [실행 `find`]). J1 도구 `SP/j1/analysis/tools/j1a_check_s31r.py`(개정 J1-A)와 `pair_prefix_s31r.py`(J1-V)를 바탕으로 런 경로·기대값만 프로필로 바꾸고, 보충 21 §4.2 H-A1–H-A9 계산과 보충 34 §7.1 보고 항목을 더했습니다.
- **고정**: 2026-10-24 07:58 KST, 런 자료를 읽기 전에 `VA/LOG.md`에 sha를 적었습니다 [실행].
  - `va_j1a.py` sha256 **`968891df5b19627bf7743b8b39a871704509b8d4f3e6643d35cbec25d6ac88c6`** (72,367 B)
  - 자기 시험 비교기 `va_j1a_selftest.py` sha256 **`2c7046017a153824291176218d60cf552582a53dbd7058016382cdec27463592`** (11,476 B)
  - 목록 `VAL/va_j1a_pins.sha256` (`43c6360d…`), 계산 전후 2/2 OK. 고정 뒤 두 도구를 고치지 않았습니다.
- **데이터 전에 고정한 읽는 법**(보충 21 §4.2가 글로 정하지 않은 두 곳) [읽음 도구 머리 글]:
  - H-A4 "다음 결정의 직전 행동 출처" = T + 150 결정의 `metadata.n31_binding.vsl_cohort_initialization`(`source` 파일 이름 = `action_T.json`, `sha256` = 유지 JSON sha). 다음 결정도 유지면 그 영수증 `source.action_json.sha256`.
  - H-A6 = 러너 행동 로그 `action_<런>.csv`의 T 행에서 앞 `sim_sec` 칸과 끝 `readback` 칸을 뺀 원시 CSV 칸 = 유지 CSV 데이터 행(행 수·순서·글자 같음).
  - 두 비교기를 모든 비유지 결정에도 돌려 "읽는 법이 정상 결정에서 성립하는지"를 보고합니다(아래 자기 시험과 §5).
- **자기 시험(J1 자료만, V-A 자료 0)** [실행, 출력 `VAL/out/selftest/`]:

| 시험 | 기대(J1 공개 산출, sha 앞 8자 대조) | 결과 |
|---|---|---|
| J1 v3c3-s31 재실행 런(j1r) check(정책 켜짐 정의) | `SP/j1/analysis/out/j1a_s31r.json` `53cf93b8` — 27항목 참, `failed_items []` | 27/27 같음, 카운터·되읽기·U9-a·VSL 상자·벽시계(중앙 469.57 s)·출처 값·읽는 법 B(거짓) 모두 같음 |
| J1 v3c3-s41·v3c3-s43 런 check(유지 없는 원래 정의) | `SP/j1/s31fail/out/j1a_s41.json` `212b1c8d`, `j1a_s43.json` `200131d5` — 23항목 참 | 23/23 같음(정책 전용 4항목은 `n/a`), 세부 값 같음 |
| pair 셋 | `pair_s31r.json` `cc81bc3d`, `pair_s41.json` `4c2249b3`, `pair_s43.json` `1f120901` | `pairing_check` 사전·900 s 전 프레임 179·진입 6,969 / 7,061 / 6,965·shim 행 수 모두 같음 |
| FRZ_K8b 재해시 | `freeze_check.json` `0a64a025` — 10,548 같음, 캐시 229, 표 밖 비캐시 0 | 같음(캐시 시각 2026-10-15 03:26–03:43) |
| H-A 영수증 단위 시험 | G-H1 관문 출력(실제 helper가 만든 유지) `REP8/offline_gates_k8h/gh1/T003900_i1`·`_i3`(부분 산출물 2개)·`_i4`(RuntimeError) | H-A1·H-A2·H-A3·H-A5·H-A7 모두 참 |
| H-A4·H-A6 비교기(비유지 결정) | 정상 결정에서는 모두 같아야 함 | 세 J1 런 모두 H-A6 61/61, H-A4 60/60 같음 |

- 비교기 결과: 269줄 비교, **`SELFTEST_ALL_OK`** (`VAL/out/selftest/selftest_compare.json` `4241cf9f…`) [실행].
- 이 결과는 `SP/j1/analysis/VALIDITY.md` §2·§2.1·§2.2·§3·§7의 값과 같습니다(v3c3-s31 재실행 27항목·J1-V 905.1/918.5/6,969·U9-a 4,026행·FRZ_K8b 10,548; v3c3-s41·v3c3-s43 23항목) [실행·읽음].

## 3. 개정 J1-A 항목별 (보충 34 §7.1 = 보충 21 §4.1 정책 켜짐 정의) [실행 `va_j1a.py check --profile va`]

- 항목 이름은 J1 `VALIDITY.md` §2 표와 같습니다. 유지 T 집합이 비어 있으므로 "유지 T를 뺀" 조건은 모든 T에 대한 조건과 같습니다.

| # | 항목 (정의) | v3c3-s31 | v3c3-s41 | v3c3-s43 | 근거 (세 런) |
|---|---|---|---|---|---|
| S1 | `DECISIONS_FAILED=0` + `DECISIONS_HELD_ON_EXCEPTION=n` 정확히 1줄 | 참 | 참 | 참 | 각 1줄, 0 / 0 |
| S2 | `ERROR=` 줄 0 | 참 | 참 | 참 | 0. `WARN=` 2줄은 J1과 같은 선택 속성 건너뛰기(DatabaseConnection, SimSpeed) |
| S3 | 발사기 `EXIT … code=0` | 참 | 참 | 참 | launch·wmi 각 1줄, `attempt_*` 폴더 0 |
| S4 | `STAGE=SIM_DONE`, `SIM_SEC=9000` | 참 | 참 | 참 | — |
| S5 | ACTION_FORMAT·COM·SIGNAL·OBSERVATION 실패 0, `SIGNAL_NAME_RULE_FALLBACKS=0` | 참 | 참 | 참 | 모두 0 |
| S6 | `*.error.txt`는 유지 T에만(영수증과 1:1), `*.hold_error.txt` 0 | 참 | 참 | 참 | 둘 다 0 |
| K8 | `DECISION_FAILED`는 허용 자리에만 | 참 | 참 | 참 | 로그 10곳 0, S6 캡처 122개 0 |
| SIG1 | `SIGNAL_MIDBLOCK_COM_SKIPS > 0` | 참 | 참 | 참 | 1,320 / 1,320 / 1,320 |
| SIG2 | `signal_readback.csv` `sg_no ≥ 9` 행 0 | 참 | 참 | 참 | 0 / 49,402·49,357·49,742행, 최대 `sg_no` 8, ok≠1 0, 요청≠되읽음 0 |
| DEC1 | `action_\d{6}.json` 61, OK + HELD = 61, 유지 T 집합 다섯 곳 같음 | 참 | 참 | 참 | 61 = 6 + 55, 61 + 0, 다섯 곳 모두 빈 집합 |
| DEC2 | 예열 no-control | 참 | 참 | 참 | `WARMUP_CONTROLLER` 6줄(T 1·150·…·750) |
| DEC3 | 유지 아닌 T ≥ 900 `sdmpc_active` 참 + `.applied`·`.sdmpc_pending` | 참 | 참 | 참 | 55/55, 둘 다 55 |
| DEC4 | 예산 `unlimited_time` 참·`expired_stage` null(키 있음)·`output_completed` 참 | 참 | 참 | 참 | 61/61 |
| DEC5 | 유지 아닌 결정 exit 0, 런로그 결정 줄 61 | 참 | 참 | 참 | 61/61 exit 0 |
| PROV1 | head = K9-2-7 40자리 (읽는 법 A) | 참 | 참 | 참 | §4 |
| PROV2 | 튜닝 `c8e3ee2c…1866` | 참 | 참 | 참 | §4 |
| PROV3 | 망 `3de889f0…1c2e` | 참 | 참 | 참 | §4 |
| 동결본 | `FREEZE.json` `011f5be2…8476` | 참 | 참 | 참 | §4 |
| 환경 | provenance env 정책 hold·`FAIL_FAST=1`, plan `expected_env` 같음 | 참 | 참 | 참 | §4 |
| 런로그 | 시작 줄 `DECISION_ERROR_POLICY=hold_previous_on_exception` 정확히 1줄 | 참 | 참 | 참 | 1줄 |
| 시드 | provenance·plan seed = S | 참 | 참 | 참 | 31 / 41 / 43 |
| VSL1 | 연속 결정 구역별 \|Δ명령\| ≤ 40, 유지 T Δ = 0 | 참 | 참 | 참 | 60쌍, 위반 0, 최대 10 km/h |
| VSL2 | 블록 0 VSL 축 허용집합 = (80, 90, 100, 110) | 참 | 참 | 참 | 결정당 6축 × 55 = 330 |
| MTR | RM_C10490 쓴 녹색에 3 없음(K3) | 참 | 참 | 참 | 러너 로그 61행 중 3 s 0, 어댑터 CSV 3 s 0 |
| K8a | 유지 아닌 T ≥ 900 `stopline_approach_install_check` 있고 `passed` 참 | 참 | 참 | 참 | 55/55 |
| K8b | 결정마다 S6 캡처 2개(+유지 T 캡처) | 참 | 참 | 참 | stdout·stderr 61/61 |
| U9-a | 사슬 1–5 불일치 0, ok≠1 0, 관련 `ERROR` 0, 되읽기 행 = 61 × 66 × 4 | 참 | 참 | 참 | 4,026행 검사, 불일치 0, `vsl_readback.csv` 16,104행, 금지 속도 행 0 |
| J1-V | `pairing_check(t_act=900)` ok (같은 시드 NC3) | 참 | 참 | 참 | §6 |

- `failed_items = []` ×3, 셈한 항목 27개 ×3 [실행 `VAL/out/va_check_s31.json` `f43bd050…`, `_s41` `446a4512…`, `_s43` `60dba8bb…`].
- U9-a 묶음 공허 규칙(K7 §3.4: 세 런 모두 110 미만 쓰기 0건이면 공허): 110 미만 명령 행이 세 런 모두 있음 → **공허 아님** [실행]. 행 수·T는 분석 §8.3-7 몫이라 여기서는 "0이 아님"만 적습니다(JSON에는 J1 꼴대로 남음).
- 보고만: 어댑터 CSV 행 머리 61/61 정상, `metadata`가 `ok`로 시작하지 않는 행 0, `metadata.sim_sec` = T 61/61, 러너 행동 로그 12,159행·61 시각, state CSV 61행 모두 `ok`.

## 4. 출처 (보충 34 §7.1 표) [실행]

| 출처 | 기대 | v3c3-s31 | v3c3-s41 | v3c3-s43 |
|---|---|---|---|---|
| launch `FREEZE_VERIFIED … head=` (줄 수) | `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d` | 같음 (1) | 같음 (1) | 같음 (1) |
| plan `freeze.head` · FRZ_K92 `FREEZE.json` `git.head` | 같음 | 같음 · 같음 | 같음 · 같음 | 같음 · 같음 |
| run_provenance `workspace_git_commit` (보고만, 읽는 법 B 판정에 쓰지 않음, 보충 34 §7.1 PROV1 행) | — | `''` | `''` | `''` |
| `FREEZE.json` 파일 sha · plan `freeze.sha256` · `FREEZE_VERIFIED` · `PROVENANCE_OK` 2줄(사전점검·런 끝) | `011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476` | 모두 같음 | 모두 같음 | 모두 같음 |
| 튜닝: plan · provenance `files.tuning` · env `RW_SIGNAL_OBSERVATION_CONFIG_SHA256` · FRZ_K92 파일 · 사전점검 provenance | `c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866` | 다섯 곳 같음 | 다섯 곳 같음 | 다섯 곳 같음 |
| 망: provenance `files.network` · 런 폴더 `.inpx` 해시 · `NETWORK_COPY_OK … sig=42` · `NETWORK_OK` · `LAUNCH_PLAN_DETAIL network_sha=3de889f0 controller=wu-link seed=S sim_period=9000` | `3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e` | 같음 | 같음 | 같음 |
| env `RW_DECISION_ERROR_POLICY` / `RW_DECISION_FAIL_FAST` / plan `expected_env` / 사전점검 env | hold / `1` / hold / hold | 같음 | 같음 | 같음 |
| WD 정책 줄(launch) | WD 호출마다 1줄 = 2줄, strict 0 (H10 읽는 법) | 2 | 2 | 2 |
| plan 컨트롤러 [컨트롤러, 예열, 시작, 간격, 길이] · `warnings` | [wu-link, no-control, 900, 150, 9000] · [] | 같음 | 같음 | 같음 |
| VBS · WD · `control_area_objective.py` sha (보고) | FRZ_K92 파일 = provenance 기록 | `bffb59f8…` · `83c36301…` · `2c21cd8c…` 같음 | 같음 | 같음 |
| `decision_hold.py` sha (보고, FRZ_K92 파일만) | — | `69e7a0a9…` | 같음 | 같음 |

- VBS·WD sha는 K8b와 같습니다(`FREEZE_PUSH.md` 공개 9번과 같은 값) [읽음 `VA/FREEZE_PUSH.md:66`; 실행].

## 5. 유지 감사 H-A (보충 21 §4.2) [실행]

| 항목 | v3c3-s31 | v3c3-s41 | v3c3-s43 |
|---|---|---|---|
| H-A1 영수증 항목·sha | 빈 검사(유지 T 0) | 빈 검사 | 빈 검사 |
| H-A2 유지 CSV = 원천 CSV | 빈 검사 | 빈 검사 | 빈 검사 |
| H-A3 유지 JSON 7필드·metadata 키 집합·`sdmpc_state` 없음 | 빈 검사 | 빈 검사 | 빈 검사 |
| H-A4 유지 T `.applied`·`.sdmpc_pending` 없음, 다음 결정의 직전 출처 | 빈 검사 | 빈 검사 | 빈 검사 |
| H-A5 실패 부분 산출물 | 빈 검사(`.failed_decision` 0) | 빈 검사 | 빈 검사 |
| H-A6 "명령 미기록" 검사 | 빈 검사 | 빈 검사 | 빈 검사 |
| H-A7 `.error.txt` 재판정 | 빈 검사(`.error.txt` 0) | 빈 검사 | 빈 검사 |
| H-A8 런로그 순서 | 빈 검사(유지 줄 0) | 빈 검사 | 빈 검사 |
| H-A9 연속 유지 예외 서명 (질문 지점) | 해당 없음 | 해당 없음 | 해당 없음 |

- 위반 0, INCOMPLETE 0 ×3. 유지 0은 다섯 곳(영수증, 런로그 두 종류, `.error.txt`, `controller_status`)과 끝 요약 `DECISIONS_HELD_ON_EXCEPTION=0`이 모두 같게 말합니다.
- H-A4·H-A6 읽는 법이 정상 결정에서 성립하는지(보고만): 러너 행동 로그 T 행 = 어댑터 CSV 61/61, 다음 결정의 `vsl_cohort_initialization` = 직전 action JSON(이름·sha) 60/60 — 세 런 모두 [실행 `/comparator_selftest`]. 그래서 유지가 있었다면 위 두 검사가 셀 수 있었을 것입니다 [추론].

## 6. J1-V 짝 (머리 구간판) [실행 `va_j1a.py pair --profile va`]

- 방법은 J1 `VALIDITY.md` §2.1과 같습니다. 고정 도구 `D:/VISSIM-merge/tools/stage1`(sha 4개 = K7 §3.6 값, 실행 때 대조)의 `stage1_scan.scan`을 FZP 앞 950 s에만 돌리고 `stage1_report.pairing_check(S, NC3, V-A, t_act=900)`을 그대로 불렀습니다. V-A FZP의 0.10 s 행은 뺐습니다(v3c3-s31·v3c3-s41 각 1행, v3c3-s43 0행). 앞 950 s의 TTT 합은 도구 안에서만 계산되고 파일·화면에 내지 않았습니다.

| 시드 | seed nc/arm | 프레임 시각 같음 | 첫 갈림 프레임 | 첫 갈림 진입 | 입력 | 900 s 전 프레임(전체·Ω 대수 같음) | 900 s 전 진입 | ok |
|---|---|---|---|---|---|---|---|---|
| v3c3-s31 | 31/31 | 참 | 905.1 s | 918.5 s | 34 | 179 (참·참) | 6,969 = 6,969 | **참** |
| v3c3-s41 | 41/41 | 참 | 905.1 s | 915.7 s | 34 | 179 (참·참) | 7,061 = 7,061 | **참** |
| v3c3-s43 | 43/43 | 참 | 915.1 s | 927.0 s | 34 | 179 (참·참) | 6,965 = 6,965 | **참** |

- 900 s 전 진입 수는 같은 시드 J1과 같습니다(6,969 / 7,061 / 6,965) [실행 §2].
- 출력 `VAL/out/va_pair_s31.json` `ffc5cad7…`, `_s41` `b08d375b…`, `_s43` `d6315a1f…`.

## 7. 보고만 (판정 아님, 성능 숫자 아님)

### 7.1 T = 150 계수 (보충 34 §7.1, 보충 24 §14.2)
- `action_000150.json` `metadata.head_observation_prior_discarded` = 1.0: v3c3-s31·v3c3-s41·v3c3-s43 모두 참. 1.0인 T 목록 = [150] ×3(다른 T 0개). 키는 61/61 결정에 있음 [실행]. 이 계수는 J1-A 항목이 아닙니다.

### 7.2 W·H-b 키 (V-A 배포 확인)
| | v3c3-s31 | v3c3-s41 | v3c3-s43 |
|---|---|---|---|
| `k92_w` 사전 있음 (61결정 / SDMPC 55) | 61 / 55 | 61 / 55 | 61 / 55 |
| `k92_hb` 사전 있음 (61 / 55) | 61 / 55 | 61 / 55 | 61 / 55 |
| `k92_w.after` repr = `5209.8` | 61 | 61 | 61 |
| (173, p4) 하한 키 정확히 1개 | 61 | 61 | 61 |
| 런 안 하한 키 이름 | `…_0d58a14f910af049` 하나 | `…_d53f3bddee47d38c` 하나 | `…_d7feec1450ade0a4` 하나 |
- 이름은 T = 900 건강 점검 이름과 같습니다. 하한 값·씨앗 묶임 계수·줄어든 T는 분석 §8.3-5 몫이라 이 단계에서 열지 않았습니다 [실행].

### 7.3 결정 벽시계 [실행 runlog `CONTROLLER_DECISION … wall_sec`, `WATCHDOG_EXIT`]
| | v3c3-s31 | v3c3-s41 | v3c3-s43 |
|---|---|---|---|
| 예열 6개 (s) | 18.89–23.01 | 19.00–22.11 | 18.34–22.81 |
| SDMPC 55개 최소 / 중앙 / 평균 / 최대 (s) | 164.73 / 536.55 / 513.5 / 743.70 | 186.83 / 559.38 / 539.2 / 818.56 | 266.03 / 473.02 / 465.4 / 782.80 |
| 900 s 넘는 결정 | 0 | 0 | 0 |
| 런 벽시계 `WATCHDOG_EXIT wall_sec` | 36,037 s (10.0 h) | 37,583 s (10.4 h) | 32,562 s (9.0 h) |
| J1 같은 시드 SDMPC 중앙 / 런 벽시계 [읽음 `J1_REPORT.md:408-410`; 실행 자기 시험] | 469.57 / 30,699 | 409.58 / 30,045 | 489.96 / 33,055 |
| 비 V-A 중앙 / J1 중앙 [계산] (G-K5 예산 1.0158은 옆에 적기만 함) | 1.1426 | 1.3657 | 0.9654 |
- 보충 34 §8.3-9: 이 비는 보고만이고 G-K5와 같은 양이 아닙니다(폐루프 상태가 다름). 분석 단계가 같은 비를 다시 냅니다.
- 동시 실행 [읽음 `RVA/wmi_launch_lines.txt`, 감시기 로그]: v3c3-s31(발사 12:34:21)·v3c3-s41(발사 12:36:17)은 12:36–22:35 동안 함께 돌았고(VISSIM 2), v3c3-s43은 22:36:57에 v3c3-s41이 돌던 중 `-AllowConcurrentDev`로 떠 23:03:01까지 약 26분 v3c3-s41과 겹쳤고, 그 뒤 혼자 돌았습니다. v3c3-s31과 v3c3-s43은 겹치지 않았습니다(22:35:18 끝, 22:36:57 발사). [r2: r1의 "12:34–22:35 내내"를 발사 시각에 맞춰 고침, §13] [추론] 동시 실행은 결정 벽시계에 영향을 줄 수 있습니다(시험하지 않음).

### 7.4 런 폴더가 런 끝 뒤 바뀌지 않음
- `EXIT` 줄 + 60 s 뒤 수정된 파일: 0 / 1,015 (v3c3-s31, 마지막 22:35:24), 0 / 1,015 (v3c3-s41, 마지막 23:03:03), 0 / 1,015 (v3c3-s43, 마지막 07:40:02) [실행].

### 7.5 VISSIM `.err` 두 사본 (내용은 `DECISION_FAILED` 수만 셈)
| | 최상위 `vissim_simulation_001.err` | `network/sdmpc31_<런>_001.err` | 같음 |
|---|---|---|---|
| v3c3-s31 | 311,296 B, 22:11:46, `8a4ca925…` | 317,794 B, 22:35:24, `fe31b2fc…` | 아니오 |
| v3c3-s41 | 311,296 B, 22:44:09, `5c70644a…` | 316,153 B, 23:03:03, `e7eb32e8…` | 아니오 |
| v3c3-s43 | 330,522 B, 07:40:01, `99265964…` | 같음 | 예 |
| J1 세 런(자기 시험) | — | — | 모두 예 |
- 해석과 영향은 §0 (가). 미삽입 remain 줄과 차로변경 제거 대수는 분석 단계에서 처음 엽니다.

### 7.6 FRZ_K92 다시 해시 [실행 `va_j1a.py freeze --profile va` → `VAL/out/va_freeze_k92.json` `918aed11…`]
- `FREEZE.json` sha `011f5be2…8476`, `git.head` `c20aff1d…`, 표 10,569개 파일 모두 같음(다름 0, 없음 0), 표 밖 비캐시 파일 0.
- 표 밖 캐시 229개(`__pycache__` 139, `__tangentcache__` 90), 시각 2026-10-23 12:34:44–12:52:39 = 발사 단계 스냅숏 `snap_02`의 값과 같음. 런이 쓴 캐시이고 J1과 같은 수입니다(S-VA-5 보고만) [실행·읽음 `VA/LOG.md` 13:03:58 줄].

### 7.7 그 밖
- FZP 마지막 프레임 8,995.1 s ×3(파일 끝 64 KB에서 시각만 읽음). 분석 적분 구간(5.1–8,995.1 s)을 덮습니다.
- S6 stderr가 빈 파일이 아닌 결정 55개 ×3(SDMPC 결정마다). J1 v3c3-s31 재실행도 55개로 같은 꼴이며 `DECISION_FAILED`는 0입니다 [실행].
- NC3 세 폴더의 마지막 수정 시각 2026-10-01(12:07 / 12:11 / 12:10) [실행].

## 8. 실패 시드와 STOP 규칙 (보충 34 §7.1 :363-365, §7.2 :369-397)

| 시드 | 개정 J1-A 거짓 | H-A1–8 위반 | `EXIT` code≠0 또는 없음 | `STAGE=SIM_DONE` 없음 | 건강 점검 STOP | 출처가 §7.1 표와 다름 | INCOMPLETE | 실패 시드 |
|---|---|---|---|---|---|---|---|---|
| v3c3-s31 | 0 | 0 | 아니오 | 아니오 | 없음(18/18) | 아니오 | 0 | **아님** |
| v3c3-s41 | 0 | 0 | 아니오 | 아니오 | 없음(18/18) | 아니오 | 0 | **아님** |
| v3c3-s43 | 0 | 0 | 아니오 | 아니오 | 없음(18/18) | 아니오 | 0 | **아님** |

| 규칙 | 상태 |
|---|---|
| S-VA-1 실패 시드 ≥ 2 → 분석 전체 STOP | 걸리지 않음 (실패 시드 0) |
| S-VA-2 실패 시드 1 → STOP | 걸리지 않음 |
| S-VA-3 건강 점검 거짓 | 걸리지 않음 (세 런 18/18) |
| S-VA-4 감시·유효성 단계에서 성능 숫자를 내거나 엶 | 걸리지 않음 (§10) |
| S-VA-5 동결본·J1·NC3·R-obs3 폴더 쓰기 | 걸리지 않음 (FRZ_K92 캐시 229는 런이 쓴 것, 보고만; 이 단계 쓰기 0) |
| S-VA-6 질문 지점(유지, H-A9, VISSIM ≥ 5, `GIVE_UP`, 좌석 24 h) | 없음 (유지 0, 발사 뒤 VISSIM 최대 2, `WATCHER_DONE`) |
| S-VA-7 WD가 끝내지 못한 멈춤 / `EXIT` 없이 죽음 | 걸리지 않음 (`EXIT` 줄 ×3, cmd PID 없음) |
| S-VA-8 발사 거부 | 걸리지 않음 (`ReturnValue` 0 ×3, `REFUSED`·`NOT_LAUNCHED` 0) |
| S-A34-8 봉인 시드·codex 64cf·v3c3-s47 | 열기·사용 0 (§0 (라) 이름 목록 노출만 공개) |
| S-A34-9 C:·D: < 8 GB | 걸리지 않음 (33 GB · 346 GB) |
| S-A34-10 K8 가지 이동 | 걸리지 않음 (`b9734abe…`) |

- **결과: 보충 34가 정한 STOP 규칙 중 걸린 것이 없고, 실패 시드는 0개입니다. 세 시드 모두 유효 런이 있으므로 §8.0 순서대로 보고 머리 → 분석으로 갈 수 있습니다.**

## 9. 다음 단계에 넘기는 것

1. 분석은 고정된 `ANALYSIS_METHOD_VA.md`·분석 도구(`VA/analysis/va_analysis_pins.sha256`, 20줄, 20/20 OK; r1의 "21/21"은 오기)로 합니다. 보고 머리(보충 21 §5 1–10, 시드마다)는 이 문서의 유지 표·§4 출처·§5 H-A를 옮기면 됩니다.
2. `.err` 최상위 사본 문제(§0 (가))는 분석 판정 입력에 들어가지 않습니다 [읽음]. 보고서 공개 칸에 한 줄 적기를 권합니다.
3. 결정 벽시계 비(§7.3)는 분석 §8.3-9가 같은 정의로 다시 냅니다.

## 10. 방법과 지킨 것

- 읽기만: V-A 세 런 폴더, RVA 최상위 로그, J1 세 런 폴더, NC3 세 폴더, FRZ_K92·FRZ_K8b·FRZ_K8, stage1 도구, G-H1 관문 출력. 파일은 읽기로만 열었고(action JSON 61개는 한 번에 하나, 약 58 MB씩), 런 폴더·동결본·NC3의 수정 시각 변화 0 [실행 §7.4, §7.6, §7.7].
- 성능 숫자 0: 도구는 목적값·예측·가격·Ω·TTT·지연·녹색 값을 출력에 넣지 않습니다. stage1 머리 구간 스캔이 안에서 계산하는 앞 950 s TTT 합은 메모리에만 있었습니다. VISSIM `.err`에서는 `DECISION_FAILED` 문자열 수와 파일 크기·sha만 봤습니다.
- 실행 위생: 모든 Python은 `python -B`, `PYTHONHASHSEED=0`, 도구 안에서 BELOW_NORMAL(0x4000), 한 번에 하나. 가장 긴 것은 동결본 재해시(FRZ_K8b 약 150 s, FRZ_K92도 5분 미만)라 WMI 분리 없이 돌림. VISSIM·COM·러너·재생·동결·커밋·푸시 0, 금지 시험 7종 0, `watch_sdmpc.py` 0. 띄우거나 끈 프로세스 0(이 세션의 짧은 Python 외).
- 쓴 곳: `VAL/`(도구·고정 목록·`out/`·이 문서), `VA/LOG.md` 덧붙임, 사본 `REPVA/VALIDITY_VA.md`·`REPVA/validity/`.

## 11. 파일 (sha256) [실행]

| 파일 | sha256 |
|---|---|
| `VAL/va_j1a.py` (고정) | `968891df5b19627bf7743b8b39a871704509b8d4f3e6643d35cbec25d6ac88c6` |
| `VAL/va_j1a_selftest.py` (고정) | `2c7046017a153824291176218d60cf552582a53dbd7058016382cdec27463592` |
| `VAL/va_j1a_pins.sha256` | `43c6360da7f2812e26540ce18f238dd8f14bc2833c3752fbfdc8075a3bc54942` |
| `VAL/out/va_check_s31.json` / `_s41` / `_s43` | `f43bd050754b9d52…` / `446a4512f940611e…` / `60dba8bb136691fd…` |
| `VAL/out/va_pair_s31.json` / `_s41` / `_s43` | `ffc5cad729367f4c…` / `b08d375b0a27f43c…` / `d6315a1ff444d790…` |
| `VAL/out/va_freeze_k92.json` | `918aed117832de1b…` |
| `VAL/out/selftest/selftest_compare.json` | `4241cf9f81c0a3a0…` |
| `VAL/out/selftest/st_check_j1r_s31.json` / `st_check_j1_s41.json` / `st_check_j1_s43.json` | `e6a9269d5786ceae…` / `6bb8852bada5079c…` / `d21506a3278e5657…` |
| `VAL/out/selftest/st_pair_j1r_s31.json` / `_j1_s41` / `_j1_s43` | `a3429aa5bd8178a4…` / `b0089508ddf920b1…` / `44330f5d1833fa5e…` |
| `VAL/out/selftest/st_freeze_j1r.json` | `3585444270fb9464…` |
| `VAL/out/selftest/st_ha_T003900_i1.json` / `_i3` / `_i4` | `aa7767f0b58959cc…` / `be46a6070620a78a…` / `1deeb927891afedc…` |
- 이 문서의 sha와 사본 대조는 `REPVA/validity/SHA256SUMS_VALIDITY.txt`에 있습니다.

## 12. 열린 것

- 사용자 결정이 필요한 질문은 없습니다.
- 공개 다섯 가지(§0 (가)–(마))는 판정에 영향이 없습니다. (가)의 원인(동시 실행 중 러너의 `.err` 복사 시점)은 시험하지 않은 추론입니다.

## 13. 바뀐 곳 (r2, 2026-10-24 KST; r1 `VAL/VALIDITY_VA_r1.md` `2021bb11e91eb407…` 대비)

- 근거: 검증 `VA/analysis/VERIFY_VA_r1.md`(sha256 `292b71413ef52efa9d2ee0125978c82c55783fdc126b76798b6c3c33e92956c9`) §5 B1–B3. 그 검증은 이 문서의 숫자·셈(런로그 셈, `.err` 두 사본, v3c3-s43 발사 시각·플래그, 벽시계 비, FRZ_K92 재해시)이 다시 나온다고 적었습니다 [읽음].
- 바꾸지 않은 것: J1-A 항목·정의·참/거짓, H-A 결과, J1-V 값, STOP 규칙 상태, 실패 시드 0, 결론 1–9, 도구 `va_j1a.py`(`968891df…`)·`va_j1a_selftest.py`(`2c704601…`)·고정 목록 `va_j1a_pins.sha256`(`43c6360d…`), `VAL/out/` 출력 [실행 sha 대조]. 다시 계산한 것 0.

| # | 자리 | r1 | r2 | 까닭 |
|---|---|---|---|---|
| 1 | 머리 | — | "판: r2" 한 줄 | 판 표시 |
| 2 | 줄임말 | GWT8·REP8·H10·R-obs3 등이 풀리지 않음 | GWT8, K8 가지, K9-2-7, GB, REP8, R-obs3, K7·K8·K8b·K3, H10, G-H1, G-K5, S-VA, S-A34, VBS·COM, WMI, BELOW_NORMAL을 풂; 파일·런 이름 안의 시드 번호 읽는 법 한 줄 | B3 (그리고 같은 꼴의 풀리지 않은 줄임말) |
| 3 | §0 (다), §1 표, §9-1 | "21/21 OK" (세 곳) | "20줄, 20/20 OK" + r1 오기 표시 | B1. 목록 파일은 2026-10-23 12:27 뒤 그대로(sha `39a97e7f…903e`)라 이 단계 때도 20줄 [실행 `wc -l`·`sha256sum -c`] |
| 4 | §0 (가)·(나), §1 표 둘, §2 표·글, §3·§4·§5·§7.2·§7.3 표 머리, §6·§7.1·§7.3·§7.4·§7.5·§7.7 글 | 맨 s31·s41·s43, "j1r s31 check", "j1 s41·s43 check" | v3c3-s31·v3c3-s41·v3c3-s43, "J1 v3c3-s31 재실행 런(j1r) check", "J1 v3c3-s41·v3c3-s43 런 check" | B2 |
| 5 | §7.3 동시 실행 글 | "s31·s41은 12:34–22:35 내내 함께", v3c3-s43은 "23:03부터 혼자" | 발사 시각(12:34:21·12:36:17·22:36:57)과 끝 시각으로 겹친 구간을 적음: v3c3-s31·v3c3-s41 12:36–22:35, v3c3-s43·v3c3-s41 22:36:57–23:03:01(약 26분), v3c3-s31·v3c3-s43 겹침 없음 | 글이 발사 시각과 어긋남(검증 A6과 같은 사실) [읽음 `VA/launch/wmi_launch_lines.txt`, `launch_s{31,41,43}.json`, 위 §1 `EXIT` 시각] |
| 6 | 끝 | — | 이 §13 | 바뀐 곳 기록 |

- `VA/LOG.md`의 2026-10-24 07:58:00 [Validity] 줄에도 "21/21 OK"가 있습니다. 옛 줄은 지우지 않고, 정정 줄을 LOG에 덧붙였습니다.
- 이 판 sha256은 `REPVA/validity/SHA256SUMS_VALIDITY.txt`(r2로 갱신; r1 목록은 `SHA256SUMS_VALIDITY_r1.txt`)에 있습니다. 사본 `REPVA/VALIDITY_VA.md`·`REPVA/validity/VALIDITY_VA.md`를 이 판으로 바꾸고, r1 사본은 `_r1` 이름으로 둡니다. `VA/analysis/VA_REPORT.md`(r2)의 인용 sha도 이 판으로 맞춥니다.

### 13.1 바뀐 곳 (r3, 2026-10-24 KST; r2 `VAL/VALIDITY_VA_r2.md` `8f57c3ab63648626…` 대비)

- 근거: 검증 `VA/analysis/VERIFY_VA_r2.md`(sha256 `ba7c3495ee4299d8629e252b9c6e6f4ac95ffceb4946da5939338c14c2166509`) §5 D2·D3. 그 검증은 이 문서 r2의 런로그 셈·`.err` 두 사본·발사 시각·벽시계 비가 다시 나온다고 적었습니다(§4.4) [읽음].
- 바꾸지 않은 것: 위 §13 "바꾸지 않은 것" 전부, 그리고 r2의 표 줄 모두(같은 순서·같은 바이트; 더한 표 줄은 아래 표뿐) [실행 `diff`]. 다시 계산한 것 0.
- 아래 "자리"는 r2 `VALIDITY_VA_r2.md`의 줄 번호입니다.

| # | 자리 | r2 | r3 | 까닭 |
|---|---|---|---|---|
| 1 | 머리 (:7) | "판: r2" 줄 | "판: r3" 줄(r2 파일 자리·sha를 더함) | 판 표시 |
| 2 | 줄임말 (:17) | "K9-2-7 = GB-7′ 목록 보충 커밋 …. GB = 기가바이트(디스크 여유)." | "K9-2-7 = GB-7′ 허용 목록 보충 커밋 …. GB-7′ = 무제어 61결정 재생 출력 대조 오프라인 관문(보충 34 §5.1). 디스크 여유의 GB는 기가바이트." | D2: GB-7′ 풀이가 없었고, 같은 줄의 GB(기가바이트)와 헷갈릴 수 있었음 [읽음 보충 34 줄임말 절 :15–16(K9-2-7, A = GB-7′ 허용 차이 경로 목록), §5.1 표 :231] |
| 3 | 줄임말 (:19 뒤, 새 줄) | — | §3 표 '#' 칸의 항목 이름은 보충 34 §7.1·J1 `VALIDITY.md` §2의 항목 이름이고, 줄임말의 K8·K8b·S6과 다른 말이며, 뜻은 '항목 (정의)' 칸을 따른다는 한 줄 | D3: r2 줄임말의 K8·K8b(문서·단계 이름)·S6(캡처 이름)과 §3 표 행 이름 S6·K8·K8b가 엇갈림 [읽음 보충 34 §7.1 :346, J1 `VALIDITY.md` §2 표] |
| 4 | 끝 | — | 이 §13.1 | 바뀐 곳 기록 |

- 이 판 sha256은 `REPVA/validity/SHA256SUMS_VALIDITY.txt`(r3로 갱신; r2 목록은 `SHA256SUMS_VALIDITY_r2.txt`, r1 목록은 `SHA256SUMS_VALIDITY_r1.txt`)에 있습니다. 사본 `REPVA/VALIDITY_VA.md`·`REPVA/validity/VALIDITY_VA.md`를 이 판으로 바꾸고, r2 사본은 `_r2` 이름으로 둡니다. `VA/analysis/VA_REPORT.md`(r3)의 인용 sha도 이 판으로 맞춥니다.
