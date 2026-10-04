# v3c3 빌드 독립 점검 (2026-10-01)

- 표기: **[실행]** 이번에 내 코드로 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단
- 대상: `reports/V3C3_BUILD.md`, `launch_lines_nc.txt`(sha `914ecfb8…`), `reports/gb1_predeclaration.md`(sha `02457383…`), 여섯 시드 망·prepared
- 내 코드: `reports/build_check/v3c3_independent_check.py`(sha `77aeb91c13a3be93…`)
  - 표준 라이브러리만 씁니다. 빌더 스크립트는 import 하지 않았습니다.
  - 결과: `reports/build_check/v3c3_independent_check.json`(sha `43fee374…`, 10:36:51 KST), **검사 39개 모두 OK**
- 읽기 전용으로 지켰습니다. 쓴 곳은 `reports/build_check/` 와 이 파일, 스크래치패드뿐입니다.
  - s37: v3c2 **source** 망(입력)과 v3c3 s37 prepared 입력만 읽었습니다. `20260930_v3c2/s37_v3c2nc` 는 열지 않았습니다. s37 prepared 는 v3c3 s31 과 대조했습니다.

## 판정

| 구분 | 개수 | 요지 |
|---|---:|---|
| **blocking** | **0** | NC 런을 무효로 만들 결함을 찾지 못했습니다 |
| nonblocking | 6 | s37 도구 허용 여부(N19 대 U2-c), 다른 세션의 GA 재생과 겹침, judge 시점, 재발사 시 로그, 표기 두 가지 |

## 1. 망: v3c2 대비 바뀐 것은 블록 3개뿐 [실행]

여섯 시드 모두 아래가 참입니다(검사 N1–N5).

- **핀**
  - v3c2 source sha = v3c2 영수증 = e3 `v3c2_sha256`
  - v3c3 source sha = **e3 `candidate_sha256`**(s31 `3de889f0…`) = v3c3 영수증
  - prepared 망 = source(바이트 동일)
- **순수 삽입**
  - 내 스캐너가 v3c2 에서 분포 80/90/100 의 닫는 줄 끝을 찾았습니다: 오프셋 805021/805613/806042, 각각 5000/5015/5025 행 앞, 바로 뒤는 85/100/110.
  - 정방향: 그 자리에 계획 JSON 텍스트를 넣은 결과 = v3c3(바이트 동일)
  - 역방향: v3c3 에서 81/91/101 블록을 잘라낸 결과 = v3c2(바이트 동일)
  - +655 B 이고, difflib 는 insert 3개·18행뿐입니다. 101 을 5023 행으로 보여 주는 것은 빌더가 공개한 표시상 모호함입니다. 바이트 대조로는 5025 행 앞이 맞습니다.
- **분포**
  - 44 → 47 개입니다. 순서는 80,81,85 / 90,91,100 / 100,101,110 입니다.
  - 새 번호를 빼면 번호 목록이 v3c2 와 같습니다.
  - ElementTree 로 보면 최상위 절 가운데 다른 것은 `desSpeedDistributions` 하나입니다. 점은 (0,80)(1,82) / (0,90)(1,92) / (0,100)(1,102), 이름은 "81 km/h" 등입니다.
  - CR 은 0개입니다. 블록과 같은 LF 형식입니다.
- **시드 간 차이**: v3c3 는 31013 행 randSeed 하나뿐이고, v3c2 30995 행의 차이와 같은 내용입니다(+18).
- **영수증**: `v3c3_edit_receipt.json` 의 `hex` 바이트 = 계획 텍스트 = 삽입 바이트(P3)

## 2. N1F 2단계 블록과 바이트 동일 [실행]

- **2단계 16개**(4시드 × c100f/c80f × source/prepared)
  - 81/91/101 블록이 v3c3 와 바이트까지 같습니다.
  - 오프셋도 같습니다(v3c3 기준 805021/805830/806476).
  - 블록 앞뒤 600 B 문맥도 같습니다.
  - 파일 sha 16개가 모두 N1F 계획 JSON(`d0e8fdba…`)에 들어 있습니다(F1).
- **1단계 16개**(c90f/c90r × source/prepared): 블록 91 이 같습니다(F2).
  - 빌더 보고의 "8개"는 source 만 센 것입니다(`v3c3_build_checks.json` `checks/n1f_networks/facts/stage1`). 모순은 아닙니다.

## 3. 번호 81/91/101 — 비어 있었나 (검토 N12) [실행]

- **v3c2 에는 분포 81/91/101 이 없습니다**(C1).
- 같은 번호를 쓰는 다른 종류의 객체는 있습니다. 링크, dataCollectionPoint, queueCounter, desSpeedDecision 81/91/101, signalController 101 등입니다(`facts.number_collision`).
  - 객체 종류마다 번호 공간이 따로라서 충돌이 아닙니다 [읽음·추론].
  - desSpeedDecision 81/91/101 은 FW_W VSL 표지(`RW_VSL_RW_FW_W_S1/S4/S6…`)입니다. v3c3 4656/4720/4800 행에 있고, 셋 다 `desSpeedDistr="110"` 입니다. 삽입 지점(5000 행 이후)보다 앞이라 행 번호와 바이트도 바뀌지 않았습니다.
- `desSpeedDistr` 가 가리키는 값은 v3c2·v3c3 모두 {25, 30, 40, 60, 70, 110(307), 1001–1029} 입니다. **81/91/101 을 가리키는 것은 0개**이고, 값 집합도 같습니다(C2).
  - 이름에 speed/distr 가 들어간 속성 가운데 값이 101 인 것은 `shirtColorDistr`·`colorDistr1` 뿐입니다. 이것은 colorDistribution 101 을 가리킵니다.
- 따라서 NC 런에서 번호 겹침은 아무 역할도 하지 않습니다. CSV 가독성 문제(`dsd_no=91,…,speed_kph=91`)는 K5/CONTRACT 단계의 몫이고, 빌더도 그렇게 적었습니다(`V3C3_BUILD.md:95-97`).

## 4. prepared 와 러너 프로필 [실행]

여섯 시드 모두 통과했습니다(R1–R2).

- **prepared.json**
  - `network` = `…\20261001_v3c3\s<S>_v3c3nc\prepared\network\baseline_s<S>_v3c3nc.inpx`
  - `source_network` = v3c3 source, sha = §1
  - `seed` = `randSeed` = S
  - native_preserve, terminal 9000, 기록 5 s, fzp_only, 수요·명령 0행, simRes 10, simPeriod 9001
  - `network_variant` 는 v3c3 이고, base_variant 는 v3c2, 영수증 sha 는 `b1bd1fd5…` 입니다.
- **핀**
  - `snapshot_sha256` 45개(망 + 자산 43 + vehicle_recording.csv)를 지금 다시 해시했고 모두 일치합니다. 러너도 발사 때 같은 검사를 합니다(`fast_nc_run.ps1:24-26`).
  - `inputs` 도 모두 일치합니다.
  - prepared/network 에는 inpx 1개 + 자산 43개만 있습니다. `.err`·`.results` 는 남아 있지 않습니다.
  - 자산은 v3c2 source 자산과 바이트가 같습니다.
- **v3c2 같은 시드와 대조**(fit 5시드)
  - 경로 토큰을 바꾸면 다른 키는 `source_network_sha256`, `inputs`, `snapshot_sha256`, `network_variant` 뿐입니다. 망 sha 와 변형 기록 때문입니다.
  - 키 순서가 같습니다. csv 2개도 바이트가 같습니다.
  - `dryrun_check.txt` 는 경로를 바꾸면 v3c2 와 같습니다.
  - 자산 sha 값도 v3c2 와 같습니다.
- **s37**: v3c3 s31 과 대조했습니다. 차이는 randSeed, 망 sha, `seed_role=held_out` 뿐입니다. csv 는 RandSeed 행만 다르고, 드라이런 필드는 arguments 를 빼고 같습니다.
- **러너**
  - sim3 의 `fast_nc_prepare.py` `eb1bd0f0…`, `fast_nc_run.ps1` `269345da…`, `fast_nc_runner.vbs` `bf07acda…` 가 핀과 같습니다.
  - v3c2 fit 5시드 run.json 의 `runner_sha256` 도 모두 `bf07acda…` 입니다.
  - 드라이런 arguments 는 `… baseline_s<S>_v3c3nc.inpx … prepared … run <S> 9000 native_fzp_only` 입니다.
- **스크립트 파생**: `v3c3_prepare.py` 와 `v3c2_prepare.py` 의 diff 를 직접 봤습니다. 바뀐 것은 경로·태그·영수증·변형 이름·문서 문자열·부모 핀뿐이고, `prepare_native_preserve` 호출은 그대로입니다 [실행 difflib].

## 5. 발사 줄 [실행]

- **줄과 순서**
  - 줄은 6개이고 순서는 s31, s41, s43, s47(묶음 A) → `# --- batch B` → s53, s37 입니다.
  - 각 줄은 v3c2 `launch_lines_nc.txt` 같은 시드 줄에서 `20260930_v3c2→20261001_v3c3`, `v3c2nc→v3c3nc` 를 바꾼 것과 정확히 같습니다.
- **명령 형식**: `cmd.exe /c powershell.exe … -File D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1 -Prepared <seed>\prepared -Output <seed>\run -Execute -MinimumFreeGiB 8 -AllowConcurrent > <seed>\launch.log 2>&1`
  - `-Seed`·`-Python` 이 없습니다. v3c2 와 같습니다.
- **경로**
  - 경로는 ASCII 이고 공백과 따옴표가 없습니다. 그래서 WMI 의 홑따옴표 CommandLine 에 안전합니다.
  - Output 6개가 모두 다릅니다.
  - 지금 `run\`·`launch.log` 는 하나도 없습니다.
  - 러너는 기존 Output 이 있으면 거부합니다(`fast_nc_run.ps1:53`).
- **cwd**: 헤더의 `CurrentDirectory='D:\VISSIM_runs\20261001_v3c3'` 이고, 이 폴더가 존재합니다.
- **환경**
  - 10:36 기준 VISSIM·cscript 프로세스는 0개입니다.
  - D: 여유는 952 GB 입니다. v3c2 FZP 가 약 1.14 GB/런이므로 충분합니다.

## 6. GB-1 사전 선언 [실행·읽음]

- **고정 상태**
  - `.sha256` 파일 값 = 실제 sha `024573832b23…` 입니다. 기록 시각은 10:25:14 KST, 파일 mtime 은 10:25:07 입니다.
  - 내 점검 시각(10:36:51)에 v3c3 `run\`·`launch.log`·`gb1_result*`·`gb1_verdict*`·`AMENDMENT_gb1*` 이 모두 없었습니다. 그러므로 선언은 어떤 런보다 앞섭니다.
- **완전성**: 과제와 검토 N9 의 요구가 모두 있습니다.
  - payload 정의: 첫 바이트부터 첫 `$VEHICLE:` 줄 끝(CR LF 포함)까지를 빼고, 나머지 EOF 까지를 비교합니다(`gb1_predeclaration.md:58-67`).
  - 가린 헤더: `* File: `·`* Date: ` 두 줄만 빼고 바이트로 비교합니다. 빌드 줄 `* PTV Vissim: 2020.00 [14]` 가 여기 들어갑니다(:68-71).
  - File 줄 양성 확인(:72-74)
  - `.err` 3개 + 사본(:76-82)
  - run.json(:84-90)
  - 전제 조건: `runner_sha256` = `bf07acda…` 이고 두 런이 같을 것, VISSIM200.exe 버전과 sha(:92-99)
  - s37 은 단어만 출력하는 봉인 판정(:122-134)
  - 실패하면 STOP(:142-148)
- **정의 재현**(내 코드, v3c2 s31 머리 64 KiB만 읽음)
  - 헤더는 38줄, 4,028 B 이고 가린 헤더 sha = 기준값입니다(G2).
  - File 줄 형식은 `* File: D:\VISSIM_runs\20260930_v3c2\s31_v3c2nc\prepared\network\baseline_s31_v3c2nc.inpx` 입니다. 선언이 v3c3 에 기대하는 형식과 같습니다.
- **기대값**: 선언 표의 payload sha 5개 = `gb1_v3c2_reference.json` = v3c2 추출 영수증 `nc_analysis/eo/s<S>_v3c2nc_extraction_receipt.json` 입니다(G1).
- **`.err` 가 망 바이트 위치에 의존하지 않는지**(v3c2 s31 세 파일, G3)
  - 경로, 날짜·시각, `line`/`offset`/`byte`, `.inpx`, 백슬래시 토큰이 0개입니다.
  - 내용은 객체 키로만 적힌 경고입니다. 예: 결정 1102, 차량 번호, SC 9101–9108.
  - 그래서 +18행 이동 때문에 ERR_LOAD/ERR_SIM 이 거짓으로 달라질 위험은 없습니다 [실행·추론].
- **도구 `scripts/gb1_identity.py`(sha `6e19cad0…`)** [읽음]
  - FZP 분할(:136-181)이 선언 정의와 같습니다.
  - `expected_file_line` 은 `'* File: ' + str(Path)` 이므로 백슬래시 형식입니다(:184-185).
  - 결과 파일은 만들기만 하고 덮어쓰지 않습니다(:97-104).
  - 봉인 모드는 예외를 문구 없이 ERROR 로 바꾸고, `[A-Z0-9_]+: WORD` 줄만 냅니다(:328-368).

## 7. nonblocking

1. **s37 해시 도구: 검토 N19 대 U2-c** [읽음]
   - 승인은 "U1–U12 권고값"과 "검토 nonblocking 노트"를 함께 받았습니다. 그런데 N19(`REPIN_V3C2_PLAN_REVIEW.md:223-224`, 허용하지 않음)와 U2-c 권고(`REPIN_V3C2_PLAN.md:474`, 허용)는 서로 반대입니다.
   - 선언은 허용을 택했고 대체 경로를 미리 적었습니다(`gb1_predeclaration.md:132-134`).
   - **`sealed` 를 돌리기 전에** 메인 세션이 사용자 선택을 확인하기를 권합니다.
   - 또 `sealed` 는 payload 만이 아니라 11개 항목(ERR_*, RUN_JSON_V3C2 포함)과 ENVIRONMENT 를 단어로 냅니다. 과제 문구("payload hash equal/not-equal only")보다 넓지만, 내용·해시는 내지 않습니다.
2. **다른 세션의 GA 재생과 겹침** [실행·읽음]
   - 10:36 에 `reports/k1k6/n1` 체인이 돌고 있었습니다: `n1_chain.py`, 어댑터, `sdmpc_tangent_worker.py`(`D:\VISSIM-merge\sim3-n31-v3c3`).
   - 계획 §6.2 는 GA 재생을 fast_nc 런과 겹치지 않게 두라고 합니다(`REPIN_V3C2_PLAN.md:407`). 러너가 첫 FZP 진행 전 300 s 에서 런을 죽이기 때문입니다(`fast_nc_run.ps1:140`).
   - 이 경우 런은 `completed=false` 로 닫힐 뿐이고 궤적이 바뀌지는 않습니다. 단일 코어 VISSIM 은 결정적이기 때문입니다 [추론]. 무효가 아니라 재발사 위험입니다.
   - 묶음 A 는 그 체인이 쉬는 때 띄우기를 권합니다.
3. **`judge` 실행 시점**
   - 결과 파일은 덮어쓰지 않습니다(`gb1_identity.py:97-104`). 그래서 런이 끝나기 전에 `judge` 를 돌리면 FAIL 파일이 남고, 그 파일은 AMENDMENT 로만 바꿀 수 있습니다.
   - 해당 시드 run.json 에 `finished` 가 있고 `completed` 가 true 인 것을 본 뒤에 돌리기를 권합니다.
4. **재발사할 때 로그**
   - `> launch.log` 리다이렉트는 러너의 기존 Output 거부(`:53`)보다 먼저 실행됩니다. 그래서 재발사하면 옛 `launch.log` 를 덮어씁니다.
   - 재발사 전에 `run\` 과 `launch.log` 를 함께 옆으로 옮기십시오. 발사 줄 머리말도 같은 내용입니다.
5. **표기 두 가지**
   - 빌더의 "N1F 1단계 망 8개"는 source 만 센 수입니다. prepared 를 넣으면 16개이고 모두 같습니다.
   - 선언 본문에는 시각이 날짜(KST)까지만 있고, 시:분은 `.sha256` 사이드카에 있습니다(10:25:14). 순서 증빙에는 발사 시각 기록(WMI 로그, run.json `started`)을 함께 남기십시오.
6. **같은 루트를 쓰는 다른 세션**: `reports/k1k6/` 의 GA 자료가 같은 `reports/` 아래에 있습니다. GB-1 도구의 파일 이름(`gb1_*`)과 겹치지 않음을 확인했습니다.

## 8. 하지 않은 것

- VISSIM·cscript 시작과 종료, 발사, 기존 런 폴더 쓰기, 코드·작업 트리 변경, git, `D:/VISSIM-merge/frozen/*` 접근, 금지 시험 7종 실행을 하지 않았습니다.
- s37/59/61/67 결과 열람, `gb1_identity.py` 실행도 하지 않았습니다.
- v3c2 출력에서 읽은 것은 fit 시드 s31 의 FZP 머리 64 KiB, s31 `.err` 3개, fit 5시드 run.json 의 `runner_sha256`, 추출 영수증의 `payload_sha256` 입니다.
- 오늘 바뀐 v3c2 파일은 `reports/repin/` 의 계획·검토·증거뿐입니다(09:05–09:39). 그 밖의 v3c2 트리(s37 제외)는 오늘 바뀐 파일이 0개입니다 [실행].
