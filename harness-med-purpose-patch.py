#!/usr/bin/env python3
"""
harness-med-purpose-patch.py -- beta-v61. Every medication says what it is for.

Aaron, 2026-09-08: "I've asked before to have something pulled from another site to say what the med
is intended for... it wasn't webMD, it was something else that couldn't sue me for using their
stuff." He was right that it never shipped, and the ask was not written down in ANY of the three
repos -- including this one, whose REQUESTS.md and BACKLOG.md have existed since app-v25.

ON THE SOURCE, because it was his actual worry. What cannot be copied is somebody's PROSE; the fact
that ondansetron prevents nausea is not ownable by anyone. So this ships SHORT ORIGINAL sentences
written for a patient -- nothing copied from WebMD, from a drug label, or from any site -- and the
app cites nothing, because a citation to a document nobody here read would be a lie. US federal
sources (openFDA, DailyMed, MedlinePlus) are public domain and would also have been safe to quote;
every one is blocked by the build sandbox's network policy, which is why the text is original rather
than quoted. Refreshing it to exact federal wording later is a data change into the same table.

WHY THIS DIFFERS FROM care-tracker's v74, SHIPPED THE SAME DAY. care-tracker has a fixed list
of thirteen medications, so its table is keyed by medication ID. ChemoWell has NO default list --
every user types their own -- so a table keyed by id would match nothing. Here the lookup is by
NAME, and by GENERIC NAME as a fallback, both lowercased and punctuation-stripped, so someone who
types "Zofran" and someone who types "ondansetron" both get the line. What the user typed in the
field always wins over the lookup, and a medication nobody recognises simply shows nothing.

WHAT IT DOES
  * MED_PURPOSE: one plain sentence per commonly-prescribed medication, keyed by lowercase name.
  * purposeOf(med): typed field > lookup on name > lookup on generic > '' (never an empty label).
  * "What it's for" is a real field in the medication editor, optional, free text.
  * The Meds screen shows it under the generic name, with ONE disclaimer above the list.
  * medicationFormFrom() carries the field, so editing a medication cannot silently wipe it. That is
    care-tracker's v43.3 failure class and this app has the identical seeder shape.
  * THE BUILT-IN LINE IS A PLACEHOLDER, NEVER A SEEDED VALUE. care-tracker's v74 seeded it as a
    value and the Zero Day Audit blocked that build twice over from the one root cause: clearing the
    box and saving did NOTHING while the app said "updated", so a line someone believed was wrong
    could be overwritten but never removed; and saving ANY edit froze that day's wording into the
    user's stored config, so a later correction would never reach a medication anyone had edited.
    Unset stays unset, typing overrides, clearing returns to the built-in line, nothing freezes.
    The placeholder is resolved from the NAME BEING TYPED, so it appears as soon as a recognised
    medication name is entered on a brand-new medication.

WHAT IT DELIBERATELY DOES NOT DO
  * Nothing on the Home quick-log cards -- that is the screen a patient taps when they feel awful,
    and every extra line sits between them and the dose button.
  * No runtime fetch. A live lookup would send a user's medication list to a third-party server and
    would fail exactly when they are offline. The text is in the file.
  * No dose, no schedule, no advice. Only what the medication is generally for.

Usage:  python3 harness-med-purpose-patch.py [--base <index.html>] [--out index.html]
The version stamp lives INSIDE this patch: it refuses a base that is not beta-v60 and emits beta-v61.
"""
import re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
FROM_V, TO_V = 'beta-v60', 'beta-v61'
FROM_C, TO_C = 'chemowell-beta-v60', 'chemowell-beta-v61'

args = sys.argv[1:]
base = args[args.index('--base') + 1] if '--base' in args else os.path.join(HERE, 'index.html')
out = args[args.index('--out') + 1] if '--out' in args else os.path.join(HERE, 'index.html')
sw_out = os.path.join(os.path.dirname(out) or '.', 'sw.js')

s = open(base, encoding='utf-8').read()
m = re.search(r"const APP_VERSION = '([^']+)';", s)
if not m or m.group(1) != FROM_V:
    sys.exit('REFUSING: base is %s, this patch transforms %s -> %s' % (m.group(1) if m else '?', FROM_V, TO_V))


def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n:
        sys.exit('REFUSING: expected %d match(es), found %d for:\n%s' % (n, c, old[:200]))
    s = s.replace(old, new)


# ---- 1. the table and the reader ---------------------------------------------------------------
rep("""function medicationFormFrom(med) {""", """// ---- WHAT EACH MEDICATION IS FOR (beta-v61) ----
// Short original sentences, written for a patient rather than a clinician. Nothing is copied from
// any site or label -- see this patch's header on why that is the safe answer. No dose, no
// schedule, no advice: only what the medication is generally used for.
// KEYED BY NAME, not by id: this app has no default medication list, so every entry is one the user
// typed. Both the brand name and the generic resolve to the same line.
// EVERY FEVER CLAUSE IS DELIBERATELY GONE, on care-tracker's audit finding the same day: a fever
// during chemo is a thing to REPORT, not to suppress, and a line that reads "brings down a fever" is
// the one sentence here most likely to change what somebody does at 2am in the wrong direction.
// "Gentle" is gone from senna, which is a stimulant laxative -- that was an editorial claim, not a
// fact. And "around chemo" / "after chemo" are gone because they are schedules written in words,
// which is what the guard in test/v72-med-purpose.mjs exists to catch.
const MED_PURPOSE = {
  'ondansetron': 'Prevents and settles nausea and vomiting.',
  'zofran': 'Prevents and settles nausea and vomiting.',
  'prochlorperazine': 'Settles nausea and vomiting.',
  'compazine': 'Settles nausea and vomiting.',
  'dexamethasone': 'A steroid that calms nausea, swelling and allergic reactions.',
  'decadron': 'A steroid that calms nausea, swelling and allergic reactions.',
  'acetaminophen': 'Eases pain.',
  'paracetamol': 'Eases pain.',
  'tylenol': 'Eases pain.',
  'ibuprofen': 'Eases pain and swelling.',
  'advil': 'Eases pain and swelling.',
  'morphine': 'A strong pain reliever for moderate to severe pain.',
  'oxycodone': 'A strong pain reliever for moderate to severe pain.',
  'hydrocodone': 'A strong pain reliever for moderate to severe pain.',
  'tramadol': 'A pain reliever for moderate pain.',
  'gabapentin': 'Eases nerve pain, and is also used for some seizures.',
  'lidocaine': 'A numbing cream for soreness in one spot on the skin.',
  'pantoprazole': 'Lowers stomach acid, which protects the stomach and eases reflux.',
  'protonix': 'Lowers stomach acid, which protects the stomach and eases reflux.',
  'omeprazole': 'Lowers stomach acid, which protects the stomach and eases reflux.',
  'famotidine': 'Lowers stomach acid, which eases reflux and heartburn.',
  'senna': 'A laxative for constipation.',
  'senokot': 'A laxative for constipation.',
  'docusate': 'A stool softener for constipation.',
  'polyethylene glycol': 'A laxative that draws water into the gut to ease constipation.',
  'miralax': 'A laxative that draws water into the gut to ease constipation.',
  'loperamide': 'Slows the gut down to control diarrhea.',
  'imodium': 'Slows the gut down to control diarrhea.',
  'lorazepam': 'Eases anxiety, and is also used for sickness and sleep.',
  'ativan': 'Eases anxiety, and is also used for sickness and sleep.',
  'buspirone': 'Eases anxiety.',
  'paroxetine': 'Treats depression, and is also used for anxiety.',
  'sertraline': 'Treats depression, and is also used for anxiety.',
  'ferrous sulfate': 'An iron supplement, for low iron levels.',
  'iron': 'An iron supplement, for low iron levels.',
  'filgrastim': 'Helps the body make white blood cells.',
  'neupogen': 'Helps the body make white blood cells.',
  'pegfilgrastim': 'Helps the body make white blood cells.',
  'allopurinol': 'Lowers uric acid levels.',
  'diphenhydramine': 'An antihistamine, used for allergic reactions and to help with sleep.',
  'benadryl': 'An antihistamine, used for allergic reactions and to help with sleep.'
};
// Lowercased, and stripped of anything but letters, digits and single spaces, so "Zofran (ODT)" and
// "zofran" land on the same key.
function medPurposeKey(text) {
  return String(text || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\\s+/g, ' ').trim();
}
// What the user typed wins; then the name; then the generic; otherwise nothing at all -- never an
// empty label under a medication nobody has described.
// hasOwnProperty, NOT a bare index. MED_PURPOSE is a plain object, so MED_PURPOSE['constructor']
// reads back Object.prototype.constructor -- a FUNCTION, truthy and not a string -- and h() then
// throws inside the Meds list render. The medication persists, so every later render throws too and
// the Meds screen comes up with no cards at all, which is the only place edit and delete live.
// Here the key comes from the NAME the user typed, so it is reachable by typing "constructor" or
// "Constructor" or "to string" as a medication name. care-tracker's Zero Day Audit blocked its v74
// on exactly this, in the id-keyed version of the same lookup, the same day.
function purposeLookup(key) {
  const k = medPurposeKey(key);
  if (!k || !Object.prototype.hasOwnProperty.call(MED_PURPOSE, k)) return '';
  const v = MED_PURPOSE[k];
  return typeof v === 'string' ? v : '';
}
function purposeOf(med) {
  if (!med) return '';
  const typed = String(med.purpose || '').trim();
  if (typed) return typed;
  return purposeLookup(med.name) || purposeLookup(med.sub);
}
function medicationFormFrom(med) {""")

# ---- 2. the editor seeds and saves it ----------------------------------------------------------
# The seeder did not carry the field. Without this, opening any medication's editor and saving would
# write an empty string over the line -- care-tracker's v43.3 failure exactly, in the same shape of
# function. Seeded with purposeOf() so the box shows what the screen shows.
rep("""    name: base.name || '',
    sub: base.sub || '',
    note: base.note || '',""",
    """    name: base.name || '',
    sub: base.sub || '',
    purpose: base.purpose || '',
    note: base.note || '',""")

rep("""    sub: String(form.sub || '').trim(),""",
    """    sub: String(form.sub || '').trim(),
    purpose: String(form.purpose || '').trim(),""")

# ---- 3. the field in the editor -----------------------------------------------------------------
rep("""      h('label', null, fieldLabel('Generic name'), formInput({ value: form.sub, place""",
    """      h('label', { style: { gridColumn: '1 / -1' } }, fieldLabel('What it\u2019s for'), formInput({ value: form.purpose, placeholder: (purposeOf({ name: (state.medEditor && state.medEditor.form && state.medEditor.form.name) || '', sub: (state.medEditor && state.medEditor.form && state.medEditor.form.sub) || '' }) || 'For example: settles nausea'), onInput: event => updateMedicationForm('purpose', event.target.value) })),
      h('label', null, fieldLabel('Generic name'), formInput({ value: form.sub, place""")

# ---- 4. the Meds screen shows it, with one disclaimer above the list -----------------------------
# The anchor MUST carry its own closing paren. Without it the replacement left `: null)` followed by
# the source's own `)`, an unbalanced paren that broke the whole module -- caught by parse-checking
# the extracted script against the unpatched baseline, which parses clean.
rep("""          h('div', { style: { fontSize: '12px', color: '#6E5261', fontWeight: '600', marginTop: '1px' } }, med.sub || 'No generic name')""",
    """          h('div', { style: { fontSize: '12px', color: '#6E5261', fontWeight: '600', marginTop: '1px' } }, med.sub || 'No generic name'),
          purposeOf(med) ? h('div', { 'data-med-purpose': med.id, style: { fontSize: '12.5px', color: '#5F4A56', fontWeight: '500', marginTop: '4px', lineHeight: '1.35' } }, purposeOf(med)) : null""")
rep("""    h('div', { 'data-tour-meds': 'true', style: { display: 'flex', flexDirection: 'column', gap: '9px' } }, ...cards)""",
    """    h('div', { 'data-med-disclaimer': 'true', style: { fontSize: '11.5px', color: '#7D6974', lineHeight: '1.4', margin: '2px 0 10px' } },
      'The line under each medication is general information, not medical advice. Your care team is the answer for anything specific.'),
    h('div', { 'data-tour-meds': 'true', style: { display: 'flex', flexDirection: 'column', gap: '9px' } }, ...cards)""")

# ---- 5. version and cache ------------------------------------------------------------------------
rep("const APP_VERSION = '%s';" % FROM_V, "const APP_VERSION = '%s';" % TO_V)

open(out, 'w', encoding='utf-8').write(s)

sw_path = os.path.join(os.path.dirname(out) or '.', 'sw.js')
sw = open(sw_path, encoding='utf-8').read()
if FROM_C not in sw: sys.exit('REFUSING: sw.js cache is not %s' % FROM_C)
open(sw_path, 'w', encoding='utf-8').write(sw.replace(FROM_C, TO_C))
print('patched %s -> %s (cache %s -> %s)' % (FROM_V, TO_V, FROM_C, TO_C))
