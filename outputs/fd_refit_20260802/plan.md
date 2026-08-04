# FD 재적합과 캘리브레이션 갱신 (2026-08-02)

## 왜

택시(class 70) VSL 편입으로 플랜트 거동이 바뀌었고 freeway 본선 체인이 정본화(8×1.3466 km)됐다.
구 FD 값(캘리브레이션 파일 100/24/7600, 컨트롤러 실효 120/30/6900)은 모두 무효다.

## 무엇

1. `evaluation/runs/no_control_fd_refit_20260801/` 의 두 수요 스케일(1.35 / 1.70) 런에서 FD 점군 추출
   → 검증: `length_km` FW_E 1.346639 / FW_W 1.347212, `lanes` 4
2. `scripts/fit_freeway_fd_20260801.py` 로 v_free / rho_crit / a / capacity 적합 (binned 평균 회귀)
   → 검증: 식별성 판정(`capacity_bin_is_interior_max`) 확인 후 fit key 채택
3. 정합성 검사 — v_free vs VSL 메뉴 [80,100,120] / 앵커 120. **결정 보류, 방안만 제시**
4. `scripts/build_fd_refit_calibration_20260801.py` 로 캘리브레이션 v2 + leaf tuning 생성
   → 검증: 어댑터 경로로 4조합 로드해 컨트롤러가 보는 network 확인
5. `outputs/vsl_sensitivity_20260801.md` 에 §10 추가(구 수치 보존)
   → 검증: 구 파라미터·구 점군으로 36.4 / +35.1, 25.84 / 92.7 % 재현
6. 회귀 테스트 2종 → 검증: 14/14, 4/4 PASS

## 손대지 않는 것

- `evaluation/calibration/real_world_modi_control_v0_20260719.json`
- `outputs/no_control_fd_mfd_20260724_*`
- 부모 tuning `real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json` (zone4 등이 상속)
- VSL 메뉴·앵커 (결정 보류 대상)
