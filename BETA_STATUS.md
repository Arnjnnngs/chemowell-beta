# chemowell-beta — STATUS

DISPATCH: IDLE

**WEB-BETA — the staging app for care-tracker (WEB-MAIN).**
Live: https://arnjnnngs.github.io/chemowell-beta/

---

## WHAT THIS APP IS, AND WHAT IT CANNOT DO

This is care-tracker with test isolation applied. It exists so changes can be proven **before**
they reach the app a cancer patient uses every day.

**It cannot touch live data. This is verified by a test, not by inspection:**

| Containment | How |
|---|---|
| Records | `caretracker_test_entries` — never `caretracker_entries` |
| Settings | `caretracker_test_prefs` — never `caretracker_prefs` |
| Push notifications | The beta **never requests an FCM token.** The reminder job sends to *every* token it finds, so a beta token would put test notifications on the patient's phone |
| In-app reminders | Disabled — the beta must not train anyone to ignore an alert |
| Identity | A permanent orange **BETA — TEST DATA ONLY** banner at the top of Home |

`beta-isolation-test.mjs` asserts on the Firestore paths the app **actually touches at runtime**,
recorded by the stub — not on whether the source contains the string `TEST_MODE`.

---

## PARITY — brought current 2026-08-19

The beta had drifted **six releases** behind: 227 KB against production's 401 KB, missing the
calendar, backup and restore, the tour, shared medication settings, the sync guards, the v43.4
deactivation fix and the v49 missed-on-card fix. **A staging app that stale cannot stage anything** —
a change would pass or fail there for reasons unrelated to the change.

**Now derived FROM production instead of patched toward it.** `harness/betaify-patch.py` transforms
a care-tracker build into this one. Re-applying the nine harness patches to the drifted beta was the
obvious route and the wrong one: its anchors came from an older lineage, would not have matched, and
every mismatch would have been resolved by guessing. Deriving the beta from production makes parity
**true by construction**.

### Re-staging after any care-tracker release — one command
```
git clone https://github.com/Arnjnnngs/care-tracker.git prod
python3 harness/betaify-patch.py --file prod/index.html    # then bump sw.js CACHE to chemowell-beta-<ver>
env -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy \
  node harness/beta-isolation-test.mjs --file prod/index.html
```
Parity stops being a project and becomes a step.

**Current:** `beta-v49`, derived from care-tracker v49 (`61eca1e`).
`index.html` md5 `b71c56f38c5b28f790474b35a9af4a03` · `sw.js` CACHE `chemowell-beta-v49`

---

## THE DATE SIMULATOR — the reason this app is worth having

`simNow()` lets a tester jump the clock without waiting for real time. Chemo offsets, medication
windows, missed-dose logic, cycle counters and in-patient ranges all become testable in seconds.

Aaron's *"Protonix says Waiting at 1 PM"* report is a thirty-second check here instead of an
afternoon of waiting. It is hard-wired to fall back to real time whenever `TEST_MODE` is false.

Controls sit at the top of Home under the banner: a date picker, ±1 day, and Today.

---

## TEST RESULTS

`beta-isolation-test.mjs` — **9/9**, and falsified:
- Flipping `TEST_MODE` to `false` turns **5 checks red**, including live collections being read
  and a dose being written to live data.
- Removing the push guard turns **ISO-4 red**.

### A check that could not fail, caught by falsification
`ISO-4` (no FCM token) originally passed **even with its guard deleted** — `subscribePush()` stops
at `Notification.requestPermission()` in headless Chromium, so `getToken()` was never reached and
the count stayed at zero for the wrong reason. The suite now grants the permission so the push path
genuinely executes and the guard is what stops it. **The mutator, not review, found this.**

### And a real defect the suite caught
The first build put the BETA badge in the **drawer footer** — a screen a tester never opens. The
build was perfectly contained and still failed `ISO-5`, correctly: containment is worthless if
someone cannot tell which app they are in. The banner is now pinned to the top of Home.

---

## WHAT THE BETA STILL CANNOT TEST

**The reminder pipeline.** `send-reminders.js` runs from care-tracker's GitHub Actions, reads FCM
tokens and sends real pushes. This repo has no workflow and no tokens **by design**. The data side
can be exercised against the test collections; delivery cannot.

To close that, the beta would need its own workflow and a dedicated test token — a deliberate
decision, not a default, because the whole containment guarantee above rests on there being no
token here.

---

## RULES

1. **`TEST_MODE` is never set to `false` in this repo.** Production is care-tracker's own build;
   this file is derived *from* it, never promoted *into* it.
2. **Never add an FCM token to this app** without also solving the "reminder job sends to every
   token" problem.
3. Re-run `beta-isolation-test.mjs` after every re-stage. 9/9 or the beta does not ship.
4. This repo must never reference ChemoWell's storage, and ChemoWell must never reference
   `caretracker_*` collections.
