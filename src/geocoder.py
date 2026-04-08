import logging

import requests

from src.config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def resolve_area(street: str, city: str) -> str | None:
    """Use Google Maps Geocoding API to resolve a street+city to a neighborhood name.

    Returns the neighborhood/sublocality name in Hebrew, or None if not found.
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.debug("No GOOGLE_MAPS_API_KEY configured, skipping geocoding")
        return None

    if not street or not city:
        return None

    query = f"{street}, {city}, ישראל"

    try:
        resp = requests.get(
            GEOCODE_URL,
            params={
                "address": query,
                "key": GOOGLE_MAPS_API_KEY,
                "language": "he",
                "region": "il",
            },
            timeout=5,
        )
        data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            logger.debug("Geocoding returned no results for: %s", query)
            return None

        components = data["results"][0].get("address_components", [])

        # Look for neighborhood or sublocality in address components
        for comp in components:
            types = comp.get("types", [])
            if "neighborhood" in types or "sublocality" in types or "sublocality_level_1" in types:
                area = comp.get("long_name", "")
                logger.info("Geocoded area: %s -> %s", query, area)
                return area

        logger.debug("Geocoding found address but no neighborhood for: %s", query)
        return None

    except Exception as e:
        logger.error("Geocoding error for '%s': %s", query, e)
        return None
