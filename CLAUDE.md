# CLAUDE.md — chemowell-beta

Instructions for any AI agent (Claude, Dispatch, or otherwise) working in this repository.

## RULE 0 — THIS REPO IS NOT THE CHEMOWELL PRODUCT. Read this before anything else.

**Despite its name, `chemowell-beta` is the STAGING COPY OF `care-tracker` — one specific person's
app.** The evidence is in its own `index.html`: `TEST_MODE = true`, writes to
`caretracker_test_entries`, `patientName: 'Brandi'` hardcoded at line 1069, and
`<title>Brandi's Meds / Vitals Historical</title>`. Her name appears five times and that is
CORRECT here, exactly as it is correct in `care-tracker`. Do not scrub it.

**The product is `chemowell-app-beta`**, the native app, which was seeded from this repo at v71.
That is the one where every user is a different patient and where her name, her medications, her
doses and her care plan must never appear.

### The naming collision is the root of a real, repeated failure

"ChemoWell" currently names two different things: a product (`chemowell-app-beta`) and one patient's
staging environment (`chemowell-beta`). On 2026-09-13, working from that name alone, I added a
"ChemoWell is a product, every user is a different patient" rule to THIS file and began treating a
private test bed as a shared product. Had that gone further it would have scrubbed a staging
environment whose whole job is to mirror production exactly — which would have made it useless for
the thing it exists for.

**Anyone reading only the repo name will get this wrong.** Check `TEST_MODE` and `COL_NAME` at the
top of `index.html` before deciding what kind of repo you are in. Renaming this repo to something
like `care-tracker-staging` is on Aaron's list as a decision; until he makes it, this section is
the guard.

### What DOES apply here

1. This is a test bed for a live patient's app. Treat `caretracker_entries` (production) as
   untouchable — see Hard Rule 1.
2. When a fix is ported to or from `chemowell-app-beta`, **the product-neutrality rules go with it in
   one direction only.** A fix travelling there must have her name, her pronouns, her doses and any
   id-keyed medication rules taken out. A fix travelling here does not need them put back, but it
   must not assume this repo is a product.
3. `chemowell-app-beta/CLAUDE.md` Rule 0 and its `test/v75-no-other-patient.mjs` are the product's
   guard. **Neither belongs in this repo**, and a copy of that test was briefly added here on
   2026-09-13 and removed again for exactly this reason.

---

## Renamed, Jul 20, 2026

This file was `CLAUDE.md`; the other two governance docs (`README.md` → `BETA_README.md`,
`CARETRACKER_HANDOFF.md` → `BETA_HANDOFF.md`) were renamed at the same time. **Purpose:**
production (`Arnjnnngs/care-tracker`) and this repo previously used identical filenames
(`README.md`, `CARETRACKER_HANDOFF.md`, `CLAUDE.md`) for both repos, so a file opened out of repo
context (pasted into a chat, handed to a tool, viewed in an editor tab) carried no name-level signal
for which environment it belonged to. The `TESTING_` prefix now makes that unambiguous at a glance,
independent of any in-file banner. See the incident below for why this matters in practice.

## What this repo is

This is the **staging/testing** counterpart to `Arnjnnngs/care-tracker` (production). It exists so new
features can be built and verified here first, using fabricated test data, before they're ever
promoted to the app Brandi's caregiver actually relies on.

- **Live app:** https://arnjnnngs.github.io/chemowell-beta/
- **Production app (do not confuse with this one):** https://arnjnnngs.github.io/care-tracker/
- **Firestore project:** `fuelforge-7c132` (shared with prod, but writes to a separate collection — see below)

## Hard rules — read before touching anything

1. **Never write test/QA data to `caretracker_entries`.** That collection is Brandi's real medical
   history. This app writes to `caretracker_test_entries` (`COL_NAME`, gated by `TEST_MODE = true`
   near the top of `index.html`). If `TEST_MODE` is ever flipped to `false` here, stop — that would
   point this staging app at production data.
2. **Never push to the production `care-tracker` repo's `main` branch without Aaron's explicit,
   in-the-moment go-ahead.** This applies even if a change looks trivial or was already approved for
   testing. Production and testing are promoted as a deliberate, separate step.
3. **Push to *this* repo (`chemowell-beta`) directly once a change is built and QA'd —
   no confirmation round-trip needed (per Aaron, Jul 16, 2026: "when I ask for changes, you can
   push to testing only from now on... we'll cut down on the back and forth"). This is the one
   exception to rule 2 — it applies ONLY to `chemowell-beta`, never to production. Still
   build and QA in the sandbox first; just don't wait for a go-ahead before pushing testing.
4. **Never run real QA against live Firestore.** Use a mocked Firestore harness (in-memory store +
   pub/sub, matching the shape of `subscribeEntries`/`addEntryDB`/`removeEntryDB`) driven by jsdom or
   a real headless browser. Only manual, deliberate testing by a human should touch the actual
   `caretracker_test_entries` collection.
5. **Keep documentation current.** Every change to `index.html` that affects behavior, medications,
   Firebase fields, or the service worker gets a matching update to `BETA_README.md` and
   `BETA_HANDOFF.md` in the same pass — see "Maintaining documentation" in both files.
6. **Never paste replacement file content into GitHub's inline web editor.** GitHub's "Edit file" box
   replaces a file's *entire contents* with whatever's in the box, with no diff shown before commit.
   On the night of Jul 19–20, 2026, a commit made this way (intended to add a Morphine half-dose
   window feature) instead replaced `index.html`, `sw.js`, and the handoff doc with the literal
   9-character text `undefined` — no feature landed, the commit only destroyed three files, and the
   live app served a blank "undefined" page that a client-side cache reset could not fix (the server
   itself was serving the broken file, not a stale client copy). See `BETA_HANDOFF.md`'s v53 entry
   for the full incident. **Always edit locally (or have an agent work from the real file contents)
   and push an actual diff** — never use GitHub's web editor to paste in a full replacement.

## Repo-specific things that trip people up

- This repo has **no** `.github/workflows/`, no `send-reminders.js`, and no live push notifications —
  `subscribePush()` and `checkNotifications()` both short-circuit when `TEST_MODE` is true. Don't
  assume the production reminder/cron system applies here; it doesn't exist in this repo at all.
- `firebase-messaging-sw.js` is present (copied from prod) but effectively unused while `TEST_MODE`
  is on, since the app never registers for a push token here.
- The visual theme is **light pink glassmorphism**, not dark — don't copy prod's dark-theme
  descriptions into these docs.
- This repo currently has features prod does not: the chemo-cycle system (chemo date, Dexamethasone,
  Zofran chemo-day block, chemo banners), missed-dose alerts, menstrual cycle tracking, In-Patient day
  tracking, a pain-level (1–10) scale on Morphine logs, and Zofran treated as a plain as-needed med
  (no gap timer, no reminders). Confirm feature parity/divergence against prod before promoting
  anything — don't assume the two `index.html` files are close to each other structurally.
- **Versioning matches prod, offset ahead.** This repo's version number is always
  `(current live/pushed prod version) + 1` while testing is ahead of production — e.g. if prod is
  live at v27, testing is v28, and the next testing change becomes v29, and so on, until those
  features are promoted to prod and prod catches up. Do NOT use a separate "tN" counter — check
  the *actual pushed* `care-tracker` repo's `sw.js`/README (not any local unpushed copy) before
  assigning the next testing version number, since prod may have moved since this repo was last
  touched. Service worker cache name here is `caretracker-testing-vN` using that same number
  (e.g. `caretracker-testing-v29`), not a separate testing-only counter.

## Working with Aaron — browser tab hygiene

- **Close Chrome tabs once you're done verifying in them.** Aaron verifies everything on his phone
  (mobile app), not by reviewing tabs on desktop — so a live-verification tab has no reason to stay
  open once the check is complete. Standing rule (Aaron, Jul 19, 2026): close tabs you opened as
  soon as you're finished with them.
- **Exception:** leave a tab open only if there's something web-only that Aaron specifically needs
  to look at himself (e.g. a GitHub Actions log, a page he asked to review). That's not the normal
  case for this project.

## Workflow for a new feature request

1. Understand the actual current `index.html` in *this* repo (don't assume it matches prod — it
   frequently doesn't). Read the real file, not stale docs.
2. Implement against this repo's actual theme, state shape, and existing features so nothing
   regresses (chemo banners, missed-dose alerts, evening-meds flow, etc.).
3. Build a mocked-Firestore QA harness and verify both the new behavior and a regression pass over
   existing features.
4. Update `BETA_README.md`'s Version History table (new row, numbered per the versioning rule
   above) and `BETA_HANDOFF.md`.
5. Bump the `sw.js` cache version.
6. Push to this repo's `main` once built and QA'd — no confirmation needed for testing (see Hard
   Rule 3). Production promotion always still needs Aaron's explicit go-ahead. **Push via a real
   git diff, never GitHub's inline web editor (Hard Rule 6).**
