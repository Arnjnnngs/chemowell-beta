# care-tracker STAGING — the instructions themselves

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

## Rule 0.7 — A TASK LIST, EVERY TIME, COMPLETED IN ORDER. (2026-09-14, Aaron, and he has said it before)

> *"Every time I give you something to do, you need to create a task list and complete in order
> unless I tell you otherwise. I've said multiple times before about task list. Those notes should be
> somewhere in the md file. There probably needs to be a meeting notes taker that can keep track of
> tasks to keep you on track. This is absurd"*

**He is right that he has said it before, and right that it was not written down here. That is the
whole defect.** The Scribe seat (Rule 1.5) was described as keeping `REQUESTS.md` and
`TASK-SHEET.md` — files. It was never made to create a LIVE, ORDERED task list at the moment he
asks for something, and so the order of work was decided by whatever I found interesting.

**What that cost, exactly, on 2026-09-13/14.** Aaron approved a three-screen redesign from
screenshots and gave the order himself: *Home timeline → Meds cards + ceiling bar → Reports.* Twelve
hours later **one card of one screen existed**, in a weaker form than the mockup, because a dose-
parser defect turned into eleven audit rounds and a back-button fix turned into three ports, and
neither was the thing he asked for. Both were real. Neither was next. **There was no list, so
nothing said so.**

### The rule

1. **The moment Aaron asks for anything, create the task list — before any other tool call.** Use
   the task tools (TaskCreate / TaskUpdate), not a paragraph and not a file. It has to be the thing
   he can see at a glance.
2. **One task per deliverable, in the order HE gave**, not the order that is easiest. If he did not
   give an order, propose one in the list and start at the top.
3. **Mark in_progress before starting and completed when it is genuinely done** — done means built,
   verified and pushed, not "written".
4. **Anything found along the way becomes its own task at the BOTTOM of the list**, not a detour.
   A defect found mid-task is logged and scheduled; only a defect that makes the current task
   impossible or unsafe is allowed to jump the queue, and then it is said out loud.
5. **The list goes in the reply** whenever the work spans more than one message, so he never has to
   ask what is happening or in what order.

**This is not the Scribe's habit. It is the first action of every request.** A role whose output is
a file Aaron does not read is not a role — that lesson is already written into Rule 2.6 about the
Enhancer, and it is the same lesson here one level up.

## Rule 0.8 — THE TASK TABLE GOES IN THE MESSAGE. EVERY MESSAGE. (2026-09-14, Aaron, EXPLICIT)

> *"I don't see the list. You said you fixed it. There needs to be very frequent task table update so
> I can see what has been done when I go back to the chat occasionally. I shouldn't have to read 15
> pages of small details to see what was done. I can scroll through and see the table and see what
> was done. Commit to your record and put into place now"*

**Rule 0.7 was written and then not obeyed.** The list was created with the task tools — which render
somewhere Aaron does not look — and the replies went back to being prose. From his side that is
identical to there being no list at all. The task tools are for me; **the table in the message is for
him**, and it is the one that counts.

### The rule

1. **Every message to Aaron carries a markdown table.** Not a bulleted list, not a paragraph, not
   "see the task list" — a table, so it is a recognisable shape he can scroll to and read in five
   seconds without reading anything around it.
2. **Columns, always these four, in this order:**

   | # | App | Task | Status |

   **App is not optional** (Aaron, 2026-09-14: *"the task should show what app is being worked on.
   Bc I have no idea which one you're actually working on"*). It is one of
   `ChemoWell app` · `care-tracker` · `staging` · `all 3 repos`.
3. **The table shows the LAST 5 COMPLETED items plus everything still open.** Not open items only —
   the completed rows are the record of what happened while he was away, and they are the reason the
   table exists. Completed rows come first, oldest of the five at the top, so the eye lands on the
   open work at the bottom where the next action is.
4. **Status is one of:** `DONE — live` · `DONE — pushed, awaiting your word` · `IN PROGRESS` ·
   `QUEUED` · `BLOCKED — needs you`. A status that names a blocker names it in the same cell.
5. **Frequent means every message, including the long ones.** This does not license a status-only
   message — Rule 0.6 still governs WHEN a message may be sent (an approval he must give, or
   completion). Rule 0.8 governs what is IN a message once one is due: the table is the top of it,
   and the detail goes underneath for whoever wants it.
6. **If a task moved since the last table, the table says so.** A row that has not changed in three
   messages while work is happening means the rows are wrong — split the task.

**Why a table and not the task tools.** The task tools are a side panel in a developer's terminal.
Aaron reads this on a tablet, scrolling back through a chat, looking for the shape of a table. Output
that lands somewhere the owner does not look is not output — the same lesson as Rule 2.6's Enhancer
list and Rule 0.7's task list, now for the third time. **Third time is the rule getting a mechanism:
the table is part of the message body, so it cannot be filed anywhere else.**

### The numbers, and why the first table got them wrong (2026-09-14, same day)

Aaron, on the very first table this rule produced: *"The # on the task table is quite confusing.
It's not in order and the range jumps from 28 to 77. Is that logical for you and do you think that
makes sense to me. You put 77 bc caretracker is on v77"*

**He is exactly right and it was worse than untidy.** The `#` column is a TASK number. I put `77` in
it because care-tracker's release is v77 — a VERSION number, in a column of task numbers, in a table
whose whole purpose is to be readable in five seconds. A reader has no way to know one row is
counting a different thing from every other row.

1. **The `#` column holds task numbers and nothing else.** Never a version, never a release, never a
   commit. A version belongs in the Task cell as words: *"care-tracker v77 — back button"*.
2. **Rows are in ascending order by number**, completed five first, then open. An out-of-order list
   is a list somebody has to read twice.
3. **Every open item gets a real task number**, allocated in sequence. If something is being tracked
   without one — a blocker, a promotion waiting on Aaron — it gets a number before it gets a row.
   A row with a `—` in the `#` column is a row that was never on the list.

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
- **Versioning: this repo has its own counter, and the rule that said otherwise had been dead for
  months.** *(Rewritten 2026-09-15 after checking it against the actual history rather than
  re-reading it.)*

  **What this section used to say:** the version here is always `(current live prod version) + 1`,
  the cache is `caretracker-testing-vN` using that same number, and *"do NOT use a separate 'tN'
  counter"*. **Every clause of that is false of this repo and has been through three different
  schemes.** Staging is at `beta-v66` against a production live at **v77** — eleven behind the
  number the rule demands, not one ahead — and the cache reads `chemowell-beta-v66`, not
  `caretracker-testing-v67`. A rule nobody has followed since July is not a rule; it is a trap for
  the next person who obeys it and renumbers a live staging app to match.

  **What actually happened**, from `BETA_README.md`'s own table:
  1. Up to `v71` (Jul 23) the number DID track production and the cache was `caretracker-testing-vN`.
     The v71 rebrand renamed the cache to `chemowell-beta-v71`.
  2. `beta-v59` (Aug 24) re-staged from production v59 after seven releases of drift and adopted
     `beta-v<the prod version it was staged from>` — so the number went DOWN, deliberately.
  3. From `beta-v61` the coupling broke for good: it was built when prod was at v74. Since then
     `beta-vN` has been this repo's own sequential counter and nothing else.

  **The rule now, which is the practice written down:**
  * `APP_VERSION` is `beta-vN`, N incrementing by one per release here. It is NOT derived from
    production's number and must never be renumbered to match it.
  * `sw.js` CACHE is `chemowell-beta-vN` with the same N. (It keeps the repo's current name even
    after the rename below; the cache name is a cache key, not a URL, and churning it renames
    nothing and re-downloads everything.)
  * **The information the old rule existed for is carried by the table's third column instead**, and
    that is the part worth enforcing: every row in `BETA_README.md`'s version history names the
    `care-tracker` version and the ChemoWell `app-v` version it corresponds to. That is what tells a
    reader whether staging is ahead of production and by what — which the version number itself
    stopped saying in August.
  * **That column was silently dropped from `beta-v65` and `beta-v66`** (their prose sat in it, and
    the Status cell was missing entirely). Both are repaired. A row without it is incomplete: fill
    it in from the *actual pushed* `care-tracker` and `chemowell-app-beta` repos, not from a local
    unpushed copy, because both move while this one sits.

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

---

## THE REPO RENAME — pending, and it is Aaron's one click

Aaron approved renaming this repo on 2026-09-13. **I could not do it from here**: there is no rename
endpoint in the GitHub tools available to this session, and the REST call needs a token this
environment does not carry (`/user` returns 401). This is one of the few things that genuinely
requires the owner.

**On github.com → `Arnjnnngs/chemowell-beta` → Settings → General → Repository name →
`care-tracker-staging` → Rename.**

**Nothing breaks.** GitHub permanently redirects the old URL for both web and git, so existing
clones keep pushing and the Pages site keeps serving. Afterwards, in any clone:

    git remote set-url origin https://github.com/Arnjnnngs/care-tracker-staging.git

The GitHub Pages URL does change, from `arnjnnngs.github.io/chemowell-beta/` to
`arnjnnngs.github.io/care-tracker-staging/`. That matters only for anyone who has the staging app
bookmarked or installed; the production app at `arnjnnngs.github.io/care-tracker/` is untouched.

**Why it is worth doing.** "ChemoWell" currently names two different things: a product
(`chemowell-app-beta`) and this, one patient's staging environment — and the product was seeded from
this repo at v71. Anyone reading only the repo name gets it backwards. On 2026-09-13 I did exactly
that, and started applying a "this is a product, scrub the patient" rule to a test bed whose entire
job is to mirror production. `chemowell-app-beta/.claude/settings.json` already lists both the old
and new names in `claudeMdExcludes`, so the rename cannot silently switch that guard off.
