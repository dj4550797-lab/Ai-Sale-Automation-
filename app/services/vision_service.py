"""
Flixora AI Sales Automation Agent — Vision Service

Analyzes uploaded images (logos, mockups, storefronts) using LLM vision capabilities.
Supports simulated vision responses when TEST_MODE is active (§75).
"""
import os
import base64
from flask import current_app
from pydantic import BaseModel, Field
from typing import List

from app.extensions import db
from app.models import UploadedFile, Lead
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


class VisionAnalysisSchema(BaseModel):
    """Pydantic schema for structured image understanding output."""
    dominant_colors: List[str] = Field(..., description="List of 3-5 hex color codes extracted from the image/logo")
    brand_style: str = Field(..., description="Description of the visual style, tone, and brand aesthetics (e.g. minimalist, luxurious, warm)")
    extracted_text: List[str] = Field(..., description="List of visible text elements, headings, or slogans found in the image")
    inferred_industry: str = Field(..., description="Logical inference about the business category or industry based on the image")


def analyze_business_image(file_id):
    """
    Perform visual audits on uploaded image files (logos/storefronts) to extract design assets.
    """
    file_record = UploadedFile.query.get(file_id)
    if not file_record:
        return {"success": False, "error": f"File with ID {file_id} not found."}

    if file_record.file_type not in ['image', 'logo']:
        return {"success": False, "error": "File type must be an image or logo to run vision analysis."}

    test_mode = current_app.config.get('TEST_MODE', True)
    if test_mode:
        logger.info(f"[TEST_MODE] Simulating vision analysis on file {file_record.original_filename}")
        return _get_mock_vision_analysis(file_record)

    logger.info(f"Analyzing image file {file_record.original_filename} via Vision Model")
    
    # Resolve absolute path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    abs_path = os.path.join(base_dir, file_record.file_path)
    
    if not os.path.exists(abs_path):
        return {"success": False, "error": "Physical image file does not exist on disk."}

    try:
        # Read file and encode to base64
        with open(abs_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

        prompt = """
        You are a design assistant. Analyze this base64 encoded business logo/visual asset.
        Identify:
        1. dominant_colors: Extract 3-5 hexadecimal color codes (e.g. '#FFFFFF', '#D4AF37') representing the core brand theme.
        2. brand_style: Describe the aesthetics, design style (luxurious, modern, retro, casual), and mood.
        3. extracted_text: Any text headings, slogans, or words visible in the logo.
        4. inferred_industry: Inferred business niche (e.g., hair salon, dental clinic, Italian restaurant).
        """
        
        # Include base64 image in options content block or as part of options/payload
        options = {
            "image_base64": encoded_image,
            "mime_type": file_record.mime_type or "image/png"
        }
        
        schema = VisionAnalysisSchema.model_json_schema()
        analysis_data = llm_router.generate_structured_output(
            prompt=prompt,
            response_schema=schema,
            task_type='image_analysis',
            options=options
        )
        
        # Optionally link analysis results directly to the lead's PRD visual notes
        if file_record.lead_id:
            lead = Lead.query.get(file_record.lead_id)
            if lead:
                lead.last_action = f"Visual logo analysis completed. Colors: {', '.join(analysis_data.get('dominant_colors', []))}"
                db.session.commit()

        return {
            "success": True,
            "data": analysis_data
        }
    except Exception as e:
        logger.error(f"Vision image analysis failed: {e}")
        return {"success": False, "error": f"Vision analysis failed: {str(e)}"}


def _get_mock_vision_analysis(file_record):
    """Generate realistic design assets mocks for business visual assets."""
    filename_lower = file_record.original_filename.lower()
    
    # Defaults
    dominant_colors = ["#2A4B7C", "#F4F7FA", "#1D2D44"]
    brand_style = "Minimalist, professional corporate branding with clean typography."
    extracted_text = ["Flixora Solutions"]
    inferred_industry = "technology"

    if "salon" in filename_lower or "beauty" in filename_lower or "hair" in filename_lower:
        dominant_colors = ["#D4AF37", "#1A1A1A", "#FDFBF7"] # Gold, Black, Off-White
        brand_style = "Luxurious, elegant visual brand styling with modern serif lettering."
        extracted_text = ["Luxe Salon", "Est. 2020"]
        inferred_industry = "beauty salon"
    elif "dent" in filename_lower or "clinic" in filename_lower:
        dominant_colors = ["#00A896", "#028090", "#F0F3F4"] # Teal, Ocean, Light Grey
        brand_style = "Clean, hygienic visual styling emphasizing trust, medical safety, and comfort."
        extracted_text = ["Family Dentistry", "Smile Care"]
        inferred_industry = "dental clinic"
    elif "restaurant" in filename_lower or "cafe" in filename_lower or "food" in filename_lower:
        dominant_colors = ["#8B0000", "#FFD700", "#3E2723"] # Dark Red, Gold, Brown
        brand_style = "Warm, inviting design language targeting traditional craft cooking and family dining."
        extracted_text = ["Green Valley Diner"]
        inferred_industry = "restaurant"

    return {
        "success": True,
        "data": {
            "dominant_colors": dominant_colors,
            "brand_style": brand_style,
            "extracted_text": extracted_text,
            "inferred_industry": inferred_industry
        }
    }
