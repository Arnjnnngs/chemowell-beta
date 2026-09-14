#!/usr/bin/env python3
"""beta-v65 -- the phone's own Back button closed the app. Ported on Aaron's "Port to both".

Same defect, same class, same fix as care-tracker v77 and ChemoWell app-v81: `grep popstate`
returned nothing in any of the three apps, so the hardware Back button had never been handled
anywhere. Rule 5.5's class exactly -- every gate on this project asks about a still frame, and none
asks what happens while a finger is moving.

**THE REGISTRY IS READ OFF THIS FILE'S OWN STATE, NOT COPIED FROM THE SIBLING.** Staging's state is
close to production's and not the same: it has `testDateControlsOpen` and `medFlash` (TEST_MODE
only) and does NOT have `confirmRemoveWeight`, `missedBannerOpen` or `whatsNewOpen`. Copying
production's list would have invented rules for three things that do not exist here and left the
TEST_MODE panel unaccounted for. The suite's completeness check enumerates THIS app's state, so a
copied list would have failed it.

WRITE MODEL: this release writes no record of any kind. It adds one history entry and one listener,
and every action it takes is one the screen already offers through a Cancel or close control. It
cannot reach `addEntryDB` or `removeEntryDB`, and it does not touch `caretracker_test_entries` or
any other collection.
"""
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / 'index.html'

def die(msg):
    print('PATCH FAILED: ' + msg); sys.exit(1)

def cut(src, old, new, what):
    if src.count(old) != 1:
        die(what + ' is not where it was (' + str(src.count(old)) + ' matches) -- nothing written')
    return src.replace(old, new, 1)

src = HTML.read_text(encoding='utf-8')
if 'BACK_LAYERS' in src:
    die('already applied')

BLOCK = """// ---- THE PHONE'S OWN BACK BUTTON -------------------------------------------------------------
// Ordered INNERMOST FIRST. Each layer says how to tell it is open and how to close it, and closing
// it is exactly what that layer's own Cancel or close control does -- if the two ever disagree,
// Back becomes a second way out of a screen that leaves different state behind.
//
// READ OFF THIS FILE'S STATE, NOT COPIED FROM PRODUCTION. Staging does not have
// `confirmRemoveWeight`, `missedBannerOpen` or `whatsNewOpen`, and production does not have the
// TEST_MODE date panel. A copied list would have carried rules for three things that do not exist.
const BACK_LAYERS = [
  // 1. CONFIRMATIONS FIRST -- they sit on top of whatever armed them.
  { key: 'confirmDeleteMed', label: 'the delete-medication confirmation', open: () => state.confirmDeleteMed != null, close: () => setState({ confirmDeleteMed: null }) },
  { key: 'confirmRemove', label: 'the remove-entry confirmation', open: () => state.confirmRemove != null, close: () => setState({ confirmRemove: null }) },
  { key: 'confirmRemovePara', label: 'the remove-paracentesis confirmation', open: () => state.confirmRemovePara != null, close: () => setState({ confirmRemovePara: null }) },
  { key: 'confirmMedList', label: 'the medication-list confirmation', open: () => !!state.confirmMedList, close: () => setState({ confirmMedList: false }) },
  { key: 'confirmClearChemo', label: 'the clear-treatment-date confirmation', open: () => !!state.confirmClearChemo, close: () => setState({ confirmClearChemo: false }) },
  { key: 'reportConfirmClear', label: 'the clear-reports confirmation', open: () => !!state.reportConfirmClear, close: () => setState({ reportConfirmClear: false }) },
  { key: 'apptConfirmDelete', label: 'the delete-appointment confirmation', open: () => state.apptConfirmDelete != null, close: () => setState({ apptConfirmDelete: null }) },
  { key: 'shareArmed', label: 'the armed share control', open: () => !!state.shareArmed, close: () => setState({ shareArmed: false }) },
  { key: 'override', label: 'the over-limit override', open: () => state.override != null, close: () => setState({ override: null }) },
  // 2. SHEETS AND POP-UPS.
  { key: 'timeModal', label: 'the confirm-the-time sheet', open: () => state.timeModal != null, close: () => setState({ timeModal: null }) },
  { key: 'missReasonSheet', label: 'the missed-dose reason sheet', open: () => state.missReasonSheet != null, close: () => setState({ missReasonSheet: null }) },
  { key: 'apptSheet', label: 'the appointment sheet', open: () => state.apptSheet != null, close: () => setState({ apptSheet: null }) },
  { key: 'backupNotice', label: 'the backup notice', open: () => state.backupNotice != null, close: () => setState({ backupNotice: null }) },
  { key: 'reportNotice', label: 'the report notice', open: () => state.reportNotice != null, close: () => setState({ reportNotice: null }) },
  { key: 'bkLocked', label: 'the locked-backup prompt', open: () => state.bkLocked != null, close: () => setState({ bkLocked: null }) },
  { key: 'tour', label: 'the guided tour', open: () => state.tour != null, close: () => setState({ tour: null }) },
  // 3. PANELS AND EDITORS.
  { key: 'medEditor', label: 'the medication editor', open: () => state.medEditor != null, close: () => setState({ medEditor: null, confirmDeleteMed: null }) },
  { key: 'drawerOpen', label: 'the menu drawer', open: () => !!state.drawerOpen, close: () => setState({ drawerOpen: false }) }
];
function backLayerKeys() { return BACK_LAYERS.map(l => l.key); }
function handleBackPress() {
  // NESTED, one level inside `medsync`, where a rule over top-level keys cannot see it. Handled
  // explicitly and first for that reason.
  if (state.medsync && state.medsync.confirm) {
    setState({ medsync: Object.assign({}, state.medsync, { confirm: null }) });
    return 'medsync.confirm';
  }
  for (let i = 0; i < BACK_LAYERS.length; i++) {
    if (BACK_LAYERS[i].open()) { BACK_LAYERS[i].close(); return BACK_LAYERS[i].key; }
  }
  if (state.view !== 'home') { setState({ view: 'home' }); return 'view'; }
  return null;
}
function armBackButton() {
  if (typeof window === 'undefined' || !window.history || !window.addEventListener) return;
  try { history.pushState({ ctBack: 1 }, ''); } catch (e) { return; }
  let leaving = false;
  window.addEventListener('popstate', () => {
    const handled = handleBackPress();
    if (handled) { try { history.pushState({ ctBack: 1 }, ''); } catch (e) {} return; }
    // NOTHING LEFT, SO LET THE PHONE LEAVE -- ON ONE PRESS, NOT TWO. Without this the first Back on
    // Home silently consumed the entry pushed at startup and did nothing visible, so it took two
    // presses to get out where every other app takes one.
    if (leaving) return;
    leaving = true;
    try { history.back(); } catch (e) {}
    setTimeout(() => { leaving = false; }, 0);
  });
}
if (typeof window !== 'undefined') {
  window.__backTest = { keys: backLayerKeys, press: handleBackPress, stateKeys: () => Object.keys(state) };
}

function setState(patch) {"""

src = cut(src, "function setState(patch) {", BLOCK, 'setState')

src = cut(src, """  checkNotifications();
}, 1000);
render();""",
"""  checkNotifications();
}, 1000);
// ARMED HERE, at module top level and after `state` exists. pushState would be harmless earlier;
// the popstate handler calls setState, which reads `state`.
armBackButton();
render();""", 'the startup tail')

HTML.write_text(src, encoding='utf-8')
print('beta-v65 applied: the phone Back button walks the app instead of leaving it')
