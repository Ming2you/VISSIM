# β300 오프라인→실제 제어 연결 검증

실제 `codex_contract_beta300_s13_1050_v3_20260910`의 900초 결정은 사전 실행과 일치했다. VSL 44키, 모델 meter 4개, green 68개, offset 17개와 N_P/N_UF가 모두 같고, 두 decision CSV 213행은 원본 bytes까지 동일하다. 이번 선택은 VSL 전부120, 모델 meter 전부1800이며 offset 11개가 0이 아니다. 네 수단의 출력 정합을 검증한 것이며 네 수단 모두가 기준에서 변경됐다는 뜻은 아니다.

사전 실행은 `area_production_preflight/wu-link_t900_beta300_20260910T021854343272Z`이며, NC v2의 실제 state900·previous750을 현재 β300 config로 최적화했다. 실제 런도 동일 β300 config SHA `35f124ef388fe18dc60dbac3599f2e28175ab71e21b4fd2a6a38d59aa0ad6141`을 사용한다. 공통으로 기록된 source 71개가 모두 같고, 비교한 입력 파일은 읽기 전후 변화가 없다. 이 비교는 optimizer/model/VISSIM을 다시 실행하지 않았다.

두 raw900의 전체 순간 물리 값, 차량 records/routes, FW셀과 legacy 누적 관측은 정확히 같다. 235개 head의 신원·좌표·통과 수·실제 GREEN 및 창[750,900]도 같다. 차이는 각자의 run provenance와 그 관측이 생성된 config SHA뿐이다. 이를 삭제하거나 다른 런의 carry를 허용하지 않고 그대로 보존했다.

이전750의 floor24개·candidate27개, 현재900의 floor28개·candidate27개는 물리 link/phase별 값이 정확히 같다. 런/config가 다른 것을 나타내는 원래 metadata hash suffix와 context identity도 JSON에 각각 보존했다. suffix를 물리 비교용 표에서만 분리했으며 controller에 재주입하지 않았다. 900의 prior_discarded0, groups_updated17, groups_carried24 등 상태도 같다. 이 카운트는 실제 포화용량 식별이나 모든 movement에 성공적으로 설치된 수를 의미하지 않는다. no_model_members19는 그대로 남는다.

첫 제어 창[900,1050]의 실제 관측 노출도 검증했다. 216개 controlled head가 공유하는107개 SG마다 immediate[900,1050)150행과 post_step(900,1050]150행, 총32,100행이 누락·중복·실패 없이 존재한다. 새로운900초 명령의 immediate 상태를 왼쪽 hold로 적분한 GREEN과 수집기 값이 모두 exact이다. 900초의 이전 명령 post_step을 새 hold로 잘못 사용하는 방식은 배제했다.

남은19개 native head 중18개는 실제 native LSA의 이전 상태와 이후 상태변화로 같은 GREEN을 확인했다. SC5/SG18의 한 head는 LSA 변화가 전혀 없으므로 독립 실제 event 비교가 불가능하다. 이 한 건은 원본에 pinned된 native program의 GREEN0과 수집기 GREEN0이 같다는 좁은 근거로 별도 표시했다. 이를 실제 trace로 확인된107개 controlled SG와 섞어 성공 범위를 부풀리지 않았다.

동일 표시시각의 COM과 FZP 경계도 구분했다. 기준 raw900은2,591대/Ω1,763대이고 FZP900은2,599대/Ω1,765대다. Ω 차이2대는 ID3177(link120, 위치6984.50m)와3211(link24,3357.32m)이며, COM에는 이미 없고 완전한 FZP901에도 없다. 물리 terminal 길이6958.141079m/3345.981430m를 각각26.358921m/11.338570m 지난 상태다. link120의 분기10638/10645는2402.481m/2087.381m로 종단보다 훨씬 앞이며 종단에는 outgoing connector가 없다. 이것은 이미 투영에 존재해야 할 차량을 놓친 증거가 아니라 두 관측 단계의 terminal 가용성 차이를 지지한다. 정확한 subsecond 유출시각은 추론하지 않으며, 이전의 정상 Ω 경계 이탈까지 ID blacklist로 지우지 않는다. 이 대조는 FZP 약295KB만 읽었다.

재현 자료:

- `beta300_preflight_live900_comparison.json`: raw/action/context/source/원본 CSV 및 물리 floor 대조.
- `beta300_controlled_head_window900_1050.json`: 모든 head와107개 실제 제어 SG의 경계·cadence·GREEN 대조.
- `observer_raw900_terminal_frame_audit.json`:900/901 선택 raw 범위 SHA와 종단 형상.
- `test_preflight_live_audits.py`: command 경계, 누락/중복/비유한/비정수/실패 readback, metadata 비교 중 충돌 거부 회귀4개. 기존 관측/pair7개와 합계11개 PASS.

이 결과는 emitted decision 및 첫 관측 창의 정합성이다. 실제 제어의 교통 성과는 동일 길이 NC와 별도로 비교해야 한다. 생산·모델·config·run 원본 변경은 없다.
