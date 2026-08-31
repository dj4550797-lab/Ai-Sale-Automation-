"""
Flixora AI Sales Automation Agent — Authentication Tests
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import User
from app.services.auth_service import create_admin_user


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        # Seed default admin user
        create_admin_user(
            username='testadmin',
            email='testadmin@flixora.com',
            password='password123',
            display_name='Test Admin'
        )
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_login_success(client):
    """Test successful login."""
    response = client.post('/login', data={
        'username': 'testadmin',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Dashboard' in response.data
    assert b'Test Admin' in response.data


def test_login_invalid_password(client):
    """Test login with incorrect password."""
    response = client.post('/login', data={
        'username': 'testadmin',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data


def test_login_invalid_username(client):
    """Test login with non-existent username."""
    response = client.post('/login', data={
        'username': 'nouser',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data


def test_logout(client):
    """Test logging out."""
    # Login first
    client.post('/login', data={
        'username': 'testadmin',
        'password': 'password123'
    })
    
    # Logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data
    assert b'You have been logged out' in response.data


def test_dashboard_login_required(client):
    """Test that dashboard requires login."""
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    # Should redirect to login page
    assert b'Login' in response.data
    assert b'Please log in to access this page' in response.data


def test_rate_limiting(client, app):
    """Test rate limiting on login endpoint."""
    app.config['DISABLE_RATE_LIMIT'] = False
    from app.security.rate_limit import rate_limiter
    
    # Reset limit first
    ip = '127.0.0.1'
    rate_limiter.reset(f'login:{ip}')
    
    # Trigger rate limit (limit is 5 attempts in window)
    for _ in range(5):
        client.post('/login', data={
            'username': 'testadmin',
            'password': 'wrongpassword'
        })
        
    # The 6th attempt should be rate limited
    response = client.post('/login', data={
        'username': 'testadmin',
        'password': 'wrongpassword'
    })
    
    # Reset config back to True
    app.config['DISABLE_RATE_LIMIT'] = True
    
    assert response.status_code == 429
    assert b'Too many login attempts' in response.data
    
    # Reset to clean up
    rate_limiter.reset(f'login:{ip}')
