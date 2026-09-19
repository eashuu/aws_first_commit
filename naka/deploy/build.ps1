# Build the Lambda deployment zip for Naka. Windows/PowerShell twin of
# build.sh -- read that file's header comment for the full "why" behind
# the --platform/--python-version flags and the flat-zip-root layout;
# this file only repeats what differs mechanically on Windows.
$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Here
$BuildDir = Join-Path $Root "build\pkg"
$DistDir = Join-Path $Root "dist"
$ZipPath = Join-Path $DistDir "naka.zip"

if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

# uv over pip when available -- see build.sh's long comment for the full
# reason. Short version: pip's --platform only filters wheel tags, it does
# NOT evaluate PEP 508 environment markers for the target. `mcp` requires
# `pywin32; sys_platform == "win32"`, so on a Windows host pip tries to
# satisfy pywin32 for aarch64, fails, and silently BACKTRACKS to
# strands-agents 1.1.0 -- which has no `strands.vended_interventions`, so
# the Lambda dies at import. uv's --python-platform gets this right.
Write-Host "==> installing deps (arm64 / manylinux2014, Python 3.12 target) into $BuildDir"
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    uv pip install -r (Join-Path $Root "requirements.txt") `
      --python-platform aarch64-manylinux2014 `
      --python-version 3.12 `
      --target $BuildDir `
      --no-installer-metadata
    if ($LASTEXITCODE -ne 0) { throw "uv pip install failed" }
} else {
    Write-Host "    uv not found -- falling back to pip. On Windows this can"
    Write-Host "    silently resolve strands-agents 1.1.0; the check below catches it."
    pip install -r (Join-Path $Root "requirements.txt") `
      --platform manylinux2014_aarch64 `
      --only-binary=:all: `
      --python-version 3.12 `
      --target $BuildDir
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
}

# Fail the build rather than ship a package that cannot import.
if (-not (Test-Path (Join-Path $BuildDir "strands\vended_interventions"))) {
    throw "strands.vended_interventions missing from the build -- resolved strands-agents is too old (needs >= 1.44)."
}

Write-Host "==> copying project source into the package root"
Copy-Item (Join-Path $Root "*.py") $BuildDir
Copy-Item (Join-Path $Root "agent.cedar") $BuildDir
Copy-Item (Join-Path $Root "fixtures") (Join-Path $BuildDir "fixtures") -Recurse
Copy-Item (Join-Path $Root "web") (Join-Path $BuildDir "web") -Recurse

# Drop bytecode caches (this repo already has a __pycache__/ next to the
# source .py files) -- pure zip bloat, Lambda compiles fresh on cold start.
Get-ChildItem $BuildDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $BuildDir -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "==> zipping -> $ZipPath"
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path (Join-Path $BuildDir "*") -DestinationPath $ZipPath -CompressionLevel Optimal

$SizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host "==> built $ZipPath ($SizeMB MB)"
Write-Host "    Lambda's direct zip-upload ceiling is 50 MB (zipped); 250 MB"
Write-Host "    unzipped across the function + any layers. If this zip is"
Write-Host "    getting close to either, that's the moment to stop bundling"
Write-Host "    strands-agents here and rely on the prebuilt layer instead"
Write-Host "    (see requirements.txt's comment on that tradeoff)."
