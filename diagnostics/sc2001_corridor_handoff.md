SC2001 남쪽 출구의 잘못된 재투영과 미정의 하류 흐름을 해결하는 검증된 제안입니다. 현재 VISSIM 실행 중이므로 production 파일에는 적용하지 않았습니다. 모든 구현·검사는 `diagnostics` 안에서 수행했습니다.

`area_routes_and_sc2001.patch` 하나로 flow agent의 dynamic route 수정, SC2001 모듈, canonical urban body의 명시적 호출, main/worker 설치 순서를 적용합니다. 이 패치는 `dynamic_area_runtime.patch`와 `sc2001_urban_flow_accounting.patch`를 **대체**하므로 세 패치를 중복 적용하지 않습니다. 현재 소스에 `git apply --check diagnostics/area_routes_and_sc2001.patch`가 통과했습니다. 파일별 변경 전후 SHA는 `area_routes_and_sc2001_patch_manifest.json`에 있습니다. 실행 종료 후 root가 한 번 적용하는 것이 예정된 다음 단계입니다.

검증된 원인은 두 가지입니다.

- 물리 링크78의 차량은 기존 투영에서 `in_SC2001_W`에 들어갔습니다. 78은 서쪽 진입로가 아니라 SC2001 남쪽 출구입니다. 78→10703은 SC2001에서 나온 차량만 지나는 경로이므로 두 링크를 실제 `SC2001_S_out` 저장 공간에 한 번만 재투영합니다. 31·124의 기존 차량을 추정 원점으로 나누지 않습니다.
- 10703은31의350.718m 지점에 합류합니다. 정적 결정1137은28.547m, 79로 돌아가는10704 분기는281.156m입니다. 둘 다 합류점 뒤쪽이 아니라 **이미 지나온 위치**이므로 78 출신 차량에1137의3:1:2 비율을 적용하거나79 복귀를 넣는 것은 물리적으로 잘못입니다. 1141/1142/1143의 upstream route는78의 약12m에서 끝나며 `combineStaRoutDec=false`, all vehicle types, 단일 정적 시간 구간입니다. 경로 없는 차량의 분기는 차로와 다음 ALL connector에 영향을 받습니다. [PTV Vissim 2020 connector attributes](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Strassennetz_Verb_str_Attr.htm), [PTV static routing simulation](https://cgi.ptvgroup.com/vision-help/VISSIM_2022_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_RoutenEntsch_Sim.htm).

root 승인에 따라 NC seed13 전체 관측의 **offline empirical constants**를 사용했습니다. 현재 제어 실행의 미래 FZP는 읽지 않습니다. `sc2001_corridor_nc13.json`은 학습 run/FZP SHA, 네트워크 SHA, 완료 표본 분모, 검열 ID, Wilson 구간, 검열만 고려한 비율 범위를 보존합니다. 원본에서78이 관측되고 하류가 확인된839개 코호트는 중복 차량 ID가 없으며, 남은8개는 실행 종료 근처에78 또는31/124에서 관측이 끝났습니다. 5초 표본이므로 짧은 링크 누락과 표본 선택 편향이 남습니다.

| 원점 | 완료 표본 | R_D_E | R_D_W | 외부125 | 종료 검열 |
|---|---:|---:|---:|---:|---:|
| W:76 |323|213|0|110|4|
| N:80 |337|226|0|111|0|
| E_SC2002:84/85 |179|19|3|157|4|
| 초기 원점 미관측: pooled |839|458|3|378|8|

각 행의 완료 표본으로 나눈 값을 해당 원점의 고정 분기 비율로 사용합니다. W 분기의 표본3개는 특히 불확실합니다. 원점76/80의0은 이번 학습 표본의0이며 물리적으로 불가능하다는 뜻이 아닙니다. 임의의 균등 분배나 pseudocount를 넣지 않았습니다. 같은 seed13의 제어 성능은 탐색 결과이며 seed14 holdout 검증이 필요합니다. 더 촘촘한 새 NC 자료를 자동으로 대체 주입하지 않습니다.

물리·Ω 계약은 다음과 같습니다.

- 입력1106은80,1107은76에 있고 이미 기존 gate 수요로 들어옵니다. 78·31·124에는 독립 native input이 없습니다. 코리더는 **새 외생 수요를 만들지 않고** 기존 세 movement가 실제로 수용한 차량만 받습니다.84는 상류SC2002로부터 옵니다.
- 76→10723→78,80→10721→78,84→10726→78은 각각 outside→outside→inside입니다. 세 movement의 actual accepted flow가78에 들어올 때 Ω entry를 기록합니다. 기존 receiving-stock 근사 때문에 외부 진입 connector의 짧은 이동시간도78 안에 먼저 놓이는 시점 오차는 명시했습니다.
- 78→10703→31→10484는 내부 R_D_E,78→10703→31→10774→124→10480은 내부 R_D_W 이동입니다. TTD는0입니다. 외부 경로의 첫 이탈은124→10775이며 이후125도 외부입니다. 이 분기의 **accepted** flow만 TTD입니다.
- 저장 용량은 실제78 길이476.458m×2차로×기존 jam density168.18veh/km/lane로 계산합니다. 31·124 용량은 추가하지 않습니다. 분기별 FIFO와 원점별 코호트를 따로 보관하고, 실제 램프 여유 공간·connector 차로 서비스·공통2차로 서비스를 제한합니다. 램프가 차면 해당 코호트가 남으며 다른 경로로 재배분하거나 삭제하지 않습니다.
- 31·124 이동 중인 SC2001 코호트도 source78 저장 공간에 보수적으로 남깁니다. 이는 공간 위치와 차로 변경을 세밀하게 재현하지 못하며78의 spillback을 너무 이르게 만들 수 있습니다. 외부125의 downstream congestion은 기존 유한 boundary service로만 근사합니다.

설치 순서는 코드로 고정했습니다: 기존 physical topology → dynamic route repair → shared69/support projection → SC2001 geometry/initial physical projection → 실제 raw 상태 재투영 → initial transit pairing → shared69/corridor 초기화 → canonical urban 설치 → area route 구성·ledger seed. Worker는 설정과 후보 상태를 받아 hook만 다시 설치하며 calibration, 수요, 초기 상태를 다시 추정하지 않습니다. Ω objective를 꺼도 corridor physics는 작동합니다. `urban.sc2001_corridor`가 없으면 기존 body의 결과와 상태가 정확히 같습니다.

추가 설정은 기존 n7 config에 다음 값을 명시적으로 합칩니다. 단일 JSON의 `extends` 동작을 가정하지 않습니다. 기본 파일은 바꾸지 않았고 아래 기능은 기본 OFF입니다.

```json
{
  "urban": {
    "conservative_initial_transit": true,
    "shared_approach": "diagnostics/shared_approach_ver2.json",
    "sc2001_corridor": "diagnostics/sc2001_corridor_nc13.json",
    "movements": {
      "physical_route_topology": "diagnostics/physical_movement_routes_ver2.json",
      "dynamic_physical_route_topology": "diagnostics/dynamic_area_routes_ver2.json"
    }
  },
  "observation": {
    "physical_support_repair": "diagnostics/physical_projection_support_635_proposal.json"
  }
}
```

위 값에 기존 `observation_projection_config.json`의 `physical_branch_projection` 블록을 그대로 합쳐야 합니다. 수량 provenance와 transit-storage marker, spillback 중복 방지 코드는 현재 adapter에 이미 들어 있습니다. 직접 landing의 local/global receiving 검증에는 `freeway.local_lane_context`, `freeway.conservative_offramp_drain`, `freeway.local_landing_state`를 함께 true로 사용했습니다. Ω 목적함수는 별도로 `enabled`, 명시적 `beta_seconds`, `membership_path=diagnostics/control_area_membership.json`, `route_contract_path=diagnostics/control_area_route_contract_physical_routes.json`을 설정합니다. 이 보고서는 beta 값을 선택하지 않습니다. `offramp_route_prior_overlay.json`은 별도 ablation이며 SC2001 활성화에 필수인 값이 아닙니다.

필수 보관 자료는 위 JSON들과 `dynamic_area_nc13_calibration.json`, `control_area_membership.json`, `control_area_route_contract_physical_routes.json`입니다. 그 JSON들이 참조하는 기존 pinned network, jam source, gate map, demand profile도 필요합니다. 학습 FZP와 `sc2001_corridor_audit.json`은 재보정·감사용이며 controller runtime은 읽지 않습니다. `build_sc2001_corridor_calibration.py`가 offline 상수를 재현하고 `build_area_routes_and_sc2001_patch.py`가 패키지를 생성합니다.

검사 결과:

- `python -m unittest diagnostics.test_sc2001_corridor`: **11 tests PASS**. 실제900/3300 재투영 총 차량 보존, geometry/units, origin prior, full-ramp retention, candidate copy, positive unknown 거부,450초 코호트 보존, flag OFF body/state 정확 일치, Ω OFF 물리 dispatcher, runtime training-file 미접근을 확인했습니다.
- `probe_sc2001_corridor_replay.py --time 900|3300 --depth 1|3`: 네 경우 모두 **strict positive route coverage와 전체 model inventory/Ω ledger closure PASS**. 각각150/450초입니다. SC2001의 모든 분기가 실제 양수 flow를 처리했고 generic `sink:SC2001_S_out` 사건은 없습니다. 이 검사는 예측 모델의 유효성이지 VISSIM 제어 성능의 증거가 아닙니다.
- `probe_area_package_runtime.py`: 현재 실제 adapter projection + 제안된 main runtime + 반복 worker 설치 + **새 subprocess worker**의150초 area 결과가 정확히 같습니다. Worker 설치는 전달받은 state를 바꾸지 않았습니다. 초기 Ω raw=**1763**, model=**1763.015564705**, shared69=32, SC2001=7입니다. 잔차0.015565는 기존 공통 FW cell length 근사이며 관측 잔차 상수 보정은 사용하지 않았습니다.

수치 산출물은 `sc2001_replay_900_150.json`, `sc2001_replay_900_450.json`, `sc2001_replay_3300_150.json`, `sc2001_replay_3300_450.json`, `area_package_runtime_replay.json`입니다. Full pure-n7 snapshots, 후보 변화, beta/pruning 광역 검사는 flow agent가 이어서 담당합니다.

최종635 전수감사 후 설정은 `control_area_physics_overlay.json`에 묶었습니다. 위 부분 설정 대신 이 파일을 n7에 명시적으로 deep merge하면 같은 물리 옵션을 재현합니다. 목적함수의 enable/beta 선택은 별도입니다. 새 `physical_projection_support_635_proposal.json`은 기존35개에170개 물리 지지점을 추가하며, 모호한45개는 임의로 귀속시키지 않습니다. 새 데이터 사용 중 그45개에 양수 차량이 생기면 정확한 링크와 차량 수를 담은 coverage error를 냅니다. 이 guard도 단일 combined patch에 포함됐습니다. 기존 데이터와 OFF는 정확히 같습니다. `test_area_projection_coverage.py`의5검사도 통과했습니다. 새 overlay를 사용한 main/반복 worker/fresh subprocess worker 재검증은 모두 통과했고1763 초기 회귀도 유지됐습니다. 상세 한계는 `area_projection_coverage_handoff.md`를 함께 보세요.
