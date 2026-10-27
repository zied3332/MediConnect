function uiGettext(message) { return typeof gettext === "function" ? gettext(message) : message; }
function uiInterpolate(message, values) { return message.replace(/%\(([^)]+)\)s/g, (_, key) => String(values[key])); }
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
        if (status) status.textContent = uiInterpolate(uiGettext("Examens affichés : %(shown)s / %(total)s"), {shown:count, total:items.length});
    });
});
