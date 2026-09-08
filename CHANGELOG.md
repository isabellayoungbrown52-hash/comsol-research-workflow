# Changelog

## v1.1.0 — 2026-09-09

- Added a symptom-driven troubleshooting and recovery guide derived from real batch, MCP, solver, export, disk, and plotting failures.
- Added a recovery ladder that resumes from the lowest necessary stage and avoids repeating valid long solves.
- Added explicit COMSOL version selection to the Java runner through `COMSOL_VERSION`/`-ComsolVersion`.
- Documented MPH file direction, Java API and physics-node compatibility, version migration, and the current 6.2/6.3 validation scope.
- Added the formal-figure identity rule: a script that can draw a figure is not automatically the script that produced the accepted figure.
- Enabled COMSOL's native `ModelUtil.showProgress(true)` window by default for Java Run using only the isolated runtime source; headless jobs can explicitly use `-NoProgressWindow`.
- Added and validated the original `gui_quickstart_3d` case through real MCP stdio on COMSOL 6.3, including a Results tree, PNG and solved MPH.
- Clarified that MCP controls the live model while the visual GUI is COMSOL Desktop connected to the same server.

## v1.0.1 — 2026-09-07

- Made a complete, directly viewable MPH the shared default deliverable for both Java and MCP modes.
- Required parameters, materials, physics, mesh, study/solver, current solution, datasets, plots, derived values, and tables to remain visible in the saved COMSOL tree.
- Required the final save to occur after result-tree construction and after later postprocessing changes.
- Added proportionate saved-model verification: same-session node checks for routine work and read-only reload for formal results.
- Clarified packaging and disclosure of external CAD, interpolation data, material data, and user-function dependencies.

## v1.0.0 — 2026-09-07

- Added an explicit first-use Java/MCP mode selector and required the selected backend to perform real COMSOL operations rather than return a workflow guide.
- Added a generic isolated Java runner and an optional bundled local MCP backend with preserved upstream MIT attribution.
- Made the fast working loop the default and reserved full evidence gates for formal reproduction, promotion, or disputed results.
- Reframed validation as risk-proportional support for modeling progress rather than a universal precondition.
- Established task-aware routing across Java batch, MCP interactive, read-only, postprocess, and hybrid workflows.
- Added the ten-stage evidence path from ReadOnly through Promote.
- Added physics-aware review for interface choice, transport, charge, porous media, fluxes, units, and claim boundaries.
- Added a dependency-free run-manifest validator with path-confinement and SHA-256 checks.
- Added bilingual release documentation and security guidance.
