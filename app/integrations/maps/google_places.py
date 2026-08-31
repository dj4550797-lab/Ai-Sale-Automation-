"""
Flixora AI Sales Automation Agent — Google Places API Integration

Uses Places API (New) endpoints Text Search and Place Details with field masking.
"""
import requests
from app.integrations.maps.base import BusinessDataProvider
from app.utils.logger import get_logger

logger = get_logger('integrations')


class GooglePlacesProvider(BusinessDataProvider):
    """Google Places API (New) provider implementation."""

    def search_businesses(self, location, category, limit=20, page_token=None):
        """Search local businesses using Google Places Text Search (New)."""
        url = "https://places.googleapis.com/v1/places:searchText"
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            # Strict field masks to reduce data payload and transaction cost (§15)
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.primaryType,"
                "places.formattedAddress,places.nationalPhoneNumber,"
                "places.websiteUri,places.rating,places.userRatingCount,"
                "places.editorialSummary,places.regularOpeningHours,"
                "nextPageToken"
            )
        }

        payload = {
            "textQuery": f"{category} in {location}",
            "pageSize": min(limit, 20)  # Places API page size limit
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
                "id,displayName,primaryType,formattedAddress,"
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
        
        return {
            'business_name': business_name,
            'business_category': p.get('primaryType', 'business'),
            'address': p.get('formattedAddress', ''),
            'phone': p.get('nationalPhoneNumber', ''),
            'website_url': p.get('websiteUri', ''),
            'rating': p.get('rating'),
            'review_count': p.get('userRatingCount', 0),
            'google_place_id': p.get('id'),
            'description': description,
            'business_hours': business_hours
        }
