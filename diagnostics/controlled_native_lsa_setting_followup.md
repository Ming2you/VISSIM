# COM 신호의 native 기록 설정 재확인

**COM 소유 SigState의 전환과 적용 후 초기 상태를 native LSA에 포함한다고 보장하는 설정은 찾지 못했다. Native-only 검증은 여전히 미해결이다.** 기존 완료 런에서 실제 readback 전환은 도시 348회·미터 88회인데, 해당 144개 SG의 900초 이후 LSA 전환은 0회였다. 미터의 1초 LSA는 OFF이고 같은 시각 실제 적용 후 readback은 GREEN이다. 이번에는 보존된 audit JSON만 재사용했으며 원 LSA나 실행 중 자료는 다시 읽지 않았다.

설치된 `PTV Vissim 2020/Doc/Eng/attribute.xlsx`의 SHA는 `139705be4bac9ac41e88c9c201a8704fb37f0631834dd49d546f57aa37e8c57e`다.

| 속성·행 | 확인한 범위 |
|---|---|
| `SignalGroup.SigState` / `ContrByCOM`, 528/530 | SigState 쓰기는 COM 소유를 켜고 정상 신호 제어를 무시한다. COM 소유를 끄면 실제 제어가 바뀌므로 기록 수선 옵션으로 사용할 수 없다. |
| `Evaluation.SigChangesWriteFile` / `SigChangesWriteDatabase`, 2302/2301 | 파일·DB 출력 선택이다. 현재 VBS `ConfigureEvaluationOutput`은 이미 파일 출력을 켠다. DB로 바꾸면 COM 전환이 생긴다는 근거는 없다. |
| `Evaluation.SCDetRecWriteFile`, 2300 | 별도의 detector protocol 출력이다. COM 상태 포함 보장은 없다. |
| `SignalController.SCDetRecShortNam` / `LabelDet` / `LabelSG`, 512–514 | 이름·라벨 설정이다. 기록하는 상태의 출처를 바꾸는 설정이 아니다. |
| `SignalHead.SigState` / `DischRecAct`, 553/557 | 실제 head 상태 읽기와 차량 방출 평가다. 전 SG의 초기 상태·전환을 기록하는 스위치가 아니다. |

[2020 LSA 문서](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/11_Auswertungen/AuswertungLSAUmschaltungen.htm)는 일반적인 신호 변경별 행과 출력 매체를 설명하지만 COM 직접 쓰기 및 적용 후 초기 상태는 별도로 보장하지 않는다. [2020 신호 시간표 문서](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/11_Auswertungen/AuswertungSignalzeitenplan.htm)는 화면 표시 기능이므로 현장 누락을 해결한 파일 출력 증거가 아니다.

[2025 LDP 문서](https://cgi.ptvgroup.com/vision-help/VISSIM_2025_ENG/Content/11_Auswertungen/AuswertungLSADetektorProtokoll.htm)는 외부 제어절차의 내부 값과 검출기 값을 기록한다고 설명한다. 이를 2020의 COM-owned SigState 대체 기록으로 해석할 수 없다. 2020 해당 웹페이지와 온라인 COM 속성 페이지는 이번 조회에서 가져오지 못했고, 설치 CHM 전체도 검토하지 않았다.

`ContrByCOM` 계약은 정상 제어와 직접 COM 제어가 분리된다는 근거다. **LSA 내부 구현이 어느 경로만 기록하는지까지 확정하는 근거는 아니다.** 다른 API나 서비스팩의 해결 가능성을 배제하지 않으며, 확인하지 않은 설정을 켜면 해결된다고 제안하지 않는다.

현재 가능한 작은 증빙은 실제 초기·인계 readback, 변경 쓰기 직후 readback, 다음 실제 step 및 경계 확인을 유지하는 것이다. 드문 관측으로 중간 매초 상태까지 증명할 수 없으며, 명령 CSV나 요청값으로 native 누락을 채워 PASS 처리하면 안 된다. 생산·설정 변경, COM·모델 실행, FZP·LSA 접근은 없었다.

속성 행과 기존 증거 SHA는 `controlled_native_lsa_setting_followup.json`에 보존했다.
