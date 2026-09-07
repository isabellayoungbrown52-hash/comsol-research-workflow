# COMSOL Research Workflow

**Model. Solve. Understand.**

![COMSOL Research Workflow: from model and solve to evidence and validation](assets/social-preview.png)

Operate COMSOL from natural language through one skill and two executable backends. Choose Java or MCP once, then let the agent build or modify models, diagnose failures, solve, extract results, and develop physical insight. This is not a read-only workflow guide.

[中文](README.md) · [Skill instructions](SKILL.md) · [Java batch](references/java-batch.md) · [MCP interactive](references/mcp-interactive.md) · [Physics review](references/physics-review.md)

## What it solves

COMSOL agents often fail in one of two ways: they issue API commands without understanding the research question, or they impose so much process that routine modeling barely moves. This skill focuses on useful progress:

- translate a research question into a computable model task;
- inspect and modify existing MPH, Java/Method, or MCP work;
- diagnose geometry, physics, selections, studies, solvers, and expressions;
- run tests and sweeps, export data, and produce scientific figures;
- deliver a directly viewable MPH with the full model tree, current solution, and result tree;
- scale validation to the consequence of the result.

The default loop is:

```text
Understand → Model → Run → Inspect → Iterate → Deliver
```

Full evidence gates are reserved for formal reproduction, promotion, disputed results, and publication-critical outputs.

## Choose a backend on first use

| Mode | How it operates COMSOL | Best for |
|---|---|---|
| Java | the agent writes or edits Java API source and calls the bundled runner, `comsolcompile`, and `comsolbatch` | formal sweeps, long runs, reproducibility |
| MCP | the agent calls the bundled optional local backend for model, geometry, physics, mesh, study, and results tools | exploration, diagnosis, model trees, live iteration |

The skill asks once when the first real COMSOL operation begins. After selection it uses the chosen backend instead of returning generic instructions. Users can switch modes later in natural language.

## Two modes, one complete MPH

Java and MCP are two ways to operate COMSOL, not two different delivery standards. Whenever a task creates, modifies, or solves a model, the default deliverable is a directly openable `.mph`, not merely source code, a live session, CSV files, or images.

The saved model retains the task's parameters and units, geometry, named selections, materials, physics and boundary conditions, mesh, study/solver configuration, current solution, datasets, plot groups and plot features, derived values, and tables. The final save happens after the result tree is built; postprocessing changes trigger another save. Formal results are also verified by reopening the saved MPH read-only.

When external CAD, interpolation data, or user functions cannot be embedded, the skill packages them beside the MPH, uses stable relative paths where possible, and declares the dependencies instead of claiming the file is self-contained.

## Quick start

Actual solves require a licensed local COMSOL Multiphysics installation. Java mode needs a terminal-capable agent; MCP mode needs the bundled connector to be installed and added to the client once.

Clone the repository or download the release ZIP, then place the complete `comsol-research-workflow/` directory in your agent's skills folder. Do not copy only `SKILL.md`. Invoke it in a COMSOL task:

```text
Use $comsol-research-workflow to operate COMSOL for me in natural language.
```

The agent then offers Java mode or MCP mode. Java installation check:

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Doctor -ComsolRoot "<COMSOL installation>"
```

First-time MCP backend installation:

```powershell
pwsh -File scripts/install-mcp.ps1
```

The bundled `heat_sink_3d` example provides an end-to-end three-dimensional heat-transfer check from model construction and meshing to stationary/transient solves and result export. See the [validation record](mcp_backend/examples/validation/README.md).

For formal reproduction or promotion, validate a run directory without opening COMSOL:

```bash
python scripts/validate_run_evidence.py /absolute/path/to/runs/<run_id>
```

The validator checks confinement, file presence, minimum sizes, SHA-256 hashes, artifact roles, and stage evidence. It deliberately does not claim that the model physics is valid.

## Three levels of rigor

| Level | Typical work | Default checks |
|---|---|---|
| Working | modeling, debugging, parameter tests, plotting | current solution, variables, units, main trends |
| Formal reproduction | long runs, formal sweeps, thesis results | stable entrypoint, case identity, logs, raw exports |
| Acceptance/promotion | handoff, disputed results, formal archive | full evidence gates, manifest, hashes, and physics QA |

Routine tasks stay fast; formal results can still be made reproducible when that effort is justified.

## Non-goals

- Bundling COMSOL, commercial licenses, manuals, or official models;
- assuming a specific MCP server, port, or tool name;
- presenting arbitrary code execution as a sandbox;
- promising identical results across COMSOL versions;
- replacing domain physics review with process compliance.

## Status

`v1.0.1`: dual Java/MCP backends, natural-language operation, directly viewable MPH delivery, and a risk-proportional scientific workflow.

COMSOL Multiphysics is commercial software and a trademark of COMSOL AB. This independent project is not affiliated with or endorsed by COMSOL AB.
