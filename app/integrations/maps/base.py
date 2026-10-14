"""
Flixora AI Sales Automation Agent — Maps Base Provider

Interface for local business data search integrations (§103).
"""
from abc import ABC, abstractmethod


class BusinessDataProvider(ABC):
    """Abstract base provider for local business search."""

    def __init__(self, api_key):
        self.api_key = api_key

    @abstractmethod
    def search_businesses(self, location, category, limit=20, page_token=None):
        """Search businesses matching query. Returns (normalized dict list, next_page_token) tuple."""
        pass

    @abstractmethod
    def get_business_details(self, place_id):
        """Get details for a single place. Returns normalized business detail dict."""
        pass
