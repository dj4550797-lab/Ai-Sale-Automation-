"""
Flixora AI Sales Automation Agent — System, Automation, and Analytics Metrics Tests
"""
import pytest
from app import create_app
from app.extensions import db
from app.models import AutomationJob, ActivityLog, CorrectionRule
from app.services.auth_service import create_admin_user
from app.constants import AutomationJobStatus


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        create_admin_user(username='testadmin', email='test@flixora.com', password='password')
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    client = app.test_client()
    # Reset rate limiting to prevent test suite interference
    from app.security.rate_limit import rate_limiter
    rate_limiter.reset('login:127.0.0.1')
    
    # Log in
    client.post('/login', data={
        'username': 'testadmin',
        'password': 'password'
    }, follow_redirects=True)
    return client


def test_analytics_dashboard_load(app, client):
    """Test Analytics page loads successfully with zero states and structured tables."""
    with app.app_context():
        # Load page
        response = client.get('/analytics')
        assert response.status_code == 200
        assert b"System Performance & Conversion Reports" in response.data
        assert b"Pipeline Funnel" in response.data


def test_automation_scheduler_toggle_and_run(app, client):
    """Test Automation job listing, enabling/disabling toggles, and manual run triggers."""
    with app.app_context():
        # Create a job
        job = AutomationJob(
            name="Scrape Google Maps Salon",
            job_type="lead_discovery",
            cron_expression="0 0 * * *",
            is_enabled=False,
            status=AutomationJobStatus.DISABLED
        )
        db.session.add(job)
        db.session.commit()
        job_id = job.id

        # List jobs
        res_list = client.get('/automation')
        assert res_list.status_code == 200
        assert b"Scrape Google Maps Salon" in res_list.data

        # Toggle job
        res_toggle = client.post(f'/automation/toggle/{job_id}', json={})
        assert res_toggle.status_code == 200
        assert res_toggle.json['is_enabled'] is True

        # Run job manually
        res_run = client.post(f'/automation/run/{job_id}', json={})
        assert res_run.status_code == 200
        assert res_run.json['success'] is True


def test_activity_logs_filtering(app, client):
    """Test Activity log listing, search filters, and actor-type queries."""
    with app.app_context():
        # Create activity logs
        log1 = ActivityLog(
            action="login",
            actor_type="admin",
            description="User testadmin logged in successfully.",
            result="success"
        )
        log2 = ActivityLog(
            action="api_error",
            actor_type="system",
            description="LLM provider OpenRouter timed out.",
            result="error"
        )
        db.session.add(log1)
        db.session.add(log2)
        db.session.commit()

        # View all logs
        response = client.get('/logs')
        assert response.status_code == 200
        assert b"User testadmin logged in successfully" in response.data
        assert b"LLM provider OpenRouter timed out" in response.data

        # Filter by actor_type
        res_filter = client.get('/logs?actor_type=system')
        assert res_filter.status_code == 200
        assert b"LLM provider OpenRouter timed out" in res_filter.data
        assert b"User testadmin logged in" not in res_filter.data


def test_performance_correction_rules(app, client):
    """Test Performance page and manual submission/toggling of AI correction rules."""
    with app.app_context():
        # Load page
        res_view = client.get('/performance')
        assert res_view.status_code == 200

        # Add correction rule
        res_add = client.post('/performance/rules/add', data={
            'error_type': 'Hallucination',
            'error_description': 'AI claimed we do custom logo designs.',
            'cause': 'Agent rules were not specific enough.',
            'correction': 'Do not offer graphics designs.'
        }, follow_redirects=True)
        assert res_add.status_code == 200
        assert b"Correction rule added successfully" in res_add.data

        # Verify added in database
        rule = CorrectionRule.query.filter_by(error_type='Hallucination').first()
        assert rule is not None
        assert rule.correction == 'Do not offer graphics designs.'
        assert rule.is_active is True

        # Toggle rule
        res_toggle = client.post(f'/performance/rules/toggle/{rule.id}', json={})
        assert res_toggle.status_code == 200
        assert res_toggle.json['is_active'] is False
