[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvRoot = Join-Path $repoRoot ".venv"
$desiredPython = (Get-Content -LiteralPath (Join-Path $repoRoot ".python-version") -Raw).Trim()

$venvPython = Join-Path $venvRoot "Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    & $venvPython -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info < (3, 14) else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "既有 .venv 使用不支援的 Python；請先把 .venv 移出 repo，再重新執行 bootstrap。"
    }
} else {
    $candidates = @()
    if (Get-Command uv.exe -ErrorAction SilentlyContinue) {
        $uvPython = (& uv.exe python find $desiredPython 2>$null | Select-Object -First 1)
        if ($uvPython -and (Test-Path -LiteralPath $uvPython -PathType Leaf)) {
            $candidates += ,@($uvPython)
        }
    }
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $launcher = (Get-Command py.exe).Source
        foreach ($version in @("3.13", "3.12", "3.11", "3.10")) {
            $candidates += ,@($launcher, "-$version")
        }
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
        & $candidateCommand @candidateArgs -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info < (3, 14) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonCommand = $candidateCommand
            $pythonArgs = $candidateArgs
            break
        }
    }
    if (-not $pythonCommand) {
        throw "找不到支援的 Python 3.10-3.13（建議 3.13）。"
    }

    & $pythonCommand @pythonArgs -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "建立 .venv 失敗。"
    }
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e "${repoRoot}[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "安裝開發依賴失敗。"
}

Write-Host "Windows 開發環境已就緒：$venvRoot"
Write-Host "驗證：pwsh -File tools/dev_check.ps1"
