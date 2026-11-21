#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export PYTHONDONTWRITEBYTECODE=1
python -m unittest discover -s tools -p 'test_*.py'
node tools/test-quest-graph.mjs
for test in tools/test-quest-gaps.mjs tools/test-items.mjs tools/test-language.mjs tools/test-locale.mjs tools/test-npcs.mjs; do
  printf '\n%s\n' "$test"
  node "$test"
done
