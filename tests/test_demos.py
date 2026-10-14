"""
Flixora AI Sales Automation Agent — Demo Website Tests
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, PRD, DemoProject
from app.constants import PRDStatus, LeadStatus
from app.services.auth_service import create_admin_user
from app.services.demo_service import compile_demo_html, publish_demo_project


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
    return app.test_client()


def test_demo_requires_approved_prd(app):
    """Test that demo generation is rejected if PRD is not approved."""
    with app.app_context():
        lead = Lead(business_name="Green Cafe", business_category="restaurant")
        db.session.add(lead)
        db.session.commit()

        # Seed under review PRD
        prd = PRD(lead_id=lead.id, title="Cafe Sitemap", status=PRDStatus.UNDER_REVIEW)
        db.session.add(prd)
        db.session.commit()

        res = compile_demo_html(lead.id)
        assert res['success'] is False
        assert "approved PRD is required" in res['error']


def test_demo_compilation_success_flow(app):
    """Test generating demo landing page after PRD approval."""
    with app.app_context():
        lead = Lead(business_name="Green Cafe", business_category="restaurant", status=LeadStatus.RESEARCHED)
        db.session.add(lead)
        db.session.commit()

        # Seed approved PRD
        prd = PRD(
            lead_id=lead.id,
            title="Cafe Sitemap",
            status=PRDStatus.APPROVED,
            website_goal="Promote reservations",
            design_direction="Warm colors"
        )
        db.session.add(prd)
        db.session.commit()

        mock_html = "<html><body><h1>Welcome to Green Cafe</h1></body></html>"

        with patch('app.services.demo_service.llm_router.generate_text', return_value=mock_html):
            res = compile_demo_html(lead.id)
            assert res['success'] is True
            assert res['preview_url'] == f"/demos/preview/{lead.id}"

            # Verify file exists on disk
            base_upload = current_app_config_upload_folder(app)
            file_path = os.path.join(base_upload, 'demos', str(lead.id), 'index.html')
            assert os.path.exists(file_path)

            # Check DB entry
            demo = DemoProject.query.filter_by(lead_id=lead.id).first()
            assert demo is not None
            assert demo.url_valid is True
            
            # Lead status should transition
            assert lead.status == LeadStatus.CONTACTED

            # Cleanup file
            if os.path.exists(file_path):
                os.remove(file_path)
                os.rmdir(os.path.dirname(file_path))


def test_demo_publish_mock_flow(app):
    """Test publishing the demo project under test mode."""
    with app.app_context():
        lead = Lead(business_name="Green Cafe", business_category="restaurant")
        db.session.add(lead)
        db.session.commit()

        # Seed local file folders
        base_upload = current_app_config_upload_folder(app)
        demo_dir = os.path.join(base_upload, 'demos', str(lead.id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        with open(file_path, "w") as f:
            f.write("<html></html>")

        # Seed Demo record
        demo = DemoProject(
            lead_id=lead.id,
            demo_name="Green Cafe Demo",
            demo_url=f"/demos/preview/{lead.id}"
        )
        db.session.add(demo)
        db.session.commit()

        res = publish_demo_project(lead.id)
        assert res['success'] is True
        assert res['published_url'] == f"https://flixora.github.io/demo-{lead.id} [TEST_MODE]"

        db.session.refresh(demo)
        assert demo.demo_url == f"https://flixora.github.io/demo-{lead.id} [TEST_MODE]"
        assert demo.url_valid is True

        # Cleanup file
        if os.path.exists(file_path):
            os.remove(file_path)
            os.rmdir(demo_dir)


def current_app_config_upload_folder(app):
    with app.app_context():
        return app.config.get('UPLOAD_FOLDER', 'uploads')
