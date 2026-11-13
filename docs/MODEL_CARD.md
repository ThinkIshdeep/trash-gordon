# Model and simulator card — Trash Gordon

## Intended use

A known-map indoor robot simulator coordinating destinations, navigation and explicit dustbin mechanism states.

## Implemented methods

- Offline WebGL scene and software perspective-rendering fallback
- A* routing, obstacle replanning and a visible speaker marker
- Typed commands and optional browser speech recognition
- Lid, fill, bag-seal/removal/inflation and cartridge state logic
- Battery policy, docking states and motion interlocks

Some projects use deterministic simulators and rules rather than trained neural models. Those distinctions are retained in this card and the source.

## Evaluation

See `docs/EXPERIMENTS.md` and the machine-readable reports. No pretrained foundation-model weights or real-world efficacy certification are included. Parameters, splits and synthetic generators are visible in source.

## Limitations

Known-map A* navigation and simulated lid/bag/docking logic. No SLAM, physical mechanism validation or telepathic speaker localization.

## Extensions not implemented in this release

- SLAM, tracked speakers and physical sensor integration
- Hardware validation of sealing, inflation and docking mechanisms
