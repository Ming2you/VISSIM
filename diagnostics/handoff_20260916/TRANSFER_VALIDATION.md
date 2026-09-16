# 2026-09-16 자료 이식 검증

2026-09-16에 Git index의 전체 파일을 원래 worktree와 다른 폴더로 내보내 검증했다. 새 VISSIM 런은 시작하지 않았다.

- 직접 보관한 파일 128개: checkout 후 크기·SHA-256 전부 일치. 아래 최종 문서 갱신 후 해당 직접 파일 manifest를 다시 계산했다.
- 분할 묶음: 약 192.99 MiB, 5개 파일(최대 48 MiB). 1,141개 고유 객체에서 2,255개 파일을 복원했고, 누락 0개 및 모든 파일의 SHA-256 일치.
- 임시 패키지 복원 검사 8개와 geometry profile 경로 이식 검사 10개 PASS.
- 복원 자료로 `evaluate_native_response.py --ramp-local-step-sec 1`을 실행해 16개 예측 창을 완료했다. Python 3.12.14와 기존 NumPy 2.5.3 설치를 사용했다. 원시 FZP는 사용하지 않았다.
- 기존 `native_response_v2`와 `predictions.json` 전체 및 `response.json.records` 전체가 정확히 일치했다. 수치 허용오차나 반올림을 사용하지 않았다.
- `windows.json` 전체와 response assumptions도 서비스 표 파일의 머신 경로만 저장소 상대 경로로 정규화한 뒤 정확히 일치했다. schema·ramp_local_step_sec·fitted_against_native_treatments·metric_scope·warnings도 일치했다.
- 새 경로와 live harness의 경로 이식 수정 때문에 source provenance와 새 frozen ZIP 해시는 과거와 다르다. 과거 ZIP·실행 결과는 그대로 보존했다. 수치 필드는 비교에서 제외하지 않았다.

JSON을 `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=False`, `allow_nan=False`로 직렬화한 비교용 SHA-256:

| 범위 | 이전 결과 = 복원 후 재실행 |
|---|---|
| predictions 전체 | `cb094fcb70d6b34ce4a1296059c0770d08e0db271089069cf4b908cc9b2a1fd9` |
| response.records 전체 | `840ff26e9f477f2ed7cef061696ea2bcc818258304edc96158e02cda6948fe57` |
| windows 전체(경로 정규화) | `6f17bafa38acc62b1fd68dd7d6f615ee9341a225a4dd4500797b90224e43618d` |

이 검사는 전달 파일의 무결성과 모델 재현성을 확인한다. 모델이 실제 교통을 정확히 예측한다는 뜻은 아니며, full GNE·새 VISSIM 실행·별도 seed 성능을 새로 검증한 것도 아니다. 주요 예측 오차와 native 삭제·미삽입은 최신 인계 문서에 남겼다.
