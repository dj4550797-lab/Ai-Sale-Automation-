"""
Flixora AI Sales Automation Agent — Website Analysis Service

Scrapes and performs website analysis using the LLM Router.
"""
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import List

from app.extensions import db
from app.models import Lead, WebsiteAnalysis
from app.constants import WebsiteVerdict
from app.services.scraper_service import scrape_website
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


class WebsiteAnalysisSchema(BaseModel):
    """Pydantic schema for website analysis output from LLM."""
    visual_design_score: int = Field(..., description="Score 1-100 for visual style, colors, fonts and design professionalism")
    layout_score: int = Field(..., description="Score 1-100 for spacing, content alignment and grid usage")
    typography_score: int = Field(..., description="Score 1-100 for font legibility, hierarchy and spacing")
    branding_score: int = Field(..., description="Score 1-100 for logo alignment and brand consistency")
    mobile_score: int = Field(..., description="Score 1-100 for mobile friendly layouts and responsiveness")
    navigation_score: int = Field(..., description="Score 1-100 for header, footer and menu usability")
    cta_score: int = Field(..., description="Score 1-100 for call-to-actions prominence and placement")
    contact_flow_score: int = Field(..., description="Score 1-100 for finding phone, email, and booking forms easily")
    service_presentation_score: int = Field(..., description="Score 1-100 for service descriptions, benefits and details")
    trust_signals_score: int = Field(..., description="Score 1-100 for reviews, testimonials, certifications and badges")
    performance_score: int = Field(..., description="Score 1-100 for page load speed signals and optimization")
    accessibility_score: int = Field(..., description="Score 1-100 for basic web accessibility elements")
    conversion_score: int = Field(..., description="Score 1-100 for customer conversion potential")
    
    overall_score: int = Field(..., description="Weighted average overall score 1-100 of the website")
    verdict: str = Field(..., description="Must be either 'needs_improvement' or 'adequate'")
    improvement_needed: bool = Field(..., description="True if website needs an overhaul or update, False otherwise")
    improvement_reason: str = Field(..., description="Short explanation of why improvement is or isn't needed")
    
    observed_facts: List[str] = Field(..., description="List of observed facts (what is actually present/missing on the site)")
    ai_recommendations: List[str] = Field(..., description="List of direct AI recommendations for improvement")
    ai_inferences: List[str] = Field(..., description="List of logical business inferences drawn from the current site status")


def analyze_lead_website(lead_id):
    """
    Trigger website scraping and LLM analysis for a lead.
    Saves results to the WebsiteAnalysis table and updates the Lead record.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": f"Lead with ID {lead_id} not found."}

    # Initialize analysis entry
    analysis = WebsiteAnalysis.query.filter_by(lead_id=lead_id).first()
    if not analysis:
        analysis = WebsiteAnalysis(lead_id=lead_id, status='pending')
        db.session.add(analysis)
        db.session.commit()

    analysis.status = 'analyzing'
    db.session.commit()

    # 1. Check if website url exists
    url = lead.website_url
    if not url:
        # Skip analysis if website does not exist (§797-803)
        analysis.website_exists = False
        analysis.url = ''
        analysis.verdict = WebsiteVerdict.NO_WEBSITE
        analysis.overall_score = 0
        analysis.improvement_needed = True
        analysis.improvement_reason = "No website exists. Opportunity to generate a completely new web footprint."
        analysis.observed_facts = ["No existing website found in search directory."]
        analysis.ai_recommendations = ["Build a new single-page modern landing page with booking CTAs."]
        analysis.ai_inferences = ["Business is missing out on 100% of direct web traffic and search engine bookings."]
        analysis.status = 'completed'
        analysis.completed_at = datetime.now(timezone.utc)
        
        lead.website_exists = False
        lead.last_action = "Skipped website analysis: No website URL"
        lead.last_action_at = datetime.now(timezone.utc)
        db.session.commit()
        
        logger.info(f"Skipped website analysis for lead {lead.id} because no website URL exists.")
        return {"success": True, "analysis_id": analysis.id, "message": "Skipped existing site analysis (no URL)."}

    # 2. Scrape the URL
    analysis.url = url
    analysis.website_exists = True
    scrape_res = scrape_website(url)
    
    if not scrape_res.get('success'):
        # Log failure and update analysis status
        analysis.status = 'failed'
        analysis.error_message = scrape_res.get('error', 'Scraping failed.')
        db.session.commit()
        
        lead.website_exists = True
        lead.last_action = f"Website scraping failed: {scrape_res.get('error')}"
        lead.last_action_at = datetime.now(timezone.utc)
        db.session.commit()
        return {"success": False, "error": scrape_res.get('error')}

    # 3. Prompt LLM to analyze the scraped content structure
    prompt = f"""
    You are an expert website consultant analyzing a local business website.
    Business Name: {lead.business_name}
    Business Category: {lead.business_category}
    Website URL: {url}

    Here is the scraped metadata and page layout representation:
    Title: {scrape_res.get('title')}
    Headings (H1/H2/H3): {", ".join(scrape_res.get('headings', []))}
    Paragraph count: {scrape_res.get('paragraph_count')}
    Detected Forms count: {scrape_res.get('forms_count')}
    Detected Phone numbers: {", ".join(scrape_res.get('detected_phones', []))}
    Page Text Snippet:
    "{scrape_res.get('raw_text_stub')}"

    Perform a deep structural audit of this page according to the following scoring criteria (each score from 1 to 100):
    - visual_design_score: Professionalism, clean branding, layout elegance.
    - layout_score: Structure grids, padding consistency, element alignment.
    - typography_score: Font hierarchy, readability on screens.
    - branding_score: Logo presence, brand styling consistency.
    - mobile_score: Check elements for mobile responsiveness.
    - navigation_score: Menu simplicity, link layouts.
    - cta_score: Visibility of primary buttons (e.g. Booking, Book Now).
    - contact_flow_score: Finding phone number, address, email.
    - service_presentation_score: How clearly services are listed.
    - trust_signals_score: Reviews, testimonials, badges.
    - performance_score: Image density, loading indicators.
    - accessibility_score: Contrast, tags.
    - conversion_score: Lead capturing capabilities.

    Determine if a website redesign/improvement is needed (improvement_needed = true/false). If overall_score is below 80, improvement_needed should be true.
    You must output lists of observed_facts (e.g., 'Only 1 H1 heading present', 'No online booking form found'), ai_recommendations (e.g., 'Add a floating Call to Action button'), and ai_inferences (e.g., 'Customers likely leave due to difficult booking path').
    """

    try:
        schema = WebsiteAnalysisSchema.model_json_schema()
        analysis_data = llm_router.generate_structured_output(prompt, schema, task_type='website_analysis')
        
        # 4. Map and save scores
        analysis.visual_design_score = analysis_data.get('visual_design_score')
        analysis.layout_score = analysis_data.get('layout_score')
        analysis.typography_score = analysis_data.get('typography_score')
        analysis.branding_score = analysis_data.get('branding_score')
        analysis.mobile_score = analysis_data.get('mobile_score')
        analysis.navigation_score = analysis_data.get('navigation_score')
        analysis.cta_score = analysis_data.get('cta_score')
        analysis.contact_flow_score = analysis_data.get('contact_flow_score')
        analysis.service_presentation_score = analysis_data.get('service_presentation_score')
        analysis.trust_signals_score = analysis_data.get('trust_signals_score')
        analysis.performance_score = analysis_data.get('performance_score')
        analysis.accessibility_score = analysis_data.get('accessibility_score')
        analysis.conversion_score = analysis_data.get('conversion_score')
        
        analysis.overall_score = analysis_data.get('overall_score')
        analysis.verdict = WebsiteVerdict.NEEDS_IMPROVEMENT if analysis_data.get('improvement_needed') else WebsiteVerdict.ADEQUATE
        analysis.improvement_needed = analysis_data.get('improvement_needed')
        analysis.improvement_reason = analysis_data.get('improvement_reason')
        
        analysis.observed_facts = analysis_data.get('observed_facts')
        analysis.ai_recommendations = analysis_data.get('ai_recommendations')
        analysis.ai_inferences = analysis_data.get('ai_inferences')
        
        analysis.status = 'completed'
        analysis.completed_at = datetime.now(timezone.utc)
        
        # 5. Update Lead properties
        lead.website_exists = True
        lead.last_action = "Website analysis completed"
        lead.last_action_at = datetime.now(timezone.utc)
        
        db.session.commit()
        logger.info(f"Website analysis completed for lead {lead.id}. Verdict: {analysis.verdict}")
        return {"success": True, "analysis_id": analysis.id, "verdict": analysis.verdict}
        
    except Exception as e:
        logger.error(f"Error during LLM website analysis for lead {lead.id}: {e}")
        analysis.status = 'failed'
        analysis.error_message = f"LLM routing or parsing failed: {str(e)}"
        db.session.commit()
        return {"success": False, "error": f"LLM analysis failed: {str(e)}"}
