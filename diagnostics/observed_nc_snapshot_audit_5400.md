# 완료된 새 무제어 스냅샷의 투영·동일성 검사

900~5400초의 완료된 8개 anchor 중 8개가 active beta0 error config의 실제 configure_runtime 및 투영을 통과했다. Endpoint나 optimizer는 실행하지 않았다. 생산·입력 파일 hash 변화: 0개.

| 시각 | 모든physical/route records | Ω raw=model | held unknown | 미지원양수 | 일반transit지원 대수(link수) | route corridor지원 대수(link수) |
|---:|---:|---:|---:|---:|---:|---:|
| 900 | 2591 | 1763 | 0 | 0 | 50 (11) | 18 (6) |
| 1500 | 4086 | 2841 | 0 | 0 | 91 (10) | 32 (7) |
| 1800 | 4581 | 3240 | 0 | 0 | 84 (13) | 26 (7) |
| 2100 | 5137 | 3681 | 0 | 0 | 92 (11) | 30 (8) |
| 2700 | 6243 | 4579 | 0 | 0 | 88 (10) | 23 (7) |
| 3600 | 6702 | 5050 | 0 | 0 | 68 (14) | 29 (8) |
| 4500 | 6265 | 4885 | 0 | 0 | 63 (11) | 21 (6) |
| 5400 | 5664 | 4667 | 0 | 0 | 48 (8) | 19 (7) |

지원 분류는 projection provenance의 처리 경로이며 전체 Ω재고를 서로 배타적으로 분할한 표가 아니다. CSV에는 각 link별 원 관측 대수, target storage, 실제 assignment를 보존했다. 순간 관측 0을 미래 native demand 0으로 해석하지 않는다.

900초는원본 `codex_nc_s13_6056c94_20260909_retry`의fullraw와차량별비교했다.2591개ID집합,link,lane,position,speed,stopped가전부정확히같다. 최대위치/속도차이는0이다. 다른nativequalifierrun은비교에사용하지않았다.

원본 NC CSV와 비교한 anchor별 차이 수: 0. 매 anchor에서 FW 42셀과 모든 양수 physical link를 대조했다. 평균속도는 CSV 6자리 정밀도로 비교한다.

900초 외에는 원본 full raw가 없어 이 producer만으로 개별 ID 궤적 동치를 주장하지 않는다. 전체 5400초 FZP·지표 비교는 별도 완료 런 감사다. 초기 투영 성공은 예측모형 fidelity나 native input 전수 모형화를 증명하지 않는다.

재현: `python -X utf8 -m diagnostics.audit_observed_nc_snapshots --max-anchor 5400 --output observed_nc_snapshot_audit_5400`. 상세JSON과지원link표CSV는동명파일이다.
