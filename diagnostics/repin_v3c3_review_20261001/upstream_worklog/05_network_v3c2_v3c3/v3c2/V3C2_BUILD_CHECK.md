# v3c2 구축·prepare·발사 줄·사전 선언 독립 검증 (2026-09-30)

태그: [실행] 이번에 제 코드로 확인 / [읽음] 파일·코드를 읽어 확인 / [추론] 시험하지 않은 판단.
검증 코드는 제가 새로 짰고 빌더 코드는 쓰지 않았습니다. 위치는 세션 스크래치패드 `v3c2_check/` 입니다(`net_check.py`, `prep_check.py`, `launch_check.py`, `g5_recount.py`, 결과 `net_check.json`, `prep_check.json`).
이 폴더에서 쓴 파일은 이 보고서 하나뿐입니다.

## 판정
- **blocking 0건.** NC 런을 무효로 만들 결함은 찾지 못했습니다.
- 비차단 관찰은 7건이고 §6 에 적었습니다.

## 1. 망 diff: v3c1 → v3c2, 여섯 시드 모두 [실행]
- **입력 sha.** v3c1 원본 sha 는 메모리 노트 값(s31 2577209b / s41 226baa37 / s43 b8e7cf1f / s47 ec0cd81d / s53 385f40da / s37 3eb06c63)과 같습니다. v3c1 prepared 사본과도 같습니다.
- **행 diff**(`difflib.SequenceMatcher`, 바이트 행 단위). 여섯 시드가 같은 세 덩어리입니다.
  - `insert` v3c1 31195 앞 → v3c2 31195–31201: 7행, 391 B, sha `82c11cd5…`
  - `replace` v3c1 31439–31444 → v3c2 31446–31451 (입력 1098)
  - `replace` v3c1 31449–31454 → v3c2 31456–31461 (입력 1099)
  - 바뀐 12행은 모두 ` vehComp="14" ` 를 ` vehComp="1" ` 로 되돌리면 옛 행과 바이트가 같습니다. 그 밖의 변화는 0건입니다.
  - 크기는 +403 B(391 + 12) 입니다.
- **XML 트리 diff**(ElementTree, 재귀 비교, 공백 tail 무시): 13건으로, 선언한 변경과 같습니다.
  - `vehicleCompositions` 에 자식 no=14 삽입 1건
  - `vehicleInput[no=1098]`·`[no=1099]` 의 `timeIntervalVehVolume[0..5]` 에서 `vehComp` 1 → 14, 12건
- **입력 1098/1099.**
  - 링크(74/26)와 volume 은 그대로입니다.
  - 구간은 입력당 6개(`timeInt` 1 0 … 1 4500000)이고, **6개 모두 vehComp 14** 입니다.
- **vehComp 사용 수.**
  - v3c1: 1 = 180, 4 = 6, 10 = 6, 11 = 6, 12 = 6
  - v3c2: 1 = 168, 14 = 12, 나머지는 그대로
  - 구성 14 를 쓰는 것은 1098·1099 뿐입니다.
- **번호 14.** v3c1 구성 번호는 1–13 이라 14 가 비어 있었습니다. 번호와 이름("Freeway entry DSD110")을 그대로 썼습니다.
- **시드 설정.** 여섯 시드 모두 `<simulation>` 속성 전체가 v3c1 같은 시드와 같습니다.
  - randSeed = 시드 번호, simRes 10, simPeriod 9001, numRuns 1
  - 루트 `<network>` 속성(version 702, 2020.00-14)도 같습니다.
- **시드 파일끼리.** v3c2 s31 과 다른 시드는 30995 행(randSeed)만 다릅니다.
- **영수증 대조.** 영수증 `v3c2_edit_receipt.json` 의 입력·출력 sha, 12개 치환 오프셋(v3c1/v3c2), 블록 오프셋 2930291 을 여섯 시드 파일에서 바이트로 확인했습니다. 모두 맞습니다.
- `reports/v3c2_build_checks.json` summary 는 19/19 참입니다.

## 2. 구성 14 vs 64cf [실행]
- **64cf 원본.** `D:/VISSIM_runs/vsl_repro_s29/source/vsl_seed29_none.inpx` 의 sha 는 `64cf5f55fe99…` 이고, 구성 14 는 31327 행입니다.
- **요소 비교.**
  - v3c2 삽입 블록의 공백을 걷어낸 바이트가 64cf 요소 바이트(388 B, sha `c86d5382…`)와 같습니다.
  - ElementTree 시그니처(태그, 속성, 자식)도 같습니다.
  - 내용: (100, 0.806, DSD 110), (150, 0.1, DSD 110), (200, 0.094, DSD 110)
- 차종 100/150/200 정의는 64cf 와 같습니다.
- **64cf 의 구성 14 사용처.** 1098·1099 의 6+6 구간뿐입니다. v3c2 사용처와 같습니다.
- **DSD 110 은 v3c1 과 같습니다(98–140, v3c2 5025–5033 행).** 64cf 는 75–145 입니다(64cf 5468–5476 행). 64cf 는 옮기지 않았고, 작업 지시("no DSD change", "our DSD 110 = 98–140")와 맞습니다.
- **64cf 1099 수량.** 64cf 는 8870.4 … 로 v3c1 의 4300 … 과 다릅니다. v3c2 에는 옮기지 않았고, 이것이 맞습니다.
- **[읽음] 입구 링크의 희망속도 결정.** 모두 클래스 10/20/30/70 에 DSD 110 을 줍니다. 구성 14 와 충돌하지 않습니다.
  - link 74 는 11.5–11.9 m(결정 36–39)
  - link 26 은 1.6–2.6 m(결정 40–42)
  - 40 m 의 VSL S0 결정(43–46, 75–77)
  - 출처: v3c2 4320–4400, 4616–4632 행

## 3. prepared 폴더 vs v3c1 NC [실행]
여섯 시드 각각 v3c2 `prepared.json` 을 v3c1 같은 시드의 `prepared.json` 과 비교했습니다.
- **키.** 키 순서가 같습니다. 달라진 키는 7개입니다: `network`, `source_network`, `source_network_sha256`, `inputs`, `snapshot_sha256`, `network_variant`, `concurrent_identity_network_stem`.
  - 경로(`20260927_v3c1` → `20260930_v3c2`, `s<n>_v3c1nc` → `s<n>_v3c2nc`)와 망 sha 를 바꿔 넣으면 `network_variant` 하나만 다릅니다.
- **러너 프로필이 같습니다.**
  - mode `native_preserve`, fzp_only true, 기록 간격 5 s, terminal 9000
  - demand_rows 0, command_rows 0
  - traffic_settings_policy, allowed_runtime_settings, tail_demand, demand_variant, saved_simulation 이 모두 같습니다.
- `native_simulation.csv`(RandSeed = 시드, SimRes 10, NumRuns 1)와 `vehicle_recording.csv`(5)는 v3c1 과 바이트가 같습니다.
- **망 참조.** `network` 은 `…\s<n>_v3c2nc\prepared\network\baseline_s<n>_v3c2nc.inpx` 입니다. 지금 그 파일의 sha 가 v3c2 표의 sha 와 같습니다(source 사본과도 같음).
- **핀 45개 전부 재해시.** 불일치 0, 누락 0 입니다. 모두 v3c2 prepared 아래에 있습니다. `fast_nc_run.ps1:24-26` 이 발사 때 같은 검사를 합니다.
  - inputs 핀 44개도 v3c2 source 와 모두 맞습니다.
- **자산.** 자산 44개(sig/jpg 43 + vehicle_recording.csv)는 이름과 sha 가 v3c1 과 같습니다.
- **폴더 구성.** prepared 폴더는 `native_simulation.csv, network, prepared.json, vehicle_recording.csv` 입니다. network 는 44개 파일이고 남는 것도 빠진 것도 없습니다.
- **`dryrun_check.txt`.** 경로를 바꿔 넣으면 v3c1 과 문자열이 같습니다. 인자는 `… baseline_s<n>_v3c2nc.inpx … <seed> 9000 native_fzp_only` 입니다.
- **러너 파일은 v3c1 NC 때와 같습니다.**
  - sha: `fast_nc_run.ps1` 269345da / `fast_nc_prepare.py` eb1bd0f0 / `fast_nc_runner.vbs` bf07acda
  - v3c1 prepare checks 에 기록된 값, v3c1 fit 런 `run.json` 의 runner_sha256 과 같습니다.
  - 파일 수정 시각은 2026-09-22 로, v3c1 런보다 앞섭니다.
- **[읽음] 러너가 망에 쓰는 것.** 네이티브 경로는 기록 설정, SimPeriod·SimBreakAt·UseMaxSimSpeed 만 씁니다(`fast_nc_runner.vbs:216-282`). 시드 일치 여부를 검사합니다(`:234`). 환경변수 의존은 없습니다.

## 4. 발사 줄 `launch_lines_nc.txt` [실행]
- **v3c1 원본과의 대조.** 각 줄은 v3c1 원본(batch1 3줄, WMI batch2 s47/s53, s37 로그 줄)에서 경로만 바꾼 것과 문자열이 같습니다(6/6).
- **순서.** A = s31, s41, s43, s47(8–11 행), B = s53, s37(13–14 행)
- **경로.**
  - `-Prepared` 는 각 시드 자기 폴더를 가리키고, 폴더가 있습니다.
  - `-Output …\run` 과 `launch.log` 는 여섯 시드 모두 **아직 없습니다**(18:21 확인). 덮어쓸 위험이 없습니다.
  - 러너도 `-Output` 폴더가 이미 있으면 거부합니다(`fast_nc_run.ps1:53`).
  - 로그 파일 6개는 서로 다릅니다.
- **형식.**
  - 작은따옴표와 공백 경로가 없어서 `Invoke-CimMethod` 의 `CommandLine='…'` 에 그대로 넣을 수 있습니다.
  - 파일은 ASCII 전용이고 CRLF 입니다.
  - CurrentDirectory `D:\VISSIM_runs\20260930_v3c2` 폴더가 있습니다.
- **동시 실행 식별.** 망 파일 이름이 시드마다 달라서, `-AllowConcurrent` 아래에서 창 제목으로 자기 VISSIM 을 찾는 방식(`fast_nc_run.ps1:119-121`)이 충돌하지 않습니다.
- **자원.** D: 여유는 896.5 GiB 로 요구치 8 GiB 를 넘습니다. 18:21 기준 VISSIM 0개, cscript 0개입니다.

## 5. 관문 사전 선언 [실행]
- **sha 와 시각.**
  - `gate_predeclaration_v3c2_nc.md` 의 sha256 은 `2aa92d425a43000e19ac0a7cc6a88d2ed1256578dba73527978d3843c0e2e167` 로, `.sha256` 파일과 작업 지시 값이 같습니다.
  - 수정 시각은 18:13:19 이고, `.sha256` 기록은 18:13:34 입니다.
  - v3c2 `run\`, `launch.log`, `analysis\` 는 지금(18:21)도 없습니다. 그래서 **선언은 어떤 런보다도 앞섭니다.**
- **인용한 sha 가 모두 실제 파일과 같습니다.**
  - 영수증, build_checks, prepare_checks, 발사 줄, 여섯 망
  - 정적 점검 `PREDECLARATION.md` `a992341e…`
  - `fzp_pass.py` `011a2462…`. 인용한 106–111 행이 실제로 0–40 m 평균 속도 코드입니다.
  - `stage1_scan.py` `651c4f51…`, `stage1_uninserted.py` `19eba94e…`
- **완결성.** G1–G5 는 모두 판정 자료, 정의, 통과 조건을 갖추고 있습니다. 판정 뒤 조치(통과·탈락), 봉인(s37), 수정 절차(AMENDMENT), 사전 노출 공개도 있습니다.
- **G2 기준을 다시 확인했습니다.**
  - v3c1 fit 5시드의 `run/` 과 `prepared/network/` 로드 .err 가 모두 200 B, sha `d1ee825c…` 입니다.
  - `VISSIG_Controller.dll.err` 는 모두 464 B, sha `f144ab0c…` 입니다.
  - 64cf 로드 .err 도 `d1ee825c…` 입니다.
- **G3 기대값.** v3c1-s31 FZP 첫 프레임은 5.10, 마지막은 8995.10 으로 선언과 같습니다.
- **G5 허용치를 다시 셌습니다**(cp949 로 읽고 오류는 대체, 제 정규식).
  - X_lc = 279/343/292/244/294
  - X_rm = 282/346/293/249/295(next-link 3/3/1/5/1, 그 밖의 removed·deleted 0)
  - X_Z = 1/2/0/1/1(전부 link 26 @3420.4)
  - 범위, T(101/99/4), 시드별 한도가 모두 선언 표와 같습니다.
- **G4 는 이번에 다시 계산하지 않았습니다.** v3c1 참고값(29.6–31.7 / 15.5–22.6)은 판정에 쓰지 않는 참고치라서 [읽음] 으로만 남깁니다.

## 6. 비차단 관찰
1. **prepared.json 의 서술 문구가 헷갈립니다.** `network_variant.edits` 에 "64cf network <경로>, sha256 c86d5382…" 라고 적혀 있는데, 이 값은 64cf **파일** sha(`64cf5f55…`)가 아니라 **구성 14 요소** sha 입니다. 러너는 이 필드를 읽지 않으므로 런에는 영향이 없습니다. 기록을 정정할 때 "element sha256" 으로 고치면 됩니다.
2. **v3c2 입구 거동은 64cf 와 수치까지 같지 않을 것입니다 [추론].** DSD 110 이 64cf(75–145)와 다르기 때문입니다(v3c2 는 98–140). 이미 공개된 사항이고, 사용자 지시와도 맞습니다.
3. **G4 정의의 원본이 스크래치패드(임시 폴더)에 있습니다.** 선언 본문이 정의를 글로 다시 적어 두었으니 판정은 재현됩니다. 다만 판정 전에 `PREDECLARATION.md` 와 `fzp_pass.py` 를 v3c2 `reports/` 로 복사해 두면 임시 폴더가 정리되어도 안전합니다.
4. **G5 의 X_Z 기준 사건은 모두 link 26 @3420.4(1099 입구 링크, 진출 10479 앞)입니다.** 입구 속도가 바뀌면 이 지점의 차로변경 제거가 늘 수 있습니다. 한도 T = 4 는 절대값이 작습니다 [추론].
   - 선언은 오탈 약 10%(5시드 전체)를 공개했고, 탈락하면 사용자 결정으로 가는 구조입니다. 그래서 무효 사유는 아닙니다.
5. **묶음 A 가 좌석 4개를 다 씁니다.** 발사 순간 다른 세션이 VISSIM 을 띄우면 5번째 COM 생성이 거부됩니다(한도 4). 발사 직전에 VISSIM 0개를 다시 확인해야 합니다. 이는 발사 줄 주석에도 적혀 있습니다.
6. **G1 (i) `v3c2_build.py recheck` 는 제가 돌리지 않았습니다.** `work/` 에 파일을 쓰기 때문입니다. 대신 같은 내용을 제 코드로 독립 확인했습니다(§1).
7. **우선순위 공개.** 첫 스크립트 `net_check.py`(약 30 s)는 ctypes 핸들 타입 오류로 SetPriorityClass 가 실패했고, 보통 우선순위로 돌았습니다.
   - `prep_check.py` 는 BELOW_NORMAL(0x4000) 로 되읽기까지 확인했습니다.
   - `launch_check.py`, `g5_recount.py` 는 1–2 s 짜리 가벼운 스크립트라 따로 설정하지 않았습니다.

## 7. 지킨 것
- v3c1, vsl_repro_s29, `D:/VISSIM-merge/frozen` 은 읽기만 했습니다. 세 곳 모두 2026-09-30 이후 수정된 파일이 0개입니다 [실행 `find -newermt`].
- v3c1-s37 은 `prepared.json`, csv, `dryrun_check.txt`, 망 파일만 열었습니다. `run/`, .err, FZP, analysis 는 열지 않았습니다. v3c2 결과는 아직 없습니다.
- VISSIM·cscript 를 시작하거나 종료하지 않았습니다. 커밋과 금지된 시험 파일 실행도 없었습니다.
