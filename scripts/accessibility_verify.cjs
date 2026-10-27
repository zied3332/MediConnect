/* Fail the regression check on missing pages, audit failures or keyboard regressions. */
const fs=require('node:fs'),assert=require('node:assert/strict');
const dir='docs/accessibility/reports/final/';
const read=name=>JSON.parse(fs.readFileSync(dir+name+'.json'));
const pages=read('summary').pages;
assert.equal(pages.length,24);
for(const page of pages){assert.equal(page.status,'loaded',page.name);assert.equal(page.violations.length,0,page.name)}
const lighthouse=read('lighthouse-summary');assert.equal(lighthouse.length,5);
for(const page of lighthouse){assert.equal(page.runtimeError,undefined,page.name);assert.equal(new URL(page.finalUrl).pathname,page.route,page.name);assert.equal(page.score,1,page.name)}
const keyboard=read('keyboard').results;assert.equal(keyboard.length,12);
for(const workflow of keyboard)assert.equal(workflow.result,'pass',workflow.name);
const responsive=read('responsive');assert.equal(responsive.length,40);
for(const scenario of responsive){assert.equal(scenario.error,undefined,scenario.name);assert.equal(scenario.overflow,false,scenario.name+' '+scenario.mode)}
for(const sample of read('contrast'))assert.notEqual(sample.result,'fail',sample.name);
console.log('PASS: 24 axe routes, 5 Lighthouse pages, 12 keyboard workflows, 40 overflow checks; no measured contrast failures. See documented limitations.');
