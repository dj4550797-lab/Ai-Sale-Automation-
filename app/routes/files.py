"""
Flixora AI Sales Automation Agent — File Explorer Routes
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import UploadedFile, Lead
from app.services.file_service import (
    save_uploaded_file, delete_uploaded_file, rename_uploaded_file
)
from app.services.vision_service import analyze_business_image
from app.security.validation import sanitize_string

files_bp = Blueprint('files', __name__, url_prefix='/files')


@files_bp.route('')
@login_required
def index():
    """Render the File explorer page."""
    search_query = sanitize_string(request.args.get('search', ''))
    
    query = UploadedFile.query
    if search_query:
        query = query.filter(UploadedFile.original_filename.ilike(f"%{search_query}%"))
        
    files = query.order_by(UploadedFile.created_at.desc()).all()
    
    # Categorize
    logos = [f for f in files if f.file_type == 'logo']
    images = [f for f in files if f.file_type == 'image']
    documents = [f for f in files if f.file_type not in ['logo', 'image']]
    
    leads = Lead.query.order_by(Lead.business_name.asc()).all()

    return render_template('files/index.html',
                           logos=logos,
                           images=images,
                           documents=documents,
                           leads=leads)


@files_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """Upload a file to the system."""
    file_storage = request.files.get('file')
    file_type = sanitize_string(request.form.get('file_type', 'document'))
    lead_id = request.form.get('lead_id')
    
    # Optional conversion
    lead_id_int = int(lead_id) if lead_id and lead_id.isdigit() else None

    if not file_storage:
        flash("No file was uploaded.", "error")
        return redirect(url_for('files.index'))

    res = save_uploaded_file(
        file_storage=file_storage,
        file_type=file_type,
        lead_id=lead_id_int,
        user_id=current_user.id
    )
    
    if res.get('success'):
        flash(f"File '{res.get('filename')}' uploaded successfully.", "success")
    else:
        flash(f"Upload failed: {res.get('error')}", "error")

    return redirect(url_for('files.index'))


@files_bp.route('/rename/<int:id>', methods=['POST'])
@login_required
def rename(id):
    """Rename file display name metadata."""
    new_name = sanitize_string(request.form.get('new_name', ''))
    
    res = rename_uploaded_file(id, new_name)
    if res.get('success'):
        flash(f"File renamed to '{res.get('new_name')}' successfully.", "success")
    else:
        flash(f"Rename failed: {res.get('error')}", "error")
        
    return redirect(url_for('files.index'))


@files_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a file from disk and database."""
    res = delete_uploaded_file(id)
    if res.get('success'):
        flash("File deleted successfully.", "success")
    else:
        flash(f"Delete failed: {res.get('error')}", "error")
        
    return redirect(url_for('files.index'))


@files_bp.route('/analyze/<int:id>', methods=['POST'])
@login_required
def analyze(id):
    """Trigger image vision analysis using LLM."""
    try:
        res = analyze_business_image(id)
        if res.get('success'):
            return jsonify({
                "success": True,
                "data": res.get("data"),
                "message": "Vision audit completed successfully."
            })
        else:
            return jsonify({
                "success": False,
                "error": res.get("error")
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@files_bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Download a file from uploads folder."""
    uploaded_file = UploadedFile.query.get_or_404(file_id)
    import os
    from flask import current_app, send_from_directory
    abs_path = os.path.abspath(os.path.join(current_app.root_path, uploaded_file.file_path))
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=uploaded_file.original_filename)
