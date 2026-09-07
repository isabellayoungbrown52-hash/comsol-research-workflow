# Security

## MCP and arbitrary code execution

Some COMSOL MCP servers expose `model_code`, Python execution, Java API execution, or equivalent tools. Treat these as local arbitrary code execution, not as a sandbox.

- Use only a trusted local server.
- Restrict file access to the declared workspace and run directory.
- Never place tokens, passwords, private keys, unpublished data, or browser profiles in prompts or transcripts.
- Inspect generated code before execution when it can access the filesystem, network, processes, or environment variables.
- Do not terminate COMSOL processes until their owner, active Study, and output directory are identified.

## Reporting a vulnerability

Use the repository's private vulnerability-reporting channel when it is enabled. If no private channel is available, open a minimal public issue asking the maintainer for private contact, without including exploit details, unpublished model data, credentials, or sensitive local paths.

## Scope

This repository contains workflow instructions and a local evidence validator. It does not bundle a COMSOL MCP server, COMSOL binaries, licenses, or commercial documentation.
