# S-DMPC RM·TSC 실행 이력 인계 — 2026-10-24

[읽음] 사용자가 확인한 대상은 `adopted355_optimized_s29_8100`이며, 이 문서는 당시 실행본을 보존한 재현 인계다.
[읽음] 문장·표의 `[측정]`은 이번 재집계/파일 계수, `[읽음]`은 보존 파일·코드의 내용, `[추정]`은 해석이며, 원자료 안의 기존 서술은 원문 그대로다.
[읽음] 코드 브랜치는 `codex/handoff-rmtsc-20261024`, 큰 원자료 루트는 `D:/VISSIM_handoff/20261024/`이며 아래 상대경로는 이 루트 기준이다.
[읽음] Git 저장소만 받았으면 문서의 `code/`를 저장소 루트로 읽고, `derived/`의 작은 표는 `handoff/evidence/`에서도 찾을 수 있다.

## 1. “약 8%”의 정체

[측정] 같은 seed29의 무제어 대비 0–8100초 **도시도로 TTT는 8.086623%, 서측 본선만 제외한 Ω701 TTT는 8.273780%, 전체 Ω701 TTT는 6.679029% 감소**했다.
[읽음] 따라서 전체 망 또는 전체 Ω의 8% 개선이라고 부르면 안 된다.
[측정] 이 세 숫자를 낸 제어 런은 하나이며, 확인된 동일 버전의 다른 시드 반복은 없다.
[측정] 시드 평균은 이 단일 짝의 값과 같고, 시드 간 분산·신뢰구간은 모름이다.

| 근거 | 지표 | NC veh·h | joint veh·h | joint−NC | 개선율 (양수=감소) |
|---|---|---|---|---|---|
| [측정] | 동측 본선 7링크 | 2124.524111 | 1840.869556 | -283.654556 | +13.351440% |
| [측정] | 사용자 국소 19링크 | 2347.393389 | 2190.818333 | -156.575056 | +6.670167% |
| [측정] | 전체 Ω701 | 7406.171375 | 6911.511042 | -494.660333 | +6.679029% |
| [측정] | Ω 밖 관측 체류 | 1588.759653 | 1634.431264 | +45.671611 | -2.874671% |
| [측정] | 물리 망 전체 관측 체류 | 8994.931028 | 8545.942306 | -448.988722 | +4.991575% |
| [측정] | 도시도로 (진입·진출 램프 제외) | 3642.612417 | 3348.048083 | -294.564333 | +8.086623% |
| [측정] | 도시도로+진출램프 | 3695.353750 | 3385.430972 | -309.922778 | +8.386823% |
| [측정] | 동측 진입램프 체류 | 121.750500 | 206.770444 | +85.019944 | -69.831290% |
| [측정] | 서측 진입램프 체류 | 77.387278 | 87.944556 | +10.557278 | -13.642136% |
| [측정] | 양방향 진출램프 체류 | 52.741333 | 37.382889 | -15.358444 | +29.120319% |
| [측정] | Ω701 − 서측 본선 (서측 진입램프는 포함) | 6019.015639 | 5521.015528 | -498.000111 | +8.273780% |

[읽음] 정확한 Ω701 링크 목록과 535개 외부 링크는 `derived/omega_membership_exact.json`, 분류 규칙은 `derived/reporting_partition.json` 및 `analysis/original_scripts/solo355_compare_20261014.py`에 있다.
[읽음] 도시도로는 Ω701에서 양방향 본선·진입램프 8개·진출램프 8개를 뺀 물리 링크 전체이며, 짧은 연결로도 포함한다.
[읽음] 진입램프는 고속도로, 진출램프는 도시부에 배정하는 추가 보고에서 도시부 개선은 8.3868%이며, 도시도로만의 8.0866%와 다른 지표다.
[읽음] 목적함수는 Ω701 TTT이고, 이번 표의 TTT는 주행·정지 차량을 모두 세는 링크 내 체류시간이며 미삽입 대기는 포함하지 않는다.
[측정] 5초 FZP 프레임 재고를 실제 관측시각 기준 사다리꼴 적분하고 초기 t=0은 빈 망, 마지막 8095.1초 재고는 8100초까지 4.9초 유지했다.
[읽음] 마지막 잔여 차량·삭제 차량을 정상 유출로 보상하지 않으며, 이 표본 적분은 VISSIM native `TravTmTot`와 동일 정밀도의 값이 아니다.
[측정] 별도 집계기 `code/handoff/check_fzp.py`로 Ω701·7링크·19링크·망 전체를 다시 세어 기존 캐시 값과 반올림 오차 범위에서 일치했다.

### 대상과 짝 기준선

[읽음] 시각은 아래 launch.log의 실제 watchdog START/OK이며 KST이고, wrapper/freeze 시작 시각과 구분한다.

- [읽음] **joint**: `E:/VISSIM_runs/20261012_adopted355_optimized_s29_8100/sdmpc`; seed29; native 길이 8100초; 분석 0–8100초; `10-12 16:34:34  START sdmpc31_sdmpc8100_s29 attempt=1 pid=38224 / 10-12 21:22:18  OK sdmpc31_sdmpc8100_s29 attempt=1 elapsed=17264s`; 인계 `raw/joint`.

- [읽음] **nc**: `D:/VISSIM_runs/20260927_sd31_wiring9000/nc`; seed29; native 길이 9000초; 분석 0–8100초; `09-27 11:12:23  START sdmpc31_nc9000_s29 attempt=1 pid=37084 / 09-27 11:59:33  OK sdmpc31_nc9000_s29 attempt=1 elapsed=2829s`; 인계 `raw/nc`.

[읽음] 공동제어는 detached HEAD `ca181e843058872ac4726758625e5c4057daba5f`에서 수정 파일이 있는 실행본이며, 원래 FREEZE의 git status 항목은 58,227개(미추적 파일 포함)다.
[읽음] NC는 브랜치 `codex/sdmpc31-upstream-20260926`, HEAD `886a014a303dd155e05cc33041796822abbc29b0a7b`, status 1,388개인 실행본이다.
[읽음] 두 런 모두 아래 동일 64cf 망과 seed29이며, 서로 다른 코드 시점이므로 무제어 설정·수요·초기 prefix 검증을 함께 제공한다.
[읽음] 저장된 검증에서 900초 이전 FZP 431,233행, 마지막895.1초의 해시가 둘 다 `f1a0b040b711e5974615873f334d28395e7aa037de356caeda101fafcc8fbcda`였다.
[읽음] 해당 prefix 검증·망/수요 핀은 `analysis/comparison/`의 summary·execution 파일에 보존했으며 이번 작업에서 prefix를 다시 검증했다고 주장하지 않는다.

### VSL·RM·TSC의 실제 작동

[읽음] 설정상 VSL은 최적화 대상이며 OFF 설정이 아니다.
[측정] 그러나 공동제어 action CSV의 **VSL 3,630행 모두 110km/h**, 대응 readback도 모두 `110|110`이었다.
[측정] RM 440행에서 8개 중 7개 미터의 녹색이 변했고 `RM_C10644`만 항상10초였으며, 도시 신호833행에서17개 controller의 green/offset plan이 각각46–48종이었다.
[측정] 결정별 녹색·offset·readback 전체는 `derived/decision_greens.csv`, 값의 종류는 `derived/action_audit.json`에 있다.
[읽음] action CSV만으로 native 통과를 선언하지 않았고, 기존 native LDP·DSD 실행 검증을 `analysis/comparison/joint/execution.json`에 포함했다.
[읽음] 이 파일의 `native_execution_passed=true`와 별개로 `passed=false`, `native_lsa_com_coverage_passed=false`가 남아 있으며 승인된 LDP 대체를 사용했다.
[읽음] 같은 파일의 process/closure 불확인 필드를 덮어쓰지 않았고, 별도 runtime queue 영수증은 `normal_sim_done=8100`, `native_exit_code=0`, `owners_closed=true`를 기록한다.
[읽음] 실제 최적화48회 중47회 fresh,6900초1회는 계산 실패 후6750초 명령 유지이며, 이를 최적화 성공이나 전역 최적해로 부르지 않는다.
[추정] 정확한 명칭은 “VSL 최적화가 허용됐지만 실제 VSL110 유지, RM·TSC가 움직인 공동제어 실행”이다.
[추정] VSL을 아예 탐색에서 제거한 정책과 같다고 보장할 수는 없다.

### 같은 런의 외부 비용과 미삽입

[측정] Ω 밖 관측 체류는 1,588.759653→1,634.431264veh·h로 2.874671% 증가했고, 동·서 진입램프 체류도 증가했다.
[읽음] 이 체류 지표는 정지 대기만을 뜻하지 않으며, 램프 순수 대기시간과 입력별 미삽입 대기 적분은 모름이다.

| 근거 | 런/구간 | native 도로 TTT | native 미삽입 대기 | 합계 veh·h | 끝 미삽입 차량 |
|---|---|---|---|---|---|
| [읽음] | nc 0–9000 | 9654.761396 | 19290.008694 | 28944.770090 | 10857.0 |
| [읽음] | joint 0–8100 | 8545.990185 | 16423.571056 | 24969.561240 | 10217.0 |

[읽음] **NC의 native 누적값은 0–9000초 하나뿐이므로 joint의0–8100초와 합계 개선율을 계산하지 않았다.**
[읽음] joint `.err`는 입력1099의 종료 미삽입10,217대를 기록하지만 입력1098·1099 각각의 대기시간 적분은 모름이며,1098 경고가 없다는 사실로 대기시간0을 추정하지 않는다.
[읽음] joint의 관측·기하 추론 Ω 유출55,101건, 종료 Ω 재고2,072대, native 삭제229대, 미분류 내부 소실682건을 별도 보존했고, NC 대응값은54,879/2,175/233/691이다.
[읽음] 미분류 소실은 정상유출로 확정하지 않았고 5초 관측 사이 경계 통과 추론의 한계가 있다.

## 2. 코드와 실행 환경

[읽음] 실행에 사용한 원래 동결본은 `D:/VISSIM_runtime/20261012_adopted355_vsl_three/frozen/sdmpc31_ca181e84_202610121132`다.
[읽음] 원래 NC 동결본은 `D:/VISSIM_runs/20260927_sd31_wiring9000_runtime/frozen/sdmpc31_886a014a_202609271108`다.
[읽음] `evidence/original_FREEZE.json`에 전체74,076파일·49,454,490,354바이트의 파일별SHA와 status가 있고, tree hash는 `2095ad63bc1dba4c7bd74700a96b2c1809488cbd1687c7edcd12246dd8ddbcb2`다.
[측정] 인계 `code/`는 해당 실행본에서 필요한 코드·설정·입력을 바이트 그대로 복사한 부분집합이며, 복사본별 SHA는 `code/handoff/SOURCE_FILES.csv`에 있다.
[읽음] **코드 부분집합은 원래49GB 전체동결본이 아니므로 원래 FREEZE.json을 그 루트에 붙여 검증하지 않는다.**
[읽음] 당시 저장된 원본 전체 git diff는 모름이며, 대체로 원래 HEAD와 복사된 tracked파일을 비교한 `evidence/reconstructed_tracked_subset.patch`를 제공한다.
[측정] 이 재구성 diff는630개 tracked 변경을 포함하고, 복사본920개 파일은 해당 base commit에 없으며 목록은 `derived/base_comparison.json`에 있다.
[읽음] 이 patch에는 복사 범위 밖 변경·삭제를 복원했다고 주장하지 않으며, 실행 설정 자체도 base commit에 없는 파일이라 실제바이트를 별도로 보존했다.
[읽음] tracked파일의 base bytes는 `evidence/base_blobs/`, 실행 bytes는 `code/`에 있다.

| 근거 | 핵심 파일 | SHA256 |
|---|---|---|
| [측정] | evaluation/controllers/sdmpc.py | 5c1ba251a3526cafa6574459e23627e59cb96e9373ff7d1c5588bcdde3c3a0c0 |
| [측정] | evaluation/controllers/vissim_stackelberg_adapter.py | a615d8caa54c42ce709e76a4a43112cf3bebd35e8bb63da8710fce07b12ad0c8 |
| [측정] | evaluation/controllers/lane_plant_runtime.py | d774daee3ae12a58f76e660b3dc0ea919f7187e39c625000205ba57dc0cb9563 |
| [측정] | evaluation/controllers/lane_freeway_runtime.py | 29e5b96eb616217ed092bbf81987d5e5211a7c2dfcc94b72be970a236593658d |
| [측정] | evaluation/controllers/lane_urban_runtime.py | e6078a3b4b2218061f9221de5a10cf18f50ee4b262f248718966f749debc5d3b |
| [측정] | evaluation/controllers/route_choice_corridor.py | 972e9f77a5f3c79ffe9598533e426ee3edea2f20179413acc1f15b36a68d984d |
| [측정] | evaluation/controllers/urban_flow_accounting.py | b9a3df868fc7483d0e4faa60153d3a8d8181b7040fc742234648fe41e7681d0d |
| [측정] | evaluation/controllers/physical_ramp_branches.py | 0ab140ac0967348b1b475d06668965284ac2170a93a7ee963cbd80b22c4dc966 |
| [측정] | evaluation/controllers/urban_storage_guard.py | 2c24b570ca5ba6f2a81d47b9eedfde1af863713fefd9a337109e2f78b64173ab |
| [측정] | scripts/run_real_world_stackelberg_controller.vbs | 1472208893db281a90a712bcf21d6e81a8100f81f6d8b1b6cfa4b66ef1b7b024 |
| [측정] | scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1 | b56e1b368b2666fbb613eac178036db6048b5fa50d60f7ae97fb4dd0d8ecad0b |
| [측정] | diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1 | 8e95423b4b3c17b6b8ac16067c4ff14ecce2078ccfbb1eafec2e180079a9b171 |

[읽음] plant·adapter의 나머지 Python/VBS, vendor NumSim 코드, 실제 runner, 원래 평가 스크립트도 포함했으며 NumSim snapshot은 `e77b7d656a9cb6deca6cc7d8bc89dee50038f043`이다.
[읽음] 원래 평가기는 `analysis/original_scripts/`, 독립 재집계기는 `code/handoff/`이며 각 파일SHA는 전체목록에 있다.
[읽음] 아래는 `evidence/runtime/optimized_native_launch.json`에 저장된 **원래 명령의 인자 문자열 그대로**다.
[읽음] 해당 영수증은 인자 문자열을 보존하지만 실행파일 자체까지 포함한 한 줄 shell 원문은 모름이며 provenance/runner의 PowerShell 경로를 함께 제공한다.

```text
"-NoProfile" "-NonInteractive" "-WindowStyle" "Hidden" "-File" "D:\VISSIM_runtime\20261012_adopted355_vsl_three\frozen\sdmpc31_ca181e84_202610121132\diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1" "-FrozenTree" "D:\VISSIM_runtime\20261012_adopted355_vsl_three\frozen\sdmpc31_ca181e84_202610121132" "-ResultsRoot" "E:/VISSIM_runs/20261012_adopted355_optimized_s29_8100" "-StatusPath" "E:\VISSIM_runs\20261012_adopted355_optimized_s29_8100\native_status.json" "-SimPeriod" "8100" "-Seed" "29" "-Arms" "sdmpc" "-TuningRelativePath" "diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json" "-PythonExe" "C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" "-PowerShellExe" "C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe" "-DependenciesPath" "C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc"
```

[읽음] 환경 변수의 실제 기록은 `raw/joint/sdmpc/run_provenance_sdmpc31_sdmpc8100_s29.json`과 canonical runner에 보존돼 있고, RW_*를 초기화한 뒤 시뮬레이션·제어·mapping·profile·VBS 경로를 설정한다.
[읽음] runner는 `PYTHONUTF8=1`, `PYTHONDONTWRITEBYTECODE=1`, 의존성 `PYTHONPATH`, `NUMSIM_REPO_ROOT`, `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`을 사용한다.
[읽음] 당시 Python 실행 경로는 원래 명령에 있지만 **당시 Python 상세 버전과 pip freeze는 모름**이다.
[측정] 현재 확인한 환경은 Python3.12.14이며 패키지 목록을 `derived/current_environment_20261024.json` 및 requirements 형식 파일로 제공했지만 역사적 lockfile로 간주하면 안 된다.
[읽음] native DB가 기록한 VISSIM 버전은 `2020.00 - 14 [95957]`다.

### RM 결정·guard·서비스

[읽음] `evaluation/controllers/sdmpc.py`의 `meter_neighbors`, `audit_meter_neighbors`와 선택 후 호출 경로가 실행 경로이며 `adapter.sdmpc_meter_neighbor_audit=true`다.
[읽음] 램프별 및 같은 freeway 소유 묶음의 증감 후보를 중복 제거해 전체 Ω 비용·NP/NUF·물리·액추에이터 제약으로 재검사하고, 서로 다른 유리한 RM의 결합도 최대1회 검사한다.
[읽음] leader cap 후보는 joint_owner_game 설정의 최대3개이며 넓은 cap도 포함되는 diverse 순서이므로, 과거의 “넓은 cap 누락” 가설은 철회됐다.
[읽음] RM은10초 주기, 최소녹색2초·최대10초·변경폭2초·amber0·allow_zero_green=false이며, 원래0초 적색 후보와 구분한다.
[읽음] `physical_ramp_branches.py`의 저장 guard는 head 앞 재고/차로별 저장공간 충족률이0.9 이상일 때 이전녹색+허용변경폭까지 녹색 하한을 올린다.
[읽음] 이는 명령 보호이고 하류 수용량까지 보장하는 무역류 증명은 아니며, 도시 저장 guard의 trigger0.9/reserve green2초도 별도 작용한다.

| 근거 | 녹색 s/10s | allocation 표 대/주기/차로 | 동측10639·10490·10484 물리 plant 대/주기 | 10681 두 차로 총 대/주기 |
|---|---|---|---|---|
| [읽음] | 2 | 0.71 | 1 | 2 |
| [읽음] | 3 | 0.99 | 1.5 | 3.0 |
| [읽음] | 4 | 1.44 | 2 | 4 |
| [읽음] | 5 | 1.89 | 2.5 | 5.0 |
| [읽음] | 6 | 2.34 | 3 | 6 |
| [읽음] | 7 | 2.79 | 3.5 | 7.0 |
| [읽음] | 8 | 3.24 | 4 | 8 |
| [읽음] | 9 | 3.69 | 4.2 | 8.4 |
| [읽음] | 10 | 4.2 | 4.2 | 8.4 |

[읽음] 위 allocation 표와 physical head 표는 다른 단계의 값이며,10681 총량을 차로당 값으로 중복 곱하면 안 된다.
[읽음] 램프 차로수는10482·10681이2, 나머지가1이고, 기본 물리 서비스 상한은 차로당1,800대/h다.
[읽음] 설정 키 전체·배열은 `derived/effective_config_fields.csv`, 정확한 실행 코드는 SOURCE_FILES 목록으로 찾아야 한다.

### TSC와 VSL

[읽음] TSC는17개 SC의 green·offset을 3개150초 블록으로 선택하며, native physical SG 계약, signal-aware 최소녹색, source reference 하한 및 실제 신호 clock과 이산 writer를 사용한다.
[읽음] 제어시작900초, 제어주기150초, 예측450초, 말단비용OFF, 고속도로 plant5초·도시 plant10초이며 VISSIM 자체의미시시간 간격을5/10초로 바꾼 뜻은 아니다.
[읽음] VSL 허용 집합은50/60/70/80/90/100/110km/h, 최대변경40km/h이며 동서 각 head2·5·10·13의4개 내부구역을 선택하고 entry0·마지막15는110이다.
[읽음] 최적화는 이미 켜져 있고 `sdmpc_vsl_activation_secant=true`이며, 실제이득을 찾지 못해110 유지한 결과를 설정 미활성으로 해석하면 안 된다.
[측정] optimized와 off 설정의 차이는 name 및 `adapter.sdmpc_fixed_vsl`뿐이며, off는 `{start_sec:0,base_kmh:110,zone_kmh:{}}`로 고정한다.
[읽음] VSL 변경 지점은 위 고정 override 제거/수정, `config_overrides`의 VSL 집합·구역 인덱스, adapter의 secant와 sdmpc 선택/실행검증 경로다.
[읽음] `derived/controlled_dsd_groups.csv`는66개 제어DSD의구역·번호·link·lane, `derived/dsd_locations.csv`는망의전체DSD 위치·차종·분포를 제공한다.
[읽음] 동측seg10은DSD59–62,seg13은63–66이며 고정 window의90은seg13에1800≤t<5700만 적용된다.
[읽음] 2026-10-15의다중블록/다중구역25후보 확장은 이 역사적 실행판에 포함되지 않는다.
[추정] Claude는 이 인계판을 먼저 재현한 뒤 별도 변경으로 VSL plant·탐색을 수정하는 편이 원인 구분에 적합하다.

## 3. 설정·망·수요·plant

[읽음] 모든 실제설정 원본은 `code/`와 각 `raw/`의 provenance가 가리키는 파일에 바이트 그대로 들어 있고, 설정 이름만 같다고 동일판으로 취급하지 않는다.

| 근거 | 파일 | SHA256 |
|---|---|---|
| [측정] | diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json | c90882628ddc75c0c75c9a82771c96a50614b297839ec32c506859a969dc1df3 |
| [측정] | diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json | efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473 |
| [측정] | diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/evidence/candidate_manifest.json | 8ae93aa35e209c7d5016d5d8f5233b352245d6486aab443a72ea716bdca7ebea |
| [측정] | diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/expanded_joint/eval_036/reference_config.json | 7f6df2d14795b22d858aa772f5813e42b67f9d1ec4296cc6203bd854c28d83a4 |
| [측정] | diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/parameters.json | bd7439894b1fcd165f53d51e7896865673efa52b82296d057cd7271bcdb1dad5 |
| [측정] | diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json | 91a584ab779330f928a79855d68bcdbb133dfaaef57a2de66d5d415e9a474ee2 |

[측정] 실제 INPX SHA256은 `64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc`이며 크기는3,168,966바이트다.
[읽음] 참조 v3c3 `3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e`와 다른 파일이고, 이 인계판을 v3c3 실험으로 부르면 안 된다.
[측정] 소유 D/E 런의 깊이3 이하 provenance136개를 검사한 범위에서 참조v3c3 SHA 일치는 없었으며, 미기록·더 깊은 런의 존재는 모름이다.
[읽음] Claude 보호 폴더를 이 인계의 소유 런으로 합치지 않았고 세부검색범위는 `derived/v3c3_scan.json`에 있다.
[측정] 34개차량입력의전체시간대표는 `derived/demand_34_inputs.csv`이고, 원래 profile은 `__default__,1.0`이므로 아래실수요를 다시 FW80이라는 이름으로 곱하지 않는다.

| 근거 | 시작 s | 1098 FW_E veh/h | 1099 FW_W veh/h |
|---|---|---|---|
| [읽음] | 0 | 7096.32 | 8870.4 |
| [읽음] | 900 | 10137.6 | 12672.0 |
| [읽음] | 1800 | 10644.48 | 13305.599999999999 |
| [읽음] | 2700 | 9123.84 | 11404.8 |
| [읽음] | 3600 | 7096.32 | 8870.4 |
| [읽음] | 4500 | 5068.8 | 6336.0 |

[측정] 모든 구간에서1099는1098÷0.8이며 마지막4500초 구간은 분석종료8100초까지 적용했다.
[읽음] 사용자 기준v3c3의1099=4300/5600/6000/5200/3900/3450veh/h와 다르다.
[읽음] DSD110은 모든차량의고정속도110을뜻하지않으며,희망속도CDF는(75,0),(95,.03),(100,.10),(115,.68),(130,.91),(145,1)이다.
[측정] 모든 희망속도분포는 `derived/desired_speed_cdfs.csv`에추출했다.
[읽음] plant 매니페스트의9개입력은이름+SHA로고정돼있고,복사코드의실제load_sources로9개핀PASS를확인했다.
[읽음] 셀별값의출처는expanded_joint/eval_036 reference와geometry/parameters이며,`derived/plant_coefficients.json`의state_response·physical_cell_fd·vsl_fd_response·component transport에전체값을보존했다.
[읽음] 기본parameters의동측δ_merge=1·서측0,top-level0.3만보고셀별값을대체하면안되며reference의cell_overrides가추가로적용된다.
[읽음] 예를들어동측cell10은δ_merge3.5303754160321255,cell12는5.0894678108751865이고,geometry의cell_index_base는0이다.
[읽음] W 기본계수는vf multiplier1.09/rho_crit multiplier0.68/tau12/nu43.05/kappa5, E는1/1.4/12/36.75/5이며 물리FD와상태응답 override를함께읽어야한다.
[읽음] 매니페스트의원래qualification은 “Frozen cellwise expanded_joint tested with current coupled routing; NOT gain qualified or production adopted.”로남겨두었고,계수가보편적으로검증됐다고바꾸지않았다.
[읽음] 실행설정adopted355는10639/10484 single_lane_causal_receiving과기존wave3.2557309454394003을사용하며,기각된410서비스율후보는포함하지않는다.
[읽음] 전체 물리모델의원인별교정완료 여부와각계수의독립식별성은모름이며,이런한계를재현기준의실험설정과구분한다.

## 4. 원자료와 기준선

[측정] `raw/joint/sdmpc/`와 `raw/nc/`의남아있는파일을원본수정없이복사했고,결정JSON·action CSV·run provenance·로그·readback·err·FZP·native DB/평가출력이포함된다.
[측정] 조건별확장자수와SQLite table 목록은 `derived/artifact_presence.json`, 전체개별파일의상대경로·크기·SHA는 `FILE_MANIFEST.csv`다.
[읽음] 정확한이름이run.json이아니면run_provenance/runlog/launch의실제이름을그대로제공하며,존재하지않는노드평가나입력별미삽입시계열을새로만들지않았다.
[읽음] native LDP는신호실행대체증거이고LSA의불통과를지우지않았으며,현재파일이존재한다는사실과유효한커버리지를구분한다.
[읽음] NC는9000초완주원자료를보존하고비교만8100초로절단했으며,9000초결과를8100초로이름만바꾸지않았다.
[측정] 본인계작업의새VISSIM실행·제어기재최적화·타인프로세스종료는0회다.

## 5. 효과를 나눠 볼 수 있는 기존 런

[읽음] 아래는동일seed29·같은64cf망의추가조건이며,표의유지횟수는48회최적화구간기준이다.

| 근거 | 조건 | 원래 런 폴더 | 시작 / 끝 KST | 설명 |
|---|---|---|---|---|
| [읽음] | window | E:/VISSIM_runs/20261012_adopted355_window_s29_8100/sdmpc | 10-12 12:32:34  START sdmpc31_sdmpc8100_s29 attempt=1 pid=36436<br>10-12 16:25:35  OK sdmpc31_sdmpc8100_s29 attempt=1 elapsed=13981s | RM+TSC, seg13 시간창90; 1 held |
| [읽음] | off | E:/VISSIM_runs/20261012_adopted355_off_s29_8100/sdmpc | 10-12 21:30:28  START sdmpc31_sdmpc8100_s29 attempt=1 pid=49964<br>10-13 00:45:56  OK sdmpc31_sdmpc8100_s29 attempt=1 elapsed=11728s | RM+TSC, VSL 고정110/최적화OFF; 8 held |
| [읽음] | freeway_only | D:/VISSIM_runs/20261013_solo355_local_freeway_only_s29_8100/sdmpc | 10-13 14:14:22  START sdmpc31_sdmpc8100_s29 attempt=1 pid=29868<br>10-13 18:47:16  OK sdmpc31_sdmpc8100_s29 attempt=1 elapsed=16374s | VSL+RM, 자기정보·고속도로목적, 도시native; 0 held |
| [읽음] | urban_only | D:/VISSIM_runs/20261013_solo355_local_urban_only_s29_8100/sdmpc | 10-13 18:51:38  START sdmpc31_sdmpc8100_s29 attempt=1 pid=14476<br>10-13 20:50:02  OK sdmpc31_sdmpc8100_s29 attempt=1 elapsed=7104s | TSC, 자기정보·도시목적, VSL110/RM OPEN; 5 held |

[읽음] window/off는joint와동일HEAD·dirty동결본이며,solo는`codex/solo355-local-information`,HEAD`2f28000ab0ea61b646badade70c172200e9c7f1a`,status55,551항목의별도동결본이다.
[읽음] solo원래동결본은`D:/VISSIM_runtime/20261013_solo355_local_pair/frozen/sdmpc31_2f28000a_202610131404`이며전체manifest와provenance핀코드를`evidence/original_solo_FREEZE.json`, `original_code_dependencies/solo/`에보존했다.
[읽음] solo는목적함수·정보·액추에이터가함께달라지므로정보교환만의효과를분리하지못한다.
[읽음] freeway_only에서는실제로100/90명령도선택됐으므로순수RM-only로부르면안된다.
[읽음] window는적용공간도optimized와다르므로VSL타이밍만의비교가아니다.

| 근거 | 조건 | seed | Ω701 veh·h | FW_E7 veh·h | 국소19 veh·h |
|---|---|---|---|---|---|
| [측정] | nc | 29 | 7406.171375 | 2124.524111 | 2347.393389 |
| [측정] | joint | 29 | 6911.511042 | 1840.869556 | 2190.818333 |
| [측정] | window | 29 | 7037.503986 | 1859.968778 | 2253.180889 |
| [측정] | off | 29 | 7011.833986 | 1823.055389 | 2199.776667 |
| [측정] | freeway_only | 29 | 7816.075653 | 1772.685778 | 2217.270778 |
| [측정] | urban_only | 29 | 7711.156153 | 2845.955833 | 3081.106333 |

[읽음] 이전고정VSL90·ALINEA RM·둘조합·무제어의seed29/43 자료도`raw/historical_alinea_s29`, `raw/historical_vsl_s29`, `raw/historical_vsl_s43`에포함했다.
[읽음] 원래루트는각각`D:/VISSIM_runs/20260924_bottleneck90_rm_s29`, `D:/VISSIM_runs/20260924_bottleneck90_full_s29`, `D:/VISSIM_runs/20260924_bottleneck90_full_s43`이며실제arm은`rm/run`, `both/run`, `none/run`, `bottleneck90/run`이다.
[읽음] 이들은9000초실험이며ALINEA는S-DMPC가아니고seed43은망파일SHA도`05c795556683e7ec7252460e33814f7aeff662a527cf24a3517aea7ddf7bafde`로다르다.
[읽음] 당시full commit·dirty·실제native시작/끝벽시각은모름이며wrapper시각을대신확정하지않았고,프로필·시드·길이·완료문구와자료위치는`derived/historical_ablations.json`에있다.
[읽음] 같은목적·같은정보의순수S-DMPC RM-only, VSL-only최적화, 이웃검사만OFF의짝실험은찾지못했으므로모름이다.
[읽음] 봉인시드37·59·61·67의수치는비교표·요약·그림에서제외했고,발견한원자료는`sealed/`에분리했으며경로목록만`sealed/PATHS.txt`로제공한다.

## 6. 사용자 지표 재계산

[측정] 본선7링크는`74,10699,2,10613,119,10702,24`,국소19는여기에`10484,10490,10639,10681,10481,10483,10643,10682,129,31,68,70`를합친중복없는집합이다.
[측정] seed별원값·NC차이·개선율은`derived/metrics_0_8100.csv`에있고1절표는같은데이터로생성했다.
[측정] independentFZP결과는`derived/independent_fzp_counts.json`으로교차확인했으며window/off도같은0–8100초범위로계산했다.
[읽음] 망전체nativeTTT+미삽입의공정한8100초NC차이와입력1098/1099별대기적분은모름이며,없는값을FZP나종료대수로복원하지않았다.

| 근거 | 계산 스크립트 | SHA256 |
|---|---|---|
| [측정] | code/handoff/audit_handoff.py | 678d0f84e38698a122865b402cd16234a34bd385e44192c799a6a252d3bf7cea |
| [측정] | code/handoff/check_fzp.py | 1a2cf5681fc18c653328bb460c0af2519760a11fa4744c35d85a0f15e0506a19 |
| [측정] | analysis/original_scripts/solo355_compare_20261014.py | 7fc91d604214b3ea757c2e7c34f59a694a801ac21bf83c7e02fd57cde27e7fd1 |
| [측정] | analysis/original_scripts/analyze.py | 6df4be7510e68f060e0294681be929e44686de93bd3608b27a4ed690fd8adf75 |

## 7. 알려진 실패·모형 결함·철회

[읽음] 대상joint는6900초에명령유지1회가있었고off는8회여서큐가최종`failed_no_retry`로기록됐지만,세조건각각의native는8100·exit0·소유종료로기록돼있다.
[읽음] 이전큐wrapper중단과PID/생성시각문자비교오류의인계기록을`evidence/runtime/continuation*`에보존했고이를native재실행으로세지않는다.
[읽음] 이전head47right런6150초와prevention런6750초는사용자중단이므로8100완료/9000완료로승격하지않으며,별도기록에있는일부150초추정과native5초확정집계를섞지않는다.
[읽음] 사용자가예로든10480적색→역류중단의정확한한개런과원인진단을이자료만으로일대일확정한결과는모름이며,대상joint는녹색0을허용하지않는설정이다.
[읽음] 206.5306veh/h 정규화movement용량의잔재는`branch_service314`진단에서확인됐지만전영역이교정됐다는증거는없으며,이인계판의해결완료여부는“부분수정,전역미검증”이다.
[읽음] 셀분할사전값·경로구성·고정ETA·공유링크129/70의FIFO/차로접근·포트수용결합은남은모형한계이고,단순용량배수로모든오차를교정했다는주장은하지않는다.
[읽음] 68자체차로별유한공간과10681앞재고전달,10639/10484의인과적수용은이판에채택돼있지만,횡방향gap/FIFO를명시적으로푸는완전미시모형은아니다.
[읽음] VSL손익방향·여러블록유지/여러구역동시제어의예측정확도는이판에서완성되지않았으며,후속보정후보를역사적실행본에섞지않았다.
[읽음] 과거다른fixedVSL90런의Ω개선5.3215%와Ω밖체류8.2537%증가는이joint의8%개선과다른수치이며,후자를개선율이라고읽으면안된다.
[읽음] 도시도로8.0866%,도시도로+진출램프8.3868%,Ω−서측본선8.2738%,전체Ω6.6790%를하나의“전체8%”로통칭한표현은이인계에서정정한다.
[읽음] 과거“넓은NUF cap미검사”가설도3후보에포함됨을확인해철회했고,최적화수렴·순수VSL효과·전체망순이득을실행성공으로추정하지않는다.

## 8. 재현 순서와 파일 검증

[읽음] 아래는Claude가향후실행할절차이며본인계작성중에는native를실행하지않았다.
[읽음] 원본설정·증거는바이트보존을위해기존절대경로를수정하지않았고,새설정/증거는상대이름+SHA로참조하며원래명령의절대경로만본문에그대로남겼다.
[읽음] `FILE_MANIFEST.csv`는payload파일의상대경로·크기·SHA256이고,각폴더`SHA256SUMS.txt`는그폴더의직접파일과자식폴더checksum파일을검증한다.
[읽음] manifest자기자신/체크섬/후작성publication receipt를payload목록에서제외해자기참조해시순환을피하며,이파일들도해당폴더checksum으로검증한다.
[읽음] `.git/`은실험원자료checksum대상이아니며Git commit으로관리한다.

```powershell
# [읽음] Existing data only: this command does not start VISSIM.
$Bundle = (Resolve-Path .).Path
& $Python (Join-Path $Bundle "code/handoff/verify_sha256.py") $Bundle
& $Python (Join-Path $Bundle "code/handoff/audit_handoff.py") --bundle $Bundle
& $Python (Join-Path $Bundle "code/handoff/check_fzp.py") --bundle $Bundle
```

[읽음] 재집계기는캐시를재사용하고출력파일을갱신하므로검증완료보관본대신별도분석사본에서실행해야한다.
[읽음] 독립FZP검사를처음부터다시하려면분석사본의`derived/independent_fzp_counts.json`만별도이름으로보존한후실행하며원본run을지우지않는다.
[읽음] 실제런재현은동결본을그대로지정하거나,새Git snapshot의`code/`를정본freezer로별도고유경로에동결한뒤원래runner를호출한다.
[읽음] 아래변수는작업자가자기환경의실제Python/PowerShell/dependencies와새출력폴더로설정해야하며Claude의기존작업트리/런/동결본을덮어쓰면안된다.

```powershell
# [읽음] Preparation example; intentionally not executed during handoff.
$Source = (Resolve-Path ./code).Path
$Config = "diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json"
$env:PYTHONUTF8 = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
& $PowerShell -NoProfile -File (Join-Path $Source "tools/sdmpc31/freeze_worktree.ps1") -Source $Source -FrozenRoot $NewFrozenRoot -Python $Python
# [읽음] Set $FRZ to the printed FRZ= path after FREEZE_DONE.
$Runner = Join-Path $FRZ "diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1"
& $PowerShell -NoProfile -File $Runner -PreflightOnly -FrozenTree $FRZ -ResultsRoot $NewResults -StatusPath $NewStatus -SimPeriod 8100 -Seed 29 -Arms sdmpc -TuningRelativePath $Config -PythonExe $Python -PowerShellExe $PowerShell -DependenciesPath $Dependencies
# [읽음] Launch only after the preflight and the operator's independent authorization.
& $PowerShell -NoProfile -File $Runner -Detached -FrozenTree $FRZ -ResultsRoot $NewResults -StatusPath $NewStatus -SimPeriod 8100 -Seed 29 -Arms sdmpc -TuningRelativePath $Config -PythonExe $Python -PowerShellExe $PowerShell -DependenciesPath $Dependencies
```

[읽음] NoGlobalKill·MaxAttempts1·Startup300·전체manifest검증을정본runner에서유지하며,새실행중복·다른프로세스종료를수행하지않는다.
[읽음] 기존NC파일로8100초비교가가능하므로인계재현을위해새NC가필수인것은아니다.
[읽음] 원래joint watchdog소요는17,264초(약4시간48분),NC9000초는2,829초(약47분)였으며freeze/manifest검증시간은별도다.
[추정] 같은환경에서도실행시간·수치의완전재현을보장할수없고,당시pip lockfile부재와일부명령유지실패의재발여부를함께기록해야한다.

## 9. 넘기지 못한 것과 해석 제한

- [읽음] 당시Python정확버전·pip freeze: 저장된역사적lock기록을찾지못해모름이다.
- [읽음] 원래전체dirty diff: 원문을찾지못해모름이며tracked부분집합재구성patch·untracked실행파일·원래FREEZE를대신제공한다.
- [읽음] NC0–8100native미삽입누적/1098·1099별대기적분: 해당구간·입력별기록이없어모름이고9000초값으로대체하지않았다.
- [읽음] 순수S-DMPC RM-only/동일정보TSC-only/이웃검사만OFF의완전한인과분해: 해당짝실험을확인하지못해모름이다.
- [읽음] 모든역사적실패런의완전목록및일부옛ALINEA런의fullcommit·native벽시각: 기록부족으로모름이다.
- [읽음] 원래전체49GB동결트리의완전복제: 과거실험출력까지중복복제하지않고원래전체manifest와런재현에필요한코드·입력부분집합을제공한다.
- [읽음] 새VISSIM실행에의한재현성확인: 사용자의금지에따라수행하지않았으며설정검사·9개plant pin·기존결과독립집계까지만검증했다.
