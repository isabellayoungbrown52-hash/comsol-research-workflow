param(
    [ValidateSet("stdio", "streamable-http", "sse")][string]$Transport = "stdio",
    [int]$Port = 8765,
    [string]$BindHost = "127.0.0.1",
    [string]$PublicUrl = "",
    [switch]$CopyHeader,
    [switch]$PrepareTokenOnly
)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if ($Transport -eq "stdio" -and ($CopyHeader -or $PrepareTokenOnly)) {
    throw "Token options apply only to streamable-http or sse."
}

function Assert-Token([string]$Value) {
    if ($Value.Length -lt 32 -or $Value -match '\s' -or
        ($Value.ToCharArray() | Sort-Object -Unique).Count -lt 8) {
        throw "Invalid token: use at least 32 random characters, without 'Bearer ' or whitespace. Existing credentials were not replaced."
    }
}

if ($Transport -ne "stdio") {
    $TokenFile = Join-Path $RepoRoot ".mcp-token"
    if (Test-Path -LiteralPath $TokenFile) {
        $SavedToken = [System.IO.File]::ReadAllText($TokenFile).Trim()
        Assert-Token $SavedToken
        if ($env:COMSOL_MCP_TOKEN -and $env:COMSOL_MCP_TOKEN -cne $SavedToken) {
            throw "COMSOL_MCP_TOKEN differs from .mcp-token. No token was changed. To reuse the saved token, remove only this window's environment variable and retry."
        }
    } else {
        # Preserve an existing connector credential during migration.
        $SavedToken = $env:COMSOL_MCP_TOKEN
        if (-not $SavedToken) {
            $RandomBytes = New-Object byte[] 32
            $RandomGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
            try { $RandomGenerator.GetBytes($RandomBytes) }
            finally { $RandomGenerator.Dispose() }
            $SavedToken = [Convert]::ToBase64String($RandomBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        }
        Assert-Token $SavedToken
        # CreateNew prevents an accidental overwrite during concurrent setup.
        $TokenStream = [System.IO.File]::Open($TokenFile, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try {
            $TokenBytes = [System.Text.Encoding]::UTF8.GetBytes($SavedToken)
            $TokenStream.Write($TokenBytes, 0, $TokenBytes.Length)
        } finally { $TokenStream.Dispose() }
    }
    $env:COMSOL_MCP_TOKEN = $SavedToken
    if ($CopyHeader) {
        Set-Clipboard -Value ("Bearer " + $SavedToken)
        Write-Host "Authorization header copied. Paste it into your local connector; do not share it in chat."
    }
    if ($PrepareTokenOnly) {
        Write-Host "Local token prepared. Future starts will reuse it; no MCP service was started."
        return
    }
}
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) { throw "Run scripts/install.ps1 first." }
$LaunchArgs = @("-m", "server.main", "serve", "--transport", $Transport, "--port", "$Port", "--host", $BindHost)
if ($PublicUrl) { $LaunchArgs += @("--public-url", $PublicUrl) }
Push-Location -LiteralPath $RepoRoot
try {
    & $VenvPython @LaunchArgs
    if ($LASTEXITCODE -ne 0) { throw "MCP exited with code $LASTEXITCODE" }
} finally { Pop-Location }
