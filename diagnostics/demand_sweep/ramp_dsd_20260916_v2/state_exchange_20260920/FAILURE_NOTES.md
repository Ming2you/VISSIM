# 보존한 준비 실패와 판정

- `observations_v1/`: 최초 추출기가 셀 길이 키를 `length_m`로 가정해 즉시 중단됐다. 실제 schema의 `length_km`를 읽도록 수정했고, 성공 자료는 `observations_v2/`다. 기존 관측·결과는 수정하지 않았다.
- 최초 fitting import: 이 Python 환경에 SciPy가 없어 실행 전에 중단됐다. 추가 설치 없이 주소별 절편을 해석적으로 제거한4변수 Poisson Newton 계산으로 바꿨다. `fit_v1/model.json`에 수렴 gradient와 반복 수가 있다.
- 최초 새 단위 검사: 구현 전 `StateDependentExchange` import 실패를 확인했다. 구현 후 검사를 통과했다. 이는 native 실패나 성능 표본이 아니다.
- `qualification_v1/`: 수치 보존과 과거 결과 재현은 통과했지만, 상태 기반 차로 이동률만으로 이득 예측은 통과하지 못했다. 성능 실패를 준비 오류와 구분한다. 기본 config에 적용하지 않았다.
- `dispersion_spatial_v1/`: 최초 셀별 비용 합산이 원래 link 기반 비용과 일치하지 않아 assertion으로 중단했다. 입력link74의 음수 위치 차량이 `Observer.locate()`에서 제외되는 것이 원인이었다. 최종 `dispersion_spatial_v2/`는 이를 별도 `unlocated_mainline` 항목에 보존해 기존 합계와 정확히 일치한다. 기존 TTT 수치를 바꾸거나 음수 위치를 임의의 셀로 재배치하지 않았다.
