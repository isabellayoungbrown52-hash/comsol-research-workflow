[CmdletBinding()]
param(
    [string]$Python = 'python',
    [string]$InstallRoot = '',
    [switch]$ForceUpdate
)

$ErrorActionPreference = 'Stop'
$skillRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $skillRoot 'mcp_backend'
if (-not $InstallRoot) {
    $publicRoot = [Environment]::GetEnvironmentVariable('PUBLIC')
    if (-not $publicRoot) { throw 'PUBLIC is unavailable; provide an ASCII-only -InstallRoot.' }
    $InstallRoot = Join-Path $publicRoot 'COMSOLResearchWorkflow\MCP'
}
$destination = [IO.Path]::GetFullPath($InstallRoot)
if ($destination -match '[^\x00-\x7F]') {
    throw 'InstallRoot must contain ASCII characters only because COMSOL/JPype may truncate non-ASCII JVM paths.'
}
if (Test-Path -LiteralPath $destination) {
    if (-not $ForceUpdate) {
        throw "MCP backend already exists: $destination. Review it first, then rerun with -ForceUpdate."
    }
    $resolved = (Resolve-Path -LiteralPath $destination).Path
    if ($resolved -ne $destination -or $destination.Length -lt 12) {
        throw "Refusing to replace unexpected destination: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $destination -Recurse -Force

& (Join-Path $destination 'scripts\install.ps1') -Python $Python
if ($LASTEXITCODE -ne 0) { throw "MCP backend installation failed with exit code $LASTEXITCODE" }

$pythonExe = Join-Path $destination '.venv\Scripts\python.exe'
[ordered]@{
    status = 'PASS'
    backend_directory = $destination
    connector = [ordered]@{
        command = $pythonExe
        args = @('-m', 'server.main', 'serve', '--transport', 'stdio')
        cwd = $destination
    }
    next_step = 'Add the connector to the Agent, refresh tools, then call comsol_doctor.'
} | ConvertTo-Json -Depth 4
