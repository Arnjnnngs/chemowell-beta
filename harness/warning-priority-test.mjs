// warning-priority-test.mjs -- beta-v63. A red overdose warning must not be replaced by an amber one.
//
// THE DEFECT, in the order it happens to a caregiver:
//   1. She logs Tylenol past the daily acetaminophen limit. A red banner appears reading
//      "Acetaminophen ceiling exceeded ... Do not give more without contacting the care team."
//   2. She taps "Take all" on the evening meds, which include Iron.
//   3. Protonix was logged within the last two hours, so afterLog({medId:'iron'}) fired the amber
//      "Iron + Protonix timing" notice -- into the SAME single `state.warn` slot.
//   4. The overdose warning is gone from the screen, with nothing to say it was ever there.
//
// `state.warn` is one slot and the iron branch set it and RETURNED before any ceiling check ran.
// Which warning she ends up looking at depended on what she happened to tap next.
//
// AND A SECOND DEFECT FOUND WRITING THIS: "Take all" called afterLog for iron ONLY
// (`if (ids.includes('iron'))`), so a batch that pushed some other medication over its own
// configured daily limit raised no warning at all -- the only medication the batch ever asked about
// was iron.
//
// ASSERTS ON THE RENDERED BANNER, not on a lifted function. The bug is that the wrong banner is on
// the screen; a unit test of the warning list would not have seen step 4 at all.
//
// Run:  node harness/warning-priority-test.mjs [--file <index.html>] [--shots <dir>]
import { createRequire } from 'node:module';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = (() => {
  const _p = require('node:path');
  const tries = ['playwright',
    _p.join(_p.dirname(process.execPath), '..', 'lib', 'node_modules', 'playwright'),
    '/opt/node22/lib/node_modules/playwright',
    '/home/claude/.npm-global/lib/node_modules/playwright'];
  for (const c of tries) { try { return require(c); } catch (e) {} }
  throw new Error('playwright not found');
})();
const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const APP_FILE = argv.indexOf('--file') >= 0 ? argv[argv.indexOf('--file') + 1] : path.join(HERE, '..', 'index.html');
const SHOTS = argv.indexOf('--shots') >= 0 ? argv[argv.indexOf('--shots') + 1] : null;
if (SHOTS) fs.mkdirSync(SHOTS, { recursive: true });
for (const v of ['HTTPS_PROXY', 'https_proxy', 'HTTP_PROXY', 'http_proxy'])
  if (process.env[v]) { console.error('REFUSING: ' + v + ' set.'); process.exit(3); }

const html = fs.readFileSync(APP_FILE, 'utf8');
let pass = 0, fail = 0;
const t = (name, cond, detail) => {
  console.log('  ' + (cond ? 'PASS  ' : 'FAIL  ') + name + (detail ? '  |  ' + detail : ''));
  cond ? pass++ : fail++;
};

// MOCKED FIRESTORE, never the real one (hard rule 4). Entries are seeded into the in-memory store
// before the app subscribes, so the app loads a day that is already over the ceiling -- which is
// the state the defect needs and is tedious to reach by tapping.
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
export async function getDocs(){return snap(store.entries);} export function serverTimestamp(){return Date.now();}
`;
const STUB_APP = `export function initializeApp(c){return{name:'[DEFAULT]',options:c};}`;
const STUB_MSG = `export function getMessaging(){throw new Error('off');}
export async function getToken(){return null;} export function onMessage(){return()=>{};}`;

const now = Date.now();
const d0 = new Date(); d0.setHours(12, 0, 0, 0);
const noon = d0.getTime();
// Over the acetaminophen ceiling for the day, and a Protonix dose 30 minutes ago so an Iron dose
// logged now falls inside the two-hour interaction window.
// THREE REAL DOSES, NOT ONE ENTRY WITH A BIG NUMBER IN IT. The first fixture wrote
// `dose: '1000 mg', mg: 4000` and the suite reported "no red warning" -- because the app derives the
// milligrams from the DOSE LABEL, not from the mg field, so the day totalled 1,000 mg and was never
// near the ceiling. The suite was right that no warning appeared and wrong about why, which is the
// most expensive kind of failing test: it accuses the code of the bug the fixture has.
const SEED = [
  { id: 's1', medId: 'tylenol', kind: 'med', ts: noon - 6 * 3600000, dose: '1000 mg', mg: 1000 },
  { id: 's2', medId: 'tylenol', kind: 'med', ts: noon - 4 * 3600000, dose: '1000 mg', mg: 1000 },
  { id: 's3', medId: 'tylenol', kind: 'med', ts: noon - 2 * 3600000, dose: '500 mg', mg: 500 },
  { id: 's4', medId: 'protonix', kind: 'med', ts: now - 30 * 60000, dose: '40 mg', mg: 40 }
];

const server = http.createServer((rq, rs) => {
  if (rq.url.startsWith('/index.html')) { rs.writeHead(200, { 'Content-Type': 'text/html' }); rs.end(html); return; }
  rs.writeHead(204); rs.end();
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
const PORT = server.address().port;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
await ctx.route('**/*', route => {
  const u = route.request().url();
  if (u.includes('firebase-app.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: STUB_APP });
  if (u.includes('firebase-firestore.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: mkStub(SEED) });
  if (u.includes('firebase-messaging.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: STUB_MSG });
  if (u.startsWith('http://127.0.0.1:' + PORT)) return route.continue();
  return route.abort();
});
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', e => errs.push(String(e)));
const VER = (html.match(/const APP_VERSION = '([^']+)'/) || [])[1] || '';
await page.addInitScript((v) => { try { localStorage.setItem('caretracker-seen-version', v); } catch (e) {} }, VER);
await page.goto('http://127.0.0.1:' + PORT + '/index.html', { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2600);
const shot = async (n) => { if (SHOTS) await page.screenshot({ path: path.join(SHOTS, n + '.png') }); };

// THE BANNER AS THE CAREGIVER SEES IT. Read from the live DOM, matched on the warning's own title
// text -- never document.body.textContent, which in a single-file app contains the source and so
// matches every string a check could look for.
const banner = () => page.evaluate(() => {
  const el = [...document.querySelectorAll('div')]
    .find(d => /ceiling exceeded|daily limit exceeded|Iron \+ Protonix timing/.test(d.innerText || '')
      && (d.innerText || '').length < 700);
  if (!el) return null;
  const txt = el.innerText || '';
  return { red: /ceiling exceeded|daily limit exceeded/.test(txt), amber: /Iron \+ Protonix timing/.test(txt),
           head: txt.split('\n')[0].slice(0, 70) };
});
const dismiss = async () => {
  await page.evaluate(() => {
    const b = document.querySelector('[aria-label="Dismiss warning"]');
    if (b) b.click();
  });
  await page.waitForTimeout(400);
};

console.log('\n1. THE APP LOADS OVER THE CEILING AND SAYS SO');
{
  t('no page error on load', errs.length === 0, errs.join(' | '));
  // Log one more Tylenol so afterLog runs on a day already past the limit.
  const logged = await page.evaluate(() => {
    const card = [...document.querySelectorAll('button')].find(b => /^1000 mg$/.test((b.innerText || '').trim()));
    if (!card) return false; card.click(); return true;
  });
  t('a Tylenol dose button was reachable on Home', logged === true);
  const confirmBtn = page.getByRole('button', { name: 'Confirm', exact: true });
  await confirmBtn.first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
  const confirm = await confirmBtn.count() > 0;
  if (confirm) await confirmBtn.first().click();
  await page.waitForTimeout(1600);
  await shot('01-red-banner');
  const b1 = await banner();
  t('the RED acetaminophen ceiling warning is on screen', !!b1 && b1.red,
    JSON.stringify(b1) + (confirm ? '' : ' (no confirm step)'));
}

console.log('\n2. AND AN AMBER TIMING NOTICE DOES NOT REPLACE IT');
{
  // Exactly what "Take all" does: log Iron while Protonix is inside the two-hour window, without
  // the caregiver dismissing the red banner first.
  const took = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => /^Take all/i.test((x.innerText || '').trim()));
    if (b) { b.click(); return 'take-all'; }
    return 'none';
  });
  await page.waitForTimeout(900);
  const c2 = page.getByRole('button', { name: /^(Confirm|Log all)/ });
  await c2.first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
  if (await c2.count()) await c2.first().click();
  await page.waitForTimeout(1800);
  await shot('02-after-take-all');
  const b2 = await banner();
  t('a Take all control was found', took === 'take-all', took);
  t('the red overdose warning is STILL the one on screen', !!b2 && b2.red && !b2.amber,
    JSON.stringify(b2));
}

console.log('\n3. THE AMBER NOTICE STILL WORKS ON ITS OWN');
{
  // Without this, section 2 would pass just as well on a build that never raised the amber warning
  // at all -- which is a way of "fixing" it that loses a real interaction warning.
  await dismiss();
  const b3a = await banner();
  t('the banner can be dismissed', b3a === null, JSON.stringify(b3a));
  const logged = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find(x => /^Take all/i.test((x.innerText || '').trim()));
    if (b) { b.click(); return true; } return false;
  });
  await page.waitForTimeout(900);
  const c2 = page.getByRole('button', { name: /^(Confirm|Log all)/ });
  await c2.first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
  if (await c2.count()) await c2.first().click();
  await page.waitForTimeout(1800);
  await shot('03-amber-alone');
  const b3 = await banner();
  t('with no red on screen, the Iron + Protonix notice is shown', !!b3 && b3.amber,
    JSON.stringify(b3) + ' (take all found: ' + logged + ')');
}

await browser.close();
server.close();
console.log('\n' + pass + '/' + (pass + fail) + ' checks passed' + (fail ? '  <-- FAIL' : ''));
process.exit(fail ? 1 : 0);

// ---------------------------------------------------------------------------------------------
// WHERE THIS HARNESS STOPS, AND WHY IT IS COMMITTED UNFINISHED.
//
// Sections 2 and 3 have never run. Section 1 cannot get a dose logged, because every route to a
// Tylenol dose that would cross the ceiling is itself blocked by the app -- correctly:
//   * seed the day to 3,000 mg and the card is LOCKED on the ceiling (`used >= max`), so tapping it
//     opens the override flow, not the dose modal;
//   * seed it to 2,500 mg and the card is locked on the four-hour GAP instead, because the last
//     seeded dose has to be recent enough to be today.
// Exceeding a daily limit in this app REQUIRES the "log anyway" override, by design. The harness
// has to drive that path, and it does not yet.
//
// It is committed rather than deleted because the defect it is written for is real and reproduced by
// reading the code (see harness-warning-priority-patch.py), and because four earlier versions of
// this file reported PASS and FAIL about screens they had never reached -- a selector matching
// nothing, a confirm button named after the dose, a fixture whose `mg: 4000` the app ignored in
// favour of the dose label. Each of those looked like a finding about the app and was a finding
// about the test. A suite in that state must say so out loud rather than be quietly trusted.
//
// NOT SHIPPED. index.html and sw.js are deliberately unchanged: the fix exists as a patch script and
// has not been verified here, and the same defect is in the production app, where it needs Aaron's
// go-ahead. The two should land together.
