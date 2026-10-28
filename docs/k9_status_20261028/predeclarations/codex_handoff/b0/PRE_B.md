# PRE_B — B 폐루프(codex 판 v3c3 이식 탐침) 사전 계획 (2026-10-26 KST, 계획만)

- 이 문서는 **계획**입니다. 발사 허락이 아닙니다. B 폐루프 VISSIM 런은 사용자가 따로 "띄워도 된다" 고 할 때만 띄웁니다(NOTES D-K9-84·D-K9-86).
- 판정 낱말은 쓰지 않습니다. Ω 는 늘 ④ 와 Ω 밖과 같이 적습니다. 시드 수를 늘 밝힙니다(3개, 모두 우리 fit 시드, codex 계수에는 표본 밖).
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- 근거: NOTES `SP/K9_1_J1_NOTES_20261013.md`(sha `67dcc32b…`) D-K9-84 Q2·Q6, D-K9-86, D-K9-87; TAKEOVER_PLAN r2 §1.2(`b75ad041…`); HANDOFF_RESULTS r2 §3(`964a23ce…`) H8–H14; B0 보고 `SP/codex_handoff/b0/B0.md`. SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`.

## 줄임말

- B = codex 판(a49981ff)을 우리 기준 망 v3c3(`3de889f0…`)로 옮긴 폐루프. NC3 = 같은 시드 v3c3 무제어 런 셋. V-A = 우리 묶음 B1 폐루프 셋. Ω635·Ω701 = 우리·codex 목적 영역. ④a = 망 전체 링크 체류 TTT, ④b = 미삽입 대기, ④ = ④a+④b, Ω 밖 (a) = ④ − Ω, (b) = ④a − Ω. ① = FW_E 본선 7링크, ② = 동측 국소 19링크. FRZ = 동결 트리. StallSec = 러너 감시가 진행 없음으로 런을 끊는 초(2,400).

## 1. 런 정의

| 항목 | 값 |
|---|---|
| 코드 | b0 트리를 동결한 FRZ. 지금 후보 = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258` (FREEZE.json `853d1c4f…`, 7,989 파일) [실행]. 발사 전 B0 를 더 고치면 다시 동결 |
| 설정 | `diagnostics/b0_v3c3/config_b0_v3c3.json` sha `729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983` [실행]. VSL 고정 110, calibrated_aggregate 끔, RM_C 키 + strict, 유지 = 예외 한정(시한 없음) |
| 망 | v3c3 `diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx`, `3de889f0…`. 시드는 러너 `-Seed` 로 줌(V-A 와 같은 방식, V-A 세 시드 모두 이 망 sha [실행]) |
| 시드·차례 | v3c3-s31 → v3c3-s41 → v3c3-s43, **차례로 하나씩**. 인계 러너는 다른 VISSIM 이 열려 있으면 거부(run_closedloop3000.ps1 의 발사 전 검사) [읽음]. A1 이 끝난 뒤에만 |
| 길이 | 9,000 s, 결정 150 s, 제어 시작 900 s(그 전은 no-control 워밍업) |
| 러너 인자 | `-FrozenTree <FRZ> -ResultsRoot <새 결과 뿌리>/s<seed> -SimPeriod 9000 -Seed <seed> -Arms sdmpc -TuningRelativePath diagnostics/b0_v3c3/config_b0_v3c3.json -NetworkRelativePath diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx -NetworkSha256 3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e -PythonExe <Python312> -PowerShellExe <codex 런타임 pwsh 7.6.5> -DependenciesPath D:/VISSIM-window264-deps` |
| 환경 | env_hsw(OPENBLAS_CORETYPE=Haswell, NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX, NUMBA_CPU_NAME=haswell), PYTHONHASHSEED=0, OMP/OPENBLAS/MKL 스레드 1, RW_* 는 러너·워치독이 세움(A1 래퍼와 같은 방식으로 사용자 env 의 RW_* 를 지움) |
| 발사 | A1 과 같은 WMI 분리 발사(Invoke-CimMethod Win32_Process Create, PowerShell), 우선순위 Normal, 래퍼가 env 를 기록 |
| 결과 뿌리 | 새 폴더(예 `D:/VISSIM_runs/<날짜>_codex_b_v3c3/`) — 발사 승인 때 정함. 기존 런 폴더에는 쓰지 않음 |
| NC | NC3 재사용: `D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run` [읽음 OM 표] |

## 2. 발사 전 관문 (모두 통과해야 발사 질문을 올림)

1. **v3c3 결정 시간과 결정 단계 예외 0 을 먼저 봄.** B0 의 V-A 상태 재생 셋(T=3,450·1,800)은 직전 명령의 SDMPC 가격 문맥이 우리 제어기 것이라 `load_prices` 에서 멈췄고 결정 시간을 내지 못했습니다 [실행 B0.md §6]. 그래서 **T=900(워밍업 직후 첫 제어 결정, 직전 명령에 sdmpc_state 없음) 재생**을 새 선언과 함께 따로 허락받아 돌립니다 [추론: sdmpc.py:772-774 의 first_sdmpc_decision 길]. 이것이 결정 단계 전체(PFO·이웃 검사·cap 후보·tangent)를 v3c3 상태에서 끝까지 도는 첫 시험입니다.
2. **StallSec 여유.** 유지 정책이 예외 한정이라 결정 시한이 없고, 결정 한 번의 상한은 StallSec 2,400 s 입니다 [읽음 B0.md §3 H1]. 이 PC 의 codex 코드 결정은 64cf 에서 최대 1,042.5 s(A0b, 다른 VISSIM 동시) [실행 LOG 18:15]. v3c3 결정 시간은 관문 1 에서 잽니다. 관문 1 의 최대가 1,500 s 를 넘으면 StallSec 를 올릴지 따로 묻습니다.
3. **러너 사전 점검(시드마다).** 같은 FRZ·인자로 `-PreflightOnly` → FREEZE_VERIFIED, 망 sha, provenance 의 RW_DECISION_ERROR_POLICY=hold_previous_on_exception·RW_DECISION_TIMEOUT_SEC=0, plant manifest·검지표 핀 확인. s31 은 B0 에서 통과 [실행 B0.md §5].
4. **VISSIM 0 확인**(내 것만 셈, 남의 것은 건드리지 않음), 디스크 C·D 각 8 GB 이상 + 런당 약 8 GB.
5. **900 s 전 같음 점검(짝 성립).** 각 B 런의 FZP 0–895 s 접두가 같은 시드 NC3 와 같은지(J1-V 꼴). 다르면 그 시드의 짝 차에 단서를 붙이고 따로 보고합니다(런은 버리지 않음).

## 3. 지표 (D-K9-84 Q2, D-K9-87, HR H10–H14)

- 같은 표에: Ω635, Ω701, ④a, ④b, ④, Ω 밖 (a)·(b) (Ω701 기준과 Ω635 기준 둘 다), ①, ②, 입력별 미삽입(1098 FW_E 입구·1099 FW_W 입구·도시 입력 합).
- 적분 꼴 둘: 우리 꼴 [0, 9000] s, codex 꼴 [0, 8100] s(OMEGA701_V3C3 §4.3 와 같은 두 꼴).
- **④b 짝 차 주 값 = 첫 관측 차분**(같은 망·같은 시드 짝, 도착열 같다고 봄, D-K9-87·H14). stage-1 재구성은 참고 열. B 런은 codex 러너가 native 망 성능을 남기면 그 DelayLatent 수준값도 적되(H14), NC3 에는 native 파일이 없어 [실행 HR §3] 짝 차는 첫 관측 차분만 씁니다.
- 짝: **B − NC3**(같은 시드, 주 표), **B − V-A**(같은 시드, 보조 표). 시드끼리 평균 내지 않음, 다중 비교 보정 없음(3시드).
- 따로 적는 줄: 링크 66(SC1004 남측, H11) 한 줄, 도시도로 두 규칙(codex 규칙·우리 규칙, H12), LDP 신호 실행 대조(B-8, `ldp_cmp.py` 꼴), 미터 실행 대조(`rm_exec.py` 꼴)와 미터 녹색·rate 분포(B-7), 결정 벽시계 분포, 유지(hold) 수와 T 와 예외 종류(H9), 결정마다 램프 도착 예측 합(메타데이터 `forecast_ramp_arrival_total_vph`)과 RM_C 별 값(있으면).

## 4. 분석 도구 고정 (B 데이터 전, 바꾸지 않음) [실행 sha256]

| 도구 | sha256 | 쓰임 |
|---|---|---|
| `SP/codex_handoff/work/vhr/vhr_firstseen.py` | `42e17585172e8c3cdc529ee0b0768ec958ab34729bbe686c590e70053ada4c94` | 차량별 첫 관측(④b 첫 관측 차분 입력) |
| `SP/codex_handoff/work/vhr/vhr_unins.py` | `fc233013623d797657c19e0efbb59b6ccad720a19a84e723491ad73a34337532` | 첫 관측 차분 짝 차 |
| `SP/codex_handoff/work/vhr/vhr_v3c3_all.py` | `b42372512a26960530cfe89b1dc731a74f7fc83531c17f4ec04c4706409d2c99` | v3c3 짝 표(Ω635·Ω701·④·Ω 밖·①, 두 적분 꼴) |
| `SP/codex_handoff/work/omega/omega701_recount.py` | `5b7826f65c58a883c2dc4a3eccd6de92563bb12f812dd0d6579be8a42c92a5ac` | 우리 꼴 적분 |
| `SP/codex_handoff/work/omega/build_tables.py` | `134d580bef43c4d0cb223f3a8571dd434e55ab6156e5f10344153e85d99712fb` | 표 조립 |
| `SP/codex_handoff/work/omega/top66.py` | `1424b5adb773ed1de0d12a517b01811c1efb15092e6826e8efcba166a2937d80` | 링크 66 줄 |
| `SP/codex_handoff/work/rawcheck/metrics.py` | `b524b51be11b15e28971b141fe9b9b812631ac5b96d86d116cc0f4955c75cf0d` | codex 꼴 지표·도시도로 분할 |
| `SP/codex_handoff/work/rawcheck/scan_fzp.py` | `c8a6e5c4ee873a698b660b32662ec09d4f5f280765a2413764259372a5ddc425` | FZP 스캔 |
| `SP/codex_handoff/work/rawcheck/ldp_cmp.py` | `2bb7d6c2bcc5da79e0d2ff37c8b04c1ed481488c58a6c0dd61db61036f34d6e8` | 신호 실행 대조 |
| `SP/codex_handoff/work/rawcheck/rm_exec.py` | `27f6402205d6c7cbd3524a44ee35632e19a90f681a10d21fffa3b5518dbb1c10` | 미터 실행 대조 |
| `SP/codex_handoff/work/rawcheck/SHA256SUMS_RAWCHECK.txt` | `3e3b53077eb3a3d43a737b14e996ede96852cfa72d67994566d03e6e2b69ceac` | rawcheck 도구 목록 |
| `SP/k92/va/analysis/va_analysis_pins.sha256` | `39a97e7f5a95d3db2d9841849ea3613f26b4d8a3a5426904156aac4770f7903e` | V-A 분석 도구 목록(20줄) |
| `SP/k92/va/analysis/r4/R4_PINS.sha256` | `1ca353a937ae81cc10bedbf46ee49cadca30012f0f97926d5e0235790841a29f` | 첫 관측 고침 도구 목록 |
| `SP/k92/va/analysis/r4/COMPARE_RULE_R4.md` | `349bd69d9074318d1f4ed3f29d706fffcd74af05bb0a01f8c15b8b92364ca363` | 첫 관측 차분 규칙 |

- 위 도구 가운데 런 경로를 파일 안 상수로 가진 것은 **경로 상수만 바꾼 사본**을 B 데이터 전에 만들고, 원본과의 차이 줄과 사본 sha 를 LOG 에 적습니다. 그 밖의 줄을 바꾸면 "데이터 뒤 변경" 으로 밝힙니다.
- B 비교 규칙 문서(COMPARE_RULE_B.md: 위 §3 를 그대로 옮기고 표 칸 이름·반올림·결측 처리를 적음)는 첫 B 런 발사 전에 쓰고 sha 를 LOG 에 고정합니다.

## 5. 감시와 멈춤

- 진행 신호는 A1 과 같은 목록(runlog·state CSV·action CSV·최신 action JSON·진행 기록·WATCHDOG_PROGRESS) [읽음 LOG 00:59]. 사용자 정책: 정상 거동보다 5분 더 진행이 없으면 확인 뒤 **이 런의 PID 만** 멈추고 한 번만 다시 띄우며 기록. 이름으로 kill 하지 않음.
- 런 사이: 앞 런 `STAGE=SIM_DONE`·결정 exit 코드·유지 수·`.err` 를 확인한 뒤 다음 시드.
- 디스크 8 GB 미만이면 멈춤. 제외 예외 8종(정지 목록, NOTES:47)은 유지하지 않고 런이 멈춤 — 그대로 보고.

## 6. 시간 어림 [계산·추론]

- 런당 약 12.1–13.6 h(HR B-9, codex joint 결정 평균 × 이 PC 배수 2.30–2.63; v3c3 결정 짐은 관문 1 전까지 모름), 세 시드 차례로 약 36–41 h. 관문 1 재생은 결정 하나 약 10–30 분 [추론, A0b 1,042 s 최대].

## 7. 이 계획이 알려 주지 않는 것 [추론]

- 64cf-s29 로 맞춘 D 부류 계수(eval_036 셀별 FD·상태 반응, port_gain parameters·port_profile, retained10638 protocol, segment_params)가 v3c3 에 맞는가, 기구별 몫, codex 64cf 숫자의 재현. 작거나 반대 방향의 결과도 "계수 불일치" 와 "기구 효과 없음" 을 가르지 못합니다(TAKEOVER_PLAN §1.2).
