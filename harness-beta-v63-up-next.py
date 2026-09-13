#!/usr/bin/env python3
"""beta-v62 -> beta-v63: Home answers "what is due next" before it asks for anything.

The port of ChemoWell app-v80 to care-tracker's staging copy, which Aaron asked for after seeing the
redesign: "Let's do redesign on both apps. Maybe on chemowell first then caretracker staging."

IT IS A PORT, NOT A COPY, and the differences are the point:

  * THE THEME IS THIS APP'S, not the other one's. This is light pink glassmorphism (#AA5375,
    #8E3D61, #342530); the product app is peach and terracotta. Pasting the product's gradient in
    here would look like a screenshot of a different app dropped onto the screen.
  * THE HELPERS DO NOT EXIST HERE. app-v80's hero reads medWindowsFor(), medScheduledOn(),
    treatmentOnlyBlocks() and doseProgressToday(). This codebase has none of them -- it is derived
    from care-tracker v60 and its status() is the legacy one, with the dexamethasone and zofran
    branches still written by name. So the computation is rebuilt against what is actually here
    rather than against what the other app has.
  * THERE IS NO `paused` IN THIS BUILD, so there is no paused case to exclude.

THE WRITE MODEL, unchanged from app-v80 and still the whole safety argument: this appends nothing,
deletes nothing, and writes no record. Every figure comes from status() and entriesFor(), which Home
already calls on every render, and the hero's button scrolls to a card that already exists rather
than logging anything. A second way to log a dose is a second way to double-log one.
"""
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
HTML, SW = ROOT / 'index.html', ROOT / 'sw.js'

def die(msg):
    print('PATCH FAILED: ' + msg); sys.exit(1)

src = HTML.read_text(encoding='utf-8')
if 'function nextDueDose' in src:
    die('already applied')

def cut(old, new, what):
    global src
    if src.count(old) != 1:
        die(what + ' is not where it was (found ' + str(src.count(old)) + ') -- nothing written')
    src = src.replace(old, new, 1)

# ---- the computation ------------------------------------------------------------------------------
cut("""function setToast(msg) {""",
    """// WHAT IS DUE NEXT, and HOW MUCH OF TODAY IS DONE. Read-only: status() and entriesFor() are both
// already called on every Home render.
//
// "Next" is the soonest of a windowed medication whose window is open right now, and one whose
// window opens later today. An as-needed medication is deliberately excluded: something available
// every four hours is not DUE at any time, and a card headed "Up next" naming one would tell a
// caregiver to give a dose nobody asked for. status() decides everything else -- the chemo block,
// the course being finished, a window already used -- so the hero cannot say something different
// from the cards below it.
function nextDueDose(now) {
  const d0 = dayStart(now);
  let best = null;
  for (const med of state.meds) {
    if (!med || med.type === 'gap') continue;        // as-needed: available, never due
    if (!(med.windows && med.windows.length)) continue;
    const st = status(med);
    if (st.chemoBlock || st.courseComplete) continue;
    if (!st.locked) { if (!best || !best.openNow) best = { med, st, openNow: true, at: now }; continue; }
    if (!Number.isFinite(st.availableAt)) continue;
    if (st.availableAt < now) continue;              // already past: that is missed, not next
    if (st.availableAt >= d0 + 86400000) continue;   // tomorrow is not "up next" today
    if (!best || (!best.openNow && st.availableAt < best.at)) best = { med, st, openNow: false, at: st.availableAt };
  }
  return best;
}
// Windows expected today against windows already logged into. The same shape the missed-dose walk
// uses, so the two cannot disagree about what "done" means.
function doseProgressToday(now) {
  const d0 = dayStart(now);
  let scheduled = 0, taken = 0;
  for (const med of state.meds) {
    if (!med || med.type === 'gap') continue;
    const windows = med.id === 'dexamethasone' ? dexWindowsForOffset(chemoOffsetFor(d0)) : (med.windows || []);
    if (!windows.length) continue;
    if (med.chemoOnly && !dexActiveOn(d0)) continue;
    scheduled += windows.length;
    const logs = entriesFor(med.id).filter(e => e.ts >= d0 && e.ts < d0 + 86400000).length;
    taken += Math.min(windows.length, logs);
  }
  return { scheduled, taken };
}
// Take the caregiver to the card that can log the dose. NOT a second logging path -- that card
// already carries the ceiling check, the gap check and the override. The highlight goes through
// state, not onto the node: this app re-renders on a tick, so anything written to the element is
// wiped within a second and the ring would flash and vanish on a real phone.
function scrollToMedCard(medId) {
  const safe = String(medId).replace(/[^A-Za-z0-9_-]/g, '');
  const el = document.querySelector('[data-med-card="' + safe + '"]');
  if (!el) return;
  try { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) { el.scrollIntoView(); }
  setState({ medFlash: safe });
  setTimeout(() => { if (state.medFlash === safe) setState({ medFlash: null }); }, 1800);
}

function setToast(msg) {""",
    'setToast')

# ---- the card, in THIS app's palette --------------------------------------------------------------
cut("""  // Temperature + Weight row
  parts.push(h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: '12px' } },""",
    """  // UP NEXT -- the first thing on Home, above the boxes that ask for a number.
  {
    const nx = nextDueDose(now);
    const prog = doseProgressToday(now);
    if (nx) {
      const mins = Math.max(0, Math.round((nx.at - now) / 60000));
      const whenWords = nx.openNow ? 'Due now'
        : mins < 60 ? ('Due in ' + mins + ' minute' + (mins === 1 ? '' : 's'))
        : ('Due at ' + fmtTime(nx.at));
      const firstDose = nx.med.doses && nx.med.doses.length ? nx.med.doses[0].label : null;
      const sub = [firstDose, nx.med.sub || null].filter(Boolean).join(' \\u00b7 ');
      const ringPct = prog.scheduled > 0 ? Math.min(100, Math.round(prog.taken / prog.scheduled * 100)) : 0;
      parts.push(h('section', { 'data-home': 'up-next', style: {
        position: 'relative', overflow: 'hidden', borderRadius: '20px', padding: '18px 18px 16px', color: '#FFFFFF',
        background: 'linear-gradient(152deg, #C2678F 0%, #AA5375 50%, #7E3454 100%)',
        boxShadow: '0 10px 30px -12px rgba(126,52,84,0.50), 0 1px 2px rgba(126,52,84,0.20)' } },
        h('div', { style: { display: 'flex', alignItems: 'flex-start', gap: '14px' } },
          h('div', { style: { flex: '1', minWidth: '0' } },
            h('div', { style: { fontSize: '11.5px', fontWeight: '800', letterSpacing: '0.09em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.82)' } }, 'Up next'),
            // A medication name is the one string here that must never be trimmed -- it is what the
            // caregiver is about to act on.
            h('div', { style: { fontSize: '23px', fontWeight: '800', letterSpacing: '-0.02em', lineHeight: '1.15', marginTop: '3px', overflowWrap: 'anywhere' } }, nx.med.name),
            sub ? h('div', { style: { fontSize: '14px', fontWeight: '500', color: 'rgba(255,255,255,0.88)', marginTop: '4px' } }, sub) : null,
            h('div', { style: { fontSize: '13.5px', fontWeight: '700', color: 'rgba(255,255,255,0.95)', marginTop: '7px' } },
              whenWords + (nx.st.windowName ? ' \\u00b7 ' + nx.st.windowName : ''))
          ),
          prog.scheduled > 0 ? h('div', { role: 'img',
            'aria-label': prog.taken + ' of ' + prog.scheduled + ' scheduled doses logged today',
            style: { flexShrink: '0', width: '56px', height: '56px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'conic-gradient(#FFFFFF ' + ringPct + '%, rgba(255,255,255,0.26) 0)' } },
            h('div', { style: { width: '45px', height: '45px', borderRadius: '50%', background: 'rgba(140,60,95,0.94)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '2px' } },
              h('div', { style: { fontSize: '14px', fontWeight: '800', letterSpacing: '-0.02em' } }, prog.taken + '/' + prog.scheduled),
              h('div', { style: { fontSize: '8px', fontWeight: '700', letterSpacing: '0.07em', color: 'rgba(255,255,255,0.8)' } }, 'DOSES')
            )
          ) : null
        ),
        h('button', { onClick: () => scrollToMedCard(nx.med.id), style: { marginTop: '15px', width: '100%', minHeight: '48px', borderRadius: '14px', border: '0', background: '#FFFFFF', color: '#8E3D61', fontSize: '16px', fontWeight: '800', boxShadow: '0 3px 10px rgba(0,0,0,0.14)' } },
          nx.openNow ? 'Go to ' + nx.med.name : 'Show me the card')
      ));
    } else if (prog.scheduled > 0 && prog.taken >= prog.scheduled) {
      // A screen that answers "what is next" by going blank looks broken at the moment it should
      // feel finished.
      parts.push(h('section', { 'data-home': 'up-next', style: { borderRadius: '20px', padding: '16px 18px', background: '#E9F6F0', border: '1px solid #BFE3D5', display: 'flex', alignItems: 'center', gap: '13px' } },
        h('div', { style: { flexShrink: '0', width: '38px', height: '38px', borderRadius: '50%', background: '#0F9D6B', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '19px', fontWeight: '800' } }, '\\u2713'),
        h('div', { style: { minWidth: '0' } },
          h('div', { style: { fontSize: '16px', fontWeight: '800', color: '#0A5A40' } }, 'All scheduled doses are in'),
          h('div', { style: { fontSize: '13.5px', fontWeight: '500', color: '#2E6B55', marginTop: '2px' } },
            'Nothing else is scheduled today. As-needed medications are still available below.')
        )
      ));
    }
  }

  // Temperature + Weight row
  parts.push(h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: '12px' } },""",
    'the vitals row')

cut("""const APP_VERSION = 'beta-v62';""", """const APP_VERSION = 'beta-v63';""", 'APP_VERSION')
# ---- the hook the hero scrolls to, and the state the highlight lives in ---------------------------
# An explicit data- attribute, not a text selector: a medication name is user text that can repeat
# or contain markup characters, and this project has already selected the wrong one of three buttons
# on a card that way.
_c = "    return h('div', { style: { background: st.chemoBlock ? 'rgba(192,69,59,0.09)' : 'rgba(255,255,255,0.55)', backdropFilter: 'blur(16px)',"
if src.count(_c) != 1:
    die('the medication card wrapper is not where it was (found ' + str(src.count(_c)) + ')')
src = src.replace(_c,
  "    const medHook = String(med.id).replace(/[^A-Za-z0-9_-]/g, '');\n"
  "    const flashed = state.medFlash === medHook;\n"
  "    return h('div', { 'data-med-card': medHook, 'data-flash': flashed ? 'on' : null, style: { boxShadow: flashed ? '0 0 0 3px rgba(170,83,117,0.60)' : undefined, transition: 'box-shadow .25s ease', background: st.chemoBlock ? 'rgba(192,69,59,0.09)' : 'rgba(255,255,255,0.55)', backdropFilter: 'blur(16px)',", 1)

cut("""let state = { dateOffsetDays: 0,""", """let state = { medFlash: null, dateOffsetDays: 0,""", 'the state initialiser')

HTML.write_text(src, encoding='utf-8')
sw = SW.read_text(encoding='utf-8')
if 'chemowell-beta-v62' not in sw:
    die('the sw.js cache name is not where it was')
SW.write_text(sw.replace('chemowell-beta-v62', 'chemowell-beta-v63', 1), encoding='utf-8')
print("beta-v63 applied: Up next, in this app's own palette")
