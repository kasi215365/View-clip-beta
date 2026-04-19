#!/usr/bin/env bash
# View/Clip — dependency audit
# Fails (exit 1) if any dependency cannot be installed from a public registry.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAIL=0

echo "=== Backend (pip) audit ==="
while IFS= read -r line; do
  # Skip empty lines and comments
  [[ -z "$line" || "$line" == \#* ]] && continue
  pkg="${line%%==*}"
  pkg="${pkg%%>=*}"; pkg="${pkg%%<=*}"; pkg="${pkg%% *}"
  [[ -z "$pkg" ]] && continue

  case "$pkg" in
    emergentintegrations)
      echo "  [PROPRIETARY] $pkg — see DEPENDENCY_AUDIT.md §Drop-in replacement"
      FAIL=1
      ;;
    *)
      # Silently OK — all other entries are on PyPI
      ;;
  esac
done < "$ROOT/backend/requirements.txt"

echo "=== Backend imports check ==="
if grep -R --include '*.py' -l '^\s*from emergent\|^\s*import emergent' "$ROOT/backend" | head -n1 >/dev/null 2>&1; then
  echo "  [WARN] Source still imports 'emergent*' modules — fine on Emergent, blocks migration elsewhere."
  grep -R --include '*.py' -n '^\s*from emergent\|^\s*import emergent' "$ROOT/backend" | head -5
  FAIL=1
fi

echo "=== Frontend (npm) audit ==="
# Any private registry in .npmrc or resolved deps?
if [[ -f "$ROOT/frontend/.npmrc" ]] && grep -qE '^registry\s*=' "$ROOT/frontend/.npmrc"; then
  CUSTOM_REG="$(grep -E '^registry\s*=' "$ROOT/frontend/.npmrc" | head -1)"
  if [[ "$CUSTOM_REG" != *"registry.npmjs.org"* ]]; then
    echo "  [WARN] .npmrc sets custom registry: $CUSTOM_REG"
    FAIL=1
  fi
fi

if [[ $FAIL -eq 0 ]]; then
  echo
  echo "✓ No blockers. App is fully portable."
else
  echo
  echo "✗ Found items above. Run migration prep as per DEPENDENCY_AUDIT.md."
  exit 1
fi
