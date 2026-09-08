# COMSOL Research Workflow

**Build, solve, inspect, and deliver complete COMSOL models from natural language.**

![COMSOL Research Workflow](assets/social-preview.png)

This skill lets an AI agent operate a local COMSOL installation through two execution modes. Describe the research problem or desired change; the agent builds or loads the model, configures physics, runs studies, inspects results, and saves an editable `.mph`.

[中文](README.md) · [Skill instructions](SKILL.md) · [Java mode](references/java-batch.md) · [MCP mode](references/mcp-interactive.md)

## What it can do

- Build 2D, 3D, stationary, transient, and parametric models from natural language;
- inspect and modify existing MPH, Java/Method, and MCP sessions;
- configure parameters, geometry, selections, materials, physics, mesh, studies, and solvers;
- run individual cases, parameter tests, and formal sweeps;
- create plots, slices, curves, derived values, and tables inside the COMSOL Results tree;
- export data and images and interpret them using the governing equations, units, and boundary conditions;
- save parameters, physics, solutions, and results in a directly viewable MPH;
- recover compile, connection, solver, save, and postprocessing tasks from the relevant stage.

```text
Understand → Model → Run → Inspect → Iterate → Deliver
```

## Choose a mode on first use

| Mode | How it works | Best for |
|---|---|---|
| Java | The agent writes or edits Java API source, runs `comsolcompile` and `comsolbatch`, and enables COMSOL's native progress window | long calculations, formal sweeps, reproducibility |
| MCP | The agent operates a live COMSOL model and can connect COMSOL Desktop to the same server | interactive modeling, rapid changes, diagnosis, visualization |

Choose once when the first COMSOL operation starts. Continue in natural language or switch modes whenever needed.

## Java mode: native solver progress

Java Run enables COMSOL's official `ModelUtil.showProgress(true)` window by default. It displays the solver hierarchy, progress, convergence, parameters, and iterations during long calculations.

![COMSOL 6.3 native progress window](assets/comsol-official-progress-window.png)

Headless servers and CI can use `-NoProgressWindow`; the batch log remains available.

## MCP mode: model tree and native visualization

MCP sends natural-language operations to a live COMSOL model. The same model can be viewed and edited in COMSOL Desktop, including geometry, materials, physics, mesh, studies, solutions, and results.

The original `gui_quickstart_3d` example has completed an end-to-end COMSOL 6.3 run covering 3D modeling, a stationary solution, a Results tree, image export, and a solved MPH.

![MCP 3D temperature field](mcp_backend/examples/validation/gui_quickstart_3d_comsol63.png)

## One delivery standard for both modes

Whenever a task creates, modifies, or solves a model, the default deliverable is a directly openable `.mph` containing:

- parameters, units, variables, and functions;
- geometry, named selections, and component couplings;
- materials and the properties used;
- physics interfaces, domains, boundaries, and sources;
- mesh, studies, solvers, and the current solution;
- datasets, plot groups, plot features, derived values, and tables.

External CAD, interpolation data, and user functions are organized beside the MPH with stable relative paths when needed.

## Quick start

Requirements: Windows, PowerShell, a licensed COMSOL Multiphysics installation, and an AI agent with local skill support.

1. Clone the repository or download the [latest Release](https://github.com/isabellayoungbrown52-hash/comsol-research-workflow/releases/latest).
2. Place the complete `comsol-research-workflow/` folder in the agent's skills directory.
3. Invoke:

```text
Use $comsol-research-workflow to operate COMSOL for me in natural language.
```

Java installation check:

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Doctor -ComsolRoot "<COMSOL installation>"
```

First-time MCP installation:

```powershell
pwsh -File scripts/install-mcp.ps1
```

## COMSOL versions

The Java runner and MCP quickstart have been validated on COMSOL 6.3. Other releases can be selected with `COMSOL_VERSION` or `COMSOL_ROOT`; keep the compiler, batch executable, JVM/server, and API version consistent within one task.

See the [version guide](references/version-compatibility.md) before migrating an existing model.

## Documentation

- [Java batch and native progress](references/java-batch.md)
- [MCP setup and Desktop visualization](references/mcp-interactive.md)
- [Version compatibility](references/version-compatibility.md)
- [Troubleshooting and recovery](references/troubleshooting-efficiency.md)
- [Physics-aware modeling](references/physics-review.md)
- [Validation records](mcp_backend/examples/validation/README.md)

## Current release

`v1.1.0`: COMSOL native Java progress, a COMSOL 6.3 MCP quickstart, complete MPH delivery, recovery guidance, and multi-version support.

COMSOL Multiphysics is commercial software and a trademark of COMSOL AB. This independent project is not affiliated with COMSOL AB.
