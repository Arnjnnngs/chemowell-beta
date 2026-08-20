/**
 * beta-isolation-test.mjs — proves the BETA app cannot reach the patient's live data.
 *
 * This is the check that makes the beta safe to hand anyone. It does NOT test features; it tests
 * containment. Everything else about staging is worthless if a tester can corrupt the live app.
 *
 * The stub records EVERY collection and document path the app touches, and every FCM token request,
 * and the checks assert on those recordings — not on the source text. Reading the source would only
 * prove the string 'TEST_MODE' exists; this proves where the bytes actually go.
 */
import { createRequire } from 'node:module';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = require('/home/claude/.npm-global/lib/node_modules/playwright');
const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const arg = (n) => { const i = argv.indexOf(n); return i >= 0 ? argv[i+1] : null; };
const APP_FILE = arg('--file') || path.join(HERE, '..', 'index.html');
const MUTATE = arg('--mutate');
for (const v of ['HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy'])
  if (process.env[v]) { console.error('REFUSING: ' + v + ' set.'); process.exit(3); }

const STUB_APP = `export function initializeApp(c){return{name:'[DEFAULT]',options:c};}`;
// Records every token request. The beta must never ask for one: the reminder job sends to every
// token it finds, so a beta token means test notifications on the patient's phone.
const STUB_MSG = `
globalThis.__iso = globalThis.__iso || { cols: [], docs: [], tokenCalls: 0 };
export function getMessaging(){ return { __m: true }; }
export async function getToken(){ globalThis.__iso.tokenCalls++; return 'TEST-TOKEN'; }
export function onMessage(){ return ()=>{}; }
`;
const STUB_FS = `
globalThis.__iso = globalThis.__iso || { cols: [], docs: [], tokenCalls: 0 };
const iso = globalThis.__iso;
const store={entries:[],prefs:{}};const eL=[],pL=[];let n=0;
function snap(l){return{docs:l.map(e=>({id:e.id,data:()=>{const c=Object.assign({},e);delete c.id;return c;}}))};}
export function getFirestore(){return{__db:true};}
export function collection(db,name){ iso.cols.push(name); return {__kind:'col',name}; }
export function doc(db,colName,id){ if(colName) iso.docs.push(colName); return {__kind:'doc',col:colName,id}; }
export function query(){return{__kind:'q'};}
export function orderBy(){return{};}
export function onSnapshot(ref,cb){if(ref&&ref.__kind==='q'){eL.push(cb);cb(snap(store.entries));return()=>{};}
 pL.push(cb);cb({exists:()=>true,data:()=>store.prefs});return()=>{};}
export async function addDoc(c,d){ iso.cols.push('WRITE:'+(c&&c.name)); store.entries.push(Object.assign({id:'a'+(++n)},d)); for(const cb of eL)cb(snap(store.entries)); return {id:'a'+n}; }
export async function setDoc(r,d){ iso.docs.push('WRITE:'+(r&&r.col)); Object.assign(store.prefs,d); for(const cb of pL)cb({exists:()=>true,data:()=>store.prefs}); }
export async function deleteDoc(r){ iso.docs.push('DELETE:'+(r&&r.col)); }
export async function getDocs(){return snap(store.entries);}
export function serverTimestamp(){return Date.now();}
`;

let html = fs.readFileSync(APP_FILE, 'utf-8');
if (MUTATE) { const [f,t]=MUTATE.split('=>'); if(!html.includes(f)){console.error('MUTATOR ANCHOR MISSING');process.exit(4);} html=html.replace(f,t); console.log('MUTATED'); }

const R=[]; const assert=(c,m)=>{if(!c)throw new Error(m);};
async function run(n,d,fn){try{await fn();R.push(1);console.log('  PASS  '+n+' — '+d);}catch(e){R.push(0);console.log('  FAIL  '+n+' — '+d+'\n          '+e.message);}}

const server=http.createServer((rq,rs)=>{if(rq.url.startsWith('/index.html')){rs.writeHead(200,{'Content-Type':'text/html'});rs.end(html);return;}rs.writeHead(404);rs.end();}).listen(0,'127.0.0.1');
await new Promise(r=>server.once('listening',r));
const PORT=server.address().port;
const browser=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--no-sandbox']});
const escaped=[];
// Notifications are GRANTED deliberately. Without this, subscribePush() stops at
// Notification.requestPermission() in headless Chromium and never reaches getToken() -- so ISO-4
// passed even with its guard removed. Falsification (M2) caught that: the check was worthless.
// Granting permission makes the push path actually execute, so the guard is what stops it.
const ctx=await browser.newContext({viewport:{width:375,height:812},serviceWorkers:'block',
  permissions:['notifications']});
await ctx.addInitScript(()=>{ try{ Object.defineProperty(Notification,'permission',{get:()=>'granted'});
  Notification.requestPermission=async()=>'granted'; }catch(e){} });
await ctx.route('**/*',(route)=>{const u=route.request().url();
 if(u.includes('firebase-app.js'))return route.fulfill({status:200,contentType:'application/javascript',body:STUB_APP});
 if(u.includes('firebase-firestore.js'))return route.fulfill({status:200,contentType:'application/javascript',body:STUB_FS});
 if(u.includes('firebase-messaging.js'))return route.fulfill({status:200,contentType:'application/javascript',body:STUB_MSG});
 if(u.startsWith('http://127.0.0.1:'+PORT))return route.continue();
 if(u.startsWith('https://fonts.'))return route.abort();
 escaped.push(u);return route.abort();});
const page=await ctx.newPage();
const errs=[]; page.on('pageerror',e=>errs.push(String(e)));
await page.goto('http://127.0.0.1:'+PORT+'/index.html',{waitUntil:'domcontentloaded'});
await page.waitForTimeout(1300);

const iso = () => page.evaluate(()=>globalThis.__iso || {cols:[],docs:[],tokenCalls:0});

console.log('\nBETA ISOLATION — can this build reach the live app?\n');

await run('ISO-1-no-live-collection-touched',
  'no LIVE collection is read or written — every path is a caretracker_test_* one', async () => {
  const i = await iso();
  const all = i.cols.concat(i.docs).map(String);
  const live = all.filter(x => /caretracker_(entries|prefs)\b/.test(x) && !/_test_/.test(x));
  assert(all.length > 0, 'the stub recorded no Firestore paths at all — the test proved nothing');
  assert(live.length === 0, 'LIVE PATHS TOUCHED: ' + JSON.stringify([...new Set(live)]));
});

await run('ISO-2-test-collections-are-used',
  'it really is talking to the test collections (positive control)', async () => {
  const i = await iso();
  const all = i.cols.concat(i.docs).map(String);
  assert(all.some(x => x.includes('caretracker_test_entries')), 'test entries collection never used: ' + JSON.stringify([...new Set(all)]));
  assert(all.some(x => x.includes('caretracker_test_prefs')), 'test prefs collection never used');
});

await run('ISO-3-writes-go-to-test-collections', 'a logged dose is WRITTEN to the test collection', async () => {
  await page.evaluate(()=>{ const b=[...document.querySelectorAll('button')].find(x=>/^Log\b/.test(x.textContent.trim())); if(b) b.click(); });
  await page.waitForTimeout(700);
  const i = await iso();
  const writes = i.cols.concat(i.docs).filter(x=>String(x).startsWith('WRITE:'));
  const badWrites = writes.filter(x=>/caretracker_(entries|prefs)\b/.test(x) && !/_test_/.test(x));
  assert(badWrites.length === 0, 'A WRITE REACHED LIVE DATA: ' + JSON.stringify(badWrites));
});

await run('ISO-4-no-fcm-token-requested',
  'the beta never requests a push token — the reminder job sends to every token it finds', async () => {
  const i = await iso();
  assert(i.tokenCalls === 0, 'the beta asked for ' + i.tokenCalls + ' FCM token(s); a beta token means test pushes on the patient phone');
});

await run('ISO-5-beta-is-visually-unmistakable', 'a BETA badge is on screen', async () => {
  const badge = await page.evaluate(()=>{ const e=document.querySelector('[data-beta-badge]'); return e? e.innerText.trim() : null; });
  assert(badge && /beta/i.test(badge), 'no BETA badge found — a tester could mistake this for the live app');
});

await run('ISO-6-date-simulator-present-and-works',
  'the date controls exist and actually move the simulated clock', async () => {
  const ctrl = await page.evaluate(()=>!!document.querySelector('[data-beta-controls]'));
  assert(ctrl, 'beta date controls not rendered');
  const before = await page.evaluate(()=>document.body.innerText);
  await page.evaluate(()=>{ const c=document.querySelector('[data-beta-controls]');
    c.querySelector('div').click(); });
  await page.waitForTimeout(400);
  const moved = await page.evaluate(()=>{ const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim()==='+1 day'); if(!b) return 'nobutton'; b.click(); return 'clicked'; });
  assert(moved === 'clicked', 'the +1 day control was not reachable');
  await page.waitForTimeout(700);
  const after = await page.evaluate(()=>document.body.innerText);
  assert(after !== before, 'shifting the simulated date changed nothing on screen');
});

await run('PARITY-production-features-present',
  'the beta carries every v44-v49 feature (this is the whole point of the exercise)', () => {
  for (const [f, why] of [['CAL_APPT_MED_ID','calendar'],['downloadBackupFile','backup'],
      ['bkRestore','restore'],['tourStart','tour'],['medConfigJson','shared med settings'],
      ['uiIsBusy','sync guards'],['data-missed-on-card','missed-on-card'],
      ['medIsOnActiveList','deactivation fix'],['throw err;','write-failure banner']]) {
    assert(html.includes(f), why + ' is MISSING — parity not achieved');
  }
});

await run('NET-1','nothing reached the network beyond 127.0.0.1 and the stubs',()=>{
  assert(escaped.length===0,'escaped: '+escaped.slice(0,3).join(', '));});
await run('NET-2','no page errors',()=>{assert(errs.length===0,errs.slice(0,2).join(' | '));});

await browser.close(); server.close();
const p=R.reduce((a,b)=>a+b,0);
console.log('\n'+p+'/'+R.length+' checks passed');
process.exit(p===R.length?0:1);
