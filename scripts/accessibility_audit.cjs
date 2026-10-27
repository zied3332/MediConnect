/* Real Chromium audit. Tools are local-only; see docs/accessibility/README.md. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_PACKAGE || 'C:/Users/zied/AppData/Local/Programs/Python/Python313/Lib/site-packages/playwright/driver/package');
const base = 'http://127.0.0.1:8765';
const out = path.resolve('docs/accessibility');
const run = process.env.AUDIT_RUN || 'baseline';
const reports = path.join(out, 'reports', run);
fs.mkdirSync(reports, {recursive:true});
fs.mkdirSync(path.join(out,'screenshots',run), {recursive:true});
const save = (name, data) => fs.writeFileSync(path.join(reports,name+'.json'), JSON.stringify(data,null,2));
const routes = [
 ['home','public','/'], ['login','public','/accounts/login/'],
 ['patient-registration','public','/accounts/signup/'], ['doctor-registration','public','/accounts/doctor/signup/'],
 ['doctor-search','public','/?q=Audit'], ['patient-dashboard','patient','/dashboard/patient/'],
 ['medical-record','patient','/medical-records/my/'], ['prescriptions','patient','/medical-records/prescriptions/'],
 ['examinations','patient','/medical-records/patients/1/examinations/'], ['booking','patient','/appointments/book/'],
 ['booking-slots','patient','/appointments/book/doctor/2/'], ['doctor-dashboard','doctor','/dashboard/doctor/'],
 ['patients','doctor','/dashboard/doctor/patients/'], ['availability','doctor','/dashboard/doctor/availability/'],
 ['consultations','doctor','/consultations/'], ['admin-dashboard','admin','/dashboard/admin/'],
 ['users','admin','/dashboard/admin/users/'], ['specialties','admin','/dashboard/admin/specialties/'],
 ['record-management','admin','/medical-records/management/records/'],
 ['examination-management','admin','/medical-records/management/examinations/'],
 ['profile','patient','/dashboard/profile/'], ['doctor-appointments','doctor','/appointments/doctor/?tab=past'],
 ['patient-brief','doctor','/consultations/1/fiche/'], ['doctor-appointments-past','doctor','/appointments/doctor/?when=past'],
];

(async()=>{
 const browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const sessions = JSON.parse(fs.readFileSync('.audit-sessions.json','utf8'));
 const contexts = {};
 for(const role of ['public','patient','doctor','admin']) {
  contexts[role] = await browser.newContext({viewport:{width:1280,height:900}, reducedMotion:'reduce'});
  if(sessions[role]) await contexts[role].addCookies([{name:'sessionid',value:sessions[role],url:base}]);
 }
 const summary=[];
 for(const [name,role,route] of routes){
  const page=await contexts[role].newPage(); const errors=[];
  page.on('pageerror', e=>errors.push(e.message));
  try{
   const response=await page.goto(base+route,{waitUntil:'domcontentloaded',timeout:30000});
   await page.waitForTimeout(800);
   const loaded=response.status()===200 && new URL(page.url()).pathname===new URL(base+route).pathname;
   if(!loaded) throw Error(`HTTP ${response.status()} final URL ${page.url()}`);
   await page.addScriptTag({path:'.audit-tools/node_modules/axe-core/axe.min.js'});
   const axe=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}}));
   save(name+'-axe',axe);
   await page.screenshot({path:path.join(out,'screenshots',run,name+'.png'),fullPage:true});
   const semantics=await page.evaluate(()=>({title:document.title,lang:document.documentElement.lang,main:document.querySelectorAll('main').length,h1:document.querySelectorAll('h1').length,images:[...document.images].map(e=>({src:e.getAttribute('src'),alt:e.getAttribute('alt')}))}));
   summary.push({name,role,route,status:'loaded',violations:axe.violations.map(v=>({id:v.id,impact:v.impact,count:v.nodes.length})),passes:axe.passes.length,incomplete:axe.incomplete.length,errors,semantics});
   console.log(name,axe.violations.map(v=>v.id+':'+v.nodes.length).join(',') || '0 violations');
  }catch(e){summary.push({name,role,route,status:'not verified',error:e.message});console.log(name,e.message)}
  await page.close();
 }
 save('summary',{date:new Date().toISOString(),browser:browser.version(),axe:require('../.audit-tools/node_modules/axe-core/package.json').version,viewport:{width:1280,height:900},pages:summary});
 const responsive=[];
 for(const name of ['home','login','patient-registration','doctor-registration','patient-dashboard','examinations','booking-slots','availability','users','record-management']){
  const [,role,route]=routes.find(r=>r[0]===name);
  for(const mode of ['320px','200percent-text','400percent-equivalent','text-spacing']){
   const page=await contexts[role].newPage();
   try{
    await page.setViewportSize({width:mode==='320px'||mode==='400percent-equivalent'?320:1280,height:900});
    await page.goto(base+route,{waitUntil:'domcontentloaded'}); await page.waitForTimeout(200);
    if(mode==='200percent-text') await page.evaluate(()=>{const values=[...document.querySelectorAll('body, body *')].map(e=>[e,parseFloat(getComputedStyle(e).fontSize)]);for(const [e,size] of values)e.style.setProperty('font-size',size*2+'px','important')});
    if(mode==='text-spacing') await page.addStyleTag({content:'*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-bottom:2em!important}'});
    const metrics=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,offscreen:[...document.querySelectorAll('main input,main select,main button,main a')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&(r.right>innerWidth+1||r.left<0)&&!e.closest('.table-responsive,.table-wrap')}).map(e=>({tag:e.tagName,text:(e.textContent||e.getAttribute('aria-label')||e.id).trim().slice(0,80),rect:e.getBoundingClientRect().toJSON()})),tables:[...document.querySelectorAll('table')].map(e=>({width:e.scrollWidth,parentWidth:e.parentElement.clientWidth,overflowX:getComputedStyle(e.parentElement).overflowX}))}));
    responsive.push({name,route,mode,...metrics});
    await page.screenshot({path:path.join(out,'screenshots',run,name+'-'+mode+'.png'),fullPage:true});
   }catch(e){responsive.push({name,route,mode,error:e.message})}
   await page.close();
  }
 }
 save('responsive',responsive);
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
