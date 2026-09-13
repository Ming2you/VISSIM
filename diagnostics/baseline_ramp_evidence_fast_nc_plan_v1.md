# 완료 baseline의 램프 증거와 fast NC 최소 후처리안

현재 가장 강한 증거는 **66의 필수 차로 접근 실패**, **10639와 직접진출10682의 실제 정지 재고**, 그리고 **10681에는 같은 수준의 정지 재고가 없었다는 차이**다. 이 자료만으로 원하는 수요가 정상 서비스 용량을 얼마나 초과했는지는 식별되지 않는다. 관측 방출은 수요·신호·차로 접근·하류 수용·삭제의 결과이므로 곧바로 용량으로 바꾸지 않는다.

대상은 완료된 `codex_nc5400_r01_baseline_s13`, 원본망 SHA `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`, seed13, 0–5400초다. 이번 작업은 저장된 JSON/CSV/MD와 기존 분석 함수 소스만 읽었다. 새 FZP 스캔·모형·COM·차트·구현은 없다. 숫자와 읽은 파일 SHA는 같은 이름의 JSON에 보존했다. 다른 제어런1200/3300의 차량 수를 이 baseline 수치로 섞지 않았다.

## 판단 가능한 것과 아직 구분되지 않는 것

| 대상 | baseline의 구체적인 관측 | 허용되는 판단 / 남은 구분 |
|---|---|---|
| 66→10633→68 | 372–5400초 매초 정지 재고 존재. 최대N302, 끝N271/정지233. 삭제76 모두1124:1, 직전 lane2=25/lane3=51, 목적10633은lane4 전용. 마지막900초 `301+101−100−31=271`. | **차로 접근 실패 직접 증거**. 마지막 감소를 정상 방출 개선으로 해석하지 않는다. 1124:1은 head 약1.14–1.25km 앞에서도 이미 관측되어 정보가 마지막에만 생긴다는 설명은 약하다. SG3의 실제 유효 GREEN·지속 대기·하류 공간을 동시에 확인한 full-run 포화 표본은 없어 excess demand와 정상 신호용량의 크기는 미식별. |
| 10639, R_F_E1 | 관측 유입292/다른link 이동291/끝N1. 최대N20/정지17, 정지 표본6979개. 2069–2756초 688개 연속 비영정지 표본. | **합류 접근의 지연 존재**. desired demand나 반사실 receiving capacity를 측정한 것은 아님. 원천69의1134:3이 이미 `69→10637→70→10639→2` 목적을 정하며10682 이후까지 가는 경로라 직접진출1130:3과 별도. |
| 10681, R_F_E2 | 관측 유입376/이동376/끝0, 최대N11, speed≤1 정지 표본0. 46/52/66→68 exact prefix 중 해당 출구376회. | 이 baseline에서 **10639 같은 connector 정지 재고 증거 없음**. 이동 중 지연·합류 간섭·상류68의 대기를 배제하지 않는다. 1135:4의1/5는 도달 차량의 조건부 설정 확률이며 희망수요 총량이나 실제 용량이 아니다. |
| 직접진출10682, OR_F_E2 | 유입1370/이동1351/끝N19, 최대N26/정지12. 정지 표본18062, 1775–2939초 1165개 연속 비영정지 표본. | **직접진출 경로의 지연 존재**. native1130:3은 `2→10682→121→123` 계열이며10643→126→71 신호 접근과 다르다. 10682의 감소 방출을 SC1004 SG2 서비스 부족으로 바로 귀속하지 않는다. 본선 lane1 접근과121의 수신/다른 유입 간섭 중 어느 것이 주원인인지는 이 축약 자료로 분리 불가. |
| 10643, OR_F_E1→126→10641→71 | 유입561/이동558/끝3, 정지 표본666. 최초 정지71=156초,10641=955,126=997,10643=1322. | 신호 접근의 정지가 상류로 이어지는 패턴과 일치. wave 속도나71의 독립 원인효과는 미식별. 71 SG2/SG5 GREEN은 매900초270/144개의1Hz 표본으로 같지만 출발량은 변함: 시간량만으로 배출을 설명할 수 없다. |
| 10646, R_F_W1 | 유입1125/이동1121/끝4, 정지 표본46, 최대정지3. 원천1135의3/5 대상. | connector의 지속 정지 재고는 약함. 66의 심한 대기를 해당 on-ramp 자체 정지와 혼동하지 않는다. |

나머지 램프도 빠뜨리지 않기 위해 정본 물리 분해표의 **8 on + 8 off** 전부를 area 결과의 체류량과 연결했다. 아래 두 값은 `전체 체류 veh·h / speed<5 체류 veh·h`이며, connector 길이와 유입량의 영향을 받으므로 서로 다른 램프의 용량 순위가 아니다. 위 표의 `speed≤1 정지 표본`과 임계값/적분 정의도 다르다.

| on-ramp | 체류 / 저속 체류 | off-ramp | 체류 / 저속 체류 |
|---|---:|---|---:|
|10639|5.415 / 2.528|10643|2.694 / 0.212|
|10681|2.206 / 0.001|10682|24.905 / 8.747|
|10490|3.376 / 0.001|10481|118.914 / 103.389|
|10484|7.922 / 0.030|10483|4.389 / 0.018|
|10480|1.256 / 0.011|10479 (Ω밖)|3.644 / 0.000|
|10482|9.980 / 0.002|10491|15.575 / 5.399|
|10646|7.860 / 0.018|10645 (Ω밖)|4.414 / 0.000|
|10644|23.918 / 0.237|10638|7.473 / 0.003|

특히10481·10491의 저속 체류도 크므로 E8만 보고 모든 진출 병목을 설명할 수 없다. 다만 이 둘의 source 선택·head/lane별 시계·하류 공간은 현재 선택32도로 요약에 없어 원인 등급을 부여하지 않는다. 다른 on-ramp의 낮은 저속 체류 역시 숨은 상류 대기나 미삽입이 없다는 뜻이 아니다.

실제 NC 명령 증거는 도시 SG override 없음, VSL120, 8 physical meter 각각900vph/green10이며 1초와900초에 같은74행을 재적용한 것이다. 이 표기 rate900을 정상 물리 capacity로 간주하지 않는다. 전체 native 삭제486건과 끝 미삽입1845대(1098=1182,1099=572,1105=91)는 별도 손실 지표다. 미삽입은 완료 기간 끝의 native 입력 잔여이며 램프별 대기수요로 임의 분배할 수 없다. 전체 input/조건부 route 희망수요 연결은 Flow의 별도 감사 범위다.

## fast NC 종료 뒤 최소 단일 FZP pass: 재사용할 정확한 함수

**현재 두 기존 CLI를 차례로 실행하면 단일 pass가 아니다.** 가장 작은 결합은 아래 기존 reader를 한 번 소비하고, 같은 frame을 선택도로 집계와 정본 area 측정에 순차 전달하는 얇은 generator다. 아직 구현하지 않았다.

| 파일 / 함수 | 재사용할 계약 | 필요한 작은 연결 / 한계 |
|---|---|---|
|`diagnostics/analyze_no_control_corridors.py:native_frames(path,evidence,deadline=...)`|매초 전체 ID/link/lane/pos/speed frame, 중복·누락·비유한 검사, raw와ordered payload SHA를 **같은 파일 읽기에서** 계산.|이 frame으로 선택도로 집계 후 정본 `Frame/Vehicle` 형태로 전달. 두 reader/두 전체 pass나 `tee`의 누적 버퍼는 사용하지 않음. reader가 끝까지 소진돼야 final hash가 완성됨.|
|`scripts/measure_control_area.py:Frame, Vehicle, measure_frames(...)`|0초 fresh empty 가정,1초 실제 frame의 Ω TTT/TD/entry/appeared/unknown/closure와 물리link 체류. 살아서 Ω밖으로 이동한 사건은 TD, 내부 전이는 아님.|정본 함수는 그대로 호출. `final_frame=None`, 실제5400 FZP 완결·tail0을 요구하면 state30/종료COM 불필요. reader 변환은 tuple link를 string으로만 정규화하고 값을 바꾸지 않음.|
|`diagnostics/analyze_no_control_corridors.py:analyze`의 frame-loop 집계식|직전/현재 전체 ID 비교로 선택도로 entry, 다른link departure, global absence, N 및speed≤1 stopped; `Nprev+entry−departure−absence=Nnow`.|현재 함수는 독립 scanner이고 속도평균을 저장하지 않으므로 main 통째 재사용 불가. 작은 누계부만 추출/재사용 예정. 모든1초 transition은 누계하되 **출력만30초**로 낮춤. 창 끝N/정지N/차량평균speed와 `(start,end]` entry/departure/absence를 분리. N0이면 speed=null.|
|`diagnostics/measure_no_control_5400_three_arm_area.py:interval_windows, spatial_checks`|1..5400 exact1s grid·cumulative 차분으로 여섯900초 창, TD분해·전체/창 closure·635inside/601outside검증.|이 함수의5400 고정 계약 유지. 다른 horizon이면 별도 인자화 검토 필요. 원 membership를 각 arm network에 무검증 해시 교체하지 않음.|
|`diagnostics/measure_startup_gui_three_arm_area.py:physical_links`|원본 대비 허용 arm의 물리 geometry/links 동일성 대조.|routing/거리만 바뀐 arm에서 분석용 membership 재바인딩 근거. 원본 membership/모형 evidence는 수정하지 않음.|
|`diagnostics/capture_native_runtime_errors.py:parse_bytes` 및 `measure_no_control_5400_three_arm_area.py:native_errors`|보존된 run-local ERR 원bytes/완전한행prefix/SHA, 삭제·미삽입·기타 경고 분리.|다음 실행이 덮는 network 옆 ERR를 사후 원자료로 쓰지 않음. 새 FZP seek 없이 삭제ID/time/link를 단일pass의 인접frame 소멸에 대조 가능. 전체ID blacklist 금지.|

최소판에는 head crossing/LSA/native route cohort 재구성/42cell 그림을 넣지 않는다. 선택도로 목록은 16개 물리램프와 66/68/69/70/71/121/123/126/127/329/420 등 목적에 필요한 도로로 명시한다. 따라서 결과는 **어디에 차량이 쌓이고 얼마나 관측 이동·소멸했는지**를 설명하며 signal capacity 또는 OD 선택까지 새로 인증하지 않는다. SG별 원인 분석이 필요하면 이후 별도 단계다. `plot_three_arm_cell_episodes.completed_run`은 state/cell CSV를 요구하므로 fast NC의 최소 경로에 재사용하지 않는다.

완주·seed·수요/망SHA·native 파일 extent·실제 command gate는 그대로 필요하다. 기존 `no_control_commands`는 continuous-static의1/900초 재적용을 요구하므로 새 fast runner가 다른 명시적 기록 계약을 사용한다면 **그대로 호출해 PASS로 만들 수 없다**. 정확한 fast profile을 읽어 적용 시각·값을 검증하는 범위만 후속 조정한다.

## 비용과 오차 경계

- 완료 baseline FZP는 **1,415,953,092 bytes / 26,693,633행 / 5400frames**다. 기존 정본 area CLI 한 번의 기록 wall은 **114.77초**였고 여기에는 별도 FZP SHA byte-read도 포함된다. 이는 측정 작업의 실제 기록이며 성능 벤치마크나 새 결합안의 시간 보장은 아니다. 별도 corridor wall은 저장 요약에 없어 만들어 쓰지 않았다.
- 제안은 큰 파일 parse1회와 동시hash1회, live previous/current frame만 보존한다. area 함수의 시간행5400개와 관측 ID 집합은 남고, 모든26.7M차량행을 누적하지 않는다. 선택도로의30초 출력은 작은 편이다. 정확한 결합 wall은 미측정이다.
- 관측 간 지나간 짧은 connector는 놓칠 수 있다. entry는 외생 desired demand가 아니라 첫 관측/도로 이동을 포함한다. absence는 throughput이 아니다. terminal24/120 추론은 별도 유지하고 EOF의 남은 차량은 censored다.
- baseline 삭제27349의4107→4108/link120 사례는 종점까지4.876km 남아 정본에서 unknown으로 처리돼 TD0이었다. 향후 **종점 근처 명시 삭제가 추론 TD와 겹치면 그 사건만** 별도 검토해야 한다. 현 정본 함수는 ERR별 exception hook이 없으므로 그 충돌을 무시한 채 자동 순위 PASS를 내지 않는다. 과거 정상 Ω밖 유출까지 ID단위로 제거하면 안 된다.
- 이번 읽기 작업은 코드 구현·수정·테스트 실행을 포함하지 않는다.
