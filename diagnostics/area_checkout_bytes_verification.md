# Staged area checkout-byte verification

**Final verification PASS: all130 staged files produce exactly the manifest's bytes through real Git checkout/smudge.** Parent forced the two script paths through `git add --renormalize`. The complete130-file check was rerun at2026-09-09 23:17:36UTC; all working bytes remained identical to the original verification, and index/manifest/attributes stayed unchanged during that rerun. The repaired raw script blob IDs are `25b5faec534f4c5d389ea4e6247a237943103f6c` (PS1) and `4bdd44d7938c95158886fbe2a3267a73fbd44bd9` (VBS).

The original verification failed for2 scripts while128 others passed. That failure and its complete evidence are retained under `initial_verification` in the JSON. It was a Git representation defect, not a change to the running trial's working inputs. Parent reports commit324a3b8 and the actual trial starting2026-09-10 08:13:13KST with the same matching working bytes. The following table and diagnosis describe the original failure before the parent's index repair.

The126 manifest sources and4 outputs were read from the index. For each indexed blob, the audit invoked real `git cat-file --filters --path=<path> <blob-oid>` and compared the returned checkout bytes against both the manifest SHA256 and working file. Staged and working attributes were identical, with141 explicit quoted rules. No effective external filter, working-tree-encoding or ident transformation applied. The index, staged manifest and staged attributes were unchanged throughout the audit.

|Path under scripts/|Index/checkout format|Working format|Expected working SHA256|
|---|---|---|---|
|run_real_world_single_watchdog_distributed_core17legs4b.ps1|588LF|488CRLF+100LF|89b5ceb5742fda1f965b87e2aa6315bbebc3f792be1ee50c9ce9b1e9b2c7711e|
|run_real_world_stackelberg_controller.vbs|5648LF|5506CRLF+142LF|c93420c54ee28a339814ed7eabe407c21cfdceb80e69e0c7bc5c975f8d0933b9|

Both paths now have `-text`. Their older indexed blobs contain normalizedLF, which `-text` correctly preserves during checkout. That differs from the pinned original mixed working bytes. Normalizing the working bytes toLF matches those indexed blobs exactly: no code-content discrepancy was found. Ordinary `git diff` returned empty, consistent with the unchanged working-file stat cache, so another ordinary add may not force the new attribute policy onto these blobs.

The proposed root-only repair leaves all working files, attributes and manifest bytes intact:

```powershell
git add --renormalize -- scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1 scripts/run_real_world_stackelberg_controller.vbs
```

This forces the current `-text` clean policy to store the raw working bytes. Expected raw Git blob IDs, independently confirmed with read-only `git hash-object --path=<path> --stdin`, are recorded in `area_checkout_bytes_verification.json`. After the parent performs this index repair, verify the two new index blobs through the same real smudge path, retain the existing expectedSHA values, and confirm the working files remain unchanged. A follow-up commit can then preserve the original execution bytes for future checkouts.

This reviewer did not stage, commit, write Git objects, run an optimizer/VISSIM, or alter any source/data/attribute/manifest file. Only these JSON/Markdown reports were written. Historical handoff fingerprints remain untouched. The failed original verification remains recorded; the parent's repair has now been independently verified across all130 paths.
