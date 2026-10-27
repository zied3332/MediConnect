const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {runInNewContext} = require('node:vm');

function fixture(description) {
    let ready;
    const events = new Map();
    const attrs = {'aria-describedby': description};
    const composer = {value: 'Hello', getAttribute: name => attrs[name],
        setAttribute: (name, value) => { attrs[name] = value; },
        addEventListener: (name, callback) => events.set(name, callback)};
    const counter = {textContent: ''};
    const thread = {scrollTop: 0, scrollHeight: 100};
    runInNewContext(readFileSync(resolve(__dirname, '../consultations.js'), 'utf8'), {
        document: {addEventListener: (_, callback) => { ready = callback; },
            getElementById: id => id === 'id_contenu' ? composer : counter,
            querySelector: () => thread},
    });
    return {ready, attrs, composer, counter, thread, events};
}

test('counter preserves server-rendered help and validation descriptions', () => {
    const f = fixture('id_contenu_helptext id_contenu_error'); f.ready();
    assert.equal(f.attrs['aria-describedby'], 'id_contenu_helptext id_contenu_error message-counter');
    assert.equal(f.counter.textContent, '5 / 4 000 caractères');
    f.composer.value = 'Hello!'; f.events.get('input')();
    assert.equal(f.counter.textContent, '6 / 4 000 caractères');
    assert.equal(f.thread.scrollTop, 100);
});

test('existing counter and repeated whitespace never create duplicate tokens', () => {
    const f = fixture('help  message-counter\nhelp error'); f.ready(); f.ready();
    assert.equal(f.attrs['aria-describedby'], 'help message-counter error');
});

test('a composer without descriptions receives only the counter reference', () => {
    const f = fixture(null); f.ready();
    assert.equal(f.attrs['aria-describedby'], 'message-counter');
});

test('pages without a composer or counter initialize safely', () => {
    for (const missing of ['id_contenu', 'message-counter']) {
        let ready;
        runInNewContext(readFileSync(resolve(__dirname, '../consultations.js'), 'utf8'), {
            document: {addEventListener: (_, callback) => { ready = callback; },
                getElementById: id => id === missing ? null : {}, querySelector: () => null},
        });
        assert.doesNotThrow(ready);
    }
});
