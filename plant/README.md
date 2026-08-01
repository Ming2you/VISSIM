# Strict VISSIM Rollout Plant

This directory contains the controller-independent rollout plant for the
`Ming2you/VISSIM` network.

## Authority

- Controlled Urban Followers: UF1 through UF16, excluding UF11.
- UF5 maps to SC109.
- UF11 maps to SC106 and remains monitoring-only.
- The physical mapping sources are `Urban-Follower.xlsx` and
  `Urban Follower ID.png` in the repository root.

## Verify

Run from this directory:

```powershell
python -B -m unittest discover -s tests -p "test_vissim_strict_*.py"
python -B -m src.vissim_strict.compiler `
  ..\network\real_world_gaepo_modi\modi.inpx `
  --output ..\evaluation\strict_plant\canonical_topology.json
```

The compiler keeps connectors in the raw topology and contracts only safe
serial elements in the hydraulic view. Generated topology files are build
artifacts and are not committed.

## Integration State

The package provides topology compilation, CTM/node conservation, freeway
hybrid coupling, oracle and detector-realistic projection, legacy schema
bridging, and shadow comparison. It does not include a controller and does not
enable VISSIM COM actuation. Candidate rollout integration belongs on the
corrected controller branch.
