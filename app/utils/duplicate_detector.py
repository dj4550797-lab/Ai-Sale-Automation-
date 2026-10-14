"""
Flixora AI Sales Automation Agent — Duplicate Detector

Checks incoming business records against existing leads database (§22).
Matches by:
1. Google Place ID
2. National Phone Number
3. Website Domain
4. Business Name + Address
"""
from urllib.parse import urlparse
from app.models import Lead, LeadContact


def clean_url_domain(url):
    """Normalize URLs to domain-only for matching (e.g. www.salon.com -> salon.com)."""
    if not url:
        return ''
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path
        domain = netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return url.lower()


def clean_address(address):
    """Extract street number/first part of address for rough alignment check."""
    if not address:
        return ''
    # Take first 15 characters of address lowercase
    return address.strip().lower()[:15]


def check_for_duplicate(business_data):
    """
    Check if a business record is a duplicate.
    Returns dict with duplicate status, matched lead ID, and verdict reason.
    """
    place_id = business_data.get('google_place_id')
    phone = business_data.get('phone')
    website = business_data.get('website_url')
    name = business_data.get('business_name')
    address = business_data.get('address')

    # ── Rule 1: Google Place ID Match (Confirmed Duplicate) ────────────────────
    if place_id:
        existing = Lead.query.filter_by(google_place_id=place_id).first()
        if existing:
            return {
                'status': 'confirmed_duplicate',
                'matched_lead_id': existing.id,
                'reason': f"Matched existing lead by Google Place ID: {place_id}"
            }

    # ── Rule 2: Phone number match (Confirmed Duplicate) ──────────────────────
    if phone:
        # Search lead contacts for national phone match
        contact = LeadContact.query.filter_by(contact_type='phone', value=phone).first()
        if contact:
            existing = Lead.query.get(contact.lead_id)
            if existing:
                return {
                    'status': 'confirmed_duplicate',
                    'matched_lead_id': existing.id,
                    'reason': f"Matched existing lead by contact phone: {phone}"
                }

    # ── Rule 3: Website Domain Match (Likely Duplicate) ────────────────────────
    if website:
        target_domain = clean_url_domain(website)
        if target_domain:
            # Query all leads with websites
            all_leads = Lead.query.filter(Lead.website_url.isnot(None), Lead.website_url != '').all()
            for lead in all_leads:
                if clean_url_domain(lead.website_url) == target_domain:
                    return {
                        'status': 'likely_duplicate',
                        'matched_lead_id': lead.id,
                        'reason': f"Matched existing lead domain: {target_domain}"
                    }

    # ── Rule 4: Business Name + Address Match (Likely Duplicate) ───────────────
    if name and address:
        clean_name = name.strip().lower()
        clean_addr_stub = clean_address(address)
        
        # Query leads with same/similar name
        leads_with_similar_name = Lead.query.filter(Lead.business_name.ilike(f"%{name}%")).all()
        for lead in leads_with_similar_name:
            if clean_address(lead.address) == clean_addr_stub:
                return {
                    'status': 'likely_duplicate',
                    'matched_lead_id': lead.id,
                    'reason': f"Matched existing lead by name '{name}' and address stub '{clean_addr_stub}'"
                }

    return {
        'status': 'unique',
        'matched_lead_id': None,
        'reason': ''
    }
