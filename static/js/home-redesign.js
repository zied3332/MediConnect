function uiGettext(message) { return typeof gettext === "function" ? gettext(message) : message; }
function uiInterpolate(message, values) { return message.replace(/%\(([^)]+)\)s/g, (_, key) => String(values[key])); }
(() => {
  const toggle = document.querySelector('.hp-menu-toggle');
  const menu = document.querySelector('#hp-navigation');
  if (toggle && menu) {
  const close = () => { toggle.setAttribute('aria-expanded', 'false'); menu.classList.remove('is-open'); };
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open)); menu.classList.toggle('is-open', open);
  });
  menu.addEventListener('click', event => { if (event.target.closest('a')) close(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { close(); toggle.focus(); } });
  document.addEventListener('click', event => { if (!event.target.closest('.hp-nav')) close(); });

  }
  const form = document.querySelector('.hp-search');
  const results = document.querySelector('#practitioners');
  if (form && results) {
    const feedback = document.createElement('p'); feedback.className = 'hp-filter-feedback';
    feedback.setAttribute('role', 'status'); feedback.setAttribute('aria-live', 'polite');
    form.after(feedback);
    let timer, controller, sequence = 0, composing = false;
    const query = form.querySelector('[name=q]'), specialty = form.querySelector('[name=specialty]');
    const searchUrl = () => {
      const url = new URL(form.action); url.search = ''; url.hash = '';
      for (const [key, value] of new FormData(form)) if (String(value).trim()) url.searchParams.set(key, value);
      return url;
    };
    const load = async (url, scroll = false, updateHistory = true) => {
      clearTimeout(timer); controller?.abort(); controller = new AbortController();
      const current = ++sequence; results.classList.add('is-loading'); results.setAttribute('aria-busy', 'true');
      feedback.textContent = uiGettext('Recherche dans les profils approuvés…');
      try {
        const response = await fetch(url, {signal: controller.signal, cache: 'no-store'});
        if (!response.ok || response.redirected) throw new Error();
        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        const fragment = page.querySelector('#practitioners'); if (!fragment) throw new Error();
        if (current !== sequence) return;
        results.innerHTML = fragment.innerHTML;
        feedback.textContent = fragment.querySelector('.hp-result-count')?.textContent.trim() || uiGettext('Résultats actualisés.');
        document.querySelectorAll('.hp-specialty').forEach(link => {
          const selected = new URL(link.href).searchParams.get('specialty') === specialty.value;
          link.classList.toggle('is-selected', selected);
          if (selected) link.setAttribute('aria-current', 'true'); else link.removeAttribute('aria-current');
        });
        if (updateHistory) history.replaceState(null, '', url.pathname + url.search);
        if (scroll && !matchMedia('(prefers-reduced-motion: reduce)').matches) results.scrollIntoView({behavior: 'smooth', block: 'start'});
        results.querySelectorAll('.hp-doctor-card').forEach((card, index) => { card.classList.add('hp-reveal'); card.style.animationDelay = `${index * 65}ms`; });
      } catch (error) {
        if (error.name !== 'AbortError' && current === sequence) feedback.textContent = uiGettext('La recherche a échoué. Les résultats précédents sont conservés. Réessayez.');
      } finally { if (current === sequence) { results.classList.remove('is-loading'); results.removeAttribute('aria-busy'); } }
    };
    const schedule = () => { clearTimeout(timer); controller?.abort(); sequence++; timer = setTimeout(() => load(searchUrl()), 300); };
    query.addEventListener('input', () => { if (!composing) schedule(); });
    query.addEventListener('compositionstart', () => { composing = true; clearTimeout(timer); controller?.abort(); sequence++; });
    query.addEventListener('compositionend', () => { composing = false; schedule(); });
    specialty.addEventListener('change', () => load(searchUrl()));
    form.addEventListener('submit', event => { event.preventDefault(); load(searchUrl(), true); });
    document.addEventListener('click', event => {
      const link = event.target.closest('.hp-specialty, .hp-filter-note a');
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); const url = new URL(link.href);
      query.value = url.searchParams.get('q') || ''; specialty.value = url.searchParams.get('specialty') || '';
      load(searchUrl(), true);
    });
    window.addEventListener('pagehide', () => { clearTimeout(timer); controller?.abort(); });
  }

  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('hp-reveal'); observer.unobserve(entry.target); }
    }), {threshold: 0.1});
    document.querySelectorAll('.hp-specialty, .hp-steps article, .hp-ai-banner, .hp-doctor-card').forEach(node => observer.observe(node));
  }
  const top = document.createElement('button'); top.type = 'button'; top.className = 'hp-back-top';
  top.textContent = '↑'; top.setAttribute('aria-label', uiGettext('Retour en haut de la page')); top.hidden = true;
  top.addEventListener('click', () => { window.scrollTo({top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'}); document.querySelector('.hp-menu-toggle, .pw-menu-toggle')?.focus({preventScroll: true}); });
  document.body.append(top);
  window.addEventListener('scroll', () => { top.hidden = window.scrollY < 650; }, {passive: true});
})();
