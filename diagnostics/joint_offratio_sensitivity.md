# 총 유출과 신호·직행 비율의 공동 민감도

**총 유출 비율만 native 값으로 바꾸면 잘못 늘어난 신호 방향 유입으로 추가 정체를 만들 수 있다.** 실제1200초 상태와 같은1200초 명령을 고정한450초 모델 예측에서 total-only는 FE 신호 저장고를 포화시키고 E8 속도를5km/h로 떨어뜨렸다. Native signal/direct/through를 함께 맞춘 arm에서는 해당 포화가 발생하지 않았다. 이 결과는 비율의 일관성 검증이며 물리 모델의 보정 완료나 실제 성능 개선을 뜻하지 않는다.

세 arm은 동일한 합본 canonical runtime, 초기 물리 재고, 수요 전망, geometry/capacity, signal/meter/VSL/offset을 쓴다. 바뀌는 것은 private cfg의 total off ratio와 (joint arm에서만) conditional direct ratio다. 과거 파일에는 현재 route가 없어4대를 명시적으로 보류하며, 모든 arm에서 같은 보류 상태를 유지했다. 새 VISSIM이나 optimizer는 실행하지 않았다.

| 그룹 | native signal/direct/through weight | total off | direct given off | total-only의 signal 몫 | native signal 몫 |
|---|---|---:|---:|---:|---:|
| OR_F_E | 1.6/4/8 | 0.411765 | 0.714286 | 0.212471 | 0.117647 |
| OR_D_E | 4/3/8 | 0.466667 | 0.428571 | 0.248267 | 0.266667 |
| OR_D_W | 3/3/10 | 0.375000 | 0.500000 | 0.199500 | 0.187500 |
| OR_F_W | 1/3/8 | 0.333333 | 0.750000 | 0.172000 | 0.083333 |

FE에서 total-only의 signal 몫0.212471은 native1.6/13.6=0.117647과 다르다. FW도0.172000 대0.083333으로 차이가 크다. 이 비율은 해당 정적 결정에 적용되는 미래 선택의 조건부 prior다. 두 출구 사이 합류 차량, 앞선 경로의 종료·조합, 시간창 내 재고 변화는 이 분모와 같지 않다. 빈1133 signal weight는 공식 VISSIM2020 default1이고 COM passage에서 추정한 값이 아니다.

| 길이(s) | arm | Ω TTT(veh·h) | Ω TD(veh) | FW cell TTT(veh·h) | 최종 FW N | 최종 Ω N | E8 v(km/h) | E8 λ |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 150 | 현재 | 110.155 | 450.041 | 50.069 | 1284.500 | 2866.506 | 96.513 | 3.919637 |
| 450 | 현재 | 379.966 | 1476.047 | 167.822 | 1529.740 | 3603.566 | 81.433 | 3.475753 |
| 150 | total만 native | 109.163 | 477.928 | 46.844 | 1143.896 | 2838.619 | 95.211 | 3.654045 |
| 450 | total만 native | 380.744 | 1358.508 | 152.847 | 1492.588 | 3721.106 | 5.000 | 3.136802 |
| 150 | 일관된 native joint | 108.802 | 496.340 | 46.823 | 1142.167 | 2820.208 | 98.927 | 3.894844 |
| 450 | 일관된 native joint | 376.818 | 1421.943 | 149.856 | 1372.503 | 3657.671 | 84.586 | 3.450567 |

E8의 초기 관측은N51대, 속도41.800km/h다. 첫150초에는 세 모델 모두95–99km/h까지 회복한다. Joint prior가 이 낙관적 회복 문제를 고쳤다는 근거는 없다.450초에서는 total-only가 artificial signal loading에 민감하게 포화되는 차이가 추가로 드러난다.

| 길이(s) | off group | 현재 accepted signal/direct(veh) | total-only signal/direct | joint signal/direct |
|---:|---|---:|---:|---:|
| 150 | OR_F_E | 27.162/25.477 | 55.585/52.138 | 31.056/77.641 |
| 150 | OR_D_E | 16.342/14.376 | 36.348/31.976 | 39.061/29.296 |
| 150 | OR_D_W | 22.915/20.158 | 40.455/35.588 | 38.342/38.342 |
| 150 | OR_F_W | 16.131/15.130 | 24.965/23.417 | 12.116/36.347 |
| 450 | OR_F_E | 81.729/76.661 | 120.048/112.603 | 93.330/233.325 |
| 450 | OR_D_E | 60.111/52.879 | 108.032/95.035 | 122.210/91.658 |
| 450 | OR_D_W | 63.560/55.914 | 70.749/62.238 | 70.749/70.749 |
| 450 | OR_F_W | 49.700/46.618 | 56.790/53.268 | 28.305/84.916 |

총 selected offflow와 signal/direct의 실제 accepted landing을 별도 계측했다. 각10초에서 signal+direct accepted 합은 freeway가 선택한 offflow와 일치하고 scheduler rejection은0이다.150초 receiving rejection은 전부0.450초 total-only의 DW/FE requested 차단은28.115/29.129대, joint의 DW만25.652대다. 따라서 branch landing 이후의 이중계수나 차량 삭제로 결과가 만들어진 것은 아니다.

| 450초 arm | FE signal 모델저장고 N/cap | FE direct 모델저장고 N/cap | FE 첫 receiving차단 시각 | R_D_W queue | R_F_W queue | R_D_E queue | R_F_E queue |
|---|---:|---:|---:|---:|---:|---:|---:|
| 현재 | 66.623/106.333 | 35.970/220.000 | 없음 | 153.200 | 123.878 | 39.903 | 56.025 |
| total만 native | 106.333/106.333 | 29.685/220.000 | 1520 | 153.200 | 144.992 | 57.501 | 63.065 |
| 일관된 native joint | 69.212/106.333 | 80.964/220.000 | 없음 | 153.200 | 174.044 | 55.117 | 75.368 |

FE total-only에서1,520초부터 receiving이 막히며, 마지막 λ=3.136802, rho93.044veh/km/lane, N149.854대, v5km/h다. Joint는 λ=3.450567, rho21.737, N38.511, v84.586이다. Joint direct 흐름은 다른 하류 문제도 바꾼다. 예를 들어 R_F_W queue가현재123.878→joint174.044대로 늘며,450초 TD는현재1476.047보다 joint1421.943이 적다. 한 비용값으로 물리 prior를 선택하거나 성능 향상이라고 해석해서는 안 된다.

위 direct 재고/용량은 모델 landing receiver `SC1004_W_out`의N/cap220이다. 물리10682 단독 저장능력이라고 부르지 않았다. 초기8개 물리 connector의 관측 대수와 projection ownership은 JSON의 `initial_physical_connector_counts_and_projection`에 별도 보존했다. λ 역시 현재 모델의 신호저장고 기반 경로와 기존 grouped cell 위치를 따르며, direct 실제 작은 connector에서 생기는 국지 queue tail을 식별한 결과가 아니다.

모든6endpoint의 원본cfg/state/control/demand 불변, 모든10초 제어벡터 일치, macrostep Ω재고 closure, 각450초의 첫150초와 독립150초의 trace 완전일치, 전후 source hash 불변을 검사했다. 현재 결과를 바탕으로 적용 가능한 가장 작은 결론은 total ratio 단독 교정안을 물리적으로 일관된 parameterization으로 취급하지 않는 것이다. 다음 물리 식별에는 출구 사이 합류와 decision eligibility를 포함한 origin/route cohort 및 실제 branch geometry가 필요하다.

생산 및 활성 config 변경 없음. 결과는 `joint_offratio_sensitivity.json`,10초 trace는 `joint_offratio_sensitivity_trace.json`, 읽기 전용 private overlay는 `joint_offratio_private_overlay.json`. 재현은 `python -X utf8 -m diagnostics.probe_joint_offratio_sensitivity`, 표/그림은 `python -X utf8 -m diagnostics.render_joint_offratio_sensitivity`.

![Model-only native joint sensitivity](joint_offratio_sensitivity.png)
