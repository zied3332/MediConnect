const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {runInNewContext} = require('node:vm');

function deferred() {
    let resolve;
    const promise = new Promise(done => { resolve = done; });
    return {promise, resolve};
}

function fixture(kind, models = Promise.resolve()) {
    const enroll = kind === 'enroll';
    const modalId = enroll ? 'faceEnrollModal' : 'faceLoginModal';
    const videoId = enroll ? 'faceEnrollVideo' : 'faceLoginVideo';
    const events = new Map(); const classes = new Set();
    const modal = {classList: {contains: value => classes.has(value)},
        addEventListener: (name, callback) => events.set(name, callback)};
    const video = {srcObject: null, play: async () => {}};
    const elements = {[modalId]: modal, [videoId]: video,
        captureFaceBtn: {disabled: false, addEventListener() {}},
        faceEnrollStatus: {}, faceLoginStatus: {}};
    let ready; let cameraCalls = 0; let stopped = 0;
    const permission = deferred();
    const stream = {getTracks: () => [{stop() { stopped++; }}]};
    const context = {
        document: {getElementById: id => elements[id] || null,
            addEventListener: (name, callback) => { if (name === 'DOMContentLoaded') ready = callback; }},
        window: {MediConnectDialog: {
            open() { classes.add('active'); },
            close() { classes.delete('active'); events.get('mc:dialog-close')(); },
        }},
        navigator: {mediaDevices: {getUserMedia() { cameraCalls++; return permission.promise; }}},
        faceapi: {nets: Object.fromEntries(['tinyFaceDetector', 'faceLandmark68Net',
            'faceRecognitionNet'].map(name => [name, {loadFromUri: () => models}])),
            TinyFaceDetectorOptions: class {},
            detectSingleFace: () => ({withFaceLandmarks: () => ({
                withFaceDescriptor: () => new Promise(() => {}),
            })}),
        },
        fetch: async () => ({json: async () => ({descriptors: [{}]})}),
        console: {log() {}, error() {}}, setTimeout() {},
    };
    runInNewContext(readFileSync(resolve(__dirname, `../face-${kind}.js`), 'utf8'), context);
    ready();
    return {open: () => context[enroll ? 'openFaceEnrollModal' : 'openFaceLoginModal'](),
        close: () => context[enroll ? 'closeFaceEnrollModal' : 'closeFaceLoginModal'](),
        permission, stream, video, calls: () => cameraCalls, stopped: () => stopped};
}

for (const kind of ['login', 'enroll']) {
    test(`${kind}: closing while models load never requests a camera`, async () => {
        const models = deferred(); const f = fixture(kind, models.promise);
        const opening = f.open(); f.close(); models.resolve(); await opening;
        assert.equal(f.calls(), 0);
    });

    test(`${kind}: camera permission resolving after close releases its stream`, async () => {
        const f = fixture(kind); const opening = f.open();
        // Allow model and descriptor promises to settle up to getUserMedia.
        for (let i = 0; i < 12; i++) await Promise.resolve();
        assert.equal(f.calls(), 1);
        f.close(); f.permission.resolve(f.stream); await opening;
        assert.equal(f.stopped(), 1);
        assert.equal(f.video.srcObject, null);
    });

    test(`${kind}: closing an active camera stops every track and clears the video`, async () => {
        const f = fixture(kind); f.permission.resolve(f.stream); await f.open();
        assert.equal(f.video.srcObject, f.stream);
        f.close();
        assert.equal(f.stopped(), 1);
        assert.equal(f.video.srcObject, null);
    });
}
