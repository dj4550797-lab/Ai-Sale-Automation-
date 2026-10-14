/**
 * FLIXORA — Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    initFunnel();
});

// ── Funnel Animation ────────────────────────────────────────
function initFunnel() {
    const bars = document.querySelectorAll('.funnel-bar');
    if (!bars.length) return;

    // Get the maximum value for scaling
    const values = Array.from(bars).map(bar => parseInt(bar.dataset.value) || 0);
    const maxVal = Math.max(...values, 1);

    bars.forEach(bar => {
        const value = parseInt(bar.dataset.value) || 0;
        const percent = Math.max(10, (value / maxVal) * 100);
        bar.style.width = '0%';

        // Animate on load
        setTimeout(() => {
            bar.style.width = percent + '%';
        }, 200);
    });
}
