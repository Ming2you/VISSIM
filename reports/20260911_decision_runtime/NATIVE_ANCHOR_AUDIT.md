# 현재 native 신호와 제어 기준점의 표현 차이

2026-09-11, 읽기 전용 조사. 새 VISSIM 실행이나 모델 rollout은 하지 않았다.

고정망 `diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx`가 지정한 `.sig`와 현재 선택된 `outputs/signal_group_actuation_plan_mainline_20260825.json`을 직접 비교했다. 계획의 정규화 JSON SHA256은 `d2bf41f133ab39216dbdc6734187e286cee620f2c5b6e6946258cc14743880d7`로 이전 조사와 같다. 원자료·모든 SG 창·최소 잔차는 `current_native_anchor_source_audit.json`에 있다.

현재 `phase_layout_order()`는 대부분 SC에 p2→p1→p3→p4를 부여한다. native 녹색 길이를 그대로 넣어도 순서가 달라지는 11개 SC는 어떤 offset으로도 native와 같아지지 않는다. 전체 17개 중 SC107·108·109·1001만 현행 순서와 적절한 offset으로 재현 가능하다. 나머지 중 11개는 SC별 순서를 바꾸면 모든 본선 SG의 RED/GREEN/AMBER가 native와 일치한다. 이는 가능성 검증이며 실제 writer 변경은 하지 않았다.

| SC | 현재 순서에서 주기당 최저 불일치 SG·초 | native와 같은 순서 한 가지 | 그 순서의 writer offset [초] |
|---|---:|---|---:|
| 1 | 198 | p3→p4→p1→p2 | 19 |
| 5 | 214 | p1→p2→p3→p4 | 36 |
| 6 | 198 | p3→p4→p1→p2 | 13 |
| 11 | 306 | p4→p1→p2→p3 | 18 |
| 12 | 222 | p2→p3→p4→p1 | 22 |
| 101 | 246 | p3→p4→p1→p2 | 25 |
| 105 | 198 | p1→p2→p3→p4 | 40 |
| 1002–1005 | 각 214 | p1→p2→p3→p4 | 0 |

표의 offset은 `intended_state(windows, t + offset, cycle, amber)` 좌표다. native `.sig` offset 자체를 같은 부호로 복사하는 값이 아니다. 녹색 길이는 JSON에 기록한 native 길이를 사용했다. 1초 단위 전체 주기 상태를 모든 정수 offset과 24개 순서에서 대조했다.

SC7과 SC16은 순서·offset 변경만으로 해결되지 않는다.

- **SC7:** native 주기는 120초다. p1의 SG4·8은 0–67초, p2의 SG7은 0–90초로 실제 동시녹색이고, p4의 SG1은 93–117초다. 현행 순차 표현은 녹색 합 181초+황색 9초=190초다. p2의 SG3, p4의 SG5 등은 영구적색이어서 단순 phase→모든 SG 전개도 부정확하다.
- **SC16:** native는 150초다. p3의 SG2·6이 0–27초, p2의 SG3·7이 64–81초, p1의 SG4·8이 84–147초다. p3 황색 이후 **30–64초의 34초 공백**이 순차 writer에서 사라져 116초가 된다. 이 공백을 다른 녹색으로 채우면 같은 신호가 아니다.

선택된 `fast_nc_fw080_urban050_s13_9000_v1/vissim_eval/baseline_001.lsa`의 600–1350초에서 기록된 본선 SG 상태 **91,500개가 `.sig` 파서와 전부 일치**했다. 영구적색 SG는 native LSA에 최초 상태가 없으므로 그 초기 상태는 이 기록만으로 검증되지 않는다. `.sig`의 영구적색 선언은 별도로 확인했다. 기록 누락을 실행 검증 성공으로 세지 않았다.

현재 코드의 `install_native_signal_structure()`는 기본 `drive_cycle_recompute=True`에서 모든 SC를 제어 주기 150초로 다시 계산하고, SC7의 동시성은 movement 용량 배율로 근사한다. 이 설정은 native 시계와 동일하다는 증거가 아니다. `native_fixed_control()`도 `native_fixed_native_program_replay=0.0`을 명시한다. 저장된 `action_000750.json`의 무제어 명목 녹색은 일반 SC 각 34.5초, SC7·16 각 live phase 47초, offset 0이므로 실제 native 이력을 나타내지 않는다.

실제 native 기준점에는 최소한 **실제 SG별 녹색·황색·적색 창, 실제 주기, 시간 offset, native/COM 소유권**이 필요하다. 기존 `.sig` 파서가 창을 제공하므로 또 다른 파서는 필요 없다. 하지만 현행 고정합 순차 green/offset 전략공간에 이 기준점을 억지로 투영하면 다른 물리 명령이 된다. 이전 native 운전 이력의 관측·서비스 계산과 앞으로 적용할 COM 후보의 명령을 구분해서 표현해야 한다. 정확한 native 기준점 주변 가격을 요구한다면 SC7의 겹침과 SC16의 공백까지 표현한 뒤 그 좌표의 유효 섭동을 정해야 한다. 단순 명목 action을 “실제 기준점”이라고 이름만 바꿔서는 안 된다.
