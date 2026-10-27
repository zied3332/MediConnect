document.addEventListener('DOMContentLoaded', () => {
    let active = null, timer = null;
    const hide = () => {
        if (active) active.tooltip.classList.remove('is-visible');
        active = null;
    };
    const position = () => {
        if (!active) return;
        const anchor = active.badge.getBoundingClientRect();
        const box = active.tooltip.getBoundingClientRect();
        const left = Math.max(12, Math.min(anchor.left + anchor.width / 2 - box.width / 2, window.innerWidth - box.width - 12));
        const above = anchor.top - box.height - 8;
        const top = above >= 12 ? above : anchor.bottom + 8;
        active.tooltip.style.left = `${left}px`;
        active.tooltip.style.top = `${Math.max(12, Math.min(top, window.innerHeight - box.height - 12))}px`;
    };
    document.querySelectorAll('[data-risk-tooltip]').forEach(badge => {
        const tooltip = badge.querySelector('[role="tooltip"]');
        if (!tooltip) return;
        // A body-level fixed tooltip escapes the table's overflow clipping.
        document.body.appendChild(tooltip);
        const state = {badge, tooltip, overBadge: false, overTooltip: false};
        const show = () => {
            clearTimeout(timer);
            if (active !== state) hide();
            active = state; tooltip.classList.add('is-visible'); position();
        };
        const leave = () => {
            clearTimeout(timer);
            timer = setTimeout(() => {
                if (active === state && !state.overBadge && !state.overTooltip && !badge.matches(':focus-within')) hide();
            }, 150);
        };
        badge.addEventListener('pointerenter', () => { state.overBadge = true; show(); });
        badge.addEventListener('pointerleave', () => { state.overBadge = false; leave(); });
        badge.addEventListener('focusin', show);
        badge.addEventListener('focusout', leave);
        tooltip.addEventListener('pointerenter', () => { state.overTooltip = true; clearTimeout(timer); });
        tooltip.addEventListener('pointerleave', () => { state.overTooltip = false; leave(); });
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && active) {
            hide(); event.preventDefault(); event.stopPropagation();
        }
    });
    document.addEventListener('focusin', event => {
        if (active && !active.badge.contains(event.target) && !active.tooltip.contains(event.target)) hide();
    });
    window.addEventListener('resize', position);
    window.addEventListener('scroll', position, true);
});
