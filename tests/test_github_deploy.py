"""
Flixora AI Sales Automation Agent — GitHub Deployment Tests
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import Lead, PRD, DemoProject, APICredential
from app.constants import PRDStatus, LeadStatus
from app.services.auth_service import create_admin_user
from app.services.demo_service import publish_demo_project


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


# Helper to mock Response
def mock_response(status_code, json_data=None, text_data=""):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    resp.text = text_data
    return resp


# ── GITHUB DEPLOYMENT TESTS ────────────────────────────────────────────

def test_github_auth_failure(app):
    """Test 20: GitHub authentication failure handles invalid tokens safely."""
    with app.app_context():
        app.config['TEST_MODE'] = False
        
        # Seed GitHub token
        from app.security.encryption import encrypt_value
        cred = APICredential(service_name='github', credential_type='api_key', encrypted_value=encrypt_value("bad-token"))
        db.session.add(cred)
        
        lead = Lead(business_name="Cafe", website_url="")
        db.session.add(lead)
        db.session.commit()

        # Seed local file
        demo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'demos', str(lead.id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        with open(file_path, "w") as f:
            f.write("<html></html>")

        demo = DemoProject(lead_id=lead.id, demo_name="Cafe Demo", demo_url="/demos/preview/1")
        db.session.add(demo)
        db.session.commit()

        # Mock auth failure response (401)
        with patch('app.services.demo_service.requests.get', return_value=mock_response(401, text_data="Bad Credentials")):
            res = publish_demo_project(lead.id)
            assert res['success'] is False
            assert "GitHub authentication failed" in res['error']

            db.session.refresh(demo)
            assert demo.url_valid is False
            assert "authentication failed" in demo.publish_error

        # Cleanup
        os.remove(file_path)
        os.rmdir(demo_dir)


def test_github_repo_creation_and_success_deploy(app):
    """Test 21, 23, 25, 27, 29: Complete successful live deploy (repo check/create, commit, Pages configure, accessibility verify)."""
    with app.app_context():
        app.config['TEST_MODE'] = False
        
        from app.security.encryption import encrypt_value
        cred = APICredential(service_name='github', credential_type='api_key', encrypted_value=encrypt_value("valid-token"))
        db.session.add(cred)
        
        lead = Lead(business_name="Cafe", website_url="")
        db.session.add(lead)
        db.session.commit()

        demo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'demos', str(lead.id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        with open(file_path, "w") as f:
            f.write("<html></html>")

        demo = DemoProject(lead_id=lead.id, demo_name="Cafe Demo", demo_url="/demos/preview/1")
        db.session.add(demo)
        db.session.commit()

        # Mock API calls:
        # 1. GET /user (auth check) -> status 200, user "testusername"
        # 2. GET /repos/testusername/flixora-demo-{id} (repo check) -> status 404 (repo doesn't exist)
        # 3. POST /user/repos (create repo) -> status 201
        # 4. GET /repos/.../contents/index.html (file check) -> status 404
        # 5. PUT /repos/.../contents/index.html (commit file) -> status 201
        # 6. GET /repos/.../pages (Pages check) -> status 404
        # 7. POST /repos/.../pages (enable Pages) -> status 201
        # 8. GET /repos/.../pages (verify pages configured) -> status 200
        # 9. GET https://testusername.github.io/flixora-demo-{id}/ (ping pages) -> status 200
        
        def mock_request_routing(url, *args, **kwargs):
            if "api.github.com/user" in url and "repos" not in url:
                return mock_response(200, json_data={"login": "testusername"})
            elif f"repos/testusername/flixora-demo-{lead.id}" in url:
                if "contents/index.html" in url:
                    return mock_response(404) # file not found
                elif "pages" in url:
                    return mock_response(404) # pages not enabled yet
                return mock_response(404) # repo not found
            elif "user/repos" in url:
                return mock_response(201)
            elif "testusername.github.io" in url:
                return mock_response(200) # reachable page!
            return mock_response(404)

        def mock_put_routing(url, *args, **kwargs):
            return mock_response(201)

        def mock_post_routing(url, *args, **kwargs):
            if "user/repos" in url:
                return mock_response(201)
            elif "pages" in url:
                return mock_response(201)
            return mock_response(404)

        with patch('app.services.demo_service.requests.get', side_effect=mock_request_routing) as mock_get, \
             patch('app.services.demo_service.requests.post', side_effect=mock_post_routing) as mock_post, \
             patch('app.services.demo_service.requests.put', side_effect=mock_put_routing) as mock_put:
             
            res = publish_demo_project(lead.id)
            assert res['success'] is True
            assert res['published_url'] == f"https://testusername.github.io/flixora-demo-{lead.id}/"
            
            db.session.refresh(demo)
            assert demo.url_valid is True
            assert demo.url_reachable is True
            assert demo.publish_error == ""

        # Cleanup
        os.remove(file_path)
        os.rmdir(demo_dir)


def test_github_repo_reuse_and_file_update(app):
    """Test 22 & 24: Reuses existing repository and updates index.html (sha provided)."""
    with app.app_context():
        app.config['TEST_MODE'] = False
        
        from app.security.encryption import encrypt_value
        cred = APICredential(service_name='github', credential_type='api_key', encrypted_value=encrypt_value("valid-token"))
        db.session.add(cred)
        
        lead = Lead(business_name="Cafe", website_url="")
        db.session.add(lead)
        db.session.commit()

        demo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'demos', str(lead.id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        with open(file_path, "w") as f:
            f.write("<html></html>")

        demo = DemoProject(lead_id=lead.id, demo_name="Cafe Demo", demo_url="/demos/preview/1")
        db.session.add(demo)
        db.session.commit()

        def mock_request_routing(url, *args, **kwargs):
            if "api.github.com/user" in url and "repos" not in url:
                return mock_response(200, json_data={"login": "testusername"})
            elif f"repos/testusername/flixora-demo-{lead.id}" in url:
                if "contents/index.html" in url:
                    return mock_response(200, json_data={"sha": "existingfile-sha123"})
                elif "pages" in url:
                    return mock_response(200) # pages already enabled
                return mock_response(200) # repo already exists!
            elif "testusername.github.io" in url:
                return mock_response(200)
            return mock_response(404)

        with patch('app.services.demo_service.requests.get', side_effect=mock_request_routing), \
             patch('app.services.demo_service.requests.put', return_value=mock_response(200)) as mock_put:
             
            res = publish_demo_project(lead.id)
            assert res['success'] is True
            
            # Verify SHA was sent during commit
            args, kwargs = mock_put.call_args
            payload = kwargs.get('json', {})
            assert payload.get('sha') == "existingfile-sha123"

        # Cleanup
        os.remove(file_path)
        os.rmdir(demo_dir)


def test_github_deploy_failure_http_unreachable(app):
    """Test 26, 28, 31: If Pages is not accessible, live mode rejects fabricated URLs and fails."""
    with app.app_context():
        app.config['TEST_MODE'] = False
        
        from app.security.encryption import encrypt_value
        cred = APICredential(service_name='github', credential_type='api_key', encrypted_value=encrypt_value("valid-token"))
        db.session.add(cred)
        
        lead = Lead(business_name="Cafe", website_url="")
        db.session.add(lead)
        db.session.commit()

        demo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'demos', str(lead.id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        with open(file_path, "w") as f:
            f.write("<html></html>")

        demo = DemoProject(lead_id=lead.id, demo_name="Cafe Demo", demo_url="/demos/preview/1")
        db.session.add(demo)
        db.session.commit()

        def mock_request_routing(url, *args, **kwargs):
            if "api.github.com/user" in url and "repos" not in url:
                return mock_response(200, json_data={"login": "testusername"})
            elif f"repos/testusername/flixora-demo-{lead.id}" in url:
                if "contents/index.html" in url:
                    return mock_response(200, json_data={"sha": "existingfile-sha123"})
                elif "pages" in url:
                    return mock_response(200)
                return mock_response(200)
            elif "testusername.github.io" in url:
                return mock_response(404) # Site returns 404 (Pages build pending / unreachable)
            return mock_response(404)

        with patch('app.services.demo_service.requests.get', side_effect=mock_request_routing), \
             patch('app.services.demo_service.requests.put', return_value=mock_response(200)), \
             patch('time.sleep', return_value=None): # skip sleep to run fast
             
            res = publish_demo_project(lead.id)
            assert res['success'] is False
            assert "is not HTTP reachable" in res['error']
            
            db.session.refresh(demo)
            assert demo.url_valid is False
            assert demo.url_reachable is False
            assert "not HTTP reachable" in demo.publish_error

        # Cleanup
        os.remove(file_path)
        os.rmdir(demo_dir)


def test_github_test_mode_simulation(app):
    """Test 30: Under TEST_MODE=True, returns clean simulated URL with developer warnings."""
    with app.app_context():
        app.config['TEST_MODE'] = True
        
        lead = Lead(business_name="Cafe", website_url="")
        db.session.add(lead)
        db.session.commit()

        demo_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'demos', str(lead.id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        with open(file_path, "w") as f:
            f.write("<html></html>")

        demo = DemoProject(lead_id=lead.id, demo_name="Cafe Demo", demo_url="/demos/preview/1")
        db.session.add(demo)
        db.session.commit()

        res = publish_demo_project(lead.id)
        assert res['success'] is True
        assert "flixora.github.io" in res['published_url']
        assert "[TEST_MODE]" in res['published_url']

        db.session.refresh(demo)
        assert demo.url_valid is True
        assert demo.url_reachable is True
        assert demo.publish_error == ""

        # Cleanup
        os.remove(file_path)
        os.rmdir(demo_dir)
