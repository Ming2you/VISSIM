# 셀24·25 실측 속도 조건부 진단

2026-09-30. 완료: baseline parity1회 + seed67 RM 완화±VSL90의450초 조건부2회. **자율 예측 또는 이득 검증 통과가 아니다.**

실제 미래 source·합류와 셀24·25 속도를 알려주는 원인 분리용 계산이다. N·경로 재고·동적 off-ramp 저장은 바꾸지 않았다. 실제 VSL로 셀18 방출이39대 늘었지만 모델의 변화는 기존−6.79대에서−17.43대로 악화했다. 회복부 속도만 맞추면 VSL 이득이 복원된다는 가설을 지지하지 않는다.

해석과 전체 표는 [본선 최초 오차 및 회복 진단](../first_recovery_divergence/README.md)에 있다. `protocol.json`, `summary.json`, `*_speed_injections.json`, `verification.json` 및 `helper_executed.txt`가 실행 근거다. 새 VISSIM/FZP 읽기/보정/push 없음. 목표 ACTIVE / NOT_QUALIFIED.
