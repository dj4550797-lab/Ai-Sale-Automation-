/**
 * FLIXORA — Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    initFunnel();
    initLiveDashboardStats();
});

// ── Live KPI Auto-Updating (No Manual Reload!) ─────────────
function initLiveDashboardStats() {
    function updateStats() {
        fetch('/dashboard/stats')
            .then(r => r.json())
            .then(data => {
                if (!data || !data.success) return;
                
                const map = {
                    'today_leads': data.today_leads,
                    'qualified_leads': data.qualified_leads,
                    'prds_pending': data.prds_pending,
                    'demos_ready': data.demos_ready,
                    'messages_sent': data.messages_sent,
                    'replies': data.replies,
                    'deals_won': data.deals_won
                };
                
                Object.keys(map).forEach(key => {
                    const el = document.querySelector(`[data-kpi="${key}"]`);
                    if (el && map[key] !== undefined && el.textContent.trim() !== String(map[key])) {
                        el.textContent = map[key];
                        el.style.transition = 'color 0.3s ease';
                        el.style.color = 'var(--primary-600)';
                        setTimeout(() => {
                            el.style.color = '';
                        }, 1200);
                    }
                });
            })
            .catch(() => {});
    }

    // Auto-update dashboard metrics every 10 seconds
    setInterval(updateStats, 10000);
}

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
