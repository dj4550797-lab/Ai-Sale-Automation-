"""
Flixora AI Sales Automation Agent — Google Places API Integration

Uses Places API (New) endpoints Text Search and Place Details with field masking.
Extracts normalized business identity including address components (city, state, country, postal code).
"""
import re
import requests
from app.integrations.maps.base import BusinessDataProvider
from app.utils.logger import get_logger

logger = get_logger('integrations')


def parse_address_text(addr):
    """Fallback parser to accurately extract city, state, country, and postal code from formatted address."""
    if not addr:
        return {'city': '', 'state': '', 'country': '', 'postal_code': ''}

    parts = [p.strip() for p in addr.split(',') if p.strip()]
    country = ''
    postal_code = ''
    state = ''
    city = ''

    # Country detection from trailing token
    if parts:
        last = parts[-1]
        known_countries = ['india', 'usa', 'united states', 'uk', 'united kingdom', 'australia', 'canada', 'uae', 'singapore']
        if last.lower() in known_countries:
            country = last
            parts = parts[:-1]

    # Postal / PIN code detection
    pin_match = re.search(r'\b(\d{5,6}(?:-\d{4})?)\b', addr)
    if pin_match:
        postal_code = pin_match.group(1)

    # State detection from last remaining token
    if parts:
        state_part = parts[-1]
        state_part_clean = re.sub(r'\b\d{5,6}(?:-\d{4})?\b', '', state_part).strip(' -')
        state = state_part_clean
        parts = parts[:-1]

    # City detection from preceding token
    if parts:
        city = parts[-1]

    return {
        'city': city,
        'state': state,
        'country': country or 'India',
        'postal_code': postal_code
    }


class GooglePlacesProvider(BusinessDataProvider):
    """Google Places API (New) provider implementation."""

    def search_businesses(self, location, category, limit=20, page_token=None):
        """Search local businesses using Google Places Text Search (New)."""
        url = "https://places.googleapis.com/v1/places:searchText"
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.primaryType,"
                "places.formattedAddress,places.addressComponents,places.nationalPhoneNumber,"
                "places.websiteUri,places.rating,places.userRatingCount,"
                "places.editorialSummary,places.regularOpeningHours,"
                "nextPageToken"
            )
        }

        payload = {
            "textQuery": f"{category} in {location}",
            "pageSize": min(limit, 20)
        }
        if page_token:
            payload["pageToken"] = page_token

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code != 200:
                logger.error(f"Google Places Text Search error: {response.text}")
                return [], None

            data = response.json()
            places = data.get("places", [])
            next_page_token = data.get("nextPageToken")
            
            results = []
            for p in places:
                normalized = self._normalize_place_data(p)
                # Keep category clean
                if category and category.lower() != normalized.get('business_name', '').lower():
                    normalized['business_category'] = category
                results.append(normalized)

            return results, next_page_token
        except Exception as e:
            logger.error(f"Google Places API request failed: {e}")
            return [], None

    def get_business_details(self, place_id):
        """Fetch details for a place using Place Details (New)."""
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "id,displayName,primaryType,formattedAddress,addressComponents,"
                "nationalPhoneNumber,websiteUri,rating,userRatingCount,"
                "editorialSummary,regularOpeningHours"
            )
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                logger.error(f"Google Places Detail error: {response.text}")
                return None

            p = response.json()
            return self._normalize_place_data(p)
        except Exception as e:
            logger.error(f"Google Place Details API request failed: {e}")
            return None

    def _normalize_place_data(self, p):
        """Map Places API (New) JSON keys to independent DB schema fields (§21)."""
        display_name = p.get('displayName', {})
        business_name = display_name.get('text', 'Unknown Business')
        
        description_data = p.get('editorialSummary', {})
        description = description_data.get('text', '') if isinstance(description_data, dict) else ''

        hours_data = p.get('regularOpeningHours', {})
        weekday_desc = hours_data.get('weekdayDescriptions', []) if isinstance(hours_data, dict) else []
        business_hours = ", ".join(weekday_desc) if weekday_desc else ''
        
        formatted_address = p.get('formattedAddress', '')
        
        # Parse components from addressComponents if available
        city = ''
        state = ''
        country = ''
        postal_code = ''
        components = p.get('addressComponents', [])
        
        for comp in components:
            types = comp.get('types', [])
            text = comp.get('longText') or comp.get('shortText') or ''
            if any(t in types for t in ['locality', 'sublocality_level_1', 'sublocality']) and not city:
                city = text
            elif 'administrative_area_level_1' in types:
                state = text
            elif 'country' in types:
                country = text
            elif 'postal_code' in types:
                postal_code = text

        # Fallback to string parser if any component is missing
        if not city or not state or not country or not postal_code:
            parsed = parse_address_text(formatted_address)
            city = city or parsed['city']
            state = state or parsed['state']
            country = country or parsed['country']
            postal_code = postal_code or parsed['postal_code']

        return {
            'business_name': business_name,
            'business_category': p.get('primaryType', 'business'),
            'address': formatted_address,
            'city': city,
            'state': state,
            'country': country,
            'postal_code': postal_code,
            'phone': p.get('nationalPhoneNumber', ''),
            'website_url': p.get('websiteUri', ''),
            'rating': p.get('rating'),
            'review_count': p.get('userRatingCount', 0),
            'google_place_id': p.get('id'),
            'description': description,
            'business_hours': business_hours
        }
