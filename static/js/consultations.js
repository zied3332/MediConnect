document.addEventListener("DOMContentLoaded", () => {
    const composer = document.getElementById("id_contenu");
    const counter = document.getElementById("message-counter");
    if (composer && counter) {
        const updateCount = () => {
            counter.textContent = `${composer.value.length} / 4 000 caractères`;
        };
        composer.setAttribute("aria-describedby", "message-counter");
        composer.addEventListener("input", updateCount);
        updateCount();
    }
    const thread = document.querySelector(".care-thread");
    if (thread) thread.scrollTop = thread.scrollHeight;
});
