
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("dashboard-menu-toggle");
    const sidebar = document.getElementById("dashboard-sidebar");

    function closeSidebar() {
        if (!sidebar || !toggle) return;
        sidebar.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
    }

    if (toggle && sidebar) {
        const close = sidebar.querySelector(".mc-sidebar-close");
        if (close) close.addEventListener("click", () => {
            closeSidebar();
            toggle.focus();
        });
        toggle.addEventListener("click", () => {
            const isOpen = sidebar.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", String(isOpen));
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                const wasOpen = sidebar.classList.contains("is-open");
                closeSidebar();
                if (wasOpen) toggle.focus();
            }
        });

        document.addEventListener("click", (event) => {
            if (
                sidebar.classList.contains("is-open") &&
                !sidebar.contains(event.target) &&
                !toggle.contains(event.target)
            ) {
                closeSidebar();
            }
        });
    }

    document.querySelectorAll("[data-modal-target]").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            const modal = document.getElementById(trigger.dataset.modalTarget);
            if (!modal) return;
            modal.classList.add("is-open");
            modal.setAttribute("aria-hidden", "false");
            modal.querySelector("input, textarea, button").focus();
        });
    });

    document.querySelectorAll("[data-modal-close]").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            const modal = trigger.closest(".mc-modal");
            if (!modal) return;
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
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
            deleteModal.classList.add("is-open");
            deleteModal.setAttribute("aria-hidden", "false");
            deleteModal.querySelector("[data-delete-cancel]").focus();
        });
    });

    if (deleteModal && deleteForm) {
        deleteForm.addEventListener("submit", (event) => {
            event.preventDefault();
            if (!pendingDeleteForm) return;
            pendingDeleteForm.submit();
        });

        deleteModal.querySelectorAll("[data-delete-cancel], [data-modal-close]").forEach((trigger) => {
            trigger.addEventListener("click", () => {
                pendingDeleteForm = null;
                deleteModal.classList.remove("is-open");
                deleteModal.setAttribute("aria-hidden", "true");
            });
        });
    }
});
