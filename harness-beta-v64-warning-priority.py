#!/usr/bin/env python3
"""beta-v63 -> beta-v64: a red overdose warning is silently replaced by an amber timing notice.

FOUND WHILE FIXING THE SAME DEFECT IN THE CHEMOWELL PRODUCT, and it is worse here because this is
the shape the product inherited FROM this code.

`state.warn` is a single slot, and afterLog's iron/protonix branch sets an amber warning and
RETURNS before any ceiling check runs. So:

  1. The caregiver takes the day to the 2,500 mg acetaminophen limit, then logs one more Tylenol
     through the app's own override. A red banner appears: "Acetaminophen ceiling exceeded ... Do
     not give more without contacting the care team."
  2. She taps "Take all" on the evening meds, which include Iron.
  3. Protonix was logged within the last two hours, so afterLog({medId:'iron'}) fires the amber
     "Iron + Protonix timing" notice into the SAME slot.

The overdose warning is gone from the screen, with nothing to say it was ever there, replaced by a
note about absorption timing. Which warning she ends up looking at depends on what she happened to
tap next. `harness/warning-priority-test.mjs` reproduces exactly that, on the rendered banner.

THE SECOND DEFECT, found writing the harness: "Take all" called afterLog for iron and nothing else
(`if (ids.includes('iron'))`). A batch that pushed some other medication past its own configured
daily limit raised no warning whatsoever, because iron was the only medication the batch ever asked
about.

The fix is the shape the product uses: collect every warning a dose earns, show the worst one, and
never let an amber displace a red the caregiver is still looking at.
"""
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
HTML, SW = ROOT / 'index.html', ROOT / 'sw.js'

def die(msg):
    print('PATCH FAILED: ' + msg); sys.exit(1)

src = HTML.read_text(encoding='utf-8')
if 'EVERY WARNING THIS DOSE EARNS' in src:
    die('already applied')

start = src.index('function afterLog(entry) {')
end = src.index('\n}\n\nasync function logMed(', start)
body = src[start:end]
for needle in ["Iron + Protonix timing", "Acetaminophen ceiling exceeded", "dailyCeiling(configuredMedication)"]:
    if needle not in body:
        die('afterLog is not shaped as expected (missing ' + needle + ') -- nothing written')

NEW = '''function afterLog(entry) {
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
    // NO `return` HERE. That return is half the defect: it meant an iron dose could never also
    // report a ceiling, and that this amber always won whatever was already on screen.
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
  // AN AMBER NEVER DISPLACES A RED THE CAREGIVER IS STILL LOOKING AT. The red banner stays until
  // she taps the x on it, and while an overdose warning is on the screen it is the thing she has to
  // deal with -- a note about iron absorption timing is not a reason to take it away. A red may
  // still replace a red: the newer figure is the one that matters. This is deliberately checked
  // against what is ON SCREEN and not against a per-batch flag, because the reported failure
  // crosses taps: the red came from a Tylenol dose and the amber from a later "Take all".
  if (state.warn && state.warn.tone === 'red' && worst.tone !== 'red') return;
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
    setTimeout(() => { ids.forEach(mid => afterLog({ medId: mid, ts, id: 'pending' })); }, 500);""",
    "take-all's afterLog call")

# TWO SEPARATE 320px OVERFLOWS ON HOME, and only one of them is beta-v63's.
#
# THE ONE THAT IS OURS: the hero's button. `'Go to ' + name` on a width:100% button with no wrapping
# rule cannot break a long pasted medication name, so the button's min-content width becomes the
# card's. It is one line now, and a long name gets the generic label; the name itself is on the card
# the button goes to, in full. This is the same finding the ChemoWell audit made against the same
# card in the same week.
#
# THE ONE THAT IS NOT: the MISSED-DOSE BANNER, which has never wrapped a medication name and does
# not depend on this release at all. One unbroken 62-character name takes Home to 655px on a 320px
# phone and carries two of the five bottom tabs off the side -- with the banner naming the very
# medication whose card the caregiver would need. Measured on `beta-v62`, before the hero existed:
# 51/53, the same two checks red. `harness/med-purpose-test.mjs` has been reporting it and it was
# read as noise. The banner's text now wraps, and its flex parent gets `minWidth: 0`, without which
# a flex item refuses to shrink below its own min-content and the wrap changes nothing.
cut("""      h('div', { style: { flex: '1' } },
        h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '4px' } },
          h('div', { style: { fontWeight: '800', color: '#C0453B', fontSize: '15.5px', letterSpacing: '0.02em', textTransform: 'uppercase' } }, 'Missed dose'""",
    """      h('div', { style: { flex: '1', minWidth: '0' } },
        h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '4px' } },
          h('div', { style: { fontWeight: '800', color: '#C0453B', fontSize: '15.5px', letterSpacing: '0.02em', textTransform: 'uppercase' } }, 'Missed dose'""",
    "the missed-dose banner's flex column")

cut("""        h('div', { style: { color: '#A13830', fontSize: '14px', fontWeight: '600', lineHeight: '1.5' } },
          bannerItems.map(m => m.when""",
    """        h('div', { style: { color: '#A13830', fontSize: '14px', fontWeight: '600', lineHeight: '1.5', overflowWrap: 'anywhere' } },
          bannerItems.map(m => m.when""",
    "the missed-dose banner's text")

cut("""        h('button', { onClick: () => scrollToMedCard(nx.med.id), style: { marginTop: '15px', width: '100%', minHeight: '48px', borderRadius: '14px', border: '0', background: '#FFFFFF', color: '#8E3D61', fontSize: '16px', fontWeight: '800', boxShadow: '0 3px 10px rgba(0,0,0,0.14)' } },
          nx.openNow ? 'Go to ' + nx.med.name : 'Show me the card')""",
    """        h('button', { onClick: () => scrollToMedCard(nx.med.id), style: { marginTop: '15px', width: '100%', minHeight: '48px', padding: '0 14px', borderRadius: '14px', border: '0', background: '#FFFFFF', color: '#8E3D61', fontSize: '16px', fontWeight: '800', boxShadow: '0 3px 10px rgba(0,0,0,0.14)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } },
          (nx.openNow && String(nx.med.name).length <= 22) ? ('Go to ' + nx.med.name) : 'Show me the card')""",
    "the hero button")

cut("""const APP_VERSION = 'beta-v63';""", """const APP_VERSION = 'beta-v64';""", 'APP_VERSION')
HTML.write_text(src, encoding='utf-8')
sw = SW.read_text(encoding='utf-8')
if "chemowell-beta-v63" not in sw:
    die('the sw.js cache name is not where it was')
SW.write_text(sw.replace("chemowell-beta-v63", "chemowell-beta-v64", 1), encoding='utf-8')
print('beta-v64 applied: the red overdose warning survives the amber one')
