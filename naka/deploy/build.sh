#!/usr/bin/env bash
# Build the Lambda deployment zip for Naka (both functions share one zip --
# app_agent.py and app_control.py each only exercise the imports their own
# handler needs, so there's no benefit to two separate packages and it
# would double the pip-install time).
#
# Packaging layout matters: everything lands FLAT at the zip root (the
# pip --target output merged with the project's own .py files, agent.cedar,
# fixtures/ and web/) because Lambda imports both `app_agent`/`app_control`
# *and* their third-party deps (`strands`, `cedarpy`, `openpyxl`, ...) off
# the same sys.path entry (/var/task). A src/ subfolder would break every
# `import strands`, `import cedarpy`, etc.
#
# --platform manylinux2014_aarch64 --only-binary=:all: (PRD §7): the
# Lambda is arm64 (Graviton, chosen for the usual price/perf reason a
# hackathon doesn't need to defend further), but this is very likely being
# built on an x86_64 or non-Linux dev machine. Without --platform, pip
# resolves/installs wheels for the BUILD machine, which then fail to
# import at all on the arm64 runtime -- a working local `python app.py`
# and a broken Lambda from the exact same commit. --only-binary=:all:
# makes pip fail loudly if no prebuilt wheel exists instead of silently
# attempting (and, without a C toolchain, usually failing) a source build.
# --python-version 3.12 is added on top of the PRD's literal command
# because pip's cross-platform installs also need to be told the target
# CPython ABI tag explicitly when the machine running pip isn't itself on
# 3.12 (a very likely case on a Windows dev box) -- without it, pip may
# look for cp<host-version> wheels under the aarch64 platform and find
# nothing for cedarpy.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
BUILD_DIR="$ROOT/build/pkg"
DIST_DIR="$ROOT/dist"
ZIP_PATH="$DIST_DIR/naka.zip"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# uv over pip, when it's available, for one specific reason: pip's
# --platform only changes which WHEEL TAGS it will accept, not how it
# evaluates PEP 508 environment markers. Those are always evaluated
# against the machine running pip. `mcp` (a strands-agents dependency)
# declares `pywin32>=310; sys_platform == "win32"`, so building on Windows
# makes pip believe it must install pywin32 -- for which no
# manylinux_aarch64 wheel exists, so --only-binary=:all: turns it into a
# resolution failure. pip does not report that as an error: it BACKTRACKS,
# silently settling on strands-agents 1.1.0 (the last version whose mcp
# range predates that marker). 1.1.0 has no `strands.vended_interventions`,
# so the zip builds and uploads fine and the Lambda dies at import with
# `No module named 'strands.vended_interventions'`.
#
# uv's --python-platform evaluates markers for the TARGET, which is the
# actual requirement here, and resolves to current strands-agents.
echo "==> installing deps (arm64 / manylinux2014, Python 3.12 target) into $BUILD_DIR"
if command -v uv >/dev/null 2>&1; then
  uv pip install -r "$ROOT/requirements.txt" \
    --python-platform aarch64-manylinux2014 \
    --python-version 3.12 \
    --target "$BUILD_DIR" \
    --no-installer-metadata
else
  echo "    uv not found -- falling back to pip. If this is a Windows or"
  echo "    macOS host, CHECK the resolved strands-agents version before"
  echo "    deploying (see the comment above); pip can silently pick 1.1.0."
  pip install -r "$ROOT/requirements.txt" \
    --platform manylinux2014_aarch64 \
    --only-binary=:all: \
    --python-version 3.12 \
    --target "$BUILD_DIR"
fi

# Fail the build rather than ship a package that cannot import. This is the
# exact failure the comment above describes, and it is invisible until the
# function runs, so it is checked here instead.
if [ ! -d "$BUILD_DIR/strands/vended_interventions" ]; then
  echo "ERROR: strands.vended_interventions missing from the build." >&2
  echo "       Resolved strands-agents is too old (needs >= 1.44)." >&2
  exit 1
fi

echo "==> copying project source into the package root"
cp "$ROOT"/*.py "$BUILD_DIR"/
cp "$ROOT/agent.cedar" "$BUILD_DIR"/
cp -r "$ROOT/fixtures" "$BUILD_DIR"/fixtures
cp -r "$ROOT/web" "$BUILD_DIR"/web

# Drop bytecode caches picked up by the `cp -r` above (this repo already
# has a __pycache__/ next to the source .py files) -- they add nothing at
# runtime (Lambda compiles fresh on cold start) and are pure zip bloat.
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.pyc" -delete

echo "==> zipping -> $ZIP_PATH"
rm -f "$ZIP_PATH"
( cd "$BUILD_DIR" && zip -rq "$ZIP_PATH" . )

SIZE="$(du -h "$ZIP_PATH" | cut -f1)"
echo "==> built $ZIP_PATH ($SIZE)"
echo "    Lambda's direct zip-upload ceiling is 50 MB (zipped); 250 MB"
echo "    unzipped across the function + any layers. If this zip is"
echo "    getting close to either, that's the moment to stop bundling"
echo "    strands-agents here and rely on the prebuilt layer instead"
echo "    (see requirements.txt's comment on that tradeoff)."
