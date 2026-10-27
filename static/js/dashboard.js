
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("dashboard-menu-toggle");
    const sidebar = document.getElementById("dashboard-sidebar");

    if (toggle && sidebar) {
        const mobile = window.matchMedia("(max-width: 900px)");
        const close = sidebar.querySelector(".mc-sidebar-close");
        const dialogs = window.MediConnectDialog;
        function syncSidebar() {
            const opened = mobile.matches && sidebar.classList.contains("is-open");
            toggle.setAttribute("aria-expanded", String(opened));
            if (close) close.hidden = !mobile.matches;
            if (mobile.matches) {
                sidebar.setAttribute("role", "dialog");
                sidebar.setAttribute("aria-modal", "true");
                sidebar.setAttribute("aria-hidden", String(!opened));
            } else {
                sidebar.removeAttribute("role");
                sidebar.removeAttribute("aria-modal");
                sidebar.removeAttribute("aria-hidden");
            }
            // Another modal may currently own the background's inert state.
            if (!dialogs.isActive()) sidebar.inert = mobile.matches && !opened;
        }
        const closeSidebar = () => dialogs.close(sidebar);
        sidebar.addEventListener("mc:dialog-close", syncSidebar);
        document.querySelectorAll('[role="dialog"]').forEach(modal => {
            if (modal !== sidebar) modal.addEventListener("mc:dialog-close", syncSidebar);
        });
        close?.addEventListener("click", closeSidebar);
        toggle.addEventListener("click", () => {
            if (!mobile.matches) return;
            if (sidebar.classList.contains("is-open")) closeSidebar();
            else {
                sidebar.inert = false;
                dialogs.open(sidebar, {opener: toggle, initialFocus: close});
                toggle.setAttribute("aria-expanded", "true");
            }
        });
        mobile.addEventListener("change", () => {
            const focusDesktop = !mobile.matches &&
                (document.activeElement === close || document.activeElement === toggle);
            closeSidebar(); syncSidebar();
            if (focusDesktop && !dialogs.isActive()) sidebar.querySelector('a[href]')?.focus();
        });
        document.addEventListener("click", event => {
            if (mobile.matches && sidebar.classList.contains("is-open") &&
                !sidebar.contains(event.target) && !toggle.contains(event.target)) closeSidebar();
        });
        syncSidebar();
    }

    document.querySelectorAll("[data-modal-target]").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            const modal = document.getElementById(trigger.dataset.modalTarget);
            if (!modal) return;
            window.MediConnectDialog.open(modal, {opener: trigger});
        });
    });

    document.querySelectorAll("[data-modal-close], [data-delete-cancel]").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            const modal = trigger.closest(".mc-modal");
            if (!modal) return;
            window.MediConnectDialog.close(modal);
        });
    });

    const deleteModal = document.getElementById("delete-confirmation-modal");
    const deleteTitle = document.getElementById("delete-confirmation-title");
    const deleteForm = document.getElementById("delete-confirmation-form");
    let pendingDeleteForm = null;

    document.querySelectorAll("[data-delete-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!deleteModal || !deleteTitle || !deleteForm) return;
            event.preventDefault();
            pendingDeleteForm = form;
            deleteTitle.textContent = `Delete “${form.dataset.deleteName}”?`;
            window.MediConnectDialog.open(deleteModal, {
                opener: event.submitter || document.activeElement,
                initialFocus: deleteModal.querySelector("[data-delete-cancel]"),
            });
        });
    });

    if (deleteModal && deleteForm) {
        deleteForm.addEventListener("submit", (event) => {
            event.preventDefault();
            if (!pendingDeleteForm) return;
            pendingDeleteForm.submit();
        });

        deleteModal.addEventListener("mc:dialog-close", () => {
            pendingDeleteForm = null;
        });
    }
});
