
document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("dashboard-menu-toggle");
    const sidebar = document.getElementById("dashboard-sidebar");

    if (!toggle || !sidebar) return;

    function closeSidebar() {
        sidebar.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", () => {
        const isOpen = sidebar.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(isOpen));
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSidebar();
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
});
