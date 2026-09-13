# 6300초 실패 archive 보존 점검

대상: `evaluation/runs/codex_fid_cl9000_s13_v2` → `attempt_01`. 기존 작은 산출물/결정 파일과 native ERR만 읽고 SHA-256으로 비교했다. FZP·LSA·LDP를 읽거나 hash하지 않았고 모델·native 실행 및 receipt/원본 수정은 없다.

- 기본 출력 6/6개 byte/SHA 동일: state CSV, action CSV, bottleneck links/segments CSV, runlog, runlog ERR.
- 결정 트리 280/280개, 114,199,061 bytes 전체 byte/SHA 동일. 누락 0개, 불일치 0개, archive 추가 파일 0개.
- 마지막 완료 6150초의 action JSON/CSV·budget·joint·joint-written·progress 및 state가 보존됐다. 실패 6300초의 state와 partial joint도 양쪽에 동일하게 남는다. 6300초 action JSON/CSV가 양쪽 모두 없는 것은 복사 누락의 증거가 아니다.

| native 원본 → archive 이름 | bytes | SHA-256 |
|---|---:|---|
| `baseline.err` → `vissim_network.err` | 2,862 | `2f5bcd5fdd852c18eb0eb7369fb7408031453310e98e0955b3f73695f3aeec14` |
| `baseline_001.err` → `vissim_simulation_001.err` | 180,968 | `173fcb77328d5a9da572c5a98732b9c31c1725269f452e3ec32d11df32c05958` |

원본 native ERR 디렉터리: `diagnostics/selected_control_demand/codex_fid_cl9000_s13_v2/native_recording`. 두 ERR 모두 archive와 정확히 같아 이 비교 시점의 복사 누락·잘림은 발견하지 못했다.

`Archive-AttemptOutputs`는 실패 시 기본 6개 + `decisions` + native ERR를 attempt 디렉터리에 보존한다(정본 watchdog 624–643행). root ERR는 성공 경로에서 복사되므로 실패 completion의 `Archived numbered native ERR missing` 및 `error_files=[]`는 root 위치 검사와 구분해야 한다. 이 메모는 failed completion을 성공으로 재분류하지 않으며 receipt를 수정하지 않았다. completion/provenance/wrapper/progress가 attempt에 없는 것도 이 함수의 복사 대상 누락이 아니다; 해당 원본은 run 루트에 남아 있다.

차량 12602의 이번 retry native ERR 명시 기록:

- `baseline_001.err:398`: `Warning	Simulation second 3180.0: Vehicle 12602 (on Static Vehicle Route 1130 - 3) arrived at the end of link 2 without having found the next link (10682) of its route.	Network object type: Vehicle	Network object keys: 12602`

이 기록이 있더라도 이전 실패런의 동명 ID와 native 운명을 무조건 동일시하지 않으며, 별도 궤적 없이 정확한 경로 이탈 원인·최종 도착·제거 여부를 확정하지 않는다.

결정 트리 정렬 manifest(relative path, bytes, SHA-256)의 SHA-256: `b2cc1197a2f444fc01f732ee37decca3d6c89ee4bdc46cc6bf835106a9020908`. 기본 출력 manifest SHA-256: `b4508d412cdf03b66189bafdb5677fdee1e1d43c712b9f06531a903a7bafb0ce`.
