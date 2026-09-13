# V3 완료 53개 결정 기록 감사

대상은 `codex_fid_cl9000_s13_v3`의 900–8700초 완료 결정 53개다. 다른 런과 seed를 섞지 않았다.

선택된 명령의 450초 예측 Ω TTT는 저장돼 있다. 같은 상태에서 직전 명령을 유지했을 때의 Ω TTT는 보존된 hold validation·progress·action에 없어 전후 이득은 모든 행에서 null이다. 기록된 owner `from_cost/to_cost/gap`은 고정 가격을 포함한 개별 payoff이며 Ω TTT 차이로 사용하지 않았다. 450초 예측창은 겹치므로 합계도 실제 TTT 절감량이 아니다.

- 매 결정의 ranking 후보 수: {'1': 53}; 선택 NP: {'2400.0': 53}; 선택 meter bank: {'0': 53}.
- 시도 후보 상태: {'feasible_final_response': 53, 'restoration_budget_stop': 106}. 복원 중단 사유: {'evaluation_budget': 106}. 후보 가능성 unknown을 불가능 증명으로 바꾸지 않았다.
- 선택 응답의 owner 방문 수: {'19': 53}; 최종 gap 완료 owner 수: {'0': 53}. 최적성 인증은 없다.
- 실제 작성 CSV의 VSL 값: [120.0] km/h; 미터 녹색: [10.0]초. 900초 이후 52회 비교에서 green 36회, offset 35회 변경됐다.
- 전체 계산 시간 min/median/max: {'min': 235.93591869997908, 'median': 255.19791990000522, 'max': 273.7569187999907}. 명령 파일 결합 기록은 {'True': 53}; native 상태는 {'pending': 53}로 완료 native 인증이 아니다.

| 결정초 | 선택 Ω TTT [veh·h] | 유지 Ω TTT / 이득 | 채택 owner | 개별 payoff 감소 (Ω 아님) | NP 실제/상한 | 최종 gap | 전체 계산초 |
|---:|---:|---|---|---:|---:|---|---:|
| 900 | 187.182562001 | missing / null | SC1004 | 0.793456680 | 308.290288/2400 | 0/19, null | 255.198 |
| 2400 | 325.829738317 | missing / null | SC6 | 0.248608313 | 316.147462/2400 | 0/19, null | 266.587 |
| 3150 | 367.449277687 | missing / null | SC1002 | 0.093654060 | 302.055470/2400 | 0/19, null | 259.847 |
| 4500 | 300.165167195 | missing / null | SC109 | 0.184392584 | 223.755735/2400 | 0/19, null | 254.274 |
| 6300 | 169.086591082 | missing / null | SC1 | 0.154536155 | 204.627783/2400 | 0/19, null | 243.602 |

정확한 필드 경로는 JSON의 `field_evidence`, 시각별 값·후보 인덱스·복원 제약은 `decisions`, 원본 SHA는 `source_files`에 있다. CSV는 53개 결정의 작은 표다.

이 기록이 직접 입증하는 것은 좁은 관측 후보 선택과 미완료 최종 gap이다. 전체 실제 TTT의 0.57% 개선이 작은 원인을 이 자료만으로 특정하거나, 예측 Ω TTT도 좋아졌다고 단정하지 않는다.

재현: 저장소 루트에서 `python -B diagnostics/performance_diagnosis_20260913/audit_decisions.py --output-prefix diagnostics/performance_diagnosis_20260913/recheck/decision_audit`. 원본 런의 위 작은 JSON/CSV/JSONL 파일이 필요하며 기존 결과는 덮어쓰지 않는다.
