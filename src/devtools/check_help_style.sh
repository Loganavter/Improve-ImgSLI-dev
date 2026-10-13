#!/bin/bash
# Style gate for help pages: jargon grep + EN/RU section parity.
# Run from anywhere: bash src/devtools/check_help_style.sh
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HELP_DIRS=(src/resources/help)
for d in src/tabs/*/resources/help src/plugins/*/resources/help; do
  [ -d "$ROOT/$d" ] && HELP_DIRS+=("$d")
done
fail=0

# 1. RU jargon in prose
RU_JARGON='тулбар|контрол|шестерёнк|скринкаст|кейфрейм|дорожк|трек|хром|бэкенд|кластеризац|пульсац'
if grep -rniE --include='*.md' "($RU_JARGON)" "${HELP_DIRS[@]/#/$ROOT/}" | grep -v '/en/'; then
  echo "STYLE FAIL: RU jargon above"; fail=1
fi
# flyout allowed only in ids/anchors/slots/links
if grep -rniE --include='*.md' 'flyout' "${HELP_DIRS[@]/#/$ROOT/}" | grep -v '{#' | grep -v 'img:' | grep -v 'help://'; then
  echo "STYLE FAIL: flyout in prose above"; fail=1
fi
# 2. EN jargon in prose
EN_JARGON='control track|keyframe|screen grab|raw screen|chrome'
if grep -rniE --include='*.md' "($EN_JARGON)" "${HELP_DIRS[@]/#/$ROOT/}" | grep '/en/'; then
  echo "STYLE FAIL: EN jargon above"; fail=1
fi
# 3. EN/RU ### parity per page
for en in $(find "${HELP_DIRS[@]/#/$ROOT/}" -path '*/en/*.md'); do
  rel="${en#/en/}"; rel="${rel#*$ROOT/}"
  ru="${en/\/en\//\/ru\/}"
  [ -f "$ru" ] || continue
  ce=$(grep -c '^### ' "$en"); cr=$(grep -c '^### ' "$ru")
  if [ "$ce" != "$cr" ]; then
    echo "STYLE FAIL: section drift $en ($ce) vs $ru ($cr)"; fail=1
  fi
done
[ $fail -eq 0 ] && echo "STYLE OK"
exit $fail
