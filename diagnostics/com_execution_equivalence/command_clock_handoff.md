# 명령표와 실제 실행 시각의 독립 대조

`command_clock.py`는 기존 `live_beta0_first_interval_audit.expected_signal/expected_ramp`와 `signal_timing_oracle.decisions_from_action_rows`를 재사용한다. 새 runner나 모델은 없다. 저수준 `intended_state`만 호출하면 빠지는 **동일 SC의 다른 SG가 GREEN일 때 AMBER를 RED로 억제하는 정본 규칙**도 기존 helper를 통해 유지한다.

연결 API:

```python
caps = native_options(pinned_vbs_text, pinned_generated_config_text)
clock = CommandClock({sec: ordered_command_rows, ...}, pinned_sc_sg_window_counts, caps)
clock.check_signal(actual_signal_readback_row)
clock.check_vsl(actual_vsl_readback_row)
```

caller는 완료 receipt/source/입력 pin을 먼저 검증하고 기존 readback loop에서 각 checker를 호출한다. VBS/config는 해당 provenance SHA와 일치하는 텍스트를 제공해야 한다. `native_options`는 기존 10초 미터 주기·1초 미터 황색·3초 도시 황색을 확인하며 다른 상수는 조용히 해석하지 않는다. 물리 미터 용량은 고정 숫자를 새로 만들지 않고 pinned config의 SC/용량 목록에서 읽는다.

**이 API는 primary 1초 stepwise pair용이다.** post_step(t)은 새 쓰기 전이므로 t−1 시각의 최신 명령·offset·창을 적용하고, immediate(t)는 t 시각의 최신 명령을 적용한다. event-continuous의 긴 callback 간격에는 이 계산을 그대로 사용하면 안 된다. 전체 cadence·초기/종료·변경 후 첫 post_step·제어경계 누락 검사는 Hubble의 기존 verifier가 계속 담당한다.

checker는 requested==actual에 더해 두 값 모두 해당 명령 clock과 일치해야 통과시킨다. 도시의 zero-window SG는 pinned 예상 집합에 속하면서 CSV 창 수가 0일 때만 RED이다. 빠진 양수 창을 RED라고 추정하지 않는다. 미터는 CSV의 실제 green_sec를 10초 clock에 적용하며 rate/capacity→green의 기존 double 연산 순서·half-even Round 관계를 검사한다. VSL은 모든 허용 값 중 하나인지에 그치지 않고 **해당 (DSD, 적용 시각)의 CSV 값**과 requested/actual distribution No가 일치해야 한다. 각 차종의 순차적 setter 직후 reference readback이며 차량 속도 측정이 아니다.

`test_command_clock.py`의 합성 10개 검사 PASS(0.002초 unittest body): pre/post·새 offset 경계, AMBER 억제와 정상 AMBER, RED-only, 미터 green/AMBER/RED와 양자화 거부, requested==actual이나 해당 시각 CSV 값이 다른 VSL 거부, 양수 SG 창 누락 거부, native 상수 변경 거부, 입력 불변. 실제 run 파일·FZP·COM·controller model 실행은 없다. `verify_pair.py`는 본 작업에서 편집하지 않았으며 Hubble이 실제 필수 checker 연결과 통합 fixture를 담당한다.
