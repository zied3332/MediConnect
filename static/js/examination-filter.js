document.addEventListener('DOMContentLoaded', () => {
    const search = document.getElementById('examSearch');
    const items = document.querySelectorAll('#examList .exam-item');
    const noResults = document.getElementById('examNoResults');
    const status = document.getElementById('examFilterStatus');
    if (!search) return;
    search.addEventListener('input', () => {
        const query = search.value.trim().toLowerCase();
        let count = 0;
        items.forEach(item => {
            const matches = (item.dataset.examTitle || '').toLowerCase().includes(query);
            item.hidden = !matches;
            if (matches) count++;
        });
        if (noResults) noResults.hidden = count !== 0;
        if (status) status.textContent = `${count} of ${items.length} examination${items.length === 1 ? '' : 's'} shown.`;
    });
});
