# 동측 본선 입력 ×0.8: native 실행 비교 감사

대상: 기준 `native9000_v1`와 후보 `east080_v1/native9000`. 후보는9000초 완료·exit0·런 소유 VISSIM 종료를 확인했다. 이번 검토에서는 LDP·LSA·완료 receipt만 읽었다. FZP·COM·새 런·소스/설정 변경은 없다.

**판정: 지정한 모든 신호의 기록 및 전환 시각이 기준 런과 정확히 일치한다.**

| 대상 | 비교 범위 | 후보 실제 상태/전환 | 기준과 차이 |
|---|---|---|---|
| SC9101–9108 / 각 SG1 | 1–9000초, 72,000개 SG 표본 | 전부 OFF. 각 LSA는 t=1 OFF1행, 이후 전환0회 | 0 |
| SC1001 / SG1–8 | 1–9000초, 72,000개 SG 표본 | LSA1,442행, 첫 표본 이후 전환1,440개 | 0 |
| SC1004 / SG1–8 | 1–9000초, 72,000개 SG 표본 | LSA1,442행, 첫 표본 이후 전환1,440개 | 0 |

각 LDP에 대해 SG 주소·고정폭·1–9000초 매초 연속성·유효 상태 문자를 기존 엄격 parser로 확인했다. 날짜/경로가 있는 헤더를 제외한 **LDP9000개 데이터 행은 SC별 바이트 단위로 동일**하다. 따라서 비교한 SG 상태뿐 아니라 각 native cycle clock도 동일하다. 각 런에서 LSA 이벤트 상태와 같은 시각 LDP 상태가 일치하고, 첫 표본 이후 전환 목록도 빠짐없이 일치한다.

추가로 전체 LSA의 정규화한 이벤트 필드 목록도 두 런에서 **51,326행 모두 동일**하다. 단순 신호별 총 녹색시간만 비교한 판정이 아니다.

기준 감사에서 SC1001/1004는 저장 SIG의 주기150초·program offset75초·controller offset0초와 일치했다. 후보의 전체 LDP 시계/상태 행이 기준과 동일하므로 같은 native 계획이 실행됐다. 두 SC의 SG1–8 녹색은 한150초당 각각24,45,23,46,24,45,23,46초이며, 황색은 각3초이다.

미터는 **native OFF**이며 COM으로 GREEN을 강제한 상태로 표현하지 않는다. 첫 관측은 첫 step 후t=1이고, 두 런 모두t=0의 독립 SG 관측은 없다. LSA 초기 상태의 한계도 같다: 미터 OFF와 도시 SG4/8 GREEN은t=1에 기록되지만 다른 도시 SG의 초기 RED는 LDP가 확인한다.

DSD·신호 자산·seed·네트워크의 동일성은 이미 완료한 준비 감사 범위이다. 이번 감사는 새로운 VSL readback을 추가하지 않았다. 동일한 seed와 신호 실행이 교통 결과까지 동일하다는 뜻은 아니다. 후보의 동측 입력은20% 감소했으므로 교통 효과는 별도 FZP 집계로 비교해야 한다.

## 재현 근거

LDP 데이터 행은 CR/LF를 제외하고 LF로 연결해 SHA256을 계산했다. 아래 해시는 기준과 후보에서 동일하다.

| SC | LDP 데이터 행 SHA256 |
|---|---|
| 1001 | `5b6d99dfaac7db9ae394f217ba5657be14c41f73a62b8d9a4236f74de0ec8f3f` |
| 1004 | `5b6d99dfaac7db9ae394f217ba5657be14c41f73a62b8d9a4236f74de0ec8f3f` |
| 9101 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |
| 9102 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |
| 9103 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |
| 9104 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |
| 9105 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |
| 9106 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |
| 9107 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |
| 9108 | `857a0ac5c60b4e8bdd0a59d5dd86ba95045263eed6078f2c0dca4c268765128d` |

원본 파일 SHA256(헤더의 날짜/경로는 런마다 다르므로 원본 파일 전체 해시는 서로 다를 수 있다):

- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\run.json`: `078ad11717ddc85b05edf3b842aaad38061b500faea29ed5f19a5ad859dd5fca` (5890 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_001.lsa`: `a296fb201d36240c26e7bb7374b3216258409a7bf6549e1d5e0e17656535266b` (4187203 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9101_001.ldp`: `0645e2a7e1ee32cf64cd2e08d994e388b7fba891a0b6c8bb005a471f97c5ddb3` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9102_001.ldp`: `53bea93a3f8834d6d93a103727db13aaf3fbdd34bf12aaeff9edc41a39b82e08` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9103_001.ldp`: `21451049a7d9c8e6a527c47856440e7ba1c62caeb72460b38afb3de7f7d9cd2b` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9104_001.ldp`: `19c238e09f011e537afa3dc39aaec3032bd2398a5d4aeb8a0658253214ae566c` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9105_001.ldp`: `f35d73abd0e9f1cdbe32102b2046b4192e1c2af4ab43ba434dcc558f95855bea` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9106_001.ldp`: `939dd557a28cfc2505f45cf9571d043808c6d7f84b1b5fea5f7400d594c70b54` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9107_001.ldp`: `1958fb8e9d23dcfbd3db26fde60aba9a937c63ba2134bcfb8790bc9421f2c1d0` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_9108_001.ldp`: `6ed5c6dd377af7b21f28e5d6d36d33e7efb546cf91dee2e487550cf2d54aca94` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_1001_001.ldp`: `2862cff2e84bfb89fd67bc5d82c07ae2f51e16c094a01488f6cced38839ecd06` (198756 bytes)
- `diagnostics\demand_sweep\user_native_20260914\native9000_v1\vissim_eval\baseline_1004_001.ldp`: `6f3bdc7cf4c31f56b61c5d5a5dccfb03c51a7cb0234b1836536fe3e877013d35` (198756 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\run.json`: `a292c6d61ab3d1fc71c826d13447d76d5a9876bd3dba9feb80c5b074b1a73a09` (5935 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_001.lsa`: `ef0e305e2d8ec5e1df0c0cf902129ef8e898fec324deefca3eaef1fe31b2fb37` (4187211 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9101_001.ldp`: `468c481d326093ca1fd58ba4170ec9ab873e3049c33a8d54a1878d7d7d7098cf` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9102_001.ldp`: `56da62414b3e55187610634c245133d71e5c03f6fa4abeaae19282ec7263846c` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9103_001.ldp`: `b1a64a9039687dca5e2ac7abff1348eb360f378858594ea449c96606c148af76` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9104_001.ldp`: `2d341d5e06c0a044baea4c6e5db9e8e66c2120276d1ad89c51240a0e0997db87` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9105_001.ldp`: `13641f3fbc52be0d6dd308fd4fd6c22bc4558d6c1b233e68436ecacf9b639d7e` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9106_001.ldp`: `7970ab93e38b6253458ae9f6d04c7b94bfe50a354b0080264f6b45b02c60c310` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9107_001.ldp`: `0dc73dba554ea95b35ef90f94e79202b19d49c99e839ebfb8e996fa9b5860a37` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_9108_001.ldp`: `03e35948a0c6619ac52b6912312d23d3cc9d35604ebb0cf0a0b1830b9b431917` (135514 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_1001_001.ldp`: `1f5ee6e22a3827d4c6b7f5aaa633b31b9edf2bd6c2549803b7dc6550e960d495` (198764 bytes)
- `diagnostics\demand_sweep\user_native_20260914\east080_v1\native9000\vissim_eval\baseline_1004_001.ldp`: `3e9498eb86150fedc912082364b6bfce619a1ac6d7e30acf247ac9e88888bb1c` (198764 bytes)
