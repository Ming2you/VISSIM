# v3c2 무제어(NC) 관문 사전 선언

- 동결: 2026-09-30 18:13 KST(+0900). 이 파일의 sha256 은 같은 폴더 `gate_predeclaration_v3c2_nc.sha256` 에 적습니다.
- 동결 시점에 v3c2 런은 하나도 없습니다. 여섯 시드 모두 `run\` 과 `launch.log` 가 없고, VISSIM·cscript 프로세스는 0개입니다 [실행 `ls`, `reports/v3c2_prepare_checks.json` running_vissim_cscript_count].
- 대상 망: v3c2 = v3c1 + 차량 구성 14 "Freeway entry DSD110" + 입력 1098(link 74, FW_E)·1099(link 26, FW_W)의 6개 시간 구간 모두 vehComp 1 → 14. 근거는 사용자 결정(2026-09-30) "고속도로 진입 차량은 희망속도 110 으로 넣는다" 입니다.
- 태그: [실행] 명령으로 확인 / [읽음] 파일·코드에서 확인 / [추론] 시험하지 않은 판단.
- 런 표기: 망 접두어를 붙입니다(v3c2-s31, v3c1-s31 …).

## 0. 고정 자료

| 항목 | 경로 (`D:/VISSIM_runs/20260930_v3c2/` 기준) | sha256 |
|---|---|---|
| 편집 영수증 | `v3c2_edit_receipt.json` | `cf8b0cb2675cff36b314a4e5af88bbc83c7d30ae92d7f7620f7df5ffed0f9fcb` |
| 정적 검사 19개(전부 참) | `reports/v3c2_build_checks.json` | `5961e92c8390db48904e7bdaba5757d7e5b4c302e111de4ef0d0921aa4fd556d` |
| prepare 검사 19개(전부 참) | `reports/v3c2_prepare_checks.json` | `0197179c9d74ef54a0d6badf94a9f3ee14ba29e50549526fb9ffadbc7855021a` |
| 발사 줄(발사 안 함) | `launch_lines_nc.txt` | `eb574c1f979db32b6cab7ea655840e7c8f123b7bcc78ec50d7d398b2c4328a7f` |

| 시드 | 역할 | v3c1 망 sha | v3c2 망 sha |
|---|---|---|---|
| 31 | fit | 2577209b | `597191ac2f9afb051888421e8d2f52a04b21ceafd6f994f874841194383eab69` |
| 41 | fit | 226baa37 | `2b15d51e92a77bcd587c637b808579340f078a8880d118e01a6073fb8d38a9b1` |
| 43 | fit | b8e7cf1f | `e11d19f2f3051fae16591e0f1a4044586b817302a778102ce51d8a4f7370fe74` |
| 47 | fit | ec0cd81d | `99689b7f3e967413ba4be0339e2950ffa4c32d6360a1ecaddec09ff5844369f6` |
| 53 | fit | 385f40da | `c2dd1a48b4be7b936e9f07505365bf366fc953e5c02d3467059d923c21dfada1` |
| 37 | 봉인(held-out) | 3eb06c63 | `f6b0b7d6a6641705f685a3ff3df801e2921912c3458f626446b9559a47eb3b99` |

- 관문 판정에는 fit 시드 5개(31/41/43/47/53)만 씁니다.
- **s37 은 봉인입니다.** 돌리기만 하고, 끝났는지는 `run.json` 의 `completed`·`exit_code` 두 필드로만 확인합니다. FZP, .err, analysis 는 열지 않습니다. v3c1-s37 도 마찬가지입니다.
- 비교 기준은 v3c1 NC fit 5시드입니다(`D:/VISSIM_runs/20260927_v3c1/s{31,41,43,47,53}_v3c1nc`, 읽기만 함).
- 같은 시드라도 망이 다르면 20–35 s 만에 궤적이 갈라집니다. 그래서 v3c1 과 v3c2 의 같은 시드는 짝이 아닙니다(v3c1 SC1004W 진단 A-1) [읽음].

## 1. 사전 노출 (정직하게 적습니다)
- v3c2 결과는 없으므로 본 적이 없습니다.
- v3c1 fit 시드 결과 중 이번 선언 전에 본 것은 다음과 같습니다.
  - (a) `_001.err` 의 제거·차로변경 대기 줄 수. G5 허용치를 정하려고 오늘 셌습니다. 수치는 §G5 표에 있습니다 [실행].
  - (b) 로드 .err 와 `VISSIG_Controller.dll.err` 의 내용 [실행].
  - (c) 정적 점검 2a·2b 보고서(`scratchpad/static_checks/2a/CHECK_2A.md`, `2b/CHECK_2B.md`)의 요약과 0–40 m 속도 표.
    - FW_E 0–40 m p50: 29.6–31.7 km/h
    - FW_W 0–40 m p50: 15.5–22.6 km/h
    - 셀 0 혼잡 비율: FW_E 0.65–0.73, FW_W 0.91–1.00
  - (d) `reports/gates_5seed/GATES_5SEED.md` §5 의 Ω·도시·진출로·미삽입 표
  - (e) v3c1-s31 `analysis/uninserted.json` 의 1098/1099 행
- G4 의 문턱 80 km/h 와 판정 방식(중앙값, t ≥ 900.1)은 작업 지시로 주어진 것입니다. 위 수치를 보고 정한 것이 아닙니다.

## 2. 관문 (구속). 하나라도 떨어지면 v3c2 를 자동으로 채택하지 않습니다

### G1 편집 영수증: 선언한 변경만 있을 것
- **판정 자료:** `reports/v3c2_build_checks.json` summary 19개 항목
- **통과 조건:** 19개 모두 참이어야 합니다. 그리고 발사 직전과 런 뒤 두 번 다음을 다시 확인합니다.
  - (i) `python -B scripts/v3c2_build.py recheck` 이 ok = True 여야 합니다.
  - (ii) 각 fit 시드의 `prepared/network/baseline_s<seed>_v3c2nc.inpx` sha 가 위 표의 v3c2 sha 와 같아야 합니다(`fast_nc_run.ps1` 도 발사 때 45개 핀을 다시 해시합니다).
- **선언한 변경:** v3c1 대비 다음 두 가지뿐입니다.
  - 7줄 삽입: v3c1 31195 행 앞, 391 B, 블록 sha `82c11cd5…`
  - 12개 행에서 ` vehComp="1" ` → ` vehComp="14" `: v3c1 31439–31444 행과 31449–31454 행
- **이미 확인한 것 [실행]**
  - `difflib` 통합 diff: `+` 19줄, `-` 12줄(`reports/v3c2_vs_v3c1_s31.diff`). GNU diff 도 여섯 시드 모두 같은 세 덩어리입니다.
  - ElementTree 위치 비교 결과는 선언한 14건과 정확히 같습니다: 구성 13 tail 1건, 구성 14 삽입 1건, 속성 12건.
  - 구성 14 요소의 바이트가 64cf 원본(31327–31333 행)과 같습니다.
  - DSD 110 과 차종 100/150/200 은 v3c1 과 바이트가 같습니다.
  - 시드 파일끼리는 randSeed 행(30995)만 다릅니다.
- 현재 상태: 통과(정적). 런 뒤 (ii) 가 다르면 탈락입니다.

### G2 로드 .err: v3c1 과 같을 것
- **판정 자료:** 각 fit 시드 `run/baseline_s<seed>_v3c2nc.err` 와 그 사본 `prepared/network/baseline_s<seed>_v3c2nc.err`
- **기준:** 같은 시드 v3c1 파일 `run/baseline_s<seed>_v3c1nc.err`. 5시드 모두 200 B 이고 sha `d1ee825c…` 로 같습니다. 내용은 기존 경고 한 줄입니다: "Static Vehicle Routing Decision 1102 is located only 5.431 m upstream of the first connector" [실행].
- **예상되는 추가 줄:** 없습니다. 근거는 구성 14 를 쓰는 64cf 망의 로드 .err(`D:/VISSIM_runs/vsl_repro_s29/none/run/vsl_seed29_none.err`)입니다. 이 파일은 v3c1 로드 .err 와 바이트까지 같습니다(sha `d1ee825c…`) [실행].
- **통과 조건:** 두 사본 모두 같은 시드 v3c1 로드 .err 와 바이트가 같아야 합니다.
  - 새 줄이 생기거나 줄이 빠지면 탈락입니다. 특히 구성 14, 입력 1098/1099, DSD 를 언급하는 줄이 있으면 탈락입니다.
  - 탈락하면 차이 나는 줄을 그대로 인용해 보고합니다.
- **보조 조건:** `prepared/network/VISSIG_Controller.dll.err` 가 v3c1 과 바이트가 같아야 합니다. v3c1 5시드는 모두 464 B, sha `f144ab0c…` 입니다.

### G3 런 완료
- **통과 조건:** 각 fit 시드의 `run/run.json` 이 다음을 모두 만족해야 합니다.
  - `completed` = true
  - `error` = null
  - `exit_code` = 0
  - `terminal_sec` = `requested_terminal_sec` = 9000
  - `native_files` 에 `baseline_s<seed>_v3c2nc_001.fzp` 가 있음
- **추가 조건:** 그 FZP 의 첫 프레임이 5.1 s, 마지막 프레임이 8995.1 s 여야 합니다. v3c1 과 같은 5 s 기록입니다.
- `launch.log` 에 예외가 없어야 합니다.

### G4 진입 거동: 입구 0–40 m 속도 ≥ 80 km/h
- **정의.** 정적 점검 사전 선언(`scratchpad/static_checks/PREDECLARATION.md`, sha `a992341e…`) §1.7 의 0–40 m 속도와 같습니다. 구현은 `static_checks/2a/code/fzp_pass.py:106-111` (sha `011a2462…`)입니다.
  - 프레임 집합 F: SIMSEC ≡ 0.1 (mod 5) 이고 900.1 ≤ t ≤ 8995.1 인 프레임(1,620개)
  - 대상 행: `LANE\LINK\NO` = ℓ 이고 0 ≤ POS < 40 m 인 행. ℓ = 74(FW_E) 와 26(FW_W)
  - v40_ℓ(t) = 프레임 t 대상 행들의 SPEED(km/h) 산술 평균. 대상 행이 없는 프레임은 뺍니다.
  - M_ℓ(s) = 비어 있지 않은 프레임들의 v40_ℓ(t) 중앙값(`numpy.median`)
- **통과 조건:** 5개 fit 시드 모두에서 M_74(s) ≥ 80.0 **그리고** M_26(s) ≥ 80.0 이어야 합니다(경계값 80.0 은 통과).
- **함께 보고(판정 밖):** 빈 프레임 수, p5/p95, v40 < 60 인 프레임 비율
- **v3c1 참고값 [읽음 CHECK_2A.md §2.3·§2.4]:** M_74 29.6–31.7, M_26 15.5–22.6
- **[추론]** link 26 은 셀 0–5 에 걸쳐 약 3 km 의 속도 구배가 있습니다(CHECK_2A §2.4). 그래서 FW_W 입구 혼잡이 삽입 속도가 아니라 하류 용량(F11) 때문이라면 G4 가 link 26 에서 떨어질 수 있습니다. 그 경우 결과는 F11 의 증거로 함께 적습니다.

### G5 망 파탄 흔적 없음: 제거·차로변경 대기 시간초과가 v3c1 + 허용치 이하
- **자료:** 각 fit 시드 `run/baseline_s<seed>_v3c2nc_001.err`. cp949 로 읽고 실패한 바이트는 대체합니다. 런 전체를 봅니다(시간 창 없음).
  - `prepared/network/` 사본과 바이트가 같은지도 확인합니다.
- **세는 것(줄 수)**
  - X_lc: "seconds of waiting for lane change" 가 들어간 줄. 45 s 와 60 s 를 모두 셉니다.
  - X_rm: X_lc + "without having found the next link" 가 들어간 줄 + 그 밖에 "removed" 또는 "deleted"(대소문자 무시)가 들어간 줄. 한 줄은 한 번만 셉니다.
  - X_Z: X_lc 와 next-link 줄 가운데 링크 번호가 고속도로 구역 Z 에 드는 것
    - Z = 본선 체인 74, 10699, 2, 10613, 119, 10702, 24, 26, 10771, 120
    - 그리고 포트 커넥터 16개: 10643, 10682, 10481, 10483, 10639, 10681, 10490, 10484, 10479, 10491, 10645, 10638, 10480, 10482, 10646, 10644
    - 목록 출처는 정적 점검 PREDECLARATION §1.6 표입니다.
- **허용치:** T_X = (v3c1 fit 5시드에서 X 의 최댓값 − 최솟값) + 2
  - 같은 시드도 짝이 아니므로, 시드 간 범위를 잡음 폭으로 씁니다. +2 는 v3c 관문 G4 의 "+2대/런" 관례입니다.
- **통과 조건:** 5개 fit 시드 모두, 세 지표 모두 X_v3c2(s) ≤ X_v3c1(s) + T_X

| 지표 | v3c1 s31/41/43/47/53 [실행] | 범위 | T | 한도 s31/41/43/47/53 |
|---|---|---:|---:|---|
| X_lc | 279 / 343 / 292 / 244 / 294 | 99 | 101 | 380 / 444 / 393 / 345 / 395 |
| X_rm | 282 / 346 / 293 / 249 / 295 | 97 | 99 | 381 / 445 / 392 / 348 / 394 |
| X_Z | 1 / 2 / 0 / 1 / 1 | 2 | 4 | 5 / 6 / 4 / 5 / 5 |

- v3c1 의 X_rm 에서 next-link 줄은 3/3/1/5/1 개이고, 그 밖의 removed·deleted 줄은 0 개입니다. X_Z 는 모두 link 26 @3420.4 m(진출 10479 앞)입니다 [실행].
- **[추론]** 변화가 없을 때 이 규칙이 잘못 탈락시킬 확률
  - X_lc 의 시드 간 sd 는 35.6 입니다. 짝이 아닌 차이의 sd 는 약 50 이므로, 시드당 약 2%, 5시드 전체로 약 10% 입니다(정규 근사).
  - 한 시드만 넘으면 탈락으로 적되, 어느 링크에서 늘었는지 함께 보고합니다.

## 3. 판정 뒤 조치
- **G1–G5 가 모두 통과하면** v3c2 NC 를 입구 거동을 고친 새 무제어 기준으로 받아들입니다.
  - 그다음 정적 점검 2a·2b 를 v3c2 NC fit 5시드(v3c2-s31/41/43/47/53)에 **동결된 방법 그대로** 다시 돌립니다. 방법은 `scratchpad/static_checks/PREDECLARATION.md`, sha `a992341e8103336d8630b301aecd96e3d662c0a0df17791087526d1966a5b3d8` 입니다.
    - 문턱, 창, 정의, 배포 plant 는 바꾸지 않습니다. 달라지는 것은 자료 경로와 추출 관측(EO)을 v3c2 FZP 에서 새로 만든다는 것뿐입니다.
  - 그 결과로 두 가지를 정합니다.
    - **F10(입구 경계):** 2a 의 OPEN/CLOSE
    - **F11(FW_W 상류 용량):** 2b 의 FW_W 셀 0–6 위반이 남는지
  - 다른 것을 바꿀 일이 생기면 그 전에 AMENDMENT 로 따로 선언합니다.
- **하나라도 떨어지면** 자동 채택도, 자동 되돌림도 하지 않습니다. 탈락한 관문과 증거를 보고하고 사용자 결정을 받습니다. 2a·2b 재실행도 그 결정 뒤에 합니다.
- 어느 경우든 s37 은 봉인을 유지합니다.
- **[추론] 재핀:** v3c2 는 망 sha 가 바뀌므로, v3c1 망 sha 에 핀된 폐루프 자료(재핀 커밋 5323faa, FRZ)는 v3c2 에 그대로 쓸 수 없습니다. 이 선언의 범위 밖입니다.

## 4. 서술 (판정 없음). 시드별로 v3c1 NC fit 5시드와 나란히 적고, 짝 비교는 아닙니다
- **D1 입구 미삽입과 삽입률(1098/1099)**
  - `D:/VISSIM-merge/tools/stage1/stage1_scan.py`(sha `651c4f51…`)와 `stage1_uninserted.py`(sha `19eba94e…`)로 v3c1 과 같은 방식으로 만든 `analysis/uninserted.json` 의 `inputs.{1098,1099}` 행을 씁니다: `delay_veh_h`, `inserted_seen / scheduled_total`, `remain_err`.
  - `analysis/scan.json` `insertions.{1098,1099}.per_bin_by_entry` 를 900 s 로 묶은 삽입 대수도 적습니다.
  - .err 의 "remain" 도 적습니다.
- **D2 FW_E/FW_W 31셀 속도 프로필**
  - PREDECLARATION §1.6 셀 경계와 §1.7 프레임 규칙을 씁니다.
  - 150 s 구간(900.1 s 부터 53개)마다 셀별 차량 가중 평균 속도(Σv/Σn)를 구합니다.
  - B1(FW_E 셀 8–13)·B2(FW_E 셀 19–24) 붕괴 시각 = 구역 가중 평균 속도가 60 km/h 미만인 첫 150 s 구간의 시작. 60 미만인 구간 수도 적습니다.
  - FW_W 는 셀별로 60 미만인 첫 구간을 적습니다.
  - 셀 0 혼잡 비율(2a 통계량 A)도 두 방향 모두 미리보기로 적습니다. 구속 판정은 2a 재실행이 냅니다.
- **D3 진출·합류 램프 유량**
  - 2a·2b 재실행용으로 만드는 EO `flows_30s.csv` 의 포트별 진출·합류 대수를 900 s 로 묶어 적습니다.
  - `scan.json` `region_vh` 의 `offramp` 와 `onramp:RM_C*` veh·h 도 적습니다.
- **D4 총량**
  - 도시 Ω: `sum(region_omega_vh['urban_omega'])`
  - Ω TTT: `totals.omega_ttt_veh_h`
  - all TTT: `totals.all_ttt_veh_h`
  - all + 미삽입: all TTT + `uninserted.json total_veh_h`
  - 표 형식은 `reports/gates_5seed/scripts/g5_scan.py` 와 같게 합니다: 시드별 값, 평균 이동, v3c1 sd, 이동/sd. 표시 규칙은 두지 않습니다.
- **D5 .err 분해**
  - 제거가 많은 링크 상위 10개
  - `scan.json err.removals_by_region`
  - 입력별 remain

## 5. 이 선언을 바꿀 때
- 동결 뒤에 바꿀 일이 생기면 `reports/AMENDMENT_v3c2_nc.md` 에 적습니다: 바뀐 부분, 이유, 결과를 본 전인지 뒤인지, 새 sha.
- 결과를 본 뒤에 바꾼 기준은 판정에 쓰지 않습니다. 원래 선언으로 낸 판정을 함께 보고합니다.
- 참고: v3c2 의 DSD 110 은 v3c1 것(98–140 km/h)입니다. 64cf 의 DSD 110 은 75–145 km/h 입니다. 따라서 v3c2 의 입구 거동은 64cf 런과 수치가 같을 것으로 기대하지 않습니다 [추론].
