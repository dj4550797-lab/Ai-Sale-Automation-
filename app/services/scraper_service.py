"""
Flixora AI Sales Automation Agent — Scraper Service

Scrapes local business websites for structure, text content, contact details, and assets.
Supports simulated profiles ONLY when TEST_MODE is explicitly True.
Includes auto-resolution for Cloudflare/ByetHost AES challenges (e.g. .great-site.net).
"""
import re
import json
from html.parser import HTMLParser
import urllib.request
import urllib.error
from flask import current_app
import httpx
from app.utils.logger import get_logger

logger = get_logger('services')


class SimpleHTMLParser(HTMLParser):
    """HTML Parser to extract title, meta description, headings, forms, and verified contact links."""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta_description = ""
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
        self.in_script = False
        self.script_type = ""
        self.script_buffer = ""
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attr_dict = dict(attrs)
        
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = (attr_dict.get("name") or attr_dict.get("property") or "").lower()
            content = attr_dict.get("content", "")
            if name in ["description", "og:description"] and not self.meta_description:
                self.meta_description = content.strip()
        elif tag == "script":
            self.in_script = True
            self.script_type = attr_dict.get("type", "")
            self.script_buffer = ""
        elif tag == "form":
            self.forms_count += 1
        elif tag == "a":
            val = attr_dict.get("href", "")
            if val:
                self.links.append(val)
                val_l = val.lower()
                if val_l.startswith("tel:"):
                    clean_p = val[4:].strip().replace(" ", "").replace("-", "")
                    if len(clean_p) >= 7:
                        self.phone_numbers_found.add(val[4:].strip())
                elif val_l.startswith("mailto:"):
                    clean_e = val[7:].strip().split("?")[0]
                    if "@" in clean_e:
                        self.email_addresses_found.add(clean_e)
                elif any(s in val_l for s in [
                    "instagram.com", "facebook.com", "linkedin.com",
                    "youtube.com", "twitter.com", "x.com", "pinterest.com"
                ]):
                    # Ignore pure root share/intent links
                    if not any(k in val_l for k in ["sharer", "intent/tweet", "sharearticle"]):
                        self.social_links_found.add(val.strip())
                elif any(k in val_l for k in [
                    "booking", "book", "appointment", "calendar",
                    "reservations", "schedule", "contact-us", "contact"
                ]):
                    self.booking_links_found.add(val.strip())

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script":
            self.in_script = False
            # Parse Schema.org JSON-LD
            if "ld+json" in self.script_type.lower() and self.script_buffer.strip():
                try:
                    data = json.loads(self.script_buffer.strip())
                    self._parse_json_ld(data)
                except Exception:
                    pass
        self.current_tag = None

    def _parse_json_ld(self, data):
        """Extract structured telephone, email, and social profiles from schema.org."""
        if isinstance(data, list):
            for item in data:
                self._parse_json_ld(item)
            return

        if not isinstance(data, dict):
            return

        # Telephone
        tel = data.get("telephone")
        if tel:
            if isinstance(tel, list):
                for t in tel:
                    self.phone_numbers_found.add(str(t).strip())
            else:
                self.phone_numbers_found.add(str(tel).strip())

        # Email
        em = data.get("email")
        if em:
            if isinstance(em, list):
                for e in em:
                    self.email_addresses_found.add(str(e).strip())
            else:
                self.email_addresses_found.add(str(em).strip())

        # SameAs social links
        same_as = data.get("sameAs")
        if same_as:
            if isinstance(same_as, list):
                for s in same_as:
                    self.social_links_found.add(str(s).strip())
            elif isinstance(same_as, str):
                self.social_links_found.add(same_as.strip())

        # ContactPoint
        cp = data.get("contactPoint")
        if isinstance(cp, dict):
            self._parse_json_ld(cp)

    def handle_data(self, data):
        if self.in_script:
            self.script_buffer += data
            return

        data_clean = data.strip()
        if not data_clean:
            return

        if self.in_title:
            self.title = (self.title + " " + data_clean).strip() if self.title else data_clean
        elif self.current_tag in ["h1", "h2", "h3"]:
            self.headings.append(f"{self.current_tag}: {data_clean}")
        elif self.current_tag == "p":
            self.paragraph_count += 1

        # Phone numbers in plain text (Indian 10-digit mobile or international formats)
        phones = re.findall(r'(?:\+?91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}|\+?\d{1,4}[-\s]?(?:\(\d{1,4}\)[-\s]?)?\d{3,4}[-\s]?\d{3,4}', data_clean)
        for ph in phones:
            digits_only = re.sub(r'\D', '', ph)
            if len(digits_only) >= 10:
                self.phone_numbers_found.add(ph.strip())

        # Email addresses in plain text
        emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', data_clean)
        for email in emails:
            # Filter obvious image/font asset names
            if not any(email.lower().endswith(ext) for ext in ['.png', '.jpg', '.webp', '.svg', '.gif']):
                self.email_addresses_found.add(email.strip())

        # Owner / Contact person name pattern
        match = re.search(r'\b(?:owner|founder|contact|manager|proprietor|director)\b\s*:\s*([a-zA-Z\s]{3,30})', data_clean, re.IGNORECASE)
        if match:
            owner_name = match.group(1).strip().split("\n")[0].strip()
            if owner_name and len(owner_name.split()) <= 4:
                self.owner_names_found.add(owner_name)


def _solve_byethost_challenge_if_present(html_content, url):
    """
    Solves ByetHost / InfinityFree AES anti-bot challenge (served on .great-site.net / .rf.gd).
    Returns the real page HTML if challenge was detected and solved, or original html_content.
    """
    if "toNumbers" not in html_content or "slowAES.decrypt" not in html_content:
        return html_content

    logger.info(f"Detected ByetHost AES challenge on {url}. Computing anti-bot cookie...")
    try:
        match = re.search(
            r'toNumbers\("([a-f0-9]{32})"\),b=toNumbers\("([a-f0-9]{32})"\),c=toNumbers\("([a-f0-9]{32})"\)',
            html_content
        )
        if not match:
            return html_content

        key_hex, iv_hex, ct_hex = match.group(1), match.group(2), match.group(3)

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)
        ciphertext = bytes.fromhex(ct_hex)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        cookie_val = (decryptor.update(ciphertext) + decryptor.finalize()).hex()

        target_url = url if "?i=" in url else (url + ("&i=1" if "?" in url else "?i=1"))
        req = urllib.request.Request(
            target_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cookie": f"__test={cookie_val}"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            real_html = resp.read().decode('utf-8', errors='ignore')
            logger.info(f"Successfully bypassed ByetHost challenge for {url} (Length: {len(real_html)} bytes)")
            return real_html
    except Exception as e:
        logger.warning(f"Failed to solve ByetHost AES challenge for {url}: {e}")
        return html_content


def scrape_website(url):
    """
    Scrape a website.
    In TEST_MODE = True, returns a simulated structural model based on business profile info.
    In LIVE_MODE (TEST_MODE = False), makes real HTTP request and extracts live metadata.
    """
    if not url:
        return {"success": False, "error": "No website URL provided."}

    # Ensure protocol
    fetch_url = url
    if not fetch_url.startswith("http://") and not fetch_url.startswith("https://"):
        fetch_url = "https://" + fetch_url

    # Handle TEST_MODE (only when explicitly set to True)
    test_mode = current_app.config.get('TEST_MODE', False)
    if test_mode:
        logger.info(f"[TEST_MODE] Simulating website crawl for: {fetch_url}")
        return _get_mock_website_profile(fetch_url)

    logger.info(f"Live scraping website: {fetch_url}")
    html_text = ""
    status_code = 200

    # 1. Primary fetch attempt with urllib and standard desktop browser headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }

    try:
        req = urllib.request.Request(fetch_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            status_code = response.status
            html_text = response.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        status_code = e.code
        html_text = e.read().decode('utf-8', errors='ignore') if e.fp else ""
        if status_code >= 400 and not html_text:
            return {"success": False, "error": f"Failed to load website. Status code: {status_code}"}
    except Exception as e_urllib:
        # Fallback to httpx if urllib encounters connection issues
        logger.debug(f"Urllib failed ({e_urllib}), attempting httpx fallback for {fetch_url}")
        try:
            resp = httpx.get(fetch_url, headers=headers, timeout=12.0, follow_redirects=True, verify=False)
            status_code = resp.status_code
            html_text = resp.text
        except Exception as e_httpx:
            logger.error(f"Error scraping website {fetch_url}: {e_httpx}")
            return {
                "success": False,
                "error": f"Connection failed or timed out: {str(e_httpx)}"
            }

    # 2. Check and solve ByetHost/InfinityFree challenge if necessary
    html_text = _solve_byethost_challenge_if_present(html_text, fetch_url)

    if not html_text or len(html_text.strip()) < 50:
        return {
            "success": False,
            "error": f"Empty response received from {fetch_url} (HTTP {status_code})"
        }

    # 3. Parse HTML
    parser = SimpleHTMLParser()
    try:
        parser.feed(html_text)
    except Exception as e:
        logger.warning(f"HTML parsing warning for {fetch_url}: {e}")

    extracted_title = parser.title or ""
    if not extracted_title and parser.headings:
        extracted_title = parser.headings[0].split(":", 1)[-1].strip()

    return {
        "success": True,
        "url": fetch_url,
        "title": extracted_title or "Business Website",
        "meta_description": parser.meta_description,
        "headings": parser.headings[:20],
        "paragraph_count": max(parser.paragraph_count, 1),
        "links_count": len(parser.links),
        "links_list": parser.links[:15],
        "forms_count": parser.forms_count,
        "detected_phones": list(parser.phone_numbers_found),
        "detected_emails": list(parser.email_addresses_found),
        "detected_socials": list(parser.social_links_found),
        "detected_bookings": list(parser.booking_links_found),
        "detected_owners": list(parser.owner_names_found),
        "html_length": len(html_text),
        "raw_text_stub": html_text[:3000]
    }


def _get_mock_website_profile(url):
    """Generate realistic poor-UX mock layouts for local business niches in unit test mode."""
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
            "meta_description": "Beauty Express salon offering hair, facials and massage.",
            "headings": ["h1: Beauty Express Hair Salon", "h2: Services We Offer"],
            "paragraph_count": 4,
            "links_count": 3,
            "links_list": ["/", "/about-us", "#services"],
            "forms_count": 0,
            "detected_phones": ["9876543210"],
            "detected_emails": ["info@beautyexpress.com"],
            "detected_socials": ["https://instagram.com/beautyexpress"],
            "detected_bookings": [],
            "detected_owners": ["Jane Stevens"],
            "html_length": 4500,
            "raw_text_stub": "Welcome to Beauty & Hair Express. We offer styling, blowouts, and facials."
        },
        "dentist": {
            "title": "Family Dental & Smile Clinic",
            "meta_description": "Complete family dental care and smile enhancement.",
            "headings": ["h1: Dental Smile Clinic", "h2: Procedures"],
            "paragraph_count": 5,
            "links_count": 4,
            "links_list": ["/", "/gallery.html"],
            "forms_count": 0,
            "detected_phones": ["111-222-3334"],
            "detected_emails": ["clinic@smilefamilydental.com"],
            "detected_socials": ["https://facebook.com/familydentist"],
            "detected_bookings": [],
            "detected_owners": ["Dr. John Doe"],
            "html_length": 5200,
            "raw_text_stub": "At Family Dental Clinic we provide crowns, cleanings, and root canals."
        },
        "restaurant": {
            "title": "Green Valley Restaurant - Delicious Pizza & Pasta",
            "meta_description": "Finest Italian cuisine and dining experience.",
            "headings": ["h1: Green Valley Diner", "h2: Lunch Menu"],
            "paragraph_count": 3,
            "links_count": 5,
            "links_list": ["/", "/menu"],
            "forms_count": 0,
            "detected_phones": ["222-333-4445"],
            "detected_emails": ["reservations@greenvalleydiner.com"],
            "detected_socials": ["https://instagram.com/greenvalleydiner"],
            "detected_bookings": [],
            "detected_owners": ["Marco Rossi"],
            "html_length": 6100,
            "raw_text_stub": "Authentic wood-fired pizza and handmade pasta since 2012."
        },
        "gym": {
            "title": "Iron Temple Fitness Center",
            "meta_description": "Heavy lifting and premier fitness gym.",
            "headings": ["h1: Iron Temple Gym", "h2: Membership Plans"],
            "paragraph_count": 6,
            "links_count": 2,
            "links_list": ["/", "/contact"],
            "forms_count": 1,
            "detected_phones": ["333-444-5556"],
            "detected_emails": ["membership@irontemple.com"],
            "detected_socials": ["https://facebook.com/irontemplegym"],
            "detected_bookings": ["https://irontemple.com/book-session"],
            "detected_owners": ["Arnold Stone"],
            "html_length": 4100,
            "raw_text_stub": "Premier heavy lifting gym. Memberships starting at 2000 INR per month."
        },
        "generic": {
            "title": "Welcome to Local Business Hub",
            "meta_description": "Local business services and solutions.",
            "headings": ["h1: Local Business Services", "h2: About"],
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
            "raw_text_stub": "We provide premium local solutions. Contact us for quotes."
        }
    }

    profile = mock_profiles[niche]
    profile["success"] = True
    profile["url"] = url
    return profile
