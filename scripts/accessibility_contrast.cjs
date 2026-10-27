const fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE||'C:/Users/zied/AppData/Local/Programs/Python/Python313/Lib/site-packages/playwright/driver/package');
const base='http://127.0.0.1:8765',run=process.env.AUDIT_RUN||'final';
(async()=>{
 const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const results=[];
 const sessions=JSON.parse(fs.readFileSync('.audit-sessions.json'));
 for(const [name,role,route,selector,state,kind] of [
  ['Home step numbers','public','/','.mc-home-steps article > span','normal','text'],
  ['Home heading','public','/','h1','normal','text'],
  ['Search input text','public','/','#mc-search-query','normal','text'],
  ['Search input boundary','public','/','#mc-search-query','normal','border'],
  ['Search button','public','/','.mc-care-submit','normal','text'],
  ['Search button hover','public','/','.mc-care-submit','hover','text'],
  ['Login keyboard focus','public','/accounts/login/','#login-email','focus','outline'],
  ['Login error text','public','/accounts/login/','.mc-auth-field-error','error','text'],
  ['Admin Review link','admin','/dashboard/admin/','.mc-quick-info a','normal','text'],
  ['Booking disabled control','patient','/appointments/book/doctor/2/','button:disabled','normal','disabled'],
 ]){
  const p=await b.newPage();try{
   if(sessions[role])await p.context().addCookies([{name:'sessionid',value:sessions[role],url:base}]);await p.goto(base+route,{waitUntil:'domcontentloaded'});await p.waitForTimeout(400);
   if(state==='error'){await p.locator('#mc-login-form button[type=submit]').click();await p.waitForTimeout(500)}
   const e=p.locator(selector).first();if(!(await e.count())){results.push({name,route,selector,state,result:'not verified',reason:'No matching rendered element'});continue}
   if(state==='hover')await e.hover();
   if(state==='focus'){for(let i=0;i<40;i++){await p.keyboard.press('Tab');if(await e.evaluate(e=>e===document.activeElement))break}}
   const colors=await e.evaluate((e,kind)=>{
    const rgb=s=>s.match(/[\d.]+/g)?.map(Number);const style=getComputedStyle(e);let bg=[255,255,255],layers=[],gradient=false;
    for(let n=e;n;n=n.parentElement){const s=getComputedStyle(n);layers.unshift({color:rgb(s.backgroundColor)||[0,0,0,0],image:s.backgroundImage!=='none'})}
    for(const {color:layer,image} of layers){const a=layer[3]??1;if(a===1)gradient=false;if(image)gradient=true;bg=bg.map((c,i)=>layer[i]*a+c*(1-a))}
    const color=kind==='border'?style.borderTopColor:kind==='outline'?style.outlineColor:style.color;const fg=rgb(color);const l=c=>{const a=c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return a[0]*.2126+a[1]*.7152+a[2]*.0722};const ratio=(Math.max(l(fg),l(bg))+.05)/(Math.min(l(fg),l(bg))+.05);
    const size=parseFloat(style.fontSize),bold=parseInt(style.fontWeight)>=700,large=size>=24||(bold&&size>=18.6667);return {foreground:color,background:`rgb(${bg.map(Math.round).join(', ')})`,ratio,fontSize:style.fontSize,fontWeight:style.fontWeight,threshold:kind==='disabled'?null:kind==='text'?(large?3:4.5):3,gradient,outline:style.outline,border:style.borderTop,text:e.textContent.trim().slice(0,60)};
   },kind);
   results.push({name,route,selector,state,kind,...colors,result:kind==='disabled'?'exempt':colors.gradient?'not verified':colors.ratio>=colors.threshold?'pass':'fail'});
  }catch(e){results.push({name,route,state,result:'not verified',error:e.message})}finally{await p.close()}
 }
 fs.writeFileSync(path.join('docs/accessibility/reports',run,'contrast.json'),JSON.stringify(results,null,2));console.log(results.map(x=>({name:x.name,ratio:x.ratio,result:x.result})));await b.close();
})();
