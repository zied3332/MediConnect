
/**
 * MediConnect — Authentication UI.
 * Frontend preview only. No credentials are sent or stored.
 */

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const inputId = button.dataset.passwordToggle;
            const input = document.getElementById(inputId);

            if (!input) return;

            const isVisible = input.type === "text";

            input.type = isVisible ? "password" : "text";
            button.textContent = isVisible ? "Show" : "Hide";
            button.setAttribute(
                "aria-label",
                isVisible ? "Show password" : "Hide password"
            );
        });
    });

    ["mc-login-form", "mc-signup-form"].forEach((formId) => {
        const form = document.getElementById(formId);

        if (!form) return;

        form.addEventListener("submit", (event) => {
            event.preventDefault();

            // Real authentication will be implemented later.
            // Never log or store entered passwords.
        });
    });
});
