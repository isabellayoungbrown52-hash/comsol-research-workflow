# Contributing

Contributions are welcome when they improve reproducibility, evidence quality, physical correctness, or compatibility without weakening the Solve authorization boundary.

## Good contributions

- a minimal reproducible fix for a COMSOL Java or MCP workflow failure;
- a version-specific compatibility note backed by a real log or documented API behavior;
- a new physics-aware QA check with a clear failure condition;
- a safer manifest rule or validator test case;
- clearer bilingual documentation that preserves the scientific meaning.

Do not submit COMSOL binaries, license files, commercial documentation, unpublished datasets, proprietary MPH models, credentials, or machine-specific absolute paths.

## Pull-request checklist

1. Explain the failure mode or user need.
2. State which workflow stage is affected.
3. Include a small, non-proprietary reproducer when code changes.
4. Run the skill validator and any relevant script checks.
5. Confirm that no COMSOL solve starts implicitly.
6. Confirm that process success is not presented as physics validation.

For security-sensitive findings, follow [SECURITY.md](SECURITY.md) instead of publishing exploit details.
