#!/usr/bin/env python3
"""beta-v62 -> beta-v63: a red overdose warning is silently replaced by an amber timing notice.

FOUND WHILE FIXING THE SAME DEFECT IN THE CHEMOWELL PRODUCT, and it is worse here because this is
the shape the product inherited FROM this code.

`state.warn` is a single slot, and afterLog's iron/protonix branch sets an amber warning and
RETURNS before any ceiling check runs. So:

  1. The caregiver logs Tylenol past the daily acetaminophen limit. A red banner appears:
     "Acetaminophen ceiling exceeded ... Do not give more without contacting the care team."
  2. She taps "Take all" on the evening meds, which include Iron.
  3. If Protonix was logged within the last two hours, afterLog({medId:'iron'}) fires the amber
     "Iron + Protonix timing" notice, which OVERWRITES the red banner.

The overdose warning is gone from the screen, with nothing to say it was ever there, replaced by a
note about absorption timing. Which warning she ends up looking at depends on what she happened to
tap next.

The fix is the same shape the product uses: collect every warning this dose earns, then show the
worst one, and never let a red be replaced by an amber inside one batch.
"""
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
HTML, SW = ROOT / 'index.html', ROOT / 'sw.js'

def die(msg):
    print('PATCH FAILED: ' + msg); sys.exit(1)

src = HTML.read_text(encoding='utf-8')
if 'warnBatch' in src:
    die('already applied')

start = src.index('function afterLog(entry) {')
end = src.index('\n}\n\nasync function logMed(', start)
body = src[start:end]
for needle in ["Iron + Protonix timing", "Acetaminophen ceiling exceeded", "dailyCeiling(configuredMedication)"]:
    if needle not in body:
        die('afterLog is not shaped as expected (missing ' + needle + ') -- nothing written')

NEW = '''function afterLog(entry, warnBatch) {
  // EVERY WARNING THIS DOSE EARNS, THEN THE WORST ONE.
  // This used to be a chain of branches each calling setState({ warn }) into a single slot, with the
  // iron/protonix branch RETURNING before the ceiling check could run. A caregiver who had just been
  // shown "Acetaminophen ceiling exceeded -- do not give more without contacting the care team", and
  // who then tapped "Take all" on the evening meds, had that red banner replaced by an amber note
  // about iron absorption timing. The overdose warning simply left the screen, with nothing to say
  // it had been there. Which warning she was looking at depended on what she happened to tap next.
  const twoH = 2 * 3600000;
  const warnings = [];
  if (entry.medId === 'iron' || entry.medId === 'protonix') {
    const other = entry.medId === 'iron' ? 'protonix' : 'iron';
    const near = state.entries.find(e => e.medId === other && e.id !== entry.id && Math.abs(e.ts - entry.ts) <= twoH);
    // NO `return` HERE. That return is the defect: it meant an iron dose could never also report a
    // ceiling, and that this amber always won whatever was already on screen.
    if (near) warnings.push({ tone: 'amber', title: 'Iron + Protonix timing', body: 'Iron and Protonix were logged within 2 hours of each other. Protonix (a PPI) lowers stomach acid, which can markedly reduce iron absorption. Aim to separate the two by at least 2 hours.' });
  }
  if (entry.medId === 'tylenol' || entry.medId === 'tylenol-liquid') {
    const mg = tylenolMg();
    const tylenol = state.meds.find(med => med.id === 'tylenol');
    const limit = medicationCeilingMax(tylenol) || CONFIG.ceilingMg;
    const mgOver = mg > limit;
    let volOver = false, vol = 0, liquidMed = null;
    if (entry.medId === 'tylenol-liquid') {
      liquidMed = state.meds.find(med => med.id === 'tylenol-liquid');
      vol = dailyVolumeMl('tylenol-liquid');
      volOver = !!(liquidMed && liquidMed.volumeCeilingMl && vol > liquidMed.volumeCeilingMl);
    }
    if (mgOver && volOver) {
      warnings.push({ tone: 'red', title: 'Acetaminophen ceiling exceeded', body: "Today's Tylenol total is " + mg.toLocaleString() + " mg (above the " + limit.toLocaleString() + " mg daily limit) and Tylenol Liquid volume is " + vol + " mL (above the " + liquidMed.volumeCeilingMl + " mL daily limit). Do not give more without contacting the care team." });
    } else if (mgOver) {
      warnings.push({ tone: 'red', title: 'Acetaminophen ceiling exceeded', body: "Today's Tylenol total is " + mg.toLocaleString() + " mg, above the " + limit.toLocaleString() + " mg daily limit. Do not give more without contacting the care team." });
    } else if (volOver) {
      warnings.push({ tone: 'red', title: 'Tylenol Liquid volume ceiling exceeded', body: "Today's Tylenol Liquid total is " + vol + " mL, above the " + liquidMed.volumeCeilingMl + " mL daily limit. Do not give more without contacting the care team." });
    }
  } else {
    // NO LONGER AN `else` ON THE IRON BRANCH. It was one before, so a medication that is neither
    // tylenol nor iron reached its own configured ceiling check, but iron itself never did -- iron
    // has no ceiling today, which is the only reason that did not already matter.
    const configuredMedication = state.meds.find(med => med.id === entry.medId);
    const configuredLimit = dailyCeiling(configuredMedication);
    if (configuredLimit && configuredLimit.used > configuredLimit.max) {
      warnings.push({ tone: 'red', title: configuredMedication.name + ' daily limit exceeded', body: "Today's " + configuredMedication.name + ' total is ' + configuredLimit.used + ' ' + configuredLimit.unit + ', above the ' + configuredLimit.label + ' daily limit. Do not give more without contacting the care team.' });
    }
  }

  if (!warnings.length) return;
  const worst = warnings.find(w => w.tone === 'red') || warnings[0];
  // SCOPED TO ONE BATCH, NOT TO THE SESSION. "Take all" calls this once per medication, so a red
  // raised by the first must survive an amber raised by the third. It is deliberately NOT keyed on
  // state.warn, which is cleared only when the caregiver taps the x on the banner -- gating on that
  // would mean a red left on screen from an hour ago silently suppressed every later warning.
  if (warnBatch && warnBatch.red && worst.tone !== 'red') return;
  if (warnBatch && worst.tone === 'red') warnBatch.red = true;
  setState({ warn: worst });
'''
src = src[:start] + NEW + src[end:]

def cut(old, new, what):
    global src
    if src.count(old) != 1:
        die(what + ' is not where it was (found ' + str(src.count(old)) + ') -- nothing written')
    src = src.replace(old, new, 1)

# "Take all" checked only for iron, so no other medication in the group was ever checked at all --
# including one that had just crossed its own daily limit inside the same tap.
cut("""    setTimeout(() => { if (ids.includes('iron')) afterLog({ medId: 'iron', ts, id: 'pending' }); }, 500);""",
    """    // EVERY MEDICATION IN THE BATCH, not just iron. `if (ids.includes('iron'))` meant a "Take all"
    // that pushed something over its own configured daily limit raised no warning whatsoever,
    // because the only medication the batch ever asked about was iron.
    setTimeout(() => { const warnBatch = {}; ids.forEach(mid => afterLog({ medId: mid, ts, id: 'pending' }, warnBatch)); }, 500);""",
    "take-all's afterLog call")

cut("""const APP_VERSION = 'beta-v62';""", """const APP_VERSION = 'beta-v63';""", 'APP_VERSION')
HTML.write_text(src, encoding='utf-8')
sw = SW.read_text(encoding='utf-8')
if "chemowell-beta-v62" not in sw:
    die('the sw.js cache name is not where it was')
SW.write_text(sw.replace("chemowell-beta-v62", "chemowell-beta-v63", 1), encoding='utf-8')
print('beta-v63 applied: the red overdose warning survives the amber one')
