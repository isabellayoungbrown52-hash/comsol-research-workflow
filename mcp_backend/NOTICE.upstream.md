# Third-party notices

`vendor/installed-mcp/` is an allowlisted snapshot of the installed source of [COMSOL_Multiphysics_MCP](https://github.com/wjc9011/COMSOL_Multiphysics_MCP). It is MIT licensed, Copyright (c) 2025; its original LICENSE is included in that directory. Snapshot date: 2026-09-05. The installed directory did not contain Git metadata, so no upstream revision is asserted. `SNAPSHOT.json` records actual file bytes and SHA-256 digests. Local modifications may differ from current upstream.

The upstream source snapshot is preserved unchanged for provenance. The new `server/` adapter applies session and execution behavior at runtime. Do not launch the unmodified vendor entry point when expecting the adapter's session protection, HTTP authentication or case tools. Some upstream high-level physics shortcuts are incomplete; consult the version-specific API and this package's tested patterns.

The dependency packages MCP Python SDK, MPh, JPype and NumPy are installed from their publishers and retain their respective licenses; their environments/binaries are not bundled here. Optional PDF indexing dependencies are not needed for normal modeling and are not downloaded by default.

COMSOL Multiphysics is a commercial product and trademark of COMSOL AB. This project is independent and is not endorsed by COMSOL AB. A suitable installed COMSOL license is required. Tutorial identifiers and relative paths refer to the user's licensed Application Library; commercial MPH, PDF, CAD and documentation files are not redistributed.

Original teaching source under `examples/original/` and sanitized verification records under `examples/validation/` were prepared for this package. Personal scientific models, unpublished research data and conversation attachments are excluded.
