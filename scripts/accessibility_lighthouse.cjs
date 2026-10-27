const fs = require('node:fs');
const path = require('node:path');
(async()=>{
 const {default:lighthouse}=await import('../.audit-tools/node_modules/lighthouse/core/index.js');
 const {chromium}=require(process.env.PLAYWRIGHT_PACKAGE||'C:/Users/zied/AppData/Local/Programs/Python/Python313/Lib/site-packages/playwright/driver/package');
 const run=process.env.AUDIT_RUN||'baseline';
 const dir=path.resolve('docs/accessibility/reports',run);fs.mkdirSync(dir,{recursive:true});
 const sessions=JSON.parse(fs.readFileSync('.audit-sessions.json'));
 const summary=[];
 for(const [name,role,route] of [['home','public','/'],['login','public','/accounts/login/'],['patient-dashboard','patient','/dashboard/patient/'],['doctor-dashboard','doctor','/dashboard/doctor/'],['admin-dashboard','admin','/dashboard/admin/']]){
  const chrome=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--remote-debugging-port=9229']});
  try{
   const result=await lighthouse('http://127.0.0.1:8765'+route,{port:9229,onlyCategories:['accessibility'],output:['json','html'],logLevel:'error',formFactor:'desktop',screenEmulation:{mobile:false,width:1280,height:900,deviceScaleFactor:1,disabled:false},extraHeaders:sessions[role]?{Cookie:'sessionid='+sessions[role]}:undefined});
   const redact=text=>Object.values(sessions).reduce((value,cookie)=>value.replaceAll(cookie,'[redacted synthetic session]'),text);
   fs.writeFileSync(path.join(dir,name+'-lighthouse.json'),redact(result.report[0]));fs.writeFileSync(path.join(dir,name+'-lighthouse.html'),redact(result.report[1]));
   summary.push({name,route,role,score:result.lhr.categories.accessibility.score,finalUrl:result.lhr.finalDisplayedUrl,runtimeError:result.lhr.runtimeError,warnings:result.lhr.runWarnings});
   console.log(name,summary.at(-1));
  }catch(e){summary.push({name,route,error:e.message})}finally{await chrome.close()}
 }
 fs.writeFileSync(path.join(dir,'lighthouse-summary.json'),JSON.stringify(summary,null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
