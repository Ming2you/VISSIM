# 경로 관측을 추가한 무제어 기준 런의 전체 검증

**관측 collector 추가는 이 seed13 무제어 실행의 물리 궤적을 바꾸지 않았다.** 새 `codex_area_observed_nc_s13_20260910`과 기존 1초 NC는 1~5400초의 26,693,633개 FZP 차량 행이 정확히 같다. 차량 ID·link·lane·위치·횡위치·속도·체류시간·delay 전체가 동일하다. 날짜 등 데이터 앞 머리말만 비교에서 제외했다.

기존 1초 기준은 `codex_meter10639_g5_s13_20260910`이다. 이 시도는 명령 생성 실패로 제어를 적용하지 못했으므로 metering 성능 실험으로 사용하지 않는다. 원래 5초 NC와 5,336,479개 공통 FZP 행이 같다는 앞선 증거에 따라 더 촘촘한 NC 측정으로만 사용했다. 새 자료는 이 1초 자료 전체와 일치한다.

| 검증 | 결과 |
|---|---|
| FZP 모든 차량 행 | 26,693,633 / 26,693,633 exact |
| 기본 물리 CSV | 181 / 181 exact (controller/wall-time 열 제외) |
| FW 42셀 CSV | 7,602 / 7,602 exact |
| Physical link CSV | 56,644 / 56,644 exact |
| 실제 active beta0 configure / 초기 투영 | 900·1500·1800·2100·2700·3600·4500·5400초 모두 PASS |
| 초기 Ω raw=model [veh] | 1763, 2841, 3240, 3681, 4579, 5050, 4885, 4667 |
| 경로 미확정 holding / 양수 미지원 / 초기 entry·TD·event | 모든 anchor 0 |

모든 anchor는 실제 새 action000001, 두 route corridor(1128/1129)의 error 정책, native1091 및 세 phase 보정을 가진 실제 canonical configure를 사용했다. Endpoint나 optimizer를 이 감사에서 실행하지 않았다. 투영 provenance의 어떤 새 지원 link가 양수였는지는 `observed_nc_snapshot_audit_5400.csv`에 보존했다.

Ω 지표는 새 FZP를 정본 `scripts/measure_control_area.py`로 독립 재계산했으며, 기존 측정의 provenance를 제외한 모든 키와 같았다.

| 지표 | 새 NC = 기존 NC |
|---|---:|
| Ω TTT [veh·h], 1초 관측 사다리꼴 적분 | 5578.610277778 |
| 직접 관측한 Ω→밖 crossing [events] | 18272 |
| 검증된 terminal에서의 소실 추론 [events] | 7931 |
| 위 두 종류 합 [events] | 26203 |
| 출구로 세지 않은 미확정 내부 소실 [events] | 398 |
| 반복 출구 events / 세어진 고유 ID | 937 / 25266 |

말단 추론은 직접 관측과 분리했다. 1초 안에 완료된 안→밖→안 왕복은 누락될 수 있고, terminal 근처 제거와 정상 출구는 관측만으로 완전히 구별되지 않는다. 시간 누락·꼬리 외삽은 0이며, 매 프레임 sampled stock closure 잔차는 0이다. 마지막 native FZP Ω재고 4670과 같은5400초의 후행 COM snapshot 4667은 수집 단계가 달라 3대 차이가 난다. 두 단계의 재고를 섞어 추가 유출을 만들어내지 않았다.

정체 시작·전파도 같은 자료에서 그대로 재현된다. 비교 기준은 차량5대 이상이고 평균속도30km/h 미만인 30초 표본이 최소90초(4개 연속표본) 지속하는 최초 시각이다. E8의1350초에서 상류 E7 1470, E6 1650, E5 1830, E4 1980, E3 2160, E2 2340, E1 2490, E0 2730초로 저속 구간이 확대된다. 이는 관측된 시공간 순서이며 이 자료만으로 특정 신호/램프가 원인이라고 단정하지 않는다. 모든42셀의 최초시각·전체저속episodes·최저속도·최대밀도는 JSON/CSV에 있다.

![동일 NC의 시공간 속도와 Ω 재고](observed_nc_congestion.png)

초기 투영과 관측 동치는 예측모형의 정확성을 증명하지 않는다. 아직 확인된 미래 native input 누락, 분기 cohort/합류 모형 및 신호 권한 제약은 별도의 물리 예측 문제로 남는다.

재현: `python -m diagnostics.audit_observed_nc_snapshots --max-anchor 5400 --output observed_nc_snapshot_audit_5400`; `python -m diagnostics.audit_observed_nc_trajectory`; `python scripts/measure_control_area.py --run evaluation/runs/codex_area_observed_nc_s13_20260910 --fzp-only --out diagnostics/observed_nc_full_measurement`; `python -m diagnostics.render_observed_nc_audit`. 입력·생산 파일 hash와 결과는 각 JSON에 보존한다. 생산 코드나 활성 config를 변경하지 않았다.
