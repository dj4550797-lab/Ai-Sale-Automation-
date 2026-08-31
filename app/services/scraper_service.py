"""
Flixora AI Sales Automation Agent — Scraper Service

Scrapes local business websites for structure, text content, and assets.
Supports simulated profiles when TEST_MODE is active.
"""
import re
from html.parser import HTMLParser
from flask import current_app
import httpx
from app.utils.logger import get_logger

logger = get_logger('services')


class SimpleHTMLParser(HTMLParser):
    """Basic HTML Parser to extract title, headings, paragraph count, forms, and links."""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.headings = []
        self.paragraph_count = 0
        self.links = []
        self.forms_count = 0
        self.phone_numbers_found = set()
        self.email_addresses_found = set()
        self.social_links_found = set()
        self.booking_links_found = set()
        self.owner_names_found = set()
        
        self.in_title = False
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag == "title":
            self.in_title = True
        elif tag == "form":
            self.forms_count += 1
        elif tag == "a":
            for attr, val in attrs:
                if attr == "href" and val:
                    self.links.append(val)
                    if val.startswith("tel:"):
                        self.phone_numbers_found.add(val[4:])
                    elif val.startswith("mailto:"):
                        self.email_addresses_found.add(val[7:])
                    elif "instagram.com/" in val.lower() or "facebook.com/" in val.lower():
                        self.social_links_found.add(val)
                    elif any(k in val.lower() for k in ["booking", "book", "appointment", "calendar", "reservations", "schedule"]):
                        self.booking_links_found.add(val)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        self.current_tag = None

    def handle_data(self, data):
        data_clean = data.strip()
        if not data_clean:
            return
            
        if self.in_title:
            self.title = data_clean
        elif self.current_tag in ["h1", "h2", "h3"]:
            self.headings.append(f"{self.current_tag}: {data_clean}")
        elif self.current_tag == "p":
            self.paragraph_count += 1
            
        # Basic regex check for phone numbers in data
        phones = re.findall(r'\+?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4}', data_clean)
        for ph in phones:
            if len(ph.replace("-", "").replace(" ", "")) >= 8:
                self.phone_numbers_found.add(ph)

        # Regex check for email addresses in data
        emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', data_clean)
        for email in emails:
            self.email_addresses_found.add(email)

        # Search for owner/contact person name
        match = re.search(r'\b(?:owner|founder|contact|manager|proprietor)\b\s*:\s*([a-zA-Z\s]{3,30})', data_clean, re.IGNORECASE)
        if match:
            owner_name = match.group(1).strip()
            owner_name = owner_name.split("\n")[0].strip()
            if owner_name and len(owner_name.split()) <= 4:
                self.owner_names_found.add(owner_name)


def scrape_website(url):
    """
    Scrape a website.
    In TEST_MODE = True, returns a simulated structural model based on business profile info.
    In LIVE_MODE (TEST_MODE = False), makes a requests/httpx call and extracts metadata.
    """
    if not url:
        return {"success": False, "error": "No website URL provided."}

    # Handle TEST_MODE
    test_mode = current_app.config.get('TEST_MODE', True)
    if test_mode:
        logger.info(f"[TEST_MODE] Simulating website crawl for: {url}")
        return _get_mock_website_profile(url)

    logger.info(f"Scraping website: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Failed to load website. Status code: {response.status_code}"
            }
            
        parser = SimpleHTMLParser()
        parser.feed(response.text)
        
        return {
            "success": True,
            "url": url,
            "title": parser.title or "Business Website",
            "headings": parser.headings[:15],  # Limit headings
            "paragraph_count": parser.paragraph_count,
            "links_count": len(parser.links),
            "links_list": parser.links[:10],
            "forms_count": parser.forms_count,
            "detected_phones": list(parser.phone_numbers_found),
            "detected_emails": list(parser.email_addresses_found),
            "detected_socials": list(parser.social_links_found),
            "detected_bookings": list(parser.booking_links_found),
            "detected_owners": list(parser.owner_names_found),
            "html_length": len(response.text),
            "raw_text_stub": response.text[:2000]  # First 2kb
        }
    except Exception as e:
        logger.error(f"Error scraping website {url}: {e}")
        return {
            "success": False,
            "error": f"Connection failed or timed out: {str(e)}"
        }


def _get_mock_website_profile(url):
    """Generate realistic poor-UX mock layouts for local business niches."""
    # Determine business type roughly from url keywords
    url_lower = url.lower()
    
    niche = "generic"
    if "salon" in url_lower or "hair" in url_lower or "spa" in url_lower:
        niche = "salon"
    elif "dental" in url_lower or "dentist" in url_lower or "teeth" in url_lower:
        niche = "dentist"
    elif "restaurant" in url_lower or "cafe" in url_lower or "bakery" in url_lower or "food" in url_lower:
        niche = "restaurant"
    elif "gym" in url_lower or "fitness" in url_lower or "yoga" in url_lower:
        niche = "gym"

    mock_profiles = {
        "salon": {
            "title": "Welcome to Beauty & Hair Express - Bookings",
            "headings": [
                "h1: Beauty Express Hair Salon",
                "h2: Services We Offer",
                "h2: Hair Styling",
                "h3: Facials & Massage",
                "h2: Contact Us"
            ],
            "paragraph_count": 4,
            "links_count": 3,
            "links_list": ["/", "/about-us", "#services", "https://instagram.com/beautyexpress"],
            "forms_count": 0,  # No booking forms (bad UX!)
            "detected_phones": ["9876543210"],
            "detected_emails": ["info@beautyexpress.com"],
            "detected_socials": ["https://instagram.com/beautyexpress", "https://facebook.com/beautyexpress"],
            "detected_bookings": ["https://beautyexpress.com/book-appointment"],
            "detected_owners": ["Jane Stevens"],
            "html_length": 4500,
            "raw_text_stub": "Welcome to Beauty & Hair Express. We offer styling, blowouts, and facials. The salon is open Tuesday to Sunday. To book, call us at 9876543210. Our site is hosted on blogger. Owner: Jane Stevens. Email us at info@beautyexpress.com."
        },
        "dentist": {
            "title": "Family Dental & Smile Clinic",
            "headings": [
                "h1: Dental Smile Clinic",
                "h2: Dr. John Doe, DDS",
                "h2: Procedures",
                "h2: Opening Hours"
            ],
            "paragraph_count": 5,
            "links_count": 4,
            "links_list": ["/", "/gallery.html", "/price_list.pdf", "/map.html", "https://facebook.com/familydentist"],
            "forms_count": 0,  # No online appointments
            "detected_phones": ["111-222-3334"],
            "detected_emails": ["clinic@smilefamilydental.com"],
            "detected_socials": ["https://facebook.com/familydentist"],
            "detected_bookings": [],
            "detected_owners": ["Dr. John Doe"],
            "html_length": 5200,
            "raw_text_stub": "At Family Dental Clinic we provide crowns, cleanings, and root canals. Dr John has been in practice since 1999. Visit us at South Extension. Call 111-222-3334 to make an appointment. Owner: Dr. John Doe. Email: clinic@smilefamilydental.com."
        },
        "restaurant": {
            "title": "Green Valley Restaurant - Delicious Pizza & Pasta",
            "headings": [
                "h1: Green Valley Diner",
                "h2: Lunch Menu",
                "h2: Dinner Menu",
                "h2: Gallery"
            ],
            "paragraph_count": 3,
            "links_count": 2,
            "links_list": ["/", "/menu_large_format.jpg", "https://instagram.com/greenvalleydiner"], # PDF/JPEG menu is bad mobile UX
            "forms_count": 0,
            "detected_phones": ["222-333-4445"],
            "detected_emails": ["info@greenvalleydiner.com"],
            "detected_socials": ["https://instagram.com/greenvalleydiner"],
            "detected_bookings": [],
            "detected_owners": ["Mario Rossi"],
            "html_length": 3200,
            "raw_text_stub": "Green Valley Diner has served Dwarka for 10 years. We cook Italian pizza, pasta, and Indian curries. Our menu is attached below as a JPEG. Please call 222-333-4445 for catering. Owner: Mario Rossi. Email: info@greenvalleydiner.com."
        },
        "gym": {
            "title": "Iron Temple Fitness Gym - Gurgaon",
            "headings": [
                "h1: Iron Temple Gym",
                "h2: Membership Pricing",
                "h2: Trainers"
            ],
            "paragraph_count": 4,
            "links_count": 2,
            "links_list": ["/", "/contact", "https://facebook.com/irontemplegym"],
            "forms_count": 1,
            "detected_phones": ["333-444-5556"],
            "detected_emails": ["membership@irontemple.com"],
            "detected_socials": ["https://facebook.com/irontemplegym"],
            "detected_bookings": ["https://irontemple.com/book-session"],
            "detected_owners": ["Arnold Stone"],
            "html_length": 4100,
            "raw_text_stub": "Gurgaon's premier heavy lifting gym. Memberships starting at 2000 INR per month. Open 24/7. Trainers are available for bookings. Phone support: 333-444-5556. Owner: Arnold Stone. Email: membership@irontemple.com."
        },
        "generic": {
            "title": "Welcome to Local Business Hub",
            "headings": [
                "h1: Local Business Services",
                "h2: About",
                "h2: Our Services"
            ],
            "paragraph_count": 3,
            "links_count": 1,
            "links_list": ["/"],
            "forms_count": 0,
            "detected_phones": ["444-555-6667"],
            "detected_emails": ["contact@localhub.com"],
            "detected_socials": [],
            "detected_bookings": [],
            "detected_owners": ["Bob Miller"],
            "html_length": 2500,
            "raw_text_stub": "We provide premium local solutions. Contact us for quotes. Customer support line: 444-555-6667. Owner: Bob Miller. Email: contact@localhub.com."
        }
    }

    profile = mock_profiles[niche]
    profile["success"] = True
    profile["url"] = url
    return profile
