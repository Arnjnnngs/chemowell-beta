#!/bin/bash
# ChemoWell session guard -- runs at SessionStart, and again at Stop.
#
# WHY THIS EXISTS. On 2026-09-13 Aaron found the medication disclaimer in this app -- the one place
# it gives safety guidance about medication -- reading "Follow her care team." The "her" is the owner's
# wife, whose own app (care-tracker) is a sibling of this one. He had given the same directive on
# 2026-08-19 and it had not been carried out.
#
# The mechanism was a filename: this repo's rules lived in APP_CLAUDE.md, which Claude Code does not
# auto-load, so the ONLY instruction file any session ever loaded was care-tracker/CLAUDE.md -- 719
# lines naming her nine times and listing four of her medications. Every session was briefed on her
# and never on this product.
#
# Renaming the file fixed the missing brief. It did NOT fix the extra one: all three repos sit under
# one working directory, so reading any file in care-tracker still pulls its instructions in. This
# hook is what makes that visible instead of silent.
#
# It NEVER blocks work -- a guard that stops a session gets disabled the first time it is wrong, and
# then it protects nothing. It prints, loudly, on every session.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT="$(dirname "$ROOT")"

echo ""
echo "================================================================"
echo " THIS IS NOT THE CHEMOWELL PRODUCT."
echo " chemowell-beta is the STAGING COPY of care-tracker -- one"
echo " specific person's app. TEST_MODE=true, writes to"
echo " caretracker_test_entries, patientName is hardcoded to her name."
echo " Her name belongs here. DO NOT SCRUB IT."
echo ""
echo " The product is ../chemowell-app-beta. That is where her name,"
echo " her medications and her doses must never appear."
echo "================================================================"
echo ""
echo " The repo name says ChemoWell and the contents are care-tracker."
echo " Working from the name alone gets this backwards -- it already did,"
echo " on 2026-09-13. Check TEST_MODE and COL_NAME in index.html before"
echo " deciding what kind of repo you are in."
echo ""
if [ -f "$PARENT/chemowell-app-beta/index.html" ]; then
  echo " When porting a fix TO the product, take her name, her pronouns, her"
  echo " doses and any medication-id-keyed rules out on the way. Porting one"
  echo " back here does not require putting them in."
  echo ""
fi
exit 0

# The four shapes, checked rather than described. Never blocks; always reports.
SIB="$PARENT/chemowell-app-beta"
if [ -f "$ROOT/test/v75-no-other-patient.mjs" ]; then
  if ( cd "$ROOT" && node test/v75-no-other-patient.mjs >/tmp/cw-guard.log 2>&1 ); then
    echo " ✓  No-other-patient check: clean (name, pronouns, hardcoded doses, id-keyed rules)."
  else
    echo " ✗  NO-OTHER-PATIENT CHECK FAILED -- one patient has leaked into this product."
    echo ""
    sed -n '/FAIL/p' /tmp/cw-guard.log | head -12 | sed 's/^/    /'
    echo ""
    echo "    Full output: /tmp/cw-guard.log    Rule 0 in CLAUDE.md explains each shape."
  fi
elif [ -f "$SIB/test/v75-no-other-patient.mjs" ]; then
  echo " ⚠  This repo has no four-shape check of its own. The sibling app carries"
  echo "    test/v75-no-other-patient.mjs; port it here rather than assuming this"
  echo "    repo is clean because that one is."
else
  echo " ⚠  No four-shape check found in either repo. It is the only mechanical"
  echo "    guard against this class; it should not be deleted."
fi
echo ""
exit 0
