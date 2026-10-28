# V-A 분석 방법 — 조작 정의 (보충 34 §8을 코드로 옮긴 것) — 2026-10-23, 첫 V-A 발사 전 고정

- 이 문서는 보충 34 §8(분석 방법)을 코드로 옮긴 **정의만** 적습니다. 새 규칙을 만들지 않습니다. 이 문서와 보충 34 §8이 다르면 §8이 이깁니다(§8.0-2).
- 고정 시점: **첫 V-A 발사 전**(보충 34 §6.1 발사 전제 (4), §8.0-2). 이 문서를 쓸 때 V-A 런은 없었고 V-A 자료는 0개입니다 [실행 RVA 목록: `_preflight` 폴더와 감시기 파일뿐].
- 고정: 이 문서와 도구 파일의 sha256을 `VA/analysis/va_analysis_pins.sha256`과 `VA/LOG.md`에 적습니다. 고정 뒤 고치면, V-A 출력을 보기 전이라도 새 고정·공개가 필요합니다. V-A 출력을 본 뒤 고치면 S-K12 꼴 STOP입니다(보충 34 §8.0-2, S-A34-7).
- 이 문서는 subagent의 Write 도구가 `.md` 쓰기를 막아 `AV/method_src.txt`로 쓴 뒤 바이트 그대로 `ANALYSIS_METHOD_VA.md`로 복사했습니다(J1 `ANALYSIS_METHOD.md` §5와 같은 방식; 내용 같음, sha는 복사본 기준).
- 표시: [실행] 이번에 돌려서 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단.
- 판정 말은 쓰지 않습니다. 이 문서의 숫자는 모두 J1·NC3 자료(이미 공개된 숫자)입니다.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`. AV = `VA/analysis`(이 문서 폴더). REPVA = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`.
- RVA = V-A 런 폴더 `D:/VISSIM_runs/20261023_sdmpc31_k92`. RR = J1 런 폴더 `D:/VISSIM_runs/20261004_sdmpc31_k8`. NC3 = 같은 시드 무제어 v3c3 런 `D:/VISSIM_runs/20261001_v3c3/s<S>_v3c3nc/run`.
- V-A = 묶음 B1(W·H-b)을 배포한 폐루프 VISSIM 3시드 런. J1 = K8 동결본 폐루프 3시드 런.
- Ω(오메가) = 제어 영역 635링크 총 통행시간(veh·h). ①–④ = K8 §5.5 네 지표. Ω 밖 = ④ − ③ 쪽.
- 미삽입 = 입력에서 생겼지만 망에 못 들어간 차량의 대기(재구성). U6(V-A)·U9·U6(J1) = 미삽입 합집합(§3).
- FZP = VISSIM 차량 궤적 파일(5 s 프레임). `.err` = 런 끝 오류 파일(remain, 차로변경 제거).
- 짝 A = V-A − NC3. 짝 B = V-A − J1. 짝 B′ = J1 − NC3를 U9로 다시 낸 것. J1R = J1 − NC3를 U6(J1)로 낸 "J1 보고 값".
- 시드는 망 접두어를 붙여 v3c3-s31처럼 적습니다.

## 1. 대상과 입력 (보충 34 §8.1)

| 시드 | V-A 런 (RVA) | J1 런 (RR) | NC3 |
|---|---|---|---|
| v3c3-s31 | `sdmpc31_v3c3_k92va_s31` | `sdmpc31_v3c3_k8j1r_s31`(재실행) | `s31_v3c3nc/run` |
| v3c3-s41 | `sdmpc31_v3c3_k92va_s41` | `sdmpc31_v3c3_k8j1_s41` | `s41_v3c3nc/run` |
| v3c3-s43 | `sdmpc31_v3c3_k92va_s43` | `sdmpc31_v3c3_k8j1_s43` | `s43_v3c3nc/run` |

- 러너 런(V-A·J1) 입력: `vissim_eval/sdmpc31_<런>_001.fzp`(0.10 s 행은 읽기 심으로 건너뜀, 자르기 없음), `network/sdmpc31_<런>_001.err`, `network/sdmpc31_<런>.inpx`, `decisions_<런>/action_<T6>.json`(61개)·`obs150/err_<T>.jsonl`, `runlog_<런>.txt`, `launch_<런>.log`, `action_<런>.csv`.
- NC3 입력: `run/vissim_eval/baseline_s<S>_v3c3nc_001.fzp`, `run/baseline_s<S>_v3c3nc_001.err`.
- J1·NC3 스캔은 `SP/j1/analysis/scans/<tag>/`를 sha256 앞 16자 확인 뒤 다시 씁니다(보충 34 §8.1 표 값). 다르면 같은 도구로 다시 스캔하고 공개합니다(`va_scan.py`가 자동으로 함). V-A 세 런만 새로 스캔합니다 [실행 2026-10-23: 여섯 스캔 sha16 모두 §8.1 값과 같음].
- 원래 v3c3-s31 J1 런(`sdmpc31_v3c3_k8j1_s31`, 무효)은 쓰지 않습니다.

## 2. 도구와 순서

| 순서 | 파일 (`AV/tools/`) | 하는 일 | 출력 (`AV/out/`) |
|---|---|---|---|
| 0 | `va_provenance.py` | 입력 해시만(값 읽지 않음) | `va_provenance.json` |
| 1 | `va_scan.py` | V-A 3런 stage-1 스캔, J1·NC3 스캔 sha 확인 | `AV/scans/va_s<S>/`, `va_scan_log.json` |
| 2 | `va_metrics.py` | 네 지표·Ω 분해·Ω 밖 (a)–(f)·두 짝·합집합·통계·표시 규칙·150 s 시계열 | `va_metrics.json`, CSV 3개, 그림 2개 |
| 3 | `va_fzp_local.py` | SC1001 EB 국소, 링크 174·SC109 동측 FZP 대수, DESSPEED | `va_local.json` |
| 4 | `va_control.py` | 결정·벽시계·유지·직전 계획 유지·SC109 p3·하한·미터·VSL | `va_control.json` |
| 5 | `va_followup.py` | 링크 174 사슬·입력 1083·SC109 동측 링크 | `va_followup.json` |
| 6 | `va_tables.py` | 표 만들기(서식만) | `va_tables.json` |
| 7 | `va_report_build.py` | 보고 글 + 표 → 보고서, 금지 낱말·같은 표 규칙 점검 | 보고서 `.md` + `.sha256` |

- 공통 정의 `va_common.py`(경로·이름·통계·표시 규칙)를 여덟 도구가 함께 씁니다.
- 실행 규칙: 한 번에 하나, BELOW_NORMAL, `python -B`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`. 5분 넘는 것은 `AV/run_py.ps1`(WMI 분리, 로그 파일, 임시 이름 = 시각 ms + 난수)로 띄웁니다. 런 폴더에는 쓰지 않습니다.
- 프로필: 모든 도구는 `--profile va` 또는 `--profile selftest`를 받습니다. `va`는 V-A 런을 읽고 `AV/out`에 씁니다. `va` 프로필은 고정 목록에 이 문서·`va_common.py`·자기 파일이 그 바이트로 있을 때만 돕니다(`va_common.require_pinned`). `selftest`는 V-A 자리에 J1 런을 넣어 자기 시험만 합니다(§7).
- 순서 (보충 34 §8.0-1): 유효성(§7.1, 개정 J1-A·H-A) → 보고 머리(보충 21 §5 1–10, 시드마다) → 분석. **V-A 성능 숫자는 분석 단계에서 이 도구로 처음 엽니다.** 감시·유효성 단계는 이 도구를 `va` 프로필로 돌리지 않습니다(S-VA-4).

## 3. 두 짝과 미삽입 합집합 (보충 34 §8.2)

- 합집합: 런 집합 안에서 `uninserted.json`의 `queued` 참 또는 `remain_err > 0`인 입력.
  - U6(V-A) = V-A 3 + NC3 3. U9 = V-A 3 + J1 3 + NC3 3. U6(J1) = J1 3 + NC3 3(= J1_REPORT 합집합).
  - 앵커는 모든 합집합에서 그 시드 NC3의 `anchored_total_generated`입니다.
- 짝과 열: 짝 A = V-A − NC3, U6(V-A) 열. 짝 B = V-A − J1, U9 열. 짝 B′ = J1 − NC3, U9 열. J1R = J1 − NC3, U6(J1) 열("J1 보고 값").
- 합집합에 기대는 줄: ④, ④b, ④b 입력별(1098, 1099, 그 밖), Ω 밖 (a). 표의 열 머리에 합집합 이름을 적습니다. 같은 합집합 열끼리만 뺍니다(R8). 합집합과 무관한 줄(①, ②, ③, ③u, ④a, Ω 밖 (b), Ω 분해, 제거, 진출 수신)은 합집합마다 같아야 하고, 다르면 도구가 멈춥니다.
- 통계(J1과 같은 꼴): 시드별 d, 평균, sd(n − 1), 90 % CI = 평균 ± 2.920 × sd / √3, 음/양 수(엄격 부등호), 평균/NC % = 100 × 평균 d / 세 NC3 평균(짝 B도 분모는 NC3 평균), 시드별 d/NC %. CI가 0을 포함하지 않으면 "관측된 차이"로만 적고, 동시 비교 행 수와 "보정 없음"을 함께 적습니다. 잡음 참고 반폭(① 175, ② 194, ③ 172, ③u 13, ④ 106)은 참고 칸에만.

## 4. 지표 정의 (보충 34 §8.3 번호대로)

1. **네 지표** (`va_metrics.py`, J1 `an_metrics.py` 그대로): ① = stage-1 영역 `fw_e_main` 칸 합. ② = `east_link_sets_source.json`의 `mainline`·`on_connectors`·`off_connectors`·`on_approaches` 19링크 `link_vh` 합. ③ = `omega_ttt` 칸 합. ③u = `urban_omega`. ④ = ④a `all_ttt` + ④b 미삽입(합집합·NC3 앵커). Ω 분해 = `region_omega_vh`의 fw_e_main, fw_w_main, onramp, offramp(Ω 안), urban_omega, outside(Ω 안, 0이어야 함), 합 = `totals.omega_ttt_veh_h`. 적분은 FZP 프레임 5.1–8,995.1 s 사다리꼴, 150 s 칸. Ω 지킴(1,236/635)은 stage-1이 합니다.
2. **Ω 밖**(Ω와 늘 같은 표): (a) ④ − ③, (b) ④a − ③, (c) ④b와 입력별(1098, 1099, 그 밖), (d) 차로변경 제거 — **읽는 법 A** = 런 끝 `.err` 제거 전체(스캔 `err.removals`), **읽는 법 B** = 같은 제거 가운데 소속 파일(`membership_inside`) 기준 Ω 밖 링크에서 난 것(데이터 전에 둘 다 고정), (e) S7 늦은 보고(V-A·J1만): obs150 `err_<T>.jsonl`의 `lane_change_removal`을 `byte_offset`으로 한 번만 세고(처음 나온 T), `time_sec ≤ T − 150`이면 늦은 보고, (f) 런 끝 입력별 remain. Ω는 ④와 Ω 밖 없이 따로 인용하지 않습니다.
3. **링크 174 사슬과 입력 1083** (`va_followup.py`): 링크 21·10112·174·10280·10281·173의 stage-1 `link_vh` 전체와 4,350 s 뒤(칸 29–59). 링크 174 FZP 프레임 대수(모든 차로) 평균·최대·최대 시각(`va_fzp_local.py`). 입력 1083: 런 끝 remain, 삽입 수, NC3 앵커 재구성 지체(stage-1 `clipped_series`), 최대 큐(프레임 시각 값)와 시각, (V-A − NC3)과 (V-A − J1)에서 0 아래 자른 큐 차가 처음 10대를 넘는 150 s 표본 시각(프레임 29::30; 자르지 않은 차의 시각은 따로 보고), 4,200 s(칸 28)부터 150 s 칸별 진입 수 차, ④b의 입력 1083 몫 d(짝 A는 U6(V-A), 짝 B는 U9; 그 합집합 밖이면 0).
4. **SC109 p3** (`va_control.py`): SDMPC 결정 55개(T ≥ 900)의 action JSON `green_times['SC109_p3']`. p3 ≤ 24.5 s인 결정 수, 첫 T, 최장 연속(T 간격 150). p2·p3·p4 지령 평균·최대(전체, 그리고 T ≥ 4,350). V-A와 같은 시드 J1을 나란히. 실현 녹색은 계산하지 않습니다.
5. **(173, p4) 하한·씨앗** (`va_control.py`, 61결정): metadata 키 `head_discharge_floor_173_p4_<16 hex>` 이름(런마다 하나인지), 그 값의 첫 T·첫 값·최댓값, 앞 값(있는 결정끼리)보다 줄어든 T(사이에 유지가 있으면 "유지 뒤"로 따로), `k92_hb_seed_binding` = float 1.0인 결정 수와 T, `head_observation_groups_carried`·`_updated` 합, `head_observation_prior_discarded` = 1.0인 T 목록(T = 150 기대), `k92_w`·`k92_hb` 있는 결정 수(61 기대).
6. **SC109 동측과 E_out** (`va_followup.py`·`va_fzp_local.py`): 링크 1220000704·1220000803의 stage-1 `link_vh` 전체와 1,800–7,200 s(칸 12–47), FZP 프레임 대수 평균·최대((F) 전체, (P) 1,800–7,200 s); d(V-A − NC3), d(V-A − J1)와 통계. 모형 `SC109_E_out`은 "없음"(폐루프 런에 기록기 없음, 추정하지 않음).
7. **미터·VSL** (`va_control.py`, J1 꼴): 러너 행동 로그 `ramp_meter` 행의 `rate_vph`·`green_sec` 분포, action JSON `ramp_metering` 값 분포, 미터 명령(`ramp_metering` 사전)이 앞 결정과 달라진 결정 수. VSL 구역 머리 FW_E·FW_W(seg0/5/10/15) 명령 분포, 110 미만 결정 비율·첫 T·최장 연속·전이 행렬, 미래 블록 1·2 계획 VSL(`diagnostics.sdmpc_prediction_sequence.future[0..1].vsl`), 110 미만 구역 노출(그 (T, 구역)의 stage-1 `speed.zones[z].veh_km` 칸 T/150 합). 110 미만 결정과 110 결정의 `selected_objective`·`held_objective`는 "plant 모형 값"으로만 표시.
8. **유지와 직전 계획 유지** (`va_control.py`, D-K9-69): (i) 유지 = 영수증 `action_<T>.hold.json` 있음 또는 metadata `hold_previous_on_exception` 있음. 횟수·T·영수증의 바깥 형·root 형·숫자를 지운 첫 메시지 줄·`chain_length`·`source_sim_sec`·`origin_sim_sec`. (ii) 직전 계획 유지로 보이는 결정 = SDMPC T ≥ 1,050, 유지 아님, 그리고 (가) `green_times`와 `offsets` 전체가 T − 150 action JSON 값과 같음(JSON을 읽은 값의 `==`), (나) `diagnostics.sdmpc_prediction_sequence` 없음, (다) `metadata.joint_leader_selection`의 `selected_objective`와 `held_objective`가 `repr`로 같음. 세 조건 각각의 결정 수, 셋 모두 참인 결정 수·T 목록, 그 결정들의 `selection_status` 분포. V-A와 J1 나란히.
9. **결정 벽시계** (`va_control.py`): 런로그 `CONTROLLER_DECISION sim_sec=T wall_sec=W result=exit=E`로 예열(T < 900)·SDMPC(T ≥ 900) 각각 최소·중앙·평균·최대·합, 900 s 넘는 결정 수, 런 벽시계(launch 로그 `WATCHDOG_EXIT … wall_sec`). 비 = V-A SDMPC 중앙 / 같은 시드 J1 SDMPC 중앙을 G-K5 예산 1.0158과 나란히 — **보고만**.
10. **SC1001 EB 국소** (`va_fzp_local.py`, J1 꼴): 10491 커넥터 대수 평균·최대, 127 차로 1–2 대수 평균·최대, FW_W·FW_E 역류 창 비율(F1 §6 정의: 900 s부터 30 s 창(6프레임), 창 안 사건 프레임 ≥ 3이면 사건 창; 첨두 = 창 시작 [1,800, 7,200), 전체 = 900–9,000 s), 사건 창 수·첫 사건. 시간 범위 (P) 1,800–7,200 s와 (F) 전체 둘 다. 짝 A·B 통계.
11. **150 s 칸별 d 시계열** (`va_metrics.py`): ①·③·④·④b·Ω 밖 (a)를 시드별·평균으로 짝 A·B 각각 CSV(`va_bins_delta.csv`), 그림(`va_bins_delta_A.png`, `_B.png`; V-A 결정 가운데 FW_E·FW_W VSL 110 미만 T 세로선). 보고서 표는 900·1,800·3,600·5,400·7,200·9,000 s 누적.
12. **U9-a `DESSPEED`** (`va_fzp_local.py`, V-A만): FW_E 구역 z(seg0/5/10/15)의 표지점 p_z = stage-1 `zone_extents` 표지 위치(0.1 m 반올림) 최솟값, 구역 끝 e_z = 다음 구역 머리(마지막은 사슬 끝). SDMPC 결정 T(900 … 8,850)마다 명령 c = action JSON `vsl[z]`. FW_E 사슬 위 사슬 위치 cp가 p_z ≤ cp < e_z인 첫 프레임이 (T, T + 150]인 차량, 그 프레임의 `DESSPEED`. 그 전에 cp < p_z로 관측됐으면 "표지 통과", 아니면 "상류 관측 없음". 띠: 읽는 법 C(m = c)와 읽는 법 M(m = M(c): 80→81, 90→91, 100→101, 110→110) 둘 다, m < 110이면 [m − 1, m + 1], m = 110이면 [98, 140]. 고르지 않습니다.
13. **점검**: 짝 A의 900 s 전 칸(0–5) d = 0과 `pairing_check(seed, NC3, V-A, 900)`. 짝 B의 900 s 전 칸 최대 |d|와 `pairing_check(seed, J1, V-A, 900)`도 보고만(예열 메타가 달라도 VISSIM 명령은 무제어로 같다는 기대 [추론]; 다르면 그 사실을 적음).
14. **J1-R 재현 표본**: 하지 않습니다(보충 34 §8.3-14, J1과 같음). 열린 항목.

## 5. 숫자를 읽을 때 쓰는 말 (보충 34 §8.4)

- `va_common.label`: d(③) < 0인 칸(시드별·3시드 평균)에만. 읽는 법 N: d(④) ≤ 0 그리고 d(④ − ③) ≤ 0 → `같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)`, 하나라도 > 0 → `대기 이전(Ω 밖으로)`. 읽는 법 W: N에 더해 d(④b) ≤ 0, d(제거) ≤ 0 — 제거는 읽는 법 A(W_A)와 B(W_B) 각각. d(③) ≥ 0 → `해당 없음(Ω 감소 아님)`. 고르지 않습니다.
- 짝 A는 U6(V-A) 값으로, 짝 B는 U9 값으로 같은 글로 셉니다(짝 B 적용은 보충 34가 데이터 전에 정한 새 적용).
- 표시 칸의 글은 위 세 문구뿐입니다. 보충 34 §8.4 R12가 금지한 낱말은 보고서 어디에도 쓰지 않습니다. `va_report_build.py`는 그 낱말과 판정 낱말(이긴·이겼·진다·졌다·낫다·좋아졌·나빠졌) 글자열이 있으면 보고서를 만들지 않고(exit 3), Ω(③)가 나오는 표에 ④와 Ω 밖 (a)가 없으면 멈춥니다(exit 4). 이 글자열 점검은 보수적입니다("-어진다" 같은 말도 걸리므로 보고 글은 그런 말을 피합니다).
- 보고서 머리: J1 단서 두 파일 + `VA/J1_CAVEAT_ADDENDUM_K92VA.md`(보충 34 §8.4 글자 그대로, 보고 단계에서 만듦), 보충 21 §5 보고 머리 10항목(시드마다; 6번 H-R1 "해당 없음", 8번 고정 문구 아래 보충 34 §8.0-1 한 줄), 보충 34 §9 공개 요약. `--require-header`를 주면 8번 아래 줄과 덧붙임 2 이름이 없을 때 멈춥니다(exit 5).

## 6. 독립 검증 (보충 34 §8.0-3)

- `AV/verify/`: `v_common.py`, `v_fzp.py`, `v_metrics.py`, `v_local.py`, `v_control.py`, `v_compare.py`, 묶음 실행 `v_chain.cmd`. 분석 도구와 stage-1 도구를 import하지 않습니다(J1 검증 도구 `SP/j1/analysis/verify/v_*.py`의 꼴을 9런으로 넓힘).
- 하는 일: FZP를 직접 읽어 프레임×링크 대수 행렬을 만들고(V-A 3런; J1·NC3은 J1 검증 출력 `fzp.npz`를 sha256 앞 16자 확인 뒤 다시 씀), `.inpx`·`.err`·obs150 jsonl·action JSON·런로그·launch 로그·러너 행동 로그에서 두 짝·세 합집합·제거 A/B·S7·입력 1083·링크 174 사슬·SC109 동측·SC1001 국소·DESSPEED(C/M)·결정·벽시계·유지·직전 계획 유지·p3·하한·미터·VSL을 다시 냅니다.
- `v_compare.py`가 분석 출력 JSON과 대조합니다: veh·h 칸은 |차| ≤ 0.05(0.1 반올림 안), 대수·T·목록·이름은 같음, 비율·평균은 1e-6(입력 1083 최대 큐는 0.5대). 끝 줄 `ALL_OK`가 아니면 그 차이를 보고하고 STOP입니다.
- 검증 도구의 sha는 이 문서와 함께 지금(첫 V-A 발사 전) 고정합니다(보충 34 §6.1 발사 전제 (4)).

## 7. 자기 시험 (보충 34 §8.0-2) [실행 2026-10-23 11:54–12:3x KST, `--profile selftest`, V-A 자리 = J1 런]

- 기준: 짝 A(= J1 − NC3, U6(J1))가 `SP/j1/analysis/J1_REPORT.md` §3.1·§3.2·§3.3·§5·§7·§8.1 표의 칸을 그 표에 보인 자릿수의 반올림 안에서(|내 값 − 표 값| ≤ 0.5 × 10^−자릿수) 다시 내야 하고, 짝 B(= J1 − J1)는 모든 칸 0이어야 합니다.
- 분석 도구 자기 시험 `va_selftest.py`(분석 도구 출력과 J1_REPORT 표·J1 도구 JSON을 대조, 읽기만) 결과: **223/223 참, `ALL_OK`** [실행]. 내용: 다시 한 V-A(=J1) 스캔이 J1 스캔과 `an`·`scan_sec`·`tag` 밖 모든 키가 같음(3/3), 미삽입 재구성 같음(3/3); 짝 A 요약이 J1 `an_metrics.json`과 최대 |차| 0; 합집합 셋 = J1 12입력; 짝 B 모든 d = 0; B′ = J1R = A; 900 s 전 칸 d = 0, `pairing_check` 참; J1_REPORT §3.1 12줄, §3.2 15줄(CI 표시 포함), §3.3 4줄(수와 표시 문구), §5 입력 1083 6줄·첫 10대 초과 시각·링크 6개, §7 11줄·FW_W 사건, §8.1 숫자 줄·선택 상태·설치 점검·미터·VSL 행; VSL 선택 통계·노출·목적값 요약·미터·벽시계가 J1 `an_control.json`과 같음; DESSPEED 읽는 법 C·M(구역별)이 J1 `an_local.json`·`an_followup.json`과 같음; SC1001 국소 대수가 J1 `an_local.json`과 같음.
- 자기 시험 중 고친 것(모두 V-A 자료 0인 상태, 고정 전): `va_control.py` 유지 영수증 필드 위치와 "줄어든 T" 계산(있는 값끼리 비교), `va_metrics.py` 합집합 반복 한 줄 단순화, `va_selftest.py` 표 열 번호·사건 줄 파싱(대조 도구 쪽 결함). 계산 정의는 바꾸지 않았습니다.
- 검증 도구 자기 시험(`v_chain.cmd selftest` → `v_compare.py --profile selftest`) 결과는 고정 줄과 함께 `VA/LOG.md`·`VA/VA_LAUNCH.md`에 적습니다(이 문서는 그 결과 전에 고정하지 않고, 결과를 본 뒤 이 줄을 고치지도 않습니다).

## 8. 공개 (보충 34 §8과 다르게 하거나 더한 것)

1. **파일이 여덟보다 많습니다**: 보충 34 §8.0이 정한 여덟 도구 이름은 그대로이고, 공통 정의 `va_common.py`, 자기 시험 `va_selftest.py`, 분리 실행 `AV/run_py.ps1`를 더했습니다. 검증 쪽은 `v_*.py` 여섯과 `v_chain.cmd`입니다. 모두 고정 목록에 넣습니다.
2. **프로필 장치**: 자기 시험을 같은 도구로 하려고 `--profile`을 두었습니다. `va` 프로필만 V-A를 읽고, 고정 목록 확인을 통과해야 돕니다.
3. **제거 읽는 법 B를 데이터 전에 고정**: J1에서는 사후였습니다(J1_REPORT §2.3-3). V-A는 보충 34 §8.3-2대로 A·B를 모두 분석 도구가 냅니다.
4. **DESSPEED 읽는 법 M을 데이터 전에 고정**: J1에서는 사후였습니다(J1_REPORT §2.3-1).
5. **직전 계획 유지의 "같음"**: JSON을 읽은 값의 `==`입니다(파이썬에서 24와 24.0은 같음으로 셈). 목적값은 `repr` 글자 비교이고 값은 출력하지 않습니다.
6. **입력 1083 "처음 10대"**: 선언 정의(0 아래 자른 큐 차)를 쓰고, 자르지 않은 큐 차의 시각은 보고만 합니다(J1 검증과 같은 두 값).
7. **SC1001 EB 국소 표에는 Ω가 없습니다.** Ω·④·Ω 밖은 §3·§4의 같은 표에 있습니다.
8. **실현 녹색(signal readback)·모형 `SC109_E_out`·J1-R**: 하지 않습니다(보충 34 §9.1-12, §8.3-14).
9. **분석은 런이 끝난 뒤 제자리 파일을 읽기만 합니다**(쓰기 0). 감시·건강 점검 단계의 사본 규칙은 `VA/launch/` 도구가 따로 지킵니다.

## 9. 고정 목록

- `AV/va_analysis_pins.sha256`: 이 문서, `AV/tools/` 열 파일(여덟 도구 + `va_common.py` + `va_selftest.py`), `AV/run_py.ps1`, `AV/verify/` 일곱 파일. sha256은 `VA/LOG.md`에도 적습니다.
