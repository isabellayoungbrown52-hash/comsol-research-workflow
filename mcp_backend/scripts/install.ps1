param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if ($RepoRoot -match '[^\x00-\x7F]') {
    throw "MCP runtime path must contain ASCII characters only. Use the top-level scripts/install-mcp.ps1 installer."
}
Push-Location -LiteralPath $RepoRoot
try {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Python venv creation failed. Install Python 3.10+ first." }
    $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    & $VenvPython -m pip install -e ".[test]"
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    & $VenvPython -m server.main doctor
    if ($LASTEXITCODE -ne 0) { throw "Doctor failed." }
    Write-Host "MCP backend installed and doctor completed. Configure the Agent connector using ../references/mcp-interactive.md."
    Write-Host "Keep this repository in place: the editable installation uses this backend, its vendored source, and its examples."
} finally { Pop-Location }
