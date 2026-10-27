
/**
 * MediConnect navigation interactions.
 * No external JavaScript dependencies.
 */

document.addEventListener("DOMContentLoaded", () => {
    const dropdownButtons = document.querySelectorAll(
        "[data-mc-dropdown]"
    );

    const mobileToggle = document.querySelector(
        ".mc-nav-mobile-toggle"
    );

    const mobileMenu = document.querySelector(
        "#mc-nav-mobile-menu"
    );

    function closeDropdowns(restoreFocus = false) {
        dropdownButtons.forEach((button) => {
            button.setAttribute("aria-expanded", "false");

            const menuId = button.getAttribute("aria-controls");
            const menu = document.getElementById(menuId);

            if (menu) {
                if (restoreFocus === true && !menu.hidden && menu.contains(document.activeElement)) button.focus();
                menu.hidden = true;
            }
        });
    }

    dropdownButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const wasOpen =
                button.getAttribute("aria-expanded") === "true";

            closeDropdowns();

            if (!wasOpen) {
                const menuId = button.getAttribute("aria-controls");
                const menu = document.getElementById(menuId);

                if (menu) {
                    menu.hidden = false;
                    button.setAttribute("aria-expanded", "true");
                }
            }
        });
    });

    function closeMobileMenu(restoreFocus = false) {
        if (!mobileToggle || !mobileMenu) return;

        if (restoreFocus === true && !mobileMenu.hidden && mobileMenu.contains(document.activeElement)) mobileToggle.focus();
        mobileMenu.hidden = true;
        mobileToggle.setAttribute("aria-expanded", "false");
        mobileToggle.setAttribute(
            "aria-label",
            "Open navigation menu"
        );
    }

    if (mobileToggle && mobileMenu) {
        mobileToggle.addEventListener("click", () => {
            const isOpen =
                mobileToggle.getAttribute("aria-expanded") === "true";

            mobileMenu.hidden = isOpen;
            mobileToggle.setAttribute(
                "aria-expanded",
                String(!isOpen)
            );

            mobileToggle.setAttribute(
                "aria-label",
                isOpen
                    ? "Open navigation menu"
                    : "Close navigation menu"
            );
        });

        mobileMenu.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", closeMobileMenu);
        });
    }

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".mc-nav-dropdown")) {
            closeDropdowns();
        }

        if (!event.target.closest(".mc-nav")) {
            closeMobileMenu();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeDropdowns(true);
            closeMobileMenu(true);
        }
    });

    window.matchMedia("(min-width: 1051px)")
        .addEventListener("change", (event) => {
            if (event.matches) {
                closeMobileMenu();
            }
        });
});
