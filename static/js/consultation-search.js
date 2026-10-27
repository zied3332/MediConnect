function uiGettext(message) { return typeof gettext === "function" ? gettext(message) : message; }
function uiInterpolate(message, values) { return message.replace(/%\(([^)]+)\)s/g, (_, key) => String(values[key])); }
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-live-search]").forEach((form) => {
        const results = document.querySelector("[data-live-results]");
        const status = document.querySelector("[data-live-status]");
        if (!results || !status) return;
        let timer = null;
        let controller = null;
        let sequence = 0;
        let composing = false;
        const cancel = () => {
            clearTimeout(timer);
            controller?.abort();
            sequence += 1;
        };
        const searchUrl = () => {
            const url = new URL(window.location.pathname, window.location.origin);
            new FormData(form).forEach((value, key) => {
                if (String(value).trim()) url.searchParams.set(key, String(value).trim());
            });
            return url;
        };
        const load = async (url, fromPagination = false) => {
            cancel();
            const requestId = sequence;
            controller = new AbortController();
            form.classList.add("is-searching");
            results.setAttribute("aria-busy", "true");
            status.textContent = uiGettext("Recherche en cours…");
            try {
                const response = await fetch(url, {
                    headers: {"X-Live-Search": "1"},
                    signal: controller.signal,
                    cache: "no-store",
                });
                if (!response.ok || response.redirected) throw new Error();
                const html = await response.text();
                if (requestId !== sequence) return;
                const focusResults = results.contains(document.activeElement) ||
                    (fromPagination && document.activeElement === document.body);
                results.innerHTML = html;
                const count = results.querySelector("[data-live-count]");
                // Focusing the count already announces it; avoid a second live announcement.
                status.textContent = count?.hasAttribute("data-live-announcement") || (focusResults && count) ? "" : count?.textContent.trim() || uiGettext("Résultats actualisés.");
                if (focusResults) count?.focus();
                window.history.replaceState(null, "", url.pathname + url.search);
            } catch (error) {
                if (error.name !== "AbortError" && requestId === sequence) {
                    status.textContent = uiGettext("La recherche n'a pas abouti. Vos résultats précédents restent affichés ; réessayez ou vérifiez votre connexion.");
                }
            } finally {
                if (requestId === sequence) {
                    form.classList.remove("is-searching");
                    results.removeAttribute("aria-busy");
                }
            }
        };
        const schedule = () => {
            cancel();
            timer = setTimeout(() => load(searchUrl()), 300);
        };
        form.addEventListener("input", (event) => {
            if (event.target.matches('input[name="q"]') && !composing) schedule();
        });
        form.addEventListener("compositionstart", () => { composing = true; cancel(); });
        form.addEventListener("compositionend", () => { composing = false; schedule(); });
        form.addEventListener("change", (event) => {
            if (event.target.matches("select")) load(searchUrl());
        });
        form.addEventListener("submit", (event) => { event.preventDefault(); load(searchUrl()); });
        form.querySelector("[data-live-reset]")?.addEventListener("click", () => {
            form.querySelectorAll('input[name="q"], select').forEach((field) => { field.value = ""; });
            load(searchUrl());
            form.querySelector('input[name="q"]')?.focus({preventScroll: true});
        });
        results.addEventListener("click", (event) => {
            const link = event.target.closest(".care-pagination a");
            if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
            event.preventDefault();
            load(new URL(link.href), true);
        });
        window.addEventListener("pagehide", cancel);
    });
});
