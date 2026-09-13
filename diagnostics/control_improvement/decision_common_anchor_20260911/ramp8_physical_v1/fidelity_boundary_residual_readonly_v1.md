# 기존 JSON 경계 잔차 검토

900–1350초 완료 자료와 정본 코드만 확인했다. 신규 모델·native·FZP 읽기와 소스 수정은 0이다.

| 비교 항목 | Native | Model | 차이 |
|---|---:|---:|---:|
| 기록된 entry: 정의 불일치 | 2166.000 | 1710.779 | -455.221 |
| 권역 내 첫 등장 / 모델 생성·본선수락 | 1622.000 | 1628.872 | +6.872 |
| live inward boundary: 모델은 잔여합 | 544.000 | 390.832 | -153.168 |
| 도시 inside 생성을 포함한 entry | 2166.000 | 2019.704 | -146.296 |

모델 `entered_veh`에는 inside 도시 생성 308.925대가 빠져 있다. 이는 내부input132.500 + inside gate93.113 + shared69 83.313대이며 이미 모델 재고에 들어갔다. `emit_input`의 source/target 양쪽이 inside여서 경계 진입으로 세지 않는 정의다. 따라서 308.925대를 **비교 지표에만** 더하며 수요나 동역학에 다시 넣지 않는다. 앞서 전달한 boundary81.907/차이−462.093은 이 값을 중복 차감한 잠정 계산으로 철회한다.

| live 출구 묶음 | Native | Model | 차이 |
|---|---:|---:|---:|
| SC1004 collector to123 | 157.000 | 124.153 | -32.847 |
| SC1001/sc2001 collector to125 | 101.000 | 28.550 | -72.450 |
| two westbound direct offramps | 189.000 | 147.439 | -41.561 |
| other live exits, aggregate residual; no exact edge allocation | 619.000 | 306.602 | -312.398 |

출구 묶음은 정본 경로의 물리 목적지를 맞춘 것이며 동일 차량·동일 순간 대응을 증명하지 않는다. 원장은 경로의 outward/inward crossing 수를 지원하므로 일반적인 끝점 전용 계수기는 아니다. 다만 이 정적 계약에는 out/in이 모두 양수인 경로가 없고, 현재 JSON에는 native 진입 edge별 집계와 모델 entered-by-route가 없어 누락된 중간 유출·재진입과 공급/방출 지연을 더 분리할 수 없다.

Native 첫 등장은 입력 ID별 발생량 검증과 다르며 TD는 기존 review flag가 있고 미확인 내부 소실12건을 제외한다. 수요와 native TTT/TD 정의는 유지한다. 부족분을 계수로 채우지 않고, 후속 native 후 필요한 동일 경계 증거를 요청한다. 출처11개 SHA256과 정확한 산식은 동명 JSON에 보존했다.
