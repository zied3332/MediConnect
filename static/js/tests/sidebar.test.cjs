const {test} = require('node:test');
const assert = require('node:assert/strict');
const {environment} = require('./interaction-fixture.cjs');

async function fixture(matches = true) {
    const f = environment(), sidebar = f.node(), toggle = f.node(), close = f.node();
    const mobile = f.node(); mobile.matches = matches; f.window.matchMedia = () => mobile;
    f.document.ids.set('dashboard-sidebar', sidebar); f.document.ids.set('dashboard-menu-toggle', toggle);
    sidebar.selectors.set('.mc-sidebar-close', close); sidebar.children.push(close);
    const firstLink = f.node(); sidebar.selectors.set('a[href]', firstLink); sidebar.children.push(firstLink);
    const other = f.node(); f.document.selectors.set('[role="dialog"]', [other]);
    let active = false;
    f.window.MediConnectDialog = {
        isActive: () => active,
        open(node, options) { active = true; node.classList.add('is-open'); node.removeAttribute('aria-hidden'); options.initialFocus.focus(); },
        async close(node) { if (!node.classList.contains('is-open')) return;
            active = false; node.classList.remove('is-open'); toggle.focus(); await node.fire('mc:dialog-close'); },
    };
    f.run('dashboard.js'); await f.ready();
    return {...f, sidebar, toggle, close, mobile, other, firstLink, setActive: value => { active = value; }};
}

test('mobile drawer starts inert and delegates open/close focus to the shared controller', async () => {
    const f = await fixture();
    assert.equal(f.sidebar.inert, true); assert.equal(f.close.hidden, false);
    assert.equal(f.sidebar.getAttribute('role'), 'dialog');
    await f.toggle.fire('click');
    assert.equal(f.sidebar.inert, false); assert.equal(f.document.activeElement, f.close);
    assert.equal(f.toggle.getAttribute('aria-expanded'), 'true');
    await f.close.fire('click');
    assert.equal(f.document.activeElement, f.toggle); assert.equal(f.sidebar.inert, true);
    assert.equal(f.toggle.getAttribute('aria-expanded'), 'false');
});

test('desktop resize closes the drawer and restores ordinary sidebar semantics', async () => {
    const f = await fixture(); await f.toggle.fire('click');
    f.mobile.matches = false; await f.mobile.fire('change');
    assert.equal(f.sidebar.inert, false); assert.equal(f.close.hidden, true);
    assert.equal(f.sidebar.getAttribute('role'), null);
    assert.equal(f.sidebar.getAttribute('aria-hidden'), null);
    assert.equal(f.toggle.getAttribute('aria-expanded'), 'false');
    assert.equal(f.document.activeElement, f.firstLink);
});

test('resizing does not override another dialog isolation; closing it resynchronizes navigation', async () => {
    const f = await fixture(); f.setActive(true);
    f.mobile.matches = false; await f.mobile.fire('change');
    assert.equal(f.sidebar.inert, true);
    f.setActive(false); await f.other.fire('mc:dialog-close');
    assert.equal(f.sidebar.inert, false);
});
