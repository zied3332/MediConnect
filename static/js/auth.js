/**
 * MediConnect — Auth page JS
 *
 * Handles password show/hide toggle only.
 * Forms now submit normally via POST to the Django backend.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Password show / hide toggles
    document.querySelectorAll("[data-password-toggle]").forEach((btn) => {
        const targetId = btn.dataset.passwordToggle;
        const input = document.getElementById(targetId);
        if (!input) return;

        btn.addEventListener("click", () => {
            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            btn.textContent = isPassword ? "Hide" : "Show";
            btn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
        });
    });
});
