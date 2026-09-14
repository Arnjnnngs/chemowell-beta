// up-next-test.mjs -- beta-v63. Home names the medication that is actually due, and never one the
// app itself says not to give.
//
// WHAT THIS PROTECTS. The hero names a medication and a caregiver acts on it. Three ways it hurts:
//   1. It names something already logged in its window, or blocked around a chemo day, or whose
//      course is finished -- every one of those tells somebody to give a dose the app is refusing.
//   2. It names an as-needed medication. Morphine available every four hours is not DUE at any
//      time, and a card headed "Up next" saying so invites a dose nobody asked for.
//   3. It vanishes when the day is done, so the screen answers "what is next" by going blank at the
//      moment it should feel finished.
//
// Mocked Firestore, never the real one (hard rule 4). The clock is frozen so the fixture cannot
// quietly stop testing anything depending on the hour it is run -- the ChemoWell port of this suite
// went vacuous exactly that way, and a mutant passed because of it.
//
// Run:  node harness/up-next-test.mjs [--file <index.html>]
import { createRequire } from 'node:module';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = (() => {
  const _p = require('node:path');
  const tries = ['playwright', '/opt/node22/lib/node_modules/playwright',
    _p.join(_p.dirname(process.execPath), '..', 'lib', 'node_modules', 'playwright')];
  for (const c of tries) { try { return require(c); } catch (e) {} }
  throw new Error('playwright not found');
})();
const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const APP_FILE = argv.indexOf('--file') >= 0 ? argv[argv.indexOf('--file') + 1] : path.join(HERE, '..', 'index.html');
for (const v of ['HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy'])
  if (process.env[v]) { console.error('REFUSING: ' + v + ' set.'); process.exit(3); }

const html = fs.readFileSync(APP_FILE, 'utf8');
let pass = 0, fail = 0;
const t = (name, cond, detail) => {
  console.log('  ' + (cond ? 'PASS  ' : 'FAIL  ') + name + (detail ? '  |  ' + detail : ''));
  cond ? pass++ : fail++;
};
// 10:00 today, so "this morning" and "this evening" mean the same thing on every run.
const FROZEN = (() => { const d = new Date(); d.setHours(10, 0, 0, 0); return d.getTime(); })();
const D0 = (() => { const d = new Date(FROZEN); d.setHours(0,0,0,0); return d.getTime(); })();

const mkStub = (seed) => `
const store={entries:${JSON.stringify(seed)},prefs:{}};const eL=[],pL=[];let n=0;
function snap(l){return{docs:l.map(e=>({id:e.id,data:()=>{const c=Object.assign({},e);delete c.id;return c;}}))};}
export function getFirestore(){return{__db:true};} export function collection(){return{__kind:'col'};}
export function doc(db,col,id){return{__kind:'doc',id:id};} export function query(){return{__kind:'q'};}
export function orderBy(){return{};}
export function onSnapshot(ref,cb){if(ref&&ref.__kind==='q'){eL.push(cb);cb(snap(store.entries));return()=>{};}
 pL.push(cb);cb({exists:()=>true,data:()=>store.prefs});return()=>{};}
export async function addDoc(c,d){store.entries.push(Object.assign({id:'a'+(++n)},d));eL.forEach(f=>f(snap(store.entries)));return{id:'a'+n};}
export async function deleteDoc(){} export async function setDoc(){}
export async function getDocs(){return snap(store.entries);} export function serverTimestamp(){return Date.now();}`;
const SA = `export function initializeApp(c){return{name:'[DEFAULT]',options:c};}`;
const SM = `export function getMessaging(){throw new Error('off');} export async function getToken(){return null;} export function onMessage(){return()=>{};}`;

const server = http.createServer((rq, rs) => {
  if (rq.url.startsWith('/index.html')) { rs.writeHead(200, {'Content-Type':'text/html'}); rs.end(html); return; }
  rs.writeHead(204); rs.end();
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
const PORT = server.address().port;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const VER = (html.match(/const APP_VERSION = '([^']+)'/) || [])[1] || '';

const heroText = async (seed) => {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 900 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
  await ctx.route('**/*', route => {
    const u = route.request().url();
    if (u.includes('firebase-app.js')) return route.fulfill({ status:200, contentType:'application/javascript', body: SA });
    if (u.includes('firebase-firestore.js')) return route.fulfill({ status:200, contentType:'application/javascript', body: mkStub(seed) });
    if (u.includes('firebase-messaging.js')) return route.fulfill({ status:200, contentType:'application/javascript', body: SM });
    if (u.startsWith('http://127.0.0.1:' + PORT)) return route.continue();
    return route.abort();
  });
  const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.addInitScript(({ v, frozen }) => {
    try { localStorage.setItem('caretracker-seen-version', v); } catch (e) {}
    const R = Date;
    const D = function (...a) { return a.length ? new R(...a) : new R(frozen); };
    D.now = () => frozen; D.parse = R.parse; D.UTC = R.UTC; D.prototype = R.prototype;
    window.Date = D;
  }, { v: VER, frozen: FROZEN });
  await p.goto('http://127.0.0.1:' + PORT + '/index.html', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(2600);
  const el = p.locator('[data-home="up-next"]');
  const txt = await el.count() ? (await el.first().innerText()).replace(/\s+/g, ' ').trim() : null;
  await ctx.close();
  return { txt, errs };
};

console.log('\n1. IT NAMES A SCHEDULED MEDICATION THAT IS DUE, NOT AN AS-NEEDED ONE');
{
  const { txt, errs } = await heroText([]);
  t('the hero is on Home', txt !== null, String(txt));
  // Morphine, Tylenol, Zofran and Imodium are this app's as-needed medications: available on a gap
  // timer, never DUE. None of them may ever appear here.
  t('never an as-needed medication',
    !/Morphine|Tylenol|Zofran|Imodium|Lidocaine/i.test(String(txt)), String(txt));
  t('and it names one of the scheduled ones',
    /Protonix|Buspirone|Paroxetine|Iron|Compazine|Senokot|Dexamethasone/i.test(String(txt)), String(txt));
  t('no page error', errs.length === 0, errs.join(' | '));
}

console.log('\n2. A MEDICATION ALREADY LOGGED IN ITS WINDOW IS NOT "UP NEXT"');
{
  // Protonix's morning window is 8-10; the frozen clock is 10:00. Log it inside that window and it
  // must stop being the answer.
  const before = (await heroText([])).txt;
  const named = (String(before).match(/UP NEXT (\w+)/) || [])[1] || '';
  const after = (await heroText([
    { id: 'l1', medId: named.toLowerCase(), kind: 'med', ts: D0 + 8.5 * 3600000, dose: 'logged', mg: 0 }
  ])).txt;
  t('the fixture named a medication to log', !!named, String(before));
  t('and once logged in its window it is no longer the one named',
    !new RegExp('UP NEXT ' + named).test(String(after)), String(after));
}

console.log('\n3. THE DOSE COUNT IS REAL');
{
  const { txt } = await heroText([]);
  const m = String(txt).match(/(\d+)\/(\d+) DOSES/);
  t('the ring shows a count', !!m, String(txt));
  if (m) {
    t('nothing logged means none taken', Number(m[1]) === 0, m[0]);
    t('and more than zero are scheduled', Number(m[2]) > 0, m[0]);
  }
}

console.log('\n4. WITH EVERY SCHEDULED DOSE LOGGED, IT SAYS SO -- IT DOES NOT FALL BACK TO AN AS-NEEDED ONE');
{
  // WHY THIS SECTION EXISTS. Section 1's as-needed check could not fail: a scheduled medication is
  // always available earlier in list order, so it won every comparison and the as-needed ones were
  // never reached. Deleting the `type === 'gap'` guard entirely left the suite green. The only
  // state where the exclusion is actually load-bearing is a day with every scheduled dose already
  // logged -- and that is exactly the moment a caregiver is most likely to act on whatever the card
  // says next.
  const scheduled = ['protonix', 'buspirone', 'paroxetine', 'iron', 'compazine', 'senokot', 'dexamethasone'];
  const seed = [];
  let n = 0;
  for (const id of scheduled) {
    // One log inside each hour a window could plausibly sit in. `Math.min(windows.length, logs)`
    // caps the count, so over-seeding cannot make the ring read more than 100%.
    for (const hour of [8, 10, 12, 14, 16, 18, 20, 22]) {
      seed.push({ id: 'f' + (++n), medId: id, kind: 'med', ts: D0 + hour * 3600000, dose: 'logged', mg: 0 });
    }
  }
  const { txt, errs } = await heroText(seed);
  t('the card is still there when the day is finished', txt !== null, String(txt));
  t('and it says the day is done', /scheduled doses are in/i.test(String(txt)), String(txt));
  t('rather than naming an as-needed medication',
    !/Morphine|Tylenol|Zofran|Imodium|Lidocaine/i.test(String(txt)), String(txt));
  t('no page error', errs.length === 0, errs.join(' | '));
}

console.log('\n7. A LONG PASTED NAME DOES NOT PUSH HOME SIDEWAYS AT 320px');
{
  // BETA-V63 SHIPPED THIS BUG AND THIS SUITE DID NOT SEE IT. `'Go to ' + name` on a width:100%
  // button with no wrapping rule cannot break a long unbroken name, so the button's min-content
  // width became the page's: Home measured 334px on a 320px phone and one of the five bottom tabs
  // went off the side -- the same shape as the app-v75 Home overflow this repo has already paid
  // for. `harness/med-purpose-test.mjs` caught it after the fact; it belongs here too, on the card
  // that introduced it.
  // ONE UNBROKEN 62-CHARACTER RUN, not a phrase. A long name made of ordinary words wraps on its
  // spaces and never pushes anything sideways, so a fixture built from words tests the button's
  // height and nothing else. The pasted names that break this app are label text with no spaces.
  const LONG = 'HydroxyprogesteroneCaproateExtendedReleaseSuspensionIntramuscular Kit';
  const c = await browser.newContext({ viewport: { width: 320, height: 780 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
  await c.route('**/*', route => {
    const u = route.request().url();
    if (u.includes('firebase-app.js')) return route.fulfill({ status:200, contentType:'application/javascript', body: SA });
    if (u.includes('firebase-firestore.js')) return route.fulfill({ status:200, contentType:'application/javascript', body: mkStub([]) });
    if (u.includes('firebase-messaging.js')) return route.fulfill({ status:200, contentType:'application/javascript', body: SM });
    if (u.startsWith('http://127.0.0.1:' + PORT)) return route.continue();
    return route.abort();
  });
  const pg = await c.newPage();
  const errs = []; pg.on('pageerror', e => errs.push(String(e)));
  await pg.addInitScript(({ v, frozen, long }) => {
    try {
      localStorage.setItem('caretracker-seen-version', v);
      // The pasted name goes on Protonix, whose morning window is open at the frozen 10:00, so it
      // is the medication the hero names -- otherwise the card under test never renders.
      localStorage.setItem('caretracker-medication-config-v1', JSON.stringify({ version: 1, archivedMeds: [], meds: [
        { id: 'protonix', name: long, sub: 'Pantoprazole', type: 'win', alerts: true,
          windows: [{ start: 8, end: 12, name: 'Morning' }], note: 'Twice daily' }
      ] }));
    } catch (e) {}
    const R = Date;
    const D = function (...a) { return a.length ? new R(...a) : new R(frozen); };
    D.now = () => frozen; D.parse = R.parse; D.UTC = R.UTC; D.prototype = R.prototype;
    window.Date = D;
  }, { v: VER, frozen: FROZEN, long: LONG });
  await pg.goto('http://127.0.0.1:' + PORT + '/index.html', { waitUntil: 'domcontentloaded' });
  await pg.waitForTimeout(2600);
  const m = await pg.evaluate(() => {
    const hero = document.querySelector('[data-home="up-next"]');
    const btn = hero && hero.querySelector('button');
    return {
      hero: !!hero,
      heroText: hero ? (hero.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 90) : null,
      // THE RULER IS THE VIEWPORT WIDTH THIS TEST SET, never window.innerWidth -- under mobile
      // emulation innerWidth grows with the content and a broken page measures as clean.
      doc: document.documentElement.scrollWidth,
      nav: (document.querySelector('nav') || { scrollWidth: -1 }).scrollWidth,
      btnH: btn ? Math.round(btn.getBoundingClientRect().height) : -1,
      btnText: btn ? (btn.innerText || '').trim() : null
    };
  });
  t('the hero renders with the pasted name', m.hero && new RegExp('Hydroxyprogesterone').test(String(m.heroText)), String(m.heroText));
  t('Home does not scroll sideways at 320px', m.doc <= 320, 'page=' + m.doc + 'px');
  t('and the bottom tab bar still fits', m.nav > 0 && m.nav <= 320, 'nav=' + m.nav + 'px');
  t('the hero button is one line', m.btnH > 0 && m.btnH <= 60, m.btnH + 'px');
  t('and a long name falls back to the generic label', m.btnText === 'Show me the card', String(m.btnText));
  t('no page error at 320px', errs.length === 0, errs.join(' | '));
  await c.close();
}

await browser.close();
server.close();
console.log('\n' + pass + '/' + (pass + fail) + ' checks passed' + (fail ? '  <-- FAIL' : ''));
process.exit(fail ? 1 : 0);
