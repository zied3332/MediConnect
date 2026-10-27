function uiGettext(message) { return typeof gettext === "function" ? gettext(message) : message; }
function uiInterpolate(message, values) { return message.replace(/%\(([^)]+)\)s/g, (_, key) => String(values[key])); }
document.addEventListener("DOMContentLoaded", () => {
    const composer = document.getElementById("id_contenu");
    const counter = document.getElementById("message-counter");
    if (composer && counter) {
        const updateCount = () => {
            counter.textContent = uiInterpolate(uiGettext("%(v0)s / 4 000 caractères"), {v0:(composer.value.length)});
        };
        const descriptions = new Set((composer.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean));
        descriptions.add("message-counter");
        composer.setAttribute("aria-describedby", [...descriptions].join(" "));
        composer.addEventListener("input", updateCount);
        updateCount();
    }
    const thread = document.querySelector(".care-thread");
    if (thread) {
        const latest = document.createElement('button');
        latest.type = 'button';
        latest.className = 'care-scroll-latest';
        latest.textContent = '↓ ' + uiGettext('Messages');
        latest.hidden = true;
        thread.after(latest);
        const updateLatest = () => {
            latest.hidden = thread.scrollHeight - thread.clientHeight - thread.scrollTop < 90;
        };
        thread.addEventListener('scroll', updateLatest, {passive:true});
        latest.addEventListener('click', () => {
            thread.scrollTo({top:thread.scrollHeight, behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
            thread.focus({preventScroll:true});
        });
        requestAnimationFrame(() => {
            thread.scrollTop = thread.scrollHeight;
            updateLatest();
        });
    }
    document.querySelectorAll('[data-message-edit]').forEach(link => {
        link.addEventListener('click', event => {
            const editor = document.getElementById(link.getAttribute('aria-controls'));
            if (!editor) return;
            event.preventDefault();
            link.closest('.care-message-actions').hidden = true;
            editor.hidden = false;
            editor.querySelector('textarea').focus({preventScroll:true});
        });
    });
    document.querySelectorAll('.care-message-editor').forEach(editor => {
        const status = document.createElement('p');
        status.setAttribute('role', 'status');
        editor.append(status);
        editor.addEventListener('submit', async event => {
            event.preventDefault();
            const submit = editor.querySelector('[type=submit]');
            if (submit.disabled) return;
            submit.disabled = true;
            status.textContent = '';
            try {
                const response = await fetch(editor.action, {
                    method:'POST', body:new FormData(editor),
                    headers:{'X-Requested-With':'XMLHttpRequest'},
                    signal:AbortSignal.timeout(20000)
                });
                if (response.redirected) throw new Error(uiGettext('Votre session a expiré. Reconnectez-vous.'));
                const data = await response.json();
                if (!response.ok) {
                    status.textContent = Object.values(data.errors || {}).flat().map(error=>error.message).join(' ') || uiGettext('La demande a échoué. Réessayez.');
                    return;
                }
                const bubble = editor.closest('article');
                bubble.querySelector(':scope > p').textContent = data.contenu;
                const metadata = bubble.querySelector(':scope > small');
                if (metadata) metadata.textContent = metadata.textContent.replace(/ · .*/, '') + ' · ' + uiGettext('Envoyé');
                editor.querySelector('textarea').defaultValue = data.contenu;
                editor.hidden = true;
                const actions = bubble.querySelector('.care-message-actions');
                actions.hidden = false;
                actions.querySelector('[data-message-edit]').focus({preventScroll:true});
            } catch (error) {
                status.textContent = uiGettext('La demande a échoué. Réessayez.');
            } finally {
                submit.disabled = false;
            }
        });
    });
    document.querySelectorAll('[data-message-cancel]').forEach(button => {
        button.addEventListener('click', () => {
            const editor = button.closest('form');
            editor.reset();
            editor.hidden = true;
            const actions = editor.closest('article').querySelector('.care-message-actions');
            actions.hidden = false;
            actions.querySelector('[data-message-edit]').focus();
        });
    });
    document.querySelectorAll('[data-message-delete]').forEach(form => {
        form.addEventListener('submit', event => {
            if (!window.confirm(form.dataset.confirm)) event.preventDefault();
        });
    });
});
