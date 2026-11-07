#!/usr/bin/env bash
# Dependencies are prepared online by the workflow before entering this boundary.
set -euo pipefail
mkdir -p .work/home .work/tmp
python_path=$(command -v python)
sudo unshare --net -- setpriv --reuid="$(id -u)" --regid="$(id -g)" --init-groups \
  env "PATH=$PATH" "LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" \
  "HOME=$PWD/.work/home" "TMPDIR=$PWD/.work/tmp" \
  "GITHUB_OUTPUT=${GITHUB_OUTPUT:-}" \
  "$python_path" -I -B tools/ci.py check --tag "${RELEASE_TAG:-}"
