# V3 중단 구간 native 신호 검사

대상 `codex_fid_cl9000_s13_v3`: 원본 요청 종료9000초, 관측 검사1–8850초, 실제 마지막 명령8700초.

- LDP prefix 상태/명령 시계 일치: **False**. 검사 sample None, mismatch None.
- 실제 VSL 적용 readback: **True**; 15576행 / 예상 15576행. 66 DSD ×4차종 ×59개 실제 명령 시각만 검사했다. 매초 검사를 추가하지 않았다.
- 전체9000초 완료·전체 native 실행·process 종료 인증은 모두 false다. 원본 provenance의 SimPeriod·state·receipt를 변경하거나8850초 명령을 만들지 않았다.
- LDP8850초는 기존 t−1 명령 시계로8849초에 유지 중인8700초 명령을 검증한다. 도시 제어 이전 native 상태는 기록 범위 확인만 하며 임의의 제어 기대값과 비교하지 않는다.
- LSA 파일 존재와 COM 전환 coverage는 다르다. LSA coverage는 미평가/미인증으로 남기며 LDP 통과로 결측을 채우지 않았다. 별도의 신호 first/changed immediate readback 검사는 이 결과에 포함하지 않는다.
- LDP 원본의 완전한 고정폭 행 마지막 시각 분포: {8742: 15, 8741: 10}. 불완전한 행을 자르거나 만들어 parser를 통과시키지 않았다.
- 분석 소요 0.950초. 실패 stage: native_ldp_prefix. 모든 실패 상세·원본 SHA는 JSON에 보존했다.

재현: `python -B diagnostics/performance_diagnosis_20260913/audit_native_signal_prefix.py --output-prefix diagnostics/performance_diagnosis_20260913/recheck/native_signal_prefix`.
원본 런의 LDP·명령 CSV·VSL readback 및 provenance에 지정된 원본 파일이 필요하다. 기존 출력은 덮어쓰지 않는다.
