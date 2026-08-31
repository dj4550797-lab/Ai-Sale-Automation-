"""
Flixora AI Sales Automation Agent — File Service
"""
import os
from werkzeug.utils import secure_filename
from flask import current_app
from app.extensions import db
from app.models import UploadedFile
from app.utils.logger import get_logger

logger = get_logger('services')


def allowed_file(filename, file_type):
    """Check if the file extension is allowed."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if file_type == 'image' or file_type == 'logo':
        return ext in current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', set())
    return ext in current_app.config.get('ALLOWED_DOC_EXTENSIONS', set())


def save_uploaded_file(file_storage, file_type='document', lead_id=None, prd_id=None, user_id=None):
    """
    Save an uploaded file to disk and record metadata in the database.
    """
    if not file_storage or file_storage.filename == '':
        return {"success": False, "error": "No file selected."}

    original_filename = file_storage.filename
    if not allowed_file(original_filename, file_type):
        return {"success": False, "error": f"File extension not allowed for type '{file_type}'."}

    # Secure the filename
    safe_name = secure_filename(original_filename)
    # Append timestamp/random prefix to avoid name clashes on disk
    import uuid
    disk_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"

    # Determine save directory
    base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    # Save folder categories
    subfolder = 'documents'
    if file_type == 'logo':
        subfolder = 'logos'
    elif file_type == 'image':
        subfolder = 'images'
        
    save_dir = os.path.join(base_upload, subfolder)
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, disk_name)

    try:
        file_storage.save(file_path)
        
        # Calculate file size
        file_size = os.path.getsize(file_path)
        
        # Create metadata entry
        uploaded_file = UploadedFile(
            filename=disk_name,
            original_filename=original_filename,
            file_path=os.path.relpath(file_path, start=current_app.root_path),
            file_type=file_type,
            mime_type=file_storage.mimetype or '',
            file_size=file_size,
            lead_id=lead_id,
            prd_id=prd_id,
            uploaded_by=user_id
        )
        db.session.add(uploaded_file)
        db.session.commit()
        
        logger.info(f"File uploaded successfully: {original_filename} (stored as {disk_name})")
        return {"success": True, "file_id": uploaded_file.id, "filename": original_filename}
    except Exception as e:
        logger.error(f"Error saving uploaded file {original_filename}: {e}")
        # Clean up disk file if saved
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"success": False, "error": str(e)}


def delete_uploaded_file(file_id):
    """
    Delete an uploaded file from disk and metadata registry.
    """
    try:
        uploaded_file = UploadedFile.query.get(file_id)
        if not uploaded_file:
            return {"success": False, "error": f"File with ID {file_id} not found."}

        # Resolve path
        path = os.path.abspath(os.path.join(current_app.root_path, uploaded_file.file_path))
        
        # Delete from disk
        if os.path.exists(path):
            os.remove(path)
            
        filename = uploaded_file.original_filename
        db.session.delete(uploaded_file)
        db.session.commit()
        
        logger.info(f"File deleted: {filename} (ID: {file_id})")
        return {"success": True}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting file {file_id}: {e}")
        return {"success": False, "error": str(e)}


def rename_uploaded_file(file_id, new_name):
    """
    Rename the file's user-facing display name (original_filename metadata).
    """
    if not new_name:
        return {"success": False, "error": "New filename cannot be empty."}
        
    try:
        uploaded_file = UploadedFile.query.get(file_id)
        if not uploaded_file:
            return {"success": False, "error": f"File with ID {file_id} not found."}
            
        old_name = uploaded_file.original_filename
        
        # Ensure extension stays correct
        old_ext = old_name.rsplit('.', 1)[1] if '.' in old_name else ''
        new_ext = new_name.rsplit('.', 1)[1] if '.' in new_name else ''
        
        if old_ext and old_ext.lower() != new_ext.lower():
            # Append correct original extension
            new_name = f"{new_name.rsplit('.', 1)[0]}.{old_ext}"
            
        uploaded_file.original_filename = new_name
        db.session.commit()
        
        logger.info(f"File renamed from '{old_name}' to '{new_name}'")
        return {"success": True, "new_name": new_name}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error renaming file {file_id}: {e}")
        return {"success": False, "error": str(e)}


def save_generated_file(file_content, original_filename, file_type='document', lead_id=None, prd_id=None, user_id=None):
    """
    Save dynamically generated text/content to disk and record metadata in DB.
    """
    safe_name = secure_filename(original_filename)
    import uuid
    disk_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"

    base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    subfolder = 'documents'
    if file_type == 'logo':
        subfolder = 'logos'
    elif file_type == 'image':
        subfolder = 'images'
        
    save_dir = os.path.join(base_upload, subfolder)
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, disk_name)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        file_size = os.path.getsize(file_path)
        
        uploaded_file = UploadedFile(
            filename=disk_name,
            original_filename=original_filename,
            file_path=os.path.relpath(file_path, start=current_app.root_path),
            file_type=file_type,
            mime_type='text/plain',
            file_size=file_size,
            lead_id=lead_id,
            prd_id=prd_id,
            uploaded_by=user_id
        )
        db.session.add(uploaded_file)
        db.session.commit()
        
        logger.info(f"Generated file saved: {original_filename} (as {disk_name})")
        return {"success": True, "file_id": uploaded_file.id, "filename": original_filename, "file_path": uploaded_file.file_path}
    except Exception as e:
        logger.error(f"Error saving generated file {original_filename}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"success": False, "error": str(e)}
