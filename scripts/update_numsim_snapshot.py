#!/usr/bin/env python3
# 상류 NumSim 커밋을 vendor/ 스냅샷으로 옮기고 무결성 앵커를 갱신하는 파이프라인 (v3 N1.5)
"""Re-snapshot `vendor/NumSim-mine` from the upstream NumSim checkout.

`verify_runtime_source.py` proves every vendored Python file against
`UPSTREAM_TREE.json`. Nothing produced that anchor - the repository only had
consumers - so any NumSim change broke the chain with no way to re-anchor it.
That blocks v3 N2 onward, which is entirely NumSim work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path


ANCHOR_SCHEMA_VERSION = "numsim-upstream-tree-v1"
OBJECT_FORMAT = "sha1"


class SnapshotError(RuntimeError):
    """Raised when the upstream checkout or the anchor rewrite is not trustworthy."""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        raise SnapshotError(
            "git %s failed: %s" % (" ".join(args), (result.stderr or "").strip())
        )
    return (result.stdout or "").strip()


def _normalise_eol(data: bytes) -> bytes:
    # verify_runtime_source._normalise_eol 과 반드시 같아야 한다.
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _git_blob_oid(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _upstream_python_files(upstream: Path) -> list[Path]:
    return sorted(
        path
        for path in (upstream / "src").rglob("*.py")
        if "__pycache__" not in path.parts
    )


def assert_clean_upstream(upstream: Path) -> None:
    """A dirty tree means the anchor commit would not describe the copied bytes."""
    porcelain = _git(upstream, "status", "--porcelain", "--", "src")
    dirty = [line for line in porcelain.splitlines() if line and not line.startswith("??")]
    if dirty:
        raise SnapshotError(
            "upstream src/ has uncommitted tracked changes:\n  " + "\n  ".join(dirty)
        )


def sync_sources(upstream: Path, vendor: Path) -> tuple[int, int]:
    """Copy src/**/*.py into the vendor tree and drop files upstream no longer has.

    A leftover vendor file has no anchor entry, so verify_runtime_source rejects it.
    """
    wanted = {
        path.relative_to(upstream).as_posix(): path
        for path in _upstream_python_files(upstream)
    }
    for relative, source in wanted.items():
        target = vendor / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        # 줄바꿈만 다르고 내용이 같으면 건드리지 않는다. 앵커는 LF 정규화 기준이라 두 형태가
        # 같은 blob OID 를 내지만, 파일을 다시 쓰면 git 이 dirty 로 보아
        # verify_runtime_source 의 tracked_source_clean 이 FAIL 한다.
        if target.is_file() and _normalise_eol(target.read_bytes()) == _normalise_eol(data):
            continue
        target.write_bytes(data)
    removed = 0
    for path in sorted((vendor / "src").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if path.relative_to(vendor).as_posix() not in wanted:
            path.unlink()
            removed += 1
    return len(wanted), removed


def rewrite_snapshot_md(path: Path, anchor: dict, snapshot_date: str) -> None:
    text = path.read_text(encoding="utf-8")
    rows = {
        "Upstream repository": anchor["upstream_repository"],
        "Upstream commit": anchor["commit"],
        "Upstream root tree": anchor["root_tree"],
        "Upstream `src` tree": anchor["src_tree"],
        "Git object format": anchor["object_format"],
        "Snapshot date": snapshot_date,
    }
    for label, value in rows.items():
        pattern = re.compile(
            r"^(\|\s*" + re.escape(label) + r"\s*\|\s*)(.*?)(\s*\|)\s*$", re.MULTILINE
        )
        text, count = pattern.subn(lambda m: m.group(1) + f"`{value}`" + m.group(3), text)
        if count != 1:
            raise SnapshotError(
                f"SNAPSHOT.md row {label!r} matched {count} times, expected exactly 1"
            )
    anchor_row = re.compile(
        r"^(\|\s*Immutable anchor\s*\|\s*`UPSTREAM_TREE\.json`\s*\(`"
        + re.escape(ANCHOR_SCHEMA_VERSION)
        + r"`,\s*)(\d+)(\s*Python blobs\)\s*\|)\s*$",
        re.MULTILINE,
    )
    text, count = anchor_row.subn(
        lambda m: m.group(1) + str(anchor["python_file_count"]) + m.group(3), text
    )
    if count != 1:
        raise SnapshotError(
            f"SNAPSHOT.md immutable-anchor row matched {count} times, expected exactly 1"
        )
    path.write_text(text, encoding="utf-8", newline="\n")


def rewrite_verifier_constants(path: Path, anchor: dict) -> None:
    """The verifier repeats the commit and file count as module constants."""
    text = path.read_text(encoding="utf-8")
    for name, value in (
        ("EXPECTED_SNAPSHOT_COMMIT", '"%s"' % anchor["commit"]),
        ("EXPECTED_PYTHON_FILE_COUNT", str(anchor["python_file_count"])),
    ):
        pattern = re.compile(r"^(" + name + r"\s*=\s*)(.+)$", re.MULTILINE)
        text, count = pattern.subn(lambda m: m.group(1) + value, text)
        if count != 1:
            raise SnapshotError(
                f"{path.name} constant {name} matched {count} times, expected exactly 1"
            )
    path.write_text(text, encoding="utf-8", newline="\n")


def build_anchor(upstream: Path, upstream_repository: str) -> dict:
    files = _upstream_python_files(upstream)
    if not files:
        raise SnapshotError("upstream src/ contains no Python files")
    blobs = {
        path.relative_to(upstream).as_posix(): _git_blob_oid(
            _normalise_eol(path.read_bytes())
        )
        for path in files
    }
    return {
        "schema_version": ANCHOR_SCHEMA_VERSION,
        "upstream_repository": upstream_repository,
        "commit": _git(upstream, "rev-parse", "HEAD"),
        "root_tree": _git(upstream, "rev-parse", "HEAD^{tree}"),
        "src_tree": _git(upstream, "rev-parse", "HEAD:src"),
        "object_format": OBJECT_FORMAT,
        "python_file_count": len(blobs),
        "python_blobs": dict(sorted(blobs.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-snapshot vendor/NumSim-mine")
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--snapshot-date", default=date.today().isoformat())
    args = parser.parse_args(argv)

    root = args.workspace_root.resolve(strict=True)
    upstream = args.upstream.resolve(strict=True)
    vendor = (root / "vendor" / "NumSim-mine").resolve(strict=True)
    anchor_path = vendor / "UPSTREAM_TREE.json"

    try:
        previous = json.loads(anchor_path.read_text(encoding="utf-8"))
        repository = str(previous.get("upstream_repository", "")).strip()
        if not repository:
            raise SnapshotError("existing UPSTREAM_TREE.json has no upstream_repository")
        # 더러운 트리는 어떤 것도 건드리기 전에 거부한다.
        assert_clean_upstream(upstream)
        copied, removed = sync_sources(upstream, vendor)
        anchor = build_anchor(upstream, repository)
        anchor_path.write_text(
            json.dumps(anchor, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        rewrite_snapshot_md(vendor / "SNAPSHOT.md", anchor, args.snapshot_date)
        rewrite_verifier_constants(root / "scripts" / "verify_runtime_source.py", anchor)
    except (SnapshotError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    print(
        "status=PASS commit=%s files=%d copied=%d removed=%d previous_commit=%s"
        % (
            anchor["commit"],
            anchor["python_file_count"],
            copied,
            removed,
            previous.get("commit", ""),
        )
    )
    print("next: verify_runtime_source.py -> build_preflight_manifest.py -> approve_physical_stock_topology.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
