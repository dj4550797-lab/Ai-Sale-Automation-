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

// ── Toast Notifications & Alert Override ────────────────────
window.alert = function(message) {
    showToast(message, 'info');
};

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

// ── In-App Confirmation Modal (No Chrome Popups) ────────────
function showFlixoraConfirm({ title = 'Please Confirm', message = 'Are you sure you want to proceed?', confirmText = 'Confirm', isDanger = true, onConfirm }) {
    let overlay = document.getElementById('globalConfirmModal');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'dialog-overlay';
        overlay.id = 'globalConfirmModal';
        overlay.innerHTML = `
            <div class="dialog" style="max-width: 440px; border-radius: var(--radius-lg); box-shadow: var(--shadow-xl);">
                <div class="dialog-header" style="padding: var(--space-5) var(--space-6) var(--space-3); border-bottom: 1px solid var(--border-color);">
                    <h3 id="globalConfirmTitle" style="font-size: var(--text-lg); font-weight: 600; margin: 0; color: var(--text-primary);">${title}</h3>
                </div>
                <div class="dialog-body" style="padding: var(--space-4) var(--space-6);">
                    <p id="globalConfirmMsg" style="color: var(--text-secondary); font-size: var(--text-sm); line-height: 1.5; margin: 0;"></p>
                </div>
                <div class="dialog-footer" style="padding: var(--space-3) var(--space-6) var(--space-5); display: flex; justify-content: flex-end; gap: var(--space-3); border-top: 1px solid var(--border-color);">
                    <button class="btn btn-secondary btn-sm" id="globalConfirmCancel">Cancel</button>
                    <button class="btn btn-sm" id="globalConfirmSubmit">${confirmText}</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    document.getElementById('globalConfirmTitle').textContent = title;
    document.getElementById('globalConfirmMsg').textContent = message;
    
    const submitBtn = document.getElementById('globalConfirmSubmit');
    submitBtn.textContent = confirmText;
    submitBtn.className = isDanger ? 'btn btn-danger btn-sm' : 'btn btn-primary btn-sm';

    const cancelBtn = document.getElementById('globalConfirmCancel');
    
    const close = () => {
        closeDialog('globalConfirmModal');
        cancelBtn.onclick = null;
        submitBtn.onclick = null;
    };
    
    cancelBtn.onclick = close;
    submitBtn.onclick = () => {
        close();
        if (typeof onConfirm === 'function') {
            onConfirm();
        }
    };

    openDialog('globalConfirmModal');
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

// ── Intercept Delete & Confirm Actions (Zero Chrome Popups) ──
function initConfirmInterceptors() {
    // 1. Intercept forms using data-confirm
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.dataset.skipConfirm === 'true') {
            form.dataset.skipConfirm = 'false';
            return;
        }
        const confirmMsg = form.getAttribute('data-confirm');
        if (confirmMsg) {
            e.preventDefault();
            showFlixoraConfirm({
                title: 'Please Confirm',
                message: confirmMsg,
                confirmText: 'Yes, Delete',
                isDanger: true,
                onConfirm: () => {
                    form.dataset.skipConfirm = 'true';
                    form.submit();
                }
            });
        }
    });

    // 2. Auto-upgrade any inline onsubmit/onclick that uses confirm()
    document.querySelectorAll('form[onsubmit*="confirm("], a[onclick*="confirm("], button[onclick*="confirm("]').forEach(el => {
        const attrName = el.hasAttribute('onsubmit') ? 'onsubmit' : 'onclick';
        const rawAttr = el.getAttribute(attrName) || '';
        const match = rawAttr.match(/confirm\(['"](.*?)['"]\)/);
        const msg = match ? match[1] : 'Are you sure you want to proceed?';

        if (el.tagName === 'FORM') {
            el.removeAttribute('onsubmit');
            el.setAttribute('data-confirm', msg);
        } else {
            el.removeAttribute('onclick');
            el.addEventListener('click', function(e) {
                e.preventDefault();
                showFlixoraConfirm({
                    title: 'Please Confirm',
                    message: msg,
                    confirmText: 'Proceed',
                    isDanger: true,
                    onConfirm: () => {
                        if (el.tagName === 'A') {
                            window.location.href = el.href;
                        } else if (el.form) {
                            el.form.dataset.skipConfirm = 'true';
                            el.form.submit();
                        }
                    }
                });
            });
        }
    });
}

// ── Theme Switcher (Multi-Themes System) ─────────────────────
function initAppTheme() {
    const currentTheme = localStorage.getItem('flixora_theme') || 'light';
    applyTheme(currentTheme);
}

function selectTheme(themeName) {
    localStorage.setItem('flixora_theme', themeName);
    applyTheme(themeName);
    const themeTitles = {
        'light': 'Clean SaaS (Light)',
        'dark': 'Obsidian Dark (Matte)',
        'glass': 'Liquid Frosted Glassmorphism',
        'flat': 'Flat UI Design',
        'neo-brutalism': 'Neo-Brutalism',
        'cyberpunk': 'Cyberpunk Neon',
        'synthwave': 'Retro-Futurism / Synthwave'
    };
    showToast(`🎨 Theme applied: ${themeTitles[themeName] || themeName}`, 'info', 2200);
}

function applyTheme(theme) {
    if (theme && theme !== 'light') {
        document.documentElement.setAttribute('data-theme', theme);
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    document.querySelectorAll('.theme-card-option').forEach(card => {
        if (card.dataset.theme === theme || (!theme && card.dataset.theme === 'light')) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });
}

// ── Typography Font Selection ──────────────────────────────
function initAppFont() {
    const currentFont = localStorage.getItem('flixora_font') || 'inter';
    applyFont(currentFont);
}

function selectFont(fontName) {
    localStorage.setItem('flixora_font', fontName);
    applyFont(fontName);
    const fontTitles = {
        'inter': 'Inter (Clean SaaS)',
        'outfit': 'Outfit (Geometric Display)',
        'jakarta': 'Plus Jakarta Sans (Startup)',
        'space': 'Space Grotesk (Futuristic)',
        'mono': 'JetBrains Mono (Code/Tech)',
        'serif': 'Playfair Display (Editorial Serif)'
    };
    showToast(`🔤 Font applied: ${fontTitles[fontName] || fontName}`, 'info', 2200);
}

function applyFont(font) {
    document.documentElement.setAttribute('data-font', font || 'inter');
    document.querySelectorAll('.font-card-option').forEach(card => {
        if (card.dataset.font === font || (!font && card.dataset.font === 'inter')) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });
}

// ── Initialize ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initAppTheme();
    initAppFont();
    setActiveNav();
    initTabs();
    initDropdowns();
    initFlashMessages();
    initConfirmInterceptors();

    // Sidebar overlay click
    const overlay = document.querySelector('.sidebar-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }
});

