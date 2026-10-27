function uiGettext(message) { return typeof gettext === "function" ? gettext(message) : message; }
function uiInterpolate(message, values) { return message.replace(/%\(([^)]+)\)s/g, (_, key) => String(values[key])); }
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
            btn.textContent = isPassword ? (btn.dataset.labelHide || uiGettext("Hide")) : (btn.dataset.labelShow || uiGettext("Show"));
            btn.setAttribute("aria-label", btn.dataset.labelShow ? (isPassword ? uiGettext("Masquer le mot de passe") : uiGettext("Afficher le mot de passe")) : (isPassword ? uiGettext("Hide password") : uiGettext("Show password")));
        });
    });
});
