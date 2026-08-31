"""
Flixora AI Sales Automation Agent — Automation Scheduler Routes
"""
import os
import threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required
from app.extensions import db, csrf
from app.models import AutomationJob, AutomationRun, Lead, Setting
from app.constants import AutomationJobStatus
from app.services.lead_service import run_lead_discovery
from app.utils.logger import get_logger

logger = get_logger('automation_routes')
automation_bp = Blueprint('automation', __name__, url_prefix='/automation')


def check_discovery_locked():
    """Look for any run in 'running' state that started in the last 15 minutes."""
    active_run = AutomationRun.query.filter_by(status='running').order_by(AutomationRun.started_at.desc()).first()
    if active_run:
        started_at = active_run.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - started_at).total_seconds() < 900:  # 15 minutes lock time
            return True
    return False


def run_lead_discovery_background(app, location, category, daily_target, job_id, run_id):
    """Run lead discovery in a background thread to prevent HTTP timeouts."""
    with app.app_context():
        run = AutomationRun.query.get(run_id)
        job = AutomationJob.query.get(job_id)
        if not run or not job:
            return
            
        try:
            logger.info(f"Background automation started for job: {job.name}")
            # Run lead discovery
            res = run_lead_discovery(location=location, category=category, daily_target=daily_target)
            
            # Update run record
            run.status = 'completed' if res.get('success') else 'failed'
            run.completed_at = datetime.now(timezone.utc)
            run.items_processed = res.get('processed_count', 0)
            run.items_succeeded = res.get('saved_count', 0)
            run.items_failed = res.get('duplicate_count', 0)
            run.log_output = f"Discovery run completed.\nDetails: {res}"
            
            # Update job record
            job.run_count = (job.run_count or 0) + 1
            if res.get('success'):
                job.success_count = (job.success_count or 0) + 1
                job.last_success_at = datetime.now(timezone.utc)
                job.status = AutomationJobStatus.ACTIVE
            else:
                job.failure_count = (job.failure_count or 0) + 1
                job.last_failure_at = datetime.now(timezone.utc)
                job.last_error = res.get('error', 'Unknown error')
                job.status = AutomationJobStatus.FAILED
                
            job.last_run_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info(f"Background automation run {run_id} completed successfully.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in background automation run {run_id}: {str(e)}")
            try:
                run.status = 'failed'
                run.completed_at = datetime.now(timezone.utc)
                run.error_message = str(e)
                run.log_output = f"Exception occurred: {str(e)}"
                
                job.failure_count = (job.failure_count or 0) + 1
                job.last_failure_at = datetime.now(timezone.utc)
                job.last_error = str(e)
                job.status = AutomationJobStatus.FAILED
                
                db.session.commit()
            except Exception as commit_err:
                logger.error(f"Could not save failure log: {commit_err}")


def start_automation_run(app, job):
    """Initialize a thread-safe automation run."""
    # Check concurrency lock
    if check_discovery_locked():
        return {"success": False, "error": "Automation job is currently running."}
        
    # Get config settings
    limit_setting = Setting.query.filter_by(category='lead_discovery', key='daily_lead_target').first()
    category_setting = Setting.query.filter_by(category='lead_discovery', key='discovery_category').first()
    location_setting = Setting.query.filter_by(category='lead_discovery', key='discovery_location').first()
    
    daily_limit = int(limit_setting.value) if limit_setting else 20
    category = category_setting.value if category_setting else 'restaurant'
    location = location_setting.value if location_setting else 'Delhi'
    
    # Check remaining capacity
    tz_setting = Setting.query.filter_by(category='agent', key='timezone').first()
    tz_name = tz_setting.value if tz_setting else 'Asia/Kolkata'
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo('Asia/Kolkata')
        
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    
    leads_today = Lead.query.filter(Lead.created_at >= start_utc).count()
    remaining_capacity = max(0, daily_limit - leads_today)
    
    if remaining_capacity <= 0:
        return {"success": False, "error": f"Daily limit reached ({leads_today}/{daily_limit})."}
        
    # Create the run record
    run = AutomationRun(
        job_id=job.id,
        status='running',
        started_at=datetime.now(timezone.utc),
        log_output=f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Started lead discovery run for {category} in {location}."
    )
    db.session.add(run)
    db.session.commit()
    
    # Start execution (synchronously if in TESTING mode to avoid SQLite threading issues)
    if app.config.get('TESTING'):
        run_lead_discovery_background(app, location, category, remaining_capacity, job.id, run.id)
    else:
        thread = threading.Thread(
            target=run_lead_discovery_background,
            args=(app, location, category, remaining_capacity, job.id, run.id)
        )
        thread.start()
    
    return {"success": True, "message": "Automation run triggered successfully.", "run_id": run.id}


@automation_bp.route('')
@login_required
def index():
    """Render the Automation Scheduler dashboard."""
    # Ensure default job exists
    job = AutomationJob.query.filter_by(job_type='lead_discovery').first()
    if not job:
        job = AutomationJob(
            name="Google Places Discovery",
            description="Scans and saves new leads daily.",
            job_type="lead_discovery",
            status=AutomationJobStatus.ACTIVE,
            is_enabled=True
        )
        db.session.add(job)
        db.session.commit()

    jobs = AutomationJob.query.order_by(AutomationJob.name.asc()).all()
    runs = AutomationRun.query.order_by(AutomationRun.started_at.desc()).limit(20).all()
    
    # Load settings
    global_enabled_setting = Setting.query.filter_by(category='automation', key='global_enabled').first()
    daily_limit_setting = Setting.query.filter_by(category='lead_discovery', key='daily_lead_target').first()
    category_setting = Setting.query.filter_by(category='lead_discovery', key='discovery_category').first()
    location_setting = Setting.query.filter_by(category='lead_discovery', key='discovery_location').first()
    tz_setting = Setting.query.filter_by(category='agent', key='timezone').first()
    schedule_setting = Setting.query.filter_by(category='lead_discovery', key='discovery_schedule').first()
    
    global_enabled = (global_enabled_setting.value.lower() == 'true') if global_enabled_setting else True
    daily_limit = int(daily_limit_setting.value) if daily_limit_setting else 20
    category = category_setting.value if category_setting else 'restaurant'
    location = location_setting.value if location_setting else 'Delhi'
    tz_name = tz_setting.value if tz_setting else 'Asia/Kolkata'
    schedule = schedule_setting.value if schedule_setting else 'Daily at 08:00 PM'

    # Timezone aware counts
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo('Asia/Kolkata')
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    leads_today = Lead.query.filter(Lead.created_at >= start_utc).count()
    remaining_capacity = max(0, daily_limit - leads_today)

    # Pipeline counts & statistics
    from app.models import WebsiteAnalysis, PRD, APICredential
    pipeline_counts = {
        'discovered': Lead.query.filter(Lead.status.in_(['new', 'qualified'])).count(),
        'analyzed': Lead.query.join(WebsiteAnalysis).filter(WebsiteAnalysis.status == 'completed').count(),
        'prd_ready': Lead.query.join(PRD).filter(PRD.status == 'ready').count(),
        'waiting_demo': Lead.query.filter(Lead.status == 'Waiting for Admin Demo').count(),
        'outreach': Lead.query.filter(Lead.status == 'contacted').count(),
        'conversation': Lead.query.filter(Lead.status == 'replied').count(),
        'hot_lead': Lead.query.filter(Lead.status.in_(['interested', 'negotiation'])).count()
    }
    
    total_runs = len(runs)
    success_runs = sum(1 for r in runs if r.status == 'completed')
    success_rate = int((success_runs / total_runs) * 100) if total_runs > 0 else 100
    
    maps_cred = APICredential.query.filter_by(service_name='google_maps').first()
    if not maps_cred:
        api_status = 'Not Configured'
    elif maps_cred.is_valid:
        api_status = 'Connected'
    else:
        api_status = 'Issues'

    return render_template(
        'automation/index.html',
        jobs=jobs,
        runs=runs,
        global_enabled=global_enabled,
        daily_limit=daily_limit,
        category=category,
        location=location,
        timezone=tz_name,
        leads_today=leads_today,
        remaining_capacity=remaining_capacity,
        pipeline_counts=pipeline_counts,
        success_rate=success_rate,
        api_status=api_status,
        schedule=schedule
    )


@automation_bp.route('/toggle-global', methods=['POST'])
@login_required
def toggle_global():
    """Toggle the global automation setting."""
    setting = Setting.query.filter_by(category='automation', key='global_enabled').first()
    if setting:
        current_val = setting.value.lower() == 'true'
        setting.value = 'false' if current_val else 'true'
    else:
        setting = Setting(category='automation', key='global_enabled', value='true')
        db.session.add(setting)
    db.session.commit()
    return jsonify({
        "success": True,
        "global_enabled": setting.value.lower() == 'true'
    })


@automation_bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_job(id):
    """Toggle enabled status of an automation job."""
    job = AutomationJob.query.get_or_404(id)
    job.is_enabled = not job.is_enabled
    job.status = AutomationJobStatus.ACTIVE if job.is_enabled else AutomationJobStatus.DISABLED
    db.session.commit()
    
    status_str = 'enabled' if job.is_enabled else 'disabled'
    return jsonify({
        "success": True,
        "message": f"Job '{job.name}' is now {status_str}.",
        "is_enabled": job.is_enabled
    })


@automation_bp.route('/run/<int:id>', methods=['POST'])
@login_required
def run_job(id):
    """Manually trigger execution of an automation job."""
    job = AutomationJob.query.get_or_404(id)
    app = current_app._get_current_object()
    res = start_automation_run(app, job)
    if res.get('success'):
        return jsonify(res)
    else:
        return jsonify(res), 400


@automation_bp.route('/settings/save', methods=['POST'])
@login_required
def save_settings():
    """Save lead discovery and automation configurations."""
    global_enabled = request.form.get('global_enabled') == 'on'
    daily_limit = request.form.get('daily_limit', '20')
    category = request.form.get('category', 'restaurant')
    location = request.form.get('location', 'Delhi')
    timezone_val = request.form.get('timezone', 'Asia/Kolkata')
    schedule = request.form.get('schedule', 'Daily at 08:00 PM')
    
    def update_setting(cat, key, val):
        s = Setting.query.filter_by(category=cat, key=key).first()
        if s:
            s.value = val
        else:
            s = Setting(category=cat, key=key, value=val)
            db.session.add(s)
            
    update_setting('automation', 'global_enabled', 'true' if global_enabled else 'false')
    update_setting('lead_discovery', 'daily_lead_target', daily_limit)
    update_setting('lead_discovery', 'discovery_category', category)
    update_setting('lead_discovery', 'discovery_location', location)
    update_setting('agent', 'timezone', timezone_val)
    update_setting('lead_discovery', 'discovery_schedule', schedule)
    
    db.session.commit()
    flash("Automation settings updated successfully.", "success")
    return redirect(url_for('automation.index'))


@automation_bp.route('/trigger-cron', methods=['POST'])
@csrf.exempt
def trigger_cron():
    """Exempt from CSRF for external cron scheduler calls."""
    cron_secret = os.environ.get('CRON_SECRET', 'default-cron-secret')
    request_secret = request.headers.get('X-Cron-Secret') or request.args.get('secret')
    
    if request_secret != cron_secret:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    # Check if automation global enabled is active
    global_enabled_setting = Setting.query.filter_by(category='automation', key='global_enabled').first()
    global_enabled = (global_enabled_setting.value.lower() == 'true') if global_enabled_setting else True
    if not global_enabled:
        return jsonify({"success": False, "error": "Automation is globally disabled."}), 400

    job = AutomationJob.query.filter_by(job_type='lead_discovery').first()
    if not job:
        job = AutomationJob(
            name="Google Places Discovery",
            description="Scans and saves new leads daily.",
            job_type="lead_discovery",
            status=AutomationJobStatus.ACTIVE,
            is_enabled=True
        )
        db.session.add(job)
        db.session.commit()

    app = current_app._get_current_object()
    res = start_automation_run(app, job)
    if res.get('success'):
        return jsonify(res), 202
    else:
        return jsonify(res), 400
