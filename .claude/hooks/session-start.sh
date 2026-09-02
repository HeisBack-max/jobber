#!/bin/bash
# SessionStart hook: rebuild the project environment after a container cold start.
#
# Claude Code on the web reclaims the container after inactivity and provisions a
# fresh one when you return, so dependencies installed in an earlier session are
# gone. This restores them. Safe to re-run; it is a no-op once the venv is warm.
set -euo pipefail

# Remote sessions only: locally, developers manage their own venv.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

VENV=".venv"

# pyproject.toml requires >=3.12, but the container's default python3 is 3.11.
PYTHON="$(command -v python3.12 || command -v python3.13 || command -v python3)"

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating virtualenv with $PYTHON ($("$PYTHON" -V 2>&1))"
  "$PYTHON" -m venv "$VENV"
fi

# uv is an order of magnitude faster; fall back to pip when it is absent.
if command -v uv >/dev/null 2>&1; then
  VIRTUAL_ENV="$PWD/$VENV" uv pip install --quiet -e ".[dev]"
else
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -e ".[dev]"
fi

# Put the venv on PATH for every tool call in this session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export VIRTUAL_ENV=\"$PWD/$VENV\""
    echo "export PATH=\"$PWD/$VENV/bin:\$PATH\""
  } >> "$CLAUDE_ENV_FILE"
fi

echo "Environment ready: $("$VENV/bin/python" -V 2>&1)"
