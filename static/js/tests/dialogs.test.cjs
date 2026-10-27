// Dependency-free DOM contract tests; browser/AT checks remain necessary.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {runInNewContext} = require('node:vm');

function fixture({empty = false, face = false} = {}) {
    const listeners = new Map();
    const document = {activeElement: null, addEventListener(type, callback) {
        listeners.set(type, callback);
    }};
    class Element {
        constructor(parent = null, tabIndex = -1) {
            this.parentElement = parent; this.children = []; this.inert = false;
            this.tabIndex = tabIndex; this.isConnected = true; this.disabled = false;
            this.visible = true; this.style = {}; this.attrs = {}; this.events = [];
            this.listeners = new Map();
            const classes = new Set();
            this.classList = {contains: name => classes.has(name),
                add: name => classes.add(name), remove: name => classes.delete(name)};
            parent?.children.push(this);
        }
        setAttribute(key, value) { this.attrs[key] = value; }
        removeAttribute(key) { delete this.attrs[key]; }
        closest(selector) {
            if (selector === '.mc-modal') return this.classList.contains('mc-modal') ?
                this : this.parentElement?.closest(selector) || null;
            return this.inert ? this : this.parentElement?.closest(selector) || null;
        }
        matches() { return this.disabled; }
        getClientRects() { return this.visible ? [{}] : []; }
        querySelectorAll() { return this.children.flatMap(child => [child, ...child.querySelectorAll()]); }
        contains(target) { return target === this || this.children.some(child => child.contains(target)); }
        focus() { document.activeElement = this; }
        addEventListener(type, callback) { this.listeners.set(type, callback); }
        dispatchEvent(event) { this.events.push(event.type); this.listeners.get(event.type)?.(event); }
    }
    const body = document.body = new Element(); body.style.overflow = 'auto';
    const header = new Element(body); const opener = new Element(header, 0);
    const main = new Element(body); const other = new Element(main);
    document.querySelector = () => main;
    const alreadyInert = new Element(main); alreadyInert.inert = true;
    const modal = new Element(main); modal.setAttribute('aria-hidden', 'true');
    if (face) modal.classList.add('face-login-modal');
    const first = empty ? null : new Element(modal, 0);
    const disabled = empty ? null : new Element(modal, 0);
    if (disabled) disabled.disabled = true;
    const last = empty ? null : new Element(modal, 0);
    opener.focus();
    const window = {};
    const context = {
        window, document, getComputedStyle: () => ({visibility: 'visible'}),
        CustomEvent: class { constructor(type) { this.type = type; } },
    };
    runInNewContext(readFileSync(resolve(__dirname, '../dialogs.js'), 'utf8'), context);
    const key = (key, shiftKey = false) => {
        const event = {key, shiftKey, prevented: false, stopped: false,
            preventDefault() { this.prevented = true; },
            stopImmediatePropagation() { this.stopped = true; }};
        listeners.get('keydown')(event); return event;
    };
    return {Element, context, document, dialog: window.MediConnectDialog, body, header, main, other,
        alreadyInert, opener, modal, first, disabled, last, key, listeners};
}

test('opening exposes and focuses a dialog while isolating all ancestor siblings', () => {
    const f = fixture(); f.dialog.open(f.modal);
    assert.equal(f.modal.attrs['aria-hidden'], undefined);
    assert.equal(f.document.activeElement, f.first);
    assert.equal(f.header.inert, true); assert.equal(f.other.inert, true);
    assert.equal(f.body.style.overflow, 'hidden');
    assert.equal(f.modal.classList.contains('is-open'), true);
});

test('Tab and Shift+Tab wrap; disabled controls are excluded', () => {
    const f = fixture(); f.dialog.open(f.modal);
    assert.equal(f.key('Tab', true).prevented, true);
    assert.equal(f.document.activeElement, f.last);
    assert.equal(f.key('Tab').prevented, true);
    assert.equal(f.document.activeElement, f.first);
    assert.equal(f.key('Tab').prevented, false);
});

test('Escape closes, restores focus, original inert states and scroll, and emits cleanup', () => {
    const f = fixture(); f.dialog.open(f.modal);
    const event = f.key('Escape');
    assert.equal(event.prevented, true); assert.equal(event.stopped, true);
    assert.equal(f.document.activeElement, f.opener);
    assert.equal(f.modal.attrs['aria-hidden'], 'true');
    assert.equal(f.modal.classList.contains('is-open'), false);
    assert.equal(f.header.inert, false); assert.equal(f.other.inert, false);
    assert.equal(f.alreadyInert.inert, true);
    assert.equal(f.body.style.overflow, 'auto');
    assert.deepEqual(f.modal.events, ['mc:dialog-close']);
    assert.equal(f.key('Tab').prevented, false);
});

test('empty dialogs retain focus and tolerate a removed opener', () => {
    const f = fixture({empty: true}); f.dialog.open(f.modal);
    assert.equal(f.document.activeElement, f.modal);
    assert.equal(f.key('Tab').prevented, true);
    f.opener.isConnected = false;
    assert.doesNotThrow(() => f.dialog.close(f.modal));
    assert.equal(f.header.inert, false);
    assert.equal(f.document.activeElement, f.main);
});

test('requested initial focus is respected and escaping focus is brought back', () => {
    const f = fixture(); f.dialog.open(f.modal, {initialFocus: f.last});
    assert.equal(f.document.activeElement, f.last);
    f.listeners.get('focusin')({target: f.opener});
    assert.equal(f.document.activeElement, f.last);
});

test('face dialog lifecycle uses its existing active class and closes idempotently', () => {
    const f = fixture({face: true}); f.dialog.open(f.modal);
    assert.equal(f.modal.classList.contains('active'), true);
    f.dialog.close(f.modal); f.dialog.close(f.modal);
    assert.equal(f.modal.classList.contains('active'), false);
    assert.equal(f.modal.events.length, 1);
});

test('nested deletion returns to the specialty dialog before restoring the page', () => {
    const f = fixture();
    const confirmation = new f.Element(f.main);
    const cancel = new f.Element(confirmation, 0);
    f.dialog.open(f.modal); f.last.focus();
    f.dialog.open(confirmation, {initialFocus: cancel});
    assert.equal(f.document.activeElement, cancel);
    assert.equal(f.modal.inert, true);
    f.key('Escape');
    assert.equal(f.document.activeElement, f.last);
    assert.equal(f.modal.inert, false);
    assert.equal(f.modal.classList.contains('is-open'), true);
    assert.equal(f.header.inert, true);
    assert.equal(f.body.style.overflow, 'hidden');
    f.key('Escape');
    assert.equal(f.document.activeElement, f.opener);
    assert.equal(f.header.inert, false);
    assert.equal(f.body.style.overflow, 'auto');
});

function deletionFixture() {
    const f = fixture(); f.modal.classList.add('mc-modal');
    const confirmationForm = new f.Element(f.modal);
    let submitted = 0;
    const source = new f.Element(f.main);
    source.dataset = {deleteName: 'appointment'};
    source.submit = () => { submitted++; };
    const title = {};
    f.modal.querySelector = () => f.first;
    f.document.getElementById = id => ({'delete-confirmation-modal': f.modal,
        'delete-confirmation-title': title, 'delete-confirmation-form': confirmationForm}[id] || null);
    f.document.querySelectorAll = selector => ({'[data-delete-confirm]': [source],
        '[data-modal-close], [data-delete-cancel]': [f.first]}[selector] || []);
    runInNewContext(readFileSync(resolve(__dirname, '../dashboard.js'), 'utf8'), f.context);
    f.listeners.get('DOMContentLoaded')();
    const submit = target => target.dispatchEvent({type: 'submit', submitter: f.opener,
        preventDefault() {}});
    return {...f, source, confirmationForm, title, submit, submitted: () => submitted};
}

test('dashboard deletion requires confirmation and restores the submitting button', () => {
    const f = deletionFixture();
    f.submit(f.source);
    assert.equal(f.submitted(), 0);
    assert.equal(f.document.activeElement, f.first);
    assert.match(f.title.textContent, /appointment/);
    f.submit(f.confirmationForm);
    assert.equal(f.submitted(), 1);
});

test('Escape and Cancel clear pending dashboard deletion without posting', () => {
    for (const close of [f => f.key('Escape'),
        f => f.first.dispatchEvent({type: 'click'})]) {
        const f = deletionFixture(); f.submit(f.source); close(f);
        assert.equal(f.document.activeElement, f.opener);
        f.submit(f.confirmationForm);
        assert.equal(f.submitted(), 0);
        assert.equal(f.modal.attrs['aria-hidden'], 'true');
    }
});
