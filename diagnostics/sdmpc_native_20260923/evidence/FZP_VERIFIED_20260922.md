# fzp 4조건 무결성 검증 (완료)

검증 도구: D:\VISSIM-merge\tools\verify_fzp.py
기대값   : D:\VISSIM-merge\tools\expected_fzp.json (00abbab 의 fzp_evidence.json 에서 추출)
해시 규약: diagnostics/control_comparison_20260922/compare.py:raw_frames 와 동일
           sha256 = 파일 전체 바이트 / prefix_before900_sha256 = t<900 행들

| 조건 | 크기 | 전체 SHA-256 | 행수 | 프레임 | 마지막 | 판정 |
|---|---|---|---|---|---|---|
| none | 1.08GB | 0ef096c864df2412… | 6,834,855 | 1799 | 8995.1 | VERIFIED |
| rm   | 1.08GB | 0ed2e3b0c95b18f6… | 6,788,080 | 1799 | 8995.1 | VERIFIED |
| vsl  | 1.11GB | 91eb334a7b9dfce3… | 6,977,185 | 1799 | 8995.1 | VERIFIED |
| both | 1.12GB | 49d2625a9606bc26… | 7,035,177 | 1799 | 8995.1 | VERIFIED |

5개 항목(전체해시·제어전 prefix·행수·프레임·마지막시각) 전부 일치. 다른 PC 에서 plant
분석에 쓰인 바로 그 파일이다.

## 파생 사실 1 — 짝지음 전제가 실측으로 증명됨

네 조건의 prefix_before900_sha256 이 **완전히 동일**하다:
  e7cf918832b30d5386ace9532610c6071a6b61f062215e449afa780ec9c9c70a

같은 시드(23)면 제어가 갈라지는 900 초까지 VISSIM 이 비트 단위로 같게 재생된다.
5 단계 짝지은 분기 실험의 전제가 가정이 아니라 증거 위에 선다. 스냅샷이 없어도
워밍업을 재계산하면 동일 상태가 나온다는 뜻이기도 하다.

## 파생 사실 2 — VISSIM 2020 에 스냅샷 기능이 없다 (probe 로 확인)

  Vissim COM 메서드      : LoadNet/LoadLayout/LoadProject/SaveNet/SaveNetAs/SaveLayout 뿐
  Simulation 메서드      : RunContinuous / RunSingleStep / Stop 뿐
  Simulation.AttValue    : Snapshot* / UseSnapshot / Save|LoadSnapshot 후보 10개 전부 없음
  설치 디렉토리          : *snapshot* / *.snp 0 건

대신 쓸 수 있는 것: Simulation.AttValue("SimBreakAt") — 지정 시각에 RunContinuous 정지.
확인된 런 설정: RandSeed=23, SimPeriod=9001, SimRes=10. 망 로드 31.6 초.

## 런 비용 기준선

native_queue_status.json: 큐 15:16:14 시작 → 17:24:07 종료 = 2h08m / 9000 초 런 3 개
(NC 는 재사용). 즉 **9000 초 런 1 개 ≈ 43 분**. 900 초 워밍업 ≈ 4.3 분, 450 초 분기 ≈ 2.2 분.

## 파일 위치

  none : D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\run\vissim_eval\baseline_001.fzp
  rm   : D:\VISSIM_runs\20260922_fw080_urban090_controls\rm\run\vissim_eval\baseline_001.fzp
  vsl  : (동일 구조) vsl\run\vissim_eval\baseline_001.fzp
  both : (동일 구조) both\run\vissim_eval\baseline_001.fzp
  → compare.py 의 RUNS 경로 규약과 정확히 일치. 수정 없이 바로 돌릴 수 있다.
