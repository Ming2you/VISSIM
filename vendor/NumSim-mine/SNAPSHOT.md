# NumSim bundled runtime snapshot

This directory is the canonical NumSim runtime used by the VISSIM adapter. It is
a source snapshot, not a standalone Git checkout.

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/Ming2you/Numerical-Sim.git` |
| Upstream commit | `b22ab9d9d2d818be7831303900b950780751aad2` |
| Upstream root tree | `bdcc3697e55afc66328b28f9521bf635db51e49b` |
| Upstream `src` tree | `615ec962f36862f915c0adae3586b017df899962` |
| Git object format | `sha1` |
| Immutable anchor | `UPSTREAM_TREE.json` (`numsim-upstream-tree-v1`, 107 Python blobs) |
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
