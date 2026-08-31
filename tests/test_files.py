"""
Flixora AI Sales Automation Agent — File Management & Vision Tests
"""
import io
import os
import pytest
from unittest.mock import patch
from werkzeug.datastructures import FileStorage
from app import create_app
from app.extensions import db
from app.models import UploadedFile, User
from app.services.auth_service import create_admin_user
from app.services.file_service import save_uploaded_file, rename_uploaded_file, delete_uploaded_file
from app.services.vision_service import analyze_business_image


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


def test_file_upload_and_delete_service(app):
    """Test saving uploaded files and cleaning them up from disk and DB."""
    with app.app_context():
        # Create a mock file
        mock_file_data = io.BytesIO(b"file contents")
        mock_file = FileStorage(stream=mock_file_data, filename="salon_logo.png", content_type="image/png")

        res = save_uploaded_file(mock_file, file_type='logo', lead_id=None, user_id=None)
        assert res['success'] is True
        file_id = res['file_id']

        # Query and verify
        db_file = UploadedFile.query.get(file_id)
        assert db_file is not None
        assert db_file.original_filename == "salon_logo.png"
        assert db_file.file_type == 'logo'
        
        # Verify file exists on disk
        disk_path = os.path.abspath(os.path.join(app.root_path, db_file.file_path))
        assert os.path.exists(disk_path)

        # Test renaming
        res_rename = rename_uploaded_file(file_id, "new_salon_logo.png")
        assert res_rename['success'] is True
        assert res_rename['new_name'] == "new_salon_logo.png"

        # Test deletion
        res_del = delete_uploaded_file(file_id)
        assert res_del['success'] is True
        assert not os.path.exists(disk_path)
        assert UploadedFile.query.get(file_id) is None


def test_vision_image_analysis_mock(app):
    """Test visual analysis of logo assets in mock mode."""
    with app.app_context():
        # Register a mock file in DB
        file_rec = UploadedFile(
            filename="logo_123.png",
            original_filename="hair_salon_logo.png",
            file_path="uploads/logos/logo_123.png",
            file_type="logo",
            mime_type="image/png"
        )
        db.session.add(file_rec)
        db.session.commit()
        file_id = file_rec.id

        res = analyze_business_image(file_id)
        assert res['success'] is True
        assert "#D4AF37" in res['data']['dominant_colors']  # Gold theme for salons
        assert "beauty salon" in res['data']['inferred_industry']
