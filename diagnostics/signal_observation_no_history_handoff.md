신호 관측 OFF 회귀의 Git 이력 의존성을 제거했다. ON consumer는 `evaluation/controllers/signal_head_observation.py` 실제 import를 유지하며, VBS와 PowerShell 함수도 생산 파일에서 읽는다.

- 기준109afeef5da0fded77b6b68848d271a68743933e의 adapter를 한 번 조회해 `install_measured_movement_capacity` 메서드303행만 `fixtures/install_measured_movement_capacity_109afee.py`에 추출했다. 전체 adapter 사본은 없다.
- 같은 이름의 `.json`에 commit/source blob SHA/fixture SHA/정규화AST SHA를 pin했다. 테스트는 이 파일만 읽고 fixture/AST hash를 확인한다. `fixed_source_reference.source_at` 또는 Git을 호출하지 않는다.
- `check_signal_observation_no_history.py`는 Python subprocess audit hook으로 Git과 선언되지 않은 executable을 거부한다. 차단 자체도 사전 probe로 확인한 뒤 기존11개 검사를 실행한다.
- 최종 **11 tests PASS,1.172초**. CScript fakeCOM3개와 PowerShell config1개 subprocess만 실행했고, 실제 테스트의 Git 시도0·생산4파일 SHA변화0이다. 결과는 `signal_observation_no_history_validation.json`에 있다.
- 기본 sandbox에서는 CScript가 사용자WSH 설정을 읽지 못해 코드 실행 전에3개 실패했다. 승인된 동일 fakeCOM 검사만 격리 밖에서 다시 실행하여PASS했으며 실제VISSIM 생성·연결·실행은 없다.

fixture SHA는 `a49febf8d125445b99a84aaace982bddd90f3689ce6c9741576fbb82a960ba4a`, source blob SHA는 `a0afaa86e0b4d9885767c391ca88412fcabe321b142438de57e042547c201481`이다. 새 fixture `.py`는 root의 stage 시 `-text` 또는 `text eol=lf`로 pin해야 checkout에서 CRLF 변환에 따른 rawSHA 변화를 막을 수 있다. `.gitattributes`·생산 파일·활성 설정·manifest·index는 이 작업에서 수정하지 않았다.

재검증: `python -X utf8 -m diagnostics.check_signal_observation_no_history`.
