# 현재 빌드의 장기 무제어 재현

`codex_contract_nc_headoff_continuous_s13_5400_v3_20260910`은 5,400초를 정상 완료했다. 이전 `codex_area_observed_nc_s13_20260910`과 native FZP의 26,693,633개 행이 순서·모든 필드에서 정확히 같다. 날짜 등 헤더는 비교에서 제외했다. 공통 payload SHA256은 `2a0747f1c8f363214273780782d97e5b7b5ca8b5024af8b745e26f5cbdabaa79`이다.

새 장기 런과 현재 빌드의 1,050초 OFF continuous 런은 135개 source pin을 포함한 candidate manifest, runtime provenance의 모든 입력 SHA, 환경, seed13이 같다. 요청 길이는 각각 5,400/1,050초다. 따라서 네 조건 대조 당시 남아 있던 과거/현재 코드 혼동은 이번 재현으로 줄었다. 같은 현재 빌드에서도 짧은 런의 마지막 20초가 장기 런의 해당 구간과 달랐으므로 성능 비교에서는 같은 요청 길이를 사용한다. 이 사례를 모든 네트워크·seed의 VISSIM 종료 길이 효과로 일반화하지 않는다.

장기 기준은 기존 1초 측정의 Ω TTT 5,578.610277778 veh·h, TTD 26,203건과 연결된다. 관측기 ON/OFF의 누적 관측창은 다르므로 물리 궤적 동일성을 MPC 관측·선택의 동일성으로 해석하지 않는다. 실행 방식은 continuous, 실제 종료 경과는 541초이며 시작 무응답 300초 조건은 발동하지 않았다.

Native ERR에는 차로 변경 대기 후 강제 제거 486건(Ω 내부 240/외부 246)이 있다. 입력 미삽입 잔량은 1098=1,182대, 1099=572대, 1105=91대다. 이전 source β0 장기 제어의 해당 값은 1,932/574/71대였다. 그 제어는 총량 성능뿐 아니라 1098 진입 전 대기도 더 컸다. 미삽입 차량을 Ω 내부 재고로 더하거나 강제 제거를 TTD로 보상하지 않는다.

이번 capture의 `terminal_inside_removal_count=1`은 **종단 도로에 있었다**는 분류다. ID27349는 4,107초에 도로120의 위치2,082.4m에서 제거됐다. 도로의 물리 끝은 약6,958m여서 이 사건을 정상 종단 이탈로 볼 근거가 없다. 이력 `capture.json/.md`의 공통 제한 문장 중 “No terminal24/120 native removal…”은 고정 문구 오류다. 실제 집계와 제거 행이 우선하며, producer는 종단 도로 소속과 실제 종단 추론을 구분하도록 문구를 고쳤다. 원시 ERR와 당시 생성 결과는 보존했다.

검증 근거는 `current_nc_v3_vs_original_full5400_trajectory.json`과 `current_nc_v3_reproduction_summary.json`이다. 후자는 양 런의 manifest와 native capture SHA, 미삽입 입력 및 해당 제거 행을 보존한다. 기존 `observer_four_condition_comparison.md`는 이 장기 런 이전의 네 조건 결과이며, 장기 확인이 아직 없다는 문장은 이번 후속 결과로 갱신된다.
