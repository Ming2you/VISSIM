# 하이브리드 빌드 — 고속도로 규칙(Carlson MTFC-VSL + ALINEA) × 도시 SDMPC, v3c1 s31 9,000 s

- 작성 2026-09-29. 태그: [실행] 이 세션에서 돌려서 확인 / [읽음] 코드·파일을 읽어서 확인 / [추론] 근거는 있으나 직접 확인 못 함
- 설계서: `hybrid/HYBRID_DESIGN.md`, 파라미터: `hybrid/hybrid_parameters.json`
- **런은 띄우지 않았다.** VISSIM·cscript 시작/종료 없음. 금지 시험(watchdog·cscript·ps1 시험) 실행 없음. 푸시 없음.

---

## 0. 결론

| 항목 | 결과 |
|---|---|
| 워크트리 | `D:/VISSIM-merge/sim3-n31-hybrid`, 브랜치 `claude/hybrid-rulefw-sdmpc-urban-20260929` (9ed2ef0 에서, 저장소 `D:/VISSIM-merge/repo`) [실행] |
| 커밋 | **43150c8** (Ming2you, 명시 경로 9개, 로컬만) [실행] |
| FRZ | **`D:\VISSIM-merge\frozen\sdmpc31_43150c8e_202609291223`** (FREEZE sha 1d9ca69a, 파일 10,313, status_entries 0) [실행] |
| 사전점검 | `run_sdmpc_n31.ps1 -Freeze -PreflightOnly` **EXIT 0**, PROVENANCE_OK, `RW_RULE_OBSERVATION=1` 전달 확인 [실행] |
| 키 부재 비트 동일 | SDMPC wu-link 결정 재생(R-obs 900) 9ed2ef0 대비 **IDENTICAL**(커밋 후 재확인), no-control 재생 8상태 기록과 **IDENTICAL** [실행] |
| 하이브리드 재생 | R-obs 900/2700/4500/6300 **4/4 PASS**. VSL 90(2700)·100(4500) 이 CSV DSD 59–62 에 쓰이고 63–66 은 110 [실행] |
| 워밍업 짝 | 하이브리드 튜닝의 no-control 결정(t=1/150/750) CSV 가 R-obs 와 바이트 동일 → 900 s 까지 R-obs 와 짝 [실행] |
| PYTHONHASHSEED | 러너→감시자→cscript→python→워커 모두 상속 [읽음]. WMI 명령줄 안에서 세워야 함(§7) |

---

## 1. 무엇을 만들었나 (config 키 하나: `adapter.sdmpc_freeway_rule`)

### 1.1 새 모듈 `evaluation/controllers/freeway_rule_hybrid.py` (395행)
- `validate_section`(정적 스키마) / `configure(section, cfg)`(설치된 모형과 대조, `sdmpc.configure` 에서만 호출)
  - 물리 미터 8개·10 s 주기·±2 s, 적용 구역 머리 10 바로 다음 머리 12 가 가속 구역, 적용 구역은 free·가속 구역은 fixed, 표지판 셀(10, 13)이 각 머리를 읽는지, 속도 단계 ⊂ 행동 집합이고 최댓값에서 끝나는지, 미터 8개와 요청 범위가 설치된 서비스표 안인지.
- `observe`: `state_json.rule_observation` 의 완료 창(시각·창 시작/끝·단위) 확인 뒤 **차로 행을 measurement_no 로만** 고른다. 측정소 집계값은 안 쓴다(같은 이름의 상류 묶음 910001–058 이 섞여 있음).
- `carlson_step`: 속도형 PI. `b(k)=clip[80/110,1](b(k-1)+K_P(o(k-1)-o(k))+K_I(ô-o(k)))`, 첫 결정 P=0, 적분기 = b 자체(자르기로 anti-windup), `v*`=가장 가까운 단계(동률 위), 결정당 ≤20 km/h.
- ALINEA 8개: `diagnostic_profile.alinea_meter_step` 그대로(±2 s 상자, 도달 범위로 적분기 자르기).
- `load_history`: 직전 행동이 하이브리드면 `metadata.hybrid_rule.next_history` 를 읽되 **`.applied` 영수증(시각·CSV 경로·크기)** 과 섹션 sha, 직전 시각, 적용된 녹색/VSL 일치를 모두 요구. 직전이 워밍업(no-control)이면 첫 결정 초기화(녹색=적용값, r~=그 녹색의 서비스, b=1, o(k-1) 없음). 직전이 SDMPC 인데 이력이 없으면 예외.
- `apply`: 기준 행동에 녹색(물리 ±2 s 상자 통과)과 구역 VSL 을 셀별로 넣는다. `verify_applied`: SDMPC 가 고른 행동의 고속도로 명령이 규칙 명령과 같은지 확인.
- 기록: `metadata.hybrid_rule`(관측 차로 행, 이력, ALINEA 감사, MTFC 단계, 명령, next_history, `python_hash_seed`).

### 1.2 기존 코드 수정 (전부 키 부재 시 동작 불변)
| 파일 | 변경 | 근거 |
|---|---|---|
| `sdmpc.py:216-220` | `configure`: 키가 있으면 `options['freeway_rule']=spec` | |
| `sdmpc.py:330-356` | `Coordinates`: 규칙이 있으면 미터·VSL 축 `allowed=[기준값]`(폭 0), 상자 밖이면 예외 | 3블록 `SequenceCoordinates` 도 블록마다 이것을 씀 → 450 s 지평 동안 명령 고정 |
| `sdmpc.py:456-465` | `solve_qp`: **모든 좌표가 경계로 고정된 QP** 는 경계점을 답(행 제약은 검사) | 재생 중 발견: 고속도로 소유자 축이 전부 폭 0 이면 scipy `minimize` 가 SLSQP 없이 결과를 돌려주고 `nit` 가 없어 `AttributeError: nit`(hyb_2700 첫 재생). 기본 경로에선 이 상황이면 원 코드가 죽으므로 도달 불가 → 비트 동일 |
| `sdmpc.py:552, 587-593` | `solve(..., freeway_rule=None)`: `prepare_held_actual_reference` 직후 기준 행동에 규칙 명령 적용(콜백·좌표·PFO 온기동이 모두 이 기준에 앵커). 이동 상자는 실제 직전 행동에 그대로 | |
| `joint_owner_game.py:147-180` | `build_ownership`: 규칙이 있으면 선언된 구역 머리(FW_E [0,5,10,12,15])를 받고, free 3개 밖의 머리(12, 15)를 fixed_recovery 로 | 원 코드는 (0,5,10,15)·21셀 확장·free site {0,5,10} 을 하드코딩(SDMPC 매 결정 호출) |
| `vissim_stackelberg_adapter.py:13010, 13059-13073` | `run_joint_owner_decision(..., rule_observation=None)`: SDMPC 전에 규칙 결정, 뒤에 `verify_applied`, `report['hybrid_rule']` | |
| `vissim_stackelberg_adapter.py:13852-13856` | `rule_observation=state_json.get('rule_observation')` 전달, `metadata['hybrid_rule']` 기록 | 키 부재면 `joint_report` 에 없음 |
| `scripts/run_real_world_stackelberg_controller.vbs:2822-2827` | 규칙 프로파일이 아니고 `RW_RULE_OBSERVATION=1` 이며 simSec ≥ ControlStartSec 이면 기존 `RuleObservationJson` 으로 `rule_observation` 기록 | 변수 없으면 아무것도 안 읽고 안 씀 |
| `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1:320-355` | 튜닝 사슬에 `adapter.sdmpc_freeway_rule` 가 있으면 `RW_RULE_OBSERVATION=1`, 없으면 변수 제거 | `RW_DECISION_FAIL_FAST` 와 같은 “config → env 운반” 방식. 바이트 보존(CRLF)으로 삽입 |
| `diagnostics/sdmpc_n31_20260924/make_config_n31.py` | `--hybrid-rule [--check]` → `config_n31_v2_hybrid_carlson_alinea.json` | 기본·urban_b1 `--check` 통과(기본 sha 3302725804… 불변) [실행] |

### 1.3 설계서와 달라진 점 (이유)
1. **관측 전달(M1 변형)**: 설계는 VBS config 사본에 `RW_RULE_OBSERVATION = True` 를 넣자고 했으나, runner config 는 plant manifest 가 sha 로 고정하고 `validate_tuning_v2` 가 `execution.signal_vbs_config == manifest runner_config` 를 요구한다(`obs150_contract.py:205-206`) [읽음]. 사본을 쓰면 plant manifest 두 벌이 필요해서, 기존 관례(감시자가 튜닝 키를 env 로 운반, `RW_DECISION_FAIL_FAST`)를 따랐다. 스위치는 여전히 튜닝 키 하나다.
2. **RM_C10490 최소 요청 360 veh/h**: 설치된 모형에서 10490 의 서비스표는 lane plant 가 실측 헤드 곡선으로 바꾼다(녹색 2 = 1.0 대/주기 = 360 veh/h, `lane_plant_runtime.py:482-486`) [읽음]. 첫 재생이 `configure` 검사에서 255.6 < 360 으로 거부됐다 [실행]. “표[2]” 규칙 그대로 360 을 쓴다(생성기가 튜닝의 곡선에서 계산).
3. 스칼라 QP 고정 좌표 처리(§1.2 `solve_qp`)는 설계에 없던 수정이다.

### 1.4 튜닝 `config_n31_v2_hybrid_carlson_alinea.json` (sha256 0b5a91ef…) = 기본 + 세 가지 [실행]
- `adapter.sdmpc_freeway_rule` (스키마 `sdmpc-freeway-rule/v1`)
  - MTFC: FW_E, 적용 머리 10(표지판 셀 10 = S4, DSD 59–62), 가속 머리 12(셀 13 = S5, DSD 63–66, 110 고정), 측정 910085–910087(RM_C10484 합류 끝 +50 m), 목표 18.5 %, K_P 0.0133, K_I 0.0813 /%p(**잠정**), 단계 {80,90,100,110}, ≤20 km/h.
  - ALINEA 목표 %: 10480/10482/10646/10644 **18.0**(식별 불가, 선언 대체값), 10639 **10.5**(쌍봉, 선언값), 10681 **17.5**, 10490 **19.5**, 10484 **18.5**. 이득 70 veh/h/%×차로(10482·10681 = 140). 요청 범위 표[2]..표[10] (10490 은 360..1512).
- `freeway.vsl_zone_heads.FW_E = [0, 5, 10, 12, 15]`
- `_n31_hybrid_note`
- 도시 부분은 `config_n31_v2.json` 과 완전히 같다(시험이 확인).

---

## 2. 시험

### 2.1 단위 시험 `diagnostics/sdmpc_n31_20260924/tests/test_n31_hybrid_rule.py` — 21개 통과 [실행]
- Carlson(8): 첫 결정 P=0, 일정 초과에서 적분 누적(단계당 K_I·Δo), P 항 반응, 위·아래 anti-windup(1 과 80/110 에서 잘림, 저장된 초과 없음), 양자화(동률 위), 속도 제한(110→90, 80→100), 활성화(18.9 % 에서 110→100…), 잘못된 입력 거부.
- ALINEA(1): 이득·목표·요청 범위·±2 s 상자·anti-windup.
- 관측(2): 측정 번호로만 선택(같은 이름 상류 묶음 60 % 섞인 집계 40 % 는 무시), 창 불일치·미완료·누락·중복 거부.
- 배선(4): 첫 결정 명령행(머리 10만 v, 나머지 110), `apply`(셀 10–11 = 90, 12–14 = 110, 링크 키 = 최소, 미터 서비스), `verify_applied` 가 VSL·미터 변경 검출, ±2 초과 녹색 거부, 이력은 영수증·시각·적용값·섹션 sha 가 맞을 때만, 실제 매핑의 표지판 배치.
- 설정(4): 스키마 거부 8종, 설치 모형 대조(가속 구역 free 거부, 단계 누락, 미터 집합, 서비스 범위, **10490 의 255.6 거부**), 생성 튜닝 = 기본 + 키, 측정 번호가 망의 합류 끝 묶음·같은 이름 상류 묶음 존재.
- QP(1): 모든 좌표 고정 → 경계점·성공, 행 위반이면 실패, 하나라도 자유면 SLSQP 그대로.
- 폭-0 축(1, 저장된 900 s tangent 요청의 실제 17+2 소유자): 규칙이 있으면 3블록 전부 미터·VSL 폭 0, 신호·offset 은 폭 유지, encode/decode 왕복, 1블록 좌표는 상자 밖 규칙 녹색 거부.
- 기존 시험 회귀 [실행]: `diagnostics.test_sdmpc_sequence`, `test_joint_owner_addresses`, `test_joint_neighbor_callbacks`, `tests.test_diagnostic_rule_profile`, `test_sdmpc_qp_fallback`, `test_n31_generators` 모두 통과(건너뜀 2 는 기존: 입력 존재·N31_SLOW).
- 감시자 함수는 스크립트를 돌리지 않고 AST 에서 `Read-SdmpcFreewayRuleDeclared` 만 꺼내 평가: 기본 False, 하이브리드 True, urban_b1 False [실행].

### 2.2 오프라인 재생 (한 번에 하나, BELOW_NORMAL, PYTHONHASHSEED=0, NUMBA_CACHE_DIR=…/nbc_hyb) — 폴더 `D:/VISSIM_runs/20260929_hybrid_offline/`
| 재생 | 결과 |
|---|---|
| `base_wu_900` (9ed2ef0 별도 워크트리 `sim3-n31-hybrid-base`, 기본 튜닝, wu-link) | 목표 348.3666786204171 / held 351.261489741853, 613 s |
| `new_wu_900` (새 코드 커밋 전) · `new_wu_900_final` (커밋 43150c8) | 둘 다 base 와 **IDENTICAL**: CSV 바이트, 제어 필드, diagnostics, 목표 repr, 선택 후보·trial rows·좌표·가격 상태·최종 제약, derived [실행] |
| `nc_default_{1,150,750,900,2700,4500,6300,9000}` (표준 `replay_decision_n31.ps1`, no-control) | 8/8 **IDENTICAL**(기록된 R-obs 결정 대비) [실행] |
| `nc_hybridtuning_{1,150,750}` (하이브리드 튜닝, no-control) | CSV·제어·diagnostics 가 R-obs 와 **동일** → 워밍업 짝 유지 [실행] |

하이브리드 재생(하이브리드 튜닝, wu-link) — `rule_observation` 은 R-obs `.mer` 의 정확한 차로별 시간점유율(합류 끝 묶음, 창 (T−150, T])로 만들고, 같은 이름 상류 묶음에는 표시된 합성값(3배)을 넣었다. 2700/4500/6300 은 직전 no-control 행동 사본에 합성 이력과 `.applied` 영수증을 붙였다(`hybrid_inputs.json` 에 기록) [실행].

| T | 이력 | o_10484 | b(k−1)→b | v*→v | 미터(녹색≠10) | SDMPC held→선택 (veh·h) | 벽시계 | 판정 |
|---|---|---|---|---|---|---|---|---|
| 900 | 첫 결정(워밍업 뒤) | 9.90 | 1→1 | 110→110 | 없음 | 354.93→348.37 | 538 s | PASS |
| 2700 | b 0.80, o 20.7 | 19.19 | 0.80→0.764 | 80→**90**(제한) | 10639=8, 10490=9 | 513.55→507.38 | 445 s | PASS |
| 4500 | b 0.95, o 19.2 | 18.72 | 0.95→0.939 | 100→**100** | 10639=8, 10490=8 | 475.87→470.00 | 618 s | PASS |
| 6300 | b 1.0, o 9.5 | 11.76 | 1→1 | 110→110 | 10639=8 | 384.69→379.84 | 603 s | PASS |

PASS 의 내용(`check_hybrid_replay.py`, 결과 `hyb_T/hybrid_check.json`):
- CSV VSL 66행이 runner config 의 VBS 행 계약(`VslActionKeyValid`·`IsCsvFiniteNumber` 를 파이썬으로 재현: 키 66개, DSD, 허용 속도 80..110)을 통과
- DSD 59–62 = MTFC 속도, 나머지 62행 = 110. 미터 8행 = ALINEA 녹색, 직전 적용 녹색 ±2 안
- 신호 17개 SC 행 있음. SDMPC 완료, 좌표의 미터·VSL `allowed` 크기 전부 1, `.joint_written.json`(verify_joint_written_action) 있음
- `python_hash_seed == "0"`
- 900 은 규칙 명령이 hold 와 같아 선택 행동이 기본 SDMPC 900 과 녹색·offset·미터·VSL 모두 같았다(선택 목표 348.3666786204171 동일) [실행].
- 결정론(H5): `hyb_2700_r2` = 같은 입력 재실행 → §2.3 (수치 동일).

### 2.3 결정론 (H5) [실행]
- `hyb_2700_r2` = 같은 R-obs 상태·같은 관측·같은 합성 이력(폴더만 다름)을 커밋 43150c8 로 다시 돌렸다(439 s).
- 같음: CSV 바이트, 제어 필드, 목표 repr(507.3811005511224 / 509.0435631413314), local rows, gradient rows, 후보, 좌표, 가격 상태, 최종 제약, derived, `hybrid_rule`(영수증 sha 제외).
- 다름: 직전 CSV 경로 문자열(합성 폴더 이름)과 그것을 담은 해시(`action_token`, 영수증 sha), 벽시계 초. 경로를 정규화하면 diagnostics 도 같다.
- 판정: PYTHONHASHSEED=0 에서 수치는 결정적이다. (PYTHONHASHSEED 를 바꾼 대조는 하지 않았다.)

---

## 3. VSL < 110 쓰기 경로
- 오프라인: 2700(90)·4500(100)에서 어댑터 → CSV → VBS 행 계약까지 통과 [실행].
- 망: 희망속도 분포 80/90/100/110 이 v3c1 망에 있고, DSD 59–62 는 link 2 @2652.0 m(S4), 63–66 은 @3998.7 m(S5) [실행].
- VBS 쓰기(읽음): 행 검증 `:1341-1343`, 적용 `SetClassSpeedChecked` 로 클래스 10/20/30/70 에 분포 번호 = 속도를 쓰고 되읽기, 실패면 fail-closed(`:1450-1463`). v3b S0e 에서 80/90/100 되읽기 16,104행 실패 0(설계서 §2) [읽음].
- 라이브 확인은 런에서만(§8 H6).

---

## 4. PYTHONHASHSEED 상속 [읽음]
- `run_sdmpc_n31.ps1` 는 RW_* 만 지우고 PYTHONPATH/스레드/PYTHONUTF8 만 세운다. `& powershell` 로 감시자를 부른다 → 상속.
- 감시자는 RW_* 와 PATH 만 만지고 `Start-Process cscript -RedirectStandardOutput`(UseShellExecute=false, 현재 환경 복사) → 상속.
- VBS 는 `shell.Exec` 로 python → 상속. VBS 가 환경을 쓰는 곳은 읽기(`:711`, `:722`, `:5107`)뿐.
- 어댑터 자식: `sdmpc_tangent.py:58`·`sdmpc_tangent_concurrent.py:52` 는 `dict(os.environ, …)`, 응답 풀은 `spawn` → 상속.
- **WMI `Win32_Process.Create` 는 호출자 환경을 넘기지 않는다** [추론: Windows 동작] → 명령줄에서 세운다. `cmd` 에서는 `set "PYTHONHASHSEED=0"` 따옴표 형식이어야 뒤 공백이 값에 안 붙는다(`set X=0 &&` 는 값이 "0 " 가 되어 Python 이 거부할 수 있다) [추론].
- 런 중 확인: 각 결정 `metadata.hybrid_rule.python_hash_seed`(provenance env 는 RW_* 만 기록).

---

## 5. 발사 명령 (사용자가 실행; 나는 띄우지 않았다)

좌석 규칙: 전체 VISSIM ≤ 3 이고 dev(VISSIM 제목에 obs150|sdmpc|probe) 0. dev 가 1개 돌고 있으면 `-AllowConcurrentDev`(전체 ≤ 2) 를 붙이거나 `-WaitSeatMinutes N`.

```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = 'cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2_hybrid_carlson_alinea.json -Name sdmpc31_v3c1_hybrid_s31 -SimPeriod 9000 -Seed 31 -Controller wu-link -RunsRoot D:\VISSIM_runs\20260929_hybrid > D:\VISSIM_runs\20260929_hybrid\wmi_sdmpc31_v3c1_hybrid_s31.log 2>&1'
  CurrentDirectory = 'D:\VISSIM-merge\frozen\sdmpc31_43150c8e_202609291223'
}
```
- 사전점검 계획: `D:\VISSIM_runs\20260929_hybrid\_preflight\sdmpc31_v3c1_hybrid_s31_20260929_122735\` (이름 `sdmpc31_v3c1_hybrid_s31` 은 아직 미점유).
- 예상 벽시계: 하이브리드 결정 445–618 s × 55 ≈ 7–9.5 h + 워밍업. 결정당 코어 약 9–16개.

---

## 6. 사용자 결정이 아직 열려 있는 것 (설계서 §12, 선언 기본값으로 빌드함)
1. **Carlson 이득**: 잠정값(K_P 0.0133, K_I 0.0813 /%p). 원문 미확인.
2. **10639 목표 10.5 %**: 재생 세 상태 모두 녹색 8(점유율 21–25 %). 폐루프에서는 결정마다 2 s 씩 녹색 2 까지 내려갈 가능성이 높다(open-loop 65–83 %). 램프 대기가 도시 쪽으로 역류할 위험. 25.5 또는 “열어 두기”로 바꾸려면 튜닝의 `alinea.meters.RM_C10639.target_occupancy_pct` 만 바꾸고 재동결.
3. MTFC 목표 단위 18.5 % (대안 14.7 %), B2 이중 적분(독립 운용; split-range 아님).
4. 위 어느 것을 바꿔도 코드 변경 없이 생성기 상수 → `--hybrid-rule` → 커밋 → `-Freeze` 로 새 FRZ.

---

## 7. 위험 / 미검증
- **R-VBS**: 새 VBS 분기는 라이브에서만 검증된다. `RuleObservationJson` 은 차량 0대 창에서 `OccupRate` 가 비면 `Err.Raise` 로 런을 멈춘다(속도만 빈값 처리). 900 s 이후 합류 끝 측정소는 교통이 있어 가능성은 낮다 [추론]. 실패하면 t=900 결정이 “observation missing” 으로 멈춘다(fail-closed).
- **R-관측 합성**: 오프라인 `rule_observation` 은 `.mer` 정확값으로 만들었지만 VISSIM COM `OccupRate` 그 자체는 아니다(설계 보정에서 .mer ↔ 공간점유 RMSE 0.4 %p).
- **R-이력 합성**: 2700/4500/6300 의 이력은 합성이다(직전 실제 행동은 no-control). 영수증 형식은 `sdmpc.load_prices` 와 같은 3줄 UTF-16 을 가정 [읽음].
- **R-예측 ZOH**: SDMPC 는 450 s 동안 고속도로 명령 고정을 가정한다. 규칙은 다음 결정에서 바뀔 수 있다.
- **R-큐 override 없음**, **R-MTFC 권한 작음**(설계서 R1): 그대로.
- **R-결정 시간**: 하이브리드 결정 445–618 s, 기본 540–613 s. `ignore_wall_time_limits` true, StallSec 2400.
- 설계서 §11 R1–R13 은 그대로 유효.

---

## 8. 발사 뒤 조기 확인 (런 폴더 읽기만)
- `decisions_*/state_000150.json`…`state_000750.json` 에 `rule_observation` **없음**(게이트가 제어 시작부터).
- `state_000900.json` 에 `rule_observation.completed_interval_available=true`, `window_start_sec=750`, `ramps.RM_C10484.lane_measurements` 에 910085–910087 행.
- `action_000900.json` `metadata.hybrid_rule`: `history_source.source=first_decision`, `python_hash_seed="0"`, `mtfc_vsl.speed_kph`, 미터 녹색. `action_001050.json` 의 `history_source` 가 900 의 `.applied` 영수증.
- `vsl_readback.csv` 에 110 미만이 나오면 DSD 59–62 만, 되읽기 실패 0.
- 900.1 s 까지 FZP 프레임이 R-obs(`sdmpc31_v3c1_nc_s31`)와 같은지(짝 유효성).

---

## 9. 파일
- 코드(커밋 43150c8): `evaluation/controllers/freeway_rule_hybrid.py`, `sdmpc.py`, `joint_owner_game.py`, `vissim_stackelberg_adapter.py`, `scripts/run_real_world_stackelberg_controller.vbs`, `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`, `diagnostics/sdmpc_n31_20260924/make_config_n31.py`, `…/config_n31_v2_hybrid_carlson_alinea.json`, `…/tests/test_n31_hybrid_rule.py`
- 오프라인 도구(스크래치, 미커밋): `hybrid/tools/{run_replay.py, make_hybrid_inputs.py, check_hybrid_replay.py, compare_replays.py, lowprio.py, hybrid_replays.sh, nc_identity.sh, postcommit.sh}`
- 재생 산출: `D:/VISSIM_runs/20260929_hybrid_offline/` (`_failed_scipy_nit_hyb_2700`, `_stale_*` 는 수정 전 실패/폐기 입력 기록)
- 기준 워크트리 `D:/VISSIM-merge/sim3-n31-hybrid-base`(9ed2ef0 detached, 기준 재생용, 내가 만든 것)
- 사전점검 로그: `hybrid/preflight_freeze.log`


---

## 10. 검증자 차단 1건 처리 — RM_C10639 ALINEA 목표 (2026-09-29 오후, 커밋 d34fd1a)

### 10.1 판정: 실재한다 [실행]
- `calib/critical_estimates.json` 의 10639 칸을 직접 봤다. 창 ≥ 8 인 칸은 4.5–10.5 와 21.5–28.5 두 무리뿐이고 11.5–20.5 는 비어 있다.
- v1 추정량(`calib/estimate_critical.py:59-74` `o1`, 이웃 평균 :71-73)은 남아 있는 이웃만으로 평균을 낸다. 그래서 빈칸 바로 아래 칸 10.5 는 (9.5, 10.5) 두 칸 평균 7,137.9 를 받아 argmax 가 됐다. 흐름이 떨어지는 쪽(11.5 이상)을 한 칸도 보지 못한 자리다. 선언 규칙의 "최상위 칸이면 미식별" 검사(`:124`)는 전체 최상위 칸(28.5)만 봐서 이 경우를 놓쳤다.
- 검증자의 수치(빈 구간, 평활 전 q90 최대 24.5 칸 7,249, v1 시드별 21.5–27.5, s31 .mer 25.5, open-loop s31 녹색 2 가 35/54 창)는 모두 같은 파일에서 그대로 확인된다.
- 코드 결함은 아니다. 규칙 층은 튜닝의 숫자를 그대로 쓴다. 고칠 것은 보정 추정량과 그 출력인 튜닝 상수다.

### 10.2 수정: 선언 변경 2 (v1 결과를 본 뒤의 사후 변경이라고 적어 둔다)
- 규칙: 3칸 이동평균과 argmax 는 **양옆 칸이 모두 남아 있는 칸에서만** 정의한다(끝 칸, 빈칸 옆 칸은 후보가 아니다). 자료·구간 점유율·q90·칸당 창 수(합동 8 / 시드별 3)·부트스트랩 씨앗·식별 규칙·대체값 규칙은 v1 그대로다.
- 구현: `hybrid/calib_v2/estimate_critical_v2.py` (sha 4bedfa45). v1 모듈을 import 하고 `o1` 만 바꾼다. 입력은 v1 과 같은 `calib/windows_s*.json`, `calib/mer_s31_robs.json` 이다. 결과는 `calib_v2/critical_estimates_v2.json` (sha b1138233) [실행]

| 미터 | 식별 | O1 v1 → v2 | 부트스트랩 5–95 (v2) | 시드별 O1 (v2) | **튜닝 목표 v1 → v2** |
|---|---|---|---|---|---|
| RM_C10480 | 아니오 | 5.5 → 4.5 | 4.5–5.5 | 4.5 ×5 | 18.0 → **19.0** (대체값) |
| RM_C10482 | 아니오 | 8.5 → 7.5 | 7.5–7.5 | 6.5–7.5 | 18.0 → **19.0** |
| RM_C10646 | 아니오 | 5.5 → 4.5 | 3.5–4.5 | 3.5–4.5 | 18.0 → **19.0** |
| RM_C10644 | 아니오 | 5.5 → 4.5 | 4.5–4.5 | 3.5–4.5 | 18.0 → **19.0** |
| **RM_C10639** | 예(쌍봉) | **10.5 → 23.5** | 9.5–25.5 | 23.5 / 9.5 / 24.5 / 26.5 / 25.5 | **10.5 → 23.5** |
| RM_C10681 | 예 | 17.5 → 17.5 | 16.5–18.5 | 15.5–17.5 | 17.5 (그대로) |
| RM_C10490 | 예 | 19.5 → 19.5 | 16.5–19.5 | 8.5–14.5 | 19.5 (그대로) |
| RM_C10484 | 예 | 18.5 → 18.5 | 14.5–18.5 | 7.5–19.5 | 18.5 (그대로, MTFC 목표도 18.5) |
| B2 밀도(참고) | 예 | 31 → 29 veh/km/차로 | 25–29 | 21–27 | MTFC 대안 표기만 14.7 → 14.0 % |

- 대체값(식별된 넷의 O1 중앙값)이 10639 가 10.5 → 23.5 로 바뀌면서 18.0 → 19.0 이 됐다. FW_W 네 곳은 NC 최대 점유율이 6.3–18.1 % 라 18.0 이든 19.0 이든 open-loop 에서 한 번도 미터링하지 않는다 [실행]. 규칙 출력을 일관되게 쓰려고 함께 바꿨다.
- s31 .mer 정확값(시드 하나, 창 ≥ 3)은 v2 에서 10639 22.5, 구간 추정 23.5 다. v1 의 25.5 는 v2 에서 재현되지 않는다.

### 10.3 10639 는 여전히 쌍봉이다 — 무엇이 측정됐고 무엇이 안 됐나 [실행]
- v2 argmax 23.5(7,084.5)와 자유류 무리의 최고 후보 9.5(7,082.2)의 차이는 2.3 veh/h(0.03 %)다. 부트스트랩도 9.5–25.5 로 두 무리를 오간다.
- 두 무리의 유량은 같다: 8–11 % 무리 중앙 6,679 veh/h (속도 중앙 88 km/h, 혼잡 0 %), 21–29 % 무리 중앙 6,694 veh/h (속도 중앙 33 km/h, 전부 v < 60).
- 측정소는 B1(10681 합류) 293 m 상류다(설계서 §7.2 [읽음]). 위 무리는 이 측정소 자체의 임계가 아니라 B1 대기열에 잠긴 상태다. 따라서 "이 합류의 FD 임계점유율"은 NC 자료로 식별되지 않는다. 식별되는 것은 "용량 유량이 9.5–25.5 % 전 범위에서 유지된다"는 것뿐이다.
- 23.5 는 사용자가 정한 방식(5개 fit 시드 합동 O1)의 **수정된 추정량이 낸 값**이다. 손으로 고른 값이 아니다. 같은 유량 평탄부 안에서 위쪽 끝에 가깝다. 그래서 B1 대기열이 23.5 % 를 넘을 때만 조인다.

### 10.4 open-loop 결과 (NC 점유율 궤적, 피드백 없음, `calib_v2/openloop_v2.py`) [실행]
10639 목표별 비교. 칸 안은 녹색 < 10 비율 / 녹색 2 비율 / 평균 서비스 veh/h.

| 목표 | s31 | s41 | s43 | s47 | s53 |
|---|---|---|---|---|---|
| 10.5 (v1) | 0.80 / 0.65 / 584 | 0.65 / 0.41 / 827 | 0.83 / 0.63 / 615 | 0.76 / 0.65 / 623 | 0.80 / 0.65 / 605 |
| 18.5 (미식별이면 대체값) | 0.76 / 0.50 / 698 | 0.50 / 0.22 / 1,056 | 0.72 / 0.37 / 760 | 0.72 / 0.54 / 680 | 0.70 / 0.56 / 724 |
| **23.5 (v2, 채택)** | **0.61 / 0.26 / 927** | 0.30 / 0.06 / 1,323 | 0.28 / 0.07 / 1,280 | 0.69 / 0.37 / 806 | 0.65 / 0.52 / 780 |
| 25.5 | 0.46 / 0.00 / 1,289 | 0.11 / 0.00 / 1,471 | 0.20 / 0.00 / 1,442 | 0.57 / 0.13 / 1,061 | 0.65 / 0.24 / 865 |

- s31 기준으로 녹색 2 창은 35 → 14 개(54 개 중)로 줄었다. **그러나 0 은 아니다.** 검증자가 걱정한 램프 대기 역류 위험은 줄었을 뿐 없어지지 않았다. B1 대기열 안의 측정소에 반응하는 ALINEA 의 성질이다(설계서 R2).
- 다른 미터(10681·10490·10484)의 목표는 그대로라 open-loop 도 그대로다.

### 10.5 검증자 제안과 다르게 한 부분, 그리고 그 이유
- **"사용자가 10.5 / 25.5 / 10639 제외 중 하나를 정해야 한다" → 대신 23.5 로 고쳤다.**
  - 사용자 지시 (2)는 "목표 = v3c1 NC 5 fit 시드에서 측정한 합류별 임계점유율"이다.
  - 10.5 는 측정값이 아니라 추정량의 결함이라서 지시와 어긋난다. 그래서 고쳤다.
  - 25.5 는 v1 추정량으로 시드 하나(s31 .mer)만 본 값이다. v2 에서는 22.5 다. 5시드 합동이라는 지시와도 맞지 않는다.
  - "제외"는 "8개 미터 모두 ALINEA"라는 지시와 어긋난다. 현재 코드에는 미터 하나를 개방으로 두는 설정도 없다. 목표 100 % 로 흉내 낼 수는 있지만 그런 우회는 하지 않았다.
  - 다만 23.5 도 쌍봉 가운데 하나를 고른 값이다(§10.3). **사용자가 원하면** 다른 값으로 바꿀 수 있다: `make_config_n31.py` 의 `HYBRID_METER_ROWS['RM_C10639']` 한 줄 → `--hybrid-rule` → 커밋 → `-Freeze`. 코드 변경은 필요 없다.
- 대안 튜닝 파일을 여러 벌 만들어 두지는 않았다. v1 의 10.5 는 결함이 있는 추정량의 값이라 승격된 선택지로 남기지 않는다("승격하면 구버전은 격리" 원칙).

### 10.6 바뀐 파일과 비트 동일성 [실행]
- 커밋 **d34fd1a** (Ming2you, 로컬만, 명시 경로 2개): `diagnostics/sdmpc_n31_20260924/make_config_n31.py`(상수·주석), `…/config_n31_v2_hybrid_carlson_alinea.json`(생성물, sha256 9a55778f…).
- JSON 수준 차이: `adapter.sdmpc_freeway_rule.alinea.meters.*.target_occupancy_pct` 5개(18.0→19.0 ×4, 10.5→23.5), 같은 섹션의 notes 뿐. "하이브리드 − 키 = 기본 튜닝" 이 성립한다.
- 생성기 `--hybrid-rule --check`, 기본 `--check` (sha 33027258… 불변), `--urban-batch1 --check` 모두 통과.
- 코드 경로는 바뀌지 않았다. 따라서 §2.2 의 "키 없으면 비트 동일" 재생(9ed2ef0 대비 IDENTICAL, no-control 8상태 IDENTICAL)은 그대로 유효하다. 튜닝 파일이 바뀌었으니 하이브리드 튜닝의 no-control 750 재생만 다시 돌렸다(§10.7).

### 10.7 다시 돌린 시험·재생 (한 번에 하나, BELOW_NORMAL, PYTHONHASHSEED=0, NUMBA_CACHE_DIR=…/nbc_hyb) [실행]
- 단위 시험: `test_n31_hybrid_rule`(21) + `test_n31_generators` + `test_sdmpc_qp_fallback` 45개 OK(건너뜀 2 는 기존), `diagnostics.test_sdmpc_sequence`·`test_joint_owner_addresses`·`test_joint_neighbor_callbacks`·`tests.test_diagnostic_rule_profile` 50개 OK. 시험 코드에는 미터 목표가 박혀 있지 않아 고칠 것이 없었다(생성 튜닝 = 기본 + 키 시험이 새 튜닝으로 통과).
- 하이브리드 결정 재생 `hyb2_6300` (커밋 d34fd1a 의 튜닝, R-obs 6300 상태 + .mer 정확 관측, 합성 이력 b 1.0 / o 9.5, 새 섹션 sha eb33b0a5 로 다시 만든 `.applied` 영수증): **PASS** (`check_hybrid_replay.py`: VBS 행 계약, DSD 59–62 = 110, 미터 행 = 규칙, 요청 범위, 신호 17개, SDMPC 완료, 폭-0 축, joint_written 영수증, python_hash_seed "0"). 벽시계 661 s.
  - 10639: o 25.23 %, 목표 23.5 → 요청 1,391.1 veh/h → **녹색 9** (v1 목표 10.5 에서는 같은 상태가 녹색 8). 순수 ALINEA 계산으로 미리 낸 값과 같다. 같은 계산으로 900/2700/4500 은 10/10/10 (v1: 10/8/8).
  - SDMPC held → 선택 384.69 → 379.87 veh·h (v1 재생 384.69 → 379.84).
  - 주석 문구(거리 343 → 293 m)를 고치기 전에 띄운 첫 시도는 내가 중단했다(`_stale_hyb2_6300_note343`, 결과 없음).
- no-control 재생 `nc2_hybridtuning_750` (새 하이브리드 튜닝, 워밍업 마지막 결정): CSV 가 R-obs `action_000750.csv` 및 이전 `nc_hybridtuning_750` 과 **바이트 동일**, 제어 필드·diagnostics 동일, `hybrid_rule` 없음 → 900 s 까지 R-obs 와의 짝은 유지된다.
- 2700/4500/900 전체 재생과 결정론 재실행은 다시 돌리지 않았다. 코드 경로가 같고 바뀐 것은 한 미터의 목표 숫자뿐이라 기존 결과(§2.2–2.3)가 유효하다고 본다 [추론].

### 10.8 새 FRZ 와 사전점검 [실행]
- `run_sdmpc_n31.ps1 -Freeze -PreflightOnly` (워크트리에서, 로그 `hybrid/preflight_freeze_v2.log`): **EXIT 0**
  - FRZ **`D:\VISSIM-merge\frozen\sdmpc31_d34fd1aa_202609291357`**, FREEZE sha 82bd9a02…, 파일 10,313, head d34fd1a, status_entries 0, FREEZE_VERIFIED
  - LAUNCH_PLAN_OK, `RW_RULE_OBSERVATION=1 (adapter.sdmpc_freeway_rule)`, PROVENANCE_OK (run_id cd04adcb…), VISSIM 시작 없음
  - FRZ 안의 튜닝 sha256 9a55778f… = 워크트리, 목표 {10480/10482/10646/10644: 19.0, 10639: 23.5, 10681: 17.5, 10490: 19.5, 10484: 18.5}
  - 사전점검 계획: `D:\VISSIM_runs\20260929_hybrid\_preflight\sdmpc31_v3c1_hybrid_s31_20260929_140001\`. 런 이름 `sdmpc31_v3c1_hybrid_s31` 은 아직 미점유.
- **옛 FRZ `sdmpc31_43150c8e_202609291223` 는 폐기(10.5 목표)다. 그것으로 발사하지 마라.** `frozen/*` 는 건드리지 않는 규칙이라 지우지 않았다.

### 10.9 최종 발사 명령 (사용자가 실행; 나는 띄우지 않았다)
좌석 규칙은 §5 와 같다(전체 VISSIM ≤ 3, dev 0; dev 1 이면 `-AllowConcurrentDev` 또는 `-WaitSeatMinutes N`).
```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = 'cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2_hybrid_carlson_alinea.json -Name sdmpc31_v3c1_hybrid_s31 -SimPeriod 9000 -Seed 31 -Controller wu-link -RunsRoot D:\VISSIM_runs\20260929_hybrid > D:\VISSIM_runs\20260929_hybrid\wmi_sdmpc31_v3c1_hybrid_s31.log 2>&1'
  CurrentDirectory = 'D:\VISSIM-merge\frozen\sdmpc31_d34fd1aa_202609291357'
}
```
- 발사 뒤 조기 확인은 §8 그대로이고, 하나를 더 본다: `action_000900.json` `metadata.hybrid_rule.alinea.RM_C10639.target_occupancy_pct == 23.5`.

### 10.10 남은 것 (사용자 판단)
1. **10639 목표는 여전히 쌍봉 중 하나다.** 23.5 는 지시한 방식의 수정된 출력이지만, 9.5 와 유량 차이는 2.3 veh/h 에 불과하다. open-loop 로 보면 s31 에서 녹색 2 가 54 창 중 14 창이다(v1 은 35 창). 램프 대기가 도시로 역류할 위험은 줄었을 뿐 남아 있다. 더 약하게 미터링하려면 25.5(s31 녹색 2 가 0 창), 더 엄격하게 하려면 9.5/10.5 로 바꾸면 된다. 방법은 §10.5 한 줄 경로다.
2. §6 의 나머지 열린 결정은 그대로다: Carlson 이득은 잠정값이고, MTFC 목표 단위(18.5 %; 밀도 대안은 이제 ρ 29 → 14.0 %)와 B2 독립 운용도 선언 기본값이다.
3. 선언 변경 2 는 v1 결과를 본 뒤에 만든 사후 변경이다. 영향은 10639 목표 하나와 FW_W 대체값(실질 영향 없음)뿐이지만, 논문·보고에 쓸 때는 사후 변경이라고 적어야 한다.
4. 정리: 옛 FRZ `sdmpc31_43150c8e_202609291223`(약 2.1 GB), 기준 워크트리 `sim3-n31-hybrid-base`, 사전점검 폴더 두 개는 필요 없으면 사용자가 지우면 된다.


---

## 11. 시험 런 3000 s 정지 수정: 서비스가 같은 녹색 두 개 (2026-09-29 저녁, 커밋 92fa4b8)

태그는 앞과 같다. 줄 번호는 커밋 92fa4b8 기준이다. 스크래치 폴더는 `hybrid/fix_dup/`.

### 11.0 요약

| 항목 | 결과 |
|---|---|
| 원인 | RM_C10490 서비스표에서 녹색 2 와 3 이 둘 다 360 veh/h 다(헤드 곡선 1.0/1.0 대/주기). 공유 디코드 `physical_ramp_branches.py:349-361` 는 360 을 녹색 하나로 되돌리지 못한다 [읽음·실행] |
| 실제 실패 지점 | SDMPC 리더 씨앗 영역 `leader_seed_domain` (`physical_ramp_branches.py:365-408`). 직전 적용 녹색 5(2850 s)의 ±2 격자에 녹색 3 이 들어 있어서 죽었다. **규칙이 3000 s 에 무엇을 명령했든 죽는다** [읽음·실행] |
| 수정 | 키(`adapter.sdmpc_freeway_rule`) 아래에서만 두 곳을 고쳤다. ① 규칙 층은 서비스가 유일한 녹색만 명령한다. ② 리더 NP 영역은 디코드가 거부할 격자 씨앗만 뺀다. 공유 디코드는 그대로다 [실행] |
| 커밋 | **92fa4b8** (Ming2you, 명시 경로 3개, 로컬만, 푸시 없음) [실행] |
| 단위 시험 | 새 `SharedServiceTests` 11개. n31 묶음 56개 OK(건너뜀 2 는 기존), 루트 회귀 50개 OK. 변이 4종 모두 잡힘 [실행] |
| 3000 s 재생 (실제 2850 이력) | **PASS**. 10490 녹색 3 → **4**. 씨앗 1개(g3)만 빠짐. SDMPC 완료, held 524.53 → 선택 521.87, 벽시계 775 s [실행] |
| 2850 s 재재생 | 기록된 결정과 **IDENTICAL** (CSV 바이트, 제어, derived, 목표 repr, `hybrid_rule`, `sdmpc_state`) [실행] |
| 키 부재 900 s | 9ed2ef0 기준 `base_wu_900` 과 **IDENTICAL** (목표 348.3666786204171) [실행] |
| 실패 런 폴더 | 파일 598개의 이름·크기·수정시각이 전후 같다 [실행] |
| 새 FRZ | **`D:\VISSIM-merge\frozen\sdmpc31_92fa4b8e_202609291737`** (FREEZE sha a93b3562…, 파일 10,313, status_entries 0). `-PreflightOnly` **EXIT 0**, PROVENANCE_OK, VISSIM 시작 없음 [실행] |
| 결정 20개까지 TTT (NC 대비) | Ω TTT **−29.4 veh·h (−1.35 %)**, 전체 링크 +22.1 (+0.73 %), 전체+미삽입 −6.7 (−0.18 %). FW_E 본선은 +21.6 (+3.6 %) 나빠졌다. §11.6 [실행] |

### 11.1 실패 경로 [읽음·실행]
- 런 `sdmpc31_v3c1_hybrid_s31` 은 결정 20개를 적용했다: t=1…750 워밍업 6개, 900…2850 하이브리드 14개. 3000 s 결정에서 멈췄다(`action_003000.error.txt`).
- 10490 녹색 이력(`metadata.hybrid_rule`): 900–2250 은 10, 2400 은 8, 2550 은 6, 2700 은 6, 2850 은 5. 3000 에서 규칙은 3 을 냈다(점유율 27.6 %, 요청이 하한 360 에 잘림).
- 설치된 10490 표는 {0:0, 2:360, 3:360, 4:518.4, 5:680.4, 6:842.4, 7:1004.4, 8:1166.4, 9:1328.4, 10:1512} 이다. 나머지 미터 7개는 서비스가 모두 다르다(시험이 확인).
- 3000 s 진행 기록: `hybrid_rule_command` → PFO 2회 완료(376 s) → 리더 영역에서 예외.
  - SDMPC 좌표(`sdmpc.py:330-340`)는 녹색 축이라 규칙의 3 을 문제없이 썼다.
  - 서비스를 녹색으로 되돌리는 곳은 리더 씨앗뿐이다.
- `leader_seed_domain` 은 **직전 적용 행동**(2850: 10490=5)을 앵커로 쓴다.
  - `_physical_meter_points`(`joint_owner_neighbors.py:1079-1104`)가 그 ±2 격자(3..7)를 만든다.
  - 씨앗마다 `candidate_from_services` 로 녹색을 찾는다. 녹색 3 의 360 은 녹색 2 와도 같아서 거부된다.
- 그래서 **지시된 "규칙 층만 수정"으로는 부족하다**:
  1. 2850 의 명령 5 는 서비스가 유일해서 규칙만 고치면 바뀌지 않는다. 같은 시드로 다시 돌리면 2850 까지 같은 궤적이고, 3000 에서 같은 자리에서 죽는다 [추론: 2850 재재생 IDENTICAL, VISSIM 같은 시드 결정론].
  2. 실제 2850 이력(앵커 5)을 쓰는 3000 재생도 통과할 수 없다.
  - 단위 시험 `test_leader_lattice_drops_only_the_refused_seeds` 가 이 경로를 재현한다. 앵커 5·4 의 격자를 원래 디코드에 넣으면 실제 오류 문구가 그대로 나온다. 변이 "대체 경로 안 탐"도 시험 2개가 잡는다.
- **"그룹에서 가장 낮은 녹색(2)만 남긴다"는 안도 쓸 수 없다.**
  - 디코드는 값 360 에 대해 녹색 2 와 3 을 모두 찾는다. 그래서 2 도 거부한다(`test_only_rm_c10490_has_shared_greens_and_the_decode_refuses_both`).
  - 규칙이 2 를 명령하면 다음 결정에서 앵커 자체의 디코드(`joint_owner_neighbors.py:1087`)가 죽는다.
  - 공유 디코드를 바꾸지 않는 한 허용 집합에서 **2 와 3 을 둘 다 뺄 수밖에 없다.**
  - 물리적으로 둘은 같은 서비스라서, 잃는 것은 "1.0 대/주기" 한 단계다. 10490 의 최저 서비스는 360 에서 518.4 veh/h(녹색 4)로 올라간다.

### 11.2 수정 (키 아래에서만) [실행·읽음]
1. **규칙 층** `freeway_rule_hybrid.py`
   - `shared_service_greens`(:188) / `admissible_table`(:197): 허용 녹색은 표에서 서비스가 유일한 녹색이다. 10490 은 0, 4..10 이다. 같음 판정은 디코드와 같은 `==` 다.
   - `meter_step`(:349-384): 공유 ALINEA 산식 `alinea_meter_step` 을 허용 표로 부른다.
     - 선택 순서는 요청에 가장 가까운 서비스, 그다음 직전 녹색에 가까운 쪽, 그다음 높은 녹색이다. anti-windup 도 허용 범위로 자른다.
     - ±2 상자에 겹침 녹색이 없으면 선택지가 원래와 같다. 그래서 결과가 비트 단위로 같고 기록 키도 추가하지 않는다(시험이 4,000개 넘는 조합으로 확인).
     - 겹침 녹색이 상자에 있으면 `alinea.<미터>.shared_service_admissibility` 에 비제한 녹색·적분기, `substituted`, `integrator_changed` 를 적는다.
     - 직전 적용 녹색이 겹침 녹색이면 명확한 오류를 낸다.
   - `configure`(:176-178): 최대 서비스 녹색과 양의 서비스 하나 이상이 유일해야 한다. 설치된 표 8개는 통과한다.
   - 동률 처리: 지시문은 "동률이면 높은 녹색"이었다.
     - 허용 녹색끼리는 서비스가 모두 달라서, 동률은 요청이 두 서비스의 정확한 중점일 때만 생긴다.
     - 그때도 공유 산식 순서(직전 녹색에 가까운 쪽 → 높은 녹색)를 그대로 쓴다. 산식을 둘로 나누지 않으려고 이렇게 했다.
2. **SDMPC 리더 NP 영역** `leader_candidates`(:482-557). 호출은 `sdmpc.py:677-681, 698-704` 두 곳이고, `freeway_rule is None` 이면 원래 호출이다.
   - 적용 앵커의 ±2 격자에 겹침 녹색이 없으면 원래 `prepare_joint_leader_candidates` 를 같은 인자로 부른다.
   - 있으면 같은 선행 검사를 하고 `leader_seed_domain` 본문을 그대로 따른다. 다만 디코드가 거부할 씨앗만 뺀다(`drop_shared_service_points`, :466).
   - `sdmpc.solve` 가 이 영역에서 쓰는 것은 `np_values` 뿐이다(`sdmpc.py:705`). 하이브리드에서는 미터 축 폭이 0 이라, 격자 씨앗은 SDMPC 가 고르는 값이 아니다.
   - 기록은 `hybrid_rule.sdmpc_leader_seed_filter`(:550)에 남는다.
3. **정책 토큰은 건드리지 않았다.**
   - `sdmpc_options['freeway_rule']`(spec)는 `token(policy)` 에 들어간다. 그 값이 `sdmpc_state.policy_sha256` 로 저장되어 다음 결정에서 대조된다(`sdmpc.py:542, 988`).
   - spec 에 키를 더하면 실제 2850 이력의 가격 영수증과 어긋난다. 그래서 겹침 녹색은 매 결정 서비스표에서 계산한다.

### 11.3 시험 [실행]
- `SharedServiceTests`(`test_n31_hybrid_rule.py:509-`) 11개가 확인하는 것:
  - 겹침 녹색은 10490 의 [2, 3] 뿐이고, 디코드가 둘 다 거부한다.
  - 5 에서 요청 3 → 4 (실제 3000 s 수치, 적분기 360 → 518.4, 감사 기록).
  - 4 에서는 2·3 어느 쪽도 명령하지 않는다(→ 4).
  - ALINEA 가 원래 허용 녹색을 고르면 대체하지 않는다. 적분기 하한만 다를 수 있고, 그때 `integrator_changed` 를 기록한다.
  - 겹침 직전 녹색은 거부한다.
  - 허용된 모든 시작점 × 점유율 × 요청 조합에서 2·3 이 나오지 않는다.
  - 상자에 겹침이 없으면 원래 산식과 비트 동일하고 기록 키도 없다(미터 8개).
  - 이력 왕복: 대체 → 영수증 → 다음 결정이 읽는다.
  - `configure` 가 최대 서비스 녹색의 겹침을 거부한다.
  - 격자: 앵커 5 는 g3, 앵커 4 는 g3·g2 만 빠진다. 원래 디코드는 실제 오류를 낸다.
  - `leader_candidates` 는 겹침이 없으면 원래 함수를 그대로 부르고, 있으면 np_values 를 보존한 채 씨앗만 뺀다.
- 묶음 실행:
  - `test_n31_hybrid_rule`(32) + `test_n31_generators` + `test_sdmpc_qp_fallback` = 56개 OK (건너뜀 2 는 기존).
  - `diagnostics.test_sdmpc_sequence`·`test_joint_owner_addresses`·`test_joint_neighbor_callbacks`·`tests.test_diagnostic_rule_profile` = 50개 OK.
- 변이 검사(`fix_dup/mutants.py`, 메모리 안 패치만, 소스 수정 없음): 허용=전체 표 / 가장 낮은 녹색 유지 / 격자 필터 끔 / 대체 경로 안 탐. 4종 모두 시험 실패로 잡힌다.

### 11.4 오프라인 재생 (한 번에 하나, BELOW_NORMAL, PYTHONHASHSEED=0, NUMBA_CACHE_DIR=…/nbc_hyb) [실행]
- 재생 폴더는 `fix_dup/replays/`(C:)에 두었다. 실패 런 폴더와 볼륨이 달라서 `make_replay_state_v2.py prepare` 가 하드링크 대신 sha 확인 사본을 만들었다.
- 직전 행동은 영수증 계약 때문에 런 폴더에서 읽기만 했다. 전후 파일 목록(598개, 크기·수정시각)이 같다.

| 재생 | 입력 | 결과 |
|---|---|---|
| `r3000_fix` | 실패 런 `state_003000.json`(실측 `rule_observation`) + 실제 `action_002850.json`·`.applied` | **PASS** (`check_hybrid_replay.py`: VBS 행 계약, DSD 59–62 = 80, 미터 행 = 규칙, 신호 17, SDMPC 완료, 폭-0 축, joint_written, hash seed "0"). 규칙 기록이 실패 시도와 다른 곳은 10490 의 녹색 3→4, 적분기 360→518.4, 서비스 360→518.4 와 새 감사 키 2개뿐이다. `sdmpc_leader_seed_filter`: 앵커 5, 빠진 씨앗 `physical:RM_C10490:g3` 1개, 남은 씨앗 9×14, np_values 6개, 후보 756. held 524.53 → 선택 521.87 veh·h, 775 s |
| `r2850_fix` | 실패 런 `state_002850.json` + 실제 `action_002700.json` | 기록과 **IDENTICAL** (`make_replay_state_v2.py compare`: derived, CSV 바이트, 제어 필드, 목표 repr, 행 계약). 루트 경로(FRZ↔워크트리)를 정규화한 전체 JSON 차이는 56건이다. 비휘발 항목은 `sdmpc.py` 소스 sha, `workspace_git_commit`, state 경로뿐이고 나머지는 토큰과 초 단위 시간이다(`normcmp.json`). `hybrid_rule`·`sdmpc_state` 는 같다 |
| `r900_keyabsent` | R-obs 900 s, 기본 튜닝(키 없음), wu-link | 9ed2ef0 기준 `base_wu_900` 과 **IDENTICAL** (CSV, 제어, diagnostics, 목표 348.3666786204171 / 351.261489741853, 선택 후보·trial·좌표·가격·제약, derived) |

- 새 런은 같은 시드이고 2850 까지 코드 경로가 같다. 그래서 3000 s 전까지는 실패 런과 같은 궤적을 따르고, 3000 결정에서만 갈라질 것으로 본다(10490 = 4, 씨앗 필터 사용) [추론].

### 11.5 커밋·FRZ·발사 [실행]
- 커밋 **92fa4b8**, 브랜치 `claude/hybrid-rulefw-sdmpc-urban-20260929`.
  - 명시 경로 3개: `evaluation/controllers/freeway_rule_hybrid.py`, `evaluation/controllers/sdmpc.py`, `diagnostics/sdmpc_n31_20260924/tests/test_n31_hybrid_rule.py`.
  - 작성자·커미터는 Ming2you 다. `--renormalize` 와 푸시는 하지 않았다.
  - 튜닝은 바꾸지 않았다(sha 9a55778f…, 섹션 sha eb33b0a5… 그대로).
- `run_sdmpc_n31.ps1 -Freeze -PreflightOnly` (로그 `fix_dup/preflight_freeze_v3.log`): **EXIT 0**.
  - FRZ **`D:\VISSIM-merge\frozen\sdmpc31_92fa4b8e_202609291737`**, head 92fa4b8, FREEZE_VERIFIED.
  - LAUNCH_PLAN_OK, `RW_RULE_OBSERVATION=1`, PROVENANCE_OK (run_id 10872ffb…).
  - 사전점검 폴더는 `D:\VISSIM_runs\20260929_hybrid\_preflight\sdmpc31_v3c1_hybrid_s31b_20260929_174024\`.
  - FRZ 안의 `freeway_rule_hybrid.py`·`sdmpc.py` 는 HEAD 와 내용이 같다(줄끝 제외). 튜닝 sha 는 9a55778f 이다.
- **옛 FRZ `sdmpc31_d34fd1aa_202609291357` 로 다시 발사하지 마라.** 같은 시드면 3000 s 에서 또 멈춘다. `frozen/*` 불가침이라 지우지는 않았다.
- 발사 명령(사용자가 실행; 나는 띄우지 않았다). 좌석 규칙은 §5 와 같다. 로그 이름이 달라서 이전 WMI 로그를 덮어쓰지 않는다.

```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
  CommandLine = 'cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2_hybrid_carlson_alinea.json -Name sdmpc31_v3c1_hybrid_s31b -SimPeriod 9000 -Seed 31 -Controller wu-link -RunsRoot D:\VISSIM_runs\20260929_hybrid > D:\VISSIM_runs\20260929_hybrid\wmi_sdmpc31_v3c1_hybrid_s31b.log 2>&1'
  CurrentDirectory = 'D:\VISSIM-merge\frozen\sdmpc31_92fa4b8e_202609291737'
}
```

- 발사 뒤 확인(§8 에 더해서):
  - `action_003000.json` 의 `metadata.hybrid_rule.alinea.RM_C10490.green_sec == 4` 이고 `shared_service_admissibility.substituted == true` 여야 한다.
  - `hybrid_rule.sdmpc_leader_seed_filter.dropped_seeds` 는 g3 1개여야 한다.
  - 3000 전 결정들의 CSV 는 실패 런과 바이트가 같아야 한다(짝 확인).
- 예상 벽시계: 결정당 10–13 분(2850 기록 10 분, 3000 재생 13 분) × 55 ≈ 9–12 h + 워밍업 [추론].

### 11.6 결정 20개까지 TTT: no control 대비 (사용자 질문) [실행]
- 비교 대상: 실패 런(하이브리드) vs v3c1 NC s31. 같은 시드로 짝지은 비교다.
- 창:
  - 결정 20개 = t=1…750 워밍업 6개(무제어) + 900…2850 하이브리드 14개. 20번째(2850) 결정의 적용 구간은 2850–3000 이다. 하이브리드 FZP 는 2995.1 s 까지 있다.
  - 기존 `hybrid/ttt3000/ttt3000.json` 을 썼다. stage-1 표준 함수, 150 s 칸, 두 런 모두 온전한 칸(0–2850)만 쓴 결과다.
  - 같은 스캔의 5 s 프레임 계열로 0–2995 를 다시 적분했다(`fix_dup/ttt20.py` → `ttt20.json`). 0–2850 값은 칸 합계와 소수점까지 같다(교차 확인).
- 0–900 차이는 모든 지표에서 정확히 0 이다. 워밍업 짝이 유효하다는 뜻이다.

| 지표 (veh·h) | NC | 하이브리드 | 차이 | % |
|---|---|---|---|---|
| **M3 Ω TTT** (0–2850) | 2,182.90 | 2,153.47 | **−29.43** | **−1.35 %** |
| M3 Ω TTT (0–2995) | 2,336.54 | 2,306.82 | −29.72 | −1.27 % |
| M3u 도시 Ω (0–2850) | 850.69 | 828.04 | −22.64 | −2.66 % |
| M1 FW_E 본선 (0–2850) | 599.58 | 621.21 | **+21.63** | +3.61 % |
| M1 FW_E 본선 (0–2995) | 640.30 | 666.69 | +26.39 | +4.12 % |
| M2 동측 국소 19링크 (0–2850) | 677.18 | 689.76 | +12.58 | +1.86 % |
| 전체 링크 TTT (0–2850) | 3,034.19 | 3,056.31 | +22.12 | +0.73 % |
| 전체 링크 TTT (0–2995) | 3,244.07 | 3,275.61 | +31.55 | +0.97 % |
| 미삽입 지체 (0–2850) | 776.73 | 747.90 | −28.83 | −3.71 % |
| **M4 전체 + 미삽입** (0–2850) | 3,810.92 | 3,804.21 | **−6.71** | **−0.18 %** |
| (참고) off-ramp 영역 | 138.36 | 110.99 | −27.37 | |
| (참고) FW_W 본선 / on-ramp 영역 | 406.19 / 248.19 | 407.12 / 247.97 | +0.94 / −0.21 | |

- 결정 창별 차이(하이브리드 − NC, 각 [T, T+150), Ω / 전체 링크, veh·h):
  - 900 −0.9 / +0.2, 1050 +1.4 / +0.9, 1200 0.0 / +1.6, 1350 −1.7 / +0.6
  - 1500 −3.4 / −1.7, 1650 −1.7 / −1.1, 1800 −3.4 / −1.7, 1950 −5.3 / −1.6, 2100 −4.7 / −1.1
  - **2250 −4.5 / +3.3, 2400 −2.3 / +5.8, 2550 −1.4 / +8.7, 2700 −1.9 / +8.3, 2850 −0.3 / +9.4**
- 읽기:
  - Ω 는 1350 부터 꾸준히 낮다 [실행].
  - 2250 부터 전체 링크가 나빠진다. 그때부터 MTFC VSL 이 켜졌다(2250: 90, 2400: 100, 2550: 90, 2700·2850: 80 km/h). ALINEA 도 10490(10→5)·10639·10484 를 조이기 시작했다 [실행: `metadata.hybrid_rule`].
  - 같은 구간에 FW_E 본선이 +3.6 % 나빠졌다. 미삽입 지체가 줄어서 전체+미삽입(M4)은 −0.2 % 다. 망 전체 합계로는 거의 비겼다 [실행].
  - VSL·미터가 FW_E 본선 비용을 올렸고, 도시 Ω 가 그만큼 좋아진 모양이다. 도시 SDMPC 효과와 규칙 고속도로 효과는 이 자료로 나눌 수 없다 [추론].
- 한계: 시드 하나, 9,000 s 중 앞 3,000 s(하이브리드 결정 14개)뿐이다. 이 수치는 판정이 아니라 조기 관찰이다. 새 런 s31b 의 3000 s 이전 구간은 이 궤적과 같을 것으로 본다(§11.4) [추론].

### 11.7 남은 것
1. 10490 의 최저 서비스가 518.4 veh/h(녹색 4)로 올라갔다. 3000 s 상태에서 ALINEA 는 360 을 원했다. 램프 제어 권한이 한 단계 줄었다. 더 내리려면 공유 디코드를 바꾸거나(녹색 2 를 대표로), 10490 헤드 곡선에서 2·3 을 구분해야 한다. 둘 다 이번 범위 밖이다.
2. 리더 씨앗 필터는 3000 s 한 상태(앵커 5)에서만 재생으로 확인했다. 앵커 4(g2·g3 제외)는 단위 시험만 거쳤다.
3. §6·§10.10 의 열린 결정(Carlson 이득 잠정값, 10639 쌍봉 목표, MTFC 목표 단위)은 그대로다.
