#!/usr/bin/env python3
"""Validate a COMSOL run manifest without opening COMSOL.

Checks evidence structure, artifact confinement, sizes, and SHA-256 hashes.
It deliberately does not claim that model physics or numerics are valid.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


STAGES = [
    "ReadOnly", "StaticOnly", "Compile", "Smoke", "Solve", "Save",
    "Export", "Canonicalize", "QA", "Promote",
]
REQUIRED_EVIDENCE = {
    "Solve": ["solve_authorized", "study_complete", "solution_identity_checked"],
    "QA": ["log_scan_pass", "model_identity_match", "units_checked",
           "physics_qa_pass", "scientific_scope_checked"],
}
REQUIRED_ROLES = {
    "Save": {"model"},
    "Export": {"model", "raw_data"},
    "QA": {"model", "raw_data", "validation"},
    "Promote": {"model", "raw_data", "validation", "source"},
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def at_least(stage: str, threshold: str) -> bool:
    return STAGES.index(stage) >= STAGES.index(threshold)


def confined_path(run_dir: Path, relative: Any) -> tuple[Path | None, str | None]:
    if not isinstance(relative, str) or not relative.strip():
        return None, "artifact path must be a non-empty string"
    raw = Path(relative)
    if raw.is_absolute():
        return None, f"artifact path must be relative: {relative}"
    candidate = (run_dir / raw).resolve()
    try:
        candidate.relative_to(run_dir)
    except ValueError:
        return None, f"artifact escapes run directory: {relative}"
    return candidate, None


def validate(run_dir: Path, manifest_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[dict[str, Any]] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be a JSON object")

    stage = payload.get("stage")
    if stage not in STAGES:
        errors.append(f"stage must be one of {STAGES}; got {stage!r}")
    if not isinstance(payload.get("run_id"), str) or not payload["run_id"].strip():
        errors.append("run_id must be a non-empty string")
    if payload.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if payload.get("status") not in {"PASS", "PARTIAL", "FAIL", "BLOCKED"}:
        errors.append("status must be PASS, PARTIAL, FAIL, or BLOCKED")
    identity = payload.get("model_identity")
    if not isinstance(identity, dict) or not identity.get("entry"):
        errors.append("model_identity.entry is required")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be a list")
        artifacts = []
    roles: set[str] = set()
    seen_paths: set[str] = set()
    for index, item in enumerate(artifacts):
        prefix = f"artifacts[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        role = item.get("role")
        if not isinstance(role, str) or not role:
            errors.append(f"{prefix}.role is required")
        else:
            roles.add(role)
        path, path_error = confined_path(run_dir, item.get("path"))
        if path_error:
            errors.append(f"{prefix}: {path_error}")
            continue
        assert path is not None
        key = str(path).casefold()
        if key in seen_paths:
            errors.append(f"duplicate artifact path: {item.get('path')}")
        seen_paths.add(key)
        if not path.is_file():
            errors.append(f"artifact missing: {item.get('path')}")
            continue
        size = path.stat().st_size
        minimum = item.get("bytes_min", 1)
        if not isinstance(minimum, int) or minimum < 1:
            errors.append(f"{prefix}.bytes_min must be a positive integer")
            minimum = 1
        if size < minimum:
            errors.append(f"artifact too small: {item.get('path')} ({size} < {minimum})")
        expected = item.get("sha256")
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            errors.append(f"{prefix}.sha256 must be a 64-character hexadecimal digest")
            actual = None
        else:
            actual = sha256_file(path)
            if actual != expected.upper():
                errors.append(f"sha256 mismatch: {item.get('path')}")
        checked.append({"role": role, "path": item.get("path"),
                        "bytes": size, "sha256": actual})

    if stage in STAGES:
        for threshold, required in REQUIRED_ROLES.items():
            if at_least(stage, threshold):
                missing = required - roles
                if missing:
                    errors.append(f"stage {stage} requires artifact role(s): "
                                  f"{', '.join(sorted(missing))}")
        evidence = payload.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
            if at_least(stage, "Solve"):
                errors.append("evidence must be an object from Solve onward")
        for threshold, keys in REQUIRED_EVIDENCE.items():
            if at_least(stage, threshold):
                for key_name in keys:
                    if evidence.get(key_name) is not True:
                        errors.append(f"stage {stage} requires evidence.{key_name}=true")
        if at_least(stage, "QA") and payload.get("status") != "PASS":
            errors.append(f"stage {stage} requires declared status PASS")
    if payload.get("status") == "PASS" and errors:
        warnings.append("manifest says PASS but evidence validation failed")
    return {
        "validator": "comsol-research-workflow/evidence-check-1.0",
        "manifest": str(manifest_path), "run_dir": str(run_dir),
        "declared_stage": stage, "declared_status": payload.get("status"),
        "overall": "PASS" if not errors else "FAIL",
        "checked_artifacts": checked, "errors": errors, "warnings": warnings,
        "note": "Structural evidence check only; physics and numerical validity require domain QA.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="COMSOL run directory")
    parser.add_argument("--manifest", type=Path,
                        default=Path("report/run_manifest.json"),
                        help="manifest relative to run_dir")
    parser.add_argument("--json-out", type=Path, help="optional output report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_dir():
        print(json.dumps({"overall": "ERROR", "error": "run_dir is not a directory"}))
        return 2
    manifest, error = confined_path(run_dir, str(args.manifest))
    if error or manifest is None:
        print(json.dumps({"overall": "ERROR", "error": error}))
        return 2
    output: Path | None = None
    if args.json_out:
        output, output_error = confined_path(run_dir, str(args.json_out))
        if output_error or output is None:
            print(json.dumps({"overall": "ERROR", "error": output_error},
                             ensure_ascii=False))
            return 2
        if output == manifest:
            print(json.dumps({"overall": "ERROR",
                              "error": "json-out must not overwrite the input manifest"}))
            return 2
    try:
        report = validate(run_dir, manifest)
    except ValueError as exc:
        print(json.dumps({"overall": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
