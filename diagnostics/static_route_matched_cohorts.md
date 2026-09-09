# Native 1초 궤적의 경로결정 통과 차량 추적

**같은 차량 ID를 끝까지 연결해도 0.2는 native decision cohort를 대표하지 않았다.** 600–750초에 decision1130–1133을 지난 차량들의 total off fraction은 F_E 0.435, D_E 0.513, D_W 0.410, F_W 0.311이었다. 각 native prior 0.412/0.467/0.375/0.333에 가까우며, 1200초까지 미도착·소멸·분류불명은 없다. 한 시드·한 시간창의 관측이므로 이 표를 새 보정값으로 쓰지는 않는다.

| 그룹 / decision | gate 통과 unique ID | signal 진출 | direct 진출 | 두 출구 뒤 본선 통과 | total off fraction | native prior | 현재 모델 |
|---|---:|---:|---:|---:|---:|---:|---:|
| F_E / 1130 | 193 | 32 | 52 | 109 | 84/193 = 0.435233 | 0.411765 | 0.2 |
| D_E / 1131 | 119 | 37 | 24 | 58 | 61/119 = 0.512605 | 0.466667 | 0.2 |
| D_W / 1132 | 205 | 52 | 32 | 121 | 84/205 = 0.409756 | 0.375000 | 0.2 |
| F_W / 1133 | 148 | 13 | 33 | 102 | 46/148 = 0.310811 | 0.333333 | 0.2 |

이 표의 분모는 해당 decision plane을 **(600,750]초에 실제로 통과한 unique ID**다. 서로 다른 decision 표에는 같은 차량이 있을 수 있으므로 네 행을 독립 차량 수로 합산하지 않는다. Gate 통과는 1초 간격의 앞뒤 관측에서 동일 road link이고 `old_pos < gate_pos <= new_pos`인 경우만 인정했다. 이동거리에 선형 비례해 crossing time을 보간했으며 원래 1초 bracket과 lane 양끝값을 모두 보존했다. 600초 이전 관측이 필요한 경계를 위해 실제로는 599초부터 읽었다.

| 그룹 | native decision plane (link / pos m) | through 확인 plane (link / pos m) | 마지막 관측 outcome 시각 | gate→outcome 최소–최대 시간 |
|---|---|---|---:|---:|
| F_E | 74 / 35.477974612 | 2 / 2013.357464508 | 935.354 | 125.125–204.789초 |
| D_E | 2 / 2320.569721435 | 119 / 393.291173233 | 821.637 | 43.395–127.390초 |
| D_W | 26 / 75.748552119 | 26 / 3651.904900904 | 906.131 | 122.782–178.115초 |
| F_W | 120 / 424.228679284 | 120 / 2403.481000814 | 816.121 | 45.355–85.921초 |

Through plane은 두 offconnector 중 **나중 출구의 실제 from-position보다 본선 진행방향으로 1m 뒤**다. Connector 전체를 통과할 때까지 기다리는 정의가 아니다. Signal/direct outcome은 해당 native `source road link → 해당 offconnector`의 실제 ID 전이를 확인한 첫 사건이다. 뒤에 도시를 돌고 본선으로 재진입하더라도 첫 outcome을 바꾸지 않았다. Short connector 생략, 단순 차량 소멸, 예상 route 또는 최단경로로 outcome을 추정하지 않았다. 실제 outcome은 전부 명시적 link 전이 또는 같은 road link의 through plane crossing이었고 보간 불능도 0이었다.

Gate에서 lane 양끝값이 달랐던 차량은 F_E 8, D_E 8, D_W 3, F_W 8대다. 이는 정확한 **gate 통과 차로**의 모호성이지 모든 차로를 가로지르는 decision plane 통과 여부의 모호성은 아니다. 양끝 차로가 같아도 중간 차로변경이 없었다는 뜻은 아니다. 첫 등장 위치가 이미 decision plane 뒤여서 통과를 판정할 수 없었던 후보도 네 그룹 모두 0이었다. Right-censored alive, outcome 전 disappearance, 재통과한 decision ID 모두 0이므로 off fraction의 전체-cohort 하한/상한이 같았다.

같은 (600,750]초에 **두 출구 사이의 on-ramp로 합류한 다른 차량 ID**도 따로 추적했다. 이들은 corresponding decision cohort와 ID 중복이 없으며, 앞선 출구는 이미 지나친 상태다. 아래 비교는 각 모집단의 출발 지점과 여행 시간이 다름을 그대로 유지한다.

| 합류 connector / 해당 그룹 | unique ID | signal | direct | through | 실제 total off |
|---|---:|---:|---:|---:|---:|
| 10639 / F_E | 7 | 0 | 0 | 7 | 0/7 |
| 10490 / D_E | 10 | 0 | 5 | 5 | 5/10 |
| 10480 / D_W | 6 | 6 | 0 | 0 | 6/6 |
| 10646 / F_W | 15 | 14 | 0 | 1 | 14/15 |

여기에도 censoring/분류불명은 없다. 단 D_E 차량161은 10490으로 602.345초와 712.144초에 **두 번 합류**했다. 602.345초 첫 합류 뒤 609.393초에 direct10483으로 나간 사실을 첫 unique-ID outcome으로 세고, 두 번째 방문을 중복 대수로 더하지 않았다. 반복 방문 event는 JSON에 남겼다. 이 때문에 D_E 표의 10 unique ID는 11회 합류 event와 다르다. 첫 구현에서 이를 발견해 중단한 뒤 unique ID와 반복 방문을 구분해 다시 실행했다.

이 차이는 현재 group 셀의 전체 `q`에 단일 비율을 곱할 때 분모가 섞인다는 실제 근거다. 특히 **F_W native decision cohort는 46/148 off지만, 뒤쪽 merge10646 cohort는14/15가 signal10638로 나간다.** Native conditional total만 넣은 900–1050 민감도 replay에서 F_W accepted가 여전히 부족한 사실과 방향은 일치하지만, 이 표는 이전 600–750 진입 cohort이므로 그 150초 잔차의 수치적 원인분해라고 주장하지 않는다. F_E merge10639의 7대는 반대로 모두 through였다. 네 그룹의 무조건 비율을 일괄 조절하거나 direct/signal 수용량을 맞추는 방식으로는 이러한 경로 차이를 보존할 수 없다.

가장 작게 식별 가능한 다음 모델 인터페이스는 **upstream decision cohort와 각 intermediate merge cohort를 별도 flow/stock으로 보존하고, branch별 실제 순서에서 accepted receipt를 분기하는 것**이다. 네 개 제어 그룹은 유지할 수 있지만 물리 진입·진출 이벤트까지 한 셀에 합칠 수는 없다. 그 구현 전에 다른 진입 시간창에서도 같은 ID 추적으로 반복 방문·차량 소멸·미도착을 분리하고, 추가 cohort별 경로가 어느 native decision에서 정해지는지 확인해야 한다. 이번 자료만으로 새 확률이나 capacity를 맞추지 않았다.

사용한 파일은 `evaluation/runs/codex_meter10639_g5_s13_20260910/vissim_eval/modi_eval_userfix Ver2_001.fzp`다. 이름은 meter trial이지만 900초 명령 생성에 실패한 **무효 intervention**이며, native/all-open 궤적의 1초 관측 자료로만 쓴다. 기존 `native_trajectory_repeat_check.json`에서 원 NC의 모든 공통 5초 시점 5,336,479행과 SHA256 `4ac7d2de933678d0ab3f8311c73e86e681288810253a47245346f84b87ed277f`로 일치함을 이미 확인한 파일이다. 이 감사에서 그 전체 파일을 다시 스캔하지 않았다.

성공한 bounded read는 **84,353,271 bytes, 6.67초**, 599–1200초의 1,638,196행/602 frame/601개 연속1초 간격이다. 해당 연속 raw 범위 SHA256은 `9ea3792be85b7d65c10cf3d568444dde0691e15abead442d6dd5889a109fd878`, 첫 byte offset은42,052,103이다. 앞서 중단한 duplicate-ID 검사는 같은 범위의 prefix이므로 두 번 합계의 보수적 상한도168,706,542 bytes로256MiB 이하다. FZP 크기/mtime 및 network·mapping·prior·native-equivalence 자료의 SHA는 전후 불변을 확인했다. 생산 파일·활성 런·config·model은 수정하지 않았다.

재현 산출물: `probe_static_route_cohorts.py`, `static_route_matched_cohorts.json`(모든 ID/event/원래 관측 bracket), 이 문서. `python -X utf8 -m unittest diagnostics.test_static_route_cohorts -v`의 **8 tests PASS**: 시간창 경계·차로 모호성·잘못된 source 거절·보간 불가 보존·실제 모든 ID의 순서 있는 outcome·branch source 정합·반복 방문 중복 방지·완전한 bounded 관측을 검증했다.
