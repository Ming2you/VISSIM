# PRE_A1 — A1 재현 런 계획 (계획서. VISSIM 을 띄우지 않았습니다) (2026-10-25 KST)

- 무엇: D-K9-83·84 의 A1 = 64cf-s29 joint 8100 s 재현 런 한 번의 계획입니다. **A1 은 사용자가 따로 "띄워도 된다" 고 할 때만 띄웁니다(D-K9-84).** 이 문서는 발사 명령을 담지 않고, 정할 것과 근거만 담습니다.
- 근거 문서: `codex_handoff/A0_PROFILE.md`(A0 결과), `TAKEOVER_PLAN.md` r2 §1.1·§5(Q5·Q5c), `RAW_CHECK.md`(codex joint 지표), `OMEGA701_V3C3.md`(지표 정의·도구), NOTES D-K9-82·83·84.
- 짝 개수: codex 증거는 64cf-s29 한 짝(joint 한 런 + NC 한 런)입니다. A1 도 한 런입니다. 한 짝으로는 런 사이 흔들림을 가를 수 없습니다.

## 줄임말 (처음 한 번)

- A0 / A1: 준비(VISSIM 없음) / 재현 런(VISSIM). R1–R3: A0-CMP-1 의 명령 CSV 바이트·일곱 필드 해시·채점 토큰 대조. env 이름 base·env_hsw·S1·py31214 는 A0_PROFILE 줄임말과 같습니다.
- NC / LNC: 무제어 / 이 PC 의 64cf-s29 NC(`D:/VISSIM_runs/vsl_repro_s29/none/run`).
- Ω701 / Ω635: codex 목적 영역 701 / 그 전 영역 635. ④a 망 전체 링크 TTT(총 통행시간, veh·h), ④b 미삽입 대기, ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω, Ω 밖 (b) = ④a − Ω. ① FW_E 본선 7링크(74·10699·2·10613·119·10702·24).
- StallSec: 워치독이 "진행 없음" 으로 런을 죽이는 시간. 시한: 결정 한 번의 상한(넘으면 직전 명령 유지).

---

## 0. 쉬운 답

1. A1 은 codex 코드(인계 `code/` 바이트 + A0 에서 복원한 데이터 3,544개 + 대역 3개)를 그대로 쓰고, 속도 변경으로는 S1 하나만 넣을 수 있습니다. S1 은 A0 의 5개 재생에서 같은 env 기준과 비트 동일이었고, 빈 PC 에서 나란히 잰 이득은 결정당 4.5 s(0.85 %)입니다 [실행, A0_PROFILE §6.3]. 넣지 않아도 됩니다.
2. 그러나 A0 에서 **수정 없는 codex 코드도 이 PC 에서 기록 결정을 세 개 모두 비트 단위로 다시 내지 못했습니다** [실행, A0_PROFILE §4]. 그래서 D-K9-83 의 재현 기준을 그대로 두면 A1 은 시작 전에 이미 채울 수 없는 기준을 가집니다. env 선택(U1)과 재현 기준(U2)을 사용자가 정해야 합니다.
3. 예상 벽시계는 약 10.9–12.2 h 입니다(codex 결정 시간 × A0 재생 배수 2.30–2.63 + VISSIM 부분 × 2.12) [계산 §6]. 결정 최대 어림 1,031–1,179 s 로 시한 1,800 s 안입니다. 배수가 4.01 을 넘으면 가장 긴 결정(codex 448.6 s @2400)이 시한에 걸립니다.
4. 인계 러너는 다른 VISSIM 이 열려 있으면 발사를 거부합니다(run_closedloop3000.ps1:164-172). 발사 순간 이 PC 에 VISSIM 이 없어야 합니다(U4).
5. NC 는 LNC 를 다시 씁니다(D-K9-84). 지표는 D-K9-84 Q2 의 표 하나로, 분석 도구는 sha 로 고정합니다(§5).

---

## 1. 런 정의 (고정할 것)

| 항목 | 값 | 근거 |
|---|---|---|
| 망 | `native_seed29.inpx` sha `64cf5f55…`(러너가 검사, run_closedloop3000.ps1:132) | [실행 sha, 읽음] |
| 시드 | 29 | D-K9-84 Q5 |
| 길이 | SimPeriod 8100 s, 결정 간격 150 s, ControlStartSec 900 | 러너 :152-153 [읽음], codex joint 와 같음 |
| 팔 | `-Arms sdmpc`(joint), tuning `diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json` sha `c9088262…` | raw joint run_provenance `/files/tuning` [실행] |
| 코드 | 인계 `code/` 바이트(SOURCE_FILES 3,638 일치) + 복원 3,544(RESTORED_FILES.json `184a2604…`, 동결 목록 sha 일치만) + 대역 3(STANDIN_FILES.json `c80839a9…`) | A0_PROFILE §1.1 |
| 러너·워치독·VBS | run_closedloop3000.ps1 `8e95423b…`, 워치독 `b56e1b36…`, run_real_world_stackelberg_controller.vbs `14722088…`, lane_native_b110.vbs `b74e05b2…`, `_sgplan.vbs` `ec731cab…` | [실행 sha] |
| 어댑터 | vissim_stackelberg_adapter.py `a615d8ca…`, sdmpc.py `5c1ba251…` | [실행 sha] |
| 의존성 | `D:/VISSIM-window264-deps`(numpy 2.3.5, numba 0.67.0, llvmlite 0.49.0, scipy 1.18.1, pandas 3.0.1) | A0_PROFILE §1.3 |
| 동결 | 새 동결 트리를 `freeze_manifest.py build` 로 만들고 러너가 `verify` (러너 :118-119). `__pycache__`·`__tangentcache__`·`*.pyc` 는 동결 검사에서 빠짐(freeze_manifest.py:37-59) | [읽음] |
| 바꾸지 않는 것 | 설정 키(cap 3, 이웃 검사, 워커 8, `ignore_wall_time_limits` true), OMP/OPENBLAS/MKL 스레드 1, 코드 바이트 | D-K9-83, A0_PROFILE §6.3 |

- [추론] 대역 3개는 원래 바이트가 아닙니다. A1 기록에서 그 세 파일의 sha 핀(`joint.json /source_sha256`)은 codex 기록과 다를 것입니다. 명령에는 env_hsw T=900 에서 영향이 없었습니다.
- [읽음] 러너가 기록하는 provenance `/env` 는 RW_* 21개뿐입니다(W264 provenance 로 확인). env_hsw·S1·py31214 의 변수는 provenance 에 남지 않으므로 발사 기록에 따로 적어야 합니다.

---

## 2. 사용자 결정

| # | 질문 | 선택지 | A0 근거 | 권장(까닭) |
|---|---|---|---|---|
| U1 | 수치 env | (a) base(인계 러너 환경 그대로) / (b) env_hsw(발사 환경에 변수 3개를 더함: `OPENBLAS_CORETYPE=Haswell`, `NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX`, `NUMBA_CPU_NAME=haswell`) / (c) 위 둘 가운데 하나 + Python 3.12.14(codex 런타임 판, `-PythonExe`) | base: 3결정 모두 기록과 다름(23·44·33행), T=2700 미터 녹색 1 s 차, T=2700·4950 작업 수도 기록과 다름. env_hsw: T=900 명령 일치, 2700·4950 은 40·17행이 녹색 ≤0.001 s·offset ≤0.003 s 차, 미터·VSL 행 같음, 작업 수는 3결정 모두 기록과 같음. Python 3.12.14: 두 env 모두 3.12.2 와 비트 동일(T=4950) → 기록 쪽으로 더 가깝게 하지 않음 | **(b), Python 은 어느 쪽이든**. 세 결정 모두 기록에 더 가깝고 이산 명령 차가 없었음. 다만 인계 러너 환경에 없는 변수라 "받은 그대로" 에서 한 걸음 벗어남. 변수는 발사 기록에 적음 |
| U2 | 재현 기준 | (a) 엄격: 결정마다 R1(명령 바이트) 일치, 처음 다른 결정에서 "재현 끝" 으로 적음 / (b) 결정 추적: 결정마다 기록과의 차(다른 행 수·최대 차·이산 명령 차)를 적고, 처음 다른 T 와 그 뒤 상태 차를 보고 / (c) 결과 수준: 지표 표(§5)를 codex joint 와 나란히, 한 짝이라 판정 없음 | A0 재생으로 보면 (a) 는 base 면 T=900 에서, env_hsw 면 늦어도 T=2700 에서 깨짐 [실행 재생, 추론: 그 전 결정이 다르면 더 일찍]. 0.001 s 녹색 차가 VISSIM 상태를 바꾸는지는 모름 | **(b)+(c) 함께**. (a) 는 A0 결과로 이미 채울 수 없음. D-K9-83 의 "비트 동일" 은 속도 변경을 고르는 기준으로만 남김(S1 은 통과) |
| U3 | 결정 시한 | (a) 1,800 s 그대로(인계 바이트) / (b) tuning `decision_timeout_sec` 2,390 s(StallSec 2,400 미만) / (c) 시한과 StallSec 함께 올림(러너 :161 수정) | 어림 최대 1,031–1,179 s. 배수 4.01 에서 최대 결정이 1,800 s, 5.33 에서 2,390 s 에 닿음. (b) 의 오프라인 시험(T=900 한 결정): 명령·채점 토큰 같음, 문맥 토큰 해시 30개·경로 잎 2개만 다름 | **(a)**. 바이트를 안 바꾸고, 어림 최대와 1.5배 넘게 떨어져 있음. 시한 유지 결정이 나오면 그 수를 적음 |
| U4 | 자리(동시 실행) | (a) A1 혼자: 발사 때 VISSIM 0(러너 강제), 런 동안 다른 VISSIM·무거운 학습 없음 / (b) 발사 뒤 다른 런 허용 | A0 재생은 다른 세션 학습이 돌 때 2.30–2.63배, 빈 PC 의 T=900 은 2.31–2.33배. 동시 VISSIM 영향은 재지 않음 | **(a)**. 결정 시간이 시한과 재현성에 닿음. TD3 등 다른 세션 작업 일정은 사용자가 정함 |
| U5 | 발사 방식 | (a) 러너 `-Detached`(예약 작업, 우선순위 5 = Normal, **실행 한도 24 h**, :82-83) / (b) 우리 WMI 분리 발사로 러너를 `-Detached` 없이(한도 없음, 우선순위는 발사 때 정함) | 어림 10.9–12.2 h 는 24 h 안. W264 는 이 PC 에서 28.3 h 였고 그 러너는 24 h 한도를 끈 수정본(diff 확인) | **(b)**, 우선순위 Normal. 러너 바이트를 안 바꾸고 24 h 한도에 걸릴 위험이 없음. 세션 종료로 죽지 않게 WMI 로(메모리 vissim-launch-detached-from-session) |
| U6 | S1 넣기 | (a) 넣음(환경 변수만, 바이트코드 접두 캐시를 발사 전에 채움) / (b) 안 넣음 | 5개 재생 비트 동일, 빈 PC 이득 결정당 4.5 s(49결정이면 약 3–4 분) [실행] | **(b)** 도 됨. 이득이 작아 기록 단순함을 택해도 잃는 것이 거의 없음. 넣으면 접두 경로·채운 시각을 발사 기록에 적음 |
| U7 | 차가운 캐시 | (a) 그대로(첫 무거운 결정에서 `__tangentcache__`·numba 를 한 번 만듦) / (b) 발사 전에 A1 트리에서 오프라인 재생 한 번으로 데움 | 첫 완주 대 데운 반복 차 22 s(열기 추적 포함) | **(a)**. 12 h 중 수십 초 |
| U8 | NC | (a) LNC 재사용 / (b) 8100 s NC 한 번 추가(약 1.7 h) | LNC = codex NC(FZP 전체 데이터행 같음, RAW_CHECK) | **(a)**(D-K9-84). ④b 0–8100 은 RAW_CHECK 의 16,643.4(경로 A)·16,644.9(경로 B) 를 씀 |
| U9 | A0b(선택, VISSIM 0) | 기록 결정 1050–2550 을 같은 env 로 차례로 재생해 "처음 다른 결정" 을 미리 찾음 / 안 함 | codex 시간 합 3,377 s × 2.3–2.6 ≈ 2.2–2.5 h. 기록 상태(codex 궤적)로 재생하므로 A1 궤적과는 처음 다른 결정까지만 같은 입력 | 하면 U2(b) 의 비교 기준점이 생김. 사용자 선택 |

- 권장은 근거 정리일 뿐이며 사용자 결정이 아닙니다. VISSIM 런은 U1–U9 를 정한 뒤 따로 물음(D-K9-84).

---

## 3. 시한과 StallSec 의 일관성 [읽음·실행]

- 시한은 tuning `runtime.decision_timeout_sec`(1800)에서 워치독이 읽어 `RW_DECISION_TIMEOUT_SEC` 로 넘기고(watchdog:325-334), VBS 가 결정 프로세스에 적용합니다(run_real_world_stackelberg_controller.vbs:1259). 넘으면 직전 명령을 유지합니다(`hold_previous`, control_hold.py:69-125).
- 워치독은 30 ≤ 시한 < StallSec 만 받습니다(watchdog:330-331). 러너는 StallSec 2,400, StartupStallSec 300 을 고정으로 넘깁니다(run_closedloop3000.ps1:161).
- 시간 무제한 결정(`ignore_wall_time_limits` true)이면 워치독은 `action_*.joint.progress.jsonl` 쓰기도 진행으로 셉니다(watchdog:672, 992-997). A0 에서 진행 기록 두 줄 사이 최대 간격은 131–199 s 였습니다(cap 2 QP 구간) [실행]. 그래서 결정 중 StallSec 에 걸릴 길은 시한보다 멉니다.
- 어댑터는 `decision_timeout_sec` 를 읽지 않습니다(grep 0) [실행]. 그러나 tuning 파일 sha 는 결정 기록 `joint.json /source_sha256` 에 핀으로 들어가고, 워치독은 tuning sha 를 `RW_SIGNAL_OBSERVATION_CONFIG_SHA256` 로 넘깁니다(watchdog:231; obs150 모드에서는 읽지 않음, obs150_contract.py:131-132) [읽음].
- U3(b) 오프라인 시험 결과 [실행, A0_PROFILE §7]: 시한 키만 2,390 으로 바꾼 tuning 사본으로 T=900(env_hsw)을 재생했더니 명령 CSV·일곱 필드·채점 토큰이 같은 env 기준과 같았습니다. 바뀐 것은 tuning 이름·sha 에서 온 문맥 토큰 해시 30개, tuning 경로 잎 2개, sha 핀 1개였습니다. 한 결정만 본 결과입니다.

| 선택 | 바뀌는 바이트 | 결정 최대 어림 대비 여유 | StallSec 관계 |
|---|---|---|---|
| (a) 1,800 | 없음 | 1,800 / 1,179 = 1.53배 | 1,800 < 2,400 |
| (b) 2,390 | tuning 한 칸(sha `c9088262…` → `9365141f…`) | 2,390 / 1,179 = 2.03배 | 2,390 < 2,400 (여유 10 s) |
| (c) 예: 3,500 / StallSec 3,600 | tuning 한 칸 + 러너 :161 | 2.97배 | 직접 맞춤 |

---

## 4. 무엇을 비교하나 (U2 (b)(c) 를 고르면)

1. 결정마다: A1 의 `action_T.csv` 와 codex 기록의 같은 T — 다른 행 수(kind 별), 최대 녹색·offset 차, 미터 rate·녹색 차, VSL 행 차. 처음 다른 T. 도구는 A0 의 s20_cmdsummary.py 꼴(고정 sha 는 §5).
2. 처음 다른 T 까지: A1 상태 JSON 과 기록 상태 JSON 의 관측 부분이 같은가(경로 칸 제외).
3. FZP: 895.1 s 까지 431,233행 LF sha256 `f1a0b040…cbda`(codex·LNC 와 같아야 함, RAW_CHECK §3). 그 뒤 처음 다른 프레임.
4. 지표 표(§5): A1 − LNC 를 codex joint − NC 와 나란히. 한 짝씩이라 판정 낱말 없이 차만 적습니다.
5. 시간: 결정마다 벽시계(runlog `CONTROLLER_DECISION wall_sec`), 시한 유지 수, codex 대비 배수.

---

## 5. 지표와 분석 도구 고정 (D-K9-84 Q2)

- 지표(0–8100 s, codex 꼴 적분, veh·h): Ω635, Ω701, ④a, ④b, ④, Ω 밖 (a)·(b)(Ω701 기준; Ω635 기준도 같이), ① FW_E 본선 7링크, ②, 입력별 미삽입(1098 FW_E 입구·1099 FW_W 입구·도시 입력 합). 0–8100 s 우리 꼴 값도 같은 표에 둡니다(OMEGA701_V3C3 §4.3 의 두 적분 꼴 차 참고).
- 비교 열: codex joint(RAW_CHECK §5.2: Ω701 6,911.5, Ω635 6,346.5, ① 1,840.9, ④a 8,545.9, ④b 16,423.6, ④ 24,969.5, Ω 밖 (a) 18,058.0, Ω 밖 (b) 1,634.4), NC(같은 표), joint − NC(Ω701 −494.7, ④ −668.8, Ω 밖 (a) −174.2, Ω 밖 (b) +45.7, ① −283.7; 64cf-s29 한 짝).
- 도구(발사 전에 sha 를 다시 확인하고 바꾸지 않음) [실행 sha]:

| 도구 | sha256 | 쓰임 |
|---|---|---|
| `work/rawcheck/scan_fzp.py` | `c8a6e5c4…` | FZP 프레임별 링크 차 수 |
| `work/rawcheck/metrics.py` | `b524b51b…` | Ω701·Ω635·①·②·④a·분할(codex 값과 ≤3.2e-11) |
| `work/rawcheck/uninserted2.py` | `bc3b4849…` | 입력별 ④b 재구성 |
| `work/rawcheck/fullhash.py` | `32f9bf44…` | FZP 접두·전체 해시 |
| `work/omega/omega701_recount.py` | `5b7826f6…` | 우리 꼴 적분(같은 표의 우리 꼴 열) |
| Ω701 소속 `derived/omega_membership_exact.json` | `efdfaeb1…` | 영역 |
| 분할 `code/…/selected/port_gain/geometry.json` | `91a584ab…` | 사슬·경계 |
| 목록 `work/rawcheck/SHA256SUMS_RAWCHECK.txt` | `3e3b5307…` | 위 rawcheck 도구 52개 |

- ④b 의 NC 쪽은 RAW_CHECK §5.1 경로 A 16,643.4 / 경로 B 16,644.9 를 그대로 씁니다. A1 쪽 ④b 는 A1 의 native DelayLatent 와 재구성 둘 다 적습니다.

---

## 6. 예상 벽시계 [계산 `work/a0/a1_estimate.json`]

- codex PC: 결정 900–8100 49개 합 14,088.1 s(평균 287.5 s, 최대 448.6 s @2400), 900 전 6개 45.5 s, 결정 밖 3,130.4 s, 전체 17,264 s.
- 이 PC 배수: 결정은 A0 데운 재생 16개의 2.30–2.63배, 빈 PC T=900 은 2.31–2.33배 [실행]. VISSIM 부분은 NC 9000 s 가 codex 2,829 s 대 이 PC 6,005 s(다른 VISSIM 2개와 동시) = 2.12배 [읽음 REPRO_RESULT.md:9-12, raw nc launch.log].
- 어림: 결정 32,365–37,021 s + 앞 결정 105–120 s + 결정 밖 6,645 s = **39,115–43,786 s(10.9–12.2 h)**. 결정 최대 1,031–1,179 s.
- [추론] 이 어림은 A0 재생 때의 부하(다른 세션 학습 포함, CPU 15–61 %)를 깔고 있습니다. 빈 PC 의 T=900 도 2.31–2.33배였으므로 U4(a)로 줄어드는 몫은 크지 않습니다(T=900 에서 588.1 → 534.1 s, 약 9 %). 동시 VISSIM 이 있으면 길어지며, 그 크기는 재지 않았습니다. TAKEOVER_PLAN 의 24–25 h 는 W264 기준이었고, W264 는 다른 설정(cap 캐시 없음)이라 이 계획에서 대체합니다.
- 분석: FZP 스캔·지표 약 1–2 h, 결정 대조 약 1 h [추론].

---

## 7. 자리와 자원

- VISSIM 1자리(동시 상한 4, 메모리 vissim-single-instance-license). 러너는 발사 때 다른 VISSIM 이 있으면 거부합니다.
- 결정마다 python 워커 최대 8(응답) + 8(미분), 주 프로세스 1. 이 PC 20스레드. 메모리 여유 약 100 GB [실행 11:39 KST].
- 디스크: codex joint 원자료 폴더는 913 파일 8.11 GB(FZP 1.05 GB)입니다 [실행 FILE_MANIFEST.csv 합, sealed/ 행 제외]. A1 도 그 정도로 잡습니다 [추론]. 발사 전에 D: 여유를 확인하고 8 GB 아래면 멈춥니다. 지금 D: 281 GB, C: 30 GB [실행 11:42 KST].

---

## 8. 발사 전 점검 (A1 승인 뒤, 차례대로)

1. A1 동결 트리 만들기(`freeze_manifest.py build`), `FREEZE_OK` 확인. 코드 3,638 sha 다시 대조, 복원·대역 목록 sha 대조.
2. 러너 `-PreflightOnly` 로 동결 검사·망 sha·워치독 설정·provenance 확인. 워치독은 이 모드에서 provenance 만 쓰고 아무것도 띄우지 않습니다("nothing is started", watchdog:855-859) [읽음]. 러너도 이 모드에서는 VISSIM 점유 검사를 건너뜁니다(run_closedloop3000.ps1:162-173) [읽음].
3. env 기록: U1·U6 변수, Python 경로·판, 의존성 경로를 발사 기록 파일에 적음(provenance 에 안 남음).
4. 이 PC 에 다른 VISSIM 0 확인(내 것만 셈, 남의 것은 건드리지 않음). 다른 세션 작업은 사용자에게 알림.
5. WMI 분리 발사(U5), 우선순위 기록. 우리 감시 정책은 5분 무진행이면 확인 뒤 kill·재실행입니다(메모리 vissim-watchdog-policy). A0 에서 결정 중 진행 기록 간격은 최대 199 s 라 정상 결정은 5분 안에 기록을 남깁니다. kill 은 소유 PID 만.
6. 런 끝: `STAGE=SIM_DONE`, 결정 49개 exit 코드·유지 수, `.err` 의 remain 줄.

---

## 9. 하지 않은 것

- VISSIM·COM·러너 발사 0, 동결 트리 만들기 0, 커밋·푸시 0. 이 문서는 계획입니다.
- D-K9-83 의 기준을 바꾸지 않았습니다. 바꿀지는 U2 입니다.
