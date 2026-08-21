from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "runtime-source-v2.1"
ANCHOR_SCHEMA_VERSION = "numsim-upstream-tree-v1"
UPSTREAM_REPOSITORY = "https://github.com/Ming2you/Numerical-Sim.git"
EXPECTED_SNAPSHOT_COMMIT = "e77b7d656a9cb6deca6cc7d8bc89dee50038f043"
EXPECTED_ROOT_TREE = "18152f85fca2f58969954fb094f43e9fb9abe87d"
EXPECTED_SRC_TREE = "6bdf291c8e0ef65925784442ba7221152180ee79"
EXPECTED_OBJECT_FORMAT = "sha1"
# 2026-08-18: 앵커에 local_patches 절이 추가되며 갱신됐다. 앵커와 이 상수는 두 열쇠라
# 한쪽만 바꿔서는 검증이 통과하지 않는다 - 의도된 설계다.
EXPECTED_ANCHOR_SEMANTIC_SHA256 = "c961979110272dd09024d832983ad9f0923568315f90719dd1d2ec988b970125"
EXPECTED_PYTHON_FILE_COUNT = 121
IMPORT_MARKER = "__RUNTIME_SOURCE_IMPORTS__="


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes()) if path.is_file() else ""


def _normalise_eol(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _git_blob_oid(data: bytes, object_format: str) -> str:
    framed = f"blob {len(data)}\0".encode("ascii") + data
    if object_format == "sha1":
        return hashlib.sha1(framed).hexdigest()
    if object_format == "sha256":
        return hashlib.sha256(framed).hexdigest()
    return ""


def _semantic_json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256(encoded)


def load_trust_anchor(path: Path) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "path": str(path.resolve()),
        "exists": path.is_file(),
        "checkout_sha256": _file_sha256(path),
        "semantic_sha256": "",
        "payload": {},
        "error": "",
    }
    if not path.is_file():
        evidence["error"] = "missing anchor"
        return evidence
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        return evidence
    if not isinstance(payload, dict):
        evidence["error"] = f"expected JSON object, got {type(payload).__name__}"
        return evidence
    evidence["payload"] = payload
    evidence["semantic_sha256"] = _semantic_json_sha256(payload)
    return evidence


def _eol_style(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    without_crlf = data.replace(b"\r\n", b"")
    bare_cr = without_crlf.count(b"\r")
    bare_lf = without_crlf.count(b"\n")
    kinds = sum(bool(value) for value in (crlf, bare_cr, bare_lf))
    if kinds == 0:
        return "none"
    if kinds > 1:
        return "mixed"
    if crlf:
        return "crlf"
    if bare_cr:
        return "cr"
    return "lf"


def _run_git(path: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except (FileNotFoundError, OSError):
        return left.resolve() == right.resolve()


def _git_metadata(root: Path) -> dict[str, Any]:
    try:
        top_result = _run_git(root, "rev-parse", "--show-toplevel", check=True)
        top = Path(top_result.stdout.strip()).resolve()
        root_relative = root.resolve().relative_to(top).as_posix()
        head = _run_git(top, "rev-parse", "HEAD", check=True).stdout.strip()
    except (OSError, ValueError, subprocess.SubprocessError):
        return {
            "available": False,
            "top_level": "",
            "root_relative": "",
            "root_is_repository": False,
            "head_commit": "",
        }
    return {
        "available": True,
        "top_level": str(top),
        "root_relative": root_relative,
        "root_is_repository": _same_path(top, root),
        "head_commit": head,
    }


def _scope_path(root_relative: str, suffix: str) -> str:
    return f"{root_relative}/{suffix}" if root_relative else suffix


def _tracked_blobs(git: Mapping[str, Any]) -> dict[str, str]:
    if not git.get("available"):
        return {}
    top = Path(str(git["top_level"]))
    scope = _scope_path(str(git["root_relative"]), "src")
    result = _run_git(top, "ls-files", "-s", "--", scope)
    blobs: dict[str, str] = {}
    prefix = f"{scope.rstrip('/')}/"
    for line in result.stdout.splitlines():
        match = re.match(r"^\d+\s+([0-9a-f]+)\s+\d+\t(.+)$", line)
        if not match:
            continue
        repository_path = match.group(2).replace("\\", "/")
        if not repository_path.startswith(prefix):
            continue
        relative = repository_path[len(prefix) :]
        if relative.endswith(".py"):
            blobs[relative] = match.group(1)
    return dict(sorted(blobs.items()))


def _declared_eols(git: Mapping[str, Any], relative_paths: Iterable[str]) -> dict[str, str]:
    if not git.get("available"):
        return {}
    top = Path(str(git["top_level"]))
    root_relative = str(git["root_relative"])
    repository_paths = [
        _scope_path(root_relative, f"src/{relative}")
        for relative in relative_paths
    ]
    if not repository_paths:
        return {}
    result = _run_git(top, "check-attr", "eol", "--", *repository_paths)
    prefix = _scope_path(root_relative, "src").rstrip("/") + "/"
    declarations: dict[str, str] = {}
    for line in result.stdout.splitlines():
        match = re.match(r"^(.*): eol: (.*)$", line)
        if not match:
            continue
        repository_path = match.group(1).replace("\\", "/")
        if repository_path.startswith(prefix):
            declarations[repository_path[len(prefix) :]] = match.group(2).strip()
    return declarations


def _dirty_tracked_source(git: Mapping[str, Any]) -> list[str]:
    if not git.get("available"):
        return []
    top = Path(str(git["top_level"]))
    scope = _scope_path(str(git["root_relative"]), "src")
    result = _run_git(top, "status", "--porcelain=v1", "--untracked-files=no", "--", scope)
    return sorted(line for line in result.stdout.splitlines() if line.strip())


def _tree_digest(files: Mapping[str, Mapping[str, Any]], field: str) -> str:
    digest = hashlib.sha256()
    for relative, record in sorted(files.items()):
        value = str(record.get(field, ""))
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest() if files else ""


def _snapshot_commit(root: Path) -> str:
    path = root / "SNAPSHOT.md"
    if not path.is_file():
        return ""
    match = re.search(
        r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])",
        path.read_text(encoding="utf-8-sig"),
        re.IGNORECASE,
    )
    return match.group(0).lower() if match else ""


def inspect_source_root(
    root: Path,
    canonical_eol_policy: Mapping[str, str] | None = None,
    object_format: str = EXPECTED_OBJECT_FORMAT,
) -> dict[str, Any]:
    root = root.resolve()
    source_root = root / "src"
    git = _git_metadata(root)
    tracked_blobs = _tracked_blobs(git)
    source_paths = sorted(
        source_root.rglob("*.py") if source_root.is_dir() else [],
        key=lambda path: path.relative_to(source_root).as_posix(),
    )
    relative_paths = [path.relative_to(source_root).as_posix() for path in source_paths]
    repository_eols = _declared_eols(git, relative_paths)
    eol_policy = canonical_eol_policy or repository_eols
    files: dict[str, dict[str, Any]] = {}
    for source, relative in zip(source_paths, relative_paths):
        data = source.read_bytes()
        files[relative] = {
            "git_blob_oid": tracked_blobs.get(relative, ""),
            "normalised_git_blob_oid": _git_blob_oid(_normalise_eol(data), object_format),
            "checkout_sha256": _sha256(data),
            "normalised_sha256": _sha256(_normalise_eol(data)),
            "checkout_eol": _eol_style(data),
            "declared_eol": eol_policy.get(relative, "unspecified"),
            "repository_declared_eol": repository_eols.get(relative, "unspecified"),
        }
    tracked_python = set(tracked_blobs)
    checkout_python = set(files)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "snapshot_path": str((root / "SNAPSHOT.md").resolve()),
        "snapshot_commit": _snapshot_commit(root),
        "snapshot_checkout_sha256": _file_sha256(root / "SNAPSHOT.md"),
        "git": git,
        "python_file_count": len(files),
        "normalised_tree_sha256": _tree_digest(files, "normalised_sha256"),
        "checkout_tree_sha256": _tree_digest(files, "checkout_sha256"),
        "git_blob_tree_sha256": _tree_digest(files, "git_blob_oid"),
        "dirty_tracked_source": _dirty_tracked_source(git),
        "untracked_python_files": sorted(checkout_python - tracked_python),
        "missing_tracked_python_files": sorted(tracked_python - checkout_python),
        "files": files,
    }


_IMPORT_PROBE = r'''
import hashlib
import json
import os
import sys
from pathlib import Path

workspace = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(workspace))
from evaluation.controllers import vissim_stackelberg_adapter as adapter

adapter.repo_imports(root)

def normalise(data):
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

modules = {}
external = []
for name, module in sorted(sys.modules.items()):
    if name != "src" and not name.startswith("src."):
        continue
    text = str(getattr(module, "__file__", "") or "").strip()
    if not text:
        continue
    path = Path(text).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        external.append({"module": name, "path": str(path)})
        continue
    data = path.read_bytes()
    modules[name] = {
        "path": str(path),
        "relative_path": relative,
        "checkout_sha256": hashlib.sha256(data).hexdigest(),
        "normalised_sha256": hashlib.sha256(normalise(data)).hexdigest(),
    }

payload = {
    "adapter_default_root": str(adapter.DEFAULT_REPO_ROOT.resolve()),
    "adapter_path": str(Path(adapter.__file__).resolve()),
    "modules": modules,
    "external_modules": external,
}
print("__RUNTIME_SOURCE_IMPORTS__=" + json.dumps(payload, sort_keys=True))
'''


def probe_imports(workspace: Path, root: Path) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["NUMSIM_REPO_ROOT"] = str(root.resolve())
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", _IMPORT_PROBE, str(workspace), str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=120,
    )
    payload_line = next(
        (line for line in reversed(result.stdout.splitlines()) if line.startswith(IMPORT_MARKER)),
        "",
    )
    if result.returncode != 0 or not payload_line:
        return {
            "ok": False,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "adapter_default_root": "",
            "adapter_path": "",
            "modules": {},
            "external_modules": [],
        }
    payload = json.loads(payload_line[len(IMPORT_MARKER) :])
    payload.update({"ok": True, "returncode": 0, "stdout": "", "stderr": ""})
    return payload


def _check(identifier: str, passed: bool, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "status": "PASS" if passed else "FAIL",
        "expected": expected,
        "actual": actual,
    }


def _python_identity(strict: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    configured = os.environ.get("RW_PYTHON_EXE", "").strip()
    configured_path = Path(configured).resolve() if configured else None
    executable = Path(sys.executable).resolve()
    exists = bool(configured_path and configured_path.is_file())
    matches = bool(exists and _same_path(configured_path, executable))
    identity = {
        "strict": strict,
        "rw_python_exe": str(configured_path) if configured_path else "",
        "executable": str(executable),
        "version": sys.version,
        "executable_sha256": _file_sha256(executable),
    }
    checks = [
        _check("python.rw_python_exe_present", not strict or bool(configured), True, bool(configured)),
        _check("python.rw_python_exe_exists", not strict or exists, True, exists),
        _check("python.executable_matches", not strict or matches, str(executable), str(configured_path or "")),
    ]
    return identity, checks


def _module_projection(probe: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    modules = probe.get("modules", {})
    if not isinstance(modules, Mapping):
        return {}
    return {
        str(name): (
            str(record.get("relative_path", "")),
            str(record.get("normalised_sha256", "")),
        )
        for name, record in modules.items()
        if isinstance(record, Mapping)
    }


def _anchored_blob_map(source: Mapping[str, Any]) -> dict[str, str]:
    files = source.get("files", {})
    if not isinstance(files, Mapping):
        return {}
    return {
        f"src/{relative}": str(record.get("normalised_git_blob_oid", ""))
        for relative, record in files.items()
        if isinstance(record, Mapping)
    }


def _blob_mismatches(
    expected: Mapping[str, str],
    actual: Mapping[str, str],
    local_patches: Mapping[str, str] | None = None,
) -> list[str]:
    """앵커와 실제 트리의 blob 불일치. **등재된 로컬 패치만** 예외로 인정한다.

    왜 예외를 두는가. vendor 는 상류 커밋의 스냅샷이지만, 상류에 아직 반영되지 않은 수정을
    당겨써야 할 때가 있다(2026-08-18 의 폴백 가드 센티널 건). 그때 앵커의 blob OID 를 조용히
    새 값으로 바꾸면 앵커가 "그 커밋에 이 내용이 있다"는 **거짓**을 주장하게 된다. 이 저장소가
    계속 잡아온 실패가 정확히 그 부류다.

    대신 앵커의 `local_patches` 에 (path, upstream_blob, patched_blob, 사유, 증거)를 적고,
    여기서는 **정확히 그 조합만** 통과시킨다. 등재되지 않은 이탈, 또는 등재됐는데 실제 지문이
    `patched_blob` 과 다른 경우는 그대로 불일치로 남는다 - 즉 패치 자체도 핀된다.
    """
    allowed = dict(local_patches or {})
    mismatches: list[str] = []
    for path in set(expected) | set(actual):
        if expected.get(path) == actual.get(path):
            continue
        pinned = allowed.get(path)
        if pinned is not None and actual.get(path) == pinned:
            continue
        mismatches.append(path)
    return sorted(mismatches)


def _local_addition_index(anchor: Mapping[str, Any]) -> tuple[dict[str, str], list[str]]:
    """앵커의 `local_additions` 를 (path -> blob) 으로 편다. 형식 오류는 사유와 함께 돌려준다.

    왜 `local_patches` 로 안 되나. 그쪽은 **상류에 있는 파일을 로컬에서 고친 것**이라
    `upstream_blob` 과 `patched_blob` 두 지문을 요구한다. 상류에 아예 없는 **신규 파일**은
    `upstream_blob` 이 존재하지 않아 그 스키마로 표현할 수 없다(40-hex OID 검사에 걸린다).

    그렇다고 `python_blobs` 에 끼워 넣으면 앵커가 "상류 커밋에 이 파일이 있다" 는 거짓을
    주장하게 된다 — `local_patches_note` 가 금지한 바로 그것이다. 그래서 별도 절을 둔다.
    여기 등재된 경로만 파일집합 비교에서 예외로 인정하고, 등재됐는데 실제 지문이 다르거나
    파일이 사라지면 그대로 실패로 남는다.
    """
    entries = anchor.get("local_additions") or []
    index: dict[str, str] = {}
    problems: list[str] = []
    if not isinstance(entries, list):
        return {}, ["local_additions must be a list"]
    for i, item in enumerate(entries):
        if not isinstance(item, Mapping):
            problems.append(f"[{i}] not an object")
            continue
        path = str(item.get("path", ""))
        blob = str(item.get("blob", ""))
        why = str(item.get("why", "")).strip()
        if not path:
            problems.append(f"[{i}] missing path")
        if not re.fullmatch(r"[0-9a-f]{40}", blob):
            problems.append(f"[{i}] {path}: blob must be a 40-hex OID")
        if not why:
            problems.append(f"[{i}] {path}: why is required")
        if path and blob:
            index[path] = blob
    return index, problems


def _local_patch_index(anchor: Mapping[str, Any]) -> tuple[dict[str, str], list[str]]:
    """앵커의 local_patches 를 (path -> patched_blob) 로 편다. 형식 오류는 사유와 함께 돌려준다."""
    entries = anchor.get("local_patches") or []
    index: dict[str, str] = {}
    problems: list[str] = []
    if not isinstance(entries, list):
        return {}, ["local_patches must be a list"]
    for i, item in enumerate(entries):
        if not isinstance(item, Mapping):
            problems.append(f"[{i}] not an object")
            continue
        path = str(item.get("path", ""))
        patched = str(item.get("patched_blob", ""))
        upstream = str(item.get("upstream_blob", ""))
        why = str(item.get("why", "")).strip()
        if not path:
            problems.append(f"[{i}] missing path")
        if not re.fullmatch(r"[0-9a-f]{40}", patched):
            problems.append(f"[{i}] {path}: patched_blob must be a 40-hex OID")
        if not re.fullmatch(r"[0-9a-f]{40}", upstream):
            problems.append(f"[{i}] {path}: upstream_blob must be a 40-hex OID")
        if not why:
            problems.append(f"[{i}] {path}: why is required")
        if path and patched:
            index[path] = patched
    return index, problems


def build_report(repo: Path, selected_root: Path, strict: bool = True) -> dict[str, Any]:
    repo = repo.resolve()
    canonical_root = (repo / "vendor" / "NumSim-mine").resolve()
    anchor_path = canonical_root / "UPSTREAM_TREE.json"
    anchor_evidence = load_trust_anchor(anchor_path)
    anchor = anchor_evidence["payload"]
    anchor_blobs_raw = anchor.get("python_blobs", {}) if isinstance(anchor, Mapping) else {}
    anchor_blobs = (
        {str(path): str(oid) for path, oid in anchor_blobs_raw.items()}
        if isinstance(anchor_blobs_raw, Mapping)
        else {}
    )
    object_format = str(anchor.get("object_format", EXPECTED_OBJECT_FORMAT))
    canonical = inspect_source_root(canonical_root, object_format=object_format)
    canonical_eol_policy = {
        relative: str(record.get("declared_eol", "unspecified"))
        for relative, record in canonical["files"].items()
    }
    selected = inspect_source_root(selected_root, canonical_eol_policy, object_format)
    canonical_probe = probe_imports(repo, canonical_root)
    selected_probe = probe_imports(repo, selected_root)
    python_identity, checks = _python_identity(strict)

    selected_is_canonical = _same_path(selected_root, canonical_root)
    selected_git = selected["git"]
    commit_actual = (
        EXPECTED_SNAPSHOT_COMMIT
        if selected_is_canonical
        else str(selected_git.get("head_commit", ""))
    )
    commit_ok = selected_is_canonical or (
        bool(selected_git.get("root_is_repository"))
        and commit_actual.lower() == EXPECTED_SNAPSHOT_COMMIT
    )
    canonical_files = set(canonical["files"])
    selected_files = set(selected["files"])
    anchor_paths = list(anchor_blobs)
    canonical_anchor_blobs = _anchored_blob_map(canonical)
    selected_anchor_blobs = _anchored_blob_map(selected)
    local_patch_index, local_patch_problems = _local_patch_index(anchor)
    local_addition_index, local_addition_problems = _local_addition_index(anchor)
    # 신규 파일도 "등재된 지문과 정확히 같을 때만" 통과시킨다 — 패치와 같은 규율.
    allowed_blobs = {**local_patch_index, **local_addition_index}
    canonical_anchor_mismatches = _blob_mismatches(anchor_blobs, canonical_anchor_blobs, allowed_blobs)
    selected_anchor_mismatches = _blob_mismatches(anchor_blobs, selected_anchor_blobs, allowed_blobs)
    local_addition_unapplied = sorted(
        path for path, oid in local_addition_index.items()
        if canonical_anchor_blobs.get(path) != oid
    )
    # 등재된 패치가 실제로 그 지문으로 존재하는지. 사라지거나 다시 바뀌면 여기서 걸린다.
    local_patch_unapplied = sorted(
        path for path, oid in local_patch_index.items()
        if canonical_anchor_blobs.get(path) != oid
    )
    canonical_modules = _module_projection(canonical_probe)
    selected_modules = _module_projection(selected_probe)

    checks.extend(
        [
            _check("canonical.root_exists", canonical["exists"], True, canonical["exists"]),
            _check("trust_anchor.exists", anchor_evidence["exists"], True, anchor_evidence["exists"]),
            _check("trust_anchor.json", not anchor_evidence["error"], "valid JSON object", anchor_evidence["error"] or "valid JSON object"),
            _check("trust_anchor.semantic_sha256", anchor_evidence["semantic_sha256"] == EXPECTED_ANCHOR_SEMANTIC_SHA256, EXPECTED_ANCHOR_SEMANTIC_SHA256, anchor_evidence["semantic_sha256"]),
            _check("trust_anchor.schema", anchor.get("schema_version") == ANCHOR_SCHEMA_VERSION, ANCHOR_SCHEMA_VERSION, anchor.get("schema_version")),
            _check("trust_anchor.repository", anchor.get("upstream_repository") == UPSTREAM_REPOSITORY, UPSTREAM_REPOSITORY, anchor.get("upstream_repository")),
            _check("trust_anchor.commit", anchor.get("commit") == EXPECTED_SNAPSHOT_COMMIT, EXPECTED_SNAPSHOT_COMMIT, anchor.get("commit")),
            _check("trust_anchor.root_tree", anchor.get("root_tree") == EXPECTED_ROOT_TREE, EXPECTED_ROOT_TREE, anchor.get("root_tree")),
            _check("trust_anchor.src_tree", anchor.get("src_tree") == EXPECTED_SRC_TREE, EXPECTED_SRC_TREE, anchor.get("src_tree")),
            _check("trust_anchor.object_format", object_format == EXPECTED_OBJECT_FORMAT, EXPECTED_OBJECT_FORMAT, object_format),
            _check("trust_anchor.python_file_count", anchor.get("python_file_count") == EXPECTED_PYTHON_FILE_COUNT and len(anchor_blobs) == EXPECTED_PYTHON_FILE_COUNT, EXPECTED_PYTHON_FILE_COUNT, {"declared": anchor.get("python_file_count"), "listed": len(anchor_blobs)}),
            _check("trust_anchor.paths_sorted", anchor_paths == sorted(anchor_paths), "sorted paths", anchor_paths == sorted(anchor_paths)),
            _check("trust_anchor.blob_oids", all(re.fullmatch(r"[0-9a-f]{40}", oid) for oid in anchor_blobs.values()), "96 SHA-1 blob OIDs", len([oid for oid in anchor_blobs.values() if re.fullmatch(r"[0-9a-f]{40}", oid)])),
            _check("canonical.anchor_python_file_set", set(canonical_anchor_blobs) == set(anchor_blobs) | set(local_addition_index), sorted(set(anchor_blobs) | set(local_addition_index)), sorted(canonical_anchor_blobs)),
            _check("trust_anchor.local_patches_wellformed", not local_patch_problems, [], local_patch_problems),
            _check("trust_anchor.local_patches_applied", not local_patch_unapplied, [], local_patch_unapplied),
            _check("trust_anchor.local_additions_wellformed", not local_addition_problems, [], local_addition_problems),
            _check("trust_anchor.local_additions_applied", not local_addition_unapplied, [], local_addition_unapplied),
            _check("trust_anchor.local_addition_count", True, "informational", sorted(local_addition_index)),
            # 등재 건수를 항상 드러낸다. 0 이 아닌 것이 조용히 지나가면 안 된다.
            _check("trust_anchor.local_patch_count", True, "informational", sorted(local_patch_index)),
            _check("canonical.anchor_python_blobs", not canonical_anchor_mismatches, [], canonical_anchor_mismatches),
            _check(
                "canonical.snapshot_commit",
                canonical["snapshot_commit"] == EXPECTED_SNAPSHOT_COMMIT,
                EXPECTED_SNAPSHOT_COMMIT,
                canonical["snapshot_commit"],
            ),
            _check("canonical.python_tree_nonempty", canonical["python_file_count"] > 0, ">0", canonical["python_file_count"]),
            _check("canonical.tracked_python_complete", not canonical["untracked_python_files"] and not canonical["missing_tracked_python_files"], [], canonical["untracked_python_files"] + canonical["missing_tracked_python_files"]),
            _check("canonical.tracked_source_clean", not canonical["dirty_tracked_source"], [], canonical["dirty_tracked_source"]),
            _check("canonical.eol_declared", all(value == "lf" for value in canonical_eol_policy.values()), "lf for every Python source", sorted(relative for relative, value in canonical_eol_policy.items() if value != "lf")),
            _check("selected.root_exists", selected["exists"], True, selected["exists"]),
            _check("selected.adapter_default_root", selected_probe.get("adapter_default_root") == str(selected_root.resolve()), str(selected_root.resolve()), selected_probe.get("adapter_default_root", "")),
            _check("selected.snapshot_commit", selected["snapshot_commit"] == EXPECTED_SNAPSHOT_COMMIT, EXPECTED_SNAPSHOT_COMMIT, selected["snapshot_commit"]),
            _check("selected.commit", commit_ok, EXPECTED_SNAPSHOT_COMMIT, commit_actual),
            _check("selected.anchor_python_file_set", set(selected_anchor_blobs) == set(anchor_blobs) | set(local_addition_index), sorted(set(anchor_blobs) | set(local_addition_index)), sorted(selected_anchor_blobs)),
            _check("selected.anchor_python_blobs", not selected_anchor_mismatches, [], selected_anchor_mismatches),
            _check("selected.python_file_set", selected_files == canonical_files, sorted(canonical_files), sorted(selected_files)),
            _check("selected.python_tree", selected["normalised_tree_sha256"] == canonical["normalised_tree_sha256"], canonical["normalised_tree_sha256"], selected["normalised_tree_sha256"]),
            _check("selected.tracked_python_complete", selected_is_canonical or (not selected["untracked_python_files"] and not selected["missing_tracked_python_files"]), [], selected["untracked_python_files"] + selected["missing_tracked_python_files"]),
            _check("selected.tracked_source_clean", not selected["dirty_tracked_source"], [], selected["dirty_tracked_source"]),
            _check("canonical.import_probe", bool(canonical_probe.get("ok")), True, canonical_probe.get("returncode")),
            _check("selected.import_probe", bool(selected_probe.get("ok")), True, selected_probe.get("returncode")),
            _check("canonical.external_imports", not canonical_probe.get("external_modules"), [], canonical_probe.get("external_modules", [])),
            _check("selected.external_imports", not selected_probe.get("external_modules"), [], selected_probe.get("external_modules", [])),
            _check("selected.import_module_set", set(selected_modules) == set(canonical_modules), sorted(canonical_modules), sorted(selected_modules)),
            _check("selected.import_module_path_hash", selected_modules == canonical_modules, canonical_modules, selected_modules),
        ]
    )
    reasons = [item["id"] for item in checks if item["status"] != "PASS"]
    status = "PASS" if not reasons else "FAIL"
    return {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": {
            "gitattributes_sha256": _file_sha256(repo / ".gitattributes"),
            "upstream_tree_anchor_sha256": anchor_evidence["checkout_sha256"],
            "upstream_tree_anchor_semantic_sha256": anchor_evidence["semantic_sha256"],
            "adapter_sha256": _file_sha256(
                repo / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"
            ),
            "canonical_snapshot_sha256": canonical["snapshot_checkout_sha256"],
            "canonical_python_tree_normalised_sha256": canonical["normalised_tree_sha256"],
            "selected_snapshot_sha256": selected["snapshot_checkout_sha256"],
            "selected_python_tree_normalised_sha256": selected["normalised_tree_sha256"],
            "python_executable_sha256": python_identity["executable_sha256"],
        },
        "command_version": {
            "command": "scripts/verify_runtime_source.py",
            "version": SCHEMA_VERSION,
            "sha256": _file_sha256(Path(__file__).resolve()),
        },
        "status": status,
        "reasons": reasons,
        "sample_dimensions": {
            "canonical_python_files": canonical["python_file_count"],
            "selected_python_files": selected["python_file_count"],
            "canonical_imported_modules": len(canonical_modules),
            "selected_imported_modules": len(selected_modules),
        },
        "units": {
            "python_file_count": "file",
            "imported_module_count": "module",
            "checkout_sha256": "SHA-256 hex digest of raw bytes",
            "normalised_sha256": "SHA-256 hex digest of LF-normalised bytes",
            "git_blob_oid": "Git object ID",
        },
        "downstream_consumers": [
            "S0R-2 strict preflight",
            "S0R-3 baseline snapshot",
            "scripts/run_plant_fidelity_matrix.ps1",
            "scripts/audit_plant_fidelity.py",
        ],
        "strict": strict,
        "expected_snapshot_commit": EXPECTED_SNAPSHOT_COMMIT,
        "trust_anchor": {
            "path": anchor_evidence["path"],
            "checkout_sha256": anchor_evidence["checkout_sha256"],
            "semantic_sha256": anchor_evidence["semantic_sha256"],
            "schema_version": anchor.get("schema_version", ""),
            "upstream_repository": anchor.get("upstream_repository", ""),
            "commit": anchor.get("commit", ""),
            "root_tree": anchor.get("root_tree", ""),
            "src_tree": anchor.get("src_tree", ""),
            "object_format": object_format,
            "python_file_count": len(anchor_blobs),
        },
        "selected_is_canonical": selected_is_canonical,
        "python": python_identity,
        "canonical": canonical,
        "selected": selected,
        "imports": {
            "canonical": canonical_probe,
            "selected": selected_probe,
        },
        "checks": checks,
    }


def write_report_atomic(path: Path, report: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the NumSim runtime source identity.")
    parser.add_argument("--repo", default=".", help="VISSIM repository root")
    parser.add_argument("--numsim-root", default="", help="Explicit NumSim root; defaults like the adapter")
    parser.add_argument("--out", required=True, help="Output JSON path")
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        help="Require RW_PYTHON_EXE to match this interpreter (default)",
    )
    strict_group.add_argument(
        "--allow-nonstrict",
        dest="strict",
        action="store_false",
        help="Diagnostic only: do not require RW_PYTHON_EXE",
    )
    parser.set_defaults(strict=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve()
    selected_text = args.numsim_root or os.environ.get("NUMSIM_REPO_ROOT", "")
    selected_root = Path(selected_text).resolve() if selected_text else (repo / "vendor" / "NumSim-mine").resolve()
    report = build_report(repo, selected_root, bool(args.strict))
    out = Path(args.out)
    write_report_atomic(out, report)
    print(json.dumps({"status": report["status"], "out": str(out.resolve())}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
