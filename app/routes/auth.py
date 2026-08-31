"""
Flixora AI Sales Automation Agent — Auth Routes

Login, logout, session management (§10).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.services.auth_service import authenticate_user
from app.security.rate_limit import rate_limiter

auth_bp = Blueprint('auth', __name__, url_prefix='')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        # Rate limiting (§10)
        ip = request.remote_addr
        from flask import current_app
        if not current_app.config.get('DISABLE_RATE_LIMIT') and rate_limiter.is_rate_limited(f'login:{ip}', max_attempts=5, window_seconds=300):
            flash('Too many login attempts. Please try again later.', 'error')
            return render_template('auth/login.html'), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')

        user = authenticate_user(username, password)
        if user:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid credentials. Please check your username and password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout and redirect to login."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/admin')
@login_required
def admin_redirect():
    """Redirect /admin to /dashboard if logged in."""
    return redirect(url_for('dashboard.index'))
