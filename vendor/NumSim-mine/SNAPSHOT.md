# NumSim bundled runtime snapshot

This directory is the canonical NumSim runtime used by the VISSIM adapter. It is
a source snapshot, not a standalone Git checkout.

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/Ming2you/Numerical-Sim.git` |
| Upstream commit | `9a5786939abe3ebc99ec146ab4c3f93433229cf1` |
| Upstream root tree | `bcf843c5a9f00b13bd0a9940c59b3172043588e8` |
| Upstream `src` tree | `499913ef5e0c745a20acacd8b4ec414dc2b4b2c2` |
| Git object format | `sha1` |
| Immutable anchor | `UPSTREAM_TREE.json` (`numsim-upstream-tree-v1`, 119 Python blobs) |
| Snapshot date | `2026-08-12` |
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
