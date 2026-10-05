# K8-6 SA 관문 하네스 (진단 전용)

SC1001 EB 안 1 v2(차로 FIFO 패킷, 모듈 SA)의 관문 G-EB-0…14와 FH 스모크 H-0…H-5(+H-2b)를 계산하는 도구입니다. 런타임 코드가 아니며, 배포 경로는 이 폴더를 import하지 않습니다.

- 구속 문서: `K8_PREDECLARATION.md` §3(3330535b) + 보충 1 r2 §3.0–§3.3(02c7b4d4) + 보충 2 N-A4·N-A9(06c3a73b) + 보충 3 + **보충 5**(342e6d62, 판정 팔 원칙·조작화 13개 확정·장부식 정정·G-EB-13/14 완결 조건·비차단 처리) + **보충 6**(c2664e46, 단위 로그 판정 규칙·포착 출처 대조·G-EB-2/5/13 완결 조건; §2는 보충 7 §1이 대체) + **보충 7**(ad745e9b, 통과 뒤 (a) 갈래 부족분 127 머리 패킷·실패 분류 하나로·계측 유효성과 양성 대조·unit_T11·잡 입력) + **보충 8**(7e4abe34, (d) 갈래 부족분도 127 머리 패킷·SAG 시도 기록 완결·문서) + **보충 10**(d7bcdc9e, T20·G-EB-11(e) 구조 비교에서 K8-2 S3 장부 기록 처리, `sa_s3parity.py`), 명세 `OPT1_V2_SPEC.md`(7a2624a7) + 명세 보충 1 r2(9efd3021), 사용자 결정 D-K8-1(판정 팔 SA-F = `storage observed_full`, SA-G = `geometric`은 보고 팔).
- **판정 팔 원칙(보충 5 §1)**: G-EB-* 판정 항목은 SAF 결과로만 정합니다. BASE는 비교 기준(G-EB-3(c) 짝 증분, G-EB-11 벽시계 비)으로만, SAG는 보고로만 씁니다. 판정 팔 입력이 하나라도 없으면 INCOMPLETE입니다. 예외는 G-EB-2 하나로, 키 있는 모든 팔(SAF·SAG)을 셉니다.
- 규칙은 상위 k8_gates와 같습니다. VISSIM·cscript 실행은 없고, 무거운 작업(●)은 한 번에 하나만 돌립니다. `python -B`, `PYTHONHASHSEED=0`, BELOW_NORMAL(도구가 스스로 낮춤)을 씁니다. 출력은 `--out`(기본 `k8common.DEFAULT_OUT`) 아래 `sa/`이고, 저장소 안이면 거부합니다.
- **이 커밋(K8-0e, K8 head ec063ff = K8-4 런타임 위로 rebase)에서는 `--help`, `--dry-run`, 컴파일, 합성 입력 단위 시험(`tests/test_sa_harness.py`, 보충 10 규칙 시험 (a)(b)(c) 포함), `sa_anchors.py --from-rev 5eef6be`(31곳 모두 앵커 대응, 탐색 대체 0)만 돌렸습니다.** 포착·롤아웃·관문 계산은 아직 한 번도 돌리지 않았습니다.

- **K8-0f(보충 11, 도구 커밋)**: `sa_capture.run_full`의 run.json `objective`는 action JSON `metadata.joint_leader_selection.selected_objective`(`sa_capture.FULL_OBJECTIVE_KEY`, `objective_key`로 기록)입니다. 이전에는 없는 키 `objective`를 읽어 늘 None이었고 G-EB-1 full 2700 비교가 None == None으로 비어 있었습니다. 이제 `sa_compare.py g1`은 두 run이 끝났는데 한쪽이라도 objective·held_objective가 None이면 그 행을 missing(INCOMPLETE)으로 둡니다. 출력 루트는 `--out`/`K8G_OUT`로 줍니다(보충 11 단계: `D:/VISSIM-merge/k8_gates_out_v2`, 기준 트리 사본 `D:/VISSIM-merge/k8_gate_trees/`). 문턱·표본·정의는 바꾸지 않았습니다.

- **K8-0h(보충 13 595eb450, 사용자 결정 D-K8-7, 도구 커밋)**: FH 스모크 H-5 실패(1/45)로 원본 §3.1 끝 대체 규칙이 발동했고, G-EB-3 (a)(b)(c)·G-EB-6 (a)(b)(c)(e) 판정을 **TL3m**(R-obs 시드 {31, 43, 47} × GRID9 = 27상태)으로 옮겼습니다. FH 45상태의 G-EB-3·6 값은 보고만 합니다. 아래 "보충 13: TL3m 대체 판정" 절이 정의·도구·경로입니다. 이 커밋에서 돌린 것은 `--help`·`--dry-run`·`status`(쓰기 없음)와 합성 입력 단위 시험(`tests/test_sa_harness.py`, 새 `tests/test_sa_tl3m.py`)뿐이고, 유효성 검사·포착·잡·관문 계산은 돌리지 않았습니다.

## 단계와 도구

| 순서 | 도구 | 하는 일 | 출력(`<out>/sa/…`) |
|---|---|---|---|
| 0 | `k8_gates/prep.py <T…>` | R-obs3 재생 상태 사본. 필요한 T: GRID9, DP 17, 61상태, H-5의 T±150 | `<out>/replays/<T>/` |
| 0a ● | `sa_tl3m.py validity --seed 31 --seed 43 --seed 47` | 보충 13 R-obs 유효성(아래 절). 무거운 IO(시드당 FZP 약 1.1 GB × 2), 한 번에 하나 | `tl3m/robs_validity_s<S>.json` |
| 0b | `sa_tl3m.py prep --seed 43\|47 [T…]` | 보충 13: 유효한 새 R-obs 런의 재생 상태 사본(기본 61상태, `make_replay_state_v2.prepare`, 복사만). s31은 0의 `<out>/replays/<T>` 그대로 | `<out>/replays/s<S>/<T>/` |
| 1 | `sa_arms.py [--source generate\|repo]` | 팔 튜닝을 만들거나 고릅니다. BASE = 루트 `config_n31_v2.json`, SAF/SAG = `make_config_n31.apply_stopline_approach`. 키 하나만 다른지 확인합니다 | `tuning/arms.json` (+ 팔 파일) |
| 2 ● | `sa_fzp_frames.py 31 41 43 47 53` | FH용 FZP 추출(사슬 26·10771·120 / 74…24, 10479·10491, 31·124; 5 s 프레임 (T−155, T+0.1] + T+150k) | `fzp/s<seed>_frames.parquet` |
| 3 | `sa_vissim_ref.py` | VISSIM 쪽 기준값(정의는 docstring): W+포트, 127 정지, W_out, 127 대기 범위 500 m, 역류 창(F1 §6), EB 방류, 차로 3 만차, EO 셀·10491, R-obs3 | `vissim_ref.json` |
| 4 ● | `sa_capture.py tl3\|dp\|robs61\|fh <arm>` | 대리 Query 틀 포착(+ H_long A1 예보, SDMPC 좌표). `fh`는 FZP 섬 이식(`sa_fh.py`, `--frames 'T-150,T,T+150'`, `--fh-disabled`). 포착 탐침은 장부식 여섯 항(N_127, N_10777, \|A\|, N_tail129, M_other, N_shortfall_kept)을 따로 기록합니다(`sa_identity.py`, 보충 5 §3·보충 7 §1). 보충 8 §1부터 M_other는 (d) 남긴 몫을 뺀 값이고, 10695 위 W 구성원 대기(`rehome_member`)를 따로 적습니다. 보충 13: `tl3`·`robs61`에 `--robs-seed 43\|47`을 주면 그 시드의 R-obs 런에서 포착합니다(유효성 valid 기록 없으면 거부) | `cap/<tree>/<KIND>/<T>[_s][_f]/<arm>/` |
| 4b ● | `sa_capture.py t9c BASE 2700` | T9c 스크래치 투영: BASE 튜닝 + 배포 보강 표 사본에 10695 → SC1001_to_SC2002 한 줄을 더한 표(출력 폴더 `tuning/`에만 씀, 저장소 밖) | `cap/<tree>/T9C/002700/BASE/` |
| 4c ● | `K8_SA_CAPTURE_ROOT=<out>/sa/cap/<tree>` + **한 번의** `run_pytest_bn.py -v` 실행으로 SA 단위 파일 셋(`tests/test_stopline_approach.py`, `tests/test_stopline_wiring.py`, `tests/test_stopline_evidence.py`)과 `tests/test_stopline_approach_captured.py`를 함께 돌려 로그 하나(`> unit_<tree>.log 2>&1`)를 만듭니다 | 단위 항목 T2·T10·T10b·T13과 포착 상태 시험 T3-N7·T6b·T8b·T9b·T9c·T15b(보충 5 §4). T6b·T3-N7·T15b는 SAF TL3 2700 틀로 `sa_worker.py` 롤아웃 1회(H3, A1, 탐침 T3N7·T15b). 변수 없으면 고정 사유로 skip. 포착 상태 시험은 읽은 포착마다 `K8_SA_CAPTURE_PROVENANCE {root, tree, harness, T, arm, template_sha256}` 줄을 로그에 찍습니다(보충 6 §1). `-q`·`-rN`·`-p no:terminal`은 쓰지 않습니다(진행 줄과 요약 줄이 판정 입력) | 단위 로그 → `sa_gates.py --unit-log` |
| 5 ● | `sa_jobs.py <family>` + `sa_worker.py` | 롤아웃 잡(아래 표). 포착 입력(capture.json, template.pickle, 포착 예보보다 긴 H면 forecast_long.pickle과 capture.json의 `forecast_long_len` ≥ H·`forecast_long_prefix_equal` true)이 없는 잡은 띄우지 않고 아무것도 쓰지 않습니다(`SA_JOB_SKIP_NO_CAPTURE`, 검토 r4 B-r4-1, 보충 7 §4) | `jobs/<tree>/<label>/summary.json` |
| 6 ● | `sa_capture.py full <arm> --tag hooks --chain s3site --s3-table <json>` | 배포 결정 전체 + 수동 훅(`sa_hooks/`) | `full/<tree>/<T>_<arm>_hooks/` |
| 7 | `sa_anchors.py --from-rev 5eef6be` (K8-2) | K8-0b S3 31곳 표를 이 트리 줄로 다시 고정(git show + difflib, 앵커 문구 확인) | `anchors/s3_table_<head>.json` |
| 8 | `sa_hookcount.py` | 훅 집계: S3 31곳, SA 접기 자리 4곳, W 구성원 용량 읽기(모듈:함수, 분류표 CLASSIFY) | `hooks_<tree>.json` |
| 9 | `sa_compare.py g1\|g9\|h0\|h4` | 숫자 필드 비교(p3_compare 규칙, 타이밍 제외) | `compare/*.json` |
| 10 | `sa_smoke.py` | H-0…H-5(+H-2b), G-EB-3 사전 제외 목록(N5) | `gates/smoke_<tree>.{json,md}` |
| 11 | `sa_gates.py --evidence-log … --unit-log <4c 로그> [--unit-log <다른 로그> …] [--leader-review …]` | G-EB-0…11, 13, 14와 §3.3 결합(PROMOTE_ELIGIBLE / STOP / INCOMPLETE). `--unit-log`는 여러 번 줄 수 있습니다(SA 단위 로그와 포착 상태 시험 로그를 따로 돌렸을 때). 판정 규칙은 아래 "단위 로그 판정 규칙" | `gates/gates_<tree>.{json,md}` |

## 잡 묶음 (`sa_jobs.py`)

| family | 잡 | 관문 |
|---|---|---|
| `tl3` | TL3 9 T × {OBS, A1} × 팔, H3. SA-G는 OBS만 | G-EB-1(BASE, 두 트리)·3(d)·4·10·11 |
| `long` | 900 H24, 2700 H42, 4950 H27 × {OBS, A1}, segment 6 (BASE·SAF) | G-EB-5·7 |
| `c11` / `tan` | C00·C11·C12 3블록 계획 / 대리 역방향 AD + FW_W(T+450) 테이프 스윕 (BASE·SAF) | G-EB-8 |
| `dp` | DP 17 T, H1 A1 (BASE·SAF) | G-EB-3(d)·10 |
| `fh` | 5시드 × 9 T, H3 OBS + FD7 + FD5, 사건 상태는 H6(SA-G는 사건 14 H6만) | G-EB-3·6·10·11 |
| `--hooks` | 훅 잡은 라벨 변이 `HOOK`(예 `TL3_2700_SAF_OBS_H3_HOOK`). 일반 TL3 잡을 대신하거나 건너뛰지 않음. G-EB-13 판정 잡은 `TL3_2700_SAF_OBS_H3_HOOK`로 고정(`sa_jobs.py tl3 --hooks --T 2700 --arms SAF`, 보충 6 §3). 그 밖의 TL3 SAF 훅 잡이 있으면 모두 같은 기준(plant 읽기 0)으로 함께 판정하고, SA 훅 기록이 없는 잡(`sa_files 0`)은 INCOMPLETE로 셉니다 | G-EB-13 |

- **SA-G 자리(보충 5 §1, 보충 1 r2 §3.0)**: FH 사건 14상태 H6과 TL3 9상태 H3 OBS뿐입니다. `sa_jobs.py`는 다른 자리의 SA-G 요청을 거부합니다(`sa_common.sag_allowed`).
| `h0`·`h3`·`h4`·`h5` | 스모크 잡 | H-0·H-3·H-4·H-5 |
| `adfull` | 2700 REF·M2ALL 비대리 AD(`state_error`, 보충 10 S3 규칙 래퍼 `sa_s3parity` 경유, summary `s3_parity`) | G-EB-11(e) |
| `tl3m` | 보충 13: R-obs 시드 31·43·47(`--seeds`, 기본 31,43,47) × 9 T, BASE·SAF H3 OBS + SAF H6 OBS(그 시드의 VISSIM 사건 상태). 각 시드 자기 배포 틀(`tl3 --robs-seed S`), OBS 진입 = 그 시드 EO. s31 H3 라벨은 `tl3`의 라벨 그대로. 유효성 invalid 시드는 계획에서 빠짐. SAG 없음 | G-EB-3·6(판정), G-EB-4 s43·s47 보고 |

## 보충 13: TL3m 대체 판정 (K8-0h, `sa_tl3m.py`)

구속: `K8_PREDECLARATION_AMENDMENT_13.md`(sha 595eb450…), 사용자 결정 D-K8-7(새 R-obs 2런 s43·s47). 조작화는 `sa_common.OPERATIONALISATIONS`의 'TL3m sample', 'R-obs validity', 'G-EB-3 TL3m', 'G-EB-6 TL3m', 'G-EB-14 R-obs seeds', 'G-EB-2 TL3m', 'G-EB-4/5/7/8 TL3m'에 코드 상수로 고정했습니다(관문 결과 0개인 시점).

- **표본**: R-obs 시드 {31, 43, 47} × GRID9 = 27상태. 각 시드 자기 R-obs 런의 배포 틀(이식 없음), 진입 OBS(그 시드 EO `s<S>_v3c2nc`, FH 관례). VISSIM 쪽은 `vissim_ref.json`의 그 시드 상태(같은 시드 v3c3 NC FZP의 x2 추출, T+0.1·T+150.1 프레임). 사건 분류는 p4 958275ac(`vissim_ref.json` inputs.p4 sha 앞 8자 확인), 시드별 사건 5/4/3·비사건 4/5/6(합 12/15)이 아니면 INCOMPLETE.
- **R-obs 유효성**(`sa_tl3m.py validity`, 구속): (1) `<runs root>/wmi_<name>.log`의 마지막 `EXIT <name> code=<n>`이 0. EXIT 줄이 없으면 `not_finished`이고 **런 폴더는 읽지 않습니다**(진행 중인 런을 건드리지 않음). (2) `decisions_<name>/`에 61상태 state·action 파일(다른 state 없음), runlog `DECISIONS_OK=61`·`DECISIONS_FAILED=0`·`STAGE=SIM_DONE`. (3) GB-6 방식 FZP 대조(`gb6_result.json` c1–c3, P10 `pair/fzp_bytecompare.py` 분할): 헤더는 `* File:`·`* Date:` 줄만 다름, R-obs의 5.1 s 앞 데이터 줄은 0.10 s 프레임뿐이고 NC는 없음, 나머지는 바이트 동일, 크기 차 = 헤더 차 + 0.10 s 바이트. 하나라도 거짓이면 `invalid` → 그 시드는 판정 표본에서 빠지고 보고합니다. 입력 파일이 없으면(`runlog`, NC FZP, wmi 로그) `error`. 판정에는 시드마다 `valid` 기록이 필요하고, 기록 없음·`not_finished`·`error`는 INCOMPLETE입니다. s31도 같은 검사를 받습니다(GB-6에서 이미 PASS, 기록 형식 통일). `valid`·`invalid` 기록은 다시 돌려도 그대로 두고(`--recheck`이면 `.stale_<k>.json`으로 옮긴 뒤 다시 씀), 그 밖의 기록은 덮어씁니다.
- **경로**: s31의 TL3·ROBS61 폴더와 라벨은 그대로(태그 없음). s43·s47은 `cap/<tree>/TL3/<T>_s<S>/<arm>`, `cap/<tree>/ROBS61/<T>_s<S>/<arm>`, 잡 `TL3_<T>_s<S>_<arm>_OBS_H<H>`, 재생 `<out>/replays/s<S>/<T>`, 유효성 `<out>/sa/tl3m/robs_validity_s<S>.json`. 포착은 `--robs-seed S`로 그 런의 결정·provenance·이전 행동을 읽고, 재생 manifest의 `source_decisions`가 그 런이 아니면 자식 프로세스를 띄우기 전에 거부합니다. TL3m 잡은 그 런의 provenance env로 돕니다(`sa_common.base_env_for`).
- **G-EB-3**(판정 팔 SAF, H3 OBS, 블록 1 = T+150): (a) 모형 W+포트 대 FZP T+150.1의 32+10778+129+10777+127+10491+10481, |평균 편향| ≤ 50 그리고 MAE ≤ 같은 27상태 FZP persistence MAE. (b) G6-7: 블록 1 W 준비 대 FZP 127 정지(< 5 km/h), |b| ≤ 20·r ≥ 0.5. (c) 10491·10481 포트 |오차| 짝 증분(SAF − BASE, BASE H3 OBS 비교 기준), iid(상태)·시드 군집(3시드) 부트스트랩 각 2,000회(rng 0), 네 하한 모두 ≤ 0. (d) 원본 그대로(DP 17·TL3 s31 9). H-5 사전 제외·N5는 FH 전용이라 FH 보고 행(`FH_report`)에만 적습니다. B1 단서(BASE 10695 재도착 질량)는 TL3m BASE 틀과 FH 둘 다 보고합니다.
- **G-EB-6**(SAF): (a) 27 H3 + 사건 12 H6 잡의 10481 차단 스텝 = 0. (b) 비사건 15상태 중 [T, T+450](H3 잡)에 10491 차단 상태 ≤ 3. (c) 차단한 사건 상태마다 H6 첫 차단 ≥ VISSIM 127 대기 500 m 첫 시각 − 30 s(못 닿으면 +inf). (e) 사건 12상태 중 [T, T+450] 차단 ≥ 6. (d) 적중 시각 오차 보고. BASE 10481은 보고, TL3 s31 SAG는 보고, FH 45/14 값은 `FH_report`.
- **G-EB-14**: (i)는 유효한 R-obs 시드마다 포착 가능 상태로 판정(+ FH 45 그대로). T = 1·150의 SAF 포착이 같은 시드·T의 BASE 포착과 같은 위치·같은 예외로 실패했으면(둘 다 자식 실패 기록, 어댑터 `action_<T>.error.txt` 또는 기록의 error에서 `sa_errors.traceback_signature` = 예외 줄 + 런타임 프레임 경로(런타임 폴더부터의 파일, 줄, 함수)가 같고 런타임 프레임 ≥ 1) 보고하고 표본에서 뺍니다(보충 9 선례). 그 밖의 실패는 기존 포착 행 규칙. (ii)(iii)는 판정 시드의 ok ROBS61 포착 + FH. 각 시드 BASE 포착 T = 1·150이 필요합니다(`robs61 BASE 1 150 --robs-seed S`; s31은 이미 있음).
- **G-EB-2**: 선언 목록에 tl3m SAF 잡(H3 OBS·사건 H6 OBS)과 그 틀 폴더, invalid가 아닌 R-obs 시드의 ROBS61 61 SAF 포착을 넣습니다. 하네스 해석: 같은 폴더의 T = 1·150 BASE 동일 실패는 `unreadable`이 아니라 보고 행 `robs_identical_to_base`입니다(G-EB-14 규칙을 같은 폴더에 적용).
- **G-EB-4·5·7·8**: 원본대로 TL3 s31 판정. G-EB-4는 TL3m H3 잡으로 s43·s47을 보고(`TL3m_s43_s47_report`, VISSIM = 그 시드 FZP FW_W 사슬 T+450.1 대수). G-EB-5·7·8의 s43·s47 보고는 long·C00·C11·TAN 잡과 시드별 EO 기준값이 TL3m 잡 목록 밖이라 "not computed"로 적습니다.
- **메인 세션 확인이 필요한 하네스 해석**(보충 13 본문에 직접 쓰이지 않은 것): (1) 시드가 빠질 때 (b)/(e) 문턱은 선언 비율(floor(0.2 × 비사건), ceil(0.5 × 사건))을 남은 상태에 적용, (2) G-EB-2의 T = 1·150 BASE 동일 실패를 보고 행으로 둠, (3) N5를 FH 보고로 내림, (4) s31도 유효성 기록 필요, (5) G-EB-5·7·8 s43·s47 보고 미계산.
- **실행 순서**: `sa_tl3m.py validity`(seed 31·43·47, 하나씩) → `sa_tl3m.py prep --seed 43`·`47` → `sa_capture.py tl3 BASE|SAF --robs-seed S`, `robs61 SAF --robs-seed S`, `robs61 BASE 1 150 --robs-seed S` → `sa_jobs.py tl3m`(s31 H3는 이미 있는 tl3 잡을 건너뜀, s31 사건 H6 5개는 새로 돔) → `sa_gates.py`. `sa_tl3m.py status --tree <tree>`가 시드별로 있는 것을 보여 줍니다(쓰기 없음).

## 보충 10: 구조 비교의 K8-2 S3 장부 기록 (`sa_s3parity.py`)

- 쓰는 곳: T20(`tests/stopline_tangent_probe.py parity`)과 G-EB-11(e)(`sa_worker.py` ad_full이 `sdmpc_tangent_state.state_error`를 이 프로세스 안에서만 `sa_s3parity.compare`로 감쌈). 런타임 비교기와 `evaluation/` 파일은 바꾸지 않습니다. 비교기가 ValueError를 낼 때만 뺄 기록을 제자리에서 빼고 같은 객체로 비교기를 다시 부른 뒤, 값·순서 그대로 되돌립니다.
- 빼는 기록(전부 만족할 때만): (1) 장부 `flow_counts`(어디 있든 `ModelAreaLedger`의 것, 또는 T20 스냅숏의 `flow_counts`)에서 탄젠트 런에만 있는 키, (2) 그 값의 원시값이 정확히 0.0, (3) 그 키를 만든 호출이 K8-2 S3 문(`count == 0 and not has_tape(count)`)만 통과시키는 `ModelAreaLedger.transfer`(금액 원시값 0.0 + 테이프), (4) 그 호출 때 `stopline_approach.py` 프레임이 스택에 없었고, SA가 만든 S3 호출이 같은 키를 만들지 않음.
- 자리 판정(호출 자리 계측): 여섯 S3 자리는 K8-2 원문(정확히 1회, `test_k8_s3_has_transfer.py`의 K8-2→K8-1 표)으로 이 트리 줄을 찾고 보충 10의 K8-2 줄 번호(PRB-bd :307/:332/:370, CAO :608, AFA :247/:393)로 보고합니다(이 트리: PRB :405, CAO :610). 장부에 기록을 쓰는 자리는 CAO :608 하나입니다. PRB는 램프 패킷, AFA는 고속도로 값을 만들 뿐이고, 그 원시값 0 테이프 값은 뒤의 transfer 호출로만 장부에 닿아 CAO 문을 지납니다. 그래서 `ModelAreaLedger.transfer`(클래스 속성, 이 프로세스·메모리만)를 감싸 원시값 0.0 + 테이프 호출마다 만든 키, 덧붙인 응답 행, 내보낸 프레임(`control_area_objective.py`와 이 모듈 밖 첫 프레임, file:line), SA 프레임 유무를 기록합니다. 자리별 계수는 장부 문 자리 기준(CAO:608만 0이 아닐 수 있음, 나머지 다섯은 0으로 나열)과 내보낸 자리 기준 두 가지입니다. 원시값·테이프는 속성으로만 읽습니다(Dual 비교·분기 사건 없음).
- 같은 원장의 transfer 행(`_response['transfers']`, 묶음·압축 행)은 런타임 비교기가 이미 (stage, start, end, source, target, route_key)로 묶어 없는 묶음을 0으로 읽으므로 원시값 0 탄젠트 전용 행은 같게 나옵니다. 빼지 않고 `s3_rows`로 셉니다. 응답을 잡지 않는 장부는 event_count를 필드로 비교하므로 거기서의 S3 호출은 수치 차이로 남아 FAIL입니다(선언대로).
- FAIL: SA가 만든 S3 호출(`sa_created` > 0, 새 키를 만들지 않았어도), 규칙 밖 키(다른 자리, 원시값 ≠ 0, 스칼라 전용 키), stocks 키·길이 차이, 다시 부른 비교기의 예외(런타임 traceback). G-EB-11(e)는 summary의 `s3_parity`(설치됨, 래퍼 통과 비교 ≥ 1)가 없으면 INCOMPLETE입니다. 행에 뺀 기록 수, 자리별 계수, SA 생성 수를 싣습니다.
- 모듈은 탄젠트 finder보다 먼저 import해야 합니다(변환되지 않은 채로 돌아야 함; 변환되면 import가 거부).
- 규칙 시험(`tests/test_sa_harness.py`, 실제 CAO·SA 코드, 정방향 탄젠트 런타임, 경우마다 새 프로세스): (a) S3 자리 기록만 다름 → 통과 + 계수 1(CAO:608, 내보낸 자리), (b) 같은 모양을 SA 자리(`stopline_approach._internal`)가 만듦 → FAIL(새 키면 비교기 예외, 기존 키면 `sa_created`만으로), (c) 다른 자리(장부 문 밖에서 `flow_counts`에 직접 씀) → FAIL, 덧붙여 (d) S3 호출이 새 stocks 키를 만듦 → FAIL, (e) 원시값 ≠ 0 탄젠트 전용 키 → FAIL.

## FH 이식 설계 (`sa_fh.py`)

- 이식은 포착 어댑터 프로세스 안에서 `lane_plant_runtime.observe_state`가 돌려준 (병합 상태, 차로 관측) 위에서 합니다.
- 그 뒤 단계는 **배포 코드가 배포 순서로** 수행합니다: `bind_current_routes` → 투영(K8-4 S5 시드·`storage_seed_split_by_link`·짝 예약) → `lane_plant_runtime.initialize`(`bin_frame`, `DelayedPort`) → `SA.initialize`(FZP 기록·경로 열) → `area_runtime.configure`(`seed_from_projection`).
- 선언 1–9단계와 FD1–FD8의 대응은 `sa_fh.py` docstring 표에 있습니다. 진입 OBS(FD2)·게이트 수요(FD7)·VSL 110(FD5)은 잡에서 겁니다.
- 이식한 링크는 FW 두 사슬, 포트 10491·10481, 섬 32·10778·129·10777·127·10695입니다. FZP 차량 번호는 +50,000,000으로 바꿔 충돌을 막습니다.
- FW_W 진출 분율(FD3)은 10491·10479만 바꿉니다. 정의는 obs150 off_split과 같습니다: 진출 / (진출 + from_cell 끝 통과).

## 훅 (`sa_hooks/sitecustomize.py`)

- `K8_SA_CHAIN_SITE`로 기본 사이트(`site/` 또는 K8-0b `s3site/`)를 먼저 실행합니다.
- `K8_S3_TABLE_JSON`이 있으면 s3site의 표 선택 블록(정확한 문구, 1회)만 메모리에서 바꿉니다. 그래서 S3 훅 기계는 그대로입니다(N-A9 "같은 훅").
- SA 접기 자리 네 함수는 `PY_START`·`PY_RETURN`으로 봅니다. 자코비안 시작 때 정방향 스윕 1회로 "정확 ≠ 0"과 "버린 탄젠트"를 셉니다.
- `_movement_capacity_flow` 호출과 `cap_flow_of[`·`movement_capacity_by_movement_veh_h` 줄 실행 가운데 W 구성원에 해당하는 것을 호출 사슬별로 셉니다(G-EB-13).
- 처리기 예외는 계수를 버리고 `hook_errors`만 올립니다. 그래서 G-EB-13은 판정 run마다 계측이 유효해야 판정합니다(검토 r3 B-r3-4, `sa_gates.g13_instrument_problems`). 조건: `hook_errors`·`patch_errors` 0, SA 훅 오류 목록 비어 있음, setup·chain 오류 파일 없음, 설치 목록에 `urban_queue_model._movement_capacity_flow`, 그리고 코드 루트의 plant 모듈 소스(`sa_hookcount.PLANT_MODULES`) 가운데 용량 토큰 줄이 n > 0인 모듈마다 `<모듈>:n lines` 줄 패치. 하나라도 어긋나면 INCOMPLETE이고, plant 읽기 > 0은 그대로 FAIL입니다. `sa_hookcount.py`가 설치 목록(`fold_extra.patched`)을 모으고 기대 줄 수(`line_patch_expected`)를 기록합니다. 지금 트리의 다섯 plant 모듈은 토큰 줄이 0이라, plant 읽기는 `_movement_capacity_flow` 패치로만 잡힙니다.
- 보충 7 §3: G-EB-11(d)·G-EB-13은 같은 run의 S3(또는 site) 훅 파일 `hook_errors`·`patch_errors` 0·`errors` 없음, SA 접기 훅 오류 0, **훅 파일 전부 final 기록**(`sa_hookcount`가 파일별 `final`을 `non_final`·`final_files`로 모음), setup 오류 없음이 필요합니다(`sa_gates.hook_run_problems`). 아니면 INCOMPLETE입니다.
- 양성 대조(보충 7 §3): BASE full 2700·4950의 W 구성원 용량 plant 읽기가 둘 다 > 0이어야 G-EB-13을 판정합니다(`base_plant_reads_control`, 판정 항목). 없거나 0이면 INCOMPLETE입니다.
- G-EB-11(d)(보충 7 §2·§3): S3 집계가 유효(31곳 이상, 앵커 불일치 없음, 모든 곳 패치)하지 않으면 INCOMPLETE입니다. 유효하면 정확 ≠ 0 사건이나 버린 접기 탄젠트는 FAIL입니다. 그 밖에는 위 계측 조건, run 완결(run.json exit 0·action JSON), SA 접기 자리 설치(`stopline_approach`), 접기 자리 `ev_unevaluated` 0(재지 못한 사건 없음)이 모두 있어야 PASS이고, 아니면 INCOMPLETE입니다.
- 훅은 final 기록을 프로세스 종료 때(atexit) 씁니다. 그래서 롤아웃 전에 죽은 run도 "패치됨·오류 0·plant 읽기 0" 기록을 남깁니다. G-EB-13은 판정 run마다 끝까지 돌았는지도 봅니다(검토 r4 B-r4-2, `sa_gates.g13_run_problems`). full 결정은 `full/<tree>/<T>_SAF_<hooks-tag>/run.json`의 exit 0과 action JSON(`action_json_bytes` > 0), 훅 잡은 summary의 ok true와 `sa.end_step_calls` > 0이 필요합니다. 아니면 INCOMPLETE이고, plant 읽기 > 0은 그대로 FAIL입니다.

## G-EB-14 포착 행 읽기 (검토 r4 B-r4-3)

- `sa_cap_child`는 탐침 블록이 예외를 내도 포착을 ok로 남기고 `probes_error`만 적습니다. adapter `main` 프레임을 못 찾으면 `metadata`도 쓰지 않습니다.
- (i): ok인데 `metadata` 블록이 없는 포착은 하네스가 못 읽은 것이라 INCOMPLETE입니다. `metadata`는 있는데 `stopline_approach_install_check`가 없으면 초기화 실패(FAIL)입니다. 실패한 포착은 child가 런타임 traceback을 기록했을 때만 FAIL이고, 아니면 INCOMPLETE입니다(보충 7 §2).
- (ii)(iii): 탐침(`probes`, `probes_error` 없음), `metadata.stopline_approach_initial.posthead_veh`·`posthead_receiver_shortfall_veh`·`posthead_rehome_shortfall_veh`, `probes.records.n10695`가 모두 있어야 그 행을 판정합니다. 하나라도 없으면 그 행은 INCOMPLETE입니다. 기본값 0을 읽지 않습니다.
- (ii): 127 수신 provenance = `posthead_veh` − (`posthead_receiver_shortfall_veh` − `posthead_rehome_shortfall_veh`)(보충 7 §1: 수신 여유를 넘는 (a) 몫은 127 머리 준비 패킷으로 남음).
- (ii): 10695의 SC1001_to_SC2002 몫 + `posthead_rehome_shortfall_veh` = 10695 차량 수, 10695 위 W 구성원 대기 = `posthead_rehome_shortfall_veh`(보충 8 §1: 남은 여유를 넘는 (d) 몫은 차로 3 머리 준비 패킷, provenance는 10695 위 N 대기). `posthead_receiver_shortfall_veh`는 (a)+(d) 합계이고, 보고 항목 `posthead_shortfall_report`는 합계와 (d) 몫(`kept_10695_veh_total`)을 함께 셉니다.

## 실패 분류 (보충 7 §2, `sa_errors.py` 하나)

- 종류(kind): `StoplineInvariantError` invariant, `StoplineRouteError` route, `StoplineInitError` init, `StoplineConfigError` config, `assert_stocks`·`Ledger` stocks, 그 밖 other. 워커(`sa_worker`)·포착 child(`sa_cap_child`)·부모(`sa_capture`)·관문이 모두 이 표 하나를 씁니다(검토 N-r4-2).
- 자리(site): child가 기록한 traceback에서 가장 안쪽의 프로젝트 프레임. `evaluation/`·`vendor/`·런타임이 import하는 `diagnostics/` 모듈(metanet_calibration_v1, capture_native_runtime_errors)은 runtime, `k8_gates/` 아래(워커, 포착 child, FH 이식, 훅 사이트)는 harness, 표준 라이브러리·설치 패키지는 건너뜁니다. child는 전체 traceback으로 `error_kind`·`error_site`를 직접 기록합니다. 포착 child는 틀 뒤 하네스 단계(forecast_long, coord, 기록 쓰기)의 예외를 `harness_stage_error`로 표시합니다.
- **SAF는 runtime traceback이 있는 실패만 FAIL**입니다. 죽음(child 기록 없음), 입력 없음, 시간 초과, 부모만 쓴 기록, 탐침·하네스 예외, traceback 없음은 INCOMPLETE(다시 돌릴 대상)입니다. full 어댑터 run은 run.json exit 0 + action JSON이면 끝난 것이고, 아니면 adapter_log.txt를 끝낸 traceback의 자리(`sa_errors.log_error_site`, run.json `error_site`)로 가릅니다.
- G-EB-1(보충 7 §2): 비교하는 두 run 가운데 하나라도 끝나지 않았으면(없음, 죽음, 입력 없음, runtime traceback 없는 실패) INCOMPLETE, 둘 다 끝났는데 한쪽만 실패하면 FAIL, 둘 다 실패하면 INCOMPLETE(같음을 읽을 수 없음)입니다(`sa_compare.pair_state`). `unit_T11`은 G-EB-9와 같은 규칙입니다(missing 행 또는 행 수 ≠ 17 → INCOMPLETE, 검토 B-r5-1).
- G-EB-11(e)·G-EB-14 (i)·H-2도 같은 분류를 씁니다.

## G-EB-2 읽기 규칙 (보충 5 §1·보충 6 §3·보충 7 §2, 검토 r3 B-r3-2·B-r3-3, r4 B-r4-1)

- 불변식 위반(invariant·route·stocks가 runtime 코드에서 난 것, SAF 포착은 init도)은 SAF·SAG 어느 팔이든 FAIL입니다.
- SAF: 그 밖의 runtime 실패(`other_failures`)와 SA.end_step 0 잡은 FAIL, runtime traceback 없는 실패는 `unreadable_runs`(INCOMPLETE)입니다.
- SAG(보고 팔): 불변식 위반이 아닌 실패(other·init·config, traceback 없음, killed, 입력 없음)와 SA.end_step 0 잡은 `sag_reported`(판정하지 않는 보고 항목)에 적고 **G-EB-2 완결을 막지 않습니다**. 시도 기록(summary.json 또는 capture(_failed).json)이 있으면 있는 것으로 셉니다.
- SAG 포착이 실패해 `sa_jobs`가 그 SAG 잡을 띄우지 않았으면(summary.json 없음, `job_inputs_missing` 비어 있지 않음), 그 틀 폴더의 시도 기록으로 그 잡도 "있음·보고"(`sag_reported`, `not_started`)로 셉니다(보충 8 §2, 검토 N-r6-2, `sa_common.sag_capture_attempt`). 시도 기록은 실패한 포착(capture.json ok false, 또는 capture_failed.json — killed 포함)과, ok 포착이지만 자기 기록으로 그 잡을 받칠 수 없는 경우(`forecast_long_len` < H 또는 `forecast_long_prefix_equal` 아님, 파일은 있음)입니다. 뒤의 경우는 기록이 그렇게 말할 때만입니다(검토 r8 N-r8-1): `ok`가 true이고 두 필드가 모두 기록됨(`forecast_long_len` 숫자, `forecast_long_prefix_equal` bool). 필드나 `ok` 키가 없으면 실패 기록이 아니므로 그 라벨은 없음(INCOMPLETE)입니다. 포착 입력이 다 있는데 아직 안 돈 SAG 잡, ok 포착인데 파일(template.pickle·forecast_long.pickle)이 없는 SAG 잡(미완 폴더, 다시 돌림), 포착 기록이 아예 없는 SAG 잡, SAF 잡은 그대로 없음(INCOMPLETE)입니다. SAG 포착의 불변식 위반은 그대로 FAIL입니다.
- 포착 폴더에 capture.json이 있으면 그것만 읽고, 옆의 capture_failed.json은 낡은 기록으로 무시합니다. 읽은 기록이 잘렸거나 JSON 객체가 아니면 그 폴더는 `unreadable_runs` 행(INCOMPLETE, 다시 포착)으로 보고서에 남습니다(검토 r8 N-r8-2, 팔 무관). `sa_capture.py`는 새 시도 전에 이전 capture_failed.json을 `stale_capture_failed_<k>.json`으로 옮깁니다(어느 관문도 읽지 않음).
- child가 쓴 기록(schema `k8-sa-capture/v1`) 없이 부모만 쓴 실패는 `killed`입니다. G-EB-2에서는 unreadable, G-EB-14 (i)와 모든 `I.cap` 독자에게는 포착 없음으로 처리해 INCOMPLETE입니다. 잡이 죽었을 때(summary.json 없음)와 같은 취급입니다.
- 포착 입력이 없는 잡(검토 r4 B-r4-1)
  - `sa_jobs.run_job`은 포착 입력(`sa_common.job_inputs_missing`)이 없으면 워커를 띄우지 않습니다. 라벨은 없는 채로 남아 INCOMPLETE입니다.
  - 이미 쓰인 summary가 자기 template.pickle·forecast_long.pickle의 FileNotFoundError로 끝났으면(`sa_common.job_input_absent`) SA 코드를 읽은 결과가 아닙니다. G-EB-2는 팔과 상관없이 unreadable로, 다른 모든 독자(`I.job`, `sa_compare`)는 잡 없음으로 읽습니다. FAIL이 아니라 INCOMPLETE입니다.
  - 입력이 생긴 뒤 `sa_jobs.py`를 다시 돌리면 그 summary를 `stale_input_absent_<k>.json`으로, hook/을 `stale_hook_<k>/`로 옮기고 잡을 다시 돌립니다. 다른 summary는 지금처럼 건너뜁니다.
- 포착 기록은 child가 임시 파일에 쓴 뒤 `os.replace`로 바꿉니다(검토 r4 N-r4-4). 쓰다 죽어도 잘린 JSON이 남지 않고, 기록 없음(killed)이 됩니다.

## 단위 로그 판정 규칙 (보충 6 §1, `sa_gates.parse_unit_log`·`unit_item`)

- 대상: G-EB-1 T2(`KeyAbsent`)·T10(`ContiguousWalk`)·T10b(`PostService`), G-EB-11 T13(`Tangent`), G-EB-14 T9b·T9c(`test_stopline_approach_captured.py::T9b`·`::T9c`).
- 행: pytest 9 `-v` 진행 줄(`<nodeid> PASSED [..%]`). 출력이 끼어들어 상태 단어가 다음 줄에 찍히면 마지막으로 시작한 nodeid에 붙입니다.
- 실패: **요약 줄이 정본**입니다. `^(SUBFAILED|FAILED|ERROR)([…]|(…))? <nodeid>`가 하나라도 있으면 그 항목 FAIL. unittest subTest 실패는 진행 줄이 PASSED로 남기 때문입니다(pytest 9.1.1에서 확인).
- 세션 요약 `N failed`·`N errors`를 요약 줄의 nodeid에 다 귀속하지 못하면(예 `-rN`) 또는 세션 요약 줄이 없으면, 그 로그에 행이 있는 항목은 INCOMPLETE.
- 모든 단위 항목은 PASSED ≥ 1, SKIPPED 0이 필요합니다. 행이 없으면 INCOMPLETE(FAIL 아님). 이름만 준 로그 파일이 없어도 INCOMPLETE.
- T9b·T9c는 추가로 포착 출처를 대조합니다. 로그의 `K8_SA_CAPTURE_PROVENANCE` 줄이 모두 `<out>/sa/cap/<tree>`(같은 tree 이름)를 가리키고 그 트리 capture.json의 `template_sha256`과 같아야 하며, T9b는 TL3 BASE, T9c는 TL3 BASE + T9C BASE 줄이 있어야 합니다. 다르면 INCOMPLETE(예: 장난감 포착 `sawip/fakecap` 로그).
- T9b·T9c의 등가 단언은 subTest 밖에 있어 실패가 진행 줄에도 FAILED로 찍힙니다.
- 하네스 시험은 설치된 pytest 9.1.1을 실제로 돌린 출력(통과, subTest 실패, 일반 실패, `-rN`, 행 누락, skip, 다른 포착 루트, 여러 로그)으로 이 규칙을 확인합니다(`tests/test_sa_harness.py`).

## 하네스 조작화 (선언이 비워 둔 세부, 결과 전에 코드 상수로 고정)

`sa_common.OPERATIONALISATIONS`에 있습니다. 관문 보고서(`gates_<tree>.md`) 끝에 그대로 실립니다. 관문 실행 중에는 바꾸지 않습니다. 바꾸려면 새 도구 커밋이 필요합니다(보충 2 N-A8).

## 명세와 다른 구현 — 편차표 (보충 5 §3·§5·§6에서 승인·고정)

| # | 무엇 | 근거 |
|---|---|---|
| D1 | 시험 위치 `tests/` → `diagnostics/sdmpc_n31_20260924/tests/` | 보충 5 §5 |
| D2 | 연결점 #0(UFA view 줄)·#10b(UFA `end_step`) 추가 | 보충 5 §5 |
| D3 | `_post_service`에 `routing` 인자. 보충 5 N-4로 **수신 링크 문자열도 인자**(호출자의 `str(spec.get('receiving_link',''))`). 키 없는 출발 루프는 `movement_specs`를 더 읽지 않음 | 보충 5 §5·N-4 |
| D4 | install_check 추가 거부: 127·10777 원천, 10777 투영 없음, 옮기는 잔차의 K8-4 seed 행, 다른 off-ramp 행의 in_SC1001_W 방출, `shared_city_arrival.receiver`. 보충 5 N-8로 `urban.queue.origin_binding` 켜짐도 거부(129 꼬리 이중 계상 방지) | 보충 5 §5·N-8 |
| D5 | `depart`(dequeue + 이전) 묶음 함수 | 보충 5 §5 |
| D6 | `posthead_lane_prior`를 차로 신호군 목적지로 제한(차로 2 0.992/0.008) | 보충 5 §5 |
| D7 | make_config의 stopline 플래그와 `--urban-batch1`·`--out-root`·distribution 계열 조합 거부 | 보충 5 §5 |
| D8 | 스텝 진단 20 숫자 키(`np_off_ramp_veh`는 port_release 두 키 합이라 제외) | 보충 5 §5 |
| D9 | **장부식 정정(B-3)**: Σ_l stock_l = N_127 + N_10777 − \|A\| + N_tail129 + M_other + N_shortfall_kept(±1e-9). T8 합성 사례: 13 + 1 − 3 + 1(129 @260 m 1132:2 꼬리) + 0 + 0 = 12 = 준비 5 + 이동 6 + 꼬리 1. 옛 목표식(=11)은 폐기. N_shortfall_kept = `posthead_receiver_shortfall_veh`((a)·(d) 두 갈래 합, 보충 7 §1·보충 8 §1). (d) 몫은 10695 provenance에 N 대기로 남으므로 탐침의 M_other는 그 몫(`posthead_rehome_shortfall_veh`)을 뺀 값 | 보충 5 §3, 보충 7 §1, 보충 8 §1 |
| D10 | `stopline_lane_room` 자원 기록 값은 room_l이 아니라 포트의 차로 배분 alloc_p,l(두 포트가 room을 나눔). 새 kind는 GB-7′ A_K8 규칙 1(`sa_common.A_K8_SA`, P10의 `gb7_allowed.py`가 아직 없어 여기 둠) | 보충 5 N-3 |
| D11 | 다른 링크 질량(§5.8-6) 출신 표지: 32·10778 = `init:city`, 그 밖(129·10777 등) = `init:unknown` | 보충 5 N-11 |
| D12 | 통과 뒤 (a)·(d) 갈래 모두 수신 여유 부족을 거부하지 않음("Posthead rehome overfills" 삭제). **규칙 (A)**: 수신 여유 안의 몫만 `_post_service`로 수신 링크에 기록(수신 저장은 0 밑으로 가지 않음). 넘는 몫은 그 차량이 지난 127 차로의 **머리 준비 패킷**(due = 초기화 시각, 출신 표지 그대로)으로 남기고, 그 차로가 상한을 넘으면 그 차로 `init_excess`(I3는 init_excess 만큼 완화). 그 차로가 경로상 목적지를 받지 못하면(예: 차로 1의 N) 남긴 몫은 목적지를 받는 차로의 머리 준비 패킷이 되고 `lane_reassigned_veh`에 더함(검토 N-r6-3). **(d) 커넥터 재배치(10695 → SC1001_to_SC2002)**: (a)가 같은 수신 여유를 먼저 쓰고, 커넥터의 in_SC1001_W 몫 a_c 가운데 fit = min(a_c, 남은 여유)만 수신 링크로 옮기며 투영 예약 칸(+15/+105)도 fit/a_c 만큼만 옮김. 나머지는 목적지(N)를 받는 차로(차로 3)의 머리 준비 패킷(due = 초기화 시각, 127의 모든 패킷보다 앞, 출신 표지 `init:unknown` — 투영 몫이라 차량별 출신을 모름, D11과 같음)이고 차로 상한을 넘으면 그 차로 `init_excess`. 그 몫의 provenance는 10695 위 N 대기로 남겨 링크별 합 = 관측 차량 수 유지(§5.8-6 뒤에 기록해 이중 포장 없음). 질량 보존, 배포 area 장부(`model_stock_values`의 `_nonnegative`) 통과, 두 갈래 부족분을 `posthead_receiver_shortfall_veh`에 합쳐 보고((d) 몫은 따로 `posthead_rehome_shortfall_veh`에도)하고 장부식 항 N_shortfall_kept로 더함. 여유가 충분하면 비트 동일. **(a) 갈래 출발 시각(보충 11 D-K8-6, 보충 12 정정, K8-6b 61ee9ed6)**: 수신 여유 안의 몫은 직전 스텝 t0−1의 수락된 출발로 `_post_service(…, t0−1, …)`에 넘김. `runtime_setup`이 SA 초기화 전에 통로 상태 넷(native_input_prehead·native_input_routes·route_choice_corridor·sc2001_corridor)을 last_step = t0−1로 두고 그 수락 hook은 last_step == step을 요구함(옛 t0 호출은 키 있는 결정에 127 헤드 너머 차량이 있으면 초기화에서 'Aggregate pre-head service clock mismatch'로 죽음). 수신 예약 칸 = t0−1 + 지연(지연 ≥ 1이라 t0 이전 칸 없음). T9b 기준 = 같은 스텝 t0−1의 UFA 출발 경로와 같은 부수효과. 남긴 몫(머리 준비 패킷)의 due는 초기화 시각 t0 그대로(보충 7·8). (d) 재배치는 출발 경로·통로 hook·시계 검사를 부르지 않으므로 t0−1 규칙 밖이고 명세 보충 1 r2 §5.8-4(d)대로 투영 예약 칸을 그대로 옮김(T9c 판정, 보충 12가 보충 11의 "(d) 포함" 문구를 정정) | 보충 5 N-2, **보충 7 §1**(보충 6 §2 철회), **보충 8 §1**, **보충 11**(D-K8-6), **보충 12** |
| D13 | I11 양쪽 단언: \|새 이동 예약 − tags\| ≤ 1e-9 | 보충 5 N-1 |
| D14 | 증거 빌더 입력(sha 고정, 약 263 KB)을 `stopline/inputs/`로 바이트 복사, 빌더 기본 경로. 증거 JSON은 builder sha 한 줄만 바뀜 | 보충 5 §6 |

## 운영: INCOMPLETE 다시 돌리기 (보충 8 §3, 검토 N-r6-4)

도구는 이미 있는 결과를 건너뜁니다(`sa_jobs.py`는 summary.json, `sa_capture.py full`은 run.json, 포착은 capture.json이 있으면 skip). 자동으로 치워지는 것은 입력 없음 summary(`set_aside_input_absent`)와 새 포착 시도 전의 capture_failed.json(`stale_capture_failed_<k>.json`)뿐입니다. 그 밖의 "다시 돌릴 대상"(INCOMPLETE)은 손으로 치운 뒤 **같은 잡을 같은 인자로** 다시 돌립니다.

1. 관문 보고서의 `missing`·`unreadable_runs`·`run_not_finished`에서 대상 라벨과 폴더를 확인합니다. FAIL(런타임 traceback)은 다시 돌릴 대상이 아닙니다.
2. 잡(`jobs/<tree>/<label>/`): `summary.json`을 같은 폴더의 `stale_manual_<k>.json`으로, `hook/`이 있으면 `stale_hook_manual_<k>/`로 이름을 바꿉니다(k는 다시 쓰지 않음). 그 뒤 `sa_jobs.py <family> …`(처음과 같은 인자, 훅 잡은 `--hooks`)를 다시 돌립니다.
3. full run(`full/<tree>/<T>_<arm>_<tag>/`): `run.json`을 `stale_manual_<k>_run.json`으로, `action_<T>.*`(`action_<T>.json`·`.csv` 등 이전 시도의 결정 파일, 있으면)을 `stale_manual_<k>_action_<T>.*`로, `hook/`을 `stale_hook_manual_<k>/`로 바꾸고(검토 r8 N-r8-6: `run_full`은 다시 돈 뒤 같은 폴더의 `action_<T>.json`을 run.json에 적으므로 이전 시도의 파일이 남으면 안 됨) `sa_capture.py full <arm> --tag … --chain … --s3-table …`을 다시 돌립니다. 그 뒤 `sa_hookcount.py`를 다시 돌려 `hooks_<tree>.json`을 새로 씁니다.
4. 포착(`cap/<tree>/…/<arm>/`): killed·하네스 실패(capture_failed.json)는 그대로 `sa_capture.py`를 다시 돌리면 됩니다. ok인데 읽지 못한 포착(`probes_error`, `metadata` 없음)은 `capture.json`을 같은 폴더의 `stale_manual_<k>_capture.json`으로 바꾼 뒤(하위 폴더로 옮기면 G-EB-2의 `**/capture.json` 탐색에 다시 잡힘) 다시 포착하고, 그 틀을 읽는 잡도 2.로 다시 돌립니다.
5. 바꾼 이름은 어느 관문·집계도 읽지 않습니다. 문턱·정의는 바꾸지 않고 해당 관문(`sa_smoke.py`, `sa_compare.py`, `sa_gates.py`)만 다시 계산합니다(보충 7 §5).

## rebase 뒤 확인한 것과 아직 가정인 것

- **확인(rebase, ec063ff)**: K8-4 `projection_diagnostics.storage_seed_split_by_link`의 위치·스키마는 `{link: {storage: {moving, stopped, due_moving_step, due_stopped_step(int)}}, 'unattributed': {storage: {moving, stopped}}}`입니다(ce8fe80 `_split_seed_storage`). K8-4 관문 포착 59상태 전부에서 `stopline_approach._seed_row`가 in_SC1001_W 행(링크 32·127·129·10695·10777, 모두 `PROBE_LINKS` 안)을 예외 없이 읽고 in_SC1001_W unattributed 행은 0상태입니다. `sa_smoke.h2b`의 unattributed 읽기를 `{storage: {moving, stopped}}`로 맞추고(옛 가정 `{storage: veh}`도 읽음), install_check의 unattributed 거부는 |이동|+|정지|로 셉니다.
- **확인(rebase)**: K8-0b `s3site/sitecustomize.py`(K8-0b 뒤 변경 없음)의 표 선택 블록 문구(`sa_hooks.S3_SELECT`)가 정확히 1회 있습니다. `sa_anchors.py --from-rev 5eef6be`(K8-2)가 31곳을 모두 `mapped`로 다시 고정합니다(줄 이동 26곳, 탐색 대체 0).
- 실행 전에 한 번도 돌리지 않은 부분은 FH 이식, 워커 기록기(초당 유입·출발, 탐침 T3N7·T15b), 포착 자식(장부식 다섯 항), `t9c` 스크래치 포착, 포착 상태 시험입니다. 스모크(H-0…H-5)가 첫 점검이고, 실패하면 선언대로 한 번 고칩니다(3시간 제한).
- 포착 상태 시험 T8b·T9b·T9c는 BASE 틀에 K8-4 `storage_seed_split_by_link`가 있어야 돕니다(없으면 사유를 적고 skip → G-EB-14 INCOMPLETE). 장난감 가짜 포착으로 코드 경로만 확인했습니다(커밋 안 함).
- 검토 r3 B-r3-1(보충 6 §2의 음수 수신 저장을 배포 area 장부가 거부)은 보충 7 §1 규칙 (A)로 처리했습니다(D12). 발생 빈도는 실제 포착에서 `posthead_receiver_shortfall_veh`로 셉니다.
- 검토 r6 N-r6-1((d) 커넥터 재배치의 "Posthead rehome overfills" 거부)은 보충 8 §1로 같은 규칙 (A)를 적용해 없앴습니다(D12). (d) 몫의 발생 빈도는 `posthead_rehome_shortfall_veh`(G-EB-14 보고 `kept_10695_veh_total`)로 셉니다.
