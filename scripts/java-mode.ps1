[CmdletBinding()]
param(
    [ValidateSet('Doctor', 'Compile', 'Run')]
    [string]$Stage = 'Doctor',
    [string]$JavaSource,
    [string]$ComsolRoot = $env:COMSOL_ROOT,
    [string]$ComsolVersion = $env:COMSOL_VERSION,
    [string]$RunRoot = '',
    [switch]$ConfirmSolve,
    [switch]$NoProgressWindow
)

$ErrorActionPreference = 'Stop'

function Find-ComsolRoot {
    param([string]$Configured, [string]$RequestedVersion)
    if ($Configured) {
        return [IO.Path]::GetFullPath($Configured)
    }
    $base = Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'COMSOL'
    if (Test-Path -LiteralPath $base -PathType Container) {
        $installations = @(Get-ChildItem -LiteralPath $base -Directory | ForEach-Object {
            $candidate = Join-Path $_.FullName 'Multiphysics'
            if (Test-Path -LiteralPath (Join-Path $candidate 'bin\win64\comsolbatch.exe') -PathType Leaf) {
                [pscustomobject]@{ Root = $candidate; Folder = $_.Name; Digits = [regex]::Replace($_.Name, '\D', '') }
            }
        })
        if ($RequestedVersion) {
            $wanted = [regex]::Replace($RequestedVersion, '\D', '')
            $matched = @($installations | Where-Object { $_.Digits -eq $wanted })
            if ($matched.Count -eq 1) { return $matched[0].Root }
            $available = ($installations.Folder -join ', ')
            throw "COMSOL version $RequestedVersion was not found under $base. Available installations: $available"
        }
        $found = $installations | Sort-Object @{Expression={ if ($_.Digits) { [int]$_.Digits } else { 0 } }; Descending=$true} | Select-Object -First 1
        if ($found) { return $found.Root }
    }
    throw 'COMSOL was not found. Set COMSOL_ROOT to the Multiphysics installation directory or COMSOL_VERSION to an installed release.'
}

$root = Find-ComsolRoot $ComsolRoot $ComsolVersion
$compiler = Join-Path $root 'bin\win64\comsolcompile.exe'
$batch = Join-Path $root 'bin\win64\comsolbatch.exe'
foreach ($required in @($compiler, $batch)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing COMSOL executable: $required"
    }
}

if (-not $RunRoot) {
    $publicRoot = [Environment]::GetEnvironmentVariable('PUBLIC')
    if (-not $publicRoot) { throw 'PUBLIC is unavailable; provide an ASCII-only -RunRoot.' }
    $RunRoot = Join-Path $publicRoot 'COMSOLResearchWorkflow\JavaRuns'
}
$RunRoot = [IO.Path]::GetFullPath($RunRoot)
if ($RunRoot -match '[^\x00-\x7F]') {
    throw 'RunRoot must contain ASCII characters only because COMSOL Java tools may fail on non-ASCII runtime paths.'
}

if ($Stage -eq 'Doctor') {
    [ordered]@{
        status = 'PASS'
        comsol_root = $root
        requested_version = $ComsolVersion
        selected_installation = (Split-Path -Leaf (Split-Path -Parent $root))
        compiler = $compiler
        batch = $batch
        solve_called = $false
    } | ConvertTo-Json
    return
}

if (-not $JavaSource) { throw 'JavaSource is required for Compile or Run.' }
$source = (Resolve-Path -LiteralPath $JavaSource).Path
if ([IO.Path]::GetExtension($source) -ne '.java') { throw 'JavaSource must be a .java file.' }

$runId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '_' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runDir = Join-Path $RunRoot $runId
$runtime = Join-Path $runDir 'runtime'
$logs = Join-Path $runDir 'logs'
$prefs = Join-Path $runDir 'prefs'
$temp = Join-Path $runDir 'tmp'
foreach ($directory in @($runtime, $logs, $prefs, $temp)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

$runtimeJava = Join-Path $runtime ([IO.Path]::GetFileName($source))
Copy-Item -LiteralPath $source -Destination $runtimeJava
$officialProgressRequested = $false
if ($Stage -eq 'Run' -and -not $NoProgressWindow) {
    $javaText = [IO.File]::ReadAllText($runtimeJava)
    if ($javaText -notmatch 'ModelUtil\.showProgress\s*\(\s*true\s*\)') {
        $init = [regex]::Match(
            $javaText,
            'ModelUtil\.initStandalone\s*\(\s*true(?:\s*,\s*"(?:swing|swt)")?\s*\)\s*;'
        )
        if (-not $init.Success) {
            throw 'Official COMSOL progress requires ModelUtil.initStandalone(true) in JavaSource. Add it, or use -NoProgressWindow only for a headless run.'
        }
        $insertion = [Environment]::NewLine + '    ModelUtil.showProgress(true);'
        $javaText = $javaText.Insert($init.Index + $init.Length, $insertion)
        [IO.File]::WriteAllText($runtimeJava, $javaText, [Text.UTF8Encoding]::new($false))
    }
    $officialProgressRequested = $true
}
$compileOut = Join-Path $logs 'compile.stdout.log'
$compileErr = Join-Path $logs 'compile.stderr.log'
& $compiler $runtimeJava 1> $compileOut 2> $compileErr
$compileExit = $LASTEXITCODE
$runtimeClass = [IO.Path]::ChangeExtension($runtimeJava, '.class')
if ($compileExit -ne 0 -or -not (Test-Path -LiteralPath $runtimeClass -PathType Leaf)) {
    throw "COMSOL compile failed (exit=$compileExit). See $compileOut and $compileErr"
}

if ($Stage -eq 'Compile') {
    [ordered]@{
        status = 'PASS'
        stage = 'Compile'
        run_id = $runId
        run_directory = $runDir
        class_file = $runtimeClass
        solve_called = $false
    } | ConvertTo-Json
    return
}

if (-not $ConfirmSolve) {
    throw 'Run requires -ConfirmSolve after the user explicitly authorizes this solve.'
}
foreach ($name in @('comsol.prefs', 'comsolserver.prefs')) {
    [IO.File]::WriteAllText((Join-Path $prefs $name), 'security.external.filepermission=full', [Text.Encoding]::ASCII)
}
$batchLog = Join-Path $logs 'batch.log'
$batchOut = Join-Path $logs 'batch.stdout.log'
$batchErr = Join-Path $logs 'batch.stderr.log'
& $batch '-prefsdir' $prefs '-tmpdir' $temp '-batchlog' $batchLog `
    '-batchlogout' '-inputfile' $runtimeClass 1> $batchOut 2> $batchErr
$batchExit = $LASTEXITCODE

[ordered]@{
    status = $(if ($batchExit -eq 0) { 'PROCESS_EXITED_ZERO' } else { 'PROCESS_FAILED' })
    stage = 'Run'
    run_id = $runId
    run_directory = $runDir
    batch_exit_code = $batchExit
    batch_log = $batchLog
    stdout_log = $batchOut
    stderr_log = $batchErr
    official_progress_requested = $officialProgressRequested
    solve_called = $true
    note = 'Inspect the COMSOL log and expected model/data outputs before claiming solve success.'
} | ConvertTo-Json

if ($batchExit -ne 0) { exit $batchExit }
