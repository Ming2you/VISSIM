# PRE_R2C — 10681 미터만 켠 규칙 ALINEA 두 런: 분석 계획 (발사 전 고정)

- 작성: 2026-10-24 14:43 KST. 근거 결정: D-K9-79(사용자: "두 런 돌림", 권장 아님), D-K9-76(주 지표 = FW_E 본선 7링크).
- 이 문서는 런을 띄우기 **전에** 고정합니다. sha256 은 `rmcause/LOG.md` 에 발사 전에 적습니다. 자료를 본 뒤 고치지 않습니다.
- 표시: [실행] 이번에 돌려서 확인 / [읽음] 문서·코드·자료에서 확인 / [추론] 시험하지 않은 판단.
- 판정 말은 쓰지 않습니다. 문턱도 두지 않습니다. 숫자와 기구만 보고합니다.

## 0. 줄임말

- RM = 램프 미터링. ALINEA = 합류점 하류 점유율을 목표(15 %)로 되먹임하는 미터 규칙.
- FW_E / FW_W = 동측 / 서측 고속도로. NC3 = 같은 시드 v3c3 무제어 런(`D:/VISSIM_runs/20261001_v3c3/s<S>_v3c3nc/run`).
- RM 팔 = 기존 8미터 규칙 ALINEA 런(`…/s<S>_v3c3rm/run`). **R1** = 이번 10681 만 규칙 ALINEA 런(`…/s<S>_v3c3rm10681/run`).
- V-A = SDMPC(우리 예측 제어기) 폐루프 런(`D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s<S>`). 미터는 내내 녹색 10 이었습니다 [읽음 `rmcause/METER_CAUSE.md:18`].
- TTT = 총 통행시간(veh·h). Ω = 제어 영역 635 링크. 미삽입 = 입력에서 생겼지만 망에 못 들어간 차의 대기(재구성).
- g = 10 s 주기 중 녹색 초. g10 = 늘 초록. FZP = VISSIM 차량 궤적 기록. KST = 한국 표준시.

## 1. 목적

1. v3c3-s41 에서 RM 팔의 FW_E 본선 7링크 감소 중 **늦은 창 6,300–8,100 s 의 −59.2 veh·h** 가 미터(그때 조이던 것은 거의 RM_C10681 뿐) 몫인지 가늠할 숫자를 만듭니다. 같은 창 V-A(미터 g10)도 −58.6 이었습니다 [읽음 `o1o4/O1_RULE_RM_V3C3.md:24`, `:240`].
2. **이른 창 2,700–4,500 s** (RM −69.7, V-A −1.7; 10490·10484 가 g2 이던 때) 도 같은 표로 보고합니다 [읽음 같은 파일 :23].
3. 시드 31 도 같은 방법으로 보고합니다.

## 2. 런 정의 (준비는 끝남, [실행])

| 항목 | R1 (s31 / s41) | 근거 |
|---|---|---|
| 준비 폴더 | `D:/VISSIM_runs/20261001_v3c3/s31_v3c3rm10681/prepared`, `…/s41_v3c3rm10681/prepared` | `r2c_n/build/r2c_build_receipt.json` |
| 만든 법 | RM 팔 prepared 를 그 팔 발사(2026-10-01 19:11 KST) 때 모습으로 복사. RM 런이 prepared/network 안에 만든 3개(.err 2개, .results/1.db)만 뺌. 56파일 바이트 같음 | `tools/build_r2c.py` (sha 아래 §6) |
| 망 | `baseline_s<S>_v3c3rm10681.inpx`, 바이트 = RM 팔 망. sha256 s31 `04630354…6f0d`, s41 `e4953eaf…7524` | `r2c_checks.json` |
| 바뀐 파일 1 | `rule_policy.json`: `meters` 8개 → `RM_C10681` 1개(같은 내용). 나머지 키 모두 같음. sha `df8acd08…` → `98887f2d…` | `build/prepared_diff_rm_vs_rm10681.txt` |
| 바뀐 파일 2 | `prepared.json`: 경로 54줄(망 경로 1 + 핀 키 53) + rule_policy 핀 1개. s31 `7d14dd25…`→`6c54c683…`, s41 `d556c865…`→`1e944b1d…` | 같음 |
| 10681 ALINEA | 목표 점유율 15 %, 이득 140, 요청 하한 511.2, 상한 3,024 veh/h, 최소 녹색 2 s, 150 s 마다 ±2 s, 시작 900 s = RM 팔과 같음 | `r2c_checks.json` s<S>_prepared_static |
| 나머지 7 미터 | COM 쓰기 없음 → native OFF(신호 프로그램 없음), NC3 와 같음 | §2.1 |
| 코드 | `D:/VISSIM-merge/sim3` 의 같은 파일(fast_fixed_profile.py a05eb0c5, diagnostic_profile.py 389d81c8, fast_nc_run.ps1 269345da, fast_nc_runner.vbs bf07acda, fast_fixed_profile_verify.py 91441391). RM 빌드 영수증 값과 같음. 코드 사본·수정 0 | `r2c_checks.json` code_used_by_rm_arms_unchanged |
| 드라이런 | fast_nc_run.ps1 를 -Execute 없이: exit 0. 출력은 RM 팔 dryrun_check.txt 와 arguments 의 경로 3개(network, prepared, output)만 다름 | `build/r2c_dryrun_receipt.json` |
| 발사 줄 | RM 팔 줄과 같은 꼴(경로만 바뀜) | `D:/VISSIM_runs/20261001_v3c3/launch_lines_rm10681.txt` |

### 2.1 미터 선택이 이렇게 되는 까닭 [읽음, 줄 번호는 `r2c_checks.json` selection_mechanism_code_lines]

- `fast_fixed_profile.py` rule_step 은 `cfg['meters']` 만 돕니다(이력 초기화 :213, 미터 고리 :224, 쓰기 :244). 그래서 rule_policy 의 meters 에 없는 미터는 한 번도 쓰이지 않습니다.
- 러너 VBS 는 rule_events.csv 의 줄만 씁니다(:423). 검증 스크립트는 결정의 meters 만 봅니다(fast_fixed_profile_verify.py :115). 쓰이지 않은 신호의 COM 소유는 처음과 끝이 같아야 합니다(:160, VBS :466).
- RM 팔은 900 s 에 8개 모두 GREEN 을 썼습니다(`s31_v3c3rm/run/decision_900.json` events) [실행]. 그래서 R1 의 나머지 7개는 RM 팔의 "COM GREEN" 이 아니라 NC3 의 "native OFF" 입니다. O1 짝 확인에서 8개 COM GREEN 과 native OFF 는 첫 RED 전까지 같은 교통을 냈습니다(첫 갈림 s31 2,500.1 s, s41 1,690.1 s; 첫 RED 2,408 / 1,509 s) [읽음 `O1_RULE_RM_V3C3.md:68`]. 이번에 §5 V3 로 다시 봅니다.

## 3. 지표 (정의 = O1 `o1/tools/o1_metrics.py` = V-A va_metrics)

- **주 지표 ①** FW_E 본선 7링크 TTT: 링크 74, 10699, 2, 10613, 119, 10702, 24 (codex `east_link_sets_source.json` `link_sets.mainline`, stage-1 구역 `fw_e_main` 과 같음).
- **같은 표에 옮겨 간 대기** (빼지 않고 늘 함께 보임):
  - FW_E 미터 대기 4개 합(stage-1 `meterbound`), 그중 RM_C10681
  - FW_E 램프 구역 4개 합(`onramp:`), 그중 RM_C10681
  - ② 동측 국소 19링크
  - FW_W 본선
  - 입력 1099 미삽입(FW_W 머리), 입력 1098 미삽입(FW_E 머리)
  - ③ Ω 635링크, ③u Ω 안 도시, 진출 램프 구역
  - ④a 전체 링크, ④b 미삽입, **④ 전체 + 미삽입**
  - **Ω 밖 (a) = ④ − ③**, Ω 밖 (b) = ④a − ③
  - FW_W 미터 대기 4개 합
- 미삽입 합집합 **UR2** = R1(31,41) + RM(31,41) + V-A(31,41,43) + NC3(31,41,43) 에서 줄 선 입력. 앵커 = 같은 시드 NC3 생성 대수. UR2 가 O1 의 UC 와 같은지 함께 적습니다.
- 보조: FW_E 구역(seg0/5/10/15) 공간 평균 속도(veh·km / veh·h), 300 s 칸.

## 4. 창과 비교

- 칸: stage-1 150 s 칸(칸 i = [150 i, 150 i + 150) s). 표는 **300 s 칸**(900–9,000 s, 27칸).
- 창: **이른 창 2,700–4,500 s**, **늦은 창 6,300–8,100 s**, **전체 900–9,000 s**. 이어 읽기용으로 0–9,000 s(O1 표 값과 같은 기준)와 0–900 s(짝 확인, 0 이어야 함)도 냅니다.
- 비교(모두 **같은 시드 짝**, 시드 31·41 각각, 두 시드뿐):
  - R1 − NC3 (10681 만 켠 몫)
  - RM − NC3 (8미터 몫, O1 값 다시 냄)
  - V-A − NC3 (미터 g10, SDMPC)
  - R1 − RM (나머지 7미터를 켠 차이; COM GREEN 대 native OFF 포함)
  - R1 − V-A (러너가 다름: fast_nc 대 COM 러너, 첫 갈림 905 s [읽음 O1 :150])
- 2시드 평균은 숫자로만 덧붙입니다. 신뢰구간·검정은 내지 않습니다.

### 4.1 "늦은 창의 미터 몫" 을 나타내는 숫자 (보고만, 문턱 없음)

시드 s, 창 W 마다 ① 의 창 합:
- a = R1 − NC3, b = RM − NC3, c = V-A − NC3
- a − b (= R1 − RM 의 창 합), a − c (= R1 − V-A 의 창 합)
- 비 a / b, a / c (분모 절댓값 0.05 veh·h 미만이면 비는 비움)
- 읽는 법(정의일 뿐): a 가 b 에 가까우면 그 창의 RM 팔 감소는 10681 하나로도 났다는 숫자이고, a 가 0 에 가까우면 10681 하나로는 나지 않았다는 숫자입니다. 둘 다 한 시드 한 짝의 값이며 혼돈성 차이(§7)가 섞입니다.
- 같은 창에서 옮겨 간 대기 줄(§3)을 같은 표에 둡니다. 10681 미터 대기·램프 구역 줄을 따로 봅니다.

## 5. 유효성 점검 (미리 정함; 실패하면 값과 함께 그대로 보고, 계획은 안 바꿈)

- V1 런: run.json completed true·exit 0, fixed_validation passed, 결정 54개(900–8,850 s), decision_failure 0, VSL 이벤트 0.
- V2 미터: R1 결정의 meters = [RM_C10681] 뿐, RED 는 SC 9106 에만, prepared rule_policy meters = [RM_C10681].
- V3 짝: R1 대 NC3 첫 갈림 프레임 ≥ R1 의 10681 첫 RED; R1 대 RM 첫 갈림 프레임 ≥ RM 팔의 첫 RED(s31 2,408 s, s41 1,509 s). 둘째가 맞으면 COM GREEN = native OFF 가 다시 확인된 것입니다.
- V4 10681 녹색 문자열: R1 대 RM 이 처음 달라지는 결정 T 를 적습니다(교통이 갈린 뒤 달라지는 것이 예상 [추론]).
- V5 재현: UC 로 다시 낸 RM − NC3·V-A − NC3 전체 차가 `o1/out/o1_metrics.json`(sha 0bc29a40…) 과 1e-6 안. s41 ① 창 값 RM − NC3 −69.77 / −59.27(O1 칸), V-A − NC3 −1.61 / −58.56 이 VERIFY_NEXT 값(−69.75 / −59.29, −1.64 / −58.58)과 0.1 안.
- 계획 밖 분석(예: FZP 이동 계수, 10681 통과율)은 하더라도 "사후(계획 밖)" 로 따로 표시합니다.

## 6. 도구 (sha256, 발사 전 고정)

| 파일 (`rmcause/r2c_n/tools/`) | sha256 | 할 일 |
|---|---|---|
| `r2c_scan.py` | `7cb45615cc656fbbf8de68b03b3a4ae4bb545ff4492e44ab3c6a719ea9cfd519` | R1 두 런 stage-1 스캔(한 번에 하나), FZP 잠금 `r2c_n/fzp.lock` 배타 생성·끝나면 지움, 출력 `r2c_n/scans/r1_s<S>/` |
| `r2c_metrics.py` | `ece90b129d793ac657ecbab3ddd741e52710f2a26edafba814f7f08a2ffcab2b` | 위 §3–§5 표, 출력 `r2c_n/out/` (r2c_metrics.json, r2c_tables.md, r2c_bins300.csv, r2c_zone300.csv) |
| `run_py.ps1` (= O1 판 사본) | `f3e3993559a5b802573f14e051974ca97ff89ad7a447db58d7c4690749713364` | WMI 분리 발사, BelowNormal, PYTHONHASHSEED=0, python -B |
| `build_r2c.py` | `acdd600cdfeb8f67b3f7b7974a3a635bb620f17e50535c6b26aa0bab094a9baf` | 준비 폴더(끝남) |
| `log_append.py` | `3a4e5ac84d81abef5baed7c2ef1dde541112c14e8a050c59c53802cd884cafb3` | LOG 덧붙이기 |

- stage-1 도구 sha 는 두 스크립트 안에 고정(common e000c69e…, scan 651c4f51…, uninserted 19eba94e…, report cb4ccc3a…). 읽는 기존 스캔 sha 도 고정(RM: O1 §9 값, NC3: 보충 34 §8.1 sha16, V-A: va_metrics.json 기록).
- 자체 시험 [실행]: `r2c_metrics.py --standin-rm`(R1 자리에 RM 스캔을 넣음) → R1 − RM 모두 0, R1 − NC3 = RM − NC3 = O1 표(① s41 −153.6, ④ +515.3, Ω 밖 (a) +591.1), V5 모두 참. 출력 `r2c_n/selftest/`(r2c_metrics.json sha dd654057…). `r2c_scan.py` 는 런이 안 끝났을 때 거부함을 확인(잠금 안 만듦).
- 분석 순서(런이 둘 다 끝난 뒤, PowerShell):
  1. `run_py.ps1 -Script <tools>\r2c_scan.py -Tag r2c_scan -LogDir <r2c_n>\logs` (재발사가 있었으면 `-ArgsLine "--run 41=run_retry1"` 꼴)
  2. 스캔 끝을 확인한 뒤 `run_py.ps1 -Script <tools>\r2c_metrics.py -Tag r2c_metrics -LogDir <r2c_n>\logs`
  3. 보고서는 `r2c_n/out/r2c_tables.md` 숫자를 옮겨 씁니다. 표마다 "같은 시드 짝, 2시드" 를 적습니다.

## 7. 한계

- 시드 2개(31, 41). 시드마다 짝 하나. 평균·분산으로 가를 수 없습니다. 무제어 5시드 σ 는 전체망 약 1 % 입니다 [읽음 기억 파일 vissim-seed-variance]. 본선 7링크 시드 사이 퍼짐은 따로 재지 않았습니다.
- 첫 갈림(첫 RED 직후) 뒤의 차에는 미터 효과와 혼돈성 차이가 섞입니다. 늦은 창은 첫 갈림보다 한참 뒤입니다. 그래서 a 와 b 의 차는 "7미터 몫" 만이 아니라 경로가 달라진 몫도 담습니다 [추론].
- R1 의 7미터는 native OFF, RM 팔은 COM GREEN 입니다(§2.1). 교통이 같다는 근거는 첫 RED 전까지의 짝 확인뿐입니다.
- V-A 는 러너·도시 신호 제어·VSL 경로가 다릅니다. R1 − V-A 는 미터만의 차가 아닙니다.
- 1099 대기가 9,000 s 에 남으면(RM s41 은 665 대) ④·Ω 밖 값은 잘린 값입니다.
- 망 v3c3, 수요 FW80/U90 하나뿐입니다. 다른 망(64cf, W264)과 빼지 않습니다.

## 8. 런 운영

- 발사: `D:/VISSIM_runs/20261001_v3c3/launch_lines_rm10681.txt` 의 두 줄을 PowerShell `Invoke-CimMethod Win32_Process Create`(CurrentDirectory `D:\VISSIM_runs\20261001_v3c3`)로, RM 팔처럼 20 s 간격. 기록은 `D:/VISSIM_runs/20261001_v3c3/wmi_launch_lines_rm10681.txt`.
- 자리: PC 전체 VISSIM 4개 이하. 다른 세션 VISSIM·python(예: codex 9a8320ec rolling_cea)은 세기만 하고 건드리지 않습니다. 이름으로 죽이지 않습니다.
- 멈춤: fast_nc_run.ps1 자체가 FZP 시각이 300 s 동안 안 늘면 자기 cscript·VISSIM PID 만 죽입니다(:140-150) [읽음]. 내 런이 5분 넘게 진행이 없으면 그 런의 PID 만 죽이고 한 번만 `-Output …\run_retry1` 로 다시 띄우고 기록합니다(사용자 방침). 분석은 그때 `--run <S>=run_retry1`.
- 예상 걸림: RM 팔 104 / 110분(동시 3런 + 다른 1개) [읽음 run.json]. 이번 끝 예상 = 발사 + 약 1 h 45 m – 2 h.

## 9. 하지 않는 것

- 새 런은 이 두 개뿐. 결정·plant 재생 0. sim3·기존 런 폴더·frozen 쓰기 0. 커밋·푸시·동결·체크아웃 0.
- 봉인 시드 37/59/61/67 자료, codex 64cf-s59/s61/s67 숫자: 열람·인용 0. `s37_v3c3rm` 폴더 열지 않음.
