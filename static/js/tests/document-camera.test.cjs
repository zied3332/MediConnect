const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {runInNewContext} = require('node:vm');

function fixture() {
    const elements = new Map();
    const callbacks = new Map();
    let stopped = 0;
    const navigator = {};
    const element = id => {
        if (!elements.has(id)) elements.set(id, {style: {}, textContent: '',
            addEventListener: (event, callback) => callbacks.set(`${id}:${event}`, callback),
            play: async () => {}});
        return elements.get(id);
    };
    const html = readFileSync(resolve(__dirname, '../../../templates/accounts/doctor/upload_docs.html'), 'utf8');
    const script = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
    runInNewContext(script, {document: {getElementById: element}, navigator,
        window: {addEventListener() {}}});
    return {element, navigator, click: id => callbacks.get(`${id}:click`)(),
        stream: {getTracks: () => [{stop() { stopped++; }}]}, stopped: () => stopped};
}

test('unsupported camera failures use the alert and preserve the upload fallback', async () => {
    const f = fixture(); await f.click('btn-open-camera');
    assert.equal(f.element('status-text').textContent, '');
    assert.equal(f.element('camera-error').textContent, 'Camera not supported in this browser.');
    assert.equal(f.element('camera-fallback').style.display, 'block');
    assert.equal(f.element('doc-selfie-fallback').name, 'selfie_with_id');
    assert.equal(f.element('selfie-file-input').name, '');
});

test('routine camera updates clear prior failures and closing releases the stream', async () => {
    const f = fixture(); await f.click('btn-open-camera');
    f.navigator.mediaDevices = {getUserMedia: async () => f.stream};
    await f.click('btn-open-camera');
    assert.equal(f.element('camera-error').textContent, '');
    assert.match(f.element('status-text').textContent, /Camera active/);
    f.click('btn-close-camera');
    assert.equal(f.element('status-text').textContent, 'Camera closed');
    assert.equal(f.stopped(), 1);
});

test('permission denial is announced as an important error', async () => {
    const f = fixture();
    f.navigator.mediaDevices = {getUserMedia: async () => { throw {name: 'NotAllowedError'}; }};
    await f.click('btn-open-camera');
    assert.equal(f.element('status-text').textContent, '');
    assert.match(f.element('camera-error').textContent, /Camera access denied/);
});
