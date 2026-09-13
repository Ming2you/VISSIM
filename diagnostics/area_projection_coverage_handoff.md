Ω635개 전체의 관측 지원을 현재 차량 수와 무관하게 대조했습니다. 기존 로컬 mask 밖에는214개가 있었지만, 이는214대가 빠졌다는 뜻이 아닙니다. 대부분 이번900초 snapshot에서는 비어 있는 짧은 connector입니다.

| 구분 | 물리 링크 수 |
|---|---:|
| 별도 FW chain으로 집계 |10|
| 램프 queue로 집계 |8|
| 기존 urban 관측·투영 지원 |402|
| 실제 단일 하류 근거로 신규 지원 |170|
| 물리 귀속 미확정 |45|
| 합계 |635|

`area_projection_coverage_635.json`은 모든635개에 한 개의 coverage 분류를 배정합니다. 새 지원 조건은 실제 connector의 to-link, 그 도로의 단일 기존 storage, connector의 기존 지원 집합이 서로 일치하는 것입니다. 신호가 없고 독립 input이 없는 단일 storage 도로9개도 포함합니다. 차로 방향이 섞인 다중 alias 도로, source와target alias가 모순되는 connector, 기존 stock 자체가 없는336 등은 미확정입니다. 완전한 route identity를 단지 mapping의 문자열 하나로 증명했다고 주장하지 않습니다.

특히 알려진 signal-to-receiver 실제 경로도 교차검사했습니다.10627·10634는 SC1004→SC107 bypass의 중간 경로인데 기존 alias는SC1004→SC1005여서 자동 추가하지 않았습니다.10611도 SC107→SC1004 경로와 기존 alias가 모순됩니다. 이미 수량이 지원되는56·385·10618·10619·10632·1220000102도 일부 full-route identity와 기존 origin이 일치하지 않습니다. 이들의 수량은 누락되지 않지만 미래 라우팅의 정확성까지 보장된 것은 아닙니다. 이 한계를 JSON에 남기고 모호한 차량을 새 origin으로 옮기지 않았습니다.

`physical_projection_support_635_proposal.json`은 기존35개와 새170개, 총205개를 지원합니다. 이번 pure-n7 전 시점에서 발견된6개 양수 누락은 모두 근거가 명확합니다.

| 물리 connector | 실제 to-link | 수용 storage |
|---|---|---|
|10224|1220015000|SC6_to_SC12|
|10554|1220008401|SC101_to_SC1|
|10774|124|SC1001_W_out|
|10273|1220009502|SC109_to_SC16|
|10579|353|SC105_to_SC1|
|10294|1220007501|SC108_to_SC7|

FW10613·10771은 별도 freeway chain에 이미 포함되므로 urban으로 추가하지 않았습니다. 새 data는 현재 빈170개에도 지원표를 미리 마련합니다. 남은45개는 `unresolved_physical_links`로 보존하고, 새 data의 `require_positive_unresolved_failure=true`가 켜진 경우 실제 full record에 양수 차량이 있으면 projection 단계가 해당 링크와 차량 수를 명시하며 중단합니다. 임의의0·균등 분배·다른 owner로 처리하지 않습니다. 현재 구자료 및 flag OFF는 동작·반환값·object identity가 유지됩니다.

적용은 `area_routes_and_sc2001.patch` 하나입니다. 여기에는 다음6개 production 파일의 변경만 들어 있습니다.

- 새 `area_dynamic_routes.py`: 검증된 실제 우회 경로·phantom 제거·원점 교정.
- 새 `sc2001_corridor.py`: 원점별 offline prior와 finite accepted transfer.
- `urban_flow_accounting.py`: 명시적 corridor advance/receipt와 generic sink 제외, Ω OFF 물리 동작.
- `runtime_setup.py`: main 설정·초기화 순서, worker에서 상태 재추정 없이 hook 복원.
- `area_runtime.py`: 실제 dynamic paths와 SC2001의 세 Ω entry 계약.
- `projection_support.py`: **새 data에서만** 양수 미확정 링크를 감지하는 guard.

설정은 `control_area_physics_overlay.json`을 n7에 deep merge합니다. 목적함수 활성화와 beta_seconds는 별도로 명시해야 합니다. 선택적인 static off-ramp route prior overlay는 이 묶음에 포함하지 않았습니다. 기본 n7 config와 production 파일은 현재 실행 동안 수정하지 않았습니다.

검증은 `python -m unittest diagnostics.test_area_projection_coverage`의 **5검사 PASS**입니다. 모든170개 신규 물리 링크에 synthetic 차량1대를 동시에 넣어 각 storage에 정확히1대씩 들어가고 총+170대임을 확인했습니다.635 분류 합계, FW/ramp 중복 금지, 실제6개 endpoint, 양수 미확정336의 정확한 오류, 기존 자료·OFF의 정확한 동일성도 검사했습니다. `probe_area_package_runtime.py`는 새 overlay를 실제 adapter projection에 적용해 main·반복 worker·fresh subprocess worker의150초 결과가 같고, rawΩ1763/modelΩ1763.015564705가 유지됨을 확인했습니다. 실재31개 pure 상태의 신규 data 재검사는 flow agent가 담당합니다.

자료 SHA256:

- `physical_projection_support_635_proposal.json`: `46965a1b605b71f707400fe6eb70c06ac17e997c7fa7c0051eb9225492d515f1`
- `control_area_physics_overlay.json`: `4d215c4d7b75f6dff18c297c42897cdc601a0c7086e4e17f229387610290c0a5`
- 파일별 code hash는 `area_routes_and_sc2001_patch_manifest.json`입니다.
