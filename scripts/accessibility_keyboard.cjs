const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE||'C:/Users/zied/AppData/Local/Programs/Python/Python313/Lib/site-packages/playwright/driver/package');
const base='http://127.0.0.1:8765',run=process.env.AUDIT_RUN||'baseline';
const dir=path.resolve('docs/accessibility/reports',run);fs.mkdirSync(dir,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const sessions=JSON.parse(fs.readFileSync('.audit-sessions.json'));const results=[];
 const focus=page=>page.evaluate(()=>{const e=document.activeElement,s=getComputedStyle(e),r=e.getBoundingClientRect();return {tag:e.tagName,id:e.id,text:e.textContent.trim().slice(0,100),outline:s.outline,boxShadow:s.boxShadow,color:s.color,background:s.backgroundColor,rect:r.toJSON(),focusVisible:e.matches(':focus-visible')}});
 async function tabTo(page,selector){for(let i=0;i<180;i++){await page.keyboard.press('Tab');if(await page.locator(selector).first().evaluate(e=>e===document.activeElement))return;}throw Error('Not reached by Tab: '+selector)}
 async function check(name,role,route,steps){const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});if(sessions[role])await context.addCookies([{name:'sessionid',value:sessions[role],url:base}]);const page=await context.newPage();try{await page.goto(base+route,{waitUntil:'domcontentloaded'});await page.waitForTimeout(600);const data=await steps(page);results.push({name,role,route,...data});console.log(name,data.result)}catch(e){results.push({name,role,route,result:'not verified',error:e.message});console.log(name,e.message)}finally{await context.close()}}
 function expect(ok,message){if(!ok)throw Error(message)}
 await check('Skip link, forward and reverse Tab','public','/',async p=>{
  await p.keyboard.press('Tab');const first=await focus(p);await p.keyboard.press('Tab');const second=await focus(p);await p.keyboard.press('Shift+Tab');const reverse=await focus(p);await p.keyboard.press('Enter');const target=await focus(p);
  return {result:first.id===reverse.id&&target.tag==='MAIN'?'pass':'fail',first,second,reverse,target};
 });
 for(const [name,role,route,opener,modal] of [['Face login dialog','public','/accounts/login/','#faceLoginBtn','#faceLoginModal'],['Face enrollment dialog','patient','/dashboard/profile/','#enrollFaceBtn','#faceEnrollModal'],['Availability deletion confirmation','doctor','/dashboard/doctor/availability/','[data-delete-confirm] button','#delete-confirmation-modal']]){
  await check(name,role,route,async p=>{
   await tabTo(p,opener);const openerFocus=await focus(p);await p.keyboard.press('Space');await p.locator(modal).waitFor({state:'visible',timeout:5000});const initial=await focus(p);const within=[];
   for(const key of ['Tab','Tab','Shift+Tab','Shift+Tab','Shift+Tab']){await p.keyboard.press(key);within.push({key,focus:await focus(p),contained:await p.locator(modal).evaluate(e=>e.contains(document.activeElement))})}
   await p.screenshot({path:`docs/accessibility/screenshots/${run}/${name.replaceAll(' ','-')}.png`});
   await p.keyboard.press('Escape');const restored=await focus(p);const hidden=!(await p.locator(modal).isVisible());
   return {result:within.every(x=>x.contained)&&hidden&&restored.id===openerFocus.id&&restored.text===openerFocus.text?'pass':'fail',openerFocus,initial,within,hidden,restored,camera:'No biometric success tested; no real face enrolled'};
  });
 }
 await check('Mobile sidebar','patient','/dashboard/patient/',async p=>{
  await p.setViewportSize({width:320,height:900});await tabTo(p,'#dashboard-menu-toggle');await p.keyboard.press('Enter');await p.waitForTimeout(200);const initial=await focus(p);const expanded=await p.locator('#dashboard-menu-toggle').getAttribute('aria-expanded');
  const contained=[];for(let i=0;i<25;i++){await p.keyboard.press(i%4===0?'Shift+Tab':'Tab');contained.push(await p.locator('#dashboard-sidebar').evaluate(e=>e.contains(document.activeElement)))}
  await p.keyboard.press('Escape');const restored=await focus(p);return {result:expanded==='true'&&contained.every(Boolean)&&restored.id==='dashboard-menu-toggle'?'pass':'fail',initial,expanded,contained,restored};
 });
 await check('Login validation','public','/accounts/login/',async p=>{
  await tabTo(p,'#mc-login-form button[type=submit]');await p.keyboard.press('Enter');await p.waitForTimeout(800);const observed=await p.locator('[role=alert]').allTextContents();const invalid=await p.locator('[aria-invalid=true]').count();return {result:invalid>0&&observed.some(x=>x.trim())?'pass':'fail',invalid,observed,focus:await focus(p)};
 });
 await check('Examination filtering','patient','/medical-records/patients/1/examinations/',async p=>{
  await tabTo(p,'#examSearch');await p.keyboard.type('no-matching-fixture');const hidden=await p.locator('#examList .exam-item:visible').count(),status=await p.locator('#examFilterStatus').textContent(),after=await focus(p);await p.keyboard.press('Control+A');await p.keyboard.press('Backspace');const restored=await p.locator('#examList .exam-item:visible').count();return {result:hidden===0&&restored>0&&after.id==='examSearch'?'pass':'fail',hidden,status,after,restored};
 });
 await check('Consultation pagination','doctor','/consultations/',async p=>{
  await tabTo(p,'.care-pagination a');await p.keyboard.press('Enter');await p.waitForTimeout(1000);const after=await focus(p),url=p.url();return {result:url.includes('page=2')&&await p.locator('[data-live-count]').evaluate(e=>e===document.activeElement)?'pass':'fail',url,after};
 });
 await check('Appointment risk tooltip','doctor','/appointments/doctor/?when=past',async p=>{
  await tabTo(p,'[data-risk-tooltip]');const before=await p.locator('[role=tooltip].is-visible').count(),observed=await focus(p);await p.keyboard.press('Escape');const after=await p.locator('[role=tooltip].is-visible').count();return {result:before>0&&after===0?'pass':'fail',before,after,observed};
 });
 await check('Patient brief panel updates','doctor','/consultations/1/',async p=>{
  await tabTo(p,'[data-brief-open]');await p.keyboard.press('Enter');await p.waitForTimeout(1000);const expanded=await p.locator('[data-brief-open]').first().getAttribute('aria-expanded'),content=await p.locator('#care-brief-content').textContent(),after=await focus(p);await tabTo(p,'[data-brief-close]');await p.keyboard.press('Space');const restored=await focus(p);return {result:expanded==='true'&&content.trim().length>0&&await p.locator('[data-brief-open]').first().evaluate(e=>e===document.activeElement)?'pass':'fail',expanded,content:content.slice(0,250),after,restored,generation:'External AI generation not invoked'};
 });
 fs.writeFileSync(path.join(dir,'keyboard.json'),JSON.stringify({browser:browser.version(),date:new Date().toISOString(),results},null,2));await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
