// overflow-longname-test.mjs -- Home must not go wider than the phone, however long a name is.
//
// WHY THIS EXISTS. A note on the task list said staging measured 334px wide on a 320px screen with
// a 313-character pasted medication name, and that the cause was never identified. Nobody could act
// on that: it named a symptom, a width and a screen, and no way to see it again.
//
// THE FIRST ATTEMPT TO REPRODUCE IT MEASURED NOTHING AT ALL. A probe that wrote a long name into
// `localStorage` and read the page width back reported a clean 320px at every size -- because THIS
// APP DOES NOT KEEP ITS DATA IN localStorage. It reads from Firestore, so the injection landed
// nowhere, the app rendered an empty shell with no `main` element, and "no overflow" was a true
// statement about a blank page. That is the same shape as every other vacuous check found this
// week: a measurement taken of the wrong thing reports confidently about nothing.
//
// So this uses the repo's own mocked-Firestore harness, the way `up-next-test.mjs` does, which is
// also what Hard Rule 4 requires: never QA against the real database.
//
// Run:  node harness/overflow-longname-test.mjs
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = (() => {
  const _p = require('node:path');
  const tries = ['playwright', '/opt/node22/lib/node_modules/playwright',
    _p.join(_p.dirname(process.execPath), '..', 'lib', 'node_modules', 'playwright')];
  for (const c of tries) { try { return require(c); } catch (e) {} }
  throw new Error('playwright not found');
})();
import fs from 'node:fs';
import http from 'node:http';

let pass = 0, fail = 0;
const t = (name, cond, detail) => {
  console.log('  ' + (cond ? 'PASS  ' : 'FAIL  ') + name + (detail !== undefined ? '  |  ' + detail : ''));
  cond ? pass++ : fail++;
};

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const FROZEN = (() => { const d = new Date(); d.setHours(10, 0, 0, 0); return d.getTime(); })();
const D0 = (() => { const d = new Date(FROZEN); d.setHours(0, 0, 0, 0); return d.getTime(); })();

// 313 characters with NO SPACES IN IT, which is the whole point: a name that cannot wrap is the
// only kind that can push a column wider than the screen. A long name with spaces proves nothing.
const LONG = 'Z'.repeat(313);

const mkStub = (seed, prefs) => `
const store={entries:${JSON.stringify(seed)},prefs:${JSON.stringify(prefs || {})}};const eL=[],pL=[];let n=0;
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
  if (rq.url.startsWith('/index.html')) { rs.writeHead(200, { 'Content-Type': 'text/html' }); rs.end(html); return; }
  rs.writeHead(204); rs.end();
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
const PORT = server.address().port;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const VER = (html.match(/const APP_VERSION = '([^']+)'/) || [])[1] || '';

async function measure(width, seed, prefs) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
  await ctx.route('**/*', route => {
    const u = route.request().url();
    if (u.includes('firebase-app.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: SA });
    if (u.includes('firebase-firestore.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: mkStub(seed, prefs) });
    if (u.includes('firebase-messaging.js')) return route.fulfill({ status: 200, contentType: 'application/javascript', body: SM });
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
  // THE APP MUST ACTUALLY HAVE RENDERED, or every width below is a measurement of a blank page.
  // The first version of this probe reported "no overflow" at all three widths against an empty
  // shell, which is the reason this guard is the first assertion and not an afterthought.
  const rendered = await p.evaluate(() => !!document.querySelector('main') && (document.querySelector('main').innerText || '').length > 20);
  const doc = await p.evaluate(() => document.documentElement.scrollWidth);
  const offenders = await p.evaluate((vw) => {
    const out = [];
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width > vw + 1 || r.right > vw + 1) {
        out.push({ tag: el.tagName, w: Math.round(r.width), right: Math.round(r.right),
          text: (el.innerText || '').replace(/\s+/g, ' ').slice(0, 26) });
      }
    }
    return out.slice(0, 4);
  }, width);
  await ctx.close();
  return { rendered, doc, offenders, errs };
}

const seedWithLongName = [
  { id: 'e1', medId: 'tylenol', dose: LONG, mg: 500, ts: D0 + 8 * 3600000 },
  { id: 'e2', medId: 'temp', temp: 99.1, dose: '99.1 °F', mg: 0, ts: D0 + 9 * 3600000 }
];

console.log('\n1. THE HARNESS ACTUALLY LOADS THE APP');
{
  const r = await measure(320, seedWithLongName, { patientName: 'Brandi' });
  t('the app rendered -- otherwise every width below is a blank page', r.rendered,
    r.rendered ? 'main has content' : 'NO main content: the mock did not feed the app');
  t('and nothing threw', r.errs.length === 0, r.errs.slice(0, 2).join(' / ') || 'none');
}

console.log('\n2. A 313-CHARACTER UNBREAKABLE NAME DOES NOT PUSH HOME SIDEWAYS');
for (const w of [320, 360, 390]) {
  const r = await measure(w, seedWithLongName, { patientName: 'Brandi' });
  t('Home fits ' + w + 'px with a 313-character name in an entry',
    r.rendered && r.doc <= w, 'scrollWidth=' + r.doc + (r.rendered ? '' : ' (BLANK PAGE - result meaningless)'));
  if (r.doc > w) console.log('     offenders: ' + JSON.stringify(r.offenders));
}

console.log('\n3. AND THE SAME NAME IN THE PATIENT NAME, WHICH THE HEADER PRINTS');
for (const w of [320, 390]) {
  const r = await measure(w, seedWithLongName, { patientName: LONG });
  t('Home fits ' + w + 'px with a 313-character patient name',
    r.rendered && r.doc <= w, 'scrollWidth=' + r.doc + (r.rendered ? '' : ' (BLANK PAGE)'));
  if (r.doc > w) console.log('     offenders: ' + JSON.stringify(r.offenders));
}

await browser.close();
server.close();
console.log('\n' + (pass + fail) + ' checks: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
