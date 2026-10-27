// Small event/element doubles for interaction contracts, not a browser emulator.
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {runInNewContext} = require('node:vm');

function environment() {
    let document;
    function node(attrs = {}) {
        const events = new Map(), selectors = new Map(), classes = new Set();
        return {attrs, events, selectors, dataset: {}, style: {}, hidden: false,
            isConnected: true, textContent: '', innerHTML: '', children: [],
            classList: {add: value => classes.add(value), remove: value => classes.delete(value),
                contains: value => classes.has(value), toggle(value) {
                    if (classes.has(value)) { classes.delete(value); return false; }
                    classes.add(value); return true;
                }},
            getAttribute: name => attrs[name] ?? null,
            setAttribute: (name, value) => { attrs[name] = value; },
            removeAttribute: name => { delete attrs[name]; },
            querySelector: selector => selectors.get(selector) || null,
            querySelectorAll: selector => selectors.get(selector) || [],
            contains(target) { return this === target || this.children.some(child => child.contains(target)); },
            closest() { return null; }, matches() { return false; },
            focus() { document.activeElement = this; }, scrollIntoView() {},
            addEventListener(type, callback) {
                if (!events.has(type)) events.set(type, []);
                events.get(type).push(callback);
            },
            async fire(type, options = {}) {
                const event = {target: this, preventDefault() { this.defaultPrevented = true; },
                    stopPropagation() {}, stopImmediatePropagation() {}, ...options};
                for (const callback of events.get(type) || []) await callback(event);
                return event;
            },
        };
    }
    document = node(); document.body = node(); document.activeElement = document.body;
    document.ids = new Map(); document.getElementById = id => document.ids.get(id) || null;
    const window = node(); window.location = {pathname: '/consultations/', origin: 'https://example.test'};
    window.history = {replaceState() {}};
    const timers = [];
    const context = {document, window, URL, AbortController, console,
        location: {...window.location, href: 'https://example.test/consultations/'},
        setTimeout: callback => { timers.push(callback); return timers.length; }, clearTimeout() {},
        setInterval: () => 1, clearInterval() {}, FormData: class { forEach() {} }};
    return {document, window, context, node, timers,
        run(file) { runInNewContext(readFileSync(resolve(__dirname, '..', file), 'utf8'), context); },
        ready() { return document.fire('DOMContentLoaded'); }};
}
module.exports = {environment};
