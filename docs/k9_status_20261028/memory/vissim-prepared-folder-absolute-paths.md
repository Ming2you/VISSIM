---
name: vissim-prepared-folder-absolute-paths
description: 다른 PC에서 가져온 prepared 폴더는 rule_runtime.txt 에 그 PC 절대경로가 박혀 있어 제어 시작 시각에 죽는다
metadata: 
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-22T14:29:10.785Z
---

VISSIM `prepared/` 폴더를 다른 워크스테이션에서 복사해 오면 `rule_runtime.txt` 안에
**원래 PC의 절대경로**가 그대로 들어 있다. 파일은 UTF-16LE + BOM, 3줄이다:

```
<python.exe 절대경로>
<fast_fixed_profile.py 절대경로>
<control start sec>
```

증상: `none`(무제어) 팔은 완주하는데 `rm`/`vsl`/`both` 팔만 **제어 시작 시각에 정확히**
죽는다. 예: ControlStartSec=900 이면 FZP 가 SIMSEC 895.10 에서 멈춘다.

```
stdout: STAGE=RUN_CONTINUOUS_BEGIN / SIM_SEC=900
stderr: fast_nc_runner.vbs(421, 9) 지정된 파일을 찾을 수 없습니다.
```

421 줄은 `shell.Run(command,0,True)` 로, 그 시점에 python 을 불러 규칙 제어를 계산한다
(`RunRuleProfile`, VBS 386-389 가 `rule_runtime.txt` 에서 python·helper 를 읽는다).
무제어 팔은 이 경로를 아예 안 타므로 멀쩡하다. 그래서 "한쪽만 죽는다" 로 보인다.

고치는 법: 세 줄 중 앞 두 줄을 현재 PC 경로로 바꿔 쓴다. **UTF-16LE + BOM 을 유지**해야
한다(VBS 가 `OpenTextFile(...,-1)` 로 유니코드로 연다). 실행 중인 런도 제어 시작 전에
고치면 살릴 수 있다. VBS 가 이 파일을 제어 시작 시점에 읽기 때문이다.
`prepared.json` 의 해시 핀은 기동 시점에 이미 통과했으므로 재검증되지 않는다.

관련: [[vissim-single-instance-license]] 의 `:174` 완료 판정 함정과 마찬가지로,
`run.json` 의 error 메시지를 믿지 말고 `run/stderr.txt` 를 먼저 봐라.
