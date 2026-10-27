const {test} = require('node:test');
const assert = require('node:assert/strict');
const {environment} = require('./interaction-fixture.cjs');

async function fixture() {
    const f = environment(), search = f.node(), status = f.node(), empty = f.node();
    const items = [f.node(), f.node()];
    items[0].dataset.examTitle = 'Blood test'; items[1].dataset.examTitle = 'Chest scan';
    search.value = ''; empty.hidden = true;
    for (const [id, node] of [['examSearch', search], ['examFilterStatus', status], ['examNoResults', empty]]) f.document.ids.set(id, node);
    f.document.selectors.set('#examList .exam-item', items);
    f.run('examination-filter.js'); await f.ready();
    return {...f, search, status, empty, items};
}

test('initialization does not announce or move focus; filtering hides nonmatches', async () => {
    const f = await fixture(); assert.equal(f.status.textContent, '');
    f.search.focus(); f.search.value = ' BLOOD '; await f.search.fire('input');
    assert.equal(f.items[0].hidden, false); assert.equal(f.items[1].hidden, true);
    assert.equal(f.document.activeElement, f.search); assert.equal(f.status.textContent, '1 of 2 examinations shown.');
});

test('empty results and clearing the filter update one persistent count region', async () => {
    const f = await fixture(); f.search.value = 'missing'; await f.search.fire('input');
    assert.equal(f.empty.hidden, false); assert.equal(f.status.textContent, '0 of 2 examinations shown.');
    f.search.value = ''; await f.search.fire('input');
    assert.equal(f.empty.hidden, true); assert.equal(f.items.every(item => !item.hidden), true);
    assert.equal(f.status.textContent, '2 of 2 examinations shown.');
});
