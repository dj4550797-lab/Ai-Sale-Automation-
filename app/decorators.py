"""
Flixora AI Sales Automation Agent — Custom Decorators
"""
from functools import wraps
from flask import jsonify, redirect, url_for, flash
from flask_login import current_user


def admin_required(f):
    """Ensure the current user is authenticated and is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_active:
            flash('Your account is disabled.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def api_response(f):
    """Wrap route return value in a standard JSON envelope."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                data, status_code = result
            else:
                data = result
                status_code = 200
            return jsonify({'success': True, 'data': data}), status_code
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except PermissionError as e:
            return jsonify({'success': False, 'error': str(e)}), 403
        except Exception as e:
            return jsonify({'success': False, 'error': 'An unexpected error occurred.'}), 500
    return decorated_function
