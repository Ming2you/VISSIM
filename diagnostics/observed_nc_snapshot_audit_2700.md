# 완료된 새 무제어 스냅샷의 투영·동일성 검사

900~2700초의 완료된5개 anchor가 모두 active beta0 error config의 실제 configure_runtime 및 투영을 통과했다. Endpoint나 optimizer는 실행하지 않았다. 모든초기 Ω재고가 원 physical records와 같고, 경로보류·양수미지원link·초기entry/TD/event가0이다. 읽은 생산/입력 파일의 전후hash도변화없다.

| 시각 | 모든physical/route records | Ω raw=model | held unknown | 미지원양수 | 일반transit지원 대수(link수) | route corridor지원 대수(link수) |
|---:|---:|---:|---:|---:|---:|---:|
| 900 | 2591 | 1763 | 0 | 0 | 50 (11) | 18 (6) |
| 1500 | 4086 | 2841 | 0 | 0 | 91 (10) | 32 (7) |
| 1800 | 4581 | 3240 | 0 | 0 | 84 (13) | 26 (7) |
| 2100 | 5137 | 3681 | 0 | 0 | 92 (11) | 30 (8) |
| 2700 | 6243 | 4579 | 0 | 0 | 88 (10) | 23 (7) |

지원분류는 projection provenance의 처리경로이며 전체 Ω재고를 서로배타적으로 분할한표가 아니다. CSV에는각link별원관측대수,targetstorage,실제assignment를모두보존했다. 이5개anchor에서native1091 source236/10381 관측은0이지만, 해당모듈은구성되어있다. 순간관측0을미래native demand0으로해석하지않는다.

900초는원본 `codex_nc_s13_6056c94_20260909_retry`의fullraw와차량별비교했다.2591개ID집합,link,lane,position,speed,stopped가전부정확히같다. 최대위치/속도차이는0이다. 다른nativequalifierrun은비교에사용하지않았다.

같은원본NC의이미완료된기본CSV와비교한5개anchor의기본물리수치차이는0이다. 매anchor의42개FW segment와288~354개physical link행도대수/정지대수/평균속도가일치한다(평균속도는CSV6자리정밀도로비교). 원본에없는새양수link도없으며,원본link행대수합은새전체차량수와같다.

이는완료anchor들의관측이같다는근거다.900초외에는원본fullraw가없어개별ID궤적동치를주장하지않는다. 실행중새CSV/FZP는읽지않았으며,전체5400초성능지표와trajectory동치는baseline완료후별도검증해야한다. 초기투영성공이예측모형fidelity나nativeinput전수모형화를증명하지도않는다.

재현: `python -X utf8 -m diagnostics.audit_observed_nc_snapshots --max-anchor 2700 --output observed_nc_snapshot_audit_2700`. 상세JSON과지원link표CSV는동명파일이다.
