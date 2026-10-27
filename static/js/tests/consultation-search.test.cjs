const {test} = require('node:test');
const assert = require('node:assert/strict');
const {environment} = require('./interaction-fixture.cjs');

async function fixture() {
    const f = environment(); const form = f.node(), results = f.node(), status = f.node();
    const input = f.node(), count = f.node(); count.textContent = '12 résultats';
    input.matches = selector => selector === 'input[name="q"]';
    results.selectors.set('[data-live-count]', count);
    f.document.selectors.set('[data-live-search]', [form]);
    f.document.selectors.set('[data-live-results]', results);
    f.document.selectors.set('[data-live-status]', status);
    let release;
    f.context.fetch = () => new Promise(resolve => { release = () => resolve({ok: true, text: async () => 'results'}); });
    f.run('consultation-search.js'); await f.ready();
    return {...f, form, results, status, input, count, release: () => release()};
}

test('filtering leaves focus in the input and announces the count', async () => {
    const f = await fixture(); f.input.focus();
    await f.form.fire('input', {target: f.input});
    const pending = f.timers.at(-1)(); f.release(); await pending;
    assert.equal(f.document.activeElement, f.input);
    assert.equal(f.status.textContent, '12 résultats');
});

test('keyboard pagination focuses the new count without duplicate status text', async () => {
    const f = await fixture(); const link = f.node(); link.href = 'https://example.test/consultations/?page=2';
    link.closest = () => link; f.results.children.push(link); link.focus();
    const pending = f.results.fire('click', {target: link, button: 0, detail: 0});
    f.release(); await pending;
    // The event listener starts the asynchronous load without awaiting it.
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(f.document.activeElement, f.count);
    assert.equal(f.status.textContent, '');
    assert.equal(f.results.getAttribute('aria-busy'), null);
});

test('a pagination response does not steal focus after the user moves elsewhere', async () => {
    const f = await fixture(); const link = f.node(); link.href = 'https://example.test/consultations/?page=2';
    link.closest = () => link; f.results.children.push(link); link.focus();
    await f.results.fire('click', {target: link, button: 0});
    f.input.focus(); f.release(); await new Promise(resolve => setImmediate(resolve));
    assert.equal(f.document.activeElement, f.input);
});
