#!/usr/bin/env python3
# N4-0 작업2 - 제어 15 SC 의 supplyFile2 를 새 dual-ring .sig 로 옮긴 inpx 를 만드는 생산자
"""Point the 15 controlled signal controllers at the rebuilt dual-ring programs.

## 왜 XML 재직렬화가 아니라 바이트 수술인가

이 `.inpx` 는 3.0 MB · 34,255 줄이고 감사 `canonical_topology` 가 `inpx_sha256` 으로
붙잡고 있다. `ET.parse` -> `ET.tostring` 왕복은 속성 순서·자기닫힘 태그·공백을 바꿀 수
있어서, 링크 하나 안 건드렸는데도 파일 전체가 달라진다. 그러면 "무엇이 바뀌었는가" 를
diff 로 증명할 수 없다.

그래서 `<signalController ...>` 시작 태그만 찾아 그 안의 `supplyFile2` 값 하나를 바꾼다.
줄 단위 diff 가 정확히 15 줄이어야 하고, 그 15 줄의 차이는 `_n4dr150` 삽입뿐이어야 한다
(`scripts/tests/test_rewire_inpx_signal_programs.py` 가 실 파일에서 확인한다).

## 무엇을 하지 않는가

- `progNo`·`offset` 은 안 건드린다. 새 프로그램도 progNo 1 이 활성이고, offset 은
  N4-7 삼중 잠금 아래 `intent_only` 라 플랜트에 도달하지 않는다.
- 원본 `.inpx` 는 덮어쓰지 않는다. 생산자 자신이 같은 경로를 거부한다.
- `.layx` 는 만들지 않는다. VISSIM 은 없으면 기본 레이아웃으로 연다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence


SCHEMA_VERSION = "inpx-signal-program-rewire-v1"

REPO = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
DEFAULT_MAPPING = (
    REPO
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "control_mapping_distributed_core15n41_20260805.json"
)
# `scripts/build_dual_ring_signal_programs.py` 가 쓴 새 파일명 접미사.
DEFAULT_SUFFIX = "_n4dr150"

_CONTROLLER_TAG = re.compile(rb"<signalController\b[^>]*>")
_SUPPLY_ATTR = re.compile(rb'supplyFile2="([^"]*)"')
_NO_ATTR = re.compile(rb'\bno="([0-9]+)"')


class RewireError(RuntimeError):
    """배선을 만들 수 없다. 조용한 폴백 대신 예외로 올린다."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _controlled_sc_numbers(mapping_path: Path) -> list[int]:
    payload = json.loads(Path(mapping_path).read_text(encoding="utf-8-sig"))
    numbers = [int(item["sc_no"]) for item in payload.get("signals", []) if item.get("sc_no")]
    if not numbers:
        raise RewireError(f"{mapping_path} declares no controlled signals")
    return numbers


def _split_reference(raw: str) -> tuple[str, str]:
    """`#data#<name>` 을 (접두사, 파일명) 으로 나눈다."""
    if raw.lower().startswith("#data#"):
        return "#data#", raw[6:]
    return "", raw


def rewire(
    *,
    network_path: Path = DEFAULT_NETWORK,
    mapping_path: Path = DEFAULT_MAPPING,
    out_path: Path,
    suffix: str = DEFAULT_SUFFIX,
) -> dict[str, Any]:
    """제어 SC 의 `supplyFile2` 를 `<stem><suffix>.sig` 로 옮긴 `.inpx` 를 쓴다."""

    network_path = Path(network_path)
    out_path = Path(out_path)
    if out_path.resolve() == network_path.resolve():
        raise RewireError(f"원본 inpx 를 덮어쓸 수 없다: {out_path}")

    raw = network_path.read_bytes()
    before_sha = _sha256_bytes(raw)
    wanted = set(_controlled_sc_numbers(Path(mapping_path)))

    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    chunks: list[bytes] = []
    cursor = 0

    for match in _CONTROLLER_TAG.finditer(raw):
        tag = match.group(0)
        no_found = _NO_ATTR.search(tag)
        if no_found is None:
            continue
        sc_no = int(no_found.group(1))
        if sc_no not in wanted:
            continue
        supply = _SUPPLY_ATTR.search(tag)
        if supply is None:
            raise RewireError(f"SC{sc_no} declares no supplyFile2")
        prefix, name = _split_reference(supply.group(1).decode("utf-8"))
        if not name.lower().endswith(".sig"):
            raise RewireError(f"SC{sc_no} supplyFile2 is not a .sig: {name!r}")
        after_name = f"{name[:-4]}{suffix}.sig"
        target = network_path.parent / after_name
        if not target.is_file():
            raise RewireError(f"SC{sc_no} target program is missing: {target}")

        # 태그 **안에서만** 속성값을 바꾼다. 같은 파일명이 다른 SC 에도 쓰이면
        # 전역 치환은 엉뚱한 컨트롤러까지 옮긴다.
        new_tag = (
            tag[: supply.start(1)]
            + f"{prefix}{after_name}".encode("utf-8")
            + tag[supply.end(1) :]
        )
        chunks.append(raw[cursor : match.start()])
        chunks.append(new_tag)
        cursor = match.end()

        rows.append(
            {
                "sc_no": sc_no,
                "before_sig": name,
                "after_sig": after_name,
                "prog_no": int(
                    (re.search(rb'progNo="([0-9]+)"', tag) or [b"", b"1"])[1]
                ),
                "target_sha256": _sha256_bytes(target.read_bytes()),
            }
        )
        seen.add(sc_no)

    missing = sorted(wanted - seen)
    if missing:
        raise RewireError(f"{network_path} declares no signalController for {missing}")

    chunks.append(raw[cursor:])
    payload = b"".join(chunks)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)

    rows.sort(key=lambda row: int(row["sc_no"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "network": str(network_path),
            "network_sha256_before": before_sha,
            "out_network": str(out_path),
            "network_sha256_after": _sha256_bytes(payload),
            "control_mapping": str(Path(mapping_path)),
            "suffix": suffix,
        },
        "controllers": rows,
        "counts": {
            "controllers_rewired": len(rows),
            "controllers_total": len(_CONTROLLER_TAG.findall(raw)),
            "bytes_before": len(raw),
            "bytes_after": len(payload),
        },
        "status": "PASS" if len(rows) == len(wanted) else "FAIL",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--suffix", default=DEFAULT_SUFFIX)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        table = rewire(
            network_path=args.network,
            mapping_path=args.mapping,
            out_path=args.out,
            suffix=args.suffix,
        )
    except (RewireError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(table, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    counts = table["counts"]
    print(
        "status=%s rewired=%d/%d sha256 %s -> %s"
        % (
            table["status"],
            counts["controllers_rewired"],
            counts["controllers_total"],
            table["source"]["network_sha256_before"][:12],
            table["source"]["network_sha256_after"][:12],
        )
    )
    return 0 if table["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
