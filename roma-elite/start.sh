#!/bin/sh
# Roma Elite — launcher (Mac/Linux). Requires Node.js 20+; no dependencies.
cd "$(dirname "$0")" || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is not installed."
  echo "Install it from https://nodejs.org (version 20 or newer), then run this again."
  echo
  echo "You can also just open dist/RomaElite.html in a browser — no install needed."
  exit 1
fi

echo "Starting Roma Elite on http://localhost:3000  (press Ctrl+C to stop)"
exec node server/index.js
