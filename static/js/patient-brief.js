document.addEventListener('DOMContentLoaded', () => {
    const panel = document.getElementById('care-brief-panel');
    const holder = document.getElementById('care-brief-content');
    const status = document.querySelector('[data-brief-status]');
    const error = document.querySelector('[data-brief-error]');
    const announce = (message, failed = false) => {
        if (status) status.textContent = failed ? '' : message;
        if (error) error.textContent = failed ? message : '';
    };
    const focusResult = root => (root.querySelector('#brief-review-result') ||
        (panel && !panel.hidden ? panel.querySelector('#care-brief-title') : root.querySelector('[data-brief-heading]')))?.focus();
    let dispose = () => {}, opener = null, briefUrl = '', inlineVersion = 0;
    async function fragment(url) {
        const target = new URL(url, location.origin);
        target.searchParams.set('fragment', '1');
        const response = await fetch(target, {cache:'no-store'});
        if (!response.ok || response.redirected) throw new Error();
        return response.text();
    }
    function bind(root, refresh, isOpen = () => true) {
        const form = root.querySelector('#brief-generate');
        if (!form) return () => {};
        const button = form.querySelector('button[type=submit]');
        const progress = root.querySelector('#brief-progress');
        let stopped = false, clock = null, retry = null, started = 0, requested = false;
        const active = () => !stopped && root.isConnected && isOpen();
        const clear = () => {clearInterval(clock); clearTimeout(retry);};
        const fail = message => {
            if (!active()) return;
            clear(); progress.hidden = true; announce(message, true);
            button.disabled = false; form.removeAttribute('aria-busy');
            if (requested && document.activeElement === document.body) button.focus();
            if (!root.closest('.care-brief-inline')) error?.scrollIntoView({block:'nearest'});
        };
        const begin = () => {
            clear(); started = Date.now(); progress.hidden = false;
            announce('Préparation de votre fiche en cours…');
            button.disabled = true; form.setAttribute('aria-busy','true');
            const elapsed = progress.querySelector('[data-brief-elapsed]');
            const tick = () => {
                if (!active()) {clear(); return;}
                if (elapsed) elapsed.textContent = `${Math.floor((Date.now()-started)/1000)} s d'attente dans cette fenêtre`;
            };
            tick(); clock = setInterval(tick,1000); if (!root.closest('.care-brief-inline')) progress.scrollIntoView({block:'nearest'});
        };
        const poll = async url => {
            if (!active()) return;
            if (Date.now()-started > 185000) {fail('Le traitement est plus long que prévu. Fermez puis rouvrez la fiche pour vérifier son état.'); return;}
            try {
                const response = await fetch(url,{headers:{Accept:'application/json'},cache:'no-store'});
                if (!response.ok) throw new Error();
                const data = await response.json();
                if (!active()) return;
                if (data.status === 'ready' || data.status === 'published') {
                    clear(); await refresh(requested, data.status === 'published' ? 'La fiche est publiée et accessible au patient.' : 'Le brouillon est prêt à vérifier.');
                }
                else if (data.status === 'failed') fail(data.error || 'La génération a échoué. Vous pouvez réessayer.');
                else retry = setTimeout(() => poll(url),1800);
            } catch {fail('Impossible de vérifier le traitement. Vérifiez votre connexion, puis rouvrez la fiche.');}
        };
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (button.disabled || !active()) return;
            requested = true; begin();
            try {
                const response = await fetch(form.action,{method:'POST',body:new FormData(form),headers:{Accept:'application/json'}});
                const data = await response.json();
                if (!active()) return;
                if (!response.ok) {fail(data.error || 'Le service est indisponible.'); return;}
                await poll(data.status_url);
            } catch {fail("Le serveur n'a pas répondu. Rouvrez la fiche pour vérifier son état avant de relancer.");}
        });
        const publish = root.querySelector('[data-brief-publish]');
        if (publish) publish.addEventListener('submit',async event => {
            event.preventDefault();
            const publishButton = publish.querySelector('button');
            if (publishButton.disabled) return;
            publishButton.disabled = true; announce('Publication de la fiche en cours…');
            try {
                const response = await fetch(publish.action,{method:'POST',body:new FormData(publish),headers:{Accept:'application/json'}});
                const data = await response.json();
                if (!active()) return;
                if (!response.ok) throw new Error(data.error || "La publication n'a pas pu être confirmée.");
                await refresh(true, 'La fiche est publiée et accessible au patient.');
            } catch (failure) {
                if (active()) {
                    announce(failure.message || 'Publication non confirmée. Rouvrez la fiche pour vérifier son état.', true);
                    publishButton.disabled=false;
                    if (document.activeElement === document.body) publishButton.focus();
                }
            }
        });
        if (form.dataset.pending === 'true') {begin(); poll(form.dataset.statusUrl);}
        return () => {stopped=true; clear();};
    }
    async function loadInline(moveFocus = false, message = 'Atelier de préparation ouvert.') {
        const version = ++inlineVersion;
        const html = await fragment(briefUrl);
        if (panel.hidden || version !== inlineVersion) return;
        const previous = holder.querySelector('[data-brief-root]');
        const restore = previous?.contains(document.activeElement) || (moveFocus && document.activeElement === document.body);
        const position = window.scrollY;
        dispose(); holder.innerHTML = html;
        const root = holder.querySelector('[data-brief-root]');
        dispose = bind(root, loadInline, () => !panel.hidden);
        window.scrollTo({top:position, behavior:'instant'});
        if (restore) focusResult(root);
        if (root.querySelector('#brief-generate')?.dataset.pending !== 'true') announce(message);
    }
    const collapse = () => {
        inlineVersion++; dispose(); announce(''); panel.hidden = true;
        opener?.setAttribute('aria-expanded','false');
        opener?.focus({preventScroll:true});
    };
    if (panel && holder) {
        document.querySelectorAll('[data-brief-open]').forEach(button => button.addEventListener('click',async () => {
            if (!panel.hidden) {collapse(); return;}
            opener = button; briefUrl = button.dataset.briefOpen;
            opener.setAttribute('aria-expanded','true');
            holder.textContent = '';
            panel.hidden = false;
            announce('Ouverture de votre atelier de préparation…');
            const version = inlineVersion + 1;
            try {await loadInline();}
            catch {if (!panel.hidden && version === inlineVersion) announce('La fiche ne peut pas être ouverte. Vérifiez votre connexion et réessayez.', true);}
        }));
        panel.querySelector('[data-brief-close]').addEventListener('click',collapse);
    }
    const standalone=document.querySelector('[data-brief-root]');
    if (standalone) {
        let current=standalone, cleanup=() => {};
        const refresh=async (moveFocus=false, message='Fiche actualisée.') => {
            const html=await fragment(location.href);
            const template=document.createElement('template'); template.innerHTML=html.trim();
            const next=template.content.querySelector('[data-brief-root]');
            if (!next) throw new Error('La fiche ne peut pas être actualisée. Réessayez.');
            const restore = current.contains(document.activeElement) || (moveFocus && document.activeElement === document.body);
            cleanup(); current.replaceWith(next); current=next; cleanup=bind(current,refresh);
            if (restore) focusResult(current);
            announce(message);
        };
        cleanup=bind(current,refresh);
    }
});
