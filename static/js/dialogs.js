/* Shared modal lifecycle. Keep existing layouts; isolate the rest of the page. */
(() => {
    "use strict";
    let current = null;
    const selector = 'a[href], button, input:not([type="hidden"]), select, textarea, summary, [tabindex]';

    function focusable(modal) {
        return [...modal.querySelectorAll(selector)].filter(element =>
            element.tabIndex >= 0 && !element.matches(":disabled") &&
            !element.closest("[inert]") && element.getClientRects().length > 0 &&
            getComputedStyle(element).visibility !== "hidden"
        );
    }

    function focusFirst() {
        if (!current) return;
        const {modal, initialFocus} = current;
        const controls = focusable(modal);
        (controls.includes(initialFocus) ? initialFocus : controls[0] || modal).focus();
    }

    function close(modal) {
        if (!current || current.modal !== modal) return;
        const state = current;
        current = state.previous;
        state.background.forEach((inert, element) => { element.inert = inert; });
        current?.background.forEach((_, element) => { element.inert = true; });
        document.body.style.overflow = state.overflow;
        // Move focus out before hiding the dialog from assistive technology.
        if (state.opener?.isConnected && !state.opener.closest("[inert]")) {
            state.opener.focus();
        } else {
            document.querySelector("main")?.focus();
        }
        modal.classList.remove(state.openClass);
        modal.setAttribute("aria-hidden", "true");
        modal.dispatchEvent(new CustomEvent("mc:dialog-close"));
    }

    function open(modal, {opener = document.activeElement, initialFocus = null} = {}) {
        if (!modal || current?.modal === modal) return;
        // A specialty dialog can open its deletion confirmation. Suspend its
        // isolation, then restore it when the confirmation closes.
        const previous = current;
        previous?.background.forEach((inert, element) => { element.inert = inert; });
        const background = new Map();
        let branch = modal;
        while (branch.parentElement) {
            for (const sibling of branch.parentElement.children) {
                if (sibling !== branch) {
                    background.set(sibling, sibling.inert);
                    sibling.inert = true;
                }
            }
            if (branch.parentElement === document.body) break;
            branch = branch.parentElement;
        }
        const openClass = modal.classList.contains("face-login-modal") ? "active" : "is-open";
        current = {modal, opener, initialFocus, background, openClass, previous,
            overflow: document.body.style.overflow};
        document.body.style.overflow = "hidden";
        modal.setAttribute("tabindex", "-1");
        modal.removeAttribute("aria-hidden");
        modal.classList.add(openClass);
        focusFirst();
    }

    document.addEventListener("keydown", event => {
        if (!current) return;
        if (event.key === "Escape") {
            event.preventDefault();
            event.stopImmediatePropagation();
            close(current.modal);
        } else if (event.key === "Tab") {
            const {modal} = current;
            const controls = focusable(modal);
            const index = controls.indexOf(document.activeElement);
            if (!controls.length || index < 0 ||
                (event.shiftKey && index === 0) ||
                (!event.shiftKey && index === controls.length - 1)) {
                event.preventDefault();
                (event.shiftKey ? controls.at(-1) || modal : controls[0] || modal).focus();
            }
        }
    }, true);

    document.addEventListener("focusin", event => {
        if (current && !current.modal.contains(event.target)) focusFirst();
    });

    window.MediConnectDialog = {open, close};
})();
