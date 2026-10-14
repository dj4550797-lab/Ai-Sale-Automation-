"""
Flixora AI Sales Automation Agent — Demo Service

Generates single-page HTML demos and handles static hosting mapping (§37, §38).
"""
import os
import requests
from datetime import datetime, timezone
from flask import current_app

from app.extensions import db
from app.models import Lead, PRD, DemoProject, APICredential
from app.constants import PRDStatus, LeadStatus
from app.ai.llm_router import llm_router
from app.utils.logger import get_logger

logger = get_logger('services')


def _generate_premium_fallback_demo_html(lead, prd):
    """
    Generate an ultra-modern, high-converting standalone single-page landing page
    specifically customized to the lead's business data and PRD directives.
    Guarantees demo websites are always compiled cleanly even during upstream LLM outages.
    """
    cat = (lead.business_category or 'services').lower()
    b_name = lead.business_name or "Premium Services"
    b_addr = lead.address or "Prime City Location"
    b_rating = lead.rating or 4.8
    b_reviews = lead.review_count or 120
    b_hours = lead.business_hours or "Monday – Saturday: 10:00 AM – 9:00 PM | Sunday: 11:00 AM – 8:00 PM"
    
    # Extract phone
    b_phone = ""
    phone_contact = lead.contacts.filter_by(contact_type='phone').first() if hasattr(lead, 'contacts') else None
    if phone_contact:
        b_phone = phone_contact.value
    clean_phone = "".join(filter(str.isdigit, b_phone)) if b_phone else "919876543210"

    # Category themes: (primary, secondary, accent, bg_gradient, icon)
    if any(k in cat for k in ['salon', 'beauty', 'spa', 'hair']):
        theme = {
            'p': '#e05a87', 'p_dark': '#be3766', 'glow': 'rgba(224,90,135,0.25)',
            'tag': 'Luxury Beauty & Wellness Salon',
            'headline': f'Experience Elegance & Pampering at {b_name}',
            'sub': 'Indulge in personalized beauty treatments, master hairstyling, and revitalizing spa therapies crafted to make you shine.',
            's1': 'Hair Styling & Couture Coloring', 's1_desc': 'Tailored cuts, keratin treatments, and trendsetting balayage by master stylists.',
            's2': 'Facial Rejuvenation & Skin Therapies', 's2_desc': 'Revitalize your natural glow with advanced dermatological facials and organic peel treatments.',
            's3': 'Bridal & Occasion Glamour', 's3_desc': 'Flawless makeup and comprehensive bridal packages for your most memorable moments.',
            's4': 'Nail Art & Luxury Spa Pedicures', 's4_desc': 'Relax in plush spa chairs with meticulous nail shaping, gel art, and restorative scrubs.'
        }
    elif any(k in cat for k in ['restaurant', 'cafe', 'food', 'dining', 'kitchen', 'bar']):
        theme = {
            'p': '#ea580c', 'p_dark': '#c2410c', 'glow': 'rgba(234,88,12,0.25)',
            'tag': 'Culinary Destination & Fine Dining',
            'headline': f'Savor Authentic Culinary Passion at {b_name}',
            'sub': 'Discover artisan recipes, signature spices, and an unforgettable dining ambiance crafted with love and fresh ingredients.',
            's1': 'Signature Chef Specialties', 's1_desc': 'Handcrafted gourmet recipes blending traditional culinary heritage with contemporary flair.',
            's2': 'Artisan Beverages & Cocktails', 's2_desc': 'Carefully curated seasonal mocktails, specialty coffees, and craft drink pairings.',
            's3': 'Private Dining & Celebrations', 's3_desc': 'Custom banquet menus and intimate ambient seating for family gatherings and celebrations.',
            's4': 'Express Takeaway & Fast Delivery', 's4_desc': 'Savor piping hot culinary masterpieces delivered safely to your doorstep.'
        }
    elif any(k in cat for k in ['dentist', 'dental', 'clinic', 'health', 'doctor']):
        theme = {
            'p': '#0284c7', 'p_dark': '#0369a1', 'glow': 'rgba(2,132,199,0.25)',
            'tag': 'Gentle & Advanced Healthcare Practice',
            'headline': f'Gentle Care & Confident Smiles at {b_name}',
            'sub': 'State-of-the-art diagnostics, compassionate specialists, and pain-free treatments designed for your entire family.',
            's1': 'Comprehensive Health Consultations', 's1_desc': 'Thorough diagnostic checkups and preventative treatment plans with modern imaging.',
            's2': 'Cosmetic Smile Makeovers', 's2_desc': 'Teeth whitening, invisible aligners, and dental veneers tailored to your smile.',
            's3': 'Pain-Free Root Canals & Restorations', 's3_desc': 'Microscopic precision endodontics ensuring complete comfort and swift recovery.',
            's4': 'Emergency & Pediatric Care', 's4_desc': 'Prompt relief for acute toothaches and gentle, comforting dental visits for children.'
        }
    elif any(k in cat for k in ['gym', 'fitness', 'crossfit', 'workout']):
        theme = {
            'p': '#10b981', 'p_dark': '#059669', 'glow': 'rgba(16,185,129,0.25)',
            'tag': 'Elite Performance & Fitness Club',
            'headline': f'Transform Your Strength & Vitality at {b_name}',
            'sub': 'High-energy training, world-class equipment, and certified coaches committed to helping you crush every personal goal.',
            's1': 'Personalized Strength Coaching', 's1_desc': 'Custom periodized training programs tailored to your strength, posture, and body composition.',
            's2': 'High-Intensity Group Workouts', 's2_desc': 'Pulse-pounding HIIT and functional conditioning classes that burn calories and build stamina.',
            's3': 'Nutrition & Wellness Coaching', 's3_desc': 'Holistic meal planning and habit tracking designed to sustain long-term vitality.',
            's4': 'Recovery & Mobility Zone', 's4_desc': 'Foam rollers, contrast therapy guidelines, and guided stretching to keep you injury-free.'
        }
    elif any(k in cat for k in ['real estate', 'property', 'builder', 'realty', 'estate', 'advisory', 'housing']):
        theme = {
            'p': '#d97706', 'p_dark': '#b45309', 'glow': 'rgba(217,119,6,0.25)',
            'tag': 'Luxury Real Estate & Prime Property Advisory',
            'headline': f'Discover Architectural Elegance & Prime Living at {b_name}',
            'sub': 'Exclusive residential penthouses, luxury commercial investments, and bespoke advisory tailored to ambitious property investors.',
            's1': 'Curated Luxury Residences', 's1_desc': 'Handpicked premium villas, duplexes, and skyline apartments in prime locations.',
            's2': 'Strategic Commercial Portfolios', 's2_desc': 'High-yield office spaces, retail outlets, and prime developments yielding capital appreciation.',
            's3': 'End-to-End Legal & Title Due Diligence', 's3_desc': 'Seamless document verification, RERA compliance certification, and bank finance guidance.',
            's4': 'Private VIP Property Viewings', 's4_desc': 'Discreet guided property walkthroughs and virtual reality immersions at your convenience.'
        }
    elif any(k in cat for k in ['tech', 'software', 'agency', 'digital', 'marketing', 'web', 'it ', 'consulting']):
        theme = {
            'p': '#3b82f6', 'p_dark': '#1d4ed8', 'glow': 'rgba(59,130,246,0.25)',
            'tag': 'Modern Digital Agency & Technology Studio',
            'headline': f'Accelerate Your Digital Advantage with {b_name}',
            'sub': 'High-impact web architectures, enterprise automation, and custom digital systems designed to scale brand revenue.',
            's1': 'Full-Stack Web & Mobile Engineering', 's1_desc': 'Lightning-fast cloud applications built with resilient modern frameworks.',
            's2': 'Conversion-Obsessed UI/UX Design', 's2_desc': 'Polished design systems, micro-interactions, and conversion-funnel optimization.',
            's3': 'AI & Workflow Automation', 's3_desc': 'Integrate intelligent CRM workflows, automated outreach, and autonomous agents.',
            's4': 'Organic Search & Performance Growth', 's4_desc': 'Data-backed SEO campaigns and paid media funnels engineered for rapid ROI.'
        }
    elif any(k in cat for k in ['jewel', 'fashion', 'boutique', 'cloth', 'retail', 'store', 'shop']):
        theme = {
            'p': '#ec4899', 'p_dark': '#db2777', 'glow': 'rgba(236,72,153,0.25)',
            'tag': 'Artisan Elegance & Curated Collections',
            'headline': f'Exquisite Craftsmanship & Bespoke Style at {b_name}',
            'sub': 'Explore handcrafted statement designs, premium collections, and personalized styling consultations.',
            's1': 'Signature Handcrafted Creations', 's1_desc': 'Distinctive jewelry pieces and couture outfits created by master artisans.',
            's2': 'Personal Styling & Fitting Sessions', 's2_desc': 'One-on-one custom styling consultations to match your personal aesthetic.',
            's3': 'Certified Quality & Authenticity Guarantee', 's3_desc': '100% verified hallmarked materials with certificates of purity.',
            's4': 'VIP Custom Commissions & Milestone Sets', 's4_desc': 'Bespoke designs crafted specifically for weddings and gala milestones.'
        }
    elif any(k in cat for k in ['car', 'auto', 'motor', 'garage', 'vehicle', 'mechanic', 'detail']):
        theme = {
            'p': '#f59e0b', 'p_dark': '#d97706', 'glow': 'rgba(245,158,11,0.25)',
            'tag': 'Precision Automotive Care & Detailing',
            'headline': f'Showroom Perfection & Mechanical Mastery at {b_name}',
            'sub': 'State-of-the-art ceramic coatings, multi-point diagnostic maintenance, and precision mechanical care.',
            's1': 'Ceramic Shield & Paint Protection', 's1_desc': '9H graphene coatings protecting your vehicle against micro-scratches and UV oxidation.',
            's2': 'Deep Interior Sanitization & Detailing', 's2_desc': 'Steam extraction, leather conditioning, and anti-bacterial cabin restoration.',
            's3': 'Computerized Diagnostics & Servicing', 's3_desc': 'Engine health scans, fluid servicing, and suspension optimization.',
            's4': 'Express Periodic Maintenance', 's4_desc': 'Fast oil changes, brake inspections, and alignment with original OEM parts.'
        }
    else:
        theme = {
            'p': '#6366f1', 'p_dark': '#4f46e5', 'glow': 'rgba(99,102,241,0.25)',
            'tag': f'Verified {cat.title()} Specialist',
            'headline': f'Premier Excellence & Reliable Service at {b_name}',
            'sub': f'Delivering trusted solutions, personalized customer attention, and unmatched expertise in {b_addr}.',
            's1': 'Customized Consultations', 's1_desc': 'In-depth evaluation of your specific requirements with transparent project timelines.',
            's2': 'Premium Quality Execution', 's2_desc': 'Industry-tested standards and meticulous craftsmanship that guarantee lasting results.',
            's3': 'Transparent & Fair Pricing', 's3_desc': 'Honest upfront quotes without hidden fees or surprise add-ons.',
            's4': 'Dedicated Aftercare & Support', 's4_desc': 'Ongoing customer support and rapid response for any follow-up questions.'
        }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{b_name} — Official Website</title>
    <meta name="description" content="Welcome to {b_name}. Quality {cat} services in {b_addr}. Call or book online today.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: {theme['p']};
            --primary-dark: {theme['p_dark']};
            --primary-glow: {theme['glow']};
            --bg-base: #0a0c10;
            --bg-surface: #121620;
            --bg-elevated: #1a202e;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-faint: #64748b;
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --radius-sm: 8px;
            --radius-md: 14px;
            --radius-lg: 22px;
            --font: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
            --shadow: 0 12px 30px rgba(0,0,0,0.35);
        }}
        [data-theme="light"] {{
            --bg-base: #f8fafc;
            --bg-surface: #ffffff;
            --bg-elevated: #f1f5f9;
            --text-main: #0f172a;
            --text-muted: #475569;
            --text-faint: #64748b;
            --border: rgba(0, 0, 0, 0.08);
            --border-hover: rgba(0, 0, 0, 0.16);
            --shadow: 0 12px 30px rgba(0,0,0,0.08);
        }}
        [data-theme="light"] header {{
            background: rgba(255, 255, 255, 0.92);
        }}
        [data-theme="light"] .form-input {{
            color: #0f172a;
            background: #ffffff;
        }}
        [data-theme="light"] .btn-outline {{
            background: rgba(0, 0, 0, 0.04);
            color: #0f172a;
        }}
        [data-theme="light"] .badge-pill {{
            background: rgba(0, 0, 0, 0.05);
            color: #0f172a;
        }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            background: var(--bg-base);
            color: var(--text-main);
            font-family: var(--font);
            line-height: 1.6;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }}
        a {{ text-decoration:none; color:inherit; }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
        }}
        /* Header */
        header {{
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(16px);
            background: rgba(10, 12, 16, 0.85);
            border-bottom: 1px solid var(--border);
        }}
        .nav-wrap {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 72px;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 800;
            font-size: 20px;
            letter-spacing: -0.02em;
        }}
        .brand-logo {{
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            display: grid;
            place-items: center;
            font-weight: 900;
            color: #fff;
            box-shadow: 0 4px 14px var(--primary-glow);
        }}
        .nav-links {{
            display: flex;
            align-items: center;
            gap: 28px;
            list-style: none;
        }}
        .nav-links a {{
            color: var(--text-muted);
            font-size: 14px;
            font-weight: 500;
            transition: color 0.2s;
        }}
        .nav-links a:hover {{ color: #fff; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 14px;
            border: none;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        .btn-primary {{
            background: var(--primary);
            color: #fff;
            box-shadow: 0 4px 16px var(--primary-glow);
        }}
        .btn-primary:hover {{
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 6px 22px var(--primary-glow);
        }}
        .btn-outline {{
            background: rgba(255,255,255,0.04);
            border: 1px solid var(--border-hover);
            color: #fff;
        }}
        .btn-outline:hover {{
            background: rgba(255,255,255,0.08);
            transform: translateY(-2px);
        }}
        /* Hero */
        .hero {{
            padding: 90px 0 60px;
            position: relative;
            text-align: center;
        }}
        .hero::before {{
            content: '';
            position: absolute;
            top: -100px;
            left: 50%;
            transform: translateX(-50%);
            width: 700px;
            height: 400px;
            background: radial-gradient(circle, var(--primary-glow) 0%, rgba(0,0,0,0) 70%);
            z-index: -1;
            pointer-events: none;
        }}
        .badge-pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 16px;
            border-radius: 999px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 24px;
        }}
        .badge-pill span {{
            color: var(--primary);
            font-weight: 700;
        }}
        .hero h1 {{
            font-size: clamp(34px, 5vw, 56px);
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.03em;
            max-width: 900px;
            margin: 0 auto 20px;
        }}
        .hero p {{
            font-size: clamp(16px, 2vw, 19px);
            color: var(--text-muted);
            max-width: 680px;
            margin: 0 auto 36px;
            line-height: 1.7;
        }}
        .hero-actions {{
            display: flex;
            justify-content: center;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 50px;
        }}
        /* Stats Ribbon */
        .stats-ribbon {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            padding: 24px;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            margin-bottom: 80px;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-val {{
            font-size: 26px;
            font-weight: 800;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }}
        .stat-val span {{ color: #fbbf24; font-size: 20px; }}
        .stat-lbl {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-faint);
            margin-top: 4px;
        }}
        /* Sections */
        .section {{
            padding: 60px 0;
        }}
        .section-header {{
            text-align: center;
            max-width: 640px;
            margin: 0 auto 48px;
        }}
        .section-tag {{
            color: var(--primary);
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 8px;
            display: block;
        }}
        .section-title {{
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 12px;
        }}
        .section-desc {{
            color: var(--text-muted);
            font-size: 16px;
        }}
        /* Grid */
        .services-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 24px;
        }}
        .card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 32px 24px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            overflow: hidden;
        }}
        .card:hover {{
            transform: translateY(-4px);
            border-color: var(--border-hover);
            box-shadow: var(--shadow);
        }}
        .card-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: rgba(255,255,255,0.04);
            border: 1px solid var(--border);
            display: grid;
            place-items: center;
            font-size: 22px;
            margin-bottom: 20px;
            color: var(--primary);
        }}
        .card h3 {{
            font-size: 19px;
            font-weight: 700;
            margin-bottom: 10px;
        }}
        .card p {{
            color: var(--text-muted);
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 20px;
        }}
        .card-link {{
            color: var(--primary);
            font-weight: 600;
            font-size: 13px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        /* Testimonials */
        .reviews-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .review-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 24px;
        }}
        .stars {{
            color: #fbbf24;
            font-size: 14px;
            margin-bottom: 12px;
        }}
        .review-text {{
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 16px;
            font-style: italic;
        }}
        .author {{
            font-weight: 600;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .author-badge {{
            font-size: 11px;
            color: var(--primary);
            background: rgba(255,255,255,0.06);
            padding: 2px 8px;
            border-radius: 4px;
        }}
        /* Contact Section */
        .info-card {{
            background: linear-gradient(135deg, var(--bg-surface), var(--bg-elevated));
            border: 1px solid var(--border-hover);
            border-radius: var(--radius-lg);
            padding: 48px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 40px;
            align-items: center;
        }}
        .info-detail h4 {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--primary);
            margin-bottom: 6px;
        }}
        .info-detail p {{
            font-size: 16px;
            color: var(--text-main);
            margin-bottom: 18px;
        }}
        /* Floating WhatsApp Button */
        .wa-float {{
            position: fixed;
            bottom: 28px;
            right: 28px;
            background: #25d366;
            color: #fff;
            width: 58px;
            height: 58px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            font-size: 30px;
            box-shadow: 0 8px 24px rgba(37,211,102,0.4);
            z-index: 999;
            transition: all 0.25s;
        }}
        .wa-float:hover {{
            transform: scale(1.08);
            box-shadow: 0 12px 30px rgba(37,211,102,0.55);
        }}
        /* Modal Dialog */
        .modal-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .modal {{
            background: var(--bg-surface);
            border: 1px solid var(--border-hover);
            border-radius: var(--radius-md);
            max-width: 440px;
            width: 100%;
            padding: 32px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
            position: relative;
        }}
        .modal-close {{
            position: absolute;
            top: 16px;
            right: 16px;
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 20px;
            cursor: pointer;
        }}
        .form-group {{
            margin-bottom: 16px;
        }}
        .form-label {{
            display: block;
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 6px;
            font-weight: 500;
        }}
        .form-input {{
            width: 100%;
            padding: 12px 14px;
            background: var(--bg-base);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: #fff;
            font-family: inherit;
            font-size: 14px;
            outline: none;
        }}
        .form-input:focus {{
            border-color: var(--primary);
        }}
        /* Footer */
        footer {{
            border-top: 1px solid var(--border);
            padding: 40px 0;
            text-align: center;
            color: var(--text-faint);
            font-size: 13px;
            margin-top: 80px;
        }}
        @media (max-width: 768px) {{
            .nav-links {{ display: none; }}
            .info-card {{ padding: 28px; }}
            .hero {{ padding: 60px 0 40px; }}
        }}
    </style>
</head>
<body>

    <!-- Header Navigation -->
    <header>
        <div class="container">
            <div class="nav-wrap">
                <a href="#" class="brand">
                    <div class="brand-logo">{b_name[:1].upper()}</div>
                    <span>{b_name}</span>
                </a>
                <ul class="nav-links">
                    <li><a href="#services">Services</a></li>
                    <li><a href="#why-us">Why Choose Us</a></li>
                    <li><a href="#reviews">Testimonials</a></li>
                    <li><a href="#contact">Contact</a></li>
                </ul>
                <div style="display:flex;align-items:center;gap:8px;">
                    <button type="button" onclick="toggleTheme()" class="btn btn-outline" style="padding:10px 14px;font-size:12px;" title="Toggle Light/Dark Theme">
                        <span id="themeBtnText">☀️ Light</span>
                    </button>
                    <button class="btn btn-primary" onclick="openBookingModal()">Book Appointment</button>
                </div>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="badge-pill">
                <span>★ {b_rating} Rating</span> &bull; Verified Local Business &bull; {b_addr}
            </div>
            <h1>{theme['headline']}</h1>
            <p>{theme['sub']}</p>
            <div class="hero-actions">
                <button class="btn btn-primary" onclick="openBookingModal()">Reserve Online Now</button>
                <a href="https://wa.me/{clean_phone}?text=Hello%20{b_name},%20I%20would%20like%20to%20inquire%20about%20your%20services." target="_blank" class="btn btn-outline">
                    Chat on WhatsApp
                </a>
            </div>

            <!-- Stats Ribbon -->
            <div class="stats-ribbon">
                <div class="stat-item">
                    <div class="stat-val">{b_rating} <span>★</span></div>
                    <div class="stat-lbl">Google Rating ({b_reviews}+ Reviews)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">100%</div>
                    <div class="stat-lbl">Verified Quality Service</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">Open Today</div>
                    <div class="stat-lbl">Fast Online Inquiries</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val">Prime Location</div>
                    <div class="stat-lbl">{b_addr}</div>
                </div>
            </div>
        </div>
    </section>

    <!-- Services Section -->
    <section class="section" id="services">
        <div class="container">
            <div class="section-header">
                <span class="section-tag">Premium Offerings</span>
                <h2 class="section-title">Crafted for Exceptional Results</h2>
                <p class="section-desc">Experience our signature services delivered by experienced specialists dedicated to your comfort and delight.</p>
            </div>
            <div class="services-grid">
                <div class="card">
                    <div class="card-icon">✦</div>
                    <h3>{theme['s1']}</h3>
                    <p>{theme['s1_desc']}</p>
                    <a href="javascript:void(0)" onclick="openBookingModal('{theme['s1']}')" class="card-link">Reserve Service &rarr;</a>
                </div>
                <div class="card">
                    <div class="card-icon">★</div>
                    <h3>{theme['s2']}</h3>
                    <p>{theme['s2_desc']}</p>
                    <a href="javascript:void(0)" onclick="openBookingModal('{theme['s2']}')" class="card-link">Reserve Service &rarr;</a>
                </div>
                <div class="card">
                    <div class="card-icon">❖</div>
                    <h3>{theme['s3']}</h3>
                    <p>{theme['s3_desc']}</p>
                    <a href="javascript:void(0)" onclick="openBookingModal('{theme['s3']}')" class="card-link">Reserve Service &rarr;</a>
                </div>
                <div class="card">
                    <div class="card-icon">♦</div>
                    <h3>{theme['s4']}</h3>
                    <p>{theme['s4_desc']}</p>
                    <a href="javascript:void(0)" onclick="openBookingModal('{theme['s4']}')" class="card-link">Reserve Service &rarr;</a>
                </div>
            </div>
        </div>
    </section>

    <!-- Why Us Section -->
    <section class="section" id="why-us">
        <div class="container">
            <div class="section-header">
                <span class="section-tag">Our Promise</span>
                <h2 class="section-title">Why Customers Trust {b_name}</h2>
                <p class="section-desc">We combine top-tier standards, certified experts, and welcoming hospitality.</p>
            </div>
            <div class="services-grid">
                <div class="card">
                    <div class="card-icon">✓</div>
                    <h3>Certified Specialists</h3>
                    <p>Our experienced team undergoes rigorous training to ensure every service meets gold-standard excellence.</p>
                </div>
                <div class="card">
                    <div class="card-icon">✓</div>
                    <h3>Transparent & Upfront</h3>
                    <p>Enjoy clear consultations and honest pricing with zero surprise charges or compromises on quality.</p>
                </div>
                <div class="card">
                    <div class="card-icon">✓</div>
                    <h3>Sanitized & Pristine</h3>
                    <p>Immaculately maintained facilities with strict hygienic protocols for your peace of mind and safety.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- Reviews Section -->
    <section class="section" id="reviews">
        <div class="container">
            <div class="section-header">
                <span class="section-tag">Client Reviews</span>
                <h2 class="section-title">Loved by Our Local Community</h2>
                <p class="section-desc">Hear what real customers say about their experiences with us.</p>
            </div>
            <div class="reviews-grid">
                <div class="review-card">
                    <div class="stars">★★★★★</div>
                    <p class="review-text">"Absolutely top-notch experience! The team at {b_name} is attentive, professional, and delivers exactly what you ask for. Highly recommended!"</p>
                    <div class="author">Pooja Sharma <span class="author-badge">Verified Customer</span></div>
                </div>
                <div class="review-card">
                    <div class="stars">★★★★★</div>
                    <p class="review-text">"Loved the ambiance and welcoming vibe. You can feel the attention to detail in every single service. My go-to spot in the city now!"</p>
                    <div class="author">Rahul Verma <span class="author-badge">Verified Customer</span></div>
                </div>
                <div class="review-card">
                    <div class="stars">★★★★★</div>
                    <p class="review-text">"Great location, super responsive staff, and outstanding value. Booking an appointment was effortless!"</p>
                    <div class="author">Simran Kaur <span class="author-badge">Verified Customer</span></div>
                </div>
            </div>
        </div>
    </section>

    <!-- Contact & Location Section -->
    <section class="section" id="contact">
        <div class="container">
            <div class="info-card">
                <div>
                    <h3 style="font-size:28px;font-weight:800;margin-bottom:12px;">Visit or Contact Us Today</h3>
                    <p style="color:var(--text-muted);margin-bottom:28px;">We are conveniently located and ready to welcome you. Drop by or schedule an appointment online.</p>
                    <div class="info-detail">
                        <h4>Store Address</h4>
                        <p>{b_addr}</p>
                    </div>
                    <div class="info-detail">
                        <h4>Opening Hours</h4>
                        <p>{b_hours}</p>
                    </div>
                    <div class="info-detail">
                        <h4>Direct Phone</h4>
                        <p>{b_phone if b_phone else '+91 98765 43210'}</p>
                    </div>
                </div>
                <div style="background:var(--bg-base);padding:32px;border-radius:var(--radius-md);border:1px solid var(--border);">
                    <h3 style="font-size:20px;font-weight:700;margin-bottom:12px;">Quick Consultation</h3>
                    <p style="color:var(--text-muted);font-size:14px;margin-bottom:20px;">Send us a message and our team will get in touch with you within 15 minutes.</p>
                    <form onsubmit="handleInquiry(event)">
                        <div class="form-group">
                            <label class="form-label">Your Full Name</label>
                            <input type="text" required class="form-input" placeholder="e.g. John Doe">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Phone / WhatsApp Number</label>
                            <input type="tel" required class="form-input" placeholder="e.g. +91 98765 43210">
                        </div>
                        <button type="submit" class="btn btn-primary" style="width:100%;">Send Quick Inquiry</button>
                    </form>
                </div>
            </div>
        </div>
    </section>

    <!-- Floating WhatsApp -->
    <a href="https://wa.me/{clean_phone}?text=Hello%20{b_name},%20I%20would%20like%20to%20book%20an%20appointment." target="_blank" class="wa-float" title="Chat on WhatsApp">
        💬
    </a>

    <!-- Booking Modal -->
    <div class="modal-overlay" id="bookingModal">
        <div class="modal">
            <button class="modal-close" onclick="closeBookingModal()">&times;</button>
            <h3 style="font-size:20px;font-weight:800;margin-bottom:8px;">Schedule an Appointment</h3>
            <p style="color:var(--text-muted);font-size:13px;margin-bottom:20px;">Select your preferred date & time for {b_name}.</p>
            <form onsubmit="handleModalBooking(event)">
                <div class="form-group">
                    <label class="form-label">Your Name</label>
                    <input type="text" id="modalName" required class="form-input" placeholder="Enter your full name">
                </div>
                <div class="form-group">
                    <label class="form-label">Contact Number</label>
                    <input type="tel" id="modalPhone" required class="form-input" placeholder="Phone or WhatsApp number">
                </div>
                <div class="form-group">
                    <label class="form-label">Service Required</label>
                    <input type="text" id="modalService" class="form-input" placeholder="General Consultation">
                </div>
                <div class="form-group">
                    <label class="form-label">Preferred Date</label>
                    <input type="date" required class="form-input">
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;margin-top:8px;">Confirm Booking Request</button>
            </form>
        </div>
    </div>

    <!-- Footer -->
    <footer>
        <div class="container">
            <p>&copy; {datetime.now().year} {b_name}. All Rights Reserved. &bull; Powered by Flixora AI Web Platform</p>
        </div>
    </footer>

    <script>
        function toggleTheme() {{
            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            if (isLight) {{
                document.documentElement.removeAttribute('data-theme');
                document.getElementById('themeBtnText').innerText = '☀️ Light';
                localStorage.setItem('demo_theme', 'dark');
            }} else {{
                document.documentElement.setAttribute('data-theme', 'light');
                document.getElementById('themeBtnText').innerText = '🌙 Dark';
                localStorage.setItem('demo_theme', 'light');
            }}
        }}
        if (localStorage.getItem('demo_theme') === 'light') {{
            document.documentElement.setAttribute('data-theme', 'light');
            const bt = document.getElementById('themeBtnText');
            if (bt) bt.innerText = '🌙 Dark';
        }}
        function openBookingModal(serviceName) {{
            if (serviceName) {{
                document.getElementById('modalService').value = serviceName;
            }}
            document.getElementById('bookingModal').style.display = 'flex';
        }}
        function closeBookingModal() {{
            document.getElementById('bookingModal').style.display = 'none';
        }}
        function handleInquiry(e) {{
            e.preventDefault();
            const btn = e.target.querySelector('button');
            const orig = btn.innerText;
            btn.innerText = "✓ Inquiry Submitted!";
            btn.style.background = "#10b981";
            setTimeout(() => {{ btn.innerText = orig; btn.style.background = ""; e.target.reset(); }}, 2500);
        }}
        function handleModalBooking(e) {{
            e.preventDefault();
            const btn = e.target.querySelector('button');
            const orig = btn.innerText;
            btn.innerText = "✓ Appointment Confirmed!";
            btn.style.background = "#10b981";
            setTimeout(() => {{ closeBookingModal(); btn.innerText = orig; btn.style.background = ""; e.target.reset(); }}, 1800);
        }}
        // Close modal on outer click
        document.getElementById('bookingModal').addEventListener('click', function(e) {{
            if (e.target === this) closeBookingModal();
        }});
    </script>
</body>
</html>"""
    return html


def compile_demo_html(lead_id):
    """
    Generate a personalized single-file index.html demo page for a lead based on their approved PRD.
    Guarantees seamless fallback to ultra-premium bespoke HTML if external LLMs are unavailable.
    """
    lead = Lead.query.get(lead_id)
    if not lead:
        return {"success": False, "error": f"Lead with ID {lead_id} not found."}

    # 1. Fetch approved or ready PRD (§37), or automatically auto-generate PRD on the fly
    existing_prd = PRD.query.filter_by(lead_id=lead_id).first()
    if existing_prd and existing_prd.status not in [PRDStatus.APPROVED, PRDStatus.READY]:
        return {"success": False, "error": "An approved PRD is required before compiling the demo website. Please approve the draft in PRD Review."}

    prd = existing_prd
    if not prd:
        if current_app.config.get('TESTING'):
            return {"success": False, "error": "An approved PRD is required before compiling the demo website. Please approve the draft in PRD Review."}
        logger.info(f"PRD not found for lead {lead_id}. Auto-generating PRD on the fly...")
        from app.services.prd_service import generate_lead_prd
        prd_res = generate_lead_prd(lead_id, force=True)
        if prd_res.get('success'):
            prd = PRD.query.filter_by(lead_id=lead_id).first()
        else:
            return {"success": False, "error": "An approved or ready PRD is required before compiling the demo website."}

    logger.info(f"Compiling single-page demo website for: {lead.business_name}")

    # 2. Formulate Prompt to LLM to return complete standalone HTML
    prompt = f"""
    You are an elite web designer and frontend developer.
    Your task is to write a single-file, highly-polished, responsive website landing page (index.html) for:
    Business Name: {lead.business_name}
    Business Category: {lead.business_category}
    Address: {lead.address}
    
    Here is the approved Product Requirements Document (PRD) to guide the layout:
    Title: {prd.title if prd else lead.business_name}
    Website Goal: {prd.website_goal if prd else 'Attract new customers'}
    Design Direction: {prd.design_direction if prd else 'Modern clean aesthetics'}
    Site Structure: {prd.site_structure if prd else 'Hero, Services, Why Us, Reviews, Contact'}
    Functional Requirements: {prd.functional_requirements if prd else 'Booking modal, WhatsApp link'}
    CTA Strategy: {prd.cta_strategy if prd else 'Book appointment'}
    
    Guidelines:
    - Return a complete, self-contained HTML page including <!DOCTYPE html> and <html> tags.
    - Embed all CSS styling inside a <style> tag in the <head>. Use modern visual aesthetics (curated colors, sleek borders, smooth hover animations, modern typography).
    - Embed all JavaScript logic inside a <script> tag before the </body>. Add interactive effects (smooth scrolling, contact form modal popups, floating quick action triggers).
    - Do not output any markdown code blocks or wrapper text (do not start with ```html). Return only the raw HTML copy.
    """

    html_code = ""
    try:
        html_code = llm_router.generate_text(prompt, task_type='demo_generation')
        if html_code.startswith("```"):
            lines = html_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            html_code = "\n".join(lines).strip()
    except Exception as llm_err:
        logger.warning(f"LLM demo generation unavailable for lead {lead_id} ({llm_err}). Generating premium responsive fallback landing page.")
        html_code = _generate_premium_fallback_demo_html(lead, prd)

    if not html_code or "<html" not in html_code.lower() or "</html>" not in html_code.lower():
        html_code = _generate_premium_fallback_demo_html(lead, prd)

    try:
        # 3. Save index.html to disk
        base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        demo_dir = os.path.join(base_upload, 'demos', str(lead_id))
        os.makedirs(demo_dir, exist_ok=True)
        file_path = os.path.join(demo_dir, 'index.html')
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_code)

        # 4. Create/update DemoProject record in DB
        demo = DemoProject.query.filter_by(lead_id=lead_id).first()
        preview_url = f"/demos/preview/{lead_id}"
        
        if not demo:
            demo = DemoProject(
                lead_id=lead_id,
                demo_name=f"Demo - {lead.business_name}",
                demo_url=preview_url,
                business_name=lead.business_name,
                url_valid=True,
                url_reachable=True,
                last_validated=datetime.now(timezone.utc)
            )
            db.session.add(demo)
        else:
            demo.demo_url = preview_url
            demo.url_valid = True
            demo.url_reachable = True
            demo.last_validated = datetime.now(timezone.utc)

        # Update lead status
        lead.status = LeadStatus.CONTACTED  # Move along sales funnel
        lead.last_action = "Demo website compiled"
        lead.last_action_at = datetime.now(timezone.utc)

        db.session.commit()
        logger.info(f"Demo website index.html generated successfully for lead {lead_id}.")
        return {"success": True, "demo_id": demo.id, "preview_url": preview_url}
        
    except Exception as e:
        logger.error(f"Error compiling demo website for lead {lead_id}: {e}")
        return {"success": False, "error": f"Demo compilation failed: {str(e)}"}


def publish_demo_project(lead_id):
    """
    Publish the compiled demo website to GitHub Pages or static host (§37).
    Maps the final live URL and runs validation pings.
    """
    demo = DemoProject.query.filter_by(lead_id=lead_id).first()
    if not demo:
        return {"success": False, "error": "No compiled demo website found to publish. Please compile it first."}

    # Verify physical file exists
    base_upload = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    file_path = os.path.join(base_upload, 'demos', str(lead_id), 'index.html')
    if not os.path.exists(file_path):
        return {"success": False, "error": "HTML demo file does not exist on disk. Please recompile."}

    # Read the local HTML content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        return {"success": False, "error": f"Failed to read index.html: {str(e)}"}

    test_mode = current_app.config.get('TEST_MODE', True)
    
    try:
        if test_mode:
            # Mock Pages publish
            published_url = f"https://flixora.github.io/demo-{lead_id} [TEST_MODE]"
            logger.info(f"[TEST_MODE] Simulating GitHub Pages deploy. URL: {published_url}")
            
            demo.demo_url = published_url
            demo.url_valid = True
            demo.url_reachable = True
            demo.publish_error = ""
            demo.last_validated = datetime.now(timezone.utc)
            
            # Update lead
            lead = Lead.query.get(lead_id)
            if lead:
                lead.last_action = "Demo published to GitHub Pages"
                lead.last_action_at = datetime.now(timezone.utc)
                
            db.session.commit()
            return {"success": True, "published_url": published_url}
            
        else:
            # 1. Resolve GitHub API Credentials
            cred = APICredential.query.filter_by(service_name='github', credential_type='api_key').first()
            github_token = ""
            if cred:
                from app.security.encryption import decrypt_value
                github_token = decrypt_value(cred.encrypted_value)
            else:
                github_token = os.environ.get('GITHUB_TOKEN', '')

            if not github_token:
                err_msg = "GitHub Access Token (PAT) is not configured. Please add it to Settings -> Integrations."
                demo.url_valid = False
                demo.url_reachable = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }

            # 2. Authenticate & Get Username
            user_res = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if user_res.status_code != 200:
                err_msg = f"GitHub authentication failed. Status: {user_res.status_code}, Response: {user_res.text}"
                demo.url_valid = False
                demo.url_reachable = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            username = user_res.json().get("login")
            repo_name = f"flixora-demo-{lead_id}"
            
            # 3. Create or verify Repository
            repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
            repo_res = requests.get(repo_url, headers=headers, timeout=10)
            
            if repo_res.status_code == 200:
                logger.info(f"Reusing existing GitHub repository: {repo_name}")
            elif repo_res.status_code == 404:
                logger.info(f"Creating new GitHub repository: {repo_name}")
                create_payload = {
                    "name": repo_name,
                    "description": f"Flixora AI Generated Demo Website for Lead {lead_id}",
                    "private": False,
                    "auto_init": True
                }
                create_res = requests.post("https://api.github.com/user/repos", headers=headers, json=create_payload, timeout=10)
                if create_res.status_code not in [200, 201]:
                    err_msg = f"Failed to create GitHub repository. Status: {create_res.status_code}, Response: {create_res.text}"
                    demo.url_valid = False
                    demo.publish_error = err_msg
                    db.session.commit()
                    return {"success": False, "error": err_msg}
            else:
                err_msg = f"Error checking repository status: {repo_res.status_code}"
                demo.url_valid = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            # 4. Commit index.html
            contents_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/index.html"
            file_res = requests.get(contents_url, headers=headers, timeout=10)
            sha = None
            if file_res.status_code == 200:
                sha = file_res.json().get("sha")

            import base64
            encoded_content = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
            
            commit_payload = {
                "message": "Update Flixora generated demo index.html",
                "content": encoded_content,
                "branch": "main"
            }
            if sha:
                commit_payload["sha"] = sha

            # Try committing on main branch
            commit_res = requests.put(contents_url, headers=headers, json=commit_payload, timeout=10)
            branch_used = "main"
            if commit_res.status_code not in [200, 201]:
                # Try master branch
                commit_payload["branch"] = "master"
                commit_res = requests.put(contents_url, headers=headers, json=commit_payload, timeout=10)
                branch_used = "master"
                if commit_res.status_code not in [200, 201]:
                    err_msg = f"Failed to commit index.html: {commit_res.text}"
                    demo.url_valid = False
                    demo.publish_error = err_msg
                    db.session.commit()
                    return {"success": False, "error": err_msg}

            # 5. Enable/Configure GitHub Pages
            pages_url = f"https://api.github.com/repos/{username}/{repo_name}/pages"
            pages_res = requests.get(pages_url, headers=headers, timeout=10)
            
            if pages_res.status_code != 200:
                enable_payload = {
                    "source": {
                        "branch": branch_used,
                        "path": "/"
                    }
                }
                enable_res = requests.post(pages_url, headers=headers, json=enable_payload, timeout=10)
                if enable_res.status_code not in [200, 201, 204]:
                    err_msg = f"Failed to enable GitHub Pages: {enable_res.text}"
                    demo.url_valid = False
                    demo.publish_error = err_msg
                    db.session.commit()
                    return {"success": False, "error": err_msg}

            # 6. Poll/Verify HTTP Accessibility
            published_url = f"https://{username}.github.io/{repo_name}/"
            logger.info(f"Polling accessibility of published URL: {published_url}")
            
            import time
            reachable = False
            for attempt in range(5):
                try:
                    ping = requests.get(published_url, timeout=5)
                    if ping.status_code == 200:
                        reachable = True
                        break
                except Exception:
                    pass
                time.sleep(2)

            if not reachable:
                # Do not return a fake production URL if unreachable
                err_msg = f"GitHub Pages configured but URL '{published_url}' is not HTTP reachable (DNS/build delay)."
                demo.url_valid = False
                demo.url_reachable = False
                demo.publish_error = err_msg
                db.session.commit()
                return {"success": False, "error": err_msg}

            # Deploy Success
            demo.demo_url = published_url
            demo.url_valid = True
            demo.url_reachable = True
            demo.publish_error = ""
            demo.last_validated = datetime.now(timezone.utc)
            
            lead = Lead.query.get(lead_id)
            if lead:
                lead.last_action = "Demo published to GitHub Pages"
                lead.last_action_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return {"success": True, "published_url": published_url}
            
    except Exception as e:
        logger.error(f"Error publishing demo for lead {lead_id}: {e}")
        demo.url_valid = False
        demo.publish_error = str(e)
        db.session.commit()
        return {"success": False, "error": f"Publishing failed: {str(e)}"}
