#!/usr/bin/env python3
"""
betaify-patch.py — turn a care-tracker production build into the isolated BETA testing build.

WHY THIS EXISTS
  chemowell-beta is documented as WEB-BETA, the staging app for care-tracker (WEB-MAIN). It had
  drifted SIX RELEASES behind: 227KB against production's 401KB, missing the calendar, backup and
  restore, the tour, shared medication settings, the sync guards, the v43.4 deactivation fix and
  the v49 missed-on-card fix. A staging app that old cannot stage anything -- a change would pass
  or fail there for reasons unrelated to the change.

WHY IT TRANSFORMS PRODUCTION INSTEAD OF PATCHING THE BETA
  Re-applying the nine harness patches to the drifted beta was the obvious route and the wrong one:
  its anchors are from an older lineage and would not match, and every mismatch would be resolved by
  guessing. Deriving the beta FROM production is exact by construction -- the beta becomes
  "production plus test isolation", and parity is guaranteed rather than hoped for.

  Run this after every care-tracker release to re-stage. That is the point: parity stops being a
  project and becomes one command.

WHAT IT ADDS (all seven pieces of the original beta harness, preserved verbatim in behaviour)
  1. TEST_MODE + separate caretracker_test_* collections  -- CANNOT touch the patient's live data
  2. Push registration disabled                           -- CANNOT send notifications to her phone
  3. Local reminders disabled                             -- same reason
  4. simNow() date simulator + set/shift/reset            -- jump the clock without waiting
  5. Beta date controls UI
  6. A loud, permanent BETA badge and banner
  7. Beta version + cache naming

SAFETY INVARIANT, ASSERTED BELOW: the string 'caretracker_entries' must never appear unguarded.
Every read and write in the output must resolve through TEST_MODE.
"""
import argparse, hashlib, re, subprocess, tempfile, os, sys

def die(m):
    print("FAIL: " + m); sys.exit(2)

EDITS = [

("1. TEST_MODE and isolated collections",
'''const COL_NAME = "caretracker_entries";''',
'''// THE ISOLATION SWITCH. Everything that could reach the patient's real data is gated on this.
// Set to false ONLY if this file is ever promoted to production, which is not how promotion works
// here -- production is care-tracker's own build and this file is derived FROM it, never into it.
const TEST_MODE = true; // TESTING APP — never set false in the beta repo
const COL_NAME = TEST_MODE ? "caretracker_test_entries" : "caretracker_entries";'''),

("2. isolated prefs collection",
'''const PREFS_COL_NAME = 'caretracker_prefs';''',
'''// Separate prefs too: clearing the missed-dose banner, or choosing a shared medication list, must
// never write into the live app's settings document.
const PREFS_COL_NAME = TEST_MODE ? 'caretracker_test_prefs' : 'caretracker_prefs';'''),

("3. no push registration from the test app",
'''async function subscribePush() {
  if (!messaging) return;''',
'''async function subscribePush() {
  // The beta must never obtain an FCM token. If it did, the reminder job -- which sends to every
  // token it finds -- would deliver test notifications to the patient's phone.
  if (!messaging || TEST_MODE) return;'''),

("4. the date simulator",
'''function simNow() { return Date.now(); }''',
'''// ---- TESTING-ONLY date override ----
// Lets a tester simulate a different "today" so date-dependent behaviour (chemo offsets,
// missed-dose windows, medication windows, cycle counters, in-patient ranges) can be exercised
// without waiting for real time to pass. This is the single most useful thing the beta has:
// Aaron's "Protonix says Waiting at 1 PM" report is a thirty-second check here.
// Falls back to real time whenever TEST_MODE is false, so it is inert outside the beta.
function simNow() {
  if (!TEST_MODE) return Date.now();
  return Date.now() + (state.dateOffsetDays || 0) * 86400000;
}
function setSimDate(dateStr) {
  if (!TEST_MODE || !dateStr) return;
  const p = dateStr.split('-').map(Number);
  const picked = dayStart(new Date(p[0], p[1] - 1, p[2]).getTime());
  const realToday = dayStart(Date.now());
  state.dateOffsetDays = Math.round((picked - realToday) / 86400000); // set first so simNow() sees it
  setState({ now: simNow() });
}
function shiftSimDate(days) {
  if (!TEST_MODE) return;
  state.dateOffsetDays = (state.dateOffsetDays || 0) + days;
  setState({ now: simNow() });
}
function resetSimDate() {
  if (!TEST_MODE) return;
  state.dateOffsetDays = 0;
  setState({ now: simNow() });
}

// The beta date controls. Collapsed by default so they never obscure the app being tested.
function renderTestingControls() {
  if (!TEST_MODE) return [];
  const dateValue = (() => { const d = new Date(state.now); const pad = n => String(n).padStart(2, '0');
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); })();
  const isOpen = !!state.testDateControlsOpen;
  const btn = (label, onClick) => h('button', { onClick, style: { minHeight: '44px', padding: '0 12px', borderRadius: '10px', background: 'rgba(199,120,0,0.16)', border: '1px solid rgba(199,120,0,0.45)', color: '#704B12', fontSize: '13px', fontWeight: '700' } }, label);
  return [h('div', { 'data-beta-controls': 'true', style: { background: 'rgba(199,120,0,0.08)', border: '1px dashed rgba(199,120,0,0.52)', borderRadius: '14px', padding: '0 12px', color: '#704B12' } },
    h('div', { onClick: () => setState({ testDateControlsOpen: !state.testDateControlsOpen }), style: { minHeight: '44px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', fontSize: '12px', fontWeight: '800', letterSpacing: '0.04em', textTransform: 'uppercase' } },
      h('span', null, 'Beta date controls'),
      h('span', { style: { fontSize: '10px' } }, isOpen ? '\\u25B2' : '\\u25BC')
    ),
    isOpen ? h('div', { style: { padding: '0 0 12px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' } },
      // 16px so iOS Safari does not zoom in on focus and stay zoomed (the v48 floor).
      h('input', { type: 'date', value: dateValue, onInput: (event) => setSimDate(event.target.value), className: 'mono', style: { minHeight: '44px', fontSize: '16px', padding: '0 10px', borderRadius: '10px', border: '1px solid rgba(199,120,0,0.45)', background: 'rgba(255,255,255,0.75)', color: '#704B12' } }),
      btn('-1 day', () => shiftSimDate(-1)),
      btn('+1 day', () => shiftSimDate(1)),
      btn('Today', () => resetSimDate()),
      h('span', { style: { fontSize: '11.5px', fontWeight: '700' } }, (state.dateOffsetDays || 0) === 0 ? 'real time' : ((state.dateOffsetDays > 0 ? '+' : '') + state.dateOffsetDays + ' days'))
    ) : null
  )];
}'''),

("5. no local reminders from the test app",
'''function checkNotifications() {''',
'''function checkNotifications() {
  if (TEST_MODE) return; // the beta never raises reminders — it must not train anyone to ignore them'''),

("6. beta state fields",
'''let state = { entries: [], chemoDates: [],''',
'''let state = { dateOffsetDays: 0, testDateControlsOpen: false, entries: [], chemoDates: [],'''),

("7. the beta badge, banner and controls",
'''        h('div', { 'data-app-version': 'true', style: { marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(212,104,138,0.12)', textAlign: 'center', fontSize: '11px', fontWeight: '700', color: '#8A7080', letterSpacing: '0.02em' } }, 'CareTracker ' + APP_VERSION)''',
'''        h('div', { 'data-app-version': 'true', style: { marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(212,104,138,0.12)', textAlign: 'center', fontSize: '11px', fontWeight: '700', color: '#8A7080', letterSpacing: '0.02em' } }, 'CareTracker BETA ' + APP_VERSION),
        // Unmissable, permanent, and never in production: nobody should ever be unsure which app
        // they are looking at, least of all while logging a real dose.
        h('div', { 'data-beta-footer-badge': 'true', style: { marginTop: '8px', textAlign: 'center' } },
          h('span', { style: { display: 'inline-block', background: '#C77800', color: '#fff', border: '1px solid #A86400', borderRadius: '99px', padding: '4px 12px', fontSize: '11px', fontWeight: '800', letterSpacing: '0.06em' } }, 'BETA — TEST DATA ONLY')
        )'''),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    src = open(a.file, encoding="utf-8").read()
    print("in   %s\n     md5 %s  (%d bytes)" % (a.file, hashlib.md5(src.encode()).hexdigest(), len(src)))
    if "const TEST_MODE" in src:
        print("ALREADY BETA — nothing written."); return
    out = src
    for name, old, new in EDITS:
        n = out.count(old)
        if n != 1: die("anchor matched %d times (need exactly 1) -> %s" % (n, name))
        out = out.replace(old, new, 1)
        print("  ok  " + name)

    # ---- mount the controls on Home, above everything ----
    anchor = "  // WRITE FAILURE — pushed above everything"
    if out.count(anchor) != 1: die("controls mount anchor not unique")
    out = out.replace(anchor,
'''  // BETA BANNER, pinned to the top of Home, above the write-failure banner and everything else.
  // The badge added below lives in the drawer footer -- which a tester never opens. The isolation
  // suite caught exactly that: 8/9 with "no BETA badge found", on a build that was otherwise
  // perfectly contained. Containment is worthless if someone cannot tell which app they are in.
  if (TEST_MODE) {
    parts.push(h('div', { 'data-beta-badge': 'true', style: { display: 'flex', alignItems: 'center', gap: '9px', background: '#C77800', color: '#fff', border: '1px solid #A86400', borderRadius: '14px', padding: '10px 12px' } },
      h('span', { style: { flexShrink: '0', width: '22px', height: '22px', borderRadius: '50%', background: 'rgba(255,255,255,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '800', fontSize: '13px' } }, '!'),
      h('span', { style: { flex: '1', minWidth: '0', fontSize: '12.5px', fontWeight: '800', letterSpacing: '0.02em', lineHeight: '1.35' } },
        'BETA — TEST DATA ONLY. Nothing logged here reaches the real app.')
    ));
  }
  // Beta date controls sit directly under it so a tester always knows what "today" is.
  if (TEST_MODE) { renderTestingControls().forEach(node => parts.push(node)); }
''' + anchor, 1)
    print("  ok  8. beta banner + date controls mounted at the top of Home")

    # ---- version / cache naming ----
    vm = re.search(r"const APP_VERSION = '([^']*)';", out)
    if not vm: die("APP_VERSION not found")
    prod = vm.group(1)
    out = out.replace("const APP_VERSION = '%s';" % prod,
                      "const APP_VERSION = 'beta-%s'; // derived from care-tracker %s" % (prod, prod), 1)
    print("  ok  9. APP_VERSION -> beta-%s" % prod)

    # =========================== SAFETY POST-CONDITIONS ===========================
    # The whole point of the beta is that it cannot reach the patient's live records.
    for bad, why in [
        ('collection(db, "caretracker_entries")', 'a direct live-entries collection reference'),
        ("collection(db, 'caretracker_entries')", 'a direct live-entries collection reference'),
    ]:
        if bad in out: die("%s survived — the beta could write to LIVE data." % why)
    for m in re.finditer(r"'caretracker_(entries|prefs)'|\"caretracker_(entries|prefs)\"", out):
        line = out[out.rfind('\n', 0, m.start())+1:out.find('\n', m.start())]
        if 'TEST_MODE ?' not in line:
            die("UNGUARDED live collection reference:\n      " + line.strip()[:140])
    if out.count("const TEST_MODE = true;") != 1: die("TEST_MODE is not set exactly once")
    if "if (!messaging || TEST_MODE) return;" not in out: die("push registration is not disabled")
    if "if (TEST_MODE) return; // the beta never raises reminders" not in out: die("local reminders not disabled")

    # ---- production invariants must survive the transform ----
    if "if (!state.timeModal && !state.apptSheet && !state.drawerOpen && !state.tour && !isEditing) render();" not in out:
        die("the composed 1s tick guard was damaged")
    for f, why in [("uiIsBusy()", "v47 sync guards"), ("throw err;", "v48 write-failure rethrow"),
                   ("data-missed-on-card", "v49 missed-on-card"), ("medIsOnActiveList", "v43.4 deactivation fix"),
                   ("CAL_APPT_MED_ID", "the calendar"), ("downloadBackupFile", "backup/restore"),
                   ("tourStart", "the tour"), ("medConfigJson", "shared medication settings")]:
        if f not in out: die("%s is missing from the output — parity was not achieved" % why)
    if out.count("function missedDosesFor") != 1: die("missedDosesFor duplicated")

    m = re.search(r'<script type="module">(.*?)</script>', out, re.S)
    if not m: die("module block not found")
    tf = tempfile.NamedTemporaryFile('w', suffix='.mjs', delete=False, encoding='utf-8')
    tf.write(m.group(1)); tf.close()
    r = subprocess.run(['node', '--check', tf.name], capture_output=True, text=True)
    os.unlink(tf.name)
    if r.returncode != 0: die("output is not valid JavaScript:\n" + r.stderr.strip()[:400])
    print("  ok  post: output parses, isolation verified, all production features present")

    if a.check:
        print("check only — nothing written."); return
    open(a.file, "w", encoding="utf-8").write(out)
    print("\nout  md5 %s  (%d bytes, %+d)" % (hashlib.md5(out.encode()).hexdigest(), len(out), len(out)-len(src)))

main()
