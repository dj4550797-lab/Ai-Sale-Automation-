/**
 * FLIXORA — Settings JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    initPasswordToggle();
});

// ── Password Visibility Toggle ──────────────────────────────
function initPasswordToggle() {
    document.querySelectorAll('.password-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = btn.previousElementSibling;
            if (input && input.type === 'password') {
                input.type = 'text';
                btn.querySelector('.material-symbols-outlined').textContent = 'visibility_off';
            } else if (input) {
                input.type = 'password';
                btn.querySelector('.material-symbols-outlined').textContent = 'visibility';
            }
        });
    });
}

// ── Test Connection ─────────────────────────────────────────
async function testConnection(credentialId, btn) {
    const origText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Testing...';
    btn.disabled = true;

    try {
        const result = await apiFetch(`/api/credentials/${credentialId}/test`, { method: 'POST' });
        if (result.success) {
            showToast('Connection successful!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast(`Connection failed: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast('Connection failed.', 'error');
    } finally {
        btn.innerHTML = origText;
        btn.disabled = false;
    }
}
