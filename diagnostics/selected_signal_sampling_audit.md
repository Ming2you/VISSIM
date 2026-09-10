# Selected signal sampling audit

동일 720→870초 NC 자료에서 30초 표본은 1초 표본의 링크 이탈 335대 중 65대(19.4%)를 놓쳤다. 71은 54→26대, 1220021201은 49→31대다. 이번 7개 링크의 NC FZP 30초 계수는 실제 raw900 COM 계수와 전부 수치가 일치한다. 이 비교 안에서는 실제 관측 손실을 재현했지만 다른 시각의 COM/FZP 위상까지 동일하다고 일반화하지 않는다.

같은 완료 NC 1초 FZP의 720–900초만 binary seek로 읽었다. 1초 전이와 30초로 downsample한 전이에 VBS `AccumulateDepartures`의 동일 규칙을 적용했다. 이탈은 이전 표본에 있던 차량이 다른 링크에 있거나 현재 표본에서 사라진 경우다. 신호 head 통과·정지선 전 우회·누락된 관측은 별도 표로 남겼다.

아래의 1초→30초 차이는 같은 자료의 표본 간격 손실이다. 실제 제어 런 raw900의 COM counter와 NC FZP 30초 counter 차이는 COM/FZP 관측 위상·collector 차이도 포함하므로 표본 간격 손실로 합치지 않았다. 실제 raw900 counter 창은 720→870이고, 750→900 표는 창 정렬 비교다.

## 720→870 seconds

| Link | 1s departures | 30s departures | Loss (%) | raw900 COM | COM−FZP30 | used green / native union (s) |
|---|---:|---:|---:|---:|---:|---:|
| 66 | 17 | 17 | 0 (0.0%) | 17.0 | 0.0 | 34.5 / 69 |
| 71 | 54 | 26 | 28 (51.9%) | 26.0 | 0.0 | 34.5 / 69 |
| 30 | 48 | 38 | 10 (20.8%) | 38.0 | 0.0 | 34.5 / 69 |
| 403 | 48 | 41 | 7 (14.6%) | 41.0 | 0.0 | 69.0 / 23 |
| 1220011503 | 58 | 56 | 2 (3.4%) | 56.0 | 0.0 | 34.5 / 75 |
| 1220021201 | 49 | 31 | 18 (36.7%) | 31.0 | 0.0 | 34.5 / 74 |
| 127 | 61 | 61 | 0 (0.0%) | 61.0 | 0.0 | estimate 없음 / 69 |

| Link | Head crossings, lower bound | Before-head bypass | No-head source lane | Unresolved departure/lane/distance | Already post-head departure |
|---|---:|---:|---:|---:|---:|
| 66 | 13 | 4 | 0 | 0 | 3 |
| 71 | 28 | 16 | 0 | 10 | 8 |
| 30 | 21 | 0 | 26 | 1 | 3 |
| 403 | 25 | 0 | 23 | 0 | 3 |
| 1220011503 | 53 | 5 | 0 | 0 | 53 |
| 1220021201 | 26 | 23 | 0 | 0 | 13 |
| 127 | 61 | 0 | 0 | 0 | 25 |

Head crossings는 같은 링크 내 위치 bracket과 단일 connector 경로 bracket의 합이다. `Already post-head`는 이탈 직전 표본에서 이미 head를 지난 차량이며 앞선 초의 crossing과 겹칠 수 있으므로 표 열을 더해 이탈량으로 사용하면 안 된다. SG·lane·position별 개수와 경로 추론 방식은 `_heads.csv`, 개별 차량 근거는 JSON에 보존했다.

| Link | 누락: 확인된 head 경로 이탈 | 누락: head 전 우회 / no-head 차로 | 누락: 미확정 |
|---|---:|---:|---:|
| 66 | 0 | 0 | 0 |
| 71 | 4 | 14 | 10 |
| 30 | 3 | 7 | 0 |
| 403 | 0 | 7 | 0 |
| 1220011503 | 0 | 2 | 0 |
| 1220021201 | 7 | 11 | 0 |
| 127 | 0 | 0 | 0 |

이탈 경로 표는 각 1초 이탈을 한 번만 분류한다. `head 경로 이탈`은 실제 head crossing 시각과 같지 않으며, 창 이전에 이미 head를 지난 차량도 포함할 수 있다. 이 표 역시 포화교통량이 아니다.

## 750→900 seconds

| Link | 1s departures | 30s departures | Loss (%) | raw900 COM | COM−FZP30 | used green / native union (s) |
|---|---:|---:|---:|---:|---:|---:|
| 66 | 16 | 16 | 0 (0.0%) | — | — | 34.5 / 69 |
| 71 | 60 | 30 | 30 (50.0%) | — | — | 34.5 / 69 |
| 30 | 31 | 24 | 7 (22.6%) | — | — | 34.5 / 69 |
| 403 | 46 | 40 | 6 (13.0%) | — | — | 69.0 / 23 |
| 1220011503 | 55 | 54 | 1 (1.8%) | — | — | 34.5 / 75 |
| 1220021201 | 45 | 27 | 18 (40.0%) | — | — | 34.5 / 74 |
| 127 | 58 | 58 | 0 (0.0%) | — | — | estimate 없음 / 69 |

| Link | Head crossings, lower bound | Before-head bypass | No-head source lane | Unresolved departure/lane/distance | Already post-head departure |
|---|---:|---:|---:|---:|---:|
| 66 | 13 | 3 | 0 | 0 | 3 |
| 71 | 32 | 20 | 0 | 8 | 11 |
| 30 | 14 | 0 | 17 | 0 | 1 |
| 403 | 25 | 0 | 21 | 0 | 3 |
| 1220011503 | 50 | 5 | 0 | 0 | 50 |
| 1220021201 | 24 | 19 | 0 | 0 | 11 |
| 127 | 58 | 0 | 0 | 0 | 24 |

Head crossings는 같은 링크 내 위치 bracket과 단일 connector 경로 bracket의 합이다. `Already post-head`는 이탈 직전 표본에서 이미 head를 지난 차량이며 앞선 초의 crossing과 겹칠 수 있으므로 표 열을 더해 이탈량으로 사용하면 안 된다. SG·lane·position별 개수와 경로 추론 방식은 `_heads.csv`, 개별 차량 근거는 JSON에 보존했다.

| Link | 누락: 확인된 head 경로 이탈 | 누락: head 전 우회 / no-head 차로 | 누락: 미확정 |
|---|---:|---:|---:|
| 66 | 0 | 0 | 0 |
| 71 | 6 | 16 | 8 |
| 30 | 2 | 5 | 0 |
| 403 | 0 | 6 | 0 |
| 1220011503 | 0 | 1 | 0 |
| 1220021201 | 7 | 11 | 0 |
| 127 | 0 | 0 | 0 |

이탈 경로 표는 각 1초 이탈을 한 번만 분류한다. `head 경로 이탈`은 실제 head crossing 시각과 같지 않으며, 창 이전에 이미 head를 지난 차량도 포함할 수 있다. 이 표 역시 포화교통량이 아니다.

## 해석 및 최소 관측 수선

두 창의 손실은 모두 30초 bin 시작 시 해당 source에 없었다가 중간에 들어와 나간 차량이다. 같은 source로 재진입해 endpoint에서 상쇄된 사례와 endpoint에서 사라진 차량은 이 7개 도로·두 창에서 0이다. 따라서 이 사례의 차이를 VISSIM 차량 제거로 설명할 근거는 없다.

720→870의 누락 65대는 확인된 head 경로 이탈 14대, head 전 우회/no-head 차로 41대, lane 미확정 10대로 나뉜다. 특히 71의 누락 28대는 4/14/10대이고 403의 누락 7대와 1220011503의 누락 2대는 모두 우회/no-head 경로다. 따라서 1초 link departure의 증가분을 전부 신호 처리량으로 해석하는 수선도 잘못이다.

720→870의 직접 식별된 정지선 전 가지는 66→10632 4대, 71→10642 16대, 1220011503→10528 5대, 1220021201→10142 23대다. 30→10686은 26대, 403→10565는 23대가 source 차로에 head가 없는 가지로 나간다. 71의 추가 10대 및 30의 1대는 이탈 전후 lane correspondence가 달라 신호/우회로 임의 귀속하지 않았다. 각 native SG head의 crossing count는 head union의 총 이탈과 다르다.

표본 간격 손실과 녹색 분모는 독립 결함이다. action750 CSV에는 도시 신호 command가 없으므로 JSON 기본 녹색은 실제 native 노출이 아니다. 같은 30초 계수에 정확한 native 녹색을 넣어도 표본 사이에 들어왔다 나간 차량을 복구하지 못한다. 반대로 1초 계수로 바꿔도 정지선 전 우회와 미실행 녹색 분모는 남는다.

최소 collector 수선은 매 simulation step 차량 ID 전이를 단일 timestamp로 누적하고 decision 시각까지 창을 닫아 serialize/reset하는 것이다. 초기 endpoint는 다음 창 전이용으로 보존하고 이중 누적을 막아야 한다. 실제 실행 SG 노출을 같은 창에 적분하고, 정지선 용량에는 SG/lane/position crossing과 GREEN 중 queue/receiving 상태가 필요하다. 이 감사는 새 포화용량을 fit하거나 기본 206.53을 대체하지 않는다.

1초 관측도 짧은 링크를 완전히 건너뛰거나 lane change와 긴 경로를 식별하지 못할 수 있어 정확한 throughput이라고 하지 않는다. 새로 source에 나타났을 때 이미 head를 지난 경우도 JSON에 검열로 분리했다. head 전 bypass는 이 링크의 head를 우회했다는 뜻이며 경로 전체가 무신호라는 뜻은 아니다.

읽은 FZP 데이터: 181 frames, 454,095 rows, 23,245,517 bytes (전체 파일 1,415,953,087 bytes). 선택 원시 범위 SHA와 geometry/native LSA/SIG/source SHA를 JSON에 보존했다. 전체 FZP 해시는 재계산하지 않았다. 모델/optimizer/VISSIM 실행 및 production 변경은 0이다.

재현: `python -X utf8 -m diagnostics.selected_signal_sampling_audit` (기존 출력이 있으면 덮어쓰지 않음).
