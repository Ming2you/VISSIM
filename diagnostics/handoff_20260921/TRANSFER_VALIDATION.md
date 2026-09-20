# 전달 검증

- 실제 파일의 main guard로170개 단위 검사 PASS(`test_output.log`). 첫 stdin 호출의 Windows spawn 실패는 별도 로그로 보존했다.
- 완료된 기준4예측 전체 JSON exact, 새 후보8예측의 서측 cell/flow/port/ramp exact, 구성 비용 차이 재합산 PASS.
- 속도분포10,800개 셀·시간 단계 차량 보존 및 가능한 분포 PASS. 이는 예측 정확도 통과를 의미하지 않는다.
- 현재 core4파일 SHA는 마지막 실험 기록과 일치한다(`latest_records_validation.json`).
- 분할 archive의 조각 SHA256, 전체 고유 object의 길이·SHA256, manifest 참조를 `verify_archive.py`로 검사한다. 9개 조각·3,598개 고유 object·5,612개 증거 경로를 모두 통과했다(`archive_validation.json`).
- 이번 전달에서 새 VISSIM 및 새450초 예측0회. 대형 원시 native 출력은 제외하고 위치·크기를 명시했다.
- 다른 머신의 VISSIM 설치·라이선스·COM 연결은 이번 검사 범위가 아니다. 새 기하 full GNE와 RM/VSL 순이득 보정도 미완료다.
