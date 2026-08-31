"""
Flixora AI Sales Automation Agent — PRD Service

Orchestrates PRD generation, revisions, version history, and approval flows.
"""
from datetime import datetime, timezone
import json
from pydantic import BaseModel, Field
from typing import Optional

from app.extensions import db
from app.models import Lead, WebsiteAnalysis, PRD, PRDVersion
from app.constants import PRDStatus, LeadStatus
from app.ai.llm_router import llm_router
from app.services.analysis_service import analyze_lead_website
from app.utils.logger import get_logger

logger = get_logger('services')


class PRDSchema(BaseModel):
    """Pydantic model schema for structured PRD output from LLM."""
    title: str = Field(..., description="A professional title for this PRD document")
    business_overview: str = Field(..., description="Overview of the business, its history, values and market position")
    business_analysis: str = Field(..., description="Factual analysis of the business strengths, weaknesses and online gaps")
    website_goal: str = Field(..., description="Primary objectives of the new/improved website (e.g. increase leads, show portfolios)")
    target_audience: str = Field(..., description="Definition of target personas, demographics and customer needs")
    design_direction: str = Field(..., description="Visual styling guidelines, branding colors, typography and mood")
    site_structure: str = Field(..., description="Suggested sitemap hierarchy, page names and section layouts")
    functional_requirements: str = Field(..., description="Detailed feature requirements (e.g. online booking forms, galleries, maps)")
    content_requirements: str = Field(..., description="Details on what copy, images, and brand resources are needed")
    cta_strategy: str = Field(..., description="Placement strategy for primary call-to-actions to maximize conversion")
    technical_requirements: str = Field(..., description="Technical hosting, domain setup, analytics, security and SEO requirements")


def generate_lead_prd(lead_id, force=False):
    """
    Generate a new PRD or update an existing draft for a lead.
    Automatically determines whether it should be a 'New Website PRD' or an 'Improvement PRD'.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": f"Lead with ID {lead_id} not found."}

    # 1. Retrieve or run Website Analysis
    analysis = WebsiteAnalysis.query.filter_by(lead_id=lead_id).first()
    if not analysis or analysis.status != 'completed':
        logger.info(f"Analysis missing or incomplete for lead {lead_id}. Running analysis first...")
        res = analyze_lead_website(lead_id)
        if not res.get("success"):
            return {"success": False, "error": f"Failed to run website analysis: {res.get('error')}"}
        analysis = WebsiteAnalysis.query.filter_by(lead_id=lead_id).first()

    # 2. Check if existing website is adequate (§988-996)
    if not force and analysis.website_exists and not analysis.improvement_needed:
        logger.info(f"Redesign not required. Website for lead {lead_id} is marked as adequate.")
        return {
            "success": False,
            "error": "The existing website is adequate. No PRD generation required.",
            "code": "adequate_website"
        }

    # 3. Formulate Prompt based on site presence (New vs Improvement)
    is_improvement = bool(analysis.website_exists)
    
    if is_improvement:
        context_prompt = f"""
        Generate an IMPROVEMENT PRD for {lead.business_name} (Category: {lead.business_category}).
        They have an existing website at {lead.website_url} with an overall audit score of {analysis.overall_score}/100.
        Audit Verdict: {analysis.verdict}
        Improvement Reason: {analysis.improvement_reason}
        
        Observed facts from current site:
        {json.dumps(analysis.observed_facts)}
        
        AI recommendations to address:
        {json.dumps(analysis.ai_recommendations)}
        
        Incorporate solutions in the PRD addressing their current design weaknesses (Visuals, CTAs, Mobile layout, performance).
        """
    else:
        context_prompt = f"""
        Generate a NEW WEBSITE PRD for {lead.business_name} (Category: {lead.business_category}) located in {lead.address or 'India'}.
        This business has NO existing website footprint.
        We need to build a brand new web presence from scratch.
        Focus on establishing a clean visual branding direction, mapping out a core sitemap layout, functional booking flow, and basic local SEO signals.
        """

    prompt = f"""
    {context_prompt}
    
    Structure the output strictly into these sections:
    - title: Professional title (e.g. 'Flixora Web Platform PRD - {lead.business_name}')
    - business_overview
    - business_analysis
    - website_goal
    - target_audience
    - design_direction
    - site_structure
    - functional_requirements
    - content_requirements
    - cta_strategy
    - technical_requirements
    
    Ensure all sections contain thorough details and clear specifications. Do not leave blank fields.
    """

    try:
        schema = PRDSchema.model_json_schema()
        prd_data = llm_router.generate_structured_output(prompt, schema, task_type='prd_generation')

        # 4. Check if PRD already exists
        prd = PRD.query.filter_by(lead_id=lead_id).first()
        version_num = 1
        
        if prd:
            version_num = prd.current_version + 1
            prd.title = prd_data.get('title')
            prd.business_overview = prd_data.get('business_overview')
            prd.business_analysis = prd_data.get('business_analysis')
            prd.website_goal = prd_data.get('website_goal')
            prd.target_audience = prd_data.get('target_audience')
            prd.design_direction = prd_data.get('design_direction')
            prd.site_structure = prd_data.get('site_structure')
            prd.functional_requirements = prd_data.get('functional_requirements')
            prd.content_requirements = prd_data.get('content_requirements')
            prd.cta_strategy = prd_data.get('cta_strategy')
            prd.technical_requirements = prd_data.get('technical_requirements')
            prd.is_improvement = is_improvement
            prd.improvement_reason = analysis.improvement_reason
            prd.current_version = version_num
            prd.status = PRDStatus.READY  # Reset to ready status on regeneration
        else:
            prd = PRD(
                lead_id=lead_id,
                title=prd_data.get('title'),
                business_overview=prd_data.get('business_overview'),
                business_analysis=prd_data.get('business_analysis'),
                website_goal=prd_data.get('website_goal'),
                target_audience=prd_data.get('target_audience'),
                design_direction=prd_data.get('design_direction'),
                site_structure=prd_data.get('site_structure'),
                functional_requirements=prd_data.get('functional_requirements'),
                content_requirements=prd_data.get('content_requirements'),
                cta_strategy=prd_data.get('cta_strategy'),
                technical_requirements=prd_data.get('technical_requirements'),
                is_improvement=is_improvement,
                improvement_reason=analysis.improvement_reason,
                current_version=1,
                status=PRDStatus.READY
            )
            db.session.add(prd)
            db.session.commit()  # commit to generate ID

        # 5. Create PRD Version history entry (§34)
        snapshot = {
            "title": prd.title,
            "business_overview": prd.business_overview,
            "business_analysis": prd.business_analysis,
            "website_goal": prd.website_goal,
            "target_audience": prd.target_audience,
            "design_direction": prd.design_direction,
            "site_structure": prd.site_structure,
            "functional_requirements": prd.functional_requirements,
            "content_requirements": prd.content_requirements,
            "cta_strategy": prd.cta_strategy,
            "technical_requirements": prd.technical_requirements
        }
        
        version_entry = PRDVersion(
            prd_id=prd.id,
            version=version_num,
            author_type='ai',
            change_summary="Initial AI generation" if version_num == 1 else "AI regeneration",
            content_snapshot=snapshot
        )
        db.session.add(version_entry)
        
        # 6. Update lead status
        lead.status = LeadStatus.RESEARCHED
        lead.last_action = "PRD generated"
        lead.last_action_at = datetime.now(timezone.utc)
        
        db.session.commit()
        logger.info(f"PRD generated for lead {lead_id} (version: {version_num}). Title: {prd.title}")
        return {"success": True, "prd_id": prd.id, "version": version_num}
        
    except Exception as e:
        logger.error(f"Error during PRD generation for lead {lead_id}: {e}")
        return {"success": False, "error": f"PRD generation failed: {str(e)}"}


def revise_prd_with_ai(prd_id, instruction, user_id=None):
    """
    Revise PRD content based on natural language feedback from Admin (PRD AI Chat).
    Applies updates, bumps version count, and records snapshot.
    """
    prd = PRD.query.get(prd_id)
    if not prd:
        return {"success": False, "error": f"PRD with ID {prd_id} not found."}

    # Fetch current state details
    current_content = {
        "title": prd.title,
        "business_overview": prd.business_overview,
        "business_analysis": prd.business_analysis,
        "website_goal": prd.website_goal,
        "target_audience": prd.target_audience,
        "design_direction": prd.design_direction,
        "site_structure": prd.site_structure,
        "functional_requirements": prd.functional_requirements,
        "content_requirements": prd.content_requirements,
        "cta_strategy": prd.cta_strategy,
        "technical_requirements": prd.technical_requirements
    }

    prompt = f"""
    You are a professional web consultant.
    An Admin wants to revise the website Product Requirements Document (PRD).
    
    Admin Instruction:
    "{instruction}"
    
    Here is the current PRD contents:
    {json.dumps(current_content, indent=2)}
    
    You MUST output a revised version of this PRD strictly matching the schema requirements.
    Review the instruction and update the relevant fields (e.g. if instruction is 'make it mobile-first', update design_direction, site_structure, and technical_requirements as needed).
    Do not touch fields that are unrelated to the instruction, keeping their existing text intact.
    """

    try:
        schema = PRDSchema.model_json_schema()
        revised_data = llm_router.generate_structured_output(prompt, schema, task_type='prd_revision')

        # Bump version
        next_version = prd.current_version + 1
        
        # Update model
        prd.title = revised_data.get('title', prd.title)
        prd.business_overview = revised_data.get('business_overview', prd.business_overview)
        prd.business_analysis = revised_data.get('business_analysis', prd.business_analysis)
        prd.website_goal = revised_data.get('website_goal', prd.website_goal)
        prd.target_audience = revised_data.get('target_audience', prd.target_audience)
        prd.design_direction = revised_data.get('design_direction', prd.design_direction)
        prd.site_structure = revised_data.get('site_structure', prd.site_structure)
        prd.functional_requirements = revised_data.get('functional_requirements', prd.functional_requirements)
        prd.content_requirements = revised_data.get('content_requirements', prd.content_requirements)
        prd.cta_strategy = revised_data.get('cta_strategy', prd.cta_strategy)
        prd.technical_requirements = revised_data.get('technical_requirements', prd.technical_requirements)
        
        prd.current_version = next_version
        prd.status = PRDStatus.UNDER_REVIEW
        
        # Create Version history snapshot
        snapshot = {
            "title": prd.title,
            "business_overview": prd.business_overview,
            "business_analysis": prd.business_analysis,
            "website_goal": prd.website_goal,
            "target_audience": prd.target_audience,
            "design_direction": prd.design_direction,
            "site_structure": prd.site_structure,
            "functional_requirements": prd.functional_requirements,
            "content_requirements": prd.content_requirements,
            "cta_strategy": prd.cta_strategy,
            "technical_requirements": prd.technical_requirements
        }
        
        version_entry = PRDVersion(
            prd_id=prd.id,
            version=next_version,
            author_type='admin' if user_id else 'ai',
            author_id=user_id,
            change_summary=f"Admin revision chat: {instruction[:100]}",
            content_snapshot=snapshot
        )
        db.session.add(version_entry)
        
        db.session.commit()
        logger.info(f"PRD {prd.id} revised successfully to version {next_version}.")
        return {"success": True, "prd_id": prd.id, "version": next_version}

    except Exception as e:
        logger.error(f"Error revising PRD {prd_id}: {e}")
        return {"success": False, "error": f"Revision failed: {str(e)}"}
