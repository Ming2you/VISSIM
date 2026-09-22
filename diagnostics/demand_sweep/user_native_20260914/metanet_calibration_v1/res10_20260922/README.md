# SimRes10 완료 자료를 이용한 METANET 재보정

사용자 요청: 지금까지 완료한 최근 수요 런으로 METANET을 다시 보정한다. 새 VISSIM 런, 수요·경로 변경, controller 실행은 포함하지 않는다. 기존 FW80%·도시100% NC9000과 자동 히트맵이 종료된 뒤 모든 궤적을 추출했다. 이전 RM/VSL 큐는 계속 중지 상태다.

결과는 `fit_v1/completion.json`, `fit_v1/README.md`, `fit_v1/summary.json`을 확인한다. completion이 없으면 완료된 보정으로 취급하지 않는다. 생산 기본값은 변경하지 않았다.

## 자료와 실험 분리

- 훈련: 전체 수요100%, 무제어9000초. 초기900초 이전 저밀도 자료로 기존 자유속도 갱신 함수를 재사용하고,9개 초기 상태에서450초 동역학을 보정한다.
- 수요 검증: 전체90%9000초, FW80%·도시100%9000초, 전체80%5400초, 전체70%5400초. 모두 seed23이다. 다른 seed 검증이나 맹검 자료라는 주장을 하지 않는다.
- 동측·서측 각각 기존6개 계수: 자유속도 배율, 임계밀도 배율, τ, ν, κ, merge 감속계수. 기존 FD 형상과 lane-drop 설정은 그대로다. 과거 미채택 차로·회복 보정 후보를 모두 합쳐 넣지 않았다.
- 동측31셀·서측31셀, 램프별 분리된 기존 guarded mesh를 유지한다. 각 실행 XML과 물리 기하 fingerprint가 일치해야 한다.
- `conditioned_diagnostic`: 실제 미래 외부 경계 유량을 알려준 물리식 진단. 미래 본선 상태는 주입하지 않는다.
- `history_forecast`: 초기 상태와 과거150초 경계 관측, 알려진 입력 시간표만 사용한다.450초 동안 본선 상태를 재설정하지 않는다. 보정 계수를 고정한 뒤 두 방식을 별도로 검증한다.
- Ω 전체 TTT, 도시 신호·램프 대기까지 포함한 폐루프 제어 이득은 이번 실험 범위 밖이다. 무제어 자료만으로 RM/VSL 이득 보정을 인증하지 않는다.

## 보정 전에 해결한 관측·수치 문제

1. 새 FZP는5초 간격이며 실제 시각은5.1,10.1,…초다. timestamp를 정수로 자르지 않고 기존 추출기·경계 예측·평가 코드를 명시적인 phase 및 가변 셀 수에 맞췄다.8995.1초 이후를 만들어내지 않는다. 마지막 완결30초 창은8970.1초다.
2. 최소 세그먼트 길이는76.03m다. 합성 상태의 기존5초 적분은 밀도 보정18회, 최대 차량 보존 오차7.04대를 냈다.1초 적분에서는 오차1.42e-14대, 밀도·속도 보정0회였다. `numerical_preflight.json`은 실제 교통 보정 결과가 아닌 수치 사전시험이다. FZP는 계속5초이며 이번 구성요소 예측만1초 적분한다.
3. 종전 관측기는 두 끝점 속도의 최댓값으로5초 이동거리를 제한했다. 구간 내 가감속과 연결부의 사용되지 않는 link 끝부분 때문에 정상 이동을 제외했다. 예를 들어74→10699→2는 본선 누적좌표에14.78m의 접속 차이가 있다. 동일 차량의 동일 link 전진 또는 단일한 인접 본선 연결이 확인된 이동에 한해 공간 경계 통과를 인정한다. 임의 점프·역행·차량 소멸은 여전히 제외한다.
4. 최초 추출은 `extraction_v1_endpoint_speed_guard/`에 보존했다. 재추출 후 다섯 자료의 관측 N·속도 CSV는 byte 단위 동일하다. 정상 내부 통과 유량만 복원했다. `extraction_verification.json`에77,810개 보존 검사와 남은 미확인 소멸, 실제 삭제를 따로 기록했다.

## 재현

기존 `extract_observations.py`에 `--phase-sec 0.1`, `--geometry-profile …/controller_response_v1/geometry_profile.json`, `--refined-geometry …/segment_resolution_20260921/geometry_200_branch_guard.json`을 지정해 각 완료 런을 별도 observations 폴더로 추출한다. `prepare.py`는100% 훈련 자료만 읽어 자유속도와 고정 프로토콜을 만든다.

```text
python -B test_fractional_observations.py
python -B calibrate.py --protocol res10_20260922/PROTOCOL.json --out res10_20260922/fit_v1 --max-evaluations 64
python -B res10_20260922/report.py fit_v1
```

실제 실행 cwd는 저장소이며 명령의 파일 경로에는 본 디렉터리까지의 상대 경로를 붙인다. 기존 결과를 덮어쓰지 않는다. source/config/훈련 입력/최종 parameter hash와 각 후보의 점수·실패 기록을 남긴다.1초 관측의 기존 동작과5초 fractional-clock·분기 통과·미래정보 차단에 대한5개 회귀검사가 통과했다.
