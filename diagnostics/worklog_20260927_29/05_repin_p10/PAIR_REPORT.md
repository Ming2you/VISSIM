# P10 짝 비교: R-obs(SDMPC 러너, 무제어 + obs150) 대 v3c1 NC s31(fast_nc 러너)

작성 2026-09-28. 표기: [실행] 이번에 돌려서 확인 / [읽음] 파일에서 읽음 / [추론] 확인하지 않은 해석.
쓰기는 이 폴더(`scratchpad/v3c1-p10/pair/`)에만 했습니다. 런 폴더, FRZ, 워크트리에는 쓰지 않았습니다. 워크트리 `git status --porcelain`은 작업 전후 모두 0줄이었습니다(HEAD 5323faa4) [실행].

## 1. 결론

- **차량 궤적은 같습니다.** 5.1 s 프레임부터 파일 끝(8995.1 s)까지 두 FZP의 데이터 부분이 바이트 단위로 같습니다. 크기는 1,183,592,740 B로 같고, sha256도 `575945c13c04…b6f42d41a`로 같습니다. 프레임 1,799개, 행 6,913,410개, 25개 열 전부가 같습니다 [실행 `fzp_bytecompare.py`].
- **차이는 두 가지이고, 둘 다 기록 설정에서 옵니다. 시뮬레이션 결과는 다르지 않습니다.**
  1. 헤더 38줄 가운데 2줄(`* File:`의 .inpx 경로, `* Date:`)
  2. R-obs에만 있는 0.10 s 프레임 한 개. 행은 한 줄(`0.10;1;90;1;1.13;…`, 130 B)이고, 차량 1이 링크 90에 있습니다.
  - 두 차이를 합하면 파일 크기 차이 145 B(= 15 + 130)가 정확히 설명됩니다 [실행].
- **처음 갈라지는 곳은 없습니다.** 0.1 s 프레임을 걸러내고 비교하면 `stage1_report.pairing_check`가 ok=True를 냅니다. 모든 프레임 수가 같고, 입력 34개 모두 진입 시각 목록이 같습니다. scan.json과 uninserted.json도 태그·경로 키를 빼면 완전히 같습니다 [실행 `pair_metrics.py`].
- **네 지표의 차이(R-obs − NC)는 0.000000 veh·h입니다(프레임 격자를 맞춘 경우).** 0.1 s 프레임을 그대로 두고 스캔하면 bin 0에만 +0.0021 ~ +0.030 veh·h가 붙습니다(§4).
- **R-obs는 이후 짝 비교에서 NC s31을 대신할 수 있습니다.** 다만 §5의 조건 세 가지를 지켜야 합니다. 0.1 s 프레임 제거, `network\…_001.err` 사용, 확인 범위가 seed 31뿐이라는 점입니다.

## 2. 비교 대상

| | R-obs | NC s31 |
|---|---|---|
| 런 | `D:\VISSIM_runs\20260928_sdmpc31_v3c1\sdmpc31_v3c1_nc_s31` | `D:\VISSIM_runs\20260927_v3c1\s31_v3c1nc` |
| 러너 | FRZ `scripts\run_real_world_stackelberg_controller.vbs` (워치독 ps1:403), `-Controller no-control`, obs150 | `D:\VISSIM-merge\sim3\diagnostics\fast_nc_runner.vbs` sha `bf07acda…` (run.json `runner_sha256`), `native_fzp_only` |
| 망 | `network\sdmpc31_sdmpc31_v3c1_nc_s31.inpx` sha `2577209b…` | `prepared\network\baseline_s31_v3c1nc.inpx` sha `2577209b…` [실행 sha256sum] |
| .sig | 42개 | 42개. 파일별 sha가 모두 같습니다 [실행] |
| seed / SimRes / SimPeriod | 31 / 10(망 값을 그대로 씀, vbs:518-519) / 9001(vbs:517) | 31 / 10 / 9001(`prepared\native_simulation.csv`, prepared.json `saved_simulation`) [읽음] |
| 종료 | launch log `EXIT … code=0`, `DECISIONS_OK=61 DECISIONS_FAILED=0` | run.json `completed=true exit_code=0` [읽음] |
| FZP | `vissim_eval\sdmpc31_sdmpc31_v3c1_nc_s31_001.fzp` 1,183,596,914 B | `run\vissim_eval\baseline_s31_v3c1nc_001.fzp` 1,183,596,769 B |
| 런타임 .err | `network\sdmpc31_sdmpc31_v3c1_nc_s31_001.err` 302,061 B | `run\baseline_s31_v3c1nc_001.err` 302,006 B |

## 3. 러너 차이와 궤적에 미친 영향

궤적이 바이트 단위로 같으므로, 아래 차이는 이 런에서 **모두 궤적에 영향이 없었습니다** [실행: 동일성]. 각 항목이 왜 무해한지는 [읽음]/[추론]으로 따로 적었습니다.

| 항목 | R-obs (SDMPC 러너) | NC (fast_nc) | 영향 |
|---|---|---|---|
| **차량 기록 시작** | `VehRecFromTime=0`(vbs:4955), 해상도 = 5 s × SimRes 10 = 50스텝(vbs:4909-4914, 4963; runlog `NATIVE_EVAL=1 … from=0 … resolution=50`) | `VehRecFromTime=5`(fast_nc_runner.vbs:298-305, intervalSec 5·SimRes 10) | **0.10 s 프레임 한 개가 여기서 생깁니다** [읽음]. 기록 전용 설정이므로 시뮬레이션은 바뀌지 않습니다. PLANT_PORTING_GUIDE.md:680에 기록된 현상과 같습니다 |
| 검지기(obs150) | 데이터 수집점 314 → 608, 측정 173 → 467개 추가, DataColl 150 s 집계와 raw(.mer) 기록(runlog `OBS150_DETECTORS`, `OBS150_EVALUATION`; vbs:4935-4941) | 없음(FZP만) | 측정 객체라서 차량에 작용하지 않습니다 [추론, 동일성으로 뒷받침] |
| obs150 읽기와 정지 | t=1, 150, …, 9000에서 `SimBreakAt` 정지 61회, COM으로 차량·신호 읽기(`OBS150_BUNDLE`), 첫 스텝은 `RunContinuousTo 1`(vbs:850-853, 7070-7084) | `SimBreakAt=9000`, `RunContinuous` 한 번(fast_nc:266, 315) | 정지·재개와 읽기가 난수열과 상태를 바꾸지 않았습니다 [실행: 동일성] |
| 램프 미터 SC 9101–9108 | t=1에 COM으로 가져가 GREEN을 씀(쓰기 8건). 이후 150 s마다 GREEN 유지 확인 480회, 모두 ok(`decisions_…\signal_readback.csv`; runlog `SIGNAL_WRITE_ATTEMPTS=8`, `SIGNAL_PERSISTENCE_OK=480`) | 쓰기 없음(fast_nc:240 "no … signal, meter … writes"). 두 런 모두 `VISSIG_Controller.dll.err` = "SC 9101 … has no signal program"(파일 동일) | 프로그램 없는 미터와 COM GREEN이 교통상 같게 동작했습니다 [실행: 동일성, 기구는 추론] |
| 도시 신호 | 쓰기 0건(`SIGNAL_WRITE_ATTEMPTS`는 미터 8건뿐), SC 17개는 네이티브 시계(runlog `SIGNAL_FRAME_ADVANCE … native_clock_scs=17`) | 네이티브 | 둘 다 네이티브입니다 [읽음] |
| VSL | 결정마다 DSD 66개 × 차종 4 = 16,104행 요청 110 / 읽음 110(`vsl_readback.csv`) | 쓰기 없음 | .inpx의 네이티브 분포가 이 66 × 4 모두 110입니다. 불일치 0/16,104 [실행] → 쓰더라도 같은 값 |
| 수요 | `DEMAND_WRITE` 204건 모두 before = target. 프로필 scale 1.0, before = after(runlog `DEMAND_PROFILE_TOTALS`) | 쓰기 없음 | 같은 값을 다시 쓴 것뿐입니다 [실행 awk] |
| 기타 평가 | 링크 평가(`FAR_MEASUREMENT` 53점), 큐 카운터 98, 신호 변경(.lsa) | 없음 | 측정 전용 [추론] |
| .err | NC와 비교해 `Note	Stop the simulation? : &Yes` 한 줄(1435행)만 더 있음. 제거 279건, `remain` 1099:37로 같음 | — | 파싱 결과가 같습니다 [실행 `parse_err`] |

## 4. 네 지표 (veh·h, 9,000 s 전 구간, stage-1 적분 격자) [실행]

정의는 N1F stage 0과 같습니다(`D:\VISSIM_runs\20260928_n1f_vsl\stage0\scripts\stage0_metrics.py:5-19`).

- M1 = 영역 fw_e_main
- M2 = `east_link_sets_source.json`의 국소 19링크 link_vh 합
- M3 = Ω TTT
- M4 = 전체 링크 TTT + 미삽입 지체
- 미삽입은 세 스캔에서 큐가 생기거나 remain이 남은 입력의 합집합 {194, 282, 1085, 1093, 1098, 1099, 1102}을 NC 앵커로 계산했습니다(`stage1_report.arm_series(…, anchor=NC)`).

| 지표 | NC s31 | R-obs (0.1 s 프레임 제외) | 차 | R-obs (원본 그대로) | 차 |
|---|---:|---:|---:|---:|---:|
| ① M1 동측 본선 7링크 | 2109.2321 | 2109.2321 | **0.000000** | 2109.2355 | +0.003400 |
| ② M2 동측 국소 19링크 | 2401.9708 | 2401.9708 | **0.000000** | 2401.9743 | +0.003480 |
| ③ M3 Ω TTT | 7232.2076 | 7232.2076 | **0.000000** | 7232.2214 | +0.013800 |
| ③u 그중 urban_omega | 2488.4973 | 2488.4973 | **0.000000** | 2488.4994 | +0.002100 |
| ④ M4 전체 + 미삽입 | 12933.7962 | 12933.7962 | **0.000000** | 12933.8262 | +0.030064 |
| ④a 전체 링크 TTT | 9600.1066 | 9600.1066 | 0.000000 | 9600.1301 | +0.023500 |
| ④b 미삽입 지체 | 3333.6896 | 3333.6896 | 0.000000 | 3333.6961 | +0.006564 |

- M3는 150 s bin(소수 4자리 반올림)의 합입니다. 반올림 없는 `totals.omega_ttt_veh_h`는 두 런 모두 7232.2056이고, 전체 링크는 9600.1056입니다 [실행].
- 원본 그대로 스캔한 경우의 차이는 모두 bin 0(0–150 s)에만 있습니다.
  - 적분이 0.1 → 5.1 s 구간 하나를 더 셉니다. 계산은 (1 + 5.1 s 차량 수)/2 × 5/3600입니다.
  - 미삽입 창도 0.1 s에서 시작하기 때문에 ④b가 조금 달라집니다.
- 기타 [실행]:
  - 제거 279 / 279
  - `vehicles_seen` 같음
  - 마지막 프레임 8995.1 s의 망 안 차량 2,635 / 2,635, Ω 2,016 / 2,016
- 이번 NC 재스캔은 기존 `s31_v3c1nc\analysis\scan.json`(읽기만 함)과 태그·경로 키를 빼고 완전히 같습니다 [실행].

**pairing_check**(t_act = None, 즉 모든 프레임이 같아야 함) [실행]:

| | 결과 |
|---|---|
| R-obs, 0.1 s 프레임 제외 | `same_frame_times=true`, `first_divergent_frame_sec=null`, `first_divergent_entry_sec=null`, 입력 34/34 진입 시각 동일, **ok=true** |
| R-obs, 원본 그대로 | `same_frame_times=false`, `first_divergent_frame_sec=5.1`, **ok=false** |

원본의 5.1 s는 궤적이 갈라진 시각이 아닙니다. 0.1 s 프레임 때문에 프레임 번호가 하나씩 밀려서 생긴 인공물입니다. 진입 시각은 원본에서도 34/34 같습니다.

## 5. R-obs가 NC s31을 대신할 수 있는가

**대신할 수 있습니다.** 5.1 s 이후 궤적이 바이트 단위로 같으므로, 5.1 – 8995.1 s 격자의 어떤 FZP 지표도 두 런에서 같습니다. 또 같은 SDMPC 러너로 돈 제어 런과 짝지을 때는 R-obs가 러너 조건까지 같은 NC입니다. 제어 런의 미터 GREEN·VSL 110 쓰기, 정지 61회, 0.1 s 프레임을 공유합니다 [추론]. 조건은 다음과 같습니다.

1. **0.1 s 프레임을 빼고 스캔합니다.**
   - SDMPC 러너 FZP를 fast_nc 계열(NC 5시드, N1 팔 등)과 `pairing_check`나 bin 단위로 비교하려면, SIMSEC 0.10 행을 읽을 때 걸러야 합니다. 이 폴더의 `pair_scan.py`가 그렇게 하는 예입니다(`_IoShim`, 파일은 건드리지 않음).
   - 거르지 않으면 pairing_check가 ok=false가 되고, 지표 bin 0에 +0.03 veh·h 이하가 붙습니다.
   - SDMPC 제어 런끼리, 또는 SDMPC 제어 런과 R-obs 사이에서는 두 파일 모두 0.1 s 프레임을 가지므로 그대로 비교해도 됩니다 [추론].
2. **stock `stage1_common.run_files`를 R-obs 폴더에 쓰지 않습니다.**
   - 이 러너 폴더에는 run.json과 `prepared\network\*.inpx`가 없어서 inpx가 None이 됩니다.
   - err는 glob `*_001.err`로 최상위 `vissim_simulation_001.err`를 잡습니다. 이 파일은 294,912 B로, 로그가 열려 있을 때 복사된 것입니다(워치독 16:50:31 WARNING). 파싱하면 `remains {}`, 제거 276건이 나옵니다(정본은 1099:37, 279건) [실행].
   - 그러므로 info를 직접 만들어 `network\sdmpc31_sdmpc31_v3c1_nc_s31_001.err`를 넘겨야 합니다(`pair_scan.py:robs_info`).
3. **범위: seed 31, 무제어만 확인했습니다.**
   - 다른 시드도 같은 기구라면 같겠지만 확인하지 않았습니다 [추론].
   - 제어 런에서 미터를 GREEN이 아닌 값으로 쓰거나 VSL을 110이 아닌 값으로 쓰면 당연히 갈라집니다. 이 등가성은 **쓰기가 네이티브 값과 같을 때만** 성립합니다.

## 6. 재현과 산출물 (이 폴더)

프로세스는 모두 BELOW_NORMAL(0x4000 읽어서 확인), 한 번에 하나씩 돌렸습니다. 벽시계는 바이트 비교 9.6 s, 스캔 3회 각 19–22 s입니다. VISSIM과 cscript는 시작하거나 종료하지 않았습니다.

- `fzp_bytecompare.py` → `fzp_bytecompare.json`: 헤더 / 5.1 s 이전 행 / 본문을 나누고, 본문을 1 MiB 단위로 비교하고 sha256을 계산합니다.
- `pair_scan.py` → `scans\{nc,robs,robs51}\{scan,uninserted}.json`, `pair_scan.log`
  - stage0_scan.py 방식을 따릅니다. `stage1_scan.main()`은 호출하지 않고 출력 위치만 이 폴더로 돌렸습니다. `find_rule_policy`는 None으로 바꿨습니다.
  - stage1 도구 4개의 sha는 stage0과 같은 값으로 고정해 확인했습니다(`stage1_common.py e000c69e…`, `stage1_scan.py 651c4f51…`, `stage1_uninserted.py 19eba94e…`, `stage1_report.py cb4ccc3a…`).
- `pair_metrics.py` → `pair_metrics.json`, `pair_metrics.log`: 네 지표, pairing_check, scan/uninserted JSON 전체 비교, 기존 NC analysis와의 대조.
- `sig_robs.txt`, `sig_nc.txt`: .sig 42개의 sha256.

## 7. 하지 않은 것

- §5.5 1(L0/L1 all-110 런 상태 대조), §5.5 4(T5·결정 재생 IDENTICAL), RA-6(U1 T1)은 이 과제 범위 밖이라 하지 않았습니다. 재생 도구도 쓰지 않았습니다.
- 금지된 데이터는 열지 않았습니다: seed 37 / 59 / 61 / 67, RM 팔 출력. v3b 폴더는 최상위 이름만 나열했고 파일은 열지 않았습니다.
- OBS150 번들 차량 수(예: t=150의 1,072대)와 FZP 프레임은 대조하지 않았습니다. 번들은 150.0 s 시점이고 FZP는 x5.1 s 시점이라 같은 순간이 아닙니다.
