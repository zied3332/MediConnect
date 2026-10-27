const {test} = require('node:test');
const assert = require('node:assert/strict');
const {environment} = require('./interaction-fixture.cjs');

async function fixture() {
    const f = environment(), badge = f.node(), tooltip = f.node();
    badge.selectors.set('[role="tooltip"]', tooltip);
    f.document.selectors.set('[data-risk-tooltip]', [badge]);
    f.document.body.appendChild = child => f.document.body.children.push(child);
    badge.getBoundingClientRect = () => ({left: 0, top: 2, bottom: 22, width: 40});
    tooltip.getBoundingClientRect = () => ({width: 160, height: 40});
    badge.matches = () => f.document.activeElement === badge;
    f.window.innerWidth = 320; f.window.innerHeight = 600;
    f.run('risk-tooltips.js'); await f.ready();
    return {...f, badge, tooltip};
}

test('keyboard focus opens a viewport-bounded tooltip outside the clipping table', async () => {
    const f = await fixture(); f.badge.focus(); await f.badge.fire('focusin');
    assert.equal(f.tooltip.classList.contains('is-visible'), true);
    assert.equal(f.document.body.children.includes(f.tooltip), true);
    assert.equal(f.tooltip.style.left, '12px'); assert.equal(f.tooltip.style.top, '30px');
    await f.document.fire('keydown', {key: 'Escape'});
    assert.equal(f.tooltip.classList.contains('is-visible'), false);
    assert.equal(f.document.activeElement, f.badge);
});

test('pointer can cross the gap and hover the tooltip until it leaves', async () => {
    const f = await fixture(); await f.badge.fire('pointerenter'); await f.badge.fire('pointerleave');
    await f.tooltip.fire('pointerenter'); f.timers.at(-1)();
    assert.equal(f.tooltip.classList.contains('is-visible'), true);
    await f.tooltip.fire('pointerleave'); f.timers.at(-1)();
    assert.equal(f.tooltip.classList.contains('is-visible'), false);
});

test('Escape dismisses a hovered tooltip without immediately reopening it', async () => {
    const f = await fixture(); await f.badge.fire('pointerenter');
    await f.document.fire('keydown', {key: 'Escape'}); await f.window.fire('resize');
    assert.equal(f.tooltip.classList.contains('is-visible'), false);
});

test('focus moving into a dialog hides even a hovered tooltip', async () => {
    const f = await fixture(); await f.badge.fire('pointerenter'); await f.tooltip.fire('pointerenter');
    await f.document.fire('focusin', {target: f.node()});
    assert.equal(f.tooltip.classList.contains('is-visible'), false);
});
