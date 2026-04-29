param(
    [switch]$SkipFrontend,
    [switch]$NoClean
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageScript = Join-Path $ScriptDir "package.py"

$ArgsList = @($PackageScript)
if ($SkipFrontend) {
    $ArgsList += "--skip-frontend"
}
if ($NoClean) {
    $ArgsList += "--no-clean"
}

python @ArgsList
