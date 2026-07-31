# Real-world modi player definition

Source: `network\real_world_gaepo_modi\modi_eval_sanitized.inpx`

## Object inventory

- Road links: 420
- Connectors: 702
- Signal controllers / groups / heads: 32 / 352 / 475
- Vehicle inputs: 31
- Desired-speed decisions: 37
- Queue counters / data collection points: 90 / 198

## Freeway geometry

- Freeway mainline links: `[2, 26]`
- Freeway demand/input links: `[26, 74]`
- Freeway-touching road links: `[31, 32, 68, 69, 70, 74]`

Top north-south long-link candidates:

- link 26: length 8029.342 m, lanes 4, x=[-5751487.704, -5748318.994], y=[-972546.408, -965388.537]
- link 2: length 8038.58 m, lanes 4, x=[-5751462.383, -5748257.511], y=[-972545.37, -965397.807]
- link 39: length 1253.965 m, lanes 4, x=[-5749946.651, -5749548.259], y=[-969893.409, -968762.759]
- link 40: length 1261.484 m, lanes 4, x=[-5749927.424, -5749531.793], y=[-969892.813, -968755.236]

## Player draft

- Leader: whole-network TTT/stopped objective, with freeway/urban split from player definition.
- Freeway follower: state links `[2, 26]`, demand inputs `[26, 74]`, current DSD actuators `[36, 37, 38, 39, 40, 41, 42]`.
- Urban follower: all non-freeway links as urban state; 32 signal controllers, interface subset `[1]`.

## Immediate risks

- Freeway VSL coverage is asymmetric because existing mainline desired-speed decisions are present on link 26 but not link 2.
- All signal controllers are fixed-time VISSIG controllers; COM control must be proven before P-Stack can change phases/offsets.
- Real-world demand is already encoded in vehicle inputs, so synthetic uniform volume overrides should not be used.

## Recommended sequence

1. Run load/short-step smoke with original demand.
2. Run no-control baseline with long warm-up and real-world state split.
3. Audit freeway VSL authority on links 2 and 26; add missing link-2 VSL decisions only after load smoke is stable.
4. Audit VISSIG signal-group COM control on a small freeway-interface controller subset.
5. Only then rebuild the P-Stack adapter around these players.
