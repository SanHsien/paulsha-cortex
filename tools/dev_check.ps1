[CmdletBinding()]
param(
    [string]$Distribution = "",
    [switch]$Quick
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "找不到 WSL。Cortex 的權威驗證需要 WSL2/Linux。"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$wslPrefix = @()
if ($Distribution) {
    $wslPrefix = @("-d", $Distribution)
}

$wslRepoOutput = & wsl.exe @wslPrefix --cd $repoRoot -- pwd
$wslExitCode = $LASTEXITCODE
if ($wslExitCode -ne 0 -or -not $wslRepoOutput) {
    throw "無法將 repo 路徑轉換為 WSL 路徑。"
}
$wslRepoRoot = ($wslRepoOutput | Out-String).Trim()

$checkArgs = @("bash", "$wslRepoRoot/tools/dev_check.sh")
if ($Quick) {
    $checkArgs += "--quick"
}

& wsl.exe @wslPrefix -- @checkArgs
if ($LASTEXITCODE -ne 0) {
    throw "開發驗證失敗，exit code: $LASTEXITCODE"
}
