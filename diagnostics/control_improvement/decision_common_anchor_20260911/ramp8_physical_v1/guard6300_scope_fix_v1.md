# Frozen runtime scope restoration qualification

Canonical changes are limited to `shared_query_runtime_scope`; the new test module is `diagnostics/test_shared_query_runtime_scope.py`. Both are frozen. The surgical edit verified bytes outside the function unchanged and preserved CRLF inside the function; existing line endings elsewhere were untouched.

Dict/list restoration retains each unchanged immediate child reference instead of rebuilding it. This preserves nested set serialization and borrowed cfg-row aliases, even when other entries changed or an equal-valued replacement child was installed. Changed entry children are restored into the runtime root from the saved snapshot without rolling back the original child: actual shared cfg/state mutations therefore remain visible to the unchanged full raw-pickle guard. Bound follower and scalar children incur no added child serialization. Top-level set behavior is unchanged.

- Red before: 10 tests, 5 failures, 0.004 s.
- Focused after: 30 tests passed, 1.234 s.
- Parent integration: 63 tests passed, 14.921 s (reported by root; no duplicate execution).
- Original captured snapshot plus three synthetic counterexamples: 4/4 raw combined pickle bytes unchanged after a no-op scope; original alias/set identities retained. Evidence: `guard6300_scope_regression_fixed_v1/result.json`.

This is not general graph rollback. As before, changed children shared across runtime globals are restored from per-root snapshots, which do not guarantee all cross-global aliases. No physical endpoint/native/FZP work was run here. The native 6300 failure cause remains unconfirmed; the synthetic counterexamples independently justify this bounded repair.

Source SHA256: `b0e427d9553404627af853696132ad1c933ba530fc81eece2054129deac36ddf`
Test SHA256: `08b3c6e42e3319a5479f31fccb4057ce04c8c16b6f488a6eea3850e12645095e`
