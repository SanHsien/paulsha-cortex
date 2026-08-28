[CmdletBinding()]
param(
    [switch]$Quick
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "找不到 .venv；請先執行 pwsh -File tools/bootstrap_dev.ps1。"
}

Push-Location $repoRoot
try {
    & git diff --check
    if ($LASTEXITCODE -ne 0) { throw "git diff --check 失敗。" }

    & $venvPython -m compileall -q paulsha_cortex tests
    if ($LASTEXITCODE -ne 0) { throw "Python bytecode compile 失敗。" }

    if ($Quick) {
        & $venvPython -m pytest -q `
            tests/test_windows_compatibility.py `
            tests/test_windows_service.py `
            tests/test_process_wrapper.py `
            tests/test_monitor_transport.py
    } else {
        & $venvPython -m pytest tests -q
    }
    if ($LASTEXITCODE -ne 0) { throw "pytest 失敗。" }

    if (-not $Quick) {
        $buildRoot = Join-Path ([IO.Path]::GetTempPath()) ("paulsha-cortex-build-" + [guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $buildRoot | Out-Null
        try {
            & $venvPython -m build --outdir $buildRoot
            if ($LASTEXITCODE -ne 0) { throw "distribution build 失敗。" }
            $distributions = @(Get-ChildItem -LiteralPath $buildRoot -File | ForEach-Object { $_.FullName })
            & $venvPython -m twine check --strict @distributions
            if ($LASTEXITCODE -ne 0) { throw "twine check 失敗。" }
        } finally {
            $resolvedBuildRoot = (Resolve-Path $buildRoot).Path
            $resolvedTempRoot = (Resolve-Path ([IO.Path]::GetTempPath())).Path
            if ($resolvedBuildRoot.StartsWith($resolvedTempRoot, [StringComparison]::OrdinalIgnoreCase)) {
                Remove-Item -LiteralPath $resolvedBuildRoot -Recurse -Force
            }
        }
    }
} finally {
    Pop-Location
}

Write-Host "Windows 驗證完成。"
