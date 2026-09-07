[CmdletBinding()]
param(
    [ValidateSet('Doctor', 'Compile', 'Run')]
    [string]$Stage = 'Doctor',
    [string]$JavaSource,
    [string]$ComsolRoot = $env:COMSOL_ROOT,
    [string]$RunRoot = '',
    [switch]$ConfirmSolve
)

$ErrorActionPreference = 'Stop'

function Find-ComsolRoot {
    param([string]$Configured)
    if ($Configured) {
        return [IO.Path]::GetFullPath($Configured)
    }
    $base = Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'COMSOL'
    if (Test-Path -LiteralPath $base -PathType Container) {
        $found = Get-ChildItem -LiteralPath $base -Directory |
            Sort-Object LastWriteTimeUtc -Descending |
            ForEach-Object { Join-Path $_.FullName 'Multiphysics' } |
            Where-Object { Test-Path -LiteralPath (Join-Path $_ 'bin\win64\comsolbatch.exe') -PathType Leaf } |
            Select-Object -First 1
        if ($found) { return $found }
    }
    throw 'COMSOL was not found. Set COMSOL_ROOT to the Multiphysics installation directory.'
}

$root = Find-ComsolRoot $ComsolRoot
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
    solve_called = $true
    note = 'Inspect the COMSOL log and expected model/data outputs before claiming solve success.'
} | ConvertTo-Json

if ($batchExit -ne 0) { exit $batchExit }
