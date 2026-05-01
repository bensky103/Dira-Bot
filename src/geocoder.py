import logging

import requests

from src.config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Yad2/Facebook often label apartments by the wrong city (e.g. a Givatayim
# street tagged as "תל אביב" because the post lives in a TLV group). Google
# returns the actual locality, but in inconsistent spellings — normalize them.
CITY_ALIASES: dict[str, str] = {
    "תל אביב-יפו": "תל אביב",
    "תל אביב יפו": "תל אביב",
    "Tel Aviv-Yafo": "תל אביב",
    "Tel Aviv": "תל אביב",
    "Ramat Gan": "רמת גן",
    "Givatayim": "גבעתיים",
    "Herzliya": "הרצליה",
    "Ramat HaSharon": "רמת השרון",
}


def geocode_address(street: str, city: str) -> dict | None:
    """Single Google Geocoding call that returns coords + neighborhood + verified city.

    Returns:
        {"lat": float, "lng": float, "area": str|None, "verified_city": str|None}
        or None if geocoding fails / no API key / no street.

    A single call gives us everything: address_components contain both the
    `neighborhood`/`sublocality` (area) and the `locality` (real city).
    Doing this once per new listing replaces what used to be two separate
    Google API calls (forward geocode in Python + reverse geocode in Next.js).
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

        result = data["results"][0]
        location = result.get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            return None

        area: str | None = None
        verified_city: str | None = None
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            name = comp.get("long_name", "")
            if area is None and (
                "neighborhood" in types
                or "sublocality" in types
                or "sublocality_level_1" in types
            ):
                area = name
            if verified_city is None and "locality" in types:
                verified_city = CITY_ALIASES.get(name, name)

        logger.info(
            "Geocoded '%s' -> (%.5f, %.5f) area=%s city=%s",
            query, lat, lng, area, verified_city,
        )
        return {
            "lat": lat,
            "lng": lng,
            "area": area,
            "verified_city": verified_city,
        }

    except Exception as e:
        logger.error("Geocoding error for '%s': %s", query, e)
        return None


def resolve_area(street: str, city: str) -> str | None:
    """Backwards-compatible thin wrapper that returns only the area name."""
    result = geocode_address(street, city)
    return result.get("area") if result else None

