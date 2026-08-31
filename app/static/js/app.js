/**
 * FLIXORA — Core Application JavaScript
 * Sidebar toggle, toasts, dialogs, CSRF, fetch wrapper
 */

// ── Sidebar Toggle ──────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('visible');
}

function closeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('visible');
}

// ── Toast Notifications ─────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
    const container = document.querySelector('.toast-container') || createToastContainer();
    
    const icons = {
        success: 'check_circle',
        error: 'error',
        warning: 'warning',
        info: 'info',
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="material-symbols-outlined toast-icon">${icons[type] || 'info'}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <span class="material-symbols-outlined">close</span>
        </button>
    `;

    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// ── Dialog Management ───────────────────────────────────────
function openDialog(dialogId) {
    const overlay = document.getElementById(dialogId);
    if (overlay) {
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }
}

function closeDialog(dialogId) {
    const overlay = document.getElementById(dialogId);
    if (overlay) {
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    }
}

// Close dialog on overlay click
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('dialog-overlay') && e.target.classList.contains('open')) {
        e.target.classList.remove('open');
        document.body.style.overflow = '';
    }
});

// Close dialog on Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const openDialogs = document.querySelectorAll('.dialog-overlay.open');
        openDialogs.forEach(d => {
            d.classList.remove('open');
        });
        document.body.style.overflow = '';
    }
});

// ── CSRF Token ──────────────────────────────────────────────
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// ── Fetch Wrapper ───────────────────────────────────────────
async function apiFetch(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
    };

    const config = { ...defaults, ...options };
    if (options.headers) {
        config.headers = { ...defaults.headers, ...options.headers };
    }

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Request failed (${response.status})`);
        }
        return data;
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    }
}

// ── Tabs ────────────────────────────────────────────────────
function initTabs() {
    document.querySelectorAll('.tabs').forEach(tabGroup => {
        const tabs = tabGroup.querySelectorAll('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                // Deactivate all
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Show corresponding panel
                const target = tab.dataset.tab;
                if (target) {
                    const parent = tabGroup.parentElement;
                    parent.querySelectorAll('.tab-panel').forEach(panel => {
                        panel.classList.toggle('active', panel.id === target);
                    });
                }
            });
        });
    });
}

// ── Dropdown ────────────────────────────────────────────────
function initDropdowns() {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
        const trigger = dropdown.querySelector('[data-dropdown-trigger]');
        const menu = dropdown.querySelector('.dropdown-menu');

        if (trigger && menu) {
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                // Close all other dropdowns
                document.querySelectorAll('.dropdown-menu.open').forEach(m => {
                    if (m !== menu) m.classList.remove('open');
                });
                menu.classList.toggle('open');
            });
        }
    });

    // Close dropdowns on outside click
    document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    });
}

// ── Password Toggle ─────────────────────────────────────────
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
    }
}

// ── Flash Message Auto-Dismiss ──────────────────────────────
function initFlashMessages() {
    document.querySelectorAll('.flash').forEach(flash => {
        setTimeout(() => {
            flash.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });
}

// ── Active Nav ──────────────────────────────────────────────
function setActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href && path.startsWith(href) && href !== '/') {
            item.classList.add('active');
        } else if (href === '/dashboard' && (path === '/' || path === '/dashboard')) {
            item.classList.add('active');
        }
    });
}

// ── Initialize ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setActiveNav();
    initTabs();
    initDropdowns();
    initFlashMessages();

    // Sidebar overlay click
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }
});
