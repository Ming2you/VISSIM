# 망 v3c2 구축·prepare·관문 사전 선언 보고 (2026-09-30)

태그: [실행] 이번에 명령으로 확인 / [읽음] 파일·코드에서 확인 / [추론] 시험하지 않은 판단.
경로는 `D:/VISSIM_runs/20260930_v3c2/` 기준입니다.

## 요약
1. **v3c2 를 깨끗하게 만들었습니다(stop 아님).** v3c1 대비 바뀐 곳은 두 가지뿐입니다 [실행 `reports/v3c2_build_checks.json`, 19개 검사 모두 참].
   - 구성 14 "Freeway entry DSD110" 7줄 삽입(v3c1 31195 행 앞, 391 B)
   - 입력 1098·1099 의 12개 시간 구간에서 `vehComp="1"` → `"14"`
2. **구성 14 요소의 바이트는 64cf 원본(`vsl_seed29_none.inpx:31327-31333`)과 같습니다.** 번호 14 와 이름은 v3c1 에서 비어 있어서 그대로 썼습니다. 다른 것은 요소 바깥 공백 두 곳뿐이고, 그 이유는 §2 에 적었습니다 [실행].
3. **DSD 110 은 v3c1 에 있고 바꾸지 않았습니다(98–140 km/h).** 64cf 의 DSD 110 은 75–145 km/h 로 내용이 다릅니다. 구성 14 는 DSD 를 번호로 가리키므로, v3c2 입구 차량은 v3c1 의 DSD 110 을 씁니다 [실행].
4. **prepare 와 건식 점검이 여섯 시드 모두 통과했습니다** [실행 `reports/v3c2_prepare_checks.json`, 19개 모두 OK].
   - 러너 프로필이 v3c1 NC 와 같습니다: SimRes 10, FZP 전용 5 s, 9000 s, 같은 수요.
   - 발사 줄 `launch_lines_nc.txt` 를 만들었고 **발사는 하지 않았습니다.**
5. **관문 사전 선언을 동결했습니다.** `reports/gate_predeclaration_v3c2_nc.md`, sha256 `2aa92d42…`, 18:13 KST. 동결 시점에 v3c2 런은 없었습니다. G1 은 정적으로 이미 통과했고, G2–G5 는 런 뒤에 판정합니다.

## 1. 입력과 고정값 [실행]
- v3c1 원본은 `D:/VISSIM_runs/20260927_v3c1/source/baseline_s<seed>_v3c1nc.inpx` 입니다. sha 는 영수증(`v3c1_edit_receipt.json`, `8e69013d…`)과 메모리 노트의 여섯 시드 값과 같습니다.
  - s31 2577209b / s41 226baa37 / s43 b8e7cf1f / s47 ec0cd81d / s53 385f40da / s37 3eb06c63
- 64cf 는 `D:/VISSIM_runs/vsl_repro_s29/source/vsl_seed29_none.inpx` 입니다(sha `64cf5f55fe99…`). 두 망의 헤더는 같습니다: `version="702" vissimVersion="2020.00 - 14 [95957]"`.
- v3c1 에서 확인한 것
  - 입력 1098 = link 74, 1099 = link 26 입니다. 두 입력 모두 6개 구간 전부 `vehComp="1"` 입니다(`baseline_s31_v3c1nc.inpx:31439-31444`, `:31449-31454`).
  - 구성 1 은 (100, 0.806, DSD 40), (150, 0.1, DSD 40), (200, 0.094, DSD 30) 입니다. DSD 40 = 40–45, DSD 30 = 30–35 km/h 입니다.
- 64cf 에서 확인한 것
  - 구성 14 는 같은 세 차종과 같은 relFlow 에 DSD 110 입니다.
  - 1098/1099 의 12개 구간에서만 쓰입니다. 다른 입력은 쓰지 않습니다.
  - 차종 100/150/200 정의 행은 v3c1 과 바이트가 같습니다.

## 2. 무엇을 바꿨나 (`v3c2_edit_receipt.json`, sha `cf8b0cb2…`)
- **E1 구성 14 삽입** (`scripts/v3c2_build.py:335-355`)
  - 위치: `\t</vehicleCompositions>` 행(v3c1 31195) 앞, 구성 13 "Emergency Vehicle" 다음
  - 내용: `\t\t` + 64cf 요소 바이트(388 B) + `\n` 을 통째 행으로 넣었습니다(7줄, 391 B, 블록 sha `82c11cd5…`). v3c2 에서는 31195–31201 행입니다.
- **E2 속성 12개 교체**
  - ` vehComp="1" ` → ` vehComp="14" `
  - 위치: v3c1 31439–31444 행(1098)과 31449–31454 행(1099). v3c2 에서는 +7 행입니다.
  - 영수증 `edits.replaced_attributes` 에 행 번호, 바이트 오프셋, 옛 행, 새 행이 모두 있습니다. 여섯 시드의 오프셋은 같습니다.
- **64cf 와 다른 공백 두 곳(피할 수 없는 문맥)**
  - 64cf 는 구성 14 시작 행 들여쓰기가 탭 1개이고, `</vehicleCompositions>` 행이 탭 2개입니다(64cf 생성기의 흔적).
  - 그 공백까지 옮기면 기존 `</vehicleCompositions>` 행을 바꾸게 됩니다. 그래서 요소 바이트만 옮기고 파일 자체의 들여쓰기(탭 2개 / 탭 1개)를 따랐습니다.
  - ElementTree 로 비교하면 구성 14 는 자기 tail 을 빼고 64cf 와 같습니다 [실행].
- **옮기지 않은 것(지시: 그 밖에는 바꾸지 않음)**
  - 64cf 의 DSD 110 내용(75–145)
  - 64cf 입력 1099 의 수량(8870.4… veh/h). v3c1 은 수요 v2(4300…)를 갖고 있고, 1098 수량은 두 망이 같습니다 [실행].
- 결과 파일 크기는 +403 B 입니다(391 + 12). 시드 파일끼리는 randSeed 행(30995)만 다릅니다.

| 시드 | 역할 | v3c1 sha | v3c2 sha |
|---|---|---|---|
| 31 | fit | 2577209b | 597191ac |
| 41 | fit | 226baa37 | 2b15d51e |
| 43 | fit | b8e7cf1f | e11d19f2 |
| 47 | fit | ec0cd81d | 99689b7f |
| 53 | fit | 385f40da | c2dd1a48 |
| 37 | 봉인 | 3eb06c63 | f6b0b7d6 |

## 3. 검증 [실행]
- **세 가지 구성법이 여섯 시드 모두 바이트까지 같습니다.**
  - (a) 텍스트 편집
  - (b) ElementTree 편집: 64cf 파싱 트리에서 요소를 깊은 복사(`v3c2_build.py:357-375`)
  - (c) s31 v3c2 의 randSeed 교체
- **diff 확인**
  - 행 diff: 앞부분 동일, 7줄 삽입, 뒷부분 길이 같음. 바뀐 행은 정확히 선언한 12개이고, 각 행의 변화는 속성 하나뿐입니다(`v3c2_build.py:378-398`).
  - `difflib` 통합 diff: `+` 19, `-` 12, 두 덩어리(`reports/v3c2_vs_v3c1_s31.diff`, sha `de8981b1…`).
  - GNU `diff` 로도 따로 확인했습니다. 여섯 시드 모두 `31194a31195,31201`, `31439,31444c31446,31451`, `31449,31454c31456,31461` 입니다.
- **ElementTree 위치 비교**(`v3c_checks.struct_diff_insert`, v3c1 lib 바이트 사본): 트리 전체 차이가 선언한 14건과 같습니다.
  - 구성 13 tail `'\n\t'` → `'\n\t\t'`
  - 구성 14 삽입
  - 1098·1099 의 `vehComp` 속성 12건
- **그 밖의 확인**
  - vehComp 사용 수: `1` 이 180 → 168 개, `14` 가 0 → 12 개. 나머지 번호는 그대로입니다.
  - DSD 44개와 차종 행이 v3c1 과 같습니다.
  - 재파싱(`netv3_common.parse_inpx`) 결과
    - 결정 138개, 링크, simulation 속성이 모두 같습니다.
    - 결정 위치는 모두 (+7 행, +403 B) 만큼 밀렸습니다.
  - ElementTree 왕복과 fzp_only 재작성이 항등입니다. 그래서 prepared 스냅샷이 원본과 바이트가 같습니다.
- 다시 확인했습니다: `v3c2_build.py recheck` → ok = True(`work/v3c2_build_recheck_20260930T180453.json`).

## 4. prepare·건식 점검·발사 줄 [실행]
- `scripts/v3c2_prepare.py` 는 v3c1_prepare.py(sha `0d238e40…`)에서 파생했습니다.
  - prepare 호출은 `fast_nc_prepare.prepare_native_preserve(net, out, 9000, recording_interval_sec=5, fzp_only=True)` 로 v3c1 과 같습니다.
  - 러너 sha(prepare `eb1bd0f0…`, run.ps1 `269345da…`, vbs `bf07acda…`)가 v3c1 NC 와 같습니다.
- **같은 시드 v3c1 prepared.json 과의 대조**(v3c1 prepare verify 가 기록한 sha 로 고정)
  - mirror 키 12개가 같습니다: saved_simulation(simRes 10, randSeed, simPeriod 9001), 기록 간격 5 s, fzp_only, terminal 9000, demand_rows 0 등.
  - `native_simulation.csv` 와 `vehicle_recording.csv` 는 바이트가 같습니다.
  - 자산 43개가 같습니다.
  - demand_variant 는 복사했습니다.
  - 다른 키는 경로·sha·변형 이름 7개뿐입니다.
  - 경로와 sha 를 바꿔 넣으면 network_variant 를 빼고 전부 같습니다.
- **건식 점검**(`-Execute` 없이, 발사 형식 명령도 함께): 여섯 시드 모두 exit 0 입니다. 인자만 다르고 다른 필드는 v3c1 dryrun_check.txt 와 같습니다. `run\` 이나 `launch.log` 는 생기지 않았습니다.
- **`launch_lines_nc.txt`**(sha `eb574c1f…`)
  - 순서: 묶음 A = s31, s41, s43, s47(좌석 4개), 묶음 B = s53, s37
  - 각 줄은 v3c1 NC 발사 줄(batch1, WMI batch2, s37 로그)의 경로만 바꾼 것과 같습니다.
  - WMI `Invoke-CimMethod … Win32_Process Create`, CurrentDirectory `D:\VISSIM_runs\20260930_v3c2`
- 점검 당시 VISSIM·cscript 프로세스는 0개였습니다.
- **경계 확인**
  - 읽은 v3c1·64cf 파일의 sha 가 바뀌지 않았습니다.
  - v3c1 트리 505개 파일(s37_*, *_rm, rm_build 제외) 가운데 영수증 뒤에 바뀐 파일은 0개입니다.
  - sim3 파일에 변화가 없고, 스크립트 폴더에 `__pycache__` 가 없습니다.
- 스크래치패드 리허설(`scratchpad/v3c2/prep_rehearsal`)도 같은 19개가 모두 OK 였습니다. 그 뒤 리허설 prepared 사본은 지웠습니다.

## 5. 관문 사전 선언 (`reports/gate_predeclaration_v3c2_nc.md`, sha `2aa92d425a43000e19ac0a7cc6a88d2ed1256578dba73527978d3843c0e2e167`)
- **G1 영수증:** 선언한 변경만 있을 것. 정적으로 통과했습니다. 발사 전과 런 뒤에 recheck 와 prepared 망 sha 를 다시 확인합니다.
- **G2 로드 .err:** run 사본과 prepared 사본 모두 같은 시드 v3c1 과 바이트가 같아야 합니다. 예상되는 추가 줄은 없습니다(64cf 로드 .err 도 v3c1 과 바이트가 같음, sha `d1ee825c…`). 보조로 `VISSIG_Controller.dll.err` 도 같아야 합니다.
- **G3 완료:** run.json 이 completed, exit_code 0, 9000 s 여야 하고, FZP 가 5.1–8995.1 s 를 덮어야 합니다.
- **G4 입구 속도:** link 74 와 26 의 0–40 m 프레임 평균 속도의 중앙값(t ≥ 900.1, 빈 프레임 제외)이 fit 5시드 모두 80 km/h 이상이어야 합니다. 정의는 정적 점검 §1.7 과 같습니다. v3c1 값은 74 에서 29.6–31.7, 26 에서 15.5–22.6 입니다.
- **G5 파탄 흔적:** 차로변경 대기(X_lc), 전체 제거(X_rm), 고속도로 구역 제거(X_Z)가 시드마다 v3c1 같은 시드 + T 이하여야 합니다. T = v3c1 fit 5시드 범위 + 2 로, 각각 101 / 99 / 4 입니다.
  - 변화가 없을 때 잘못 탈락할 확률은 5시드 전체로 약 10% 입니다 [추론]. 선언에 그대로 적었습니다.
- **서술 D1–D5:** 1098/1099 미삽입 지연·삽입률, 31셀 속도 프로필과 B1/B2 붕괴 시각, 램프 유량, 도시 Ω·Ω TTT·all·all + 미삽입, .err 분해. 모두 v3c1 NC fit 5시드와 나란히, 짝 비교 없이 적습니다.
- **판정 뒤 조치**
  - 모두 통과하면 정적 점검 2a·2b 를 v3c2 NC 에 동결 방법(PREDECLARATION.md sha `a992341e…`) 그대로 다시 돌려 F10(입구)과 F11(FW_W 상류 용량)을 정합니다.
  - 하나라도 떨어지면 자동 채택도 자동 되돌림도 하지 않고 사용자 결정을 받습니다.

## 6. 공개와 주의
- **DSD 110 차이.** 사용자와 작업 지시가 말한 "our DSD 110 = 98–140" 은 v3c1 값이 맞습니다. 다만 64cf 런은 75–145 로 삽입했으므로, v3c2 입구 거동이 64cf 와 수치까지 같지는 않을 것입니다 [추론].
  - 64cf 와 같은 분포가 필요하면 DSD 변경이 따로 필요하고, 그것은 사용자 결정 사항입니다.
- **FW_W 쪽 [추론].** v3c1 의 FW_W 셀 0–5 에는 약 3 km 의 속도 구배가 있습니다(CHECK_2A §2.4). 입구 삽입 속도만 바꿔서는 link 26 G4 가 떨어질 수 있습니다. 그렇다면 F11 쪽 증거입니다.
- **재핀 [추론].** 망 sha 가 바뀌었으므로, v3c1 sha 에 핀된 폐루프 자료(5323faa, FRZ)는 v3c2 에 그대로 쓸 수 없습니다. 이번 범위 밖입니다.
- **지킨 것**
  - D:/VISSIM_runs/20260927_v3c1, vsl_repro_s29, 다른 런 폴더, 워크트리, D:/VISSIM-merge/frozen 에는 쓰지 않았습니다(루트 가드, 경계 확인).
  - 커밋, VISSIM·cscript 시작이나 종료, 금지 시험 파일 실행은 없었습니다.
  - s37 은 v3c1 의 prepared.json, csv, dryrun_check.txt 만 읽었고 런 출력은 열지 않았습니다.
  - Python 은 모두 BELOW_NORMAL(0x4000, 되읽기 확인)과 `-B` 로 돌렸습니다.
- 이번에 v3c1 fit 시드의 `_001.err`, 로드 .err, `VISSIG_Controller.dll.err` 를 읽었습니다. G5 허용치와 G2 기준을 정하려는 것이었고, 사전 선언 §1 에 적었습니다.

## 7. 파일
| 파일 | sha256 (앞 16자) |
|---|---|
| `scripts/v3c2_build.py` | 5dae8984b7947e14 |
| `scripts/v3c2_prepare.py` | b91153fcf9b2ff06 |
| `scripts/v3c_lib/netv3_common.py`, `v3c_checks.py` (v3c1 바이트 사본) | 88c6c5565d255a42, cc3fc895d65140bd |
| `v3c2_edit_receipt.json` | cf8b0cb2675cff36 |
| `reports/v3c2_build_checks.json` | 5961e92c8390db48 |
| `reports/v3c2_vs_v3c1_s31.diff` | de8981b1f89f0a62 |
| `reports/v3c2_prepare_checks.json` | 0197179c9d74ef54 |
| `reports/gate_predeclaration_v3c2_nc.md` (+ `.sha256`) | 2aa92d425a43000e |
| `launch_lines_nc.txt` | eb574c1f979db32b |
| `source/` | 망 6개 + 자산 43개(v3c1 바이트 사본) |
| `s<seed>_v3c2nc/prepared/`, `s<seed>_v3c2nc/dryrun_check.txt` | 여섯 시드 |

## 8. 다음 단계 (메인 세션)
1. `launch_lines_nc.txt` 의 묶음 A(s31, s41, s43, s47)를 WMI 로 발사합니다. 다른 VISSIM 이 0개여야 합니다.
2. 좌석이 비면 묶음 B(s53, s37)를 발사합니다.
3. 5시드가 끝나면 사전 선언대로 G2–G5 를 판정하고 D1–D5 를 서술합니다. 모두 통과하면 2a·2b 재실행으로 F10·F11 을 정합니다.
