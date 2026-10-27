const {test} = require('node:test');
const assert = require('node:assert/strict');
const {environment} = require('./interaction-fixture.cjs');

async function fixture(inline = true, open = true) {
    const f = environment(); const status = f.node(), error = f.node(), panel = f.node(), holder = f.node();
    const opener = f.node(), close = f.node(); panel.hidden = true; opener.dataset.briefOpen = '/brief/';
    f.document.selectors.set('[data-brief-status]', status);
    f.document.selectors.set('[data-brief-error]', error);
    f.document.selectors.set('[data-brief-open]', [opener]);
    panel.selectors.set('[data-brief-close]', close);
    const roots = [];
    function root() {
        const node = f.node(), form = f.node(), button = f.node(), publish = f.node(), save = f.node();
        const progress = f.node(), heading = f.node();
        form.action = '/generate/'; publish.action = '/publish/';
        form.selectors.set('button[type=submit]', button); publish.selectors.set('button', save);
        node.selectors.set('#brief-generate', form); node.selectors.set('#brief-progress', progress);
        node.selectors.set('[data-brief-publish]', publish); node.selectors.set('#brief-review-result', heading);
        node.children.push(form, publish); form.children.push(button); publish.children.push(save);
        roots.push({node, form, button, publish, save, heading});
        return node;
    }
    let current = inline ? null : root();
    if (inline) {
        f.document.ids.set('care-brief-panel', panel); f.document.ids.set('care-brief-content', holder);
        holder.selectors.set('[data-brief-root]', null);
        Object.defineProperty(holder, 'innerHTML', {set() {
            if (current) current.isConnected = false;
            current = root(); holder.selectors.set('[data-brief-root]', current);
        }});
    } else {
        f.document.selectors.set('[data-brief-root]', current);
        const replace = node => { node.replaceWith = next => { node.isConnected = false; current = next; replace(next); }; };
        replace(current);
        f.document.createElement = () => ({content: {querySelector: () => root()}});
    }
    f.window.scrollTo = () => {}; f.window.scrollY = 0;
    f.context.fetch = async url => ({ok: true, text: async () => 'fragment',
        json: async () => String(url).includes('generate') ? {status_url: '/status/'} : {status: 'ready'}});
    f.run('patient-brief.js'); await f.ready();
    if (inline && open) { opener.focus(); await opener.fire('click'); }
    return {...f, roots, status, error, panel, opener, close, latest: () => roots.at(-1)};
}

for (const inline of [true, false]) {
    test(`${inline ? 'inline' : 'standalone'} publication restores result focus and announces success`, async () => {
        const f = await fixture(inline); const before = f.latest(); before.save.focus();
        await before.publish.fire('submit');
        assert.notEqual(f.latest(), before);
        assert.equal(f.document.activeElement, f.latest().heading);
        assert.match(f.status.textContent, /publiée/);
        assert.equal(f.error.textContent, '');
    });
}

test('generation refresh focuses the ready result and retains the persistent status', async () => {
    const f = await fixture(); const before = f.latest(); before.button.focus();
    await before.form.fire('submit');
    assert.equal(f.document.activeElement, f.latest().heading);
    assert.match(f.status.textContent, /brouillon est prêt/);
});

test('publication failure is announced without replacing content or losing its control', async () => {
    const f = await fixture(); const before = f.latest(); before.save.focus();
    f.context.fetch = async () => ({ok: false, json: async () => ({error: 'Publication refusée'})});
    await before.publish.fire('submit');
    assert.equal(f.latest(), before);
    assert.equal(before.save.disabled, false);
    assert.equal(f.error.textContent, 'Publication refusée');
    assert.equal(f.status.textContent, '');
});

test('closing an inline brief restores its opener and discards pending updates', async () => {
    const f = await fixture(); let release;
    f.context.fetch = () => new Promise(resolve => { release = () => resolve({ok: true, json: async () => ({})}); });
    const before = f.latest(); before.save.focus(); const pending = before.publish.fire('submit');
    await f.close.fire('click'); release(); await pending;
    assert.equal(f.document.activeElement, f.opener);
    assert.equal(f.panel.hidden, true);
    assert.equal(f.latest(), before);
    assert.equal(f.status.textContent, '');
});

test('publication completion does not steal focus when the user has left the brief', async () => {
    const f = await fixture(); const normalFetch = f.context.fetch; let release;
    f.context.fetch = url => String(url).includes('publish') ? new Promise(resolve => {
        release = () => resolve({ok: true, json: async () => ({})});
    }) : normalFetch(url);
    const before = f.latest(); before.save.focus(); const pending = before.publish.fire('submit');
    const elsewhere = f.node(); elsewhere.focus(); release(); await pending;
    assert.equal(f.document.activeElement, elsewhere);
    assert.match(f.status.textContent, /publiée/);
});

test('an old opening failure cannot overwrite feedback after closing and reopening', async () => {
    const f = await fixture(true, false); const normalFetch = f.context.fetch; let reject;
    f.context.fetch = () => new Promise((_, fail) => { reject = fail; });
    const first = f.opener.fire('click'); await f.close.fire('click');
    f.context.fetch = normalFetch; await f.opener.fire('click');
    reject(new Error('old request')); await first;
    assert.equal(f.error.textContent, '');
    assert.match(f.status.textContent, /ouvert/);
});
