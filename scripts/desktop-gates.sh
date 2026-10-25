#!/usr/bin/env bash
# Every desktop suite, one after another, on the settled build.
set -u
cd "$(dirname "$0")/.."
status=0
run() {
  local name="$1"; shift
  echo "=== $name"
  if "$@" > "artifacts/phase8/desktop-$name.log" 2>&1; then
    echo "PASS $name"
  else
    echo "FAIL $name"
    tail -25 "artifacts/phase8/desktop-$name.log"
    status=1
  fi
}
run baseline npm run test:desktop
run phase8 npx tsx tests/phase8-desktop.ts
run phase4 npx tsx tests/phase4-desktop.ts
run phase4-files npx tsx tests/phase4-files-desktop.ts
run phase5 npx tsx tests/phase5-desktop.ts
run phase6 npx tsx tests/phase6-desktop.ts
run phase7 npx tsx tests/phase7-desktop.ts
exit $status
