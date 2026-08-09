[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvRoot = Join-Path $repoRoot ".venv"

$candidates = @()
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    $launcher = (Get-Command py.exe).Source
    $candidates += ,@($launcher, "-3.13")
    $candidates += ,@($launcher, "-3")
}
if (Get-Command python.exe -ErrorAction SilentlyContinue) {
    $candidates += ,@((Get-Command python.exe).Source)
}

$pythonCommand = $null
$pythonArgs = @()
foreach ($candidate in $candidates) {
    $candidateCommand = $candidate[0]
    $candidateArgs = @($candidate | Select-Object -Skip 1)
    & $candidateCommand @candidateArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pythonCommand = $candidateCommand
        $pythonArgs = $candidateArgs
        break
    }
}
if (-not $pythonCommand) {
    throw "找不到 Python 3.10+（建議 3.13）。"
}

if (-not (Test-Path (Join-Path $venvRoot "Scripts\python.exe"))) {
    & $pythonCommand @pythonArgs -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "建立 .venv 失敗。"
    }
}

$venvPython = Join-Path $venvRoot "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e "${repoRoot}[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "安裝開發依賴失敗。"
}

Write-Host "Windows 開發環境已就緒：$venvRoot"
Write-Host "驗證：pwsh -File tools/dev_check.ps1"
