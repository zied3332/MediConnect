const {test} = require('node:test');
const assert = require('node:assert/strict');
const {environment} = require('./interaction-fixture.cjs');

async function fixture() {
    const f = environment(), button = f.node({'aria-controls': 'browse', 'aria-expanded': 'false'});
    const menu = f.node(), link = f.node(), mobileToggle = f.node({'aria-expanded': 'false'}), mobileMenu = f.node();
    menu.hidden = true; mobileMenu.hidden = true; menu.children.push(link);
    const mobileLink = f.node(); mobileMenu.children.push(mobileLink);
    f.document.ids.set('browse', menu); f.document.selectors.set('[data-mc-dropdown]', [button]);
    f.document.selectors.set('.mc-nav-mobile-toggle', mobileToggle);
    f.document.selectors.set('#mc-nav-mobile-menu', mobileMenu);
    mobileMenu.selectors.set('a', [mobileLink]); f.window.matchMedia = () => f.node();
    f.run('navbar.js'); await f.ready();
    return {...f, button, menu, link, mobileToggle, mobileMenu, mobileLink};
}

test('Escape restores focus from dropdown links to their disclosure button', async () => {
    const f = await fixture(); await f.button.fire('click'); f.link.focus();
    await f.document.fire('keydown', {key: 'Escape'});
    assert.equal(f.document.activeElement, f.button); assert.equal(f.menu.hidden, true);
    assert.equal(f.button.getAttribute('aria-expanded'), 'false');
});

test('Escape restores mobile menu focus and synchronizes its name and expanded state', async () => {
    const f = await fixture(); await f.mobileToggle.fire('click'); f.mobileLink.focus();
    await f.document.fire('keydown', {key: 'Escape'});
    assert.equal(f.document.activeElement, f.mobileToggle); assert.equal(f.mobileMenu.hidden, true);
    assert.equal(f.mobileToggle.getAttribute('aria-expanded'), 'false');
    assert.equal(f.mobileToggle.getAttribute('aria-label'), 'Open navigation menu');
});

test('Escape does not steal focus from outside an open menu; ordinary link activation still closes it', async () => {
    const f = await fixture(); await f.button.fire('click');
    const outside = f.node(); outside.focus(); await f.document.fire('keydown', {key: 'Escape'});
    assert.equal(f.document.activeElement, outside);
    await f.mobileToggle.fire('click'); f.mobileLink.focus(); await f.mobileLink.fire('click');
    assert.equal(f.mobileMenu.hidden, true); assert.equal(f.document.activeElement, f.mobileLink);
});
