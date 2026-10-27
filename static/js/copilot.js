(() => {
    const form = document.getElementById('copilot-input');
    if (!form) return;
    const t = text => typeof gettext === 'function' ? gettext(text) : text;
    const source = document.getElementById('copilot-notes');
    const cards = document.getElementById('copilot-cards');
    const status = document.getElementById('copilot-status');
    const approval = document.getElementById('copilot-approval');
    const reviewed = document.getElementById('copilot-reviewed');
    const loading = document.getElementById('copilot-loading');
    let snapshot = '', pending = false;
    source.addEventListener('input', () => { reviewed.checked = false; approval.hidden = true; });
    cards.addEventListener('input', () => { reviewed.checked = false; });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (pending || !form.reportValidity()) return;
        pending = true;
        const submitted = source.value;
        const submit = form.querySelector('[type=submit]');
        submit.disabled = true;
        reviewed.checked = false;
        approval.hidden = cards.hidden = true;
        document.getElementById('copilot-empty').hidden = true;
        loading.hidden = false;
        status.textContent = '';
        const started = Date.now();
        document.getElementById('copilot-clock').textContent = '0 s';
        const clock = setInterval(() => { document.getElementById('copilot-clock').textContent = Math.floor((Date.now()-started)/1000) + ' s'; }, 1000);
        form.setAttribute('aria-busy','true');
        try {
            const response = await fetch(form.action,{method:'POST',body:new FormData(form),headers:{'Accept':'application/json'},signal:AbortSignal.timeout(45000)});
            if (response.redirected) throw new Error(t('Votre session a expiré. Reconnectez-vous.'));
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || t('La demande a échoué. Réessayez.'));
            if (source.value !== submitted) throw new Error(t('Les notes ont changé. Relancez la préparation.'));
            snapshot = submitted;
            cards.replaceChildren();
            for (const section of data.sections) {
                const article = document.createElement('article');
                const title = document.createElement('h4');
                const label = document.createElement('label');
                const input = document.createElement('textarea');
                input.id = 'draft-' + section.key;
                input.dataset.section = section.key;
                input.dataset.title = section.title;
                input.value = section.text;
                input.maxLength = 8000;
                input.rows = 3;
                input.placeholder = t('Non renseigné dans les notes.');
                label.htmlFor = input.id;
                label.textContent = section.title;
                title.append(label);
                article.append(title,input);
                if (section.sources.length) {
                    const details = document.createElement('details');
                    const summary = document.createElement('summary');
                    summary.textContent = t('Voir les extraits d’origine');
                    details.append(summary);
                    for (const quote of section.sources) {
                        const block = document.createElement('blockquote');
                        block.textContent = quote;
                        details.append(block);
                    }
                    article.append(details);
                }
                cards.append(article);
            }
            cards.hidden = approval.hidden = false;
            status.textContent = t('Brouillon prêt. Comparez les rubriques avec vos notes avant de les appliquer.');
        } catch (error) {
            status.textContent = error.name === 'TimeoutError' || error.name === 'AbortError' ? t('Le délai de réponse a été dépassé. Vous pouvez réessayer.') : (error.message || t('La demande a échoué. Réessayez.'));
        } finally {
            clearInterval(clock);
            pending = false;
            submit.disabled = false;
            loading.hidden = true;
            form.removeAttribute('aria-busy');
        }
    });
    document.getElementById('copilot-apply').addEventListener('click', () => {
        if (source.value !== snapshot || !reviewed.checked) {
            status.textContent = t('Vérifiez le brouillon et cochez la confirmation.');
            reviewed.focus({preventScroll:true});
            return;
        }
        const diagnostic = document.getElementById('id_diagnostic');
        const notes = document.getElementById('id_notes');
        if ((diagnostic.value || notes.value) && !window.confirm(t('Remplacer les champs du compte rendu par ce brouillon ?'))) return;
        const diagnosis = cards.querySelector('[data-section=diagnostic]').value.trim();
        // An absent diagnosis must be completed explicitly by the physician.
        diagnostic.value = diagnosis;
        notes.value = [...cards.querySelectorAll('textarea')].filter(input=>input.dataset.section!=='diagnostic' && input.value.trim()).map(input=>input.dataset.title+'\n'+input.value.trim()).join('\n\n');
        diagnostic.dispatchEvent(new Event('input',{bubbles:true}));
        notes.dispatchEvent(new Event('input',{bubbles:true}));
        status.textContent = t('Brouillon appliqué. Vérifiez le formulaire puis enregistrez le compte rendu.');
        diagnostic.focus({preventScroll:true});
        document.getElementById('consultation-report-form').scrollIntoView({block:'start',behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
    });
})();
