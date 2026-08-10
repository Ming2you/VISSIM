# NumSim bundled runtime snapshot

This directory is the canonical NumSim runtime used by the VISSIM adapter. It is
a source snapshot, not a standalone Git checkout.

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/Ming2you/Numerical-Sim.git` |
| Upstream commit | `5a2fe7dd7f4ecc9b53c7b59767f0a12441ce853c` |
| Upstream root tree | `bc7e4a04724bd6427255f20fe60b90ca76f0c7ac` |
| Upstream `src` tree | `dbf5a604f1a0796ebfa93ab1719ed1aba09fbab8` |
| Git object format | `sha1` |
| Immutable anchor | `UPSTREAM_TREE.json` (`numsim-upstream-tree-v1`, 111 Python blobs) |
| Snapshot date | `2026-08-10` |
| Runtime source | `src/**/*.py` |

## Import contract

`evaluation/controllers/vissim_stackelberg_adapter.py` selects this directory
by default. `NUMSIM_REPO_ROOT` may select another checkout, but strict preflight
accepts it only when `scripts/verify_runtime_source.py` proves all of the
following:

- the declared snapshot and Git commit identify the full upstream commit;
- every LF-normalized Python file has the path/blob OID recorded in
  `UPSTREAM_TREE.json`;
- `repo_imports()` loads the same `src` module paths and module bytes; and
- no tracked Python source is dirty.

The verifier records the immutable upstream blob OID, checkout/index Git blob
OID, and raw checkout SHA-256 value for every Python file.
Tree and imported-module identity use LF-normalized bytes, so a checkout-only
CRLF conversion is recorded without being mistaken for a source-code change.
The normalization policy is declared in the repository `.gitattributes` file.

Strict runs also require `RW_PYTHON_EXE` to name the Python executable that is
actually running the verifier. Any source, commit, snapshot, import, dirty-tree,
or interpreter mismatch makes the verifier exit nonzero.
